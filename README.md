# Black Box Car Vehicle
## Overview

This project focuses on the development of a **Black Box System** for vehicles, which captures critical data during vehicle operation. Using a Raspberry Pi 4, multiple sensors, and cloud integration, the system continuously monitors and records data such as speed, temperature, acceleration, alcohol levels, and RFID-based driver identification. In the event of an accident, the system automatically detects the event and pushes data to Firebase and ThingsBoard via MQTT for real-time tracking and analysis.

## Features

- **Raspberry Pi 4** as the core processing unit.
- **RFID Module** for driver identification and authentication. Also, tracking time driving of the driver and notification. RFID driver's license card designed according to Vietnamese law.
- **Temperature Sensor** to monitor environmental conditions inside or outside the vehicle.
- **Velocity Sensor** to measure the vehicle’s speed.
- **Alcohol Sensor** to detect alcohol levels from the driver.
- **Accelerometer** to track vehicle motion and detect accidents.
- **Camera** continuously records the journey along with coordinates and saves the video to a memory card when there is a possibility of an accident.
- **Accident Detection**: Automatic detection of abnormal events such as collisions.
- **GPS 4G Module (EM06)** for real-time location tracking.
- **Data Push to Firebase**: All data is stored securely in the cloud for further analysis.
- **MQTT Protocol** to send data to a **ThingsBoard Dashboard** for real-time monitoring.

## Data Flow

1. **Sensor Data Collection**: Data is continuously collected from sensors and processed by the Raspberry Pi.
2. **RFID Identification**: The driver is identified using RFID, their information and time driving track is logged.
3. **Accident Detection**: In case of sudden deceleration or impact, the accelerometer triggers an accident detection event.
4. **Data Upload**: All data (sensor readings, RFID info, GPS coordinates, etc.) is uploaded to Firebase and pushed to the ThingsBoard dashboard via MQTT.
5. **Real-time Monitoring**: The ThingsBoard dashboard provides live updates on the vehicle's status.
6. **The map** of the route the vehicle has traveled is saved. When exceeding speed, image will be taken and push to Firebase to store the evidence.

## Dashboard - ThingsBoard

The data is visualized in real-time on a custom **ThingsBoard** dashboard, where you can track:
- Driver information (from RFID)
- Information of vehicle like: speed, temperature, alcohol levels, etc.
- GPS location, map running.
- Accident alerts.

## Technologies

- **Cloud Services**: Firebase for data storage, ThingsBoard for dashboard visualization
- **Protocols**: MQTT for data transfer
- **Programming Language**: Python

## Future Improvements

- Integration with emergency services for automatic accident alerting.
- Expansion of sensor data for additional vehicle metrics.
- Mobile app for user-side monitoring and reporting.
