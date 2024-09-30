import binascii
import os
import random
import time
from datetime import datetime
from os import path
import requests
import traceback
from busio import I2C
import board
import numpy as np
import pocketbase
import RPi.GPIO as GPIO
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import PN532
from digitalio import DigitalInOut
from PIL import Image
from pocketbase import PocketBase


DEVID = 2222


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

            i2c = board.I2C()
            reset_pin = DigitalInOut(board.D6)
            req_pin = DigitalInOut(board.D12)
            pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
            ic, ver, rev, support = pn532.firmware_version
            print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))
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

def read_data_test():
    block_to_read = 4  # Starting block
    blocks_to_read = 3  # Number of blocks to read (based on how much data was written)
    data = bytearray()
    uid = pn532.read_passive_target(timeout=0.5)
    authentication_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    success_auth = pn532.mifare_classic_authenticate_block(uid, block_to_read, 0x60, authentication_key)
    for i in range(blocks_to_read):
        data_bytes = pn532.mifare_classic_read_block(block_to_read)
        if data_bytes:
            data.extend(data_bytes)
            block_to_read += 1
        else:
            print(f"Failed to read block {block_to_read}")
            break
    # Decode and strip null bytes from the data
    data_str = data.decode("utf-8").rstrip('\0')
    return data_str


def device_check_connect():
    return os.system("ping -c 1 google.com.vn >/dev/null") == 0

if __name__ == "__main__":
    init_pn532()
    while True:
        data = read_data_test()
        print(data)
        time.sleep(1)
