import cv2

class VideoCamera(object):
    def __init__(self):
        # Open USB camera (device 0)
        self.video = cv2.VideoCapture(0)  # You may need to change this index based on your setup

        if not self.video.isOpened():
            print("Unable to open camera")
            exit(1)  # Exit with an error code

    def __del__(self):
        self.video.release()

    def get_frame(self):
        ret, frame = self.video.read()
        if not ret:
            print("Unable to capture frame")
            return None

        # Return the frame in BGR format
        return frame  # Return the raw frame for processing in WebRTC
