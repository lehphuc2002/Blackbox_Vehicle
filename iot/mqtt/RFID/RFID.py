import json
import board
from busio import I2C
from digitalio import DigitalInOut
import time
from adafruit_pn532.i2c import PN532_I2C
import traceback
import binascii

class RFID_lib:
    def __init__(self):
        # These are now instance variables
        self.pn532 = None
        self.last_uid = None  # Store the last UID of the card
        self.data = {'name': None, 'phone_number': None}  # Initial data when no card is detected

        while True:
            try:
                i2c = board.I2C()
                reset_pin = DigitalInOut(board.D6)
                req_pin = DigitalInOut(board.D12)
                self.pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
                ic, ver, rev, support = self.pn532.firmware_version
                print(f"Found PN532 with firmware version: {ver}.{rev}")
                self.pn532.SAM_configuration()
                break
            except Exception:
                traceback.print_exc()
                pass

    def save_user_data(self, uid, name, phone_number):
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

    def write_data(self):
        uid = self.pn532.read_passive_target(timeout=0.5)
        if uid is None:
            print("No card found")
            return False

        uid_hex = binascii.hexlify(uid).decode().upper()
        print(f"UID: {uid_hex}")

        name = input("Name: ")
        phone_number = input("Phone number: ")

        self.save_user_data(uid_hex, name, phone_number)

        return True

    def get_user_data(self, uid):
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

    def read_data(self):
        """Continuously read NFC cards and update user data."""
        uid = self.pn532.read_passive_target(timeout=0.5)

        if uid is None:
            # No new card detected, retain the last user's data
            if self.last_uid is not None:
                print(f"No new card detected. Retaining last user data for UID: {self.last_uid}")
            else:
                # If no card has ever been detected, display default data
                print(f"No card detected. User data: Name: {self.data['name']}, Phone number: {self.data['phone_number']}")
            return False

        # Convert UID to a hex string
        uid_hex = binascii.hexlify(uid).decode().upper()

        # If a new card is detected, update the data
        if uid_hex != self.last_uid:
            print(f"New card detected. UID: {uid_hex}")
            user_data = self.get_user_data(uid_hex)

            if user_data:
                self.data = user_data  # Update with new user information
                print(f"User information for UID {uid_hex}:")
                print(f"Name: {self.data['name']}")
                print(f"Phone number: {self.data['phone_number']}")
            else:
                # If the card UID is not found, keep default None values
                self.data = {'name': None, 'phone_number': None}
                print("No user information found for this card.")

            self.last_uid = uid_hex  # Update the last detected UID

        return True
    def get_data(self):
        """Return the current data."""
        return self.data

if __name__ == "__main__":
    rfid = RFID_lib()  # Initialize the RFID object
    while True:
        rfid.read_data()
        print(rfid.data)  # Print current data
        time.sleep(1)  # Read every 1 second
