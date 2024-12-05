from enum import Enum
from datetime import datetime
import threading
import math
import time
import json
from collections import deque
from statistics import mean, stdev

class VehicleState(Enum):
    STOP = "STOPPED"      # Vehicle stopped with engine on
    IDLE = "PARKED"       # Vehicle parked with engine off
    RUN = "RUNNING"       # Vehicle in motion

def format_duration(seconds):
    """Format duration in human-readable format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)

class MotionStateHandler:
    def __init__(self, sensor_handler):
        self.sensor_handler = sensor_handler
        self.current_state = VehicleState.STOP
        self._state_lock = threading.Lock()
        self.state_start_time = time.time()
        self.last_movement_time = time.time()

        # State transition buffers
        self.gps_buffer = deque(maxlen=10)
        self.accel_buffer = deque(maxlen=60)
        self.velocity_buffer = deque(maxlen=10)
        
        # Movement detection windows
        self.movement_window = deque(maxlen=30)  # 30 seconds window
        self.stop_window = deque(maxlen=10)      # 10 seconds window

        # Thresholds
        self.SPEED_THRESHOLD = 3.0           # km/h
        self.ACCEL_MOVEMENT_THRESHOLD = 0.25 # m/s² for movement detection
        self.ACCEL_IDLE_THRESHOLD = 0.15     # m/s² for engine vibration detection
        self.GPS_DISTANCE_THRESHOLD = 0.003  # km
        self.IDLE_TIMEOUT = 30               # seconds
        self.MIN_MOVEMENT_CONFIDENCE = 0.7
        self.MIN_STOP_CONFIDENCE = 0.8
        self.MIN_SAMPLES = 5
        
        self.running = True
        # self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        # self.update_thread.start()

    def _update_loop(self):
        while self.running:
            try:
                gps_location = (self.sensor_handler.latitude, self.sensor_handler.longitude)
                velocity = self.sensor_handler.velocity
                acceleration = self.sensor_handler.bno055.linear_accel_data

                self._update_buffers(gps_location, velocity, acceleration)
                self._update_movement_status()
                self._update_state()

                time.sleep(0.5)  # Sample rate of 2Hz
                
            except Exception as e:
                print(f"Error in update loop: {e}")
                time.sleep(1)

    def _update_buffers(self, gps_location, velocity, acceleration):
        current_time = time.time()
        
        if gps_location and all(isinstance(x, (int, float)) for x in gps_location):
            self.gps_buffer.append((gps_location, current_time))
            
        if isinstance(velocity, (int, float)):
            self.velocity_buffer.append((velocity, current_time))
            
        if acceleration and all(isinstance(x, (int, float)) for x in acceleration):
            self.accel_buffer.append((acceleration, current_time))

    def _check_engine_running(self):
        """Check engine status using accelerometer vibration data."""
        if len(self.accel_buffer) < self.MIN_SAMPLES:
            return True  # Default to true if not enough samples
            
        recent_accels = [
            math.sqrt(sum(x*x for x in a[0])) 
            for a in self.accel_buffer 
            if time.time() - a[1] <= 5  # Last 5 seconds
        ]
        
        if not recent_accels:
            return True
            
        avg_vibration = mean(recent_accels)
        vibration_variance = stdev(recent_accels) if len(recent_accels) > 1 else 0
        print(f"avg_vibration to check engine running is {avg_vibration}")
        print(f"vibration_variance to check engine running is {vibration_variance}")
        
        # Engine is considered running if either:
        # 1. Average vibration is above idle threshold
        # 2. Vibration variance is significant
        return avg_vibration > self.ACCEL_IDLE_THRESHOLD or vibration_variance > 0.06

    def _update_movement_status(self):
        current_time = time.time()
        
        # Check all movement indicators
        velocity_moving = self._check_velocity_movement()
        accel_moving = self._check_accelerometer_movement()
        gps_moving = self._check_gps_movement()
        
        # Weighted voting system
        movement_score = (
            (velocity_moving * 0.5) +    # Velocity has highest weight
            (accel_moving * 0.3) +       # Acceleration second
            (gps_moving * 0.2)           # GPS least weight
        )
        
        is_moving = movement_score >= self.MIN_MOVEMENT_CONFIDENCE
        self.movement_window.append((is_moving, current_time))
        
        if is_moving:
            self.last_movement_time = current_time

    def _update_state(self):
        with self._state_lock:
            current_time = time.time()
            
            recent_movements = [m[0] for m in self.movement_window if current_time - m[1] <= 10]
            if not recent_movements:
                return
                
            movement_confidence = sum(recent_movements) / len(recent_movements)
            time_since_last_movement = current_time - self.last_movement_time
            engine_running = self._check_engine_running()
            
            new_state = self.current_state
            
            if movement_confidence >= self.MIN_MOVEMENT_CONFIDENCE:
                new_state = VehicleState.RUN
            elif movement_confidence <= (1 - self.MIN_STOP_CONFIDENCE):
                if time_since_last_movement >= self.IDLE_TIMEOUT and not engine_running:
                    new_state = VehicleState.IDLE
                else:
                    new_state = VehicleState.STOP
            
            if new_state != self.current_state:
                self._handle_state_change(new_state)
    def _check_velocity_movement(self):
        if len(self.velocity_buffer) < self.MIN_SAMPLES:
            return False
            
        recent_velocities = [v[0] for v in self.velocity_buffer 
                           if time.time() - v[1] <= 5]  # Last 5 seconds
        if not recent_velocities:
            return False
            
        avg_velocity = sum(recent_velocities) / len(recent_velocities)
        return avg_velocity > self.SPEED_THRESHOLD

    def _check_accelerometer_movement(self):
        if len(self.accel_buffer) < self.MIN_SAMPLES:
            return False
            
        recent_accels = [
            math.sqrt(sum(x*x for x in a[0])) 
            for a in self.accel_buffer 
            if time.time() - a[1] <= 3  # Last 3 seconds
        ]
        
        if not recent_accels:
            return False
            
        avg_accel = sum(recent_accels) / len(recent_accels)
        return avg_accel > self.ACCEL_MOVEMENT_THRESHOLD

    def _check_gps_movement(self):
        if len(self.gps_buffer) < self.MIN_SAMPLES:
            return False
            
        recent_positions = [g for g in self.gps_buffer 
                          if time.time() - g[1] <= 10]  # Last 10 seconds
        
        if len(recent_positions) < 2:
            return False
            
        total_distance = sum(
            self._calculate_gps_distance(recent_positions[i][0], recent_positions[i+1][0])
            for i in range(len(recent_positions)-1)
        )
        
        return total_distance > self.GPS_DISTANCE_THRESHOLD

    def _handle_state_change(self, new_state):
        current_time = time.time()
        duration = current_time - self.state_start_time

        # Create detailed state change payload
        state_payload = json.dumps({
            "preSta": self.current_state.value,
            "newSta": new_state.value,
            "duration": format_duration(duration)
        })
        
        self.sensor_handler._publish_data(state_payload, "vehicle_state_change")
        
        print(f"\nState Change: {self.current_state.value} -> {new_state.value}")
        print(f"Duration in previous state: {format_duration(duration)}")
        
        self.current_state = new_state
        self.state_start_time = current_time

    def _calculate_gps_distance(self, loc1, loc2):
        R = 6371  # Earth's radius in km
        lat1, lon1 = math.radians(loc1[0]), math.radians(loc1[1])
        lat2, lon2 = math.radians(loc2[0]), math.radians(loc2[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def cleanup(self):
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=1)