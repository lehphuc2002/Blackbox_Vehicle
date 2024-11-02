import serial
import time
import math

class GPSModule:

    def __init__(self, gps_port="/dev/ttyUSB1", command_port="/dev/ttyUSB2", baud_rate=115200):
        self.gps_port = gps_port
        self.command_port = command_port
        self.baud_rate = baud_rate
        self.ser2 = None
        self.setup_gps()
        self.open_serial()

    def setup_gps(self):
        self.ser2 = serial.Serial(self.command_port, self.baud_rate, timeout=1)
        print(f"{self.command_port} Open!!!")
        self.ser2.write('AT+QGPS=1\r'.encode())
        print("AT+QGPS=1")
        time.sleep(2)  
        self.ser2.close()
        print(f"{self.command_port} Close!!!")

    def open_serial(self):
        self.ser2 = serial.Serial(self.command_port, self.baud_rate, timeout=1)
        print(f"{self.command_port} Open!!!")

    def read_coordinates(self):
        try:
            # G?i l?nh AT+QGPSGNMEA="GGA" t?i ttyUSB2
            self.ser2.write('AT+QGPSGNMEA="GGA"\r'.encode())
            time.sleep(1) 

            lines = []
            while self.ser2.in_waiting:  
                line = self.ser2.readline().decode('utf-8').strip()
                lines.append(line)
                print(f"Received: {line}")

           
            for line in lines:
                if line.startswith("+QGPSGNMEA:"):
                    data = line.split(",")
                    if len(data) >= 5 and data[2] and data[4]:  
                        latitude = float(data[2])
                        latitude_direction = data[3]
                        longitude = float(data[4])
                        longitude_direction = data[5]

                        if latitude_direction == "S":
                            latitude = -latitude
                        if longitude_direction == "W":
                            longitude = -longitude

                        latitude_temp = int(latitude / 100) + (latitude / 100 - int(latitude / 100)) * 100 / 60
                        longitude_temp = int(longitude / 100) + (longitude / 100 - int(longitude / 100)) * 100 / 60

                        return longitude_temp, latitude_temp
                    else:
                        print("Invalid GPS data")
                        return None, None
            print("No GPS data found")
            return None, None

        except serial.SerialException as e:
            print(f"Serial exception: {e}")
            return None, None

    def destroy(self):
        try:
            if self.ser2 and not self.ser2.is_open:
                self.ser2.open()
            self.ser2.write('AT+QGPSEND\r'.encode())
            print("AT+QGPSEND")
        except serial.SerialException as e:
            print(f"Serial exception: {e}")
        finally:
            if self.ser2 and self.ser2.is_open:
                self.ser2.close()
                print(f"{self.command_port} Close!!!")

# Usage example
if __name__ == "__main__":
    try:
        gps = GPSModule()
        while True:
            longi, lati = gps.read_coordinates()
            if longi is not None and lati is not None:
                print(f"Longitude: {longi}, Latitude: {lati}")
            else:
                print("Failed to read coordinates")
            time.sleep(2)
    except KeyboardInterrupt:
        gps.destroy()
