import random as rnd
import time
import json
import os
import subprocess
import paho.mqtt.client as paho
# import ssl  # For TLS encryption
from datetime import datetime

# Constants
ACCESS_TOKENS = {
	'CAR1': 'CAR1_TOKEN',  # Mercedes
	'CAR2': 'CAR2_TOKEN',  # Toyota
	'CAR3': 'CAR3_TOKEN',  # Tesla
}

# BROKER = '192.168.1.12'
# PORT = 1883
# INTERVAL = 3

BROKER = '192.168.156.125'
PORT = 1883
INTERVAL = 3

# BROKER = 'invite-priorities-commodities-surge.trycloudflare.com'
# PORT = 1883
# INTERVAL = 3

# BROKER = "services-liberty-advantage-im.trycloudflare.com"
# PORT = 443  # The default port for HTTPS (Cloudflare Tunnel uses TLS)
# INTERVAL = 3  # Data publish interval

#BROKER = '192.168.31.222'
#PORT = 1883
#INTERVAL = 3

# BROKER = '0.tcp.ap.ngrok.io'
# PORT = 14282
# INTERVAL = 3

# BROKER = 'f7203bb08fbe0f4761e13ae31b373e28.serveo.net'
# PORT = 443  # Serveo supports SSL
# INTERVAL = 3

class MQTTClient:
	_instance = None  # Singleton instance

	def __new__(cls, token, connection_handler):
		if cls._instance is None:
			cls._instance = super(MQTTClient, cls).__new__(cls)
			cls._instance.client = paho.Client()
			cls._instance.connection_handler = connection_handler  # Store connection handler
			cls._instance.init_client(token)
		return cls._instance

	def init_client(self, token):
		self.client.on_message = self.on_message
		self.client.on_publish = self.on_publish
		self.client.on_connect = self.on_connect
		# self.client.on_disconnect = self.on_disconnect  # Add on_disconnect callback
		self.client.username_pw_set(token)
   		# # Enable TLS encryption for Cloudflare Tunnel
		# self.client.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS)

		# Set car type and license plates based on the token
		if token == ACCESS_TOKENS['CAR1']:
			self.type_car = 'Mercedes'
			self.license_plates = "59Y1-66699"
		elif token == ACCESS_TOKENS['CAR2']:
			self.type_car = 'Toyota'
			self.license_plates = "74D1-14515"
		elif token == ACCESS_TOKENS['CAR3']:
			self.type_car = 'Tesla'
			self.license_plates = "60D-12345"

		try:
			if self.connection_handler.get_connection_status():
				self.client.connect(BROKER, PORT, keepalive=60)
				self.client.loop_start()
			else:
				print("No internet connection. Cannot connect to MQTT Broker.")
		except Exception as e:
			print(f"Could not connect to MQTT Broker. Error: {e}. Check your ThingsBoard IP.")
			exit()

	def on_publish(self, client, userdata, result):
		print("Data published to ThingsBoard")

	def on_connect(self, client, userdata, flags, rc):
		if rc == 0:
			print("Connected to MQTT Broker!")
			client.subscribe('v1/devices/me/rpc/response/+')
		else:
			print(f"Failed to connect, return code {rc}\n")

	def on_message(self, client, userdata, msg):
		print("Received response from ThingsBoard")
		print("Message received:", msg.payload.decode())

	def create_payload(self, ax, ay, az, speed, status):
		now = datetime.now()
		timestamp = now.strftime("%H:%M:%S:%f")[:-3]
		payload = {
			'Accelerometer X': ax,
			'Accelerometer Y': ay,
			'Accelerometer Z': az,
			'Speed': speed,
			'Timestamp': timestamp,
			'Longitude': self.longitude_GPS,
			'Latitude': self.latitude_GPS,
			'License plates': self.license_plates,
			'Status': status,
			'Company': self.type_car
		}
		return json.dumps(payload)

	def publish(self, payload):
		ret = self.client.publish("v1/devices/me/telemetry", payload, qos=0)
		if ret.rc == paho.MQTT_ERR_SUCCESS:
			print("Publish success")
		else:
			print(f"Publish failed with error code: {ret.rc}")
		return ret  # Ensure to return the result

	def send_data(self):
		user = self.get_rfid_user()

		try:
			while True:
				# Gather sensor data
				ax, ay, az = self.get_accelerometer_data()
				speed = self.get_speed()
				status = 'Normal' if speed <= 90 else 'Over Speed'

				# Create and publish the payload
				payload = self.create_payload(ax, ay, az, speed, status)
				self.publish(payload)

				# Send data at intervals
				time.sleep(INTERVAL)

		except KeyboardInterrupt:
			print("Disconnecting from MQTT Broker...")
			self.client.disconnect()
			self.client.loop_stop()
			print("Disconnected")

	def get_rfid_user(self):
		return {
			"name": "Le Huu Phuc",
			"phone": rnd.choice(["+84776544745", "+84919555999"])
		}

	def get_accelerometer_data(self):
		return (
			round(rnd.uniform(0, 50), 2),  # Accelerometer X
			round(rnd.uniform(0, 30), 2),  # Accelerometer Y
			round(rnd.uniform(20, 120), 2)  # Accelerometer Z
		)

	def get_speed(self):
		return round(rnd.uniform(20, 120), 2)

	def create_payload_URL_camera(self, url, link_local_streaming):
		return json.dumps({
      		'URL Camera ': url,
			'URL Stream' : link_local_streaming
        })
  
	def create_payload_accident_signal(self, accident_signal):
		return json.dumps({
			'accident': accident_signal,
		})

	# Keep all original payload creation functions
	def create_payload_motion_data(self, lax, lay, laz, speed, status, acc_sqrt):
		return json.dumps({
			'Accelerometer X': lax,
			'Accelerometer Y': lay,
			'Accelerometer Z': laz,
			'Acc_sqrt': round(acc_sqrt, 2),
			# 'AccLinearX': lax,
			'Speed': speed,
			'status': status
		})

	def create_payload_user_info(self, user):
      # Get the current timestamp in the required format
		timestamp = datetime.now().strftime('%H:%M:%S:%f')[:-3]  # Remove last 3 digits of microseconds to get milliseconds
		return json.dumps({
			'Name': user['name'],
			'Phone number': user['phone_number'],
   			'license plates': self.license_plates,
			'Company': self.type_car,
			'Timestamp': timestamp
		})

	def create_payload_accelerometer(self, ax, ay, az):
		return json.dumps({
			'Accelerometer X': ax,
			'Accelerometer Y': ay,
			'Accelerometer Z': az
		})

	def create_payload_speed(self, speed):
		return json.dumps({'Speed': speed})

	def create_payload_alcohol(self, alcohol_value):
			return json.dumps({'Alcohol': alcohol_value})

	def create_payload_temp(self, temp):
		return json.dumps({'Temperature': temp})

	def create_payload_timestamp(self):
		now = datetime.now()
		timestamp = now.strftime("%H:%M:%S:%f")[:-3]
		return json.dumps({'Timestamp': timestamp})

	def create_payload_gps(self, longitude_GPS, latitude_GPS, speed):
		return json.dumps({
			'Longitude': longitude_GPS,
			'Latitude': latitude_GPS,
   			'Speed': speed,
		})

	def create_payload_license_plates(self, license_plates):
		return json.dumps({'License plates': license_plates})

	def create_payload_status(self, status):
		return json.dumps({'Status': status})

	def create_payload_company(self, type_car):
		return json.dumps({'Company': type_car})


if __name__ == "__main__":
	client = MQTTClient(ACCESS_TOKENS['CAR2'])
	client.send_data()
