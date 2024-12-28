# handle/rfid_handle.py
import os
import json
import time
import threading
import traceback
import binascii

import board
import RPi.GPIO as GPIO
from busio import I2C
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C

from handle.tft_handle import TFTHandler

class RFIDHandler:
    """Handles RFID reading, user data management, and interaction with TFT display and MQTT."""

    BUZZER_PIN = 20
    USER_DATA_FILENAME = 'users.json'

    def __init__(self, mqtt_client):
        self.pn532 = None
        self.last_uid = None
        self.data = {'name': None, 'phone_number': None}
        self.first_time = 0
        self.stop_event = threading.Event()
        # self.tft_handler = TFTHandler()

        # Use the passed MQTT client instance
        self.mqtt_client = mqtt_client

        # Initialize GPIO
        self.setup_gpio()

        # Initialize PN532 hardware
        self.initialize_pn532()

        # Path to user data file
        self.user_data_file = os.path.join(os.path.dirname(__file__), self.USER_DATA_FILENAME)

    def setup_gpio(self):
        """Set up GPIO settings."""
        GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT)  # Set buzzer pin as output
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)  # Ensure buzzer is off initially

    def initialize_pn532(self):
        """Initialize the PN532 RFID reader."""
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
                print("Retrying PN532 initialization...")
                time.sleep(1)

    # def save_user_data(self, uid, name, phone_number):
    #     """Save user data based on UID to a JSON file."""
    #     data = self.load_user_data()
    #     data[uid] = {'name': name, 'phone_number': phone_number}

    #     with open(self.user_data_file, 'w') as f:
    #         json.dump(data, f, indent=4)

    #     print(f"Information saved for card UID {uid}.")

    def load_user_data(self):
        """Load user data from the JSON file."""
        try:
            with open(self.user_data_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print("Error decoding JSON from user data file.")
            return {}

    def get_user_data(self, uid):
        """Retrieve user data from the JSON file based on the UID."""
        users = self.load_user_data()
        user = users.get(uid)
        if user:
            return user
        else:
            print(f"No information found for UID {uid}.")
            return None

    def read_rfid(self):
        """Continuously read RFID cards and handle user data."""
        while not self.stop_event.is_set():
            uid = self.pn532.read_passive_target(timeout=0.5)

            if uid is None:
                self.handle_no_card_detected()
            else:
                self.handle_new_card(uid)

            # Wait for 0.7 seconds or until stop_event is set
            self.stop_event.wait(0.7)

    def handle_no_card_detected(self):
        """Handle the scenario when no new RFID card is detected."""
        if self.last_uid is not None:
            print(f"No new card detected. Last UID: {self.last_uid}")
        else:
            self.first_time += 1
            print(f"No card detected. User data: Name: {self.data['name']}, Phone number: {self.data['phone_number']}")
            if self.first_time == 1:
              pass
                #self.tft_handler.display_user_info(self.data)

    def handle_new_card(self, uid):
        """Handle actions when a new RFID card is detected."""
        uid_hex = binascii.hexlify(uid).decode().upper()
        self.ring_buzzer(duration=0.1)

        if uid_hex != self.last_uid:
            print(f"New card detected. UID: {uid_hex}")
            user_data = self.get_user_data(uid_hex)

            if user_data:
                self.data = user_data
                print(f"User information for UID {uid_hex}:")
                print(f"Name: {self.data['name']}")
                print(f"Phone number: {self.data['phone_number']}")
                #self.tft_handler.display_user_info(self.data)

                # Publish user info to MQTT
                self.mqtt_client.publish("Driver_information", self.data)
  
            else:
                self.data = {'name': "None", 'phone_number': "None"}
                #self.tft_handler.display_user_info(self.data)
                # Publish user info to MQTT
                self.mqtt_client.publish("Driver_information", self.data)


            self.last_uid = uid_hex

    def ring_buzzer(self, duration=0.1):
        """Activate the buzzer for a specified duration."""
        GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def stop_reading(self):
        """Stop the RFID reading process."""
        self.stop_event.set()
        self.cleanup()
        print("Stopping RFID reading process.")

    def cleanup(self):
        """Clean up GPIO settings."""
        GPIO.cleanup()
