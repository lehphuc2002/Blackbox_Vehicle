import random as rnd
import time
import json
import paho.mqtt.client as paho
from datetime import datetime
import math

ACCESS_TOKEN1 = 'CAR1_TOKEN'   #mercedes
ACCESS_TOKEN2 = 'CAR2_TOKEN'   #toyota
ACCESS_TOKEN3 = 'CAR3_TOKEN' 
ACC_X_THRESHOLD = 15
ACC_Y_THRESHOLD = 7
ACC_Z_THRESHOLD = 4
interval = 3 
status = 'Normal'
type_car = 'Mercedes'
broker = '0.tcp.ap.ngrok.io'
port = 13834
#broker = '192.168.1.4'
#port = 1883
start_time_latency = None
# longitude_GPS = 106.65829755
# latitude_GPS = 10.771835167
speed = 10
ax, ay, az = 0, 0, 0  

def on_publish(client, userdata, result):
	print("Data published to ThingsBoard")

def on_connect(client, userdata, flags, rc):
	if rc == 0:
		print("Connected to MQTT Broker!")
		client.subscribe('v1/devices/me/rpc/response/+') 
	else:
		print(f"Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
	global start_time_latency
	end_time_latency = time.time()
	latency = end_time_latency - start_time_latency
	print("Received response from ThingsBoard")
	print("Latency: {:.3f} ms".format(latency * 1000))
	print("Message received:", msg.payload.decode())

def on_log(client, userdata, level, buf):
	print("log:", buf)

def get_RFID_name():
	name_user = "Le Huu Phuc"
	return name_user

def get_RFID_phone_number():
	return rnd.choice(["+84776544745", "+84919555999"])

def get_Acclerometion_X():
	return round(rnd.uniform(0, 50), 2)

def get_Acclerometion_Y():
	return round(rnd.uniform(0, 30), 2)

def get_Acclerometion_Z():
	return round(rnd.uniform(20, 120), 2)

def get_speed():
	return round(rnd.uniform(20, 120), 2)

def get_payload_test(ax, ay, az, speed, status):
	now = datetime.now()
	timestamp = now.strftime("%H:%M:%S:%f")[:-3]
	payload = {
		'Name': get_RFID_name(),
		'Phone number': get_RFID_phone_number(),
		'Acclerometion X': ax,
		'Acclerometion Y': ay,
		'Acclerometion Z': az,
		'Speed': speed,
		'Timestamp': timestamp,
		'Longitude': longitude_GPS,
		'Latitude': latitude_GPS,
		'license plates': "74D1-145.15" ,
		'status': status,
		'Company': type_car
	}
	return json.dumps(payload)

def haversine(lon1, lat1, lon2, lat2):
        
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    r = 6371 
    return 1000*c * r

def get_payload( ax,ay,az, vel, name_user, phone_user,longitude_GPS, latitude_GPS, statu):
	#global longitude_GPS, latitude_GPS		
	#latitude_GPS += rnd.uniform(-0.0001, 0.0001)
	#longitude_GPS += rnd.uniform(-0.0001, 0.0001)
	now = datetime.now()
	timestamp = now.strftime("%H:%M:%S:%f")[:-3]  # Format the timestamp as HH:MM:SS:millisecond
	payload = {
		'Name': name_user,
		'Phone number': phone_user,
		'Acclerometion X': ax,
		'Acclerometion Y': ay,
		'Acclerometion Z': az,
		'Speed': vel,
		'Timestamp': timestamp,
		'Longitude': longitude_GPS,
		'Latitude': latitude_GPS,
		'license plates': license_plates ,
		'status': statu,
		'Company': type_car
	}
	return json.dumps(payload)

def init_client(token):
	global type_car, license_plates
	client = paho.Client()
	client.on_message = on_message
	client.on_publish = on_publish
	client.on_connect = on_connect
	client.on_log = on_log
	client.username_pw_set(token)
	if token == 'CAR1_TOKEN':
		type_car = 'Mercedes'
		license_plates = "59D6666"
	elif token == 'CAR2_TOKEN':
		type_car = 'Toyota'
		license_plates = "74D1-14515"
	elif token == 'CAR3_TOKEN':
		type_car = 'Tesla'
		license_plates = "60D-12345"
	try:
		client.connect(broker, port, keepalive=60)
	except Exception as e:
		print(f"Could not connect to MQTT Broker. Error: {e}")
		exit()

	client.loop_start()
	return client

def send_data(client):
	global longitude_GPS, latitude_GPS
	try:
		while not client.is_connected():
			time.sleep(0.1)
		
		while True:
			current_time = time.time()
			latitude_GPS += rnd.uniform(-0.0001, 0.0001)
			longitude_GPS += rnd.uniform(-0.0001, 0.0001)
			payload1 = get_payload()
			ret = client.publish("v1/devices/me/telemetry", payload1)
			if ret.rc == paho.MQTT_ERR_SUCCESS:
				print("Publish success")
				print("Here is the latest telemetry")
				print(payload1)
			else:
				print(f"Publish failed with error code: {ret.rc}")

			time.sleep(3)
	except KeyboardInterrupt:
		print("Disconnecting from MQTT Broker...")
		client.disconnect()
		client.loop_stop()
		print("Disconnected")

def send_data_test(self, client, accel_x, accel_y, accel_z, vel, name_user, phone_user,longitude_GPS, latitude_GPS ):
	last_send_time = time.time()
	try:
		while not client.is_connected():
			time.sleep(0.1)
			
		while True:
			
			current_time = time.time()
			self.status = 'Normal'

			if vel > 90:
				self.status = 'Over Speed'

			payload1 = get_payload(accel_x, accel_y, accel_z, vel, name_user, phone_user,longitude_GPS, latitude_GPS, self.status)
			
			# Gui ngay khi co thay doi lon ve gia toc
			if accel_x > ACC_X_THRESHOLD or accel_y > ACC_Y_THRESHOLD or accel_z > ACC_Z_THRESHOLD:
				self.status = 'Warning Accident'
			#	payload1 = get_payload_test(ax, ay, az, speed, status)
				ret = client.publish("v1/devices/me/telemetry", payload1)
				if ret.rc == paho.MQTT_ERR_SUCCESS:
					print("Immediate alert published")
					print(payload1)
				else:
					print(f"Immediate alert failed with error code: {ret.rc}")
			
			# Doi khoang 3s moi gui
			if current_time - last_send_time >= 3:
			#	payload1 = get_payload_test(ax, ay, az, speed, status)
				ret = client.publish("v1/devices/me/telemetry", payload1)
				if ret.rc == paho.MQTT_ERR_SUCCESS:
					print("Regular data published")
					print(payload1)
				else:
					print(f"Regular data failed with error code: {ret.rc}")
				last_send_time = current_time
			time.sleep(0.1)
	except KeyboardInterrupt:
		print("Disconnecting from MQTT Broker...")
		client.disconnect()
		client.loop_stop()
		print("Disconnected")

if __name__ == "__main__":
	client1 = init_client(ACCESS_TOKEN2)
	send_data_test(client1)
