import binascii
import os
import random
import time
from datetime import datetime
from os import path
import requests
import traceback

import adafruit_rgb_display.st7789 as st7789
import board
import numpy as np
import pocketbase
import RPi.GPIO as GPIO
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import PN532
from digitalio import DigitalInOut
from PIL import Image
from pocketbase import PocketBase

# ID c?a th?
DEVID = 2222

# Kho?ng ngh? gi?a hai l?n d?c th?
DEVICE_DELAY_BETWEEN_READ = 3  
DEVICE_BEEP_DELAY = 0.5  

#
display = None
pn532 = None
buzzer_pin = 4
pn532_address = 0x24
i2c_bus = 1



def init_pn532():
    global pn532
    while True:
        try:
            i2c = I2C(SCL, SDA)
            pn532 = PN532_I2C(i2c, debug=False)
            pn532.SAM_configuration()

            break
        except Exception:
            traceback.print_exc()
            pass

def check_connection():
    global pn532
    try:
        ic, ver, rev, support = pn532.firmware_version
        return True
    except Exception:
        traceback.print_exc()
        return False




def device_read_data():

    uid = pn532.read_passive_target(timeout=0.5)
    if uid is None:
        # print("No card found")
        return

    authentication_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    success = pn532.mifare_classic_authenticate_block(uid, 1, 0x60, authentication_key)
    if success:
        data_bytes = pn532.mifare_classic_read_block(1)
        if data_bytes:
            data = data_bytes.decode("utf-8").rstrip("\0")

            return data
        else:
            print("Error reading data")
    else:
        print("Authentication failed")


def device_isvalid_time(read_ts: float = datetime.now().timestamp()):
    return True




def device_check_connect():
    return os.system("ping -c 1 google.com.vn >/dev/null") == 0

if __name__ == "__main__":
	init_pn532()
	while True:
		check_connection()
		device_read_data()
		time.sleep(1)
