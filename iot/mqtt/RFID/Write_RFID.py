import board
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



def write_data(data):
    # Convert data to bytes (UTF-8 encoded string)
    data_bytes = bytearray(data, 'utf-8')

    # Start writing from block 4 (beginning of Sector 1)
    block_to_write = 4
    blocks_needed = (len(data_bytes) + 15) // 16  # Calculate number of blocks needed
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is None
        print("No card found")
        return False
    for i in range(blocks_needed):
        # Get the next 16-byte chunk
        chunk = data_bytes[i * 16:(i + 1) * 16]

        # Pad the chunk with 0x00 if it's less than 16 bytes
        if len(chunk) < 16:
            chunk += b'\x00' * (16 - len(chunk))

        # Authenticate the block before writing
        authentication_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        success_auth = pn532.mifare_classic_authenticate_block(uid, block_to_write, 0x60, authentication_key)

        if success_auth:
            # Write the chunk to the current block
            success = pn532.mifare_classic_write_block(block_to_write, chunk)
            if success:
                print(f"Successfully wrote to block {block_to_write}")
            else:
                print(f"Failed to write to block {block_to_write}")
                break  # Stop if there is a write error
        else:
            print(f"Authentication failed for block {block_to_write}")
            break  # Stop if there is an authentication error

        # Move to the next block
        block_to_write += 1

    print("Data writing completed.")
    return True




if __name__ == "__main__":
    init_pn532()
    while True:
        data_1 = input("Enter Name: ")
        data_2 = input("Enter Phone number: ")
        data = f"Name: {data_1}, Phone number: {data_2}"
        wRFID = write_data(data)
        if wRFID is True:
            print("Card was written")
            break
        time.sleep(1)
