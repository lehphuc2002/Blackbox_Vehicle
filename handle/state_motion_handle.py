from enum import Enum
from datetime import datetime
import threading
import math
import time
import json
from collections import deque


class VehicleState(Enum):
    STOP = "STOPPED"  # Temporarily stopped with engine on
    IDLE = "PARKED"  # Parked with engine off
    RUN = "RUNNING"  # In motion


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

        # Buffers
        self.gps_buffer = deque(maxlen=5)
        self.accel_buffer = deque(maxlen=10)
        self.velocity_buffer = deque(maxlen=5)

        # Thresholds
        self.SPEED_THRESHOLD = 2.0  # km/h
        self.ACCEL_THRESHOLD = 0.15  # m/s²
        self.GPS_DISTANCE_THRESHOLD = 0.003  # km
        self.IDLE_TIMEOUT = 300  # 5 minutes
        self.MIN_SAMPLES_FOR_DECISION = 3

        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _update_loop(self):
        while self.running:
            try:
                gps_location = (self.sensor_handler.latitude, self.sensor_handler.longitude)
                velocity = self.sensor_handler.velocity
                acceleration = self.sensor_handler.bno055.linear_accel_data

                # Print sensor data for debugging
                print(f"Sensor Data -> GPS: {gps_location}, Velocity: {velocity}, Acceleration: {acceleration}")

                self.update_state(gps_location, velocity, acceleration)

                # Periodically print current state
                with self._state_lock:
                    current_duration = time.time() - self.state_start_time
                    print(f"Current State: {self.current_state.value}, Duration: {format_duration(current_duration)}", end="\r")
                # time.sleep(0.2)  # 5Hz update rate
                time.sleep(2)
            except Exception as e:
                print(f"Error in update loop: {e}")
                time.sleep(1)

    def update_state(self, gps_location, velocity, acceleration):
        with self._state_lock:
            # Update buffers
            if gps_location:
                self.gps_buffer.append((gps_location, time.time()))
            self.velocity_buffer.append((velocity, time.time()))
            self.accel_buffer.append((acceleration, time.time()))

            is_moving = self._check_movement_status()
            new_state = self._determine_state(is_moving)

            if new_state != self.current_state:
                self._handle_state_change(new_state)

    def _check_movement_status(self):
        velocity_moving = self._check_velocity_movement()
        accel_moving = self._check_accelerometer_movement()
        gps_moving = self._check_gps_movement()

        print(f"Movement Status -> Velocity: {velocity_moving}, Accel: {accel_moving}, GPS: {gps_moving}")
        return any([velocity_moving, accel_moving, gps_moving])

    def _check_velocity_movement(self):
        if len(self.velocity_buffer) < self.MIN_SAMPLES_FOR_DECISION:
            return False

        avg_velocity = sum(v[0] for v in self.velocity_buffer) / len(self.velocity_buffer)
        print(f"Average Velocity: {avg_velocity} km/h")
        return avg_velocity > self.SPEED_THRESHOLD

    def _check_accelerometer_movement(self):
        if len(self.accel_buffer) < self.MIN_SAMPLES_FOR_DECISION:
            return False

        recent_accels = [
            math.sqrt(a[0][0]**2 + a[0][1]**2 + a[0][2]**2)
            for a in self.accel_buffer
        ]
        avg_accel = sum(recent_accels) / len(recent_accels)
        print(f"Average Acceleration: {avg_accel} m/s²")
        return avg_accel > self.ACCEL_THRESHOLD

    def _check_gps_movement(self):
        if len(self.gps_buffer) < self.MIN_SAMPLES_FOR_DECISION:
            return False

        total_distance = sum(
            self._calculate_gps_distance(self.gps_buffer[i][0], self.gps_buffer[i + 1][0])
            for i in range(len(self.gps_buffer) - 1)
        )
        print(f"Total GPS Distance: {total_distance} km")
        return total_distance > self.GPS_DISTANCE_THRESHOLD

    def _determine_state(self, is_moving):
        current_time = time.time()

        if is_moving:
            return VehicleState.RUN

        stop_duration = current_time - self.state_start_time
        if stop_duration > self.IDLE_TIMEOUT:
            return VehicleState.IDLE

        return VehicleState.STOP

    def _handle_state_change(self, new_state):
        current_time = time.time()
        duration = current_time - self.state_start_time

        # Publish the state change
        state_payload = json.dumps({
            "preSta": self.current_state.value,
            "newSta": new_state.value,
            "duration": format_duration(duration)
        })
        self.sensor_handler._publish_data(state_payload, "vehicle_state_change")

        # Print state change for debugging
        print(f"\nState Change Detected -> Previous: {self.current_state.value}, New: {new_state.value}, Duration: {format_duration(duration)}")

        # Update the current state and reset the timer
        self.current_state = new_state
        self.state_start_time = current_time

    def _calculate_gps_distance(self, loc1, loc2):
        R = 6371
        lat1, lon1 = math.radians(loc1[0]), math.radians(loc1[1])
        lat2, lon2 = math.radians(loc2[0]), math.radians(loc2[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def cleanup(self):
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
