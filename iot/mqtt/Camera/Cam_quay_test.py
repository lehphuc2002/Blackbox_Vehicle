import cv2
import numpy as np

# Create a blank image (black)
frame = np.zeros((480, 640, 3), dtype=np.uint8)  # 480p resolution

# Set up video writer
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Try different codecs if needed
out = cv2.VideoWriter('test_output.avi', fourcc, 30.0, (640, 480))

# Write 100 frames
for _ in range(100):
    out.write(frame)

out.release()
print("Video saved.")
