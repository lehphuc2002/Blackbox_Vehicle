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


# def init_device():
    # #global display
    # global pn532

    # while True:
        # try:
            # i2c = board.I2C()
            # # reset_pin = DigitalInOut(board.D6)
            # # req_pin = DigitalInOut(board.D12)
            # # pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
			# pn532 = PN532_I2C(i2c, debug=False)
			
            # spi = board.SPI()
            # # CS_PIN = DigitalInOut(board.CE1)
            # # DC_PIN = DigitalInOut(board.D14)
            # # RST_PIN = DigitalInOut(board.D24)

            # # display = st7789.ST7789(
                # # spi,
                # # cs=CS_PIN,
                # # dc=DC_PIN,
                # # rst=RST_PIN,
                # # baudrate=64000000,
                # # width=240,
                # # height=320,
                # # rotation=90,
            # # )

            # # ic, ver, rev, support = pn532.firmware_version

            # pn532.SAM_configuration()

            # # GPIO.setwarnings(False)
            # # GPIO.setmode(GPIO.BCM)

            # # GPIO.setup(buzzer_pin, GPIO.OUT)

            # break
        # except Exception:
            # pass

def init_pn532():
    global pn532
    while True:
        try:
            i2c = board.I2C()
            # reset_pin = DigitalInOut(board.D6)
            # req_pin = DigitalInOut(board.D12)
            # pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
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


# def device_beep():
    # print("[DEVICE] Beep!!!!!!!!!!!!!!!!!!!!!")
    # GPIO.output(buzzer_pin, GPIO.HIGH)
    # time.sleep(0.1)
    # GPIO.output(buzzer_pin, GPIO.LOW)


def device_read_data():
    # card_number = input('[DEVICE] Input card number: ')
    # return card_number

    # card_number = '0111111'
    # card_number = '0004010132023'

    # random_number = random.randint(0, 100)
    # if random_number < 80:
    #     return None

    # return card_number
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


def device_beep_ts(duration_ts: int):
    while duration_ts > 0:
        start_ts = time.perf_counter()
        device_beep()
        wait_ts = DEVICE_BEEP_DELAY - (time.perf_counter() - start_ts)
        if wait_ts <= 0:
            continue
        time.sleep(wait_ts)
        duration_ts -= time.perf_counter() - start_ts


def device_check_connect():
    return os.system("ping -c 1 google.com.vn >/dev/null") == 0

if __name__ == "__main__":
	init_pn532()
	while True:
		check_connection()
		device_read_data()
		time.sleep(1)
