
from board import SCL, SDA
from busio import I2C
from digitalio import DigitalInOut
import binascii
import time
import RPi.GPIO as GPIO
from adafruit_pn532.i2c import PN532_I2C
import traceback


pn532 = None

def init_pn532():
    global pn532
    while True:
        try:
            i2c = I2C(SCL, SDA)
            #reset_pin = DigitalInOut(board.D6)
            #req_pin = DigitalInOut(board.D12)
            pn532 = PN532_I2C(i2c, debug=False)
            #pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
            ic, ver, rev, support = pn532.firmware_version
            print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))
            pn532.SAM_configuration()
            break
        except Exception:
            traceback.print_exc()
            pass

# buzzer_pin = 4
# GPIO.setwarnings(False)
# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(buzzer_pin, GPIO.OUT)

# def device_beep():
    # GPIO.output(buzzer_pin, GPIO.HIGH)
    # time.sleep(0.1)
    # GPIO.output(buzzer_pin, GPIO.LOW)


def write_data(data):
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is None:
        print("No card found")
        return
    
    uid_decode = binascii.hexlify(uid).decode("utf-8")
    print("UID:", uid_decode)

    authentication_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    sector_number = 0
    block_number = 1

    success = False

    while not success:
        success = pn532.mifare_classic_authenticate_block(uid, sector_number * 4, 0x60, authentication_key)
        if success:
            print("Successful")

            data_bytes = data.encode("utf-8").ljust(16, b"\0")

            block_to_write = sector_number * 4 + block_number
            success = pn532.mifare_classic_write_block(block_to_write, data_bytes)
            if success:
                #device_beep()
                print("Data written to block {0}: {1}".format(block_to_write, data))
            else:
                print("Error writing data to block {0}".format(block_to_write))
        else:
            print("Failed. Retrying...")


if __name__ == "__main__":
	init_pn532()
	while True:
        data_1 = input("Enter Name: ")
        data_2 = input("Enter Phone number: ")
        data = f"Name: {data_1}, Phone number: {data_2}"
        write_data(data)
        time.sleep(1)
