import cv2
import time
from datetime import datetime
import os

class RecordHandler:
    def __init__(self, output_dir="/home/pi/Thesis/handle", fps=20):
        self.output_dir = output_dir
        self.fps = fps
        self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.writer = None
        self.recording = False
        os.makedirs(output_dir, exist_ok=True)

    def start_recording(self, frame):
        if not self.recording:
            h, w = frame.shape[:2]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f'output_{timestamp}.avi')
            self.writer = cv2.VideoWriter(output_path, self.fourcc, self.fps, (w, h))
            print("HEHEHEHE")
            self.recording = True
            print(f"Started recording to {output_path}")

    def add_frame_to_record(self, frame):
        if self.recording and self.writer:
            self.writer.write(frame)

    def stop_recording(self):
        if self.recording and self.writer:
            self.writer.release()
            self.writer = None
            self.recording = False
            print("Recording stopped")

    def is_recording(self):
        return self.recording
