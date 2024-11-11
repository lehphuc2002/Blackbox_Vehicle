import board
import busio
import digitalio
import adafruit_pcd8544
from PIL import Image, ImageDraw, ImageFont

def draw_tft(text_name, text_phone):
    """Draw text on the TFT display."""
    BORDER = 5
    FONTSIZE = 10

    # Initialize SPI and the display
    spi = busio.SPI(board.SCK, MOSI=board.MOSI)
    dc = digitalio.DigitalInOut(board.D6)  # Data/command
    cs = digitalio.DigitalInOut(board.CE1)  # Chip select
    reset = digitalio.DigitalInOut(board.D5)  # Reset
    display = adafruit_pcd8544.PCD8544(spi, dc, cs, reset)

    # Set display settings
    display.bias = 4
    display.contrast = 60

    # Turn on backlight
    backlight = digitalio.DigitalInOut(board.D13)  # Backlight
    backlight.switch_to_output()
    backlight.value = True

    # Clear display
    display.fill(0)
    display.show()

    # Create image for drawing
    image = Image.new("1", (display.width, display.height))
    draw = ImageDraw.Draw(image)

    # Draw background and border
    draw.rectangle((0, 0, display.width, display.height), outline=255, fill=255)
    draw.rectangle(
        (BORDER, BORDER, display.width - BORDER - 1, display.height - BORDER - 1),
        outline=0,
        fill=0,
    )

    # Load font
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONTSIZE)

    # Clear previous content and display new text
    display.fill(0)
    (font_width_name, font_height_name) = font.getsize(text_name)
    (font_width_phone, font_height_phone) = font.getsize(text_phone)

    # Display name
    draw.text(
        (display.width // 2 - font_width_name // 2, display.height // 4 - font_height_name // 2),
        text_name,
        font=font,
        fill=255
    )

    # Display phone number
    offset = 10
    draw.text(
        (display.width // 2 - font_width_phone // 2, (display.height // 2) + font_height_phone - offset),
        text_phone,
        font=font,
        fill=255
    )

    # Show the new content on the display
    display.image(image)
    display.show()

def main():
    """Main function to run the program."""
    not_card = {'name': 'None User', 'phone': 'None'}
    text_name = not_card['name']
    text_phone = not_card['phone']

    
    try:
        draw_tft(text_name, text_phone)  
    except KeyboardInterrupt:
        print("Program stopped by user")


if __name__ == "__main__":
    main()
