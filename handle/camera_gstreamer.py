# Thesis/handle/camera_gstreamer.py
import cv2
from flask import Flask, Response, render_template, jsonify
import os
import signal
import threading
import time
import subprocess
import re
from iot.mqtt.publish import FirebaseClient
from datetime import datetime
from collections import deque
import numpy as np
import random
from handle.record_handle import RecordHandler
import smtplib
from email.message import EmailMessage
# from handle.email_config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL
from handle.sensors_handle import SensorHandler  # Import your SensorHandler class



# Initialize Flask app
app = Flask(__name__)

# Global variables
frame_lock = threading.Lock()
camera = None
active_viewers = set()
server_running = False

class CameraStream:
    def __init__(self, firebaseclient, record_handler, sensor_handler):
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 20)
        self.count = 0
        self.link_local_streaming = "http://127.0.0.1:5001"
        self.accident_signal = 0
        
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
        self.firebaseclient = firebaseclient
        self.record_handler = record_handler
        self.current_velocity = 0
        self.use_simulated_velocity = True

        self.record_handler = record_handler

        # Base directory for saving images
        current_script_path = os.path.abspath(__file__)
        self.base_dir = os.path.dirname(os.path.dirname(current_script_path))
        
        # Construct the save directory path dynamically
        self.save_dir = os.path.join(self.base_dir, "iot", "firebase", "image", "customer_Phuc")
        
        # Create directories if they don't exist
        os.makedirs(self.save_dir, exist_ok=True)
        
        print(f"Images will be saved to: {self.save_dir}")  # Debug print
        
        # Start threads for capturing video and simulating velocity
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
        
        # Add recording queue
        self.recording_queue = deque()
        
        # Modified recording state variables
        self.recording_triggered = False
        self.recording_start_time = None
        self.post_trigger_duration = 20  # seconds after trigger
        
        self.thread = threading.Thread(target=self._recording_loop)
        self.thread.daemon = True
        self.thread.start()
        
        # self.simulate_velocity_thread = threading.Thread(target=self._simulate_velocity)
        # self.simulate_velocity_thread.daemon = True
        # self.simulate_velocity_thread.start()
        
        self.keyboard_thread = threading.Thread(target=self._keyboard_control)
        self.keyboard_thread.daemon = True
        self.keyboard_thread.start()
        
        self.sensor_handler = sensor_handler
        self.gps_data = "Unknown"
        
        self.start_cloudflared_tunnel()

    def _simulate_velocity(self):
        """Simulates velocity changes over time"""
        while self.stream_active and self.use_simulated_velocity:
            # Generate random velocity between 0 and 100
            simulated_velocity = random.uniform(0, 100)
            self.update_velocity(simulated_velocity)
            print(f"Simulated velocity: {simulated_velocity:.2f}")
            time.sleep(6)

    def update_velocity(self, velocity):
        """Update current velocity and trigger image capture if needed"""
        self.current_velocity = velocity
        print(f"Current velocity is {velocity}")
        if velocity > 50:
            self.capture_and_save_image()
            
    def start_recording(self):
        """Trigger the recording process in RecordHandler."""
        if not self.record_handler.is_recording():
            # Start recording when the velocity exceeds threshold
            print("Accident was detected, starting recording...")
            self.record_handler.start_recording(self.get_frame())

    def stop_recording(self):
        """Stop recording process."""
        self.record_handler.stop_recording()


    # def capture_and_save_image(self):
    #     """Capture and save image when velocity threshold is exceeded, then upload."""
    #     try:
    #         with frame_lock:
    #             if self.frame_buffer is not None:
    #                 # Convert frame buffer to image
    #                 nparr = np.frombuffer(self.frame_buffer, np.uint8)
    #                 frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
    #                 # Generate filename with timestamp and velocity
    #                 timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    #                 filename = f'image_{timestamp}_speed_{self.current_velocity:.1f}.jpg'
    #                 filepath = os.path.join(self.save_dir, filename)
                    
    #                 # Save image
    #                 cv2.imwrite(filepath, frame)
    #                 print(f"Captured image: {filepath}")
                    
    #                 # Call the upload function
    #                 try:
    #                     upload_images_and_generate_html()
    #                     print("Successfully uploaded to Firebase")
    #                 except Exception as e:
    #                     print(f"Error uploading to Firebase: {str(e)}")

    #     except Exception as e:
    #         print(f"Error capturing image: {str(e)}")
    
    def capture_and_save_image(self):
        """Capture and save image when velocity threshold is exceeded, then upload."""
        # try:
        #     with frame_lock:
        #         if self.frame_buffer:
        #             # Get the latest frame from the deque (buffer)
        #             frame = self.frame_buffer[-1]
                    
        #             # Generate filename with timestamp and velocity
        #             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        #             filename = f'image_{timestamp}_speed_{self.current_velocity:.1f}.jpg'
        #             filepath = os.path.join(self.save_dir, filename)
                    
        #             # Save image
        #             cv2.imwrite(filepath, frame)
        #             print(f"Captured image: {filepath}")
                    
        #             # Call the upload function
        #             try:
        #                 upload_images_and_generate_html()
        #                 print("Successfully uploaded to Firebase")
        #             except Exception as e:
        #                 print(f"Error uploading to Firebase: {str(e)}")

        # except Exception as e:
        #     print(f"Error capturing image: {str(e)}")

    # def _capture_loop(self):
    #     while self.stream_active:
    #         if self.cap.isOpened():
    #             ret, frame = self.cap.read()
    #             if ret:
    #                 with frame_lock:
    #                     _, buffer = cv2.imencode('.jpg', frame)
    #                     self.frame_buffer = buffer.tobytes()
                        
    #             # Add frame to the recorder if recording
    #                 if self.record_handler.is_recording():
    #                     self.record_handler.add_frame_to_record(frame)
                        
    #         time.sleep(1/30)
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

                # Write pre-trigger frames to the recording
                pre_trigger_frames = list(self.frame_buffer)  # Get all frames from buffer (20 seconds)
                if pre_trigger_frames:
                    self.record_handler.start_recording(pre_trigger_frames[0])  # Start with the first frame
                    for frame in pre_trigger_frames:
                        self.record_handler.add_frame_to_record(frame)

            # Write frames from the recording queue
            while self.recording_queue and self.record_handler.is_recording():
                frame = self.recording_queue.popleft()
                self.record_handler.add_frame_to_record(frame)
                
                # Add a delay to maintain FPS consistency
                time.sleep(1 / self.fps)  # Sleep to match frame rate

            # Check if post-trigger duration has elapsed
            if self.recording_triggered and self.recording_start_time:
                elapsed_time = time.time() - self.recording_start_time
                if elapsed_time >= 20.0:  # 20 seconds post-trigger
                    print("Stopping recording after post-trigger duration...")
                    self.recording_triggered = False
                    self.recording_start_time = None
                    self.record_handler.stop_recording()
                    self.recording_queue.clear()

            time.sleep(0.01)
        
    def add_timestamp_to_frame(self, frame):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        h, w = frame.shape[:2]
        
        # Define colors and fonts
        TEXT_COLOR = (255, 255, 255)  # White
        HIGHLIGHT_COLOR = (0, 255, 255)  # Yellow
        WARNING_COLOR = (0, 0, 255)  # Red
        FONT = cv2.FONT_HERSHEY_SIMPLEX
        
        # Create semi-transparent overlay for the entire bottom bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h-80), (w, h), (0, 0, 0), -1)
        alpha = 0.7
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # Add company/device name (top left)
        cv2.putText(frame, "DASHCAM PRO", (10, 30), 
                    FONT, 0.7, HIGHLIGHT_COLOR, 2)

        # Left side information
        # Time
        cv2.putText(frame, current_time, (20, h-50), 
                    FONT, 0.7, TEXT_COLOR, 1)
        
        # Speed with dynamic color based on velocity
        speed_color = WARNING_COLOR if self.current_velocity > 80 else TEXT_COLOR
        cv2.putText(frame, f'{self.current_velocity:.1f} km/h', (20, h-20), 
                    FONT, 0.7, speed_color, 1)

        # Center information
        # GPS coordinates (if available)
        gps_text = "GPS: 51.5074° N, 0.1278° W"  # Replace with actual GPS data
        text_size = cv2.getTextSize(gps_text, FONT, 0.6, 1)[0]
        text_x = (w - text_size[0]) // 2
        cv2.putText(frame, gps_text, (text_x, h-20), 
                    FONT, 0.6, TEXT_COLOR, 1)
        
        # Add subtle border lines
        cv2.line(frame, (0, h-82), (w, h-82), HIGHLIGHT_COLOR, 1)
        
        # Optional: Add event markers or warnings
        if self.current_velocity > 80:  # Example speed warning
            warning_text = "SPEED WARNING"
            text_size = cv2.getTextSize(warning_text, FONT, 0.7, 2)[0]
            text_x = (w - text_size[0]) // 2
            cv2.putText(frame, warning_text, (text_x, 60), 
                        FONT, 0.7, WARNING_COLOR, 2)

        return frame
        
    def send_alert_email(self):
        """Prepare email content and return the message object"""
        msg = EmailMessage()
        
        latitude = getattr(self.sensor_handler, 'latitude', 'N/A')
        longitude = getattr(self.sensor_handler, 'longitude', 'N/A')
        self.system_id = "Mercedes C300"
        
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
                        <li>System ID: {self.system_id}</li>
                        <li>Location: Latitude: {latitude}, Longitude: {longitude}</li>
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
        System ID: {self.system_id}
        Location: Latitude: {latitude}, Longitude: {longitude}
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

    def _keyboard_control(self):
        """Handle keyboard controls in the terminal."""
        while self.stream_active:
            # Use input() to listen for key presses in terminal
            key = input("Press 'q' to trigger recording (press 'exit' to quit): ").strip().lower()
            if key == 'q':
                print("Keyboard 'q' pressed")
                self.trigger_recording()
                
                # Prepare email message
                # msg = self.send_alert_email()
                # # Start email sending in a separate thread
                # email_thread = threading.Thread(
                #     target=self.send_email_thread,
                #     args=(msg,),
                #     daemon=True
                # )
                # email_thread.start()
                
                self.accident_signal = 1
                payload = self.firebaseclient.create_payload_accident_signal(self.accident_signal)
                self.firebaseclient.publish("Accident", payload)
                print(f"Accident signal published successfully. Its value is {self.accident_signal}")
                self.accident_signal = 0
                payload = self.firebaseclient.create_payload_accident_signal(self.accident_signal) # send 0 to turn off accident signal
                self.firebaseclient.publish("Accident", payload)
                print(f"Accident signal down published successfully. Its value is {self.accident_signal}")
                
            elif key == 'exit':
                print("Exiting keyboard control")
                self.stream_active = False
                break


    # def get_frame(self):
    #     with frame_lock:
    #         return self.frame_buffer
    
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
                            payload = {'Link streaming': tunnel_url}
                            self.firebaseclient.publish("Link streaming", payload)

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

def initialize_camera(firebaseclient, record_handler, sensor_handler):
    global camera
    if camera is not None:
        camera.stop()
    camera = CameraStream(firebaseclient, record_handler, sensor_handler)
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
        camera = initialize_camera(camera.firebaseclient, camera.record_handler)  # Re-initialize with same clients
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
        firebaseclient = FirebaseClient()
        camera = initialize_camera(firebaseclient, record_handler)
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        cleanup()
