import os
import time
import math
import json
import threading
import serial
from datetime import datetime

import paho.mqtt.client as paho

from publish import (
	init_client, get_payload_test, ACCESS_TOKEN2, 
	get_payload, ACC_X_THRESHOLD, ACC_Y_THRESHOLD, ACC_Z_THRESHOLD, 
	haversine
)
from BNO055_lib import BNO055Sensor
from GPS_lib import GPSReader
from RFID_lib import RFIDReader, create_user_library
import publish_test

global user_info

def start_recording(filename):
	"""Starts video recording using rpicam."""
	print("Starting recording")
	os.system(f"rpicam-vid -t 3000s -o /home/pi/Videos{filename}")
	time.sleep(2)

def stop_recording():
	"""Stops video recording."""
	print("Stopping recording")
	os.system("sudo pkill rpicam-vid")

def main():
	"""Main function to read sensor data, record video, and send telemetry."""
	global status, start_time_latency, ser1, user_info
	print("Connect to internet or reset 4G module for system")

	# Initialize sensor and MQTT client
	mpu_BNO055 = BNO055Sensor()
	gps = GPSReader()
	client1 = init_client(ACCESS_TOKEN2)
	ser1 = serial.Serial("/dev/ttyUSB1", 115200)
	user_library = create_user_library()
	reader = RFIDReader(user_library)

	time_lt = time.time()
	user_info = {'name': 'Chua Quet The', 'phone': 'None'}
	last_send_time = time.time()
	vx, vy, vz = 0, 0, 0
	acc_offset = mpu_BNO055.accel_calib()

	try:
		gps.start()
		now = datetime.now()
		filename = now.strftime("%Y%m%d_%H%M%S.h264")

		# Start video recording in a separate thread
		recording_thread = threading.Thread(target=start_recording, args=(filename,))
		recording_thread.start()

		longitude_GPS_t, latitude_GPS_t = gps.get_current_location()
		print("Recording started")
		time.sleep(2)

		while True:
			# Read acceleration
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

			# Read GPS data
			latitude_GPS, longitude_GPS = gps.get_current_location()
			print(f"Longitude: {longitude_GPS}, Latitude: {latitude_GPS}")

			if velocity > 90:
				status = 'Over Speed'

			# Read RFID data
			uid = reader.read_id()
			if uid:
				user_info = reader.get_user_info(uid)
				if user_info:
					print(f'User Info: {user_info}')
				else:
					print(f'UID {uid:X} not found in user library.')

			# Check for potential accidents
			if any(abs(a) > threshold for a, threshold in zip((ax, ay, az), (ACC_X_THRESHOLD, ACC_Y_THRESHOLD, ACC_Z_THRESHOLD))):
				status = 'Warning Accident'
				payload1 = get_payload_test(ax, ay, az, velocity, status)
				ret = client1.publish("v1/devices/me/telemetry", payload1)
				print("Immediate alert published" if ret.rc == paho.MQTT_ERR_SUCCESS else f"Failed with error code: {ret.rc}")

				rpc_request = {'method': 'getCurrentTime', 'params': {}}
				publish_test.start_time_latency = time.time()
				client1.publish(f'v1/devices/me/rpc/request/1', json.dumps(rpc_request))

			# Send regular data every 3 seconds
			if current_time - last_send_time >= 3:
				if all([longitude_GPS, latitude_GPS, longitude_GPS_t, latitude_GPS_t]):
					d = haversine(longitude_GPS_t, latitude_GPS_t, longitude_GPS, latitude_GPS)
					velocity = (d / (current_time - last_send_time)) * 3.6

				longitude_GPS_t, latitude_GPS_t = longitude_GPS, latitude_GPS
				payload1 = get_payload(ax, ay, az, velocity, user_info["name"], user_info["phone"], longitude_GPS, latitude_GPS, status)
				ret = client1.publish("v1/devices/me/telemetry", payload1)
				print("Regular data published" if ret.rc == paho.MQTT_ERR_SUCCESS else f"Failed with error code: {ret.rc}")

				rpc_request = {'method': 'getCurrentTime', 'params': {}}
				publish_test.start_time_latency = time.time()
				client1.publish(f'v1/devices/me/rpc/request/1', json.dumps(rpc_request))
				last_send_time = current_time

			time.sleep(0.1)

	except KeyboardInterrupt:
		print("Disconnecting from MQTT Broker...")
		client1.disconnect()
		client1.loop_stop()
		print("Disconnected")
		gps.stop()
		gps.destroy()
		print("Program terminated.")
		stop_recording()

if __name__ == '__main__':
	main()
