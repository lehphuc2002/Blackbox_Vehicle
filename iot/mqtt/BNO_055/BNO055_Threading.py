from BNO055_lib import BNO055Sensor
import threading

# Usage example
if __name__ == "__main__":
    sensor = BNO055Sensor()

    accel_thread = threading.Thread(target=sensor.read_accelerometer_thread)
    linear_accel_thread = threading.Thread(target=sensor.read_linear_accelerometer_thread)
    accel_thread.daemon = True
    linear_accel_thread.daemon = True
    accel_thread.start()
    linear_accel_thread.start()

    try:
        sensor.main_1()
    except KeyboardInterrupt:
        # Stop the threads gracefully when Ctrl+C is pressed
        sensor.stop_threads()
        accel_thread.join()
        linear_accel_thread.join()
        print("Threads stopped and program exited.")