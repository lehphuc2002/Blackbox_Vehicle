import cv2
import time
from collections import deque
from datetime import datetime

# Initialize camera
cap = cv2.VideoCapture(0)

# Set up buffer for 20 seconds before the signal (assuming 30fps)
fps = 30
buffer_size = fps * 20  # number of frames for 20 seconds
buffer = deque(maxlen=buffer_size)  # circular buffer to hold frames

# Set up video writer
#fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Video format
fourcc = cv2.VideoWriter_fourcc(*'MJPG')
#fourcc = cv2.VideoWriter_fourcc(*'X264')
out = None  # Initialize video writer object

signal_received = False  # Flag to detect when signal is triggered
start_time = None  # To track time after signal
now = datetime.now()
i = now.strftime("%Y%m%d_%H%M%S.h264")

while True:

	ret, frame = cap.read()  # Capture frame from camera
	if ret:
		h,w, _ = frame.shape
		current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  
		font = cv2.FONT_HERSHEY_SIMPLEX
		font_scale = 0.6
		thickness = 2
		color = (255, 255, 255) 
		line_type = cv2.LINE_4
		text = current_time
		text_x = 10
		text_y = h-10
		
		(text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

		overlay = frame.copy() 
		cv2.rectangle(overlay, (text_x - 10, text_y - text_h - 10), (text_x + text_w + 10, text_y + baseline + 10), (0, 0, 0), -1)

		alpha = 0.6 
		frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

		cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness, line_type)
		
	if not ret:
		break
    # Add the frame to the buffer (store the last 20 seconds)
	buffer.append(frame)

    # Display the current frame on the screen
	cv2.imshow('Camera', frame)
    # Assuming signal is triggered when 'q' key is pressed
	if cv2.waitKey(1) & 0xFF == ord('q'):
		if signal_received == False:
			signal_received = True  # Set :the flag that signal is received 		
			start_time = time.time()  # Record the current time when signal is triggered

			# Set up the video writer to save the video, with frame size from the camera
			frame_height, frame_width = frame.shape[:2]
			print("frame size:",frame_height, frame_width)   # Get frame dimensions
			out = cv2.VideoWriter(f'/home/pi/Thesis/handle/output{i}.avi', fourcc, fps, (frame_width, frame_height))
			now = datetime.now()
			i = now.strftime("%Y%m%d_%H%M%S.h264")
			# Write the buffered frames (20 seconds before the signal) to the video file
			for buffered_frame in buffer:
				out.write(buffered_frame)

    # After signal is received, continue recording for 20 seconds
	if signal_received:
		out.write(frame)  # Write the current frame to the video file
		if time.time() - start_time >= 25:  # Check if 20 seconds have passed
				# If 20 seconds after the signal have been recorded, stop
			
			signal_received = False
			#break

# Release resources
cap.release()  # Release the camera
out.release()  # Release the video writer
cv2.destroyAllWindows()  # Close all OpenCV windows