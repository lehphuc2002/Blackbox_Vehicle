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
from BNO055_lib import BNO055Sensor
from GPS_lib import GPSModule
import time


def main():
	#  MPU, GPS, client init
	mpu_BNO055 = BNO055Sensor()
	gps_EM06 = GPSModule()
	client1 = init_client();
	try:
		while True:
			#  Read acceleration
			ax, ay, az = mpu_BNO055.read_sensor_data()
			print("Acclerometer", ax,ay,az)
			
			#  Read GPS parameters
			longitude_GPS, latitude_GPS = gps_EM06.read_coordinates()
			if longitude_GPS is not None and latitude_GPS is not None:
				print(f"Longitude: {longitude_GPS}, Latitude: {latitude_GPS}")
			payload1 = get_payload()
			ret = client1.publish("v1/devices/me/telemetry", payload1)
			if ret.rc == paho.MQTT_ERR_SUCCESS:
				print("Publish success")
				print("Here is the latest telemetry")
				print(payload1)
			else:
				print(f"Publish failed with error code: {ret.rc}")
			time.sleep(5)
	except KeyboardInterrupt:
		print("Disconnecting from MQTT Broker...")
		client.disconnect()
		client.loop_stop()
		print("Disconnected")
	
	return 0

if __name__ == '__main__':
	main()
