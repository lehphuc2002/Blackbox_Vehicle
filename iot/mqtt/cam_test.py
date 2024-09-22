import cv2


cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("khong the mo cam")
    exit()

while True:
    #doc khung hinh camera
    ret, frame = cap.read()

    
    if not ret:
        print("khong the nhan khung hinh")
        break

    cv2.imshow("Camera", frame)


    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()
