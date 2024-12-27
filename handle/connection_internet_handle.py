# Thesis/handle/connection_internet_handle.py
import threading
import time
import socket
import urllib.request
import logging
from typing import Optional

class InternetConnectionMonitor:
    def __init__(self, check_interval: int = 5):
        self._connection_status: bool = False
        self._check_interval: int = check_interval
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_flag: threading.Event = threading.Event()
        
        # Multiple reliable hosts for checking connection
        self._hosts = [
            ("8.8.8.8", 53),       # Google DNS
            ("1.1.1.1", 53),       # Cloudflare DNS
            ("208.67.222.222", 53)  # OpenDNS
        ]
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _check_connection(self) -> bool:
        """Check internet connectivity using multiple methods"""
        # Method 1: Socket connection to DNS servers
        for host, port in self._hosts:
            try:
                socket.create_connection((host, port), timeout=2)
                return True
            except OSError:
                continue

        # Method 2: HTTP request
        try:
            urllib.request.urlopen("http://www.google.com", timeout=2)
            return True
        except Exception:
            pass

        return False

    def _monitor_connection(self) -> None:
        """Monitor internet connection in a separate thread"""
        previous_status = None
        
        while not self._stop_flag.is_set():
            try:
                current_status = self._check_connection()
                self._connection_status = current_status

                # Only log when status changes
                if current_status != previous_status:
                    if current_status:
                        self.logger.info("Internet connection established")
                    else:
                        self.logger.warning("Internet connection lost")
                    previous_status = current_status

            except Exception as e:
                self.logger.error(f"Error monitoring connection: {str(e)}")

            self._stop_flag.wait(self._check_interval)

    def start_monitoring(self) -> None:
        """Start the connection monitoring thread"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_flag.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_connection, 
                daemon=True
            )
            self._monitor_thread.start()
            self.logger.info("Connection monitoring started")

    def stop_monitoring(self) -> None:
        """Stop the connection monitoring thread"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop_flag.set()
            self._monitor_thread.join()
            self.logger.info("Connection monitoring stopped")

    def get_connection_status(self) -> bool:
        """Return the current connection status"""
        return self._connection_status

# Create a singleton instance
connection_monitor = InternetConnectionMonitor()