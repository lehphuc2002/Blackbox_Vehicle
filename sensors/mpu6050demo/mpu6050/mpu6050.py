from Kalman import KalmanFilter1 
from Kalman import KalmanFilter2
from Kalman import KalmanFilter3
from Kalman import KalmanFilter4
from Kalman import KalmanFilter5
from Kalman import KalmanFilter6
import smbus
import time
import numpy as np
from scipy.optimize import curve_fit
import pandas as pd
from datetime import datetime
import math
import sys 
from mpu6050lib import mpu6050

#set up Kalman filter
kalman_filter_1 = KalmanFilter1(process_variance=1e-5, measurement_variance=1e-2)
kalman_filter_2 = KalmanFilter2(process_variance=1e-5, measurement_variance=1e-2)
kalman_filter_3 = KalmanFilter3(process_variance=1e-5, measurement_variance=1e-2)
kalman_filter_4 = KalmanFilter4(process_variance=1e-5, measurement_variance=1e-2)
kalman_filter_5 = KalmanFilter5(process_variance=1e-5, measurement_variance=1e-2)
kalman_filter_6 = KalmanFilter6(process_variance=1e-5, measurement_variance=1e-2)

def accel_cal(cal_size):
    print("-" * 50)
    print("Accelerometer Calibration")
    mpu_offsets = [[], [], []]
    axis_vec = ['z', 'y', 'x']
    cal_directions = ["upward", "downward", "perpendicular to gravity"] #"downward",
    cal_indices = [2, 1, 0]
    for qq, ax_qq in enumerate(axis_vec):
        ax_offsets = [[], [], []]
        print("-" * 50)
        for direc_ii, direc in enumerate(cal_directions):
            input("-" * 8 + f" Press Enter and Keep IMU Steady to Calibrate the Accelerometer with the -{ax_qq}-axis pointed {direc}")
            [mpu6050_conv() for ii in range(0, cal_size)]
            mpu_array = []
            while len(mpu_array) < cal_size:
                try:
                    ax, ay, az = get_accel()
                    mpu_array.append([ax, ay, az])
                except:
                    continue
            ax_offsets[direc_ii] = np.array(mpu_array)[:, cal_indices[qq]]

        popts, _ = curve_fit(accel_fit, np.append(np.append(ax_offsets[0],
                                                             ax_offsets[1]), ax_offsets[2]),
                             np.append(np.append(1.0 * np.ones(np.shape(ax_offsets[0])),
                                              -1.0 * np.ones(np.shape(ax_offsets[1]))),
                                       0.0 * np.ones(np.shape(ax_offsets[2]))),
                             maxfev=10000)
        mpu_offsets[cal_indices[qq]] = popts
    print('Accelerometer Calibrations Complete')
    return mpu_offsets

def gyro_filter():

    _, _, _, w_x, w_y, w_z = mpu6050_conv()
    
    filtered_x = kalman_filter_1.update(w_x)
    filtered_y = kalman_filter_2.update(w_y)
    filtered_z = kalman_filter_3.update(w_z)
    return filtered_x, filtered_y, filtered_z
    
def gyro_calib(cal_size):
    mpu_array = []
    gyro_offsets = [0.0, 0.0, 0.0]
    while 1:
        try:
            wx, wy, wz = gyro_filter()
        except:
            continue

        mpu_array.append([wx, wy, wz])

        if np.shape(mpu_array)[0] == cal_size:
            for qq in range(0, 3):
                gyro_offsets[qq] = np.mean(np.array(mpu_array)[:, qq])
            break
    print('Gyro Calibration Complete')
    return gyro_offsets
    
def mpu6050_conv():
        # Assuming get_accel_data() and get_gyro_data() are functions that return tuples
        mpu = mpu6050(0x68)
        acc_data = mpu.get_accel_data()
        gyr_data = mpu.get_gyro_data()
        return acc_data['0'],acc_data['1'],acc_data['2'],gyr_data['0'],gyr_data['1'],gyr_data['2']

def is_identity_matrix(matrix):
    rows = len(matrix)
    cols = len(matrix[0])

    if rows != cols:
        return False

    for i in range(rows):
        for j in range(cols):
            if i == j:
                if matrix[i][j] != 1:
                    return False
            else:
                if matrix[i][j] != 0:
                    return False

    return True

def accel_fit(x_input, m_x, b):
    return (m_x * x_input) + b

def get_accel():
    
    ax, ay, az, _, _, _ = mpu6050_conv()
    filtered_accx = ax#kalman_filter_4.update(ax)
    filtered_accy = ay#kalman_filter_5.update(ay)
    filtered_accz = az#kalman_filter_6.update(az)
    
    return filtered_accx, filtered_accy, filtered_accz

def round_matrix(matrix, decimal=0):
    rounded_matrix = [[round(element, decimal) for element in row] for row in matrix]
    return rounded_matrix

def mul_matrix(matrix1, matrix2):
    size = len(matrix1)
    result = [[0] * size for _ in range(size)]

    for i in range(size):
        for j in range(size):
            for k in range(size):
                result[i][j] += matrix1[i][k] * matrix2[k][j]
    return result



if __name__ == "__main__":
    
    Rx=np.eye(3)
    Ry=np.eye(3)
    Rz=np.eye(3)
    print('recording data')
    accel_offests=np.zeros(3)
    t = 0
    roll = 0
    pitch = 0
    yaw = 0
    sample_freq = 1000
    time_interval = 1.0 / sample_freq
    alpha = 0.98
    dt = 0
    start_time = time.time()
    ax, ay, az = get_accel()
    R_rotate = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    if (is_identity_matrix(R_rotate) == False):
        R_rotate = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    
    #Calib ofsets
    gyro_offsets = gyro_calib(500)
    accel_offests = accel_cal(200)
  
    
    ax, ay, az = get_accel()
    ax =ax-accel_offests[0]
    ay =ay-accel_offests[1]  
    az =az-accel_offests[2]
   
    # print("ACCX" + " " + str(ax))
    # print()
    # print("AccY" + " " + str(ay))
    # print()
    # print("AccZ" + " " + str(az))
    # print()
    with open('Acc.txt', 'w', encoding='utf-8'):
        pass
    with open('Rotate_matrix.txt', 'a', encoding='utf-8') as file:
        file.writelines("\n" + str(R_rotate))
    acc_0  = [ax[0],ay[0],az[0]]

    time.sleep(1)
    while 1:
        # if (time.time() - start_time) > time_interval:
            dt = time.time() - start_time
            start_time = time.time()
            # try:

            ax, ay, az = get_accel()
                # #mx, my, mz = AK8963_conv()
            # except:
                # continue

            ax -=accel_offests[0]
            ay -=accel_offests[1]
            az -=accel_offests[2]
            
            acc= [ax[0], ay[0], az[0]]

            wx, wy, wz = gyro_filter()
            
            wx -= gyro_offsets[0]
            wy -= gyro_offsets[1]
            wz -= gyro_offsets[2]
            
            print("gyroX" + " " + str(wx))
            print()
            print("gyroY" + " " + str(wy))
            print()
            print("GyroZ" + " " + str(wz))
            print()
            
            roll = wx*dt*3.14/180
            pitch = wy*dt*3.14/180
            yaw = wz*dt*3.14/180
            
            goc =[roll, pitch, yaw]
            
            print("Roll" + " " + str(roll))
            print()
            print("Pitch" + " " + str(pitch))
            print()
            print("Yaw" + " " + str(yaw))
            print()
            
            Rx=[[1, 0, 0], [0, math.cos(roll), math.sin(roll)], [0, -math.sin(roll), math.cos(roll)]]
            Rx = round_matrix(Rx, decimal = 5)
            Ry=[[math.cos(pitch), 0, -math.sin(pitch)], [0, 1, 0], [math.sin(pitch), 0, math.cos(pitch)]]
            Ry = round_matrix(Ry, decimal = 5)
            Rz=[[math.cos(yaw), math.sin(yaw), 0], [-math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]]
            Rz = round_matrix(Rz, decimal = 5)
                        
            R_rotate = mul_matrix(Rz, R_rotate)
            R_rotate = mul_matrix(Ry, R_rotate)
            R_rotate = mul_matrix(Rx, R_rotate)
            
            with open('Rotate_matrix2.txt', 'a', encoding='utf-8') as file:
                file.writelines("\n" + str(R_rotate))

            for index, row in enumerate(R_rotate):
                print(f"rowR {index + 1}:  {row}")
                print()
            # #acc= [ax[0], ay[0], az[0]]
            print("AccX" + " " + str(acc[0]))
            print()
            print("AccY" + " " + str(acc[1]))
            print()
            print("AccZ" + " " + str(acc[2]))
            print()
            
            #acc_global= np.dot(R_rotate, ((np.dot(np.linalg.inv(R_rotate),acc)) - acc_0))
            acc_global= acc - np.dot(R_rotate, acc_0)
            # for index, row in enumerate(acc_0):
                # print(f"ACC ban dau {index + 1}:  {row}")
                # print()
            
            # for index, row in enumerate(np.dot(np.linalg.inv(R_rotate),acc)):
                # print(f"Acc hien tai {index + 1}:  {row}")
                # print()

            for index, row in enumerate(acc_global):
                print(f"a tinh tien {index + 1}:  {row}")
                print()
      
            with open('Acc.txt', 'a', encoding='utf-8') as file:
                file.writelines("\n" + str(acc_global))

            time.sleep(0.03)
