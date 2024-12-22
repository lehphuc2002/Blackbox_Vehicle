import board
import busio
import digitalio
import adafruit_pcd8544
from PIL import Image, ImageDraw, ImageFont

def draw_tft(text_name, text_status):
    """
    Draw name and status on the TFT display with enhanced visual styling.
    Args:
        text_name (str): Name to display
        text_status (str): Status message to display
    """
    # Display constants
    BORDER = 3
    NAME_FONT_SIZE = 12
    STATUS_FONT_SIZE = 8
    LINE_SPACING = 3

    # Initialize SPI and the display
    spi = busio.SPI(board.SCK, MOSI=board.MOSI)
    dc = digitalio.DigitalInOut(board.D6)    # Data/command
    cs = digitalio.DigitalInOut(board.CE1)   # Chip select
    reset = digitalio.DigitalInOut(board.D5) # Reset
    display = adafruit_pcd8544.PCD8544(spi, dc, cs, reset)

    # Optimize display settings for better text clarity
    display.bias = 5
    display.contrast = 60

    # Turn on backlight
    backlight = digitalio.DigitalInOut(board.D13)
    backlight.switch_to_output()
    backlight.value = True

    # Clear display
    display.fill(0)
    display.show()

    # Create blank image for drawing
    image = Image.new("1", (display.width, display.height))
    draw = ImageDraw.Draw(image)

    # Draw elegant background frame
    draw.rectangle(
        (0, 0, display.width, display.height),
        outline=255,
        fill=0
    )
    
    # Inner decorative frame
    draw.rectangle(
        (BORDER, BORDER, display.width - BORDER - 1, display.height - BORDER - 1),
        outline=255,
        fill=0
    )

    # Load fonts
    try:
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", NAME_FONT_SIZE)
        font_status = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", STATUS_FONT_SIZE)
    except:
        font_name = ImageFont.load_default()
        font_status = ImageFont.load_default()

    # Format text
    text_name = text_name.upper()  # Make name uppercase for emphasis

    # Calculate text dimensions
    name_width, name_height = font_name.getsize(text_name)
    status_width, status_height = font_status.getsize(text_status)

    # Calculate positions for centered text
    name_x = (display.width - name_width) // 2
    name_y = (display.height // 3) - (name_height // 2)
    
    status_x = (display.width - status_width) // 2
    status_y = name_y + name_height + LINE_SPACING + 3

    # Draw decorative elements
    # Top line
    draw.line(
        (BORDER + 4, name_y - 2, display.width - BORDER - 5, name_y - 2),
        fill=255,
        width=1
    )
    
    # Bottom line
    draw.line(
        (BORDER + 4, status_y + status_height + 2, display.width - BORDER - 5, status_y + status_height + 2),
        fill=255,
        width=1
    )

    # Draw name with bold effect
    draw.text(
        (name_x, name_y),
        text_name,
        font=font_name,
        fill=255
    )

    # Draw status with a subtle indicator
    draw.text(
        (status_x, status_y),
        text_status,
        font=font_status,
        fill=255
    )

    # Add status indicator dot
    dot_radius = 2
    dot_x = status_x - dot_radius - 4
    dot_y = status_y + (status_height // 2)
    draw.ellipse(
        [dot_x - dot_radius, dot_y - dot_radius, 
         dot_x + dot_radius, dot_y + dot_radius],
        fill=255
    )

    # Show the final image
    display.image(image)
    display.show()

def main():
    """Main function to run the program."""
    not_card = {'name': 'None User', 'status': 'Driving single session'}
    text_name = not_card['name']
    text_status = not_card['status']

    try:
        draw_tft(text_name, text_status)
    except KeyboardInterrupt:
        print("Program stopped by user")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()