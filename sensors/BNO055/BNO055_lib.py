import smbus2
import time
import numpy as np
import math
from sensors.BNO055.Kalman import KalmanFilter1, KalmanFilter2, KalmanFilter3

class BNO055Sensor:
    BNO055_ADDRESS = 0x29
    BNO055_OPR_MODE = 0x3D
    BNO055_PWR_MODE = 0x3E
    BNO055_SYS_TRIGGER = 0x3F
    BNO055_TEMP = 0x34
    BNO055_ACCEL_DATA_X_LSB = 0x28
    OPR_MODE_CONFIG = 0x00
    OPR_MODE_NDOF = 0x0C

    def __init__(self, bus_num=1):
        self.bus = smbus2.SMBus(bus_num)
        self.kalman_filters = {
            'x': KalmanFilter1(process_variance=1e-5, measurement_variance=1e-2),
            'y': KalmanFilter2(process_variance=1e-5, measurement_variance=1e-2),
            'z': KalmanFilter3(process_variance=1e-5, measurement_variance=1e-2),
        }
        self.initialize_sensor()

    def write_byte_data(self, reg, value):
        self.bus.write_byte_data(self.BNO055_ADDRESS, reg, value)

    def read_byte_data(self, reg):
        return self.bus.read_byte_data(self.BNO055_ADDRESS, reg)

    def read_i2c_block_data(self, reg, length):
        return self.bus.read_i2c_block_data(self.BNO055_ADDRESS, reg, length)

    def initialize_sensor(self):
        self.write_byte_data(self.BNO055_OPR_MODE, self.OPR_MODE_CONFIG)
        time.sleep(0.03)
        self.write_byte_data(self.BNO055_OPR_MODE, self.OPR_MODE_NDOF)
        time.sleep(0.03)

    def read_accel_data(self):
        accel_data = self.read_i2c_block_data(self.BNO055_ACCEL_DATA_X_LSB, 6)
        return self._convert_accel_data(accel_data)

    def _convert_accel_data(self, data):
        def convert(val_lsb, val_msb):
            value = (val_msb << 8) | val_lsb
            return value - 65536 if value > 32767 else value
        
        accel_x = convert(data[0], data[1])
        accel_y = convert(data[2], data[3])
        accel_z = convert(data[4], data[5])

        return accel_x, accel_y, accel_z

    def apply_kalman_filter(self, accel_data):
        return (
            self.kalman_filters['x'].update(accel_data[0]),
            self.kalman_filters['y'].update(accel_data[1]),
            self.kalman_filters['z'].update(accel_data[2]),
        )

    def accel_calib(self, samples=100):
        print("Starting calibration...")
        accel_values = {'x': [], 'y': [], 'z': []}

        for _ in range(samples):
            try:
                accel_x, accel_y, accel_z = self.read_accel_data()
                accel_values['x'].append(accel_x)
                accel_values['y'].append(accel_y)
                accel_values['z'].append(accel_z)
            except Exception:
                continue

        offsets = {axis: np.mean(values) for axis, values in accel_values.items()}
        print("Calibration complete. Offsets:", offsets)
        return offsets

    def main_1(self):
        offsets = self.accel_calib()
        vx = vy = vz = 0
        time_start = time.time()

        while True:
            ax, ay, az = self.read_accel_data()
            ax -= offsets['x']
            ay -= offsets['y']
            az -= offsets['z']

            dt = time.time() - time_start
            time_start = time.time()

            vx += ax * dt
            vy += ay * dt
            vz += az * dt

            v = math.sqrt(vx**2 + vy**2 + vz**2) * 3.6
            print(f"Speed: {v:.2f} km/h, Accelerometer: {ax:.2f}, {ay:.2f}, {az:.2f}")
            time.sleep(0.02)

# Usage example
if __name__ == "__main__":
    sensor = BNO055Sensor()
    sensor.main_1()
