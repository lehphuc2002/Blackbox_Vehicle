# sensors/GPS/gps_simulator.py

import time
import threading
import math
import random
from datetime import datetime

class GPSSimulator:
    def __init__(self, start_lat=35.6895, start_lon=139.6917):  # Default: Tokyo coordinates
        self.latitude = start_lat
        self.longitude = start_lon
        self.running = False
        self.thread = None
        self.speed = 0  # km/h
        self.heading = 0  # degrees, 0 = North, 90 = East
        self._lock = threading.Lock()

    def start(self):
        """Start the GPS simulation thread"""
        self.running = True
        self.thread = threading.Thread(target=self._simulate_movement, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the GPS simulation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def destroy(self):
        """Cleanup resources"""
        self.stop()

    def set_speed(self, speed):
        """Set the simulation speed in km/h"""
        with self._lock:
            self.speed = speed

    def set_heading(self, heading):
        """Set the heading in degrees (0-360)"""
        with self._lock:
            self.heading = heading % 360

    def get_current_location(self):
        """Return current simulated GPS coordinates"""
        with self._lock:
            return self.latitude, self.longitude

    def _simulate_movement(self):
        """Simulate GPS movement based on speed and heading"""
        while self.running:
            with self._lock:
                if self.speed > 0:
                    # Convert speed from km/h to degrees per second
                    # Approximate conversion: 1 degree latitude = 111 km
                    speed_deg_per_sec = (self.speed / 3600) / 111

                    # Calculate latitude and longitude changes
                    lat_change = speed_deg_per_sec * math.cos(math.radians(self.heading))
                    lon_change = speed_deg_per_sec * math.sin(math.radians(self.heading))

                    # Add some random noise to simulate GPS inaccuracy
                    noise = random.uniform(-0.00001, 0.00001)
                    
                    # Update position
                    self.latitude += lat_change + noise
                    self.longitude += lon_change + noise

                    # Keep longitude within -180 to 180 range
                    if self.longitude > 180:
                        self.longitude -= 360
                    elif self.longitude < -180:
                        self.longitude += 360

                    # Keep latitude within -90 to 90 range
                    if self.latitude > 90:
                        self.latitude = 90
                    elif self.latitude < -90:
                        self.latitude = -90

            time.sleep(1)  # Update position every second

    def simulate_route(self, waypoints, speed=30):
        """
        Simulate movement along a predefined route
        waypoints: list of (lat, lon) tuples
        speed: speed in km/h
        """
        if not waypoints:
            return

        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            # Calculate heading to next waypoint
            delta_lon = end[1] - start[1]
            y = math.sin(delta_lon) * math.cos(end[0])
            x = math.cos(start[0]) * math.sin(end[0]) - math.sin(start[0]) * math.cos(end[0]) * math.cos(delta_lon)
            heading = math.degrees(math.atan2(y, x))
            
            # Set current position and movement parameters
            self.latitude = start[0]
            self.longitude = start[1]
            self.set_speed(speed)
            self.set_heading(heading)

            # Wait until we're close to the destination
            while self.running:
                current_lat, current_lon = self.get_current_location()
                distance = self._calculate_distance(current_lat, current_lon, end[0], end[1])
                if distance < 0.1:  # Within 100 meters
                    break
                time.sleep(1)

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c