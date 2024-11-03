import cv2
from flask import Flask, Response, render_template, jsonify
import os
import signal
import threading
import time
import subprocess
import re
import paho.mqtt.client as paho
from iot.mqtt.publish import MQTTClient  # Assuming MQTTClient is properly defined

# Initialize Flask app
app = Flask(__name__)

# Global variables
frame_lock = threading.Lock()
camera = None
active_viewers = set()
server_running = False

class CameraStream:
    def __init__(self, mqtt_client):
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 20)
        self.frame_buffer = None
        self.stream_active = True
        self.mqtt_client = mqtt_client
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
        self.start_cloudflared_tunnel()

    def _capture_loop(self):
        while self.stream_active:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with frame_lock:
                        _, buffer = cv2.imencode('.jpg', frame)
                        self.frame_buffer = buffer.tobytes()
            time.sleep(1/30)  # Limit to ~30 FPS

    def get_frame(self):
        with frame_lock:
            return self.frame_buffer

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

def initialize_camera(mqtt_client):
    global camera
    if camera is not None:
        camera.stop()
    camera = CameraStream(mqtt_client)
    return camera

def generate_frames():
    viewer_id = threading.get_ident()
    active_viewers.add(viewer_id)
    
    try:
        while True:
            if not camera or not camera.stream_active:
                break
            frame = camera.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1/30)  # Limit frame rate
    finally:
        active_viewers.discard(viewer_id)

@app.route('/')
def index():
    return render_template('index_gstreamer.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

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
        camera = initialize_camera(mqtt_client)
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        cleanup()