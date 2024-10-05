from RFID import RFID_lib
import time 

if __name__ == "__main__":
    rfid = RFID_lib()  # Initialize the RFID object
    while True:
        rfid.read_data()
        data = rfid.get_data()
        print(data)
        time.sleep(1)  # Read every 1 second
