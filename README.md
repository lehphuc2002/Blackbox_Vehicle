# Black Box Car Vehicle - Thesis Project
## Overview

This project focuses on the development of a **Black Box System** for vehicles, which captures critical data during vehicle operation. Using a Raspberry Pi 4, multiple sensors, and cloud integration, the system continuously monitors and records data such as speed, temperature, acceleration, alcohol levels, and RFID-based driver identification. In the event of an accident, the system automatically detects the event and pushes data to Firebase and ThingsBoard via MQTT for real-time tracking and analysis.

## Features

- **Raspberry Pi 4** as the core processing unit.
- **RFID Module** for driver identification and authentication.
- **Temperature Sensor** to monitor environmental conditions inside or outside the vehicle.
- **Velocity Sensor** to measure the vehicle’s speed.
- **Alcohol Sensor** to detect alcohol levels from the driver.
- **Accelerometer** to track vehicle motion and detect accidents.
- **Accident Detection**: Automatic detection of abnormal events such as collisions.
- **GPS 4G Module (EM06)** for real-time location tracking.
- **Data Push to Firebase**: All data is stored securely in the cloud for further analysis.
- **MQTT Protocol** to send data to a **ThingsBoard Dashboard** for real-time monitoring.

## System Components

- **Raspberry Pi 4**: Central controller for the system.
- **RFID Module**: Used for driver identification and recording.
- **Sensors**:
  - **Temperature Sensor**
  - **Velocity Sensor**
  - **Alcohol Sensor**
  - **Accelerometer**
- **GPS 4G Module (EM06)**: For real-time GPS tracking.
- **Firebase**: Cloud storage for sensor data.
- **ThingsBoard**: IoT dashboard for live monitoring via MQTT.

## Usage

The system starts collecting data from all connected sensors (RFID, temperature, velocity, alcohol, and accelerometer). In case of an accident, the accelerometer detects the event, and the data is sent to Firebase and ThingsBoard via MQTT for real-time monitoring and analysis.

## Data Flow

1. **Sensor Data Collection**: Data is continuously collected from sensors and processed by the Raspberry Pi.
2. **RFID Identification**: The driver is identified using RFID, and their information is logged.
3. **Accident Detection**: In case of sudden deceleration or impact, the accelerometer triggers an accident detection event.
4. **Data Upload**: All data (sensor readings, RFID info, GPS coordinates) is uploaded to Firebase and pushed to the ThingsBoard dashboard via MQTT.
5. **Real-time Monitoring**: The ThingsBoard dashboard provides live updates on the vehicle's status.

## Dashboard - ThingsBoard

The data is visualized in real-time on a custom **ThingsBoard** dashboard, where you can track:
- Driver information (from RFID)
- Speed, temperature, and alcohol levels
- GPS location
- Accident alerts

## Technologies

- **Hardware**: Raspberry Pi 4, RFID module, temperature sensor, velocity sensor, alcohol sensor, accelerometer, GPS 4G module (EM06)
- **Cloud Services**: Firebase for data storage, ThingsBoard for dashboard visualization
- **Protocols**: MQTT for data transfer
- **Programming Language**: Python

## Future Improvements

- Integration with emergency services for automatic accident alerting.
- Expansion of sensor data for additional vehicle metrics.
- Mobile app for user-side monitoring and reporting.
