# -*- coding: utf-8 -*-
import smbus2
import time
import numpy as np
import sys
import math
import threading

class BNO055Sensor:
    BNO055_ADDRESS = 0x29
    BNO055_OPR_MODE = 0x3D
    BNO055_PWR_MODE = 0x3E
    BNO055_SYS_TRIGGER = 0x3F
    BNO055_TEMP = 0x34

    # Acceleration and Linear Acceleration register addresses
    BNO055_ACCEL_DATA_X_LSB = 0x08
    BNO055_LINEAR_ACCEL_DATA_X_LSB = 0x28
    
    OPR_MODE_CONFIG = 0x00
    OPR_MODE_NDOF = 0x0C

    def __init__(self, bus_num=1):
        self.bus = smbus2.SMBus(bus_num)
        self.accel_data = [0, 0, 0]
        self.linear_accel_data = [0, 0, 0]
        self.lock = threading.Lock()
        self.running = True  # Add a running attribute to control threads

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

    def read_accelerometer_data(self):
        accel_data = self.read_i2c_block_data(self.BNO055_ACCEL_DATA_X_LSB, 6)

        accel_x = ((accel_data[1] << 8) | accel_data[0]) & 0xFFFF
        accel_y = ((accel_data[3] << 8) | accel_data[2]) & 0xFFFF
        accel_z = ((accel_data[5] << 8) | accel_data[4]) & 0xFFFF

        if accel_x > 32767: accel_x -= 65536
        if accel_y > 32767: accel_y -= 65536
        if accel_z > 32767: accel_z -= 65536

        return accel_x / 100, accel_y / 100, accel_z / 100

    def read_linear_accelerometer_data(self):
        linear_accel_data = self.read_i2c_block_data(self.BNO055_LINEAR_ACCEL_DATA_X_LSB, 6)

        linear_accel_x = ((linear_accel_data[1] << 8) | linear_accel_data[0]) & 0xFFFF
        linear_accel_y = ((linear_accel_data[3] << 8) | linear_accel_data[2]) & 0xFFFF
        linear_accel_z = ((linear_accel_data[5] << 8) | linear_accel_data[4]) & 0xFFFF

        if linear_accel_x > 32767: linear_accel_x -= 65536
        if linear_accel_y > 32767: linear_accel_y -= 65536
        if linear_accel_z > 32767: linear_accel_z -= 65536

        return linear_accel_x / 100, linear_accel_y / 100, linear_accel_z / 100

    def read_accelerometer_thread(self):
        while self.running:
            accel_x, accel_y, accel_z = self.read_accelerometer_data()
            with self.lock:
                self.accel_data = [accel_x, accel_y, accel_z]
            time.sleep(0.02)

    def read_linear_accelerometer_thread(self):
        while self.running:
            linear_accel_x, linear_accel_y, linear_accel_z = self.read_linear_accelerometer_data()
            with self.lock:
                self.linear_accel_data = [linear_accel_x, linear_accel_y, linear_accel_z]
            time.sleep(0.02)

    def stop_threads(self):
        """Stops the accelerometer and linear accelerometer threads."""
        self.running = False

    def main_1(self):
        time_start = time.time()
        vx = vy = vz = 0

        while self.running:
            with self.lock:
                ax, ay, az = self.accel_data
                lax, lay, laz = self.linear_accel_data
#
#            t = time.time()
#            dt = t - time_start
#            time_start = t
#
#            vx += ax * dt
#            vy += ay * dt
#            vz += az * dt

            #velocity = math.sqrt(vx**2 + vy**2 + vz**2) * 3.6
            #print("Velocity:", velocity)
            print("Accelerometer:", ax, ay, az)
            print("Linear Accelerometer:", lax, lay, laz)
            time.sleep(0.02)

