import os
import subprocess
import threading
import time
import paho.mqtt.client as paho
from flask import Flask, render_template, Response
from handle.camera_init import VideoCamera
from iot.firebase.push_image import upload_images_and_generate_html  # just for test, should be deleted
from datetime import datetime  # just for test, should be deleted
import random  # just for test
from iot.mqtt.publish import MQTTClient  # just for test

class VideoStreamer:
    def __init__(self, mqtt_client, fps):
        self.mqtt_client = mqtt_client
        self.serveo_process = None
        self.serveo_url = None
        self.running = False
        self.fps = fps  # Set the frame rate
        print(f"FPS is {fps}")
        
        # Testing overspeed and capture picture
        self.image_save_dir = os.path.join(os.path.dirname(__file__), '..', 'iot', 'firebase', 'image', 'customer_Phuc')
        print(f"Image save at {self.image_save_dir}")

        # Ensure the save directory exists
        if not os.path.exists(self.image_save_dir):
            os.makedirs(self.image_save_dir)
        
         # Initialize shared camera instance
        self.camera = VideoCamera()  # Only one camera instance for all clients

    def gen(self):
        """Generator function to serve video frames from the shared camera instance."""
        frame_interval = 1.0 / self.fps  # Time between frames based on the FPS
        while True:
            start_time = time.time()

            # Get the frame from the shared camera instance
            frame = self.camera.get_frame()
            if frame is None:
                break

            # Yield the frame as part of the video stream
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

            # Control the frame rate
            time_taken = time.time() - start_time
            sleep_time = max(0, frame_interval - time_taken)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start_serveo(self):
        """Start Serveo SSH tunnel in another terminal and retrieve the public URL."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__)) 
            log_file_path = os.path.join(current_dir, 'serveo_log.txt')
            print(f"log file path at: {log_file_path}")

            # Remove the log file if it exists to start fresh
            if os.path.exists(log_file_path):
                os.remove(log_file_path)
                
             # Check if the Serveo session is already running, kill it if found
            kill_command = "tmux kill-session -t serveo_session"
            subprocess.run(kill_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Run the Serveo command in a new tmux session
            command = f"ssh -R 80:localhost:5000 serveo.net | tee {log_file_path}"
            # self.serveo_process = subprocess.Popen(
            #     ['tmux', 'new-session', '-d', '-s', 'serveo_session', 'bash', '-c', command]
            # )

            time.sleep(2)  # Give the Serveo command time to start
            print("Serveo is starting...")

            # Read the log file to capture the URL
            while True:
                if not os.path.exists(log_file_path):
                    time.sleep(1)  # Wait if the log file hasn't been created yet
                    continue

                with open(log_file_path, 'r') as log_file:
                    lines = log_file.readlines()

                for line in lines:
                    print(f"Serveo output: {line.strip()}")  # Print Serveo output for debugging
                    if "http://" in line or "https://" in line:
                        self.serveo_url = line.strip()  # Store the Serveo URL
                        print(f"Serveo URL: {self.serveo_url}")
                        break

                if self.serveo_url:
                    break  # Exit loop once the URL is found

            # Push Serveo URL to MQTT
            if self.serveo_url:
                payload = self.mqtt_client.create_payload_URL_camera_serveo(self.serveo_url)
                ret = self.mqtt_client.publish(payload)
                if ret.rc == paho.MQTT_ERR_SUCCESS:
                    print("Serveo URL published successfully")
                else:
                    print(f"Failed to publish URL, error code: {ret.rc}")

        except Exception as e:
            print(f"Error starting Serveo: {e}")


    def capture_image(self, camera):
        """Capture a single frame from the video feed and save it."""
        frame = camera.get_frame()
        if frame is not None:
            # Create a unique filename based on the current timestamp
            timestamp = datetime.now().strftime("%Y/%m/%d_%Hh%Mm%Ss")
            image_path = os.path.join(self.image_save_dir, f"overspeed_{timestamp}.jpg")

            # Write the frame to the image file
            with open(image_path, 'wb') as f:
                f.write(frame)
            print(f"Image saved at: {image_path}")
            return image_path
        return None

    def monitor_velocity(self, camera):
        """Monitor random velocity and capture image if overspeed occurs."""
        while True:
            # Generate a random velocity between 0 and 100
            velocity = random.randint(0, 100)
            print(f"Current velocity: {velocity} km/h")

            if velocity > 70:
                print("Overspeed detected! Capturing image...")
                # image_path = self.capture_image(camera)
                
                # if image_path:
                #     # Push image to Firebase
                #     print("Pushing image to Firebase...")
                    # upload_images_and_generate_html(image_path)

            # Sleep for a short interval before checking again
            time.sleep(2)

    def video_feed(self):
        """Start the video feed and serve it to multiple clients."""
        if not self.running:
            self.running = True

            # Create the Flask app
            app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

            # Define the routes
            @app.route('/')
            def index():
                return render_template('index.html')

            @app.route('/video_feed')
            def video_feed():
                """Serve the video feed to each client, sharing the camera instance."""
                print("Client connected to video feed.")
                return Response(self.gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

            # Run the Flask app with threading enabled to handle multiple clients
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)


    def stop(self):
        """Stop the video feed and clean up resources."""
        self.running = False
        if self.serveo_process:
            self.serveo_process.terminate()
        print("Stopping video feed...")

# Example usage:
if __name__ == '__main__':
    mqtt_client = MQTTClient('CAR2_TOKEN')  # Replace with actual token
    video_streamer = VideoStreamer(mqtt_client, fps=10)
    video_streamer.video_feed()
