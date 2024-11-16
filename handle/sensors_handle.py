# Thesis/handle/sensors_handle.py
import threading
import time
import math
import json
import queue
from datetime import datetime
import paho.mqtt.client as paho
import os

from sensors.BNO055.BNO055_lib import BNO055Sensor 
from sensors.Temp_DS18B20.DS18B20 import read_temp  

class SensorBuffer:
    def __init__(self, max_size=1000):
        self.buffer = queue.Queue(maxsize=max_size)
        # Set the absolute path for the cache file
        self.cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "handle", "sensor_cache.json")
        self._ensure_cache_directory()
        self.buffer_lock = threading.Lock()  # Add thread safety
        
    def _ensure_cache_directory(self):
        """Ensure the cache directory exists"""
        cache_dir = os.path.dirname(self.cache_file)
        os.makedirs(cache_dir, exist_ok=True)

    def add_data(self, sensor_type, data):
        try:
            entry = {
                'timestamp': datetime.now().isoformat(),
                'sensor_type': sensor_type,
                'data': data
            }
            with self.buffer_lock:
                if self.buffer.full():
                    # Remove oldest entry if buffer is full
                    self.buffer.get()
                self.buffer.put(entry)
                print(f"Buffered data: {entry}")
                self._save_to_cache()
        except Exception as e:
            print(f"Error adding data to buffer: {e}")

    def _save_to_cache(self):
        try:
            with self.buffer_lock:
                # Convert queue to list for serialization while preserving order
                cache_data = []
                temp_buffer = queue.Queue()
                
                while not self.buffer.empty():
                    item = self.buffer.get()
                    cache_data.append(item)
                    temp_buffer.put(item)
                
                # Restore the buffer
                while not temp_buffer.empty():
                    self.buffer.put(temp_buffer.get())

            # Write to file with proper formatting
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                print(f"Cache saved to {self.cache_file}") 
        except Exception as e:
            print(f"Error saving to cache: {e}")

    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    print(f"Loaded cache: {cache_data}")
                    # Sort data by timestamp before loading
                    cache_data.sort(key=lambda x: x['timestamp'])
                    for entry in cache_data:
                        self.add_data(entry['sensor_type'], entry['data'])
            else:
                print("No cache file found, starting with empty buffer")
        except Exception as e:
            print(f"Error loading cache: {e}")

    def get_pending_data(self):
        pending_data = []
        with self.buffer_lock:
            while not self.buffer.empty():
                pending_data.append(self.buffer.get())
        return pending_data
    
    def clear_cache(self):
        """Clear the cache file and buffer"""
        with self.buffer_lock:
            while not self.buffer.empty():
                self.buffer.get()
            if os.path.exists(self.cache_file):
                try:
                    os.remove(self.cache_file)
                except Exception as e:
                    print(f"Error clearing cache file: {e}")


class SensorHandler:
    def __init__(self, mqtt_client, connection_handler):
        # Initialize BNO055 sensor (accelerometer)
        self.bno055 = BNO055Sensor()
        
        # Initialize GPS reader
        # self.gps = GPSReader()  # Uncomment and implement this line
        
        self.running = True  # Flag to control sensor reading loops
        self.last_send_time = time.time()  # Last telemetry send time
        
        # Velocity components
        self.vx, self.vy, self.vz = 0, 0, 0
        
        # Accelerometer thresholds for accident detection
        self.ACC_X_THRESHOLD = 15
        self.ACC_Y_THRESHOLD = 7
        self.ACC_Z_THRESHOLD = 4

        # Use the passed MQTT client instance
        self.mqtt_client = mqtt_client
        
        self.connection_handler = connection_handler
        self.sensor_buffer = SensorBuffer()
        self.sensor_buffer.load_cache()

        # Start data publishing thread
        self.publisher_thread = threading.Thread(target=self._publish_buffered_data, daemon=True)
        self.publisher_thread.start()
        
        self.acc_threshold = 0.1  # Minimum acceleration to consider (m/s²)
        self.velocity_decay = 0.95  # Velocity decay factor
        self.zero_velocity_threshold = 0.1  # Threshold to reset velocity to zero
        self.acc_window_size = 5
        self.acc_window = {'x': [], 'y': [], 'z': []}
        
        self.accel_thread = threading.Thread(target=self.bno055.read_accelerometer_thread, daemon=True)
        self.linear_accel_thread = threading.Thread(target=self.bno055.read_linear_accelerometer_thread, daemon=True)
        self.accel_thread.start()
        self.linear_accel_thread.start()

    def _publish_data(self, payload, sensor_type, priority=False):
        """Attempt to publish data or buffer it if connection is lost"""
        if self.connection_handler.get_connection_status():
            ret = self.mqtt_client.client.publish("v1/devices/me/telemetry", payload)
            if ret.rc == paho.MQTT_ERR_SUCCESS:
                print(f"{sensor_type} data published successfully")
                return True
            else:
                print(f"Failed to publish {sensor_type} data. Error code: {ret.rc}")
                self.sensor_buffer.add_data(sensor_type, payload)
                return False
        else:
            print(f"No connection. Buffering {sensor_type} data...")
            self.sensor_buffer.add_data(sensor_type, payload)
            return False

    def _publish_buffered_data(self):
        """Continuously attempt to publish buffered data when connection is available"""
        while self.running:
            if self.connection_handler.get_connection_status():
                pending_data = self.sensor_buffer.get_pending_data()
                for entry in pending_data:
                    ret = self.mqtt_client.client.publish("v1/devices/me/telemetry", entry['data'])
                    if ret.rc == paho.MQTT_ERR_SUCCESS:
                        print(f"Published buffered {entry['sensor_type']} data from {entry['timestamp']}")
                    else:
                        print(f"Re-buffering failed data: {entry}")
                        # Put back in buffer if publish fails
                        self.sensor_buffer.add_data(entry['sensor_type'], entry['data'])
            time.sleep(5)  # Check every 5 seconds
            
    def moving_average(self, values):
        if not values:
            return 0
        return sum(values) / len(values)

    def read_accelerometer(self):
        """Read accelerometer data, update velocity, and publish telemetry."""
        while self.running:
            ax, ay, az = self.bno055.accel_data
            lax, lay, laz = self.bno055.linear_accel_data
            print("Accelerometer:", ax, ay, az)
            print("Linear Accelerometer:", lax, lay, laz)

            # Update acceleration window
            self.acc_window['x'].append(lax)
            self.acc_window['y'].append(lay)
            self.acc_window['z'].append(laz)
            
            # Keep window size fixed
            if len(self.acc_window['x']) > self.acc_window_size:
                self.acc_window['x'].pop(0)
                self.acc_window['y'].pop(0)
                self.acc_window['z'].pop(0)
                
            # Calculate smoothed acceleration
            smooth_ax = self.moving_average(self.acc_window['x'])
            smooth_ay = self.moving_average(self.acc_window['y'])
            smooth_az = self.moving_average(self.acc_window['z'])
            
            current_time = time.time()
            dt = current_time - self.last_send_time
            self.last_send_time = current_time
            
            # Apply threshold to acceleration
            smooth_ax = 0 if abs(smooth_ax) < self.acc_threshold else smooth_ax
            smooth_ay = 0 if abs(smooth_ay) < self.acc_threshold else smooth_ay
            smooth_az = 0 if abs(smooth_az) < self.acc_threshold else smooth_az

            # Update velocity
            # self.vx += round(lax, 8) * dt
            # self.vy += round(lay, 8) * dt
            # self.vz += round(laz, 8) * dt
            
            # Update velocity with decay
            self.vx = (self.vx + smooth_ax * dt) * self.velocity_decay
            self.vy = (self.vy + smooth_ay * dt) * self.velocity_decay
            self.vz = (self.vz + smooth_az * dt) * self.velocity_decay

            # Reset velocity if it's very small
            if abs(self.vx) < self.zero_velocity_threshold:
                self.vx = 0
            if abs(self.vy) < self.zero_velocity_threshold:
                self.vy = 0
            if abs(self.vz) < self.zero_velocity_threshold:
                self.vz = 0
            
            velocity = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2) * 3.6  # Convert to km/h
            print("Velocity real is:", velocity)

            # Check for potential accidents
            if any(abs(a) > threshold for a, threshold in zip((ax, ay, az),
                (self.ACC_X_THRESHOLD, self.ACC_Y_THRESHOLD, self.ACC_Z_THRESHOLD))):
                status = 'Warning Accident'
                payload = self.mqtt_client.create_payload_motion_data(ax, ay, az, velocity, status)
                self._publish_data(payload, "accelerometer", priority=True)

            # Publish telemetry data every 3 seconds
            if current_time - self.last_send_time >= 3:
                status = "Normal"  # Replace with your status logic
                payload = self.mqtt_client.create_payload_motion_data(ax, ay, az, velocity, status)
                self._publish_data(payload, "accelerometer")
                self.last_send_time = current_time  # Update last send time

            threading.Event().wait(0.015)  # Short delay (~66Hz loop)

    def read_temperature(self):
        """Continuously read temperature data and publish it."""
        while self.running:
            try:
                temp_c, temp_f = read_temp()  # Use the imported function
                print(f'Temperature: {temp_c:.2f} °C, {temp_f:.2f} °F')
                
                # MQTT publish payload for temperature
                payload = self.mqtt_client.create_payload_temp(temp_c)
                # ret = self.mqtt_client.publish(payload)
                # if ret.rc == paho.MQTT_ERR_SUCCESS:
                #     print("Temperature data published successfully.")
                # else:
                #     print(f"Failed to publish temperature data. Error code: {ret.rc}")
                self._publish_data(payload, "temperature")
                
            except Exception as e:
                print(f"Error reading temperature: {e}")
            
            threading.Event().wait(5)  # Wait 5 seconds before reading again


    def read_gps(self):
        """Continuously read and log GPS data."""
        self.gps.start()  # Make sure your GPS class has this method
        while self.running:
            try:
                latitude, longitude = self.gps.get_current_location()
                payload = self.mqtt_client.create_payload_gps(longitude, latitude)
                # ret = self.mqtt_client.publish(payload)  # Publish GPS data
                # print("GPS data published successfully" if ret.rc == paho.MQTT_ERR_SUCCESS 
                #           else f"Failed with error code: {ret.rc}")
                self._publish_data(payload, "gps")
            except Exception as e:
                print(f"Error reading GPS: {e}")
            print(f"Latitude: {latitude}, Longitude: {longitude}")
            threading.Event().wait(2)  # Wait 2 seconds between GPS readings

    def cleanup(self):
        """Clean up and stop sensors."""
        self.running = False
        self.bno055.stop_threads()  # Stop accelerometer threads
        self.accel_thread.join(timeout=1)
        self.linear_accel_thread.join(timeout=1)
        
        if hasattr(self, 'gps'):
            self.gps.stop()  # Ensure the GPS is stopped properly
            self.gps.destroy()  # Free GPS resources if applicable
            print("Cleaned up GPS resources.")
            
        self.publisher_thread.join(timeout=1)
        print("Sensor handler cleaned up")
