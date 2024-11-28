import threading
import time
from handle.rfid_handle import RFIDHandler
from handle.sensors_handle import SensorHandler
from handle.state_motion_handle import MotionStateHandler
from iot.mqtt.publish import MQTTClient 
from handle.camera_gstreamer import initialize_camera
from handle.record_handle import RecordHandler
import handle.connection_internet_handle as conn_handle 

def main():
    connection_monitor_thread = threading.Thread(target=conn_handle.monitor_connection, daemon=True)
    connection_monitor_thread.start()
    # Wait for the connection to stabilize
    while not conn_handle.get_connection_status():
        print("Waiting for internet connection...")
        time.sleep(1)
    # Initialize sensor, MQTT, RFID, and TFT handlers
    # mqtt_client = MQTTClient('CAR2_TOKEN')  # Initialize MQTT client with token
    mqtt_client = MQTTClient('CAR2_TOKEN', conn_handle)  # Initialize MQTT client with token and connection handler
    sensor_handler = SensorHandler(mqtt_client, conn_handle)  # Initialize sensor handler
    rfid_handler = RFIDHandler(mqtt_client)  # Initialize RFID handler
    record_handler = RecordHandler()
    video_streamer = initialize_camera(mqtt_client, record_handler)
    motion_state_handler = MotionStateHandler(sensor_handler)

    try:
        # Create and start threads for GPS, accelerometer, and RFID handling
        # gps_thread = threading.Thread(target=sensor_handler.read_gps, args=(mqtt_client,))  # Use instance method for GPS
        # acc_thread = threading.Thread(target=sensor_handler.read_accelerometer, args=(mqtt_client,))  # Pass mqtt_client to accelerometer
        rfid_thread = threading.Thread(target=rfid_handler.read_rfid)  # Start RFID reading thread
        temp_thread = threading.Thread(target=sensor_handler.read_temperature)
        acc_thread = threading.Thread(target=sensor_handler.read_accelerometer)
        
        # Create video streaming thread with the new run_server method
        video_thread = threading.Thread(target=video_streamer.run_server, daemon=True)

        # gps_thread.start()
        rfid_thread.start()  # Start RFID thread
        temp_thread.start()  # Start temperature thread
        video_thread.start()  # Start video streaming
        acc_thread.start()

        # Start video recording in a separate thread
        # recording_thread = threading.Thread(target=start_recording, args=("filename.h264",))
        # recording_thread.start()
        
        print("All services started successfully")
        
        # Ensure the main program waits for all threads to finish
        # gps_thread.join()
        rfid_thread.join()  # Wait for RFID thread to finish
        temp_thread.join()  # Wait for temperature thread to finish
        # recording_thread.join()  # Join the recording thread as well
        video_thread.join()
        acc_thread.join()

    except KeyboardInterrupt:
        # Handle manual shutdown (Ctrl+C)
        print("Shutting down...")
        mqtt_client.client.disconnect()  # Disconnect MQTT client
        sensor_handler.running = False
        # sensor_handler.cleanup()  # Clean up sensor resources
        rfid_handler.stop_reading()  # Stop RFID reading thread
        video_streamer.stop()
        
        # Clean up resources for each handler
        sensor_handler.cleanup()
        motion_state_handler.cleanup()
        rfid_thread.join()  # Ensure RFID thread completes before exit
        temp_thread.join()  # Ensure temperature thread completes
        video_thread.join() # Ensure video thread completes
        acc_thread.join()

if __name__ == '__main__':
    main()