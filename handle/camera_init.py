import cv2

class VideoCamera(object):
    def __init__(self):
        # Open USB camera (device 0)
        self.video = cv2.VideoCapture(0)
        # Set a lower resolution for the video feed
        # self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        # self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not self.video.isOpened():
            print("Unable to open camera")
            exit()

    def __del__(self):
        self.video.release()

    def get_frame(self):
        ret, frame = self.video.read()
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

        if not ret:
            print("Unable to capture frame")
            return None

        # Encode the frame to JPEG format
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()
