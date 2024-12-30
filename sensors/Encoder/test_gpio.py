import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def callback(channel):
    print(f"Edge detected on {channel}")

GPIO.add_event_detect(15, GPIO.BOTH, callback=callback)
GPIO.add_event_detect(27, GPIO.BOTH, callback=callback)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()