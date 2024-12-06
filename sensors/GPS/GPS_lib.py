#!/usr/bin/env python
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import serial
import time
import threading
import math
import os
import subprocess
from geopy.geocoders import Nominatim
from unidecode import unidecode


class GPSModule:
    def __init__(self, gps_port="/dev/ttyUSB2", baud_rate=115200, power_key=6):
        """
        Initialize the GPS module.
        Parameters:
            gps_port (str): GPS serial port.
            baud_rate (int): Baud rate for serial communication.
            power_key (int): GPIO pin for power control.
        """
        self.gps_port = gps_port
        self.baud_rate = baud_rate
        self.power_key = power_key
        self.ser = None
        self.latitude = None
        self.longitude = None
        self.prev_latitude = None
        self.prev_longitude = None
        self.velocity = None
        self._stop_event = threading.Event()
        self._gps_read_thread = threading.Thread(target=self._read_gps_data)
        self.buffer = ""  # Buffer to store serial data
        self.buffer_lock = threading.Lock()

        # Setup hardware
        self.setup_serial()
        self.setup_gpio()
        self.power_on()

    def setup_serial(self):
        """
        Set up the serial connection for GPS.
        """
        self.ser = serial.Serial(self.gps_port, self.baud_rate, timeout=1)
        self.ser.flushInput()
        print(f"{self.gps_port} Opened with baud rate {self.baud_rate}")

    def setup_gpio(self):
        """
        Set up GPIO for controlling the power key.
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.power_key, GPIO.OUT)

    def power_on(self):
        """
        Power on the GPS module.
        """
        print("SIM7600X is starting...")
        GPIO.output(self.power_key, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(self.power_key, GPIO.LOW)
        time.sleep(10)
        self.ser.flushInput()
        if self.send_at("AT+CGPS=1", "OK", timeout=1):
            time.sleep(2)
            print("SIM7600X is ready.")
        else:
            print("SIM7600X is busy.")

    def power_down(self):
        """
        Power down the GPS module.
        """
        print("SIM7600X is shutting down...")
        self.send_at("AT+CGPS=0", "OK", timeout=1)
        GPIO.output(self.power_key, GPIO.HIGH)
        time.sleep(3)
        GPIO.output(self.power_key, GPIO.LOW)
        time.sleep(10)
        print("Goodbye.")

    def send_at(self, command, expected_response, timeout=1):
        """
        Send an AT command to the GPS module.
        Parameters:
            command (str): The AT command.
            expected_response (str): Expected response from the module.
            timeout (int): Time to wait for a response.
        Returns:
            bool: True if the response matches the expected response, otherwise False.
        """
        self.ser.write((command + "\r\n").encode())
        time.sleep(timeout)
        response = b""

        if self.ser.in_waiting:
            time.sleep(0.01)
            response = self.ser.read(self.ser.inWaiting())

        if response:
            decoded_response = response.decode()
            if expected_response not in decoded_response:
                print(f"{command} ERROR")
                print(f"Response: {decoded_response}")
                return False
            else:
                print(decoded_response)
                return True
        else:
            print("No response or GPS not ready.")
            return False

    def _read_gps_data(self):
        """
        Continuously read and process GPS data.
        """
        while not self._stop_event.is_set():
            try:
                with self.buffer_lock:
                    self.ser.write(("AT+CGPSINFO" + "\r\n").encode())
                    time.sleep(1)
                    data = b""
                    if self.ser.inWaiting():
                        time.sleep(0.01)
                        data = self.ser.readline().decode("utf-8", errors="ignore")
                        if data:
                            self.buffer += data
                            self._process_gps_data()
            except serial.SerialException as e:
                print(f"Serial Exception: {e}")

    def _process_gps_data(self):
        """
        Process GPS data from the buffer.
        """
        lines = self.buffer.split("\n")
        self.buffer = lines.pop()  # Keep the last incomplete line in the buffer

        for line in lines:
            line = line.strip()
            if "+CGPSINFO" in line:
                # Clean and extract GPS data
                GPSDATA = (
                    line.replace("\n", "")
                    .replace("\r", "")
                    .replace("AT", "")
                    .replace("+CGPSINFO", "")
                    .replace(": ", "")
                )
                # Check if GPS data length is valid
                if len(GPSDATA) > 29:
                    # Extract latitude and longitude components
                    Lat = GPSDATA[:2]
                    SmallLat = GPSDATA[2:11]
                    NorthOrSouth = GPSDATA[12]
                    Long = GPSDATA[14:17]
                    SmallLong = GPSDATA[17:26]
                    EastOrWest = GPSDATA[27]

                    # Convert latitude and longitude to decimal degrees
                    FinalLat = float(Lat) + float(SmallLat) / 60
                    FinalLong = float(Long) + float(SmallLong) / 60

                    # Adjust for hemisphere
                    latitude = FinalLat if NorthOrSouth == "N" else -FinalLat
                    longitude = FinalLong if EastOrWest == "E" else -FinalLong

                    # Update current latitude and longitude
                    self.latitude = latitude
                    self.longitude = longitude

                    # Calculate velocity if previous coordinates are available
                    if self.prev_latitude is not None and self.prev_longitude is not None:
                        distance = haversine(
                            self.prev_longitude,
                            self.prev_latitude,
                            self.longitude,
                            self.latitude,
                        )
                        time_elapsed = 1  # Assuming 1 second interval
                        self.velocity = distance / time_elapsed
                    else:
                        self.velocity = None  # Velocity is undefined for the first data point

                    # Update previous coordinates
                    self.prev_latitude = self.latitude
                    self.prev_longitude = self.longitude
            time.sleep(1)

    def get_velocity(self):
        """
        Retrieve the current velocity.
        Returns:
            float: The current velocity in m/s, or None if it hasn't been calculated yet.
        """
        return self.velocity

    def get_location(self):
        """
        Retrieve the current GPS location.
        Returns:
            tuple: (latitude, longitude) or (None, None) if data is not available.
        """
        return self.latitude, self.longitude

    def start(self):
        """
        Start the GPS data reading thread.
        """
        self._gps_read_thread.start()

    def stop(self):
        """
        Stop the GPS data reading thread.
        """
        self.power_down()
        self._stop_event.set()
        self._gps_read_thread.join()

    def cleanup(self):
        """
        Clean up resources.
        """
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"{self.gps_port} Closed.")
        GPIO.cleanup()
        print("GPIO Cleaned up.")

    def kill_process_using_tty(self, tty_device):
        """
        Kill the process using the given tty device.
        Parameters:
            tty_device (str): The tty device to free.
        """
        try:
            result = os.popen(f"sudo fuser {tty_device}").read().strip()
            if result:
                print(f"Terminating processes using {tty_device}: {result}")
                os.system(f"sudo kill -9 {result}")
                time.sleep(1)
        except Exception as e:
            print(f"Error killing process using {tty_device}: {e}")


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points on the Earth.
    Parameters:
        lon1, lat1, lon2, lat2 (float): Longitude and latitude of the two points.
    Returns:
        float: Distance in meters.
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    r = 6371  # Earth radius in kilometers
    return 1000 * c * r  # Convert to meters


def main():
    gps = GPSModule()
    geolocator = Nominatim(user_agent="geoapi")

    try:
        gps.start()
        while True:
            latitude, longitude = gps.get_location()
            if latitude is not None and longitude is not None:
                location = geolocator.reverse((latitude, longitude), language="en")
                address = location.address
                address_no_accent = unidecode(address)
                print(f"Latitude: {latitude}, Longitude: {longitude}")
                print(f"Address: {address_no_accent}")
            else:
                print("Waiting for GPS data...")
            velocity = gps.get_velocity()
            if velocity is not None:
                print(f"Velocity: {velocity:.2f} m/s")
            else:
                print("Waiting for velocity data...")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        gps.stop()
        gps.cleanup()


if __name__ == "__main__":
    main()
