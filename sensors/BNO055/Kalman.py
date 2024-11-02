# import time
# from mpu6050lib import mpu6050
# import smbus			#import SMBus module of I2C

class KalmanFilter1:
    def __init__(self, process_variance, measurement_variance):
        self.process_variance_1 = process_variance
        self.measurement_variance_1 = measurement_variance
        self.estimated_measurement_1 = 0
        self.error_covariance_1 = 1
        self.kalman_gain_1 = 1
 
    def update(self, measurement_1):
        #Prediction step
        self.error_covariance_1 = self.error_covariance_1 + self.process_variance_1

        #Update step
        self.kalman_gain_1 = self.error_covariance_1 / (self.error_covariance_1 + self.measurement_variance_1)
        self.estimated_measurement_1 += self.kalman_gain_1 * (measurement_1 - self.estimated_measurement_1)
        self.error_covariance_1 = (1 - self.kalman_gain_1) * self.error_covariance_1

        return self.estimated_measurement_1

class KalmanFilter2:
    def __init__(self, process_variance, measurement_variance):
        self.process_variance_2 = process_variance
        self.measurement_variance_2 = measurement_variance
        self.estimated_measurement_2 = 0
        self.error_covariance_2 = 1
        self.kalman_gain_2 = 1

    def update(self, measurement_2):
        #Prediction step
        self.error_covariance_2 = self.error_covariance_2 + self.process_variance_2

        #Update step
        self.kalman_gain_2 = self.error_covariance_2 / (self.error_covariance_2 + self.measurement_variance_2)
        self.estimated_measurement_2 += self.kalman_gain_2 * (measurement_2 - self.estimated_measurement_2)
        self.error_covariance_2 = (1 - self.kalman_gain_2) * self.error_covariance_2

        return self.estimated_measurement_2

class KalmanFilter3:
    def __init__(self, process_variance, measurement_variance):
        self.process_variance_3 = process_variance
        self.measurement_variance_3 = measurement_variance
        self.estimated_measurement_3 = 0
        self.error_covariance_3 = 1
        self.kalman_gain_3 = 1

    def update(self, measurement_3):
        #Prediction step
        self.error_covariance_3 = self.error_covariance_3 + self.process_variance_3

        #Update step
        self.kalman_gain_3 = self.error_covariance_3 / (self.error_covariance_3 + self.measurement_variance_3)
        self.estimated_measurement_3 += self.kalman_gain_3 * (measurement_3 - self.estimated_measurement_3)
        self.error_covariance_3 = (1 - self.kalman_gain_3) * self.error_covariance_3

        return self.estimated_measurement_3
        
class KalmanFilter4:
    def __init__(self, process_variance, measurement_variance):
        self.process_variance_4 = process_variance
        self.measurement_variance_4 = measurement_variance
        self.estimated_measurement_4 = 0
        self.error_covariance_4 = 1
        self.kalman_gain_4 = 1

    def update(self, measurement_4):
        #Prediction step
        self.error_covariance_4 = self.error_covariance_4 + self.process_variance_4

        #Update step
        self.kalman_gain_4 = self.error_covariance_4 / (self.error_covariance_4 + self.measurement_variance_4)
        self.estimated_measurement_4 += self.kalman_gain_4 * (measurement_4 - self.estimated_measurement_4)
        self.error_covariance_4 = (1 - self.kalman_gain_4) * self.error_covariance_4

        return self.estimated_measurement_4

class KalmanFilter5:
    def __init__(self, process_variance, measurement_variance):
        self.process_variance_5 = process_variance
        self.measurement_variance_5 = measurement_variance
        self.estimated_measurement_5 = 0
        self.error_covariance_5 = 1
        self.kalman_gain_5 = 1

    def update(self, measurement_5):
        #Prediction step
        self.error_covariance_5 = self.error_covariance_5 + self.process_variance_5

        #Update step
        self.kalman_gain_5 = self.error_covariance_5 / (self.error_covariance_5 + self.measurement_variance_5)
        self.estimated_measurement_5 += self.kalman_gain_5 * (measurement_5 - self.estimated_measurement_5)
        self.error_covariance_5 = (1 - self.kalman_gain_5) * self.error_covariance_5

        return self.estimated_measurement_5
        
class KalmanFilter6:
    def __init__(self, process_variance, measurement_variance):
        self.process_variance_6 = process_variance
        self.measurement_variance_6 = measurement_variance
        self.estimated_measurement_6 = 0
        self.error_covariance_6 = 1
        self.kalman_gain_6 = 1

    def update(self, measurement_6):
        #Prediction step
        self.error_covariance_6 = self.error_covariance_6 + self.process_variance_6

        #Update step
        self.kalman_gain_6 = self.error_covariance_6 / (self.error_covariance_6 + self.measurement_variance_6)
        self.estimated_measurement_6 += self.kalman_gain_6 * (measurement_6 - self.estimated_measurement_6)
        self.error_covariance_6 = (1 - self.kalman_gain_6) * self.error_covariance_6

        return self.estimated_measurement_6
    
#Initialize the MPU6050 and the Kalman filter
# sensor = mpu6050(0x68)
# kalman_filter = KalmanFilter(process_variance=1e-5, measurement_variance=1e-2)

# bus = smbus.SMBus(1) 	# or bus = smbus.SMBus(0) for older version boards
# DeviceAddress = 0x68   # MPU6050 device address

# while True:
    # # Read gyro data (in degrees per second)
    # gyro_data = sensor.get_gyro_data()
    # gyro_x = gyro_data['0']
    # gyro_y = gyro_data['1']
    # gyro_z = gyro_data['2']

    # # Update Kalman filter with current measurements
    # filtered_x = kalman_filter.update(gyro_x)
    # filtered_y = kalman_filter.update(gyro_y)
    # filtered_z = kalman_filter.update(gyro_z)

    # # Print the filtered values
    # print(f"Filtered gyro values: X={filtered_x}, Y={filtered_y}, Z={filtered_z}")

    # # Wait before reading the next values
    # time.sleep(0.1)
