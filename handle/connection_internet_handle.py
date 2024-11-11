# connection_internet_handle.py
import threading
import time
import subprocess

PING_HOST = "8.8.8.8"  # Host to ping for connection check
connection_status = False  # Global variable to store connection status

def check_internet_connection():
    """Ping a reliable host to check for an internet connection."""
    try:
        subprocess.check_call(['ping', '-c', '1', PING_HOST], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def monitor_connection():
    """Continuously monitor internet connection in a separate thread."""
    global connection_status
    while True:
        connection_status = check_internet_connection()
        if connection_status:
            print("Connected to the internet.")
        else:
            print("No internet connection.")
        time.sleep(5) 

def get_connection_status():
    """Return the current connection status."""
    print(f"Connection status is {connection_status}")
    return connection_status

# Start the connection monitor thread when the module is imported
# monitor_thread = threading.Thread(target=monitor_connection, daemon=True)
# monitor_thread.start()
