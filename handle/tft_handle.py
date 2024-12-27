from sensors.Nokia_5110_LCD.tft_display import draw_tft

class TFTHandler:
    def __init__(self):
        """Initialize the TFTHandler class."""
        pass  # No need to initialize anything, display handled in tft_display.py

    def display_user_info(self, data):
        """Display the user information on the TFT screen."""
        name = data.get('name', 'None User')
        phone_number = data.get('phone_number', 'None')
        status = data.get('status', 'Unauthorized')
        
        # Debugging statements
        print(f"Displaying on TFT: Name: {name}, Status: {status}")
        
        # Call the draw_tft function from tft_display to update the display
        draw_tft(str(name), str(status))

if __name__ == "__main__":
    # Example of usage
    tft_handler = TFTHandler()
    user_data = {'name': 'John Doe', 'phone_number': '1234567890', 'status': 'Authorized'}

    try:
        tft_handler.display_user_info(user_data)
    except KeyboardInterrupt:
        print("Display interrupted by user")
