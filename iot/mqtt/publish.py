import random as rnd
import time
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
import json

# Constants
ACCESS_TOKENS = {
    "CAR1": "CAR1_TOKEN",  # Mercedes
    "CAR2": "CAR2_TOKEN",  # Toyota
    "CAR3": "CAR3_TOKEN",  # Tesla
}

TYPE_CAR = "Mercedes"
LICENSE_PLATE = "60H1-47413"

# Firebase Initialization
cred = credentials.Certificate(
    "/home/pi/Documents/01_Thesis/01_project/Blackbox_Vehicle/blackboxvehicle-c345e-firebase-adminsdk-u58su-3da590c691.json"
)  # Update with your service account path
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "https://blackboxvehicle-c345e-default-rtdb.firebaseio.com/"  # Update with your Firebase Realtime Database URL
    },
)


class FirebaseClient:
    def __init__(self):
        self.type_car = TYPE_CAR
        self.license_plates = LICENSE_PLATE

        self.current_ref = db.reference(
            f'/cars/{self.license_plates.replace("-", "_").upper()}'
        )
        self.logs_ref = db.reference(
            f'/logs/{self.license_plates.replace("-", "_").upper()}'
        )

    def publish(self, group_name, data):
 
        ref = db.reference(f'/cars/{self.license_plates.replace("-", "_")}')
        if not ref.get():
            print(
                f"License plate {self.license_plates} not found in Firebase. Waiting..."
            )
            return None

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        self.current_ref.update(data)
        print(f"Current data updated in Firebase: {data}")
        
        if not group_name:
            return

    
        group_ref = self.logs_ref.child(group_name)
        group_ref.child(timestamp).set(data)
        print(f"Log saved for group '{group_name}' with timestamp: {timestamp}")

  
        self.cleanup_old_logs(group_ref)

        return data

    def cleanup_old_logs(self, group_ref):
        """
        Xóa các log cu hon 30 phút.
        """
        now = datetime.now()
        thirty_minutes_ago = now - timedelta(seconds=60)
        old_logs = group_ref.get()
        if old_logs:
            for key, _ in old_logs.items():
                record_time = datetime.strptime(key, "%Y-%m-%d %H:%M:%S")
                if record_time < thirty_minutes_ago:
                    group_ref.child(key).delete()

    def create_payload(self, ax, ay, az, speed, status):
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "Accelerometer X": ax,
            "Accelerometer Y": ay,
            "Accelerometer Z": az,
            "Speed": speed,
            "Timestamp": timestamp,
            "Longitude": 106.706718,
            "Latitude": 10.825225,
            "License plates": self.license_plates,
            "Temperature": round(rnd.uniform(0, 50), 2),
            "Status": status,
            "Company": self.type_car,
            "Camera Streaming": "https://www.youtube.com/",
        }
        return payload
        
        
   	# Keep all original payload creation functions
    def create_payload_motion_data(self, ax, ay, az, speed, status):
        payload = {
        'Accelerometer X': ax,
        'Accelerometer Y': ay,
        'Accelerometer Z': az,
			  'Speed': speed,
			  'Status': status
		  }
        return payload
        

    def send_accelerometer_data(self):
        data = {
            "accleromentionX": round(rnd.uniform(0, 50), 2),
            "accleromentionY": round(rnd.uniform(0, 30), 2),
            "accleromentionZ": round(rnd.uniform(20, 120), 2),
            "acclerorationLinear": round(rnd.uniform(0, 50), 2),
        }
        self.publish("accelerometer", data)
    
    def create_payload_URL_camera(self, url, link_local_streaming):
        payload = {
      		'URL Camera ': url,
			'URL Stream' : link_local_streaming
		}
        return payload
  
    def create_payload_accident_signal(self, accident_signal):
        payload = {
      		'accident': accident_signal,
		}
        return payload

    def send_speed_data(self):
        data = {"speed": round(rnd.uniform(20, 120), 2)}
        self.publish("speed", data)

    def send_location_data(self):

        data = {"longitude": 106.706718, "latitude": 10.825225}
        self.publish("location", data)

    def send_temperature_data(self):

        data = {"temperature": round(rnd.uniform(0, 50), 2)}
        self.publish("temperature", data)

    def send_status_data(self):

        speed = round(rnd.uniform(20, 120), 2)
        status = "Normal" if speed <= 90 else "Over Speed"
        data = {"status": status}
        self.publish("status", data)

    def send_data(self):
        try:
            while True:
                # Gather sensor data
                ax, ay, az = self.get_accelerometer_data()
                speed = self.get_speed()
                status = "Normal" if speed <= 90 else "Over Speed"

                # Create payload
                payload = self.create_payload(ax, ay, az, speed, status)

                # Publish to Firebase
                self.publish(payload)

        except KeyboardInterrupt:
            print("Stopped sending data to Firebase.")


    def get_accelerometer_data(self):
        # Get sensor data (e.g., accelerometer readings)
        ax = round(rnd.uniform(0, 50), 2)  # Accelerometer X
        ay = round(rnd.uniform(0, 30), 2)  # Accelerometer Y
        az = round(rnd.uniform(20, 120), 2)  # Accelerometer Z
        return ax, ay, az

    def get_speed(self):
        # Get speed data
        speed = round(rnd.uniform(20, 120), 2)
        return speed


if __name__ == "__main__":
    client = FirebaseClient()  # Bi?n s? xe
    try:
        while True:
            client.send_accelerometer_data()
            client.send_speed_data()
            client.send_location_data()
            client.send_temperature_data()
            client.send_status_data()
            time.sleep(5)  # G?i m?i giây
    except KeyboardInterrupt:
        print("Stopped.")
