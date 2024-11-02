import os
import time
import math
import json
import threading
import serial
import paho.mqtt.client as paho

from datetime import datetime
from sensors.BNO055.BNO055_lib import BNO055Sensor
from sensors.GPS.GPS_EM06 import GPSReader
from sensors.RFID.rfid_reader_lib import RFIDReader, create_user_library
from sensors.Temp_DS18B20.DS18B20 import read_temp
from iot.mqtt.publish_not_clean import (
    init_client, get_payload_test, ACCESS_TOKEN2, 
    get_payload, ACC_X_THRESHOLD, ACC_Y_THRESHOLD, ACC_Z_THRESHOLD, 
    haversine
)

# Initialize global variables
vx, vy, vz = 0, 0, 0
last_send_time = time.time()
acc_offset = None
user_info = {'name': 'None User', 'phone': 'None'}
status = 'Normal'

# Define timer variables
acc_timer = None
telemetry_timer = None

def start_recording(filename):
    """Starts video recording using rpicam."""
    print("Starting recording")
    os.system(f"rpicam-vid -t 3000s -o /home/pi/Videos/{filename}")
    time.sleep(2)

def stop_recording():
    """Stops video recording."""
    print("Stopping recording")
    os.system("sudo pkill rpicam-vid")

def read_accelerometer(mpu_BNO055, client1):
    """Read accelerometer data and update velocity."""
    global vx, vy, vz, status, acc_timer, last_send_time, user_info

    ax, ay, az = mpu_BNO055.read_sensor_data()
    ax -= acc_offset[0]
    ay -= acc_offset[1]
    az -= acc_offset[2]
    print("Accelerometer:", ax, ay, az)

    status = 'Normal'
    current_time = time.time()
    dt = current_time - last_send_time

    # Update velocity
    vx += round(ax, 0) * dt
    vy += round(ay, 0) * dt
    vz += round(az, 0) * dt
    velocity = math.sqrt(vx**2 + vy**2 + vz**2) * 3.6
    print("Velocity:", velocity)

    # Check for potential accidents
    if any(abs(a) > threshold for a, threshold in zip((ax, ay, az), (ACC_X_THRESHOLD, ACC_Y_THRESHOLD, ACC_Z_THRESHOLD))):
        status = 'Warning Accident'
        payload1 = get_payload_test(ax, ay, az, velocity, status)
        ret = client1.publish("v1/devices/me/telemetry", payload1)
        print("Immediate alert published" if ret.rc == paho.MQTT_ERR_SUCCESS else f"Failed with error code: {ret.rc}")

        rpc_request = {'method': 'getCurrentTime', 'params': {}}
        publish_test.start_time_latency = time.time()
        client1.publish(f'v1/devices/me/rpc/request/1', json.dumps(rpc_request))

    # Schedule next accelerometer reading
    acc_timer = threading.Timer(0.1, read_accelerometer, args=(mpu_BNO055, client1))
    acc_timer.start()

def publish_telemetry(mpu_BNO055, gps, client1):
    """Publish telemetry data every 3 seconds."""
    global last_send_time, telemetry_timer, user_info

    current_time = time.time()

    # Send regular data every 3 seconds
    if current_time - last_send_time >= 3:
        ax, ay, az = mpu_BNO055.read_sensor_data()
        ax -= acc_offset[0]
        ay -= acc_offset[1]
        az -= acc_offset[2]
        
        # Read GPS data
        latitude_GPS, longitude_GPS = gps.get_current_location()
        print(f"Longitude: {longitude_GPS}, Latitude: {latitude_GPS}")

        # Read temperature data from the DS18B20 sensor
        temperature_celsius = read_temp()[0]
        print(f'Temperature: {temperature_celsius:.2f} °C')

        payload = get_payload(ax, ay, az, 0, user_info["name"], user_info["phone"], longitude_GPS, latitude_GPS, status, temperature_celsius)
        ret = client1.publish("v1/devices/me/telemetry", payload)
        print("Regular data published" if ret.rc == paho.MQTT_ERR_SUCCESS else f"Failed with error code: {ret.rc}")

        last_send_time = current_time

    # Schedule the next telemetry publish
    telemetry_timer = threading.Timer(3, publish_telemetry, args=(mpu_BNO055, gps, client1))
    telemetry_timer.start()

def main():
    """Main function to read sensor data, record video, and send telemetry."""
    global acc_offset

    print("Connect to internet or reset 4G module for system")

    # Initialize sensor and MQTT client
    mpu_BNO055 = BNO055Sensor()
    gps = GPSReader()
    client1 = init_client(ACCESS_TOKEN2)
    ser1 = serial.Serial("/dev/ttyUSB1", 115200)
    user_library = create_user_library()
    reader = RFIDReader(user_library)

    # Initial state
    acc_offset = mpu_BNO055.accel_calib()

    try:
        gps.start()
        now = datetime.now()
        filename = now.strftime("%Y%m%d_%H%M%S.h264")

        # Start video recording in a separate thread
        recording_thread = threading.Thread(target=start_recording, args=(filename,))
        recording_thread.start()

        # Start accelerometer and telemetry timers
        read_accelerometer(mpu_BNO055, client1)
        publish_telemetry(mpu_BNO055, gps, client1)

    except KeyboardInterrupt:
        print("Disconnecting from MQTT Broker...")
        client1.disconnect()
        client1.loop_stop()
        print("Disconnected")
        gps.stop()
        gps.destroy()
        stop_recording()
        print("Program terminated.")

if __name__ == '__main__':
    main()
