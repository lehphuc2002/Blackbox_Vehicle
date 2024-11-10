import cv2
from flask import Flask, Response, render_template, jsonify
import os
import signal
import threading
import time
import subprocess
import re
import paho.mqtt.client as paho
from iot.mqtt.publish import MQTTClient
from datetime import datetime
from collections import deque
from datetime import datetime
import numpy as np
import random
from iot.firebase.push_image import upload_images_and_generate_html
from handle.record_handle import RecordHandler

# Initialize Flask app
app = Flask(__name__)

# Global variables
frame_lock = threading.Lock()
camera = None
active_viewers = set()
server_running = False

class CameraStream:
    def __init__(self, mqtt_client, record_handler):
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 20)
        
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
        
        self.simulate_velocity_thread = threading.Thread(target=self._simulate_velocity)
        self.simulate_velocity_thread.daemon = True
        self.simulate_velocity_thread.start()
        
        self.keyboard_thread = threading.Thread(target=self._keyboard_control)
        self.keyboard_thread.daemon = True
        self.keyboard_thread.start()
        
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
        while self.stream_active:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # Add timestamp to frame
                    frame_with_timestamp = self.add_timestamp_to_frame(frame)
                    
                    # Store frame in circular buffer
                    self.frame_buffer.append(frame_with_timestamp.copy())
                    
                    # Update JPEG buffer for streaming
                    with frame_lock:
                        _, buffer = cv2.imencode('.jpg', frame_with_timestamp)
                        self.frame_buffer_jpg = buffer.tobytes()
                    
                    # Handle recording if triggered
                    if self.recording_triggered:
                        if not self.record_handler.is_recording():
                            print("STARTING RECORDING...")
                            # Start new recording and write buffered frames
                            self.record_handler.start_recording(frame_with_timestamp)
                            for buffered_frame in list(self.frame_buffer)[-self.fps*10:]:
                                self.record_handler.add_frame_to_record(buffered_frame)
                            self.recording_start_time = time.time()
                        
                        # Add current frame to recording
                        self.record_handler.add_frame_to_record(frame_with_timestamp)
                        
                        # Check recording duration
                        if time.time() - self.recording_start_time >= 20:
                            self.recording_triggered = False
                            self.record_handler.stop_recording()
                            
            time.sleep(1/self.fps)
    
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
                            payload = self.mqtt_client.create_payload_URL_camera(tunnel_url)
                            ret = self.mqtt_client.publish(payload)
                            if ret.rc == paho.MQTT_ERR_SUCCESS:
                                print("URL published successfully")
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

def initialize_camera(mqtt_client, record_handler):
    global camera
    if camera is not None:
        camera.stop()
    camera = CameraStream(mqtt_client, record_handler)
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
        camera = initialize_camera(camera.mqtt_client, camera.record_handler)  # Re-initialize with same clients
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