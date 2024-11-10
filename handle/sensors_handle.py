# handle/sensors_handle.py
import threading
import time
import math
import paho.mqtt.client as paho

from sensors.Temp_DS18B20.DS18B20 import read_temp  


class SensorHandler:
    def __init__(self, mqtt_client):
        # Initialize BNO055 sensor (accelerometer)
        # self.bno055 = BNO055Sensor()  # Uncomment and implement this line
        
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

    def read_accelerometer(self):
        """Read accelerometer data, update velocity, and publish telemetry."""
        global status  # Assuming global variables for status

        while self.running:
            ax, ay, az = self.bno055.read_sensor_data()  # Update according to your sensor

            # Apply calibration offsets if needed
            ax -= self.acc_offset[0]
            ay -= self.acc_offset[1]
            az -= self.acc_offset[2]
            print("Accelerometer:", ax, ay, az)

            current_time = time.time()
            dt = current_time - self.last_send_time

            # Update velocity
            self.vx += round(ax, 0) * dt
            self.vy += round(ay, 0) * dt
            self.vz += round(az, 0) * dt
            velocity = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2) * 3.6  # Convert to km/h
            print("Velocity:", velocity)

            # Check for potential accidents
            if any(abs(a) > threshold for a, threshold in zip((ax, ay, az), 
                (self.ACC_X_THRESHOLD, self.ACC_Y_THRESHOLD, self.ACC_Z_THRESHOLD))):
                status = 'Warning Accident'
                payload = self.mqtt_client.create_payload_motion_data(ax, ay, az, velocity, status)
                ret = self.mqtt_client.publish(payload)  # Publish alert payload immediately
                print("Immediate alert published" if ret.rc == paho.MQTT_ERR_SUCCESS 
                      else f"Failed with error code: {ret.rc}")

            # Publish telemetry data every 3 seconds
            if current_time - self.last_send_time >= 3:
                payload = self.mqtt_client.create_payload_motion_data(ax, ay, az, velocity, status)
                ret = self.mqtt_client.publish(payload)  # Publish regular telemetry data
                print("Regular data published successfully" if ret.rc == paho.MQTT_ERR_SUCCESS 
                      else f"Failed with error code: {ret.rc}")

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
                ret = self.mqtt_client.publish(payload)
                if ret.rc == paho.MQTT_ERR_SUCCESS:
                    print("Temperature data published successfully.")
                else:
                    print(f"Failed to publish temperature data. Error code: {ret.rc}")
                
                threading.Event().wait(5)  # Wait 5 seconds before reading again
            except Exception as e:
                print(f"Error reading temperature: {e}")

    def read_gps(self):
        """Continuously read and log GPS data."""
        self.gps.start()  # Make sure your GPS class has this method
        while self.running:
            latitude, longitude = self.gps.get_current_location()
            payload = self.mqtt_client.create_payload_gps(longitude, latitude)
            ret = self.mqtt_client.publish(payload)  # Publish GPS data
            print("GPS data published successfully" if ret.rc == paho.MQTT_ERR_SUCCESS 
                      else f"Failed with error code: {ret.rc}")
            print(f"Latitude: {latitude}, Longitude: {longitude}")
            threading.Event().wait(2)  # Wait 2 seconds between GPS readings

    def cleanup(self):
        """Clean up and stop sensors."""
        self.running = False
        if hasattr(self, 'gps'):
            self.gps.stop()  # Ensure the GPS is stopped properly
            self.gps.destroy()  # Free GPS resources if applicable
            print("Cleaned up GPS resources.")
