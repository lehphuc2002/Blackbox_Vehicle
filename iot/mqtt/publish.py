import random as rnd
import time
import json
import paho.mqtt.client as paho
from datetime import datetime

ACCESS_TOKEN1 = 'CAR1_TOKEN'
broker = '0.tcp.ap.ngrok.io'
port = 11728
#broker = '192.168.1.4'
#port = 1883
longitude_GPS = 106.65829755
latitude_GPS = 10.771835167

def on_publish(client, userdata, result):
	print("Data published to ThingsBoard")

def on_connect(client, userdata, flags, rc):
	if rc == 0:
		print("Connected to MQTT Broker!")
	else:
		print("Failed to connect, return code %d\n", rc)

def on_log(client, userdata, level, buf):
	print("log: ", buf)

def get_temperature():
	return round(rnd.uniform(-50, 50), 2)

def get_longitude_GPS():
	return longitude_GPS
	
def get_latitude_GPS():
	return latitude_GPS

def get_humidity():
	return round(rnd.uniform(0, 100),2)

def get_wind_direction():
	return round(rnd.randrange(0, 360),2)

def get_payload():
	now = datetime.now()
	timestamp = now.strftime("%H:%M:%S:%f")[:-3]  # Format the timestamp as HH:MM:SS:millisecond
	payload = {
		'Temperature': get_temperature(),
		'Humidity': get_humidity(),
		'Wind direction': get_wind_direction(),
		'Timestamp': timestamp,
		'Longitude': longitude_GPS,
		'Latitude': latitude_GPS
	}
	return json.dumps(payload)


def init_client():
	client = paho.Client()
	client.on_publish = on_publish
	client.on_connect = on_connect
	client.on_log = on_log
	client.username_pw_set(ACCESS_TOKEN1)
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
			time.sleep(5)
	except KeyboardInterrupt:
		print("Disconnecting from MQTT Broker...")
		client.disconnect()
		client.loop_stop()
		print("Disconnected")

if __name__ == "__main__":
	client1 = init_client()
	send_data(client1)

