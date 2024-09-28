# -*- coding: utf-8 -*-
import smbus2
import time
import numpy as np
import sys
import math
from Kalman import KalmanFilter1
from Kalman import KalmanFilter2
from Kalman import KalmanFilter3
import threading  # Import thêm threading

class BNO055Sensor:
    BNO055_ADDRESS = 0x29
    BNO055_OPR_MODE = 0x3D
    BNO055_PWR_MODE = 0x3E
    BNO055_SYS_TRIGGER = 0x3F
    BNO055_TEMP = 0x34
    BNO055_ACCEL_DATA_X_LSB = 0x28
    BNO055_MAG_DATA_X_LSB = 0x0E
    BNO055_GYRO_DATA_X_LSB = 0x14
    OPR_MODE_CONFIG = 0x00
    OPR_MODE_NDOF = 0x0C

    def __init__(self, bus_num=1):
        self.bus = smbus2.SMBus(bus_num)
        self.kalman_filter_1 = KalmanFilter1(process_variance=1e-5, measurement_variance=1e-2)
        self.kalman_filter_2 = KalmanFilter2(process_variance=1e-5, measurement_variance=1e-2)
        self.kalman_filter_3 = KalmanFilter3(process_variance=1e-5, measurement_variance=1e-2)
        self.accel_data = [0, 0, 0]  # T?o bi?n d? luu d? li?u gia t?c k?
        self.lock = threading.Lock()  # T?o m?t lock d? b?o v? d? li?u chia s?

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

    def read_sensor_data(self):
        accel_data = self.read_i2c_block_data(self.BNO055_ACCEL_DATA_X_LSB, 6)

        accel_x = ((accel_data[1] << 8) | accel_data[0]) & 0xFFFF
        if accel_x > 32767:
            accel_x -= 65536

        accel_y = ((accel_data[3] << 8) | accel_data[2]) & 0xFFFF
        if accel_y > 32767:
            accel_y -= 65536

        accel_z = ((accel_data[5] << 8) | accel_data[4]) & 0xFFFF
        if accel_z > 32767:
            accel_z -= 65536

        return accel_x / 100, accel_y / 100, accel_z / 100

    def read_accelerometer_thread(self):
        while True:
            accel_x, accel_y, accel_z = self.read_sensor_data()
            with self.lock:  # S? d?ng lock khi c?p nh?t d? li?u
                self.accel_data = [accel_x, accel_y, accel_z]
            time.sleep(0.02)  # Ð?c d? li?u m?i 20ms

    def accel_calib(self):
        print("Start calib")
        wx_values = []
        wy_values = []
        wz_values = []
        i = 0
        while i < 100:
            try:
                wx, wy, wz = self.read_sensor_data()
                i += 1
            except:
                continue
            wx_values.append(wx)
            wy_values.append(wy)
            wz_values.append(wz)

        wx_mean = np.mean(wx_values)
        wy_mean = np.mean(wy_values)
        wz_mean = np.mean(wz_values)

        Accel_offsets = [wx_mean, wy_mean, wz_mean]

        print('Accel Calibration Complete')
        return Accel_offsets

    def main_1(self):
        offset = self.accel_calib()
        time_start = time.time()
        vx = 0
        vy = 0
        vz = 0

        while True:
            with self.lock:  # S? d?ng lock d? d?m b?o d? li?u không b? thay d?i gi?a ch?ng
                ax, ay, az = self.accel_data

            ax = ax - offset[0]
            ay = ay - offset[1]
            az = az - offset[2]

            t = time.time()
            dt = t - time_start
            time_start = t

            vx = round(vx + round(ax, 1) * dt, 1)
            vy = round(vy + round(ay, 1) * dt, 1)
            vz = round(vz + round(az, 1) * dt, 1)

            v = math.sqrt(vx * vx + vy * vy + vz * vz) * 3.6
            print("Van toc:", v)
            print("Accelerometer:", ax, ay, az)
            time.sleep(0.02)

# Usage example
if __name__ == "__main__":
    sensor = BNO055Sensor()

    # T?o thread d? d?c d? li?u t? gia t?c k?
    accel_thread = threading.Thread(target=sensor.read_accelerometer_thread)
    accel_thread.daemon = True  # Ð?m b?o thread d?ng khi chuong trình chính d?ng
    accel_thread.start()

    # Ch?y hàm chính
    sensor.main_1()
