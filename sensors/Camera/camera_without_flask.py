import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Unable to open /dev/video0")
    exit()

ret, frame = cap.read()
if not ret:
    print("Unable to capture frame")
else:
    # Save the frame to disk
    cv2.imwrite("test_frame.jpg", frame)
    print("Frame saved as test_frame.jpg")

cap.release()
