import json
import board
from busio import I2C
from digitalio import DigitalInOut
import binascii
import time
from adafruit_pn532.i2c import PN532_I2C
import traceback

pn532 = None
last_uid = None  # Store the last UID of the card
data = {'name': None, 'phone_number': None}  # Initial data when no card is detected

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

def get_user_data(uid):
    """Retrieve user data from the JSON file based on the UID."""
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
            if uid in users:
                return users[uid]
            else:
                print(f"No information found for UID {uid}.")
                return None
    except FileNotFoundError:
        print("User data file not found.")
        return None

def read_data():
    """Continuously read NFC cards and update user data."""
    global last_uid, data
    
    uid = pn532.read_passive_target(timeout=0.5)

    if uid is None:
        # No new card detected, retain the last user's data
        if last_uid is not None:
            print(f"No new card detected. Retaining last user data for UID: {last_uid}")
        else:
            # If no card has ever been detected, display default data
            print(f"No card detected. User data: Name: {data['name']}, Phone number: {data['phone_number']}")
        return False

    # Convert UID to a hex string
    uid_hex = binascii.hexlify(uid).decode().upper()

    # If a new card is detected, update the data
    if uid_hex != last_uid:
        print(f"New card detected. UID: {uid_hex}")
        user_data = get_user_data(uid_hex)
        
        if user_data:
            data = user_data  # Update with new user information
            print(f"User information for UID {uid_hex}:")
            print(f"Name: {data['name']}")
            print(f"Phone number: {data['phone_number']}")
        else:
            # If the card UID is not found, keep default None values
            data = {'name': None, 'phone_number': None}
            print("No user information found for this card.")
        
        last_uid = uid_hex  # Update the last detected UID

    return True

if __name__ == "__main__":
    init_pn532()
    while True:
        rRFID = read_data()
        print(data)
        time.sleep(1)  # Read every 1 second
