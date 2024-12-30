# Thesis/handle/camera_gstreamer.py
import cv2
from flask import Flask, Response, render_template, jsonify
import os
import signal
import threading
import time
import subprocess
import re

import numpy as np
import random
import paho.mqtt.client as paho
import smtplib
import atexit

from collections import deque
from datetime import datetime
from twilio.rest import Client

from iot.firebase.push_image import upload_images_and_generate_html
from handle.record_handle import RecordHandler
from iot.mqtt.publish import MQTTClient
from email.message import EmailMessage
from handle.email_config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL
from handle.sms_config import ACCOUNT_SID, AUTH_TOKEN

# Initialize Flask app
app = Flask(__name__)

# Global variables
frame_lock = threading.Lock()
camera = None
active_viewers = set()
server_running = False

# Constants
ACCEL_THRESHOLD = 2.5 * 9.8 # also remember changing threshold acc in sensors_handle.py
SPEED_DROP_THRESHOLD = 0

class AccidentDetector:
    def __init__(self):
        # Constants
        # self.ACC_THRESHOLD = 1.5 * 9.81  # Critical impact threshold (m/s²)
        # self.SPEED_DROP_THRESHOLD = 15    # Sudden speed drop threshold (km/h)
        
        # Acceleration processing
        self.acc_window = deque(maxlen=6)  # Store last 5 acc readings (~75ms at 66Hz)
        self.acc_timestamp = deque(maxlen=5)
        self.potential_accident = False
        self.accident_timestamp = None
        
        # Speed processing
        self.last_speed = None
        self.last_speed_time = None
        self.speed_drop_confirmed = False
        
        # Thread safety
        self.lock = threading.Lock()

    def process_acceleration(self, acc_value, timestamp):
        with self.lock:
            if self.potential_accident: # just add here
                return "NORMAL" # just add here 
            
            self.acc_window.append(abs(acc_value))
            self.acc_timestamp.append(timestamp)
            
            # Filter noise: Check if we have 2 readings above threshold in our window
            high_acc_count = sum(1 for acc in self.acc_window if acc > ACCEL_THRESHOLD)
            
            if high_acc_count >= 2:
                self.potential_accident = True
                self.accident_timestamp = timestamp
                return "POTENTIAL_ACCIDENT"
            
            return "NORMAL"

    def process_speed(self, current_speed, timestamp):
        """Process incoming speed data (called at 1Hz)"""
        with self.lock:
            if not self.last_speed:
                self.last_speed = current_speed
                self.last_speed_time = timestamp
                return "NORMAL"
            
            speed_drop = self.last_speed - current_speed
            print(f"speed drop is {speed_drop}")
            print(f"self.last_speed is {self.last_speed}")
            
            # If we have a potential accident from acceleration
            if self.potential_accident:
                # Check if speed reading is within 2 seconds of potential accident
                if abs(timestamp - self.accident_timestamp) <= 2.0:
                    print(f"timestamp - self.accident_timestamp) in process_speed is {timestamp - self.accident_timestamp}")
                    print(f"speed_drop in procees_speed is {speed_drop}")
                    print(f"self.current_speed_accident * 0.2 in process_speed is {current_speed * 0.2}")
                    if abs(speed_drop) >= SPEED_DROP_THRESHOLD:
                    # if abs(speed_drop) >= max(self.last_speed * 0.2, SPEED_DROP_THRESHOLD):
                    # if abs(speed_drop) >= (self.last_speed * 0.1):
                        self.speed_drop_confirmed = True
                        return "ACCIDENT"
                else:
                    # Reset if no speed drop confirmed within time window
                    self.potential_accident = False
                    self.accident_timestamp = None
            
            self.last_speed = current_speed
            self.last_speed_time = timestamp
            return "NORMAL"

    def reset(self):
        """Reset detector state"""
        with self.lock:
            self.acc_window.clear()
            self.acc_timestamp.clear()
            self.potential_accident = False
            self.accident_timestamp = None
            self.speed_drop_confirmed = False

class CameraStream:
    def __init__(self, mqtt_client, record_handler, sensor_handler):
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 20)
        self.count = 0
        self.link_local_streaming = "http://127.0.0.1:5001"
        self.accident_signal = 0
        
        self.sensor_handler = sensor_handler
        self.gps_data = "Unknown"
        self.latitude = getattr(self.sensor_handler, 'latitude', 'N/A')
        self.longitude = getattr(self.sensor_handler, 'longitude', 'N/A')
        self.address_no_accent = getattr(self.sensor_handler, 'address_no_accent', 'N/A')
        # Buffer setup
        self.fps = 20
        self.buffer_size = self.fps * 20  # 20 seconds buffer
        self.frame_buffer = deque(maxlen=self.buffer_size)
        self.frame_buffer_jpg = None  # Initialize frame buffer for JPEG

        # Recording state
        self.recording_triggered = False
        self.recording_start_time = None
        
        # self.frame_buffer = None
        self.stream_active = True
        self.mqtt_client = mqtt_client
        self.record_handler = record_handler
        self.current_velocity = 0
        self.use_simulated_velocity = True
        
        self.last_accident_time = None
        self.accident_cooldown = 30  # 30 seconds cooldown between accident triggers

        # Base directory for saving images
        current_script_path = os.path.abspath(__file__)
        self.base_dir = os.path.dirname(os.path.dirname(current_script_path))
        
        # Construct the save directory path dynamically
        self.save_dir = os.path.join(self.base_dir, "iot", "firebase", "image", "customer_Phuc")
        self.thresold_speed = 40
        
        # Create directories if they don't exist
        os.makedirs(self.save_dir, exist_ok=True)
        
        print(f"Images will be saved to: {self.save_dir}")
        
        # Start threads for capturing video and simulating velocity
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        # Add recording queue
        self.recording_queue = deque()
        
        # Modified recording state variables
        self.recording_triggered = False
        self.recording_start_time = None
        self.post_trigger_duration = 20  # seconds after trigger
        
        self.recording_thread = threading.Thread(target=self._recording_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        # self.simulate_velocity_thread = threading.Thread(target=self._simulate_velocity)
        # self.simulate_velocity_thread.daemon = True
        # self.simulate_velocity_thread.start()
        
        self.accident_detector = AccidentDetector()
        self.fetch_accelerometer_accident_thread = threading.Thread(target=self.fetch_accelerometer_data)
        self.fetch_accelerometer_accident_thread.daemon = True
        self.fetch_accelerometer_accident_thread.start()
        
        self.fetch_gps_speed_thread = threading.Thread(target=self.fetch_gps_speed_data)
        self.fetch_gps_speed_thread.daemon = True
        self.fetch_gps_speed_thread.start()
        
        sms_send = 0
        
        self.keyboard_thread = threading.Thread(target=self._keyboard_control)
        self.keyboard_thread.daemon = True
        self.keyboard_thread.start()
        
        self.start_cloudflared_tunnel()
        
        # Add log file management settings
        self.log_buffer = []
        self.log_buffer_max_size = 10
        self.log_buffer_lock = threading.Lock()
        self.log_max_size_mb = 10  # 10MB maximum log file size
        self.log_dir = os.path.join(self.base_dir, "logs")
        self.accident_logs_dir = os.path.join(self.log_dir, "accident_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.accident_logs_dir, exist_ok=True)
        
        # Initialize main log file
        self.main_log_file = os.path.join(self.log_dir, "accelerometer_data.txt")
        
        atexit.register(self._cleanup)
        #Hoan change
        # Add new storage management variables
        self.storage_limit_mb = 500  # 500MB limit
        self.continuous_recording = True
        self.continuous_video_files = deque()
        self.current_video_writer = None
        self.video_duration = 300  # 5 minutes per file
        self.video_start_time = time.time()
        
        # Create directory for continuous recording
        self.continuous_record_dir = os.path.join(self.base_dir, "continuous_recording")
        os.makedirs(self.continuous_record_dir, exist_ok=True)
        
        # Start continuous recording thread
        self.continuous_record_thread = threading.Thread(target=self._continuous_recording_loop)
        self.continuous_record_thread.daemon = True
        self.continuous_record_thread.start()
        #Hoan changed all innit
    
    #Hoan change function from now 
    
    def _continuous_recording_loop(self):
        """Handle continuous recording with storage management"""
        while self.stream_active:
            current_time = time.time()
            
            # Start new video file if needed
            if self.current_video_writer is None or (current_time - self.video_start_time) >= self.video_duration:
                if self.current_video_writer is not None:
                    self.current_video_writer.release()
                
                # Create new video file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                video_path = os.path.join(self.continuous_record_dir, f'continuous_{timestamp}.avi')
                self.current_video_writer = cv2.VideoWriter(
                    video_path,
                    cv2.VideoWriter_fourcc(*'MJPG'),
                    self.fps,
                    (640, 480)
                )
                self.continuous_video_files.append(video_path)
                self.video_start_time = current_time
                
                # Check and manage storage limit
                self._manage_storage()
            
            # Write frame if available
            with frame_lock:
                if self.frame_buffer:
                    self.current_video_writer.write(self.frame_buffer[-1])
            
            time.sleep(1/self.fps)

    def _manage_storage(self):
        """Manage storage to keep under the limit"""
        total_size = 0
        files_to_keep = []
        
        # Calculate total size and identify files to keep
        for video_file in reversed(self.continuous_video_files):
            if os.path.exists(video_file):
                file_size = os.path.getsize(video_file) / (1024 * 1024)  # Convert to MB
                if total_size + file_size <= self.storage_limit_mb:
                    total_size += file_size
                    files_to_keep.append(video_file)
                else:
                    try:
                        os.remove(video_file)
                        print(f"Removed old video file: {video_file}")
                    except Exception as e:
                        print(f"Error removing file {video_file}: {str(e)}")
        
        # Update the list of video files
        self.continuous_video_files = deque(reversed(files_to_keep))
    #end 2 function Hoan changed
    
    def _simulate_velocity(self):
        """Simulates velocity changes over time"""
        while self.stream_active and self.use_simulated_velocity:
            # Generate random velocity between 0 and 100
            simulated_velocity = random.uniform(50, 100)
            self.update_velocity(simulated_velocity)
            print(f"Simulated velocity: {simulated_velocity:.2f}")
            time.sleep(2.5)

    def update_velocity(self, velocity):
        """Update current velocity and trigger image capture if needed"""
        self.current_velocity = velocity
        print(f"Current velocity simulate is {velocity}")
        if self.current_velocity > self.thresold_speed:
            self.capture_and_save_image()
            
        payload = self.mqtt_client.create_payload_simulate_velocity(self.current_velocity)
        ret = self.mqtt_client.publish(payload)
        if ret.rc == paho.MQTT_ERR_SUCCESS:
            print("Velocity simulate published successfully")
        else:
            print(f"Failed to publish velocity simulate, error code: {ret.rc}")
        
    def start_recording(self):
        """Trigger the recording process in RecordHandler."""
        if not self.record_handler.is_recording():
            # Start recording when exceeds threshold
            print("Accident was detected, starting recording...")
            self.record_handler.start_recording(self.get_frame())

    def stop_recording(self):
        """Stop recording process."""
        self.record_handler.stop_recording()
    
    def capture_and_save_image(self):
        """Capture and save image when velocity threshold is exceeded, then upload."""
        try:
            with frame_lock:
                if self.frame_buffer:
                    # Get the latest frame and overlay details
                    frame = self.frame_buffer[-1].copy()
                    
                    # Add overlay information
                    frame = self.add_timestamp_to_frame(frame)
                    
                    # Generate filename with timestamp and current velocity
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'image_{timestamp}_speed_{self.current_velocity:.1f}.jpg'
                    filepath = os.path.join(self.save_dir, filename)
                    
                    # Save image with overlay
                    cv2.imwrite(filepath, frame)
                    print(f"Captured image: {filepath} with speed: {self.current_velocity:.1f} km/h")
                    
                    # Call the upload function
                    try:
                        # upload_images_and_generate_html()
                        print("Successfully uploaded to Firebase")
                        # print("Do nothing upload image")
                    except Exception as e:
                        print(f"Error uploading to Firebase: {str(e)}")
        except Exception as e:
            print(f"Error capturing image: {str(e)}")

    def _capture_loop(self):
        """Capture frames and manage the pre-trigger buffer."""
        while self.stream_active:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # Add timestamp to frame
                    frame_with_timestamp = self.add_timestamp_to_frame(frame)
                    
                    # Store frame in the pre-trigger circular buffer
                    self.frame_buffer.append(frame_with_timestamp.copy())
                    
                    # Update JPEG buffer for live streaming
                    with frame_lock:
                        _, buffer = cv2.imencode('.jpg', frame_with_timestamp)
                        self.frame_buffer_jpg = buffer.tobytes()
                    
                    # If recording is triggered, add frame to the recording queue
                    if self.recording_triggered:
                        self.recording_queue.append(frame_with_timestamp)
            time.sleep(1/self.fps)
            
    def _recording_loop(self):
        """Handle recording logic including pre-trigger and post-trigger frames."""
        while self.stream_active:
            if self.recording_triggered and not self.record_handler.is_recording():
                print("Starting recording with pre-trigger buffer...")
                self.recording_start_time = time.time()

                # Calculate required frames for pre-trigger
                pre_trigger_frames = list(self.frame_buffer)
                required_frames = int(self.fps * 20)  # 20 seconds * fps
                
                print(f"Pre-trigger frames available: {len(pre_trigger_frames)}")
                print(f"Required frames for 20s: {required_frames}")
                
                # Ensure we have exactly 20 seconds of pre-trigger frames
                if len(pre_trigger_frames) >= required_frames:
                    pre_trigger_frames = pre_trigger_frames[-required_frames:]
                
                # Start recording
                if pre_trigger_frames:
                    self.record_handler.start_recording(pre_trigger_frames[0])
                    for frame in pre_trigger_frames:
                        self.record_handler.add_frame_to_record(frame)
                    print(f"Added {len(pre_trigger_frames)} pre-trigger frames")

                # Calculate post-trigger end time
                post_trigger_end_time = self.recording_start_time + 40.0  # 40 seconds total duration

                # Process post-trigger frames
                frames_added = len(pre_trigger_frames)
                total_frames_needed = int(self.fps * 40)  # 40 seconds total

                while frames_added < total_frames_needed and time.time() < post_trigger_end_time:
                    if self.recording_queue:
                        frame = self.recording_queue.popleft()
                        self.record_handler.add_frame_to_record(frame)
                        frames_added += 1
                    else:
                        time.sleep(1/self.fps)

                print(f"Total frames recorded: {frames_added}")
                print("Stopping recording - 40s total duration reached")
                self.recording_triggered = False
                self.recording_start_time = None
                self.record_handler.stop_recording()
                self.recording_queue.clear()

            time.sleep(0.01)

    def add_timestamp_to_frame(self, frame):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        h, w = frame.shape[:2]
        
        # Colors and fonts - kept consistent with your original
        TEXT_COLOR = (255, 255, 255)  # White
        HIGHLIGHT_COLOR = (0, 255, 255)  # Yellow
        WARNING_COLOR = (0, 0, 255)  # Red
        FONT = cv2.FONT_HERSHEY_SIMPLEX
        
        # Professional font scales
        HEADER_SCALE = 0.7
        SPEED_SCALE = 1.2
        NORMAL_SCALE = 0.6
        SMALL_SCALE = 0.5
        THICKNESS = 2

        # Semi-transparent overlay for better readability
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)  # Top bar
        cv2.rectangle(overlay, (0, h - 110), (w, h), (0, 0, 0), -1)  # Bottom bar
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Top bar content
        cv2.putText(frame, "DASHCAM PRO", (20, 28), 
                    FONT, HEADER_SCALE, HIGHLIGHT_COLOR, THICKNESS)
        
        timestamp_size = cv2.getTextSize(current_time, FONT, NORMAL_SCALE, THICKNESS)[0]
        cv2.putText(frame, current_time, (w - timestamp_size[0] - 20, 28), 
                    FONT, NORMAL_SCALE, TEXT_COLOR, THICKNESS)

        # Speed display (large, centered)
        speed_text = f'{self.sensor_handler.velocity:.0f}'
        # print(f"speed_text show in camera is {speed_text}")
        speed_color = WARNING_COLOR if self.current_velocity > self.thresold_speed else TEXT_COLOR
        
        speed_size = cv2.getTextSize(speed_text, FONT, SPEED_SCALE, THICKNESS)[0]
        speed_x = 30
        cv2.putText(frame, speed_text, (speed_x, h - 50), 
                    FONT, SPEED_SCALE, speed_color, THICKNESS)
        
        # Speed unit
        cv2.putText(frame, "km/h", (speed_x + 5, h - 25), 
                    FONT, SMALL_SCALE, speed_color, THICKNESS)

        # Address display (right-aligned, two lines)
        if hasattr(self, 'address_no_accent') and self.address_no_accent:
            addr_parts = self.address_no_accent.split(', ')
            
            # First line: Street number and name
            line1 = ', '.join(addr_parts[:2])
            line1_size = cv2.getTextSize(line1, FONT, NORMAL_SCALE, THICKNESS)[0]
            max_width = w - 200  # Leave space for speed
            
            if line1_size[0] > max_width:
                char_width = line1_size[0] / len(line1)
                max_chars = int(max_width / char_width)
                line1 = line1[:max_chars-3] + "..."
            
            cv2.putText(frame, line1, (200, h - 60), 
                        FONT, NORMAL_SCALE, TEXT_COLOR, THICKNESS)
            
            # Second line: District and City
            line2 = ', '.join(addr_parts[2:])
            line2_size = cv2.getTextSize(line2, FONT, NORMAL_SCALE, THICKNESS)[0]
            
            if line2_size[0] > max_width:
                char_width = line2_size[0] / len(line2)
                max_chars = int(max_width / char_width)
                line2 = line2[:max_chars-3] + "..."
                
            cv2.putText(frame, line2, (200, h - 30), 
                        FONT, NORMAL_SCALE, TEXT_COLOR, THICKNESS)

        # Speed warning (centered at top)
        if self.current_velocity > self.thresold_speed:
            warning_text = "! SPEED WARNING !"
            warning_size = cv2.getTextSize(warning_text, FONT, HEADER_SCALE, THICKNESS)[0]
            warning_x = (w - warning_size[0]) // 2
            
            # Warning background
            cv2.rectangle(frame, 
                        (warning_x - 10, 45),
                        (warning_x + warning_size[0] + 10, 75),
                        WARNING_COLOR, -1)
            
            cv2.putText(frame, warning_text, (warning_x, 67),
                        FONT, HEADER_SCALE, TEXT_COLOR, THICKNESS)

        return frame
            
    def send_alert_email(self):
        """Prepare email content and return the message object"""
        msg = EmailMessage()
        print("======CALLING EMAIL ALERT======")
        
        self.system_id = self.mqtt_client.license_plates
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="padding: 20px; background-color: #f8f8f8;">
                <div style="background-color: #ff0000; color: white; padding: 10px; text-align: center;">
                    <h2 style="margin: 0;">⚠️ CRITICAL ALERT: ACCIDENT DETECTED ⚠️</h2>
                </div>
                
                <div style="background-color: white; padding: 20px; margin-top: 20px;">
                    <h3>Emergency Response Required</h3>
                    <p><strong>Incident Details:</strong></p>
                    <ul>
                        <li>Time of Detection: {self.get_current_time()}</li>
                        <li>License Plates: {self.system_id}</li>
                        <li>Location: Latitude: {self.latitude}, Longitude: {self.longitude}</li>
                        <li>{self.address_no_accent}</li>
                        <li>Alert Level: HIGH PRIORITY</li>
                    </ul>
                    
                    <p style="color: #ff0000;"><strong>Immediate action required.</strong></p>
                    
                    <div style="background-color: #f0f0f0; padding: 10px; margin-top: 20px;">
                        <p style="margin: 0;"><small>This is an automated emergency alert. 
                        Please do not reply to this email. If this is an emergency, 
                        please contact emergency services immediately.</small></p>
                    </div>
                </div>
                
                <div style="margin-top: 20px; font-size: 12px; color: #666;">
                    <p>Confidential: This message contains sensitive information and is intended 
                    for authorized personnel only.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_text = f"""
        CRITICAL ALERT: ACCIDENT DETECTED
        Emergency Response Required
        
        Time of Detection: {self.get_current_time()}
        License Plates: {self.system_id}
        Location: Latitude: {self.latitude}, Longitude: {self.longitude}
        {self.address_no_accent}
        Alert Level: HIGH PRIORITY
        
        IMMEDIATE ACTION REQUIRED
        
        This is an automated emergency alert. Please do not reply to this email.
        If this is an emergency, please contact emergency services immediately.
        """

        msg.set_content(plain_text)
        msg.add_alternative(html_content, subtype='html')
        
        msg['Subject'] = '🚨 CRITICAL ALERT: Accident Detected - Immediate Response Required'
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Priority'] = 'urgent'
        
        return msg
    
    def send_sms_alert(self):
        """Send SMS alert about accident"""
        try:
            # Your Twilio credentials
            print("======CALLING SMS ALERT======")
            account_sid = ACCOUNT_SID
            auth_token = AUTH_TOKEN
            client = Client(account_sid, auth_token)

            message = client.messages.create(
                body=f"\n‼️ URGENT ALERT ‼️\n➜ Accident reported!\n📍 Plates: {self.mqtt_client.license_plates}\n⚠️ Please check status immediately",
                from_='+12183949340',  
                to='+84377300827'   
            )

            print(f"SMS alert sent successfully. SID: {message.sid}")
            
        except Exception as e:
            print(f"Error sending SMS alert: {e}")

    def send_email_thread(self, msg):
        """Actually send the email in a separate thread"""
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
                print("[ALERT] Emergency notification email sent successfully")
                
        except Exception as e:
            print(f"[ERROR] Failed to send emergency alert email: {str(e)}")

    def get_current_time(self):
        """Get formatted current time."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def trigger_recording(self):
        """Trigger recording with buffer"""
        if not self.recording_triggered:
            self.recording_triggered = True
            print("Recording triggered with buffer...")

    def fetch_accelerometer_data(self):
        # Determine the file path relative to the script location
        # script_dir = os.path.dirname(os.path.abspath(__file__))
        # log_file_path = os.path.join(script_dir, "accelerometer_data.txt")
        while self.stream_active:
            try:
                # Get the current timestamp
                timestamp = time.time()
                readable_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                # Get acceleration data
                self.acclerometer_detect = self.sensor_handler.acc_detect_accident
                # print(f"acclerometer_detect from camera_gstreamer.py is {self.acclerometer_detect}")
                # Process acceleration data through the accident detector
                
                self.status = self.accident_detector.process_acceleration(self.acclerometer_detect, timestamp)
        
                # Create log entry
                log_line = (
                    f"{readable_time}: "
                    f"Acceleration={self.acclerometer_detect:.2f}m/s^2, "
                    f"Velocity={self.current_velocity:.1f}km/h, "
                    f"Status={self.status}\n"
                )
                
                if self.status == "POTENTIAL_ACCIDENT":
                    # Check if we can trigger a new accident detection
                    if (self.last_accident_time is None or 
                        timestamp - self.last_accident_time >= self.accident_cooldown):
                        # Set the timestamp BEFORE handling the accident
                        self.last_accident_time = timestamp
                    
                        print(f"\n=== ACCIDENT DETECTED ===")
                        print(f"Time: {readable_time}")
                        print(f"Impact: {self.acclerometer_detect:.2f}g")
                        
                        self._save_accident_data(timestamp)
                        self.handle_accident()  

                        # Reset potential_accident flag after cooldown
                        def reset_potential_accident(): #just add here
                            with self.accident_detector.lock: #just add here
                                self.accident_detector.potential_accident = False #just add here
                        threading.Timer(self.accident_cooldown, reset_potential_accident).start() #just add here
                    
                # Write to log file with size management      
                self._write_to_log(log_line) 
                  
            except Exception as e:
                # Log errors to the file as well
                print(f"Error in accelerometer monitoring: {e}")
                    
            threading.Event().wait(0.1)  # Short delay (~66Hz loop)
            
    def _write_to_log(self, log_line):
        """Write to log file with buffering and size management"""
        try:
            with self.log_buffer_lock:
                self.log_buffer.append(log_line)
                
                # Only write when buffer is full
                if len(self.log_buffer) >= self.log_buffer_max_size:
                    current_size = 0
                    if os.path.exists(self.main_log_file):
                        current_size = os.path.getsize(self.main_log_file) / (1024 * 1024)
                    
                    if current_size >= self.log_max_size_mb:
                        with open(self.main_log_file, 'r') as file:
                            lines = file.readlines()
                        lines = lines[-int(len(lines) * 0.8):]
                        with open(self.main_log_file, 'w') as file:
                            file.writelines(lines)
                    
                    # Write buffered lines
                    with open(self.main_log_file, 'a') as file:
                        file.writelines(self.log_buffer)
                    self.log_buffer.clear()
                    
        except Exception as e:
            print(f"Error writing to log: {e}")

    def _save_accident_data(self, accident_time):
        """Save accident data including before and after the incident"""
        try:
            # Create accident log filename
            timestamp = datetime.fromtimestamp(accident_time).strftime('%Y%m%d_%H%M%S')
            accident_file = os.path.join(
                self.accident_logs_dir, 
                f"accident_log_{timestamp}.txt"
            )
            
            # Copy current log content (pre-accident data)
            if os.path.exists(self.main_log_file):
                with open(self.main_log_file, 'r') as source:
                    pre_accident_data = source.readlines()
            
            # Start thread to collect post-accident data
            thread = threading.Thread(
                target=self._collect_post_accident_data,
                args=(accident_file, pre_accident_data, accident_time),
                daemon=True
            )
            thread.start()
            
        except Exception as e:
            print(f"Error saving accident data: {e}")

    def _collect_post_accident_data(self, accident_file, pre_accident_data, accident_time):
        try:
            with open(accident_file, 'w') as file:
                file.writelines(pre_accident_data)
            
            collection_start = time.time()
            end_time = accident_time + 20
            timeout = 25  # Maximum wait time
            
            while time.time() < min(end_time, collection_start + timeout):
                time.sleep(0.1)
                
                try:
                    with open(self.main_log_file, 'r') as main_file:
                        current_data = main_file.readlines()
                    
                    if len(current_data) > len(pre_accident_data):
                        new_lines = current_data[len(pre_accident_data):]
                        with open(accident_file, 'a') as file:
                            file.writelines(new_lines)
                        pre_accident_data = current_data
                except Exception as e:
                    print(f"Error reading log during collection: {e}")
                    time.sleep(0.5)
            
            print(f"Accident log saved: {accident_file}")
            
        except Exception as e:
            print(f"Error collecting post-accident data: {e}")
        
    def fetch_gps_speed_data(self):
        while self.stream_active:
            try:
                # with threading.Lock():
                self.latitude = self.sensor_handler.latitude
                self.longitude = self.sensor_handler.longitude
                self.address_no_accent = self.sensor_handler.address_no_accent
                print(f"address_no_accent in camera_gstreamer.py is {self.address_no_accent}")
                
                current_speed_accident = self.sensor_handler.velocity
                print(f"Velocity checking accident is {current_speed_accident}")
                timestamp = time.time()
                
                # Update current velocity
                self.current_velocity = self.sensor_handler.velocity
                print(f"self.current_velocity at camera_gstreamer is {self.current_velocity}")
                if self.current_velocity > self.thresold_speed:
                    self.capture_and_save_image()
                
                # Process speed through accident detector
                self.status = self.accident_detector.process_speed(current_speed_accident, timestamp)
                
                if self.status == "ACCIDENT":
                    print("Accident confirmed! Triggering emergency response...")
                    self.handle_accident()
            except Exception as e:
                print(f"Error fetching gps & speed data: {e}")  
                
            threading.Event().wait(1)
    
    def handle_accident(self):
        """Handle confirmed accident detection"""
        try:
            # Trigger recording
            self.trigger_recording()
            
            
            # sms_thread = threading.Thread(
            # target=self.send_sms_alert,
            # daemon=True
            # )
            # sms_thread.start()
            # sms_thread.join(timeout=10)  # Wait up to 10 seconds for SMS to be sent
            
            # Send email alert
            msg = self.send_alert_email()
            email_thread = threading.Thread(
                target=self.send_email_thread,
                args=(msg,),
                daemon=True
            )
            email_thread.start()
            
            # Send MQTT alert
            self.accident_signal = 1
            payload = self.mqtt_client.create_payload_accident_signal(self.accident_signal)
            ret = self.mqtt_client.publish(payload)
            
            if ret.rc == paho.MQTT_ERR_SUCCESS:
                print(f"Accident signal is {self.accident_signal} published successfully")
                # Reset accident signal after short delay
                threading.Timer(10.0, self.reset_accident_signal).start()
            else:
                print(f"Failed to publish accident signal, error code: {ret.rc}")
            
            # Reset the potential_accident flag after handling
            # self.potential_accident = False #just add here
                
        except Exception as e:
            print(f"Error handling accident: {e}")

    def reset_accident_signal(self):
        """Reset accident signal after alert"""
        self.accident_signal = 0
        payload = self.mqtt_client.create_payload_accident_signal(self.accident_signal)
        self.mqtt_client.publish(payload)
        print("Accident signal reset")
                        
    def _keyboard_control(self):
        """Handle keyboard controls in the terminal, it simulate the accident, if 'q' is pressed, accident signal will be sent."""
        while self.stream_active:
            # Use input() to listen for key presses in terminal
            key = input("Press 'q' to trigger recording (press 'exit' to quit): ").strip().lower()
            if key == 'q':
                print("Keyboard 'q' pressed")
                # self.trigger_recording()
                self.handle_accident()
                
            elif key == 'exit':
                print("Exiting keyboard control")
                self.stream_active = False
                break
    
    def get_frame(self):
        with frame_lock:
            return self.frame_buffer_jpg

    def stop(self):
        self.stream_active = False
        if hasattr(self, 'thread'):
            self.thread.join()
        if self.cap:
            self.cap.release()

    def start_cloudflared_tunnel(self):
        """Starts cloudflared tunnel with additional parameters and retrieves the URL for ThingsBoard."""
        def run_tunnel():
            print("Calling command cloudflare...", flush=True)
            process = subprocess.Popen(
                [
                    "cloudflared", "tunnel", "--url", "http://localhost:5000",
                    "--http2-origin", "--no-chunked-encoding",
                    "--proxy-keepalive-timeout", "120s", "--proxy-connection-timeout", "120s"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                universal_newlines=True,
                bufsize=1
            )
            print("Done call command cloudflare!", flush=True)
            
            try:
                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    print(line, flush=True)  # Print each line of output

                    # Check for the line with the URL
                    if "https://" in line:
                        url_match = re.search(r"https://[\w-]+\.trycloudflare\.com", line)
                        if url_match:
                            tunnel_url = url_match.group(0)
                            print(f"Tunnel URL: {tunnel_url}")
                            # Push Serveo URL to MQTT
                            if self.count == 0:
                                payload = self.mqtt_client.create_payload_URL_camera(tunnel_url, self.link_local_streaming)
                                ret = self.mqtt_client.publish(payload)
                                if ret.rc == paho.MQTT_ERR_SUCCESS:
                                    print("URL published successfully")
                                    self.count = 1
                                else:
                                    print(f"Failed to publish URL, error code: {ret.rc}")
            except Exception as e:
                print(f"Error reading output: {e}", flush=True)
            finally:
                process.stdout.close()
                process.wait()

        tunnel_thread = threading.Thread(target=run_tunnel)
        tunnel_thread.daemon = True
        tunnel_thread.start()

    def run_server(self):
        """Method to run the Flask server"""
        global server_running
        if not server_running:
            server_running = True
            app.run(host="0.0.0.0", port=5000, threaded=True)
            
    def _cleanup(self):
        """Clean up resources on program exit"""
        try:
            # Flush remaining log buffer
            with self.log_buffer_lock:
                if self.log_buffer:
                    with open(self.main_log_file, 'a') as file:
                        file.writelines(self.log_buffer)
            
            # Stop all threads
            self.stream_active = False
            
            # Release camera
            if self.cap is not None:
                self.cap.release()
                
            # Close video writer
            if self.current_video_writer is not None:
                self.current_video_writer.release()
                
        except Exception as e:
            print(f"Error during cleanup: {e}")

def initialize_camera(mqtt_client, record_handler, sensor_handler):
    global camera
    if camera is not None:
        camera.stop()
    camera = CameraStream(mqtt_client, record_handler, sensor_handler)
    return camera

def generate_frames():
    viewer_id = threading.get_ident()
    active_viewers.add(viewer_id)
    
    try:
        while True:
            if not camera or not camera.stream_active:
                break
            try:
                frame = camera.get_frame()
                if frame is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1/30)
            except Exception as e:
                print(f"Error generating frame: {e}")
                break
    finally:
        active_viewers.discard(viewer_id)

@app.route('/')
def index():
    return render_template('index_gstreamer.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/restart_stream', methods=['POST'])
def restart_stream():
    """Handle stream restart request."""
    global camera  # Use the global camera object defined in camera_gstreamer.py

    if camera:
        camera.stop()  # Stop the current stream
        camera = initialize_camera(camera.mqtt_client, camera.record_handler, camera.sensor_handler)  # Re-initialize with same clients
        return jsonify({"status": "Stream restarted"}), 200
    return jsonify({"error": "No active video stream"}), 500

@app.route('/get_viewer_count')
def get_viewer_count():
    return jsonify({"count": len(active_viewers)})

def cleanup():
    global camera
    if camera:
        camera.stop()

def signal_handler(signum, frame):
    cleanup()
    os._exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    try:
        mqtt_client = MQTTClient()
        camera = initialize_camera(mqtt_client, record_handler)
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        cleanup()