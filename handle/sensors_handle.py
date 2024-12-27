# Thesis/handle/sensors_handle.py
import threading
import time
import math
import json
import queue
import RPi.GPIO as GPIO
import paho.mqtt.client as paho
import os
from datetime import datetime
from geopy.geocoders import Nominatim
from unidecode import unidecode

from sensors.BNO055.BNO055_lib import BNO055Sensor 
from sensors.Temp_DS18B20.DS18B20 import read_temp
from sensors.MQ3_ADS1115.MQ3_ADS115 import MQ3Sensor
from sensors.GPS.GPS_lib import GPSModule
# from sensors.GPS.gps_simulator import GPSSimulator # Simulate GPS

class SensorBuffer:
    def __init__(self, max_size=1000, max_cache_size=100):
        self.buffer = queue.Queue(maxsize=max_size)
        self.max_cache_size = max_cache_size
        # Get absolute path and ensure it's writable
        try:
            current_file_path = os.path.abspath(__file__)
            parent_dir = os.path.dirname(os.path.dirname(current_file_path))
            self.cache_dir = os.path.join(parent_dir, "handle")
            self.cache_file = os.path.join(self.cache_dir, "sensor_cache.json")
            
            # Create directory if it doesn't exist
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir, exist_ok=True)
                print(f"Created cache directory: {self.cache_dir}")
            
            # Test write permissions
            test_file = os.path.join(self.cache_dir, "test_write.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                print(f"Cache directory is writable: {self.cache_dir}")
            except Exception as e:
                print(f"Cache directory is not writable, using /tmp: {e}")
                self.cache_file = "/tmp/sensor_cache.json"
                
        except Exception as e:
            print(f"Error setting up cache file: {e}")
            self.cache_file = "/tmp/sensor_cache.json"
            
        print(f"Using cache file: {self.cache_file}")
        self.buffer_lock = threading.Lock()
        
    def _ensure_cache_directory(self):
        """Ensure the cache directory exists"""
        cache_dir = os.path.dirname(self.cache_file)
        os.makedirs(cache_dir, exist_ok=True)
        print(f"Cache directory ensured: {cache_dir}")


    def add_data(self, sensor_type, data):
        try:
            entry = {
                'timestamp': datetime.now().isoformat(),
                'sensor_type': sensor_type,
                'data': data
            }
            print(f"Adding data to buffer: {sensor_type}")
            
            # Hold lock only for buffer operations
            with self.buffer_lock:
                if self.buffer.full():
                    self.buffer.get()
                self.buffer.put(entry)
                print(f"Buffered data: {entry}")
            
            # Call save_to_cache outside the lock
            print(f"Calling _save_to_cache...")
            self._save_to_cache()
                
        except Exception as e:
            print(f"Error adding data to buffer: {str(e)}")
            import traceback
            print(f"Traceback:\n{traceback.format_exc()}")

    def _save_to_cache(self):
        print("Starting _save_to_cache method...")
        cache_data = []
        
        # Try to acquire lock with timeout
        print("Attempting to acquire buffer lock...")
        if not self.buffer_lock.acquire(timeout=2):  # 2 second timeout
            print("Could not acquire lock after 2 seconds, aborting save")
            return
            
        try:
            print("Lock acquired, getting data from buffer...")
            temp_buffer = queue.Queue()
            
            # Get all items from buffer
            while not self.buffer.empty():
                item = self.buffer.get()
                cache_data.append(item)
                temp_buffer.put(item)
            
            # Restore buffer
            while not temp_buffer.empty():
                self.buffer.put(temp_buffer.get())
                
        finally:
            self.buffer_lock.release()
            print(f"Lock released. Got {len(cache_data)} items from buffer")
        
        # Skip if no data to save
        if not cache_data:
            print("No data to save, returning")
            return
            
        # Limit cache size
        if len(cache_data) > self.max_cache_size:
            print(f"Limiting cache size from {len(cache_data)} to {self.max_cache_size}")
            cache_data = cache_data[-self.max_cache_size:]
        
        try:
            # Write to temporary file first
            temp_file = f"{self.cache_file}.tmp"
            print(f"Attempting to write to temporary file: {temp_file}")
            
            try:
                with open(temp_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                print(f"Successfully wrote to temporary file")
                
                # If write successful, rename to actual file
                print(f"Attempting to rename {temp_file} to {self.cache_file}")
                os.replace(temp_file, self.cache_file)
                print(f"Successfully saved {len(cache_data)} items to {self.cache_file}")
                
            except Exception as write_error:
                print(f"Error writing to primary cache file: {write_error}")
                # Try fallback location
                fallback_file = "/tmp/sensor_cache.json"
                print(f"Attempting to write to fallback location: {fallback_file}")
                with open(fallback_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                print(f"Successfully saved to fallback location: {fallback_file}")
                
        except Exception as e:
            print(f"Critical error in _save_to_cache: {e}")
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")
            
    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    print(f"Loaded cache: {cache_data}")
                    print("HEHEHEHHE")
                    # Sort data by timestamp before loading
                    cache_data.sort(key=lambda x: x['timestamp'])
                    for entry in cache_data:
                        self.add_data(entry['sensor_type'], entry['data'])
            else:
                print("No cache file found, starting with empty buffer")
                print("hahahahahaahhaha")
        except Exception as e:
            print(f"Error loading cache: {e}")

    def get_pending_data(self):
        pending_data = []
        with self.buffer_lock:
            while not self.buffer.empty():
                pending_data.append(self.buffer.get())
        return pending_data
    
    def remove_published_data(self, published_entries):
        """Remove successfully published entries from the cache file"""
        print(f"Removing {len(published_entries)} published entries from cache")
        try:
            # Read current cache
            current_cache = []
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    current_cache = json.load(f)

            # Create set of published timestamps for efficient lookup
            published_timestamps = {entry['timestamp'] for entry in published_entries}

            # Filter out published entries
            updated_cache = [
                entry for entry in current_cache 
                if entry['timestamp'] not in published_timestamps
            ]

            # Save updated cache
            if len(updated_cache) > 0:
                with open(self.cache_file, 'w') as f:
                    json.dump(updated_cache, f, indent=2)
                print(f"Updated cache file with {len(updated_cache)} remaining entries")
            else:
                # If no entries remain, delete the cache file
                if os.path.exists(self.cache_file):
                    os.remove(self.cache_file)
                print("Cache file deleted as all entries were published")

        except Exception as e:
            print(f"Error removing published data from cache: {e}")
            import traceback
            print(f"Traceback:\n{traceback.format_exc()}")


class SensorHandler:
    def __init__(self, mqtt_client, connection_handler):
        # Initialize BNO055 sensor (accelerometer)
        self.bno055 = BNO055Sensor()
        self.mq3_sensor = MQ3Sensor(adc_channel=0, gain=1, vcc=5.0)
        
        # Initialize GPS reader
        # self.gps = GPSReader()
        
        self.running = True  # Flag to control sensor reading loops
        self.last_send_time = time.time()  # Last telemetry send time
        
        # Velocity components
        self.vx, self.vy, self.vz = 0, 0, 0
        self.velocity = 0 
        self.status = "Normal"
        
        # Accelerometer thresholds for accident detection
        self.ACC_THRESHOLD = 2.0 * 9.8 # remmember changing in camera_gstreamer.py threshold acc

        # Use the passed MQTT client instance
        self.mqtt_client = mqtt_client
        
        self.connection_handler = connection_handler
        self.sensor_buffer = SensorBuffer()
        self.sensor_buffer.load_cache()

        # Start data publishing thread
        self.publisher_thread = threading.Thread(target=self._publish_buffered_data, daemon=True)
        self.publisher_thread.start()
        
        self.acc_threshold = 0.1  # Ignore very small accelerations below 0.1 m/s²
        self.velocity_decay = 0.95  # Reduce velocity by 5% each iteration
        self.zero_velocity_threshold = 0.1  # Threshold to reset velocity to zero
        self.acc_window_size = 5 # Keep track of last 5 acceleration readings
        self.acc_window = {'x': [], 'y': [], 'z': []} # Store acceleration history
        
        self.accel_thread = threading.Thread(target=self.bno055.read_accelerometer_thread, daemon=True)
        self.linear_accel_thread = threading.Thread(target=self.bno055.read_linear_accelerometer_thread, daemon=True)
        self.accel_thread.start()
        self.linear_accel_thread.start()
        
        # self.gps = GPSSimulator()
        self.gps = GPSModule()
        self.gps_thread = threading.Thread(target=self.read_gps, daemon=True)
        self.gps_thread.start()
        print("GPS thread reading at sensors_handle starting done.")

    def _publish_data(self, payload, sensor_type, priority=False):
        """Attempt to publish data or buffer it if connection is lost"""
        if self.connection_handler.get_connection_status():
            ret = self.mqtt_client.client.publish("v1/devices/me/telemetry", payload, qos=0)
            if ret.rc == paho.MQTT_ERR_SUCCESS:
                print(f"{sensor_type} data published successfully")
                return True
            else:
                print(f"Failed to publish {sensor_type} data. Error code: {ret.rc}")
                print(f"Data being buffered: {payload}")
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
                if not pending_data:
                    time.sleep(5)
                    continue

                successfully_published = []
                for entry in pending_data:
                    ret = self.mqtt_client.client.publish("v1/devices/me/telemetry", entry['data'])
                    if ret.rc == paho.MQTT_ERR_SUCCESS:
                        print(f"Published buffered {entry['sensor_type']} data from {entry['timestamp']}")
                        successfully_published.append(entry)
                    else:
                        print(f"Re-buffering failed data: {entry}")
                        # Put back in buffer if publish fails
                        self.sensor_buffer.add_data(entry['sensor_type'], entry['data'])

                # Remove successfully published entries from cache
                if successfully_published:
                    self.sensor_buffer.remove_published_data(successfully_published)

            time.sleep(5)
            
    def moving_average(self, values):
        """Takes a list of values and returns their average. It helps smooth out noisy acceleration readings."""
        if not values:
            return 0
        return sum(values) / len(values)

    def read_accelerometer(self):
        """Read accelerometer data, update velocity, and publish telemetry."""
        last_publish_time = time.time()  # Track the last publish time
        while self.running:
            while self.bno055.accel_data is not None:
                ax, ay, az = self.bno055.accel_data 
                self.acc_detect_accident = math.sqrt(ax**2 + ay**2 + az**2)
                lax, lay, laz = self.bno055.linear_accel_data
                self.acc_sqrt_linear = math.sqrt(lax**2 + lay**2 + laz**2)
                
                if (ax > 100 or ay > 100 or az > 100):
                    continue
                # print("Accelerometer:", ax, ay, az)
                # print("Linear Accelerometer:", lax, lay, laz)

                # Store recent acceleration readings
                self.acc_window['x'].append(lax)
                self.acc_window['y'].append(lay)
                self.acc_window['z'].append(laz)
                
                # Keep only the last 5 readings
                if len(self.acc_window['x']) > self.acc_window_size:
                    self.acc_window['x'].pop(0)
                    self.acc_window['y'].pop(0)
                    self.acc_window['z'].pop(0)
                    
                # Calculate average acceleration from recent readings
                smooth_ax = self.moving_average(self.acc_window['x'])
                smooth_ay = self.moving_average(self.acc_window['y'])
                smooth_az = self.moving_average(self.acc_window['z'])
                
                self.current_time = time.time()
                dt = self.current_time - self.last_send_time
                self.last_send_time = self.current_time
                
                # If acceleration is very small, treat it as zero
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
                    
                ######################## Example ########################
                """
                Let's say sensor reads these accelerations:
                Reading 1: 0.03 m/s²
                Reading 2: -0.02 m/s²
                Reading 3: 0.04 m/s²
                Reading 4: 0.01 m/s²
                Reading 5: -0.03 m/s²
                The moving average would be: (0.03 - 0.02 + 0.04 + 0.01 - 0.03) / 5 = 0.006 m/s²
                Since 0.006 is less than threshold (0.1), it gets set to 0
                This prevents tiny readings from affecting the velocity.
                """
                
                """ 
                WITHOUT DECAY
                Starting velocity = 0 m/s
                Reading tiny acceleration = 0.01 m/s²

                After 1 second: v = 0 + 0.01 = 0.01 m/s
                After 2 seconds: v = 0.01 + 0.01 = 0.02 m/s
                After 3 seconds: v = 0.02 + 0.01 = 0.03 m/s
                ...keeps increasing forever
                
                WITH DECAY
                Starting velocity = 0 m/s
                Reading tiny acceleration = 0.01 m/s²

                After 1 second: v = (0 + 0.01) * 0.95 = 0.0095 m/s
                After 2 seconds: v = (0.0095 + 0.01) * 0.95 = 0.0185 m/s
                After 3 seconds: v = (0.0185 + 0.01) * 0.95 = 0.027 m/s
                Eventually stabilizes instead of increasing forever
                """
                ######################## End Example ########################
                
                # self.velocity = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2) * 3.6  # Convert to km/h
                # print("Velocity real is:", self.velocity)

                # Check for potential accidents
                if self.acc_detect_accident >= self.ACC_THRESHOLD:
                    # payload = self.mqtt_client.create_payload_motion_data(lax, lay, laz, self.velocity, status, self.acc_detect_accident)
                    self.status = "PotentialAccident"
                    payload = self.mqtt_client.create_payload_motion_data(lax, lay, laz, self.velocity, self.status, self.acc_detect_accident)
                    self._publish_data(payload, "accelerometer_detect")

                # Publish telemetry data every ... seconds
                if self.current_time - last_publish_time >= 4:
                    self.status = "Normal"
                    payload = self.mqtt_client.create_payload_motion_data(lax, lay, laz, self.velocity, self.status, self.acc_sqrt_linear)
                    self._publish_data(payload, "accelerometer")
                    # Update the last publish time
                    last_publish_time = self.current_time

                timestamp = time.time()
                readable_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
     
                script_dir = os.path.dirname(os.path.abspath(__file__))
                log_file_path = os.path.join(script_dir, "acc_sensors_handle.txt")
                with open(log_file_path, "a") as log_file:
                    log_file.write(
                        f"{readable_time}: Acceleration={ax}, {ay}, {az}, {lax}, {lay}, {laz}, Velocity is: {self.velocity}, acc_detect_accident is {self.acc_detect_accident}, Status is {self.status} \n"
                    )
         
                threading.Event().wait(0.1)  # Short delay (~66Hz loop)
                # threading.Event().wait(1)  
    def read_temperature(self):
        """Continuously read temperature data and publish it."""
        while self.running:
            try:
                temp_c, temp_f = read_temp()
                print(f'Temperature: {temp_c:.2f} °C, {temp_f:.2f} °F')
                
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
    
    def ring_buzzer(self, duration=0.1):
        """Activate the buzzer for a specified duration."""
        self.BUZZER_PIN = 20
        GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)
            
    def read_alcohol_value(self):
        """Continuously read alcohol data and publish it."""
        last_publish_time = 0
        while self.running:
            try:
                current_time = time.time()
                alcohol_value = self.mq3_sensor.get_concentration()

                if alcohol_value > 50:
                    payload = self.mqtt_client.create_payload_alcohol(round(alcohol_value, 2))
                    self._publish_data(payload, "alcohol")
                    print("Publish alcohol value immediately!")
                    self.ring_buzzer(3)

                if (current_time - last_publish_time) >= 5:
                    payload = self.mqtt_client.create_payload_alcohol(round(alcohol_value, 2))
                    self._publish_data(payload, "alcohol") 
                    print("Publish alcohol value after 5s")
                    last_publish_time = current_time
                    
            except Exception as e:
                print(f"Error reading alcohol: {e}")
            
            threading.Event().wait(1)

    def read_gps(self):
        """Continuously read and log GPS data."""
        try:
            self.gps.start()
            print("GPS Reader started (at sensors_handle.py). Reading data...")
            geolocator = Nominatim(user_agent="geoapi")
            print(f"self.running at sensors_handle.py is {self.running}")
            
            while self.running:
                while self.gps.get_velocity() is not None:
                    try:
                        self.velocity = self.gps.get_velocity()
                        print(f"self.velocity at sensors_handle.py is {self.velocity}")
                        # self.velocity_accident = self.gps.instant_velocity
                        # print(f"self.velocity_accident at sensors_handle.py is {self.velocity_accident}")
                        
                        self.latitude, self.longitude = self.gps.get_location()
                        print(f"self.latitude, self.longitude at sensors_handle.py is {self.latitude}, {self.longitude}")
                        if self.latitude is not None and self.longitude is not None:
                            # location = geolocator.reverse((latitude, longitude), language="en") 
                            geolocator = Nominatim(user_agent="geoapi", timeout=10)
                            locat = geolocator.reverse((self.latitude, self.longitude), language="en")
                            address = locat.address
                            self.address_no_accent = unidecode(address)
                            # location = geolocator.reverse((latitude, longitude), language="en")  
                            print("Lagitude: ", self.latitude, "Longitude: ", self.longitude)
                            print(self.address_no_accent)
                            payload = self.mqtt_client.create_payload_gps(self.longitude, self.latitude, self.velocity)
                            # ret = self.mqtt_client.publish(payload)  # Publish GPS data
                            # print("GPS data published successfully" if ret.rc == paho.MQTT_ERR_SUCCESS 
                            #         else f"Failed with error code: {ret.rc}")
                            self._publish_data(payload, "gps")
                            print(f"GPS - Latitude: {self.latitude}, Longitude: {self.longitude}")
                        else: 
                            print("Waiting for location...")
                        if self.velocity is not None:
                            print(f"Current Velocity: {self.velocity:.2f} km/h")
                        else:
                            print("Waiting for velocity data...")
                    except Exception as e:
                        print(f"Error reading GPS: {e}")
                    
                    threading.Event().wait(1)
                
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected. Stopping GPS reader...")

    def cleanup(self):
        """Clean up and stop sensors."""
        self.running = False
        self.bno055.stop_threads()  # Stop accelerometer threads
        self.accel_thread.join(timeout=1)
        self.linear_accel_thread.join(timeout=1)
        
        if hasattr(self, 'gps'):
            self.gps.stop()  # Ensure the GPS is stopped properly
            self.gps.destroy()  # Free GPS resources if applicable
            self.gps.read_gps.join(timeout=1)
            print("Cleaned up GPS resources.")
            
        self.publisher_thread.join(timeout=1)
        print("Sensor handler cleaned up")
