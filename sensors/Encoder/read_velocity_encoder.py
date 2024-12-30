import RPi.GPIO as GPIO
import time
from collections import deque
from threading import Lock
import logging
from datetime import datetime
import sys

class MotorVelocitySensor:
    """
    Professional DC Motor Velocity Sensor using X4 Quadrature Encoder
    - Motor: JGB37-520
    - Encoder: 11 PPR (Base)
    - Gear Ratio: 1:30
    - Mode: X4 Quadrature (4x multiplication)
    """
    
    def __init__(self, pin_a=15, pin_b=27, debug_mode=False):
        # Setup logging
        self._setup_logging(debug_mode)
        self.logger.info("Initializing Motor Velocity Sensor...")
        
        # GPIO Configuration
        self._PIN_A = pin_a
        self._PIN_B = pin_b
        
        # Motor Constants
        self._BASE_PPR = 11
        self._GEAR_RATIO = 30
        self._X4_MULTIPLIER = 4
        self._PULSES_PER_REV = self._BASE_PPR * self._GEAR_RATIO * self._X4_MULTIPLIER
        self._MAX_RPM = 333  # JGB37-520 max RPM
        
        # Measurement Configuration
        self._UPDATE_INTERVAL = 0.05  # 50ms for real-time performance
        self._BUFFER_SIZE = 5         # Moving average window
        self._MAX_UINT32 = 0xFFFFFFFF
        
        # Thread-safe variables
        self._lock = Lock()
        self._pulse_count = 0
        self._overflow_count = 0
        self._total_pulses = 0
        self._last_calc_pulses = 0
        
        # State variables
        self._last_state_a = 0
        self._last_state_b = 0
        self._last_calc_time = time.time()
        self._current_velocity = 0.0
        self._velocity_buffer = deque(maxlen=self._BUFFER_SIZE)
        self._is_running = False
        self._error_state = False
        
        # Initialize hardware
        self._initialize_hardware()
        
    def _setup_logging(self, debug_mode):
        """Configure logging with timestamps and appropriate level"""
        self.logger = logging.getLogger('MotorVelocitySensor')
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
        # File handler
        fh = logging.FileHandler('motor_velocity.log')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def _initialize_hardware(self):
        """Initialize GPIO and encoder hardware"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self._PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Setup X4 mode interrupts
            GPIO.add_event_detect(self._PIN_A, GPIO.BOTH, 
                                callback=self._encoder_callback,
                                bouncetime=1)
            GPIO.add_event_detect(self._PIN_B, GPIO.BOTH, 
                                callback=self._encoder_callback,
                                bouncetime=1)
            
            self._is_running = True
            self.logger.info("Hardware initialization complete")
            self.logger.debug(f"Encoder Resolution: {self._PULSES_PER_REV} PPR (X4 mode)")
            
        except Exception as e:
            self._error_state = True
            self.logger.error(f"Hardware initialization failed: {str(e)}")
            raise

    def _encoder_callback(self, channel):
        """X4 quadrature decoder callback"""
        if not self._is_running or self._error_state:
            return
            
        try:
            with self._lock:
                # Read current states
                current_a = GPIO.input(self._PIN_A)
                current_b = GPIO.input(self._PIN_B)
                
                # State transition detection
                state = (self._last_state_a << 3) | (self._last_state_b << 2) | \
                       (current_a << 1) | current_b
                
                # Direction determination
                if state in [0b1101, 0b0100, 0b0010, 0b1011]:
                    direction = 1
                elif state in [0b1110, 0b0111, 0b0001, 0b1000]:
                    direction = -1
                else:
                    return  # Invalid state transition
                
                # Update counters with overflow handling
                new_count = (self._pulse_count + direction) & self._MAX_UINT32
                
                if direction > 0 and new_count < self._pulse_count:
                    self._overflow_count += 1
                elif direction < 0 and new_count > self._pulse_count:
                    self._overflow_count -= 1
                
                self._pulse_count = new_count
                self._total_pulses = (self._overflow_count << 32) | self._pulse_count
                
                # Update states
                self._last_state_a = current_a
                self._last_state_b = current_b
                
        except Exception as e:
            self._error_state = True
            self.logger.error(f"Encoder callback error: {str(e)}")

    def _calculate_velocity(self):
        """Calculate current velocity in km/h"""
        try:
            current_time = time.time()
            delta_time = current_time - self._last_calc_time
            
            if delta_time >= self._UPDATE_INTERVAL:
                with self._lock:
                    current_total = self._total_pulses
                    delta_pulses = abs(current_total - self._last_calc_pulses)
                    self._last_calc_pulses = current_total
                
                # Calculate RPM
                rpm = (delta_pulses * 60) / (delta_time * self._PULSES_PER_REV)
                
                # Convert RPM to km/h (assuming 0.5m wheel diameter)
                wheel_circumference = 0.5 * 3.14159  # meters
                velocity_kmh = (rpm * wheel_circumference * 60) / 1000
                
                # Apply filtering and limits
                if 0 <= rpm <= self._MAX_RPM:
                    self._velocity_buffer.append(velocity_kmh)
                    self._current_velocity = sum(self._velocity_buffer) / len(self._velocity_buffer)
                
                self._last_calc_time = current_time
                
                # Debug logging
                self.logger.debug(
                    f"Pulses: {delta_pulses}, "
                    f"RPM: {rpm:.2f}, "
                    f"Velocity: {self._current_velocity:.2f} km/h"
                )
                
        except Exception as e:
            self._error_state = True
            self.logger.error(f"Velocity calculation error: {str(e)}")
            return 0.0
            
        return self._current_velocity

    @property
    def velocity(self):
        """Get current velocity in km/h"""
        if self._error_state:
            return 0.0
        return round(self._calculate_velocity(), 2)

    def get_diagnostic_data(self):
        """Get diagnostic data for debugging"""
        with self._lock:
            return {
                'total_pulses': self._total_pulses,
                'current_count': self._pulse_count,
                'overflow_count': self._overflow_count,
                'velocity_kmh': self._current_velocity,
                'error_state': self._error_state,
                'buffer_size': len(self._velocity_buffer)
            }

    def cleanup(self):
        """Clean up resources"""
        self._is_running = False
        GPIO.cleanup([self._PIN_A, self._PIN_B])
        self.logger.info("Sensor cleanup complete")

def main():
    """Main function for standalone operation"""
    try:
        # Create sensor instance with debug mode
        sensor = MotorVelocitySensor(debug_mode=True)
        print("\nMotor Velocity Sensor Started")
        print("Press Ctrl+C to stop")
        
        while True:
            # Get velocity and diagnostic data
            velocity = sensor.velocity
            # diagnostics = sensor.get_diagnostic_data()
            
            # Clear screen and display information
            # print("\033[H\033[J")  # Clear screen
            print("=== Motor Velocity Monitor ===")
            print(f"Current Velocity: {velocity:.2f} km/h")
            print("\nDiagnostic Data:")
            # print(f"Total Pulses: {diagnostics['total_pulses']}")
            # print(f"Current Count: {diagnostics['current_count']}")
            # print(f"Overflow Count: {diagnostics['overflow_count']}")
            # print(f"Buffer Size: {diagnostics['buffer_size']}")
            # print(f"Error State: {diagnostics['error_state']}")
            print("\nPress Ctrl+C to stop")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping sensor...")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        sensor.cleanup()
        print("Program terminated")

if __name__ == "__main__":
    main()