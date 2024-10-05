from RFID import RFID_lib
import time 
import threading  # Added threading module


if __name__ == "__main__":
    rfid = RFID_lib()  # Initialize the RFID object
    rfid.start_reading_thread()  # Start the thread to read data in the background

    # The main thread can continue doing other things
    try:
        while True:
            # You can still access the data from the main thread
            print(rfid.get_data())  # Print current data
            time.sleep(2)  # Main thread waits for 2 seconds
    except KeyboardInterrupt:
        rfid.stop_reading_thread()  # Stop the background thread when exiting
