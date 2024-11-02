import os
import cv2
from flask import Flask, render_template, request, jsonify
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import asyncio
from test_camera_webRTC import VideoCamera
from av import VideoFrame
import threading
import queue

app = Flask(__name__)
camera = VideoCamera()  # Initialize camera once

# Queue to hold frames
frame_queue = queue.Queue(maxsize=10)  # Limit the queue size to prevent memory issues

def capture_frames():
    while True:
        frame = camera.get_frame()
        if frame is not None:
            if not frame_queue.full():
                frame_queue.put(frame)

# Start the frame capture thread
threading.Thread(target=capture_frames, daemon=True).start()

class CameraVideoTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        
    async def recv(self):
        if not frame_queue.empty():
            frame = frame_queue.get()
            # Convert the frame from JPEG to a format suitable for WebRTC
            frame_rgb = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            if frame_rgb is None:
                raise Exception("No frame captured")
            
            av_frame = VideoFrame.from_ndarray(frame_rgb, format="bgr24")
            av_frame.pts = None  # Set PTS based on your frame rate
            av_frame.time_base = None
            
            return av_frame
        else:
            # If no frame is available, return None
            return None

@app.route('/')
def index():
    return render_template('index_camera.html')

@app.route('/offer', methods=['POST'])
async def offer():
    params = request.get_json()
    if not params or "sdp" not in params or "type" not in params:
        return jsonify({"error": "Invalid SDP"}), 400

    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    video_track = CameraVideoTrack()
    pc.addTrack(video_track)

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        if pc.iceConnectionState in ["closed", "failed"]:
            await pc.close()

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return jsonify({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
