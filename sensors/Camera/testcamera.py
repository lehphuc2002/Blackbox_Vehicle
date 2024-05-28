import cv2

cap = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)

if not cap.isOpened():
    print("Cannot open camera")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Cannot receive frame (stream end?). Exiting ...")
        break
    cv2.imshow('Camera', frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
