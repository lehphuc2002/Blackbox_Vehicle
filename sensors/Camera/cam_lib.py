import threading
import time
import os
from datetime import datetime

# Function to start recording video
def start_recording(filename):
    os.system(f"rpicam-vid -t 20s -o /home/pi/Videos/{filename}")  # Start recording

# Function to stop recording video after 20 seconds
def stop_recording():
    os.system("pkill rpicam-vid")

# Main function
def main():
    # Get current datetime and format it as a string
    now = datetime.now()
    filename = now.strftime("%Y%m%d_%H%M%S.h264")

    # Create and start the recording thread
    recording_thread = threading.Thread(target=start_recording, args=(filename,))
    recording_thread.start()

    while True:
        # Check some condition here
        # This is just an example, replace it with your actual condition

        # Continue doing other tasks
        print("dang quay")
        time.sleep(1)

# Function to check some condition
def some_condition_is_met():
    # Replace with your actual condition logic
    return False

# Function to perform other tasks
def do_other_tasks():
    # Replace with the actual tasks you need to perform
    time.sleep(1)  # Simulate doing some work

if __name__ == "__main__":
    main()
