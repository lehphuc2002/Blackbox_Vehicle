#Thesis/sensors/MQ3_ADS1115/MQ3_ADS115.py
import time
import threading
import busio
import board
import Adafruit_ADS1x15 as ADS
import Adafruit_GPIO.I2C as I2C
from .alcohol_concentration_interpolator import AlcoholConcentrationInterpolator


class MQ3Sensor:
    def __init__(self, adc_channel=0, gain=1, vcc=5.0):
        """
        Initializes the MQ3 sensor class.
        
        Args:
            adc_channel (int): The ADS1115 channel to which MQ3 is connected (default: 0).
            gain (int): Gain setting for ADS1115, use 1 for 0-4.096V (default: 1).
            vcc (float): Supply voltage to the MQ3 sensor (default: 5.0V).
        """
        I2C.require_repeated_start()
        i2c = busio.I2C(board.SCL, board.SDA)
        self.adc = ADS.ADS1115(busnum=1)
        self.adc_channel = adc_channel
        self.gain = gain
        self.vcc = vcc
        self.interpolator = AlcoholConcentrationInterpolator()
        self.running = True

    def read_sensor(self):
            # Read ADC value from ADS1115
            adc_value = self.adc.read_adc(self.adc_channel, gain=self.gain)
            
            # Convert ADC value to voltage (ADC 16 bit, 2^15 = 32768)
            voltage = adc_value * (5 / 32768.0)
            
            # Calculate Rs/Ro ratio using the Vcc and the voltage from the sensor
            if voltage != 0:
                Rs = (self.vcc - voltage) / voltage * 200
                Rs_Ro_ratio = Rs / 1900
            else:
                Rs_Ro_ratio = None 
            
            return adc_value, voltage, Rs_Ro_ratio

    def get_concentration(self):
        # get alcohol concentration from interpolator
        adc_value, voltage, Rs_Ro_ratio = self.read_sensor()
        self.concentration = None
        if Rs_Ro_ratio is not None:
            self.concentration = self.interpolator.get_concentration(Rs_Ro_ratio) * 10
        return self.concentration

    def start_reading(self):
        threading.Thread(target=self._read_continuously, daemon=True).start()

    def _read_continuously(self):
        while self.running:
            self.concentration = self.get_concentration()
            if self.concentration is not None:
                print(f"Concentration (mg/100ml): {self.concentration:.2f}")
            else:
                print("Invalid Rs/Ro ratio, concentration cannot be calculated.")
            time.sleep(1)  

    def stop_reading(self):
        self.running = False



