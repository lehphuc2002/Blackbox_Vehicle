import smbus2
import time
from Kalman import KalmanFilter1 
from Kalman import KalmanFilter2
from Kalman import KalmanFilter3

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
        mag_data = self.read_i2c_block_data(self.BNO055_MAG_DATA_X_LSB, 6)
        gyro_data = self.read_i2c_block_data(self.BNO055_GYRO_DATA_X_LSB, 6)

        accel_x = ((accel_data[1] << 8) | accel_data[0]) & 0xFFFF
        if accel_x > 32767:
            accel_x -= 65536

        accel_y = ((accel_data[3] << 8) | accel_data[2]) & 0xFFFF
        if accel_y > 32767:
            accel_y -= 65536

        accel_z = ((accel_data[5] << 8) | accel_data[4]) & 0xFFFF
        if accel_z > 32767:
            accel_z -= 65536

        filtered_x = self.kalman_filter_1.update(accel_x)
        filtered_y = self.kalman_filter_2.update(accel_y)
        filtered_z = self.kalman_filter_3.update(accel_z)
        
        # filtered_x = accel_x
        # filtered_y = accel_y
        # filtered_z = accel_z
        
        
        mag_x = (mag_data[1] << 8) | mag_data[0]
        mag_y = (mag_data[3] << 8) | mag_data[2]
        mag_z = (mag_data[5] << 8) | mag_data[4]

        gyro_x = (gyro_data[1] << 8) | gyro_data[0]
        gyro_y = (gyro_data[3] << 8) | gyro_data[2]
        gyro_z = (gyro_data[5] << 8) | gyro_data[4]

        return filtered_x / 100, filtered_y / 100, filtered_z / 100
        # return {
            # 'accel': (filtered_x / 100, filtered_y / 100, filtered_z / 100),
            # 'mag': (mag_x, mag_y, mag_z),
            # 'gyro': (gyro_x, gyro_y, gyro_z) }

    # def read_accelerometer(self):
        # sensor_data = self.read_sensor_data()
        # return sensor_data()   #['accel']

# Usage example
if __name__ == "__main__":
    sensor = BNO055Sensor()
    while True:
        ax, ay, az  = sensor.read_sensor_data()
        print("Accelerometer:", ax, ay, az)
        time.sleep(0.02)
