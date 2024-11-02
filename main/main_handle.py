import threading

from handle.rfid_handle import RFIDHandler
from handle.sensors_handle import SensorHandler
from iot.mqtt.publish import MQTTClient 
from handle.camera_gstreamer import initialize_camera


def main():
    # Initialize sensor, MQTT, RFID, and TFT handlers
    mqtt_client = MQTTClient('CAR2_TOKEN')  # Initialize MQTT client with token
    sensor_handler = SensorHandler(mqtt_client)  # Initialize sensor handler
    rfid_handler = RFIDHandler(mqtt_client)  # Initialize RFID handler
    video_streamer = initialize_camera(mqtt_client)

    try:
        # Create and start threads for GPS, accelerometer, and RFID handling
        # gps_thread = threading.Thread(target=sensor_handler.read_gps, args=(mqtt_client,))  # Use instance method for GPS
        # acc_thread = threading.Thread(target=sensor_handler.read_accelerometer, args=(mqtt_client,))  # Pass mqtt_client to accelerometer
        rfid_thread = threading.Thread(target=rfid_handler.read_rfid)  # Start RFID reading thread
        temp_thread = threading.Thread(target=sensor_handler.read_temperature)
        
        # Create video streaming thread with the new run_server method
        video_thread = threading.Thread(target=video_streamer.run_server)

        # gps_thread.start()
        # acc_thread.start()
        rfid_thread.start()  # Start RFID thread
        temp_thread.start()  # Start temperature thread
        video_thread.start()  # Start video streaming

        # Start video recording in a separate thread
        # recording_thread = threading.Thread(target=start_recording, args=("filename.h264",))
        # recording_thread.start()
        
        print("All services started successfully")
        
        # Ensure the main program waits for all threads to finish
        # gps_thread.join()
        # acc_thread.join()
        rfid_thread.join()  # Wait for RFID thread to finish
        temp_thread.join()  # Wait for temperature thread to finish
        # recording_thread.join()  # Join the recording thread as well
        video_thread.join()

    except KeyboardInterrupt:
        # Handle manual shutdown (Ctrl+C)
        print("Shutting down...")
        mqtt_client.client.disconnect()  # Disconnect MQTT client
        sensor_handler.cleanup()  # Clean up sensor resources
        rfid_handler.stop_reading()  # Stop RFID reading thread
        video_streamer.stop()

if __name__ == '__main__':
    main()