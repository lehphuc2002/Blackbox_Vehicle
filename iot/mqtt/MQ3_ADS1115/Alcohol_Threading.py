import time
from MQ3_ADS115 import MQ3Sensor

if __name__ == "__main__":

    mq3_sensor = MQ3Sensor(adc_channel=0, gain=1, vcc=5.0)
    mq3_sensor.start_reading()
    
    try:
        while True:
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        mq3_sensor.stop_reading()
        print("Sensor reading stopped.")
