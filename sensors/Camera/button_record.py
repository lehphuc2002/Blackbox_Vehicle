#!/usr/bin/env python

# Import necessary libraries
import time
import os
import keyboard  # For detecting key presses

# Initial state of recording
recording = True

# Function to handle key press
def toggle_recording():
    global recording
    if recording:
        recording = False
        os.system("sudo sh /home/pi/DO_AN_git/Blackbox_Vehicle/sensors/Camera/stop_recording.sh")
    else:
        recording = True
        os.system("sudo sh /home/pi/DO_AN_git/Blackbox_Vehicle/sensors/Camera/record.sh")

# Register the key press event for 'q'
keyboard.on_press_key("q", lambda _: toggle_recording())

try:
    while True:
        # Check if 'q' is held down for 5 seconds to shutdown
        if keyboard.is_pressed("q"):
            time.sleep(5)
            if keyboard.is_pressed("q"):
                os.system("sudo shutdown -h now")
                break
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
