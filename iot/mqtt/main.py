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
from publish import init_client, get_payload
import paho.mqtt.client as paho
from BNO055_lib import BNO055Sensor
from GPS_lib import GPSModule
import time
import math
from RFID_lib import RFIDReader, create_user_library
global user_info
import distant

def main():
	#  MPU, GPS, client init
	mpu_BNO055 = BNO055Sensor()
	#gps_EM06 = GPSModule()
	client1 = init_client()
	user_library = create_user_library()
	reader = RFIDReader(user_library)
	user_info = dict({'name': 'Jane Smith', 'phone': '987-654-3210'})
	dt = 0
	time_start = time.time()
	vx = 0
	vy = 0
	vz = 0
	v = 0
	# longitude_GPS_t, latitude_GPS_t = gps_EM06.read_coordinates()
	try:
		while True:
			#  Read acceleration
			ax, ay, az = mpu_BNO055.read_sensor_data()
			print("Acclerometer", ax,ay,az)
			
			t = time.time()
			dt = t-time_start
			time_start = t

			vx = vx + round(ax,3)*dt
			vy = vy + round(ay,3)*dt
			vz = vz + round(az,3)*dt
			
			
			#  Read GPS parameters
			# longitude_GPS, latitude_GPS = gps_EM06.read_coordinates()
			# if longitude_GPS is not None and latitude_GPS is not None:
				# print(f"Longitude: {longitude_GPS}, Latitude: {latitude_GPS}")
			#d = haversine(longitude_GPS_t, latitude_GPS_t, longitude_GPS, latitude_GPS)
			#longitude_GPS_t, latitude_GPS_t = longitude_GPS, latitude_GPS
			
			v = math.sqrt(vx*vx +vy*vy +vz*vz)*3.6
			#v_2 = d/dt
			#v = 0.9*v_2 + 0.1*v_1
			print("velocity", v)
			uid = reader.read_id()
			if uid is not None:
				user_info = reader.get_user_info(uid)
				if user_info is not None:
					print(f'User Info: {user_info}')
				else:
					print(f'UID {uid:X} not found in user library.')
			

			payload1 = get_payload(ax, ay, az, v, user_info["name"], user_info["phone"])
			ret = client1.publish("v1/devices/me/telemetry", payload1)
			if ret.rc == paho.MQTT_ERR_SUCCESS:
				print("Publish success")
				print("Here is the latest telemetry")
				print(payload1)
			else:
				print(f"Publish failed with error code: {ret.rc}")
			time.sleep(0.03)
	except KeyboardInterrupt:
		print("Disconnecting from MQTT Broker...")
		client1.disconnect()
		client1.loop_stop()
		print("Disconnected")
		gps_EM06.destroy()
	
	return 0

if __name__ == '__main__':
	main()
