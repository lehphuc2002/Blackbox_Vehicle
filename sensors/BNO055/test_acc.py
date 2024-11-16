import smbus
import time

BNO055_ADDRESS = 0x29
ACCEL_DATA_REG = 0x08  # Example register for accelerometer data (check BNO055 datasheet)

bus = smbus.SMBus(1)  # Initialize I2C bus

# Read 6 bytes of accelerometer data (AX, AY, AZ)
def read_accel_data():
    try:
        accel_data = bus.read_i2c_block_data(BNO055_ADDRESS, ACCEL_DATA_REG, 6)
        ax = (accel_data[1] << 8) | accel_data[0]
        ay = (accel_data[3] << 8) | accel_data[2]
        az = (accel_data[5] << 8) | accel_data[4]

        print(f"Accelerometer Data - X: {ax}, Y: {ay}, Z: {az}")
    except Exception as e:
        print(f"Error reading accelerometer data: {e}")

# Run the test
while True:
    read_accel_data()
    time.sleep(1)
