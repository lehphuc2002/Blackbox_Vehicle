#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  main.py
#  
#  Copyright 2024  <pi@raspberrypi>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from publish import init_client, get_payload_test, ACCESS_TOKEN1, ACCESS_TOKEN2,ACCESS_TOKEN3, send_data_test, get_payload,ACC_X_THRESHOLD,ACC_Y_THRESHOLD ,ACC_Z_THRESHOLD, haversine, start_time_latency
import paho.mqtt.client as paho
from BNO_055.BNO055_lib import BNO055Sensor
from GPS.GPS_lib import GPSReader
import time
import math
from RFID.RFID_lib import RFIDReader, create_user_library
global user_info
import serial
from datetime import datetime
import threading
import os
import json
import publish_test

def start_recording(filename):
	print("start record")
	os.system(f"rpicam-vid -t 3000s -o /home/pi/Videos{filename}")
	time.sleep(2)  # Start recording


def stop_recording():
	print("Stop record")
	os.system("sudo pkill rpicam-vid")
    
def main():
	#  MPU, GPS, client init
	global status, start_time_latency
	print("Connect to internet or reset module 4G for system")
	#time.sleep(60)
	
	mpu_BNO055 = BNO055Sensor()
	gps = GPSReader()
	client1 = init_client(ACCESS_TOKEN2)
	global ser1
	ser1 = serial.Serial("/dev/ttyUSB1", 115200)
	user_library = create_user_library()

	reader = RFIDReader(user_library)
	time_lt = time.time()
	user_info = dict({'name': 'Chua Quet The', 'phone': 'None'})
	dt = 0
	d_t = 1
	last_send_time = time.time()
	vx = 0
	vy = 0
	vz = 0
	v = 0
	acc_offset = mpu_BNO055.accel_calib()
	

	try:
		
		gps.start()
		now = datetime.now()
		filename = now.strftime("%Y%m%d_%H%M%S.h264")

    # Create and start the recording thread
		recording_thread = threading.Thread(target=start_recording, args=(filename,))
		recording_thread.start()
		longitude_GPS_t, latitude_GPS_t = gps.get_current_location()
		print("Recording started")
		time.sleep(2)
		while True:
			#  Read acceleration
			ax, ay, az = mpu_BNO055.read_sensor_data()
			
			ax = ax - acc_offset[0]
			ay = ay - acc_offset[1]
			az = az - acc_offset[2]
			print("Acclerometer", ax,ay,az)
			status = 'Normal'
			current_time = time.time()
			dt = current_time - last_send_time


			vx = vx + round(ax,0)*dt
			vy = vy + round(ay,0)*dt
			vz = vz + round(az,0)*dt
			
			v_1 = math.sqrt(vx*vx +vy*vy +vz*vz)*3.6
			v = v_1
			#  Read GPS parameters
			latitude_GPS, longitude_GPS = gps.get_current_location()
			print(f"Longitude: {longitude_GPS}, Latitude: {latitude_GPS}")
			# if longitude_GPS is not None and latitude_GPS is not None and longitude_GPS_t is not None and latitude_GPS_t is not None :
				# time_t = time.time()
				# d_t = time_t - time_lt
				# d = haversine(longitude_GPS_t, latitude_GPS_t, longitude_GPS, latitude_GPS)
				# v_2 = d/d_t
				# time_lt = time_t
				# v = v_2/3.6
				
			if v > 90:
				status = 'Over Speed'
			
			print("velocity", v)
			uid = reader.read_id()
			if uid is not None:
				user_info = reader.get_user_info(uid)
				if user_info is not None:
					print(f'User Info: {user_info}')
				else:
					print(f'UID {uid:X} not found in user library.')

			
			
			
			if ax > ACC_X_THRESHOLD or ay > ACC_Y_THRESHOLD or az > ACC_Z_THRESHOLD:
				status = 'Warning Accident'
			#	payload1 = get_payload_test(ax, ay, az, speed, status)
				ret = client1.publish("v1/devices/me/telemetry", payload1)
				if ret.rc == paho.MQTT_ERR_SUCCESS:
					print("Immediate alert published")
					print(payload1)
				else:
					print(f"Immediate alert failed with error code: {ret.rc}")
					
				rpc_request = {'method': 'getCurrentTime', 'params': {} }
				publish_test.start_time_latency = time.time()
				request_id = 1 
				client1.publish('v1/devices/me/rpc/request/' + str(request_id), json.dumps(rpc_request))
                #~~~~~###################### end test latency ----	
			# Doi khoang 3s moi gui
			if current_time - last_send_time >= 3:
			#	payload1 = get_payload_test(ax, ay, az, speed, status)
				
				if longitude_GPS is not None and latitude_GPS is not None and longitude_GPS_t is not None and latitude_GPS_t is not None :
					d_t = current_time - last_send_time
					d = haversine(longitude_GPS_t, latitude_GPS_t, longitude_GPS, latitude_GPS)
					v_2 = d/d_t
					v = v_2*3.6
				longitude_GPS_t, latitude_GPS_t = longitude_GPS, latitude_GPS
				payload1 = get_payload(ax, ay, az, v, user_info["name"], user_info["phone"],longitude_GPS , latitude_GPS, status)
				ret = client1.publish("v1/devices/me/telemetry", payload1)
				if ret.rc == paho.MQTT_ERR_SUCCESS:
					print("Regular data published")
					print(payload1)
				else:
					print(f"Regular data failed with error code: {ret.rc}")
				rpc_request = {'method': 'getCurrentTime', 'params': {} }
				publish_test.start_time_latency = time.time()
				request_id = 1 
				client1.publish('v1/devices/me/rpc/request/' + str(request_id), json.dumps(rpc_request))
				last_send_time = current_time
				
			# if ret.rc == paho.MQTT_ERR_SUCCESS:
				# print("Publish success")
				# print("Here is the latest telemetry")
				# print(payload1)
			# else:
				# print(f"Publish failed with error code: {ret.rc}")
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
	
	return 0

if __name__ == '__main__':
	main()
