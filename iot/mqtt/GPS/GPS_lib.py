import serial
import time
import threading

class GPSReader:
    def __init__(self, gps_port="/dev/ttyUSB1", setup_port="/dev/ttyUSB2", baudrate=115200):
        self.gps_port = gps_port
        self.setup_port = setup_port
        self.baudrate = baudrate
        self.ser1 = None
        self.ser2 = None
        self.latitude = None
        self.longitude = None
        self._stop_event = threading.Event()
        self._gps_thread = threading.Thread(target=self._read_gps_continuously)

    def setup(self):
        self.ser2 = serial.Serial(self.setup_port, self.baudrate)
        print(f"{self.setup_port} Open!!!")
        self.ser2.write('AT+QGPS=1\r'.encode())
        print("AT+QGPS=1")
        self.ser2.close()
        print(f"{self.setup_port} Close!!!")

    def open_gps_port(self):
        self.ser1 = serial.Serial(self.gps_port, self.baudrate)
        print(f"{self.gps_port} Open!!!")

    def close_gps_port(self):
        if self.ser1 and self.ser1.is_open:
            self.ser1.close()
            print(f"{self.gps_port} Close!!!")

    def _read_gps_continuously(self):
        if not self.ser1 or not self.ser1.is_open:
            self.open_gps_port()

        while not self._stop_event.is_set():
            try:
                line = str(self.ser1.readline(), encoding='utf-8').strip()
                if line.startswith("$GPRMC"):
                    data = line.split(",")

                    if not data[3] or not data[5]:
                        print("Invalid data received: latitude or longitude is empty")
                        continue

                    try:
                        latitude = float(data[3])
                        longitude = float(data[5])
                    except ValueError:
                        print("Invalid data received: could not convert latitude or longitude to float")
                        continue

                    latitude_direction = data[4]
                    longitude_direction = data[6]

                    if latitude_direction == "S":
                        latitude = -latitude
                    if longitude_direction == "W":
                        longitude = -longitude

                    self.latitude = int(latitude / 100) + (latitude / 100 - int(latitude / 100)) * 100 / 60
                    self.longitude = int(longitude / 100) + (longitude / 100 - int(longitude / 100)) * 100 / 60

            except serial.SerialException as e:
                print(f"SerialException during read: {e}")
                time.sleep(1)
            except BrokenPipeError as e:
                print(f"BrokenPipeError during read: {e}")
                break

    def start(self):
        self.setup()
        self._gps_thread.start()

    def stop(self):
        self._stop_event.set()
        self._gps_thread.join()

    def get_current_location(self):
        return self.latitude, self.longitude

    def stop_gps(self):
        self.ser2 = serial.Serial(self.setup_port, self.baudrate)
        print(f"{self.setup_port} Open!!!")
        self.ser2.write('AT+QGPSEND\r'.encode())
        print("AT+QGPSEND")
        self.ser2.close()
        print(f"{self.setup_port} Close!!!")

    def destroy(self):
        self.close_gps_port()
        self.stop_gps()
