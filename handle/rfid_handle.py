# handle/rfid_handle.py
import os
import json
import time
import logging
import threading
import traceback
import binascii
from datetime import datetime, timedelta

import board
import RPi.GPIO as GPIO
from busio import I2C
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C

from handle.tft_handle import TFTHandler
import paho.mqtt.client as paho

class RFIDHandler:
    """Handles RFID reading, user data management, and interaction with TFT display and MQTT."""

    BUZZER_PIN = 20
    USER_DATA_FILENAME = 'users.json'
    DRIVER_STATUS_FILENAME = 'driver_status.json'
    MAX_CONTINUOUS_DRIVE_TIME = 4 * 3600  # 4 hours in seconds
    CONTINUOUS_DRIVE_WARNING = 3 * 3600 + 55 * 60  # Warning at 3 hours 55 minutes
    MIN_REST_TIME = 15 * 60  # 15 minutes in seconds
    MAX_DAILY_DRIVE_TIME = 10 * 3600  # 10 hours in seconds
    WARNING_INTERVAL = 10  # 1 minute warning interval


    def __init__(self, mqtt_client):
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.pn532 = None
        self.last_uid = None
        self.data = {'name': None, 'phone_number': None}
        self.first_time = 0
        self.stop_event = threading.Event()
        self.tft_handler = TFTHandler()

        # Use the passed MQTT client instance
        self.mqtt_client = mqtt_client
        
        # Driver session tracking
        self.current_driver = None
        self.drive_start_time = None
        self.last_rest_time = None
        self.daily_drive_time = 0
        self.daily_reset_time = None
        self.last_warning_time = None
        self.is_single_driver = False

        self.setup_gpio()
        self.initialize_pn532()
        
        # Variables time tracking
        self.accumulated_drive_time = {}  # {uid: seconds}
        self.driver_status_file = os.path.join(os.path.dirname(__file__), self.DRIVER_STATUS_FILENAME)

        # Path to user data file
        self.user_data_file = os.path.join(os.path.dirname(__file__), self.USER_DATA_FILENAME)
        
        # Load previous driver status
        self.load_driver_status()
        
        self.warning_thread = threading.Thread(target=self.check_warnings)
        self.warning_thread.daemon = True
        self.warning_thread.start()
        self.warning_lock = threading.Lock()

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
        try:
            users = self.load_user_data()
            self.logger.debug(f"Loaded users: {list(users.keys())}")
            
            user = users.get(uid)
            if user:
                self.logger.info(f"Found user data for UID {uid}")
                return user
            else:
                self.logger.warning(f"No user data found for UID {uid}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting user data: {e}")
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
                self.tft_handler.display_user_info(self.data)
    
    def save_driver_status(self):
        """Save current driver status to file"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'current_driver': self.current_driver,
                'accumulated_times': self.accumulated_drive_time,
                'daily_drive_time': self.daily_drive_time,
                'daily_reset_time': self.daily_reset_time.isoformat() if self.daily_reset_time else None,
                'last_rest_time': self.last_rest_time.isoformat() if self.last_rest_time else None  # Add this
            }
            
            # Create backup before writing
            if os.path.exists(self.driver_status_file):
                backup_file = f"{self.driver_status_file}.bak"
                os.replace(self.driver_status_file, backup_file)
                
            with open(self.driver_status_file, 'w') as f:
                json.dump(status, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving driver status: {e}")
            # Try to restore from backup
            if os.path.exists(f"{self.driver_status_file}.bak"):
                os.replace(f"{self.driver_status_file}.bak", self.driver_status_file)
            
    def load_driver_status(self):
        """Load driver status from file and handle power loss situations"""
        try:
            if not os.path.exists(self.driver_status_file):
                return

            with open(self.driver_status_file, 'r') as f:
                status = json.load(f)

            # Calculate time difference since last save
            last_time = datetime.fromisoformat(status['timestamp'])
            current_time = datetime.now()
            time_diff = (current_time - last_time).total_seconds()

            # If more than 15 minutes passed, reset accumulated times
            if time_diff >= self.MIN_REST_TIME:
                self.accumulated_drive_time = {}
                self.current_driver = None
                self.drive_start_time = None
            else:
                # Restore previous status
                self.accumulated_drive_time = status['accumulated_times']
                self.current_driver = status['current_driver']
                if self.current_driver:
                    self.accumulated_drive_time[self.current_driver] += time_diff

            # Restore daily tracking
            if status['daily_reset_time']:
                self.daily_reset_time = datetime.fromisoformat(status['daily_reset_time'])
                if current_time.date() > self.daily_reset_time.date():
                    self.daily_drive_time = 0
                else:
                    self.daily_drive_time = status['daily_drive_time']
            
            # Add daily drive time validation
            if self.daily_drive_time < 0:
                self.daily_drive_time = 0
            elif self.daily_drive_time > self.MAX_DAILY_DRIVE_TIME:
                self.daily_drive_time = self.MAX_DAILY_DRIVE_TIME

        except Exception as e:
            self.logger.error(f"Error loading driver status: {e}")
            self.accumulated_drive_time = {}

    def reset_daily_drive_time(self):
        """Reset daily drive time at midnight"""
        try:
            current_time = datetime.now()
            if (self.daily_reset_time is None or 
                current_time.date() > self.daily_reset_time.date()):
                self.daily_drive_time = 0
                self.daily_reset_time = current_time
                self.save_driver_status()  # Save after reset
        except Exception as e:
            self.logger.error(f"Error resetting daily drive time: {e}")

    def check_driving_limits(self, uid_hex):
        """Enhanced driving limits check"""
        current_time = datetime.now()
        
        # Reset daily counters if needed
        self.reset_daily_drive_time()

        # Get accumulated time
        accumulated_time = self.accumulated_drive_time.get(uid_hex, 0)
        
        # Check if rest period was sufficient
        if uid_hex in self.accumulated_drive_time:
            if self.last_rest_time:
                rest_duration = (current_time - self.last_rest_time).total_seconds()
                if rest_duration >= self.MIN_REST_TIME:
                    # Reset accumulated time after sufficient rest
                    self.accumulated_drive_time[uid_hex] = 0
                    accumulated_time = 0

        # Check limits
        if accumulated_time >= self.MAX_CONTINUOUS_DRIVE_TIME:
            return False, "Must rest 15 minutes"
            
        if self.daily_drive_time >= self.MAX_DAILY_DRIVE_TIME:
            return False, "Maximum daily drive time reached"

        return True, "OK"


    def start_driving_session(self, uid_hex):
        """Enhanced session start with accumulated time check"""
        # Add check for None or invalid uid_hex
        if not uid_hex:
            return False, "Invalid card"
        
        # Add lock to prevent race conditions
        with threading.Lock():
            can_drive, message = self.check_driving_limits(uid_hex)
            if not can_drive:
                return False, message
            
            try:
                self.current_driver = uid_hex
                self.drive_start_time = datetime.now()
                if uid_hex not in self.accumulated_drive_time:
                    self.accumulated_drive_time[uid_hex] = 0

                self.save_driver_status()
                return True, "Session started"
            except Exception as e:
                self.logger.error(f"Error starting session: {e}")
                return False, "System error"

    def end_driving_session(self):
        """Enhanced session end with status saving"""
        try:
            if self.drive_start_time and self.current_driver:
                with threading.Lock():
                    session_duration = (datetime.now() - self.drive_start_time).total_seconds()
                    
                    # Update accumulated and daily times
                    self.accumulated_drive_time[self.current_driver] += session_duration
                    self.daily_drive_time += session_duration
                    
                    # Set rest time
                    self.last_rest_time = datetime.now()
                    
                    # Clear current session
                    self.drive_start_time = None
                    self.current_driver = None
                    
                    # Save status
                    self.save_driver_status()
                    self.ring_buzzer_pattern('logout')

                    return session_duration
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
        return 0

    def start_rest_period(self):
        """Start driver rest period"""
        self.last_rest_time = datetime.now()
        self.drive_start_time = None

    def check_warnings(self):
        """Continuously check for warning conditions"""
        last_no_driver_warning = 0
        last_rest_warning = 0
        
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                with self.warning_lock:
                    # No driver warning (every minute)
                    if not self.current_driver:
                        if current_time - last_no_driver_warning >= self.WARNING_INTERVAL:
                            self.logger.info("No driver warning - beeping")
                            self.ring_buzzer_pattern('warning')
                            last_no_driver_warning = current_time
                    
                    # Rest needed warning (3h 55m)
                    if self.current_driver and self.drive_start_time:
                        drive_duration = current_time - self.drive_start_time.timestamp()
                        if drive_duration >= self.CONTINUOUS_DRIVE_WARNING:
                            if current_time - last_rest_warning >= self.WARNING_INTERVAL:
                                self.logger.info("Rest needed warning - beeping")
                                self.ring_buzzer_pattern('rest_needed')
                                last_rest_warning = current_time
                
                time.sleep(1)  # Move sleep outside the lock
                
            except Exception as e:
                self.logger.error(f"Error in check_warnings: {e}")
                time.sleep(1)
    
    def ring_buzzer_pattern(self, pattern):
        """
        Activate the buzzer with specific patterns:
        - 'login': 2 beeps for successful login
        - 'logout': 3 beeps for successful logout
        """
        if pattern == 'login':
            # Two beeps for login
            for _ in range(2):
                GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self.BUZZER_PIN, GPIO.LOW)
                time.sleep(0.2)
        elif pattern == 'logout':
            # Three beeps for logout
            for _ in range(3):
                GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self.BUZZER_PIN, GPIO.LOW)
                time.sleep(0.2)
        elif pattern == 'warning':
            # Single beep for no driver warning
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.2)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
        elif pattern == 'rest_needed':
            # Two beeps for approaching driving limit
            for _ in range(2):
                GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self.BUZZER_PIN, GPIO.LOW)
                time.sleep(0.2)

    def handle_new_card(self, uid):
        """
        Handle card detection with local processing and simple MQTT publish.
        Handles:
        1. Single driver login/logout
        2. Driver switching (A -> B)
        3. Time tracking
        4. Rest periods
        """
        uid_hex = binascii.hexlify(uid).decode().upper()
        self.logger.info(f"Card detected: {uid_hex}")
        
        self.first_time = 0
        
        user_data = self.get_user_data(uid_hex)
        if not user_data:
            self.logger.warning(f"Unauthorized card detected: {uid_hex}")
            self.handle_unauthorized_card()
            return

        # Get accumulated time for this driver
        accumulated_time = self.accumulated_drive_time.get(uid_hex, 0)
        
        # Case 1: No active driver - New Login
        if not self.current_driver:
            can_start, message = self.start_driving_session(uid_hex)
            if can_start:
                self.ring_buzzer_pattern('login')
                status = f"Driving (Total: {accumulated_time/3600:.1f}h)"
                self.last_warning_time = time.time()
            else:
                status = message
        
        # Case 2: Same driver taps card again - Logout
        elif uid_hex == self.current_driver:
            session_duration = self.end_driving_session()
            # self.ring_buzzer_pattern('logout')
            status = f"End driving {session_duration/3600:.1f}h"
            self.start_rest_period()
        
        # Case 3: Different driver taps while someone is driving - Driver Switch
        else:
            # End current driver's session
            self.end_driving_session()
            
            # Try to start new driver's session
            can_start, message = self.start_driving_session(uid_hex)
            if can_start:
                self.ring_buzzer_pattern('login')
                status = "New driver session"
            else:
                status = message

        # Update display and save status
        self.data = {**user_data, 'status': status}
        self.tft_handler.display_user_info(self.data)
        
        # Simple MQTT publish with just card data
        payload = self.mqtt_client.create_payload_user_info(self.data)
        self.mqtt_client.client.publish("v1/devices/me/telemetry", payload, qos=0)
        
        # Save current state
        self.save_driver_status()
        self.last_uid = uid_hex

    def handle_unauthorized_card(self):
        """Handle unauthorized card detection"""
        try:
            # First reset all states
            self.reset_all_states()
            
            # Set unauthorized card message
            self.data = {
                'name': "Unauthorized", 
                'phone_number': "None", 
                'status': "Unauthorized card",
                'license': "Unauthorized"
            }
            
            # Display on TFT
            self.tft_handler.display_user_info(self.data)
            
            # Beep for unauthorized card
            self.ring_buzzer(0.1)
            
            # MQTT publish
            try:
                payload = self.mqtt_client.create_payload_user_info(self.data)
                self.mqtt_client.client.publish("v1/devices/me/telemetry", payload, qos=0)
                print("HEHEHHEHEEHEHHE DONT USER")
            except Exception as e:
                self.logger.error(f"MQTT publish error in handle_unauthorized_card: {e}")
                
            self.logger.info("Unauthorized card detected and handled")
            
        except Exception as e:
            self.logger.error(f"Error in handle_unauthorized_card: {e}")
            
    def reset_all_states(self):
        """Reset all system states"""
        self.data = {'name': None, 'phone_number': None}
        self.last_uid = None
        self.first_time = 0
        self.current_driver = None
        self.drive_start_time = None
        self.last_warning_time = None
            
    def publish_mqtt_update(self):
        """Publish update to MQTT"""
        try:
            payload = self.mqtt_client.create_payload_user_info(self.data)
            self.mqtt_client.client.publish("v1/devices/me/telemetry", payload, qos=0)
        except Exception as e:
            self.logger.error(f"MQTT publish error: {e}")

    def ring_buzzer(self, duration=0.1):
        """Activate the buzzer for a specified duration."""
        GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def stop_reading(self):
        """Stop the RFID reading process."""
        self.stop_event.set()
        try:
            self.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        print("Stopping RFID reading process.")


    def cleanup(self):
        """Clean up GPIO settings."""
        GPIO.cleanup()

#####################################################################################
"""
Assume the driver starts working at 6:00 AM

Morning Session:

    Login: 06:00:00

    Start time: 06:00:00

    Daily drive time: 0 hours

    Warning time: 09:55:00 (after 3 hours and 55 minutes)

    Must rest: 10:00:00 (after 4 hours)

    Logout: 10:00:00

    Session duration: 4 hours

    Daily drive time: 4 hours

    Mandatory Rest Period:

    Last rest time: 10:00:00
    Minimum rest required: 15 minutes
    Can drive again after: 10:15:00
    
Midday Session:

    Login: 10:20:00 (after resting for 20 minutes)

    New start time: 10:20:00

    Previous daily drive time: 4 hours

    Warning time: 14:15:00

    Must rest: 14:20:00

    Logout: 14:20:00

    Session duration: 4 hours

    Daily drive time: 8 hours

Afternoon Session:

    Login: 14:40:00

    Remaining daily drive time: 2 hours
    (because MAX_DAILY_DRIVE_TIME = 10 hours)

    Must stop: 16:40:00
    (when the daily limit of 10 hours is reached)
"""