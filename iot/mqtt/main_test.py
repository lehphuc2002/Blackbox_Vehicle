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

from publish_test import init_client, get_payload_test, ACCESS_TOKEN1, ACCESS_TOKEN2,ACCESS_TOKEN3, send_data_test, get_payload,ACC_X_THRESHOLD,ACC_Y_THRESHOLD ,ACC_Z_THRESHOLD, haversine
import paho.mqtt.client as paho
from BNO055_lib import BNO055Sensor
from GPS_lib import GPSReader
import time
import math
from RFID_lib import RFIDReader, create_user_library
global user_info
import distant
import serial

def main():
	#  MPU, GPS, client init
	global status
	mpu_BNO055 = BNO055Sensor()
	gps = GPSReader()
	client1 = init_client(ACCESS_TOKEN2)
	global ser1
	ser1 = serial.Serial("/dev/ttyUSB1", 115200)
	user_library = create_user_library()

	reader = RFIDReader(user_library)

	user_info = dict({'name': 'Chua Quet The', 'phone': 'None'})
	dt = 0
	last_send_time = time.time()
	vx = 0
	vy = 0
	vz = 0
	v = 0
	acc_offset = mpu_BNO055.accel_calib()
	longitude_GPS_t, latitude_GPS_t = None, None

	try:
		gps.start()
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


			vx = vx + round(ax,1)*dt
			vy = vy + round(ay,1)*dt
			vz = vz + round(az,1)*dt
			
			v_1 = math.sqrt(vx*vx +vy*vy +vz*vz)*3.6
			#v = v_1
			#  Read GPS parameters
			latitude_GPS, longitude_GPS = gps.get_current_location()
			print(f"Longitude: {longitude_GPS}, Latitude: {latitude_GPS}")
			if longitude_GPS is not None and latitude_GPS is not None and longitude_GPS_t is not None and latitude_GPS_t is not None :
				d = haversine(longitude_GPS_t, latitude_GPS_t, longitude_GPS, latitude_GPS)
				v_2 = d/dt
				v = 0.999999*v_2 + 0.000001*v_1
				
			longitude_GPS_t, latitude_GPS_t = longitude_GPS, latitude_GPS	
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

			
			payload1 = get_payload(ax, ay, az, v, user_info["name"], user_info["phone"],longitude_GPS , latitude_GPS, status)
			
			if ax > ACC_X_THRESHOLD or ay > ACC_Y_THRESHOLD or az > ACC_Z_THRESHOLD:
				status = 'Warning Accident'
			#	payload1 = get_payload_test(ax, ay, az, speed, status)
				ret = client1.publish("v1/devices/me/telemetry", payload1)
				if ret.rc == paho.MQTT_ERR_SUCCESS:
					print("Immediate alert published")
					print(payload1)
				else:
					print(f"Immediate alert failed with error code: {ret.rc}")
			
			# Doi khoang 3s moi gui
			if current_time - last_send_time >= 3:
			#	payload1 = get_payload_test(ax, ay, az, speed, status)
				ret = client1.publish("v1/devices/me/telemetry", payload1)
				if ret.rc == paho.MQTT_ERR_SUCCESS:
					print("Regular data published")
					print(payload1)
				else:
					print(f"Regular data failed with error code: {ret.rc}")
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
	
	return 0

if __name__ == '__main__':
	main()
