import json
import board
from board import SCL, SDA
from busio import I2C
from digitalio import DigitalInOut
import time
from adafruit_pn532.i2c import PN532_I2C
import traceback
import binascii

pn532 = None

def init_pn532():
    global pn532
    while True:
        try:
            i2c = board.I2C()
            reset_pin = DigitalInOut(board.D6)
            req_pin = DigitalInOut(board.D12)
            pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
            ic, ver, rev, support = pn532.firmware_version
            print(f"Found PN532 with firmware version: {ver}.{rev}")
            pn532.SAM_configuration()
            break
        except Exception:
            traceback.print_exc()
            pass


def save_user_data(uid, name, phone_number):
    data = {}
    try:
       
        with open('users.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        pass

    data[uid] = {
        'name': name,
        'phone_number': phone_number
    }

    
    with open('users.json', 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Information was saved for card UID {uid}.")

def write_data():
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is None:
        print("No card found")
        return False

    
    uid_hex = binascii.hexlify(uid).decode().upper()
    print(f"UID: {uid_hex}")

   
    name = input("Name: ")
    phone_number = input("Phone number: ")

   
    save_user_data(uid_hex, name, phone_number)

    return True

if __name__ == "__main__":
    init_pn532()
    while True:
        wRFID = write_data()
        if wRFID is False:
            print("Waiting ... ")
        else:
            break
        time.sleep(1)
