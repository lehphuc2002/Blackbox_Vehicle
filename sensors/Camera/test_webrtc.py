import cv2
from flask import Flask, Response, render_template, jsonify
import os
import signal
import threading
import time

# Initialize Flask app
app = Flask(__name__)

# Global variables
camera_thread = None
stream_active = True
cap = None
active_viewers = set()
frame_buffer = None
frame_lock = threading.Lock()

class CameraStream:
    def __init__(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 20)
        self.frame_buffer = None
        self.stream_active = True
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()

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
        self.thread.join()
        if self.cap:
            self.cap.release()

# Global camera stream instance
camera = None

def initialize_camera():
    global camera
    if camera is not None:
        camera.stop()
    camera = CameraStream()
    return camera

# Initialize camera
camera = initialize_camera()

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

@app.route('/restart_stream', methods=['POST'])
def restart_stream():
    try:
        global camera
        # Initialize new camera
        camera = initialize_camera()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Clean up function
def cleanup():
    global camera
    if camera:
        camera.stop()

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    cleanup()
    os._exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Start the Flask app
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        cleanup()