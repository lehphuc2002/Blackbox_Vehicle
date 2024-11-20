#!/usr/bin/env python
# -*- coding: utf-8 -*-
import serial
import time
import threading
import math
import os
import subprocess
from geopy.geocoders import Nominatim


class GPSModule:
    def __init__(self, gps_port="/dev/ttyUSB1", setup_port="/dev/ttyUSB2", baudrate=115200):
        """
        Initialize the GPSReader object.
        Parameters:
            gps_port (str): Port for GPS data.
            setup_port (str): Port for GPS setup commands.
            baudrate (int): Baudrate for serial communication.
        """
        self.gps_port = gps_port
        self.setup_port = setup_port
        self.baudrate = baudrate
        self.ser1 = None  # Serial connection for GPS data
        self.ser2 = None  # Serial connection for GPS setup
        self.latitude = None
        self.longitude = None
        self.prev_latitude = None
        self.prev_longitude = None
        self.velocity = None  # Store current velocity in m/s
        self._stop_event = threading.Event()
        self.buffer = ""  # Buffer to store data read from serial
        self.buffer_lock = threading.Lock()  # Lock to manage buffer access
        self._gps_read_thread = threading.Thread(target=self._read_from_serial)
        self._gps_process_thread = threading.Thread(target=self._process_gps_data)

    def kill_process_using_tty(self, tty_device):
        """
        Kill the process using the given tty device.
        Parameters:
            tty_device (str): The tty device to free.
        """
        try:
            # Use `fuser` to get PIDs using the tty device
            result = os.popen(f"sudo fuser {tty_device}").read().strip()
            if result:
                print(f"Terminating processes using {tty_device}: {result}")
                os.system(f"sudo kill -9 {result}")
                time.sleep(1)
            else:
                print(f"No process using {tty_device}.")
        except Exception as e:
            print(f"Error killing process using {tty_device}: {e}")

    def open_tty_in_terminal(self, tty_device):
        """
        Open a new terminal and run the minicom command for the specified tty device.
        Parameters:
            tty_device (str): The tty device to open (e.g., "/dev/ttyUSB1").
        """
        try:
            print(f"Opening terminal for {tty_device}...")
            subprocess.Popen(['x-terminal-emulator', '-e', f'sudo minicom -D {tty_device}'])
            print(f"Minicom started for {tty_device}.")
        except Exception as e:
            print(f"Error opening terminal for {tty_device}: {e}")


    def setup(self):
        """
        Setup the GPS module by sending initialization commands via the setup port.
        """
        # Kill all processes more aggressively
        try:
            # Kill ModemManager if it's running
            os.system("sudo systemctl stop ModemManager")
            
            # Kill using fuser
            os.system(f"sudo fuser -k {self.setup_port}")
            
            # Additional kill using lsof
            os.system(f"sudo lsof {self.setup_port} | awk 'NR!=1 {{print $2}}' | xargs -r sudo kill -9")
            
            # Wait longer for processes to be killed
            time.sleep(3)
            
            # Check if port is really free
            result = os.popen(f"sudo fuser {self.setup_port}").read().strip()
            if result:
                raise Exception(f"Port {self.setup_port} is still busy after killing processes")
                
            # Try to open port directly first
            self.open_tty_in_terminal(self.setup_port)
            #self.open_tty_in_terminal(self.gps_port)
            self.ser2 = serial.Serial(self.setup_port, self.baudrate)
            print(f"{self.setup_port} Opened.")
            self.ser2.write('AT+QGPS=1\r'.encode())
            print("Sent: AT+QGPS=1")
            time.sleep(1)  # Wait for command to process
            self.ser2.close()
            print(f"{self.setup_port} Closed.")
            
        except Exception as e:
            print(f"Error in setup: {e}")
            raise


    def open_gps_port(self):
        """
        Open the GPS port for reading data.
        """
        try:
            # Kill any existing processes
            os.system(f"sudo fuser -k {self.gps_port}")
            time.sleep(1)
            
            self.ser1 = serial.Serial(
                port=self.gps_port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,  
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            self.ser1.reset_input_buffer()
            self.ser1.reset_output_buffer()
            
            print(f"{self.gps_port} Opened successfully.")
            
        except Exception as e:
            print(f"Error opening {self.gps_port}: {e}")
            raise

    def close_gps_port(self):
        """
        Close the GPS port if it is open.
        """
        if self.ser1 and self.ser1.is_open:
            self.ser1.close()
            print(f"{self.gps_port} Closed.")


    def _read_from_serial(self):
        """
        Continuously read data from the GPS serial port.
        """
        if not self.ser1 or not self.ser1.is_open:
            self.open_gps_port()
    
        while not self._stop_event.is_set():
            try:
                
                if self.ser1.in_waiting:
                    data = self.ser1.readline().decode("utf-8", errors="ignore")
                    if data: 
                        #print(data.strip())
                        with self.buffer_lock:
                            self.buffer += data
                else:
                    time.sleep(0.1) 
                    
            except serial.SerialException as e:
                print(f"SerialException: {e}")
                
                try:
                    self.close_gps_port()
                    time.sleep(1)
                    self.open_gps_port()
                except Exception as reconnect_error:
                    print(f"Reconnect failed: {reconnect_error}")
                time.sleep(1)
                

    def _process_gps_data(self):
        """
        Process GPS data from the buffer.
        """
        t_previous = time.time()

        while not self._stop_event.is_set():
            with self.buffer_lock:
                # Extract complete lines from the buffer
                lines = self.buffer.split("\n")
                self.buffer = lines.pop()  # Keep the last incomplete line in the buffer

            for line in lines:
                line = line.strip()
                #print(f"Processing line: {line}")

                if line.startswith("$GPRMC"):
                    data = line.split(",")
                    if not data[3] or not data[5]:
                        print("Invalid data received: latitude or longitude is empty")
                        continue

                    try:
                        latitude = float(data[3])
                        longitude = float(data[5])
                        t = time.time()
                    except ValueError:
                        print("Invalid data received: could not convert latitude or longitude to float")
                        continue

                    latitude_direction = data[4]
                    longitude_direction = data[6]

                    if latitude_direction == "S":
                        latitude = -latitude
                    if longitude_direction == "W":
                        longitude = -longitude

                    self.latitude = int(latitude / 100) + (latitude / 100 - int(latitude / 100)) * 100 / 60
                    self.longitude = int(longitude / 100) + (longitude / 100 - int(longitude / 100)) * 100 / 60

                    if self.prev_latitude is not None and self.prev_longitude is not None:
                        distance = haversine(self.prev_longitude, self.prev_latitude, self.longitude, self.latitude)
                        time_elapsed = t - t_previous

                        if time_elapsed > 0:
                            self.velocity = distance / time_elapsed  # Velocity in m/s
                            #print(f"Velocity: {self.velocity:.2f} m/s")
                        else:
                            print("Time elapsed is zero; skipping velocity calculation.")

                    self.prev_latitude = self.latitude
                    self.prev_longitude = self.longitude
                    t_previous = time.time()
            time.sleep(1)              

    def get_velocity(self):
        """
        Retrieve the current velocity.
        Returns:
            float: The current velocity in m/s, or None if it hasn't been calculated yet.
        """
        return self.velocity
    def get_location(self):
        
        return self.latitude, self.longitude

    def start(self):
        """
        Start the GPS reader and begin reading data.
        """
        self.setup()
        self._gps_read_thread.start()
        self._gps_process_thread.start()

    def stop(self):
        """
        Stop all threads and terminate the GPS reader.
        """
        self._stop_event.set()
        self._gps_read_thread.join()
        self._gps_process_thread.join()

    def destroy(self):
        """
        Clean up resources by closing ports and stopping the GPS module.
        """
        self.close_gps_port()


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
    gps_reader = GPSModule()

    try:
        gps_reader.start()
        print("GPS Reader started. Reading data...")
        geolocator = Nominatim(user_agent="geoapi")
        while True:
            velocity = gps_reader.get_velocity()
            latitude, longitude = gps_reader.get_location()
            if latitude is not None and longitude is not None:
                location = geolocator.reverse((latitude, longitude), language="en")  
                print("Lagitude: ", latitude, "Longitude: ", longitude)
                print(location)
            else: 
                print("Waiting for location...")
            if velocity is not None:
                print(f"Current Velocity: {velocity:.2f} m/s")
            else:
                print("Waiting for velocity data...")
            time.sleep(1)

    except KeyboardInterrupt:
        print("KeyboardInterrupt detected. Stopping GPS reader...")
    finally:
        gps_reader.stop()
        gps_reader.destroy()
        print("GPS Reader stopped and resources cleaned up.")


if __name__ == "__main__":
    main()
