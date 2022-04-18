from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from adafruit_epd.epd import Adafruit_EPD

small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
medium_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
large_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)

# RGB Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

class CTA_Graphics:
    def __init__(self, display):

        self.small_font = small_font
        self.medium_font = medium_font
        self.large_font = large_font

        self.display = display

        self._metro_icon = None
        self._destination_name_1 = None
        self._location_name_1 = None
        self._arrival_minutes_1 = None
        self._destination_name_2 = None
        self._location_name_2 = None
        self._arrival_minutes_2 = None
        self._line = None
        self._time_text = None

    def display_metro(self, cta_status):
        
        count = 0
        while count < len(cta_status):
            try:
                destination_name_1 = cta_status[count]['line_and_destination']
                self._destination_name_1 = destination_name_1
                print('Destination 1: ' + destination_name_1)
                
                location_name_1 = cta_status[count]['station_name']
                self._location_name_1 = location_name_1
                print('Station Name 1: ' + location_name_1)
                
                arrival_minutes_1 = cta_status[count]['estimated_times']
                self._arrival_minutes_1 = arrival_minutes_1
                print('Arrival Status: ' + arrival_minutes_1)
            except:
                destination_name_1 = ""
                self._destination_name_1 = ""
                location_name_1 = ""
                self._location_name_1 = ""
                arrival_minutes_1 = ""
                self._arrival_minutes_1 = ""
            count += 1
            try:
                destination_name_2 = cta_status[count]['line_and_destination']
                self._destination_name_2 = destination_name_2
                print('Destination 2: ' + destination_name_2)
                
                location_name_2 = cta_status[count]['station_name']
                self._location_name_2 = location_name_2
                print('Station Name 2: ' + location_name_2)
                
                arrival_minutes_2 = cta_status[count]['estimated_times']
                self._arrival_minutes_2 = arrival_minutes_2
                print('Arrival Status: ' + arrival_minutes_2)
            except:
                destination_name_2 = ""
                self._destination_name_2 = ""
                location_name_2 = ""
                self._location_name_2 = ""
                arrival_minutes_2 = ""
                self._arrival_minutes_2 = ""
            count += 1

        self.update_time()
        self.update_display()

    def update_time(self):
        self._time_text = datetime.strftime(datetime.now(), "%H:%M")

    def update_display(self):
        self.display.fill(Adafruit_EPD.WHITE)
        image = Image.new("RGB", (self.display.width, self.display.height), color=WHITE)
        draw = ImageDraw.Draw(image)

        # Draw the time
        (font_width, font_height) = medium_font.getsize(self._time_text)
        draw.text(
            (self.display.width - font_width - 5, 5),
            self._time_text,
            font=self.medium_font,
            fill=BLACK,
        )

        # Draw the destination
        (font_width, font_height) = medium_font.getsize(self._destination_name)
        draw.text(
            (5, 5),
            self._destination_name,
            font=self.medium_font,
            fill=BLACK,
        )

        # Draw the line
        (font_width, font_height) = large_font.getsize(self._line)
        draw.text(
            (5, self.display.height - font_height * 4),
            self._line,
            font=self.large_font,
            fill=BLACK,
        )
        
        # Draw line break
        draw.line([(0, self.display.height / 2), (self.display.width, self.display.height / 2)], BLACK, 1) 
         
        # Draw the arrival time
        (font_width, font_height) = large_font.getsize(self._arrival_minutes)
        draw.text(
            (
                self.display.width - font_width - 5,
                self.display.height - font_height * 4,
            ),
            self._arrival_minutes,
            font=self.large_font,
            fill=BLACK,
        )

        # Draw progress
        if not self._has_arrived:
            box_width = self.display.width / 10
            box_height = self.display.width / 10
            i = 0
            for i in range(10):
                x0 = box_width * i + 1
                y0 = self.display.height - (self.display.height / 4)
                x1 = (box_width * 2) * i
                y1 = (self.display.height - (self.display.height / 4)) + box_height
                # draw.rounded_rectangle([(x0, y0), (x1, y1)], 2, BLACK, BLACK, 30)
            self._progress = self._progress * 2
       
        self.display.image(image)
        self.display.display()
