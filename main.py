"""ctapi by Brandon McFadden - Github: https://github.com/brandonmcfadd/ctapi"""
import math
import os
import json
import textwrap
import time  # Used to Get Current Time
import xml.etree.ElementTree as ET  # Used to Parse API Response
import re
# Used for converting Prediction from Current Time
from datetime import datetime, timedelta
from geopy import distance
from dotenv import load_dotenv  # Used to Load Env Var
import requests  # Used for API Calls
from waveshare_epd import epd2in13_V3
from PIL import Image, ImageDraw, ImageFont

epd = epd2in13_V3.EPD()
epd.init()
epd.Clear(0xFF)

bold_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
standard_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
standard_font_small = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
tweet_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-Bold.ttf", 17)

# Load .env variables
load_dotenv()

# ENV Variables
train_api_key = os.getenv('TRAIN_API_KEY')
bus_api_key = os.getenv('BUS_API_KEY')
twitter_api_key = os.getenv('TWITTER_API_KEY')
home_latitude = os.getenv('HOME_LATITUDE')
home_longitude = os.getenv('HOME_LONGITUDE')

# API URL's
TRAIN_TRACKER_URL = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key={}&stpid={}"
BUS_TRACKER_URL = "http://www.ctabustracker.com/bustime/api/v2/getpredictions?key={}&stpid={}&rt={}"
DIVVY_STATION_INFORMATION_URL = "https://gbfs.divvybikes.com/gbfs/en/station_information.json"
DIVVY_STATION_STATUS_URL = "https://gbfs.divvybikes.com/gbfs/en/station_status.json"
TWITTER_TWEETS_URL = "https://api.twitter.com/2/users/{}/tweets"

# Station/Stop Information for Trains/Buses - Bus Stop Items must contain equal number of items
# Enter the train station #'s to lookup
ENABLE_TRAIN_TRACKER = True  # Enter True or False to Enable or Disable Train Portion
TRAIN_STATION_STOP_IDS = "30197,30198"

# Enter the bus stop #'s for the stops you want estimated times for
ENABLE_BUS_TRACKER = True  # Enter True or False to Enable or Disable Bus Portion
BUS_STOP_STOP_IDS = "5465,1323,11264,18261"
# Enter the corresponding bus route # you want for each bus_stop_id
BUS_STOP_ROUTE_IDS = "76,74,82,82"

# Enter the Divvy station #'s to lookup
ENABLE_DIVVY_STATION_CHECK = True  # Enter True or False to Enable or Disable Divvy Portion
DIVVY_STATION_IDS = "a3a9607f-a135-11e9-9cda-0a87ae2ba916,a3b01578-a135-11e9-9cda-0a87ae2ba916"

# Twitter Lookup
ENABLE_TWITTER_LOOKUP = True

# Setting Up Variable for Storing Station Information - Will keep stations long turn
arrival_information = json.loads('{"trains":{},"buses":{},"bicycles":{}}')
REFRESH_DISPLAY = None


def train_api_call_to_cta(stop_id):
    """Gotta talk to the CTA and get Train Times"""
    print("Making CTA Train API Call...")
    api_response = requests.get(
        TRAIN_TRACKER_URL.format(train_api_key, stop_id))
    train_arrival_times(parse_api_response(api_response))
    return api_response


def bus_api_call_to_cta(stop_code, route_code):
    """Gotta talk to the CTA and get Bus Times"""
    print("Making CTA Bus API Call...")
    api_response = requests.get(
        BUS_TRACKER_URL.format(bus_api_key, stop_code, route_code))
    bus_eta_times(parse_api_response(api_response))
    return api_response


def divvy_api_call_station_information():
    """Gotta talk to the Divvy and get Station Status"""
    print("Making Divvy Station Information API Call...")
    api_response = requests.get(DIVVY_STATION_INFORMATION_URL)
    station_json = json.loads(api_response.content)
    return station_json


def divvy_api_call_station_status():
    """Gotta talk to the Divvy and get Station Status"""
    print("Making Divvy Station Stats API Call...")
    api_response = requests.get(DIVVY_STATION_STATUS_URL)
    station_json = json.loads(api_response.content)
    return station_json


def get_latest_cta_tweet():
    """Get the latest problems accoring to CTA Twitter"""
    print("Making Twitter API Call...")
    headers = {"Authorization": twitter_api_key}
    cta_user_id = "342782636"
    api_response = requests.get(TWITTER_TWEETS_URL.format(cta_user_id),
                                headers=headers)
    tweets_json = json.loads(api_response.content)
    tweet_counter = 0
    found_tweet = False
    # All status Tweets start with an Open Bracket - Hoping to filter out some of the other garbage
    while found_tweet is False:
        found_tweet = str(
            tweets_json["data"][tweet_counter]["text"]).startswith('[')
        latest_tweet = tweets_json["data"][tweet_counter]["text"]
        tweet_counter += 1
    return latest_tweet


def parse_api_response(api_response_input):
    """Turns XML Response into a useable format"""
    root = ET.fromstring(api_response_input.content)
    return root


def minutes_between(date_1, date_2):
    """Takes the difference between two times and returns the minutes"""
    date_1 = datetime.strptime(date_1, "%Y%m%d %H:%M:%S")
    date_2 = datetime.strptime(date_2, "%Y%m%d %H:%M:%S")
    difference = date_2 - date_1
    difference_in_minutes = int(difference / timedelta(minutes=1))
    return difference_in_minutes


def add_train_station_to_json(station_name):
    """Function is called if a new station is identified per API Call"""
    station_information = {}
    arrival_information["trains"][station_name] = station_information
    # persistent_station_tracking["trains"][station_name] = station_information


def add_train_stop_to_json(eta, stop_id):
    """Function is called if a new train stop is identified per API Call"""
    stop_information = {}
    station_name = eta.find('staNm').text

    stop_information["full_name"] = eta.find(
        'rt').text + " Line to " + eta.find('destNm').text
    stop_information["destination_name"] = eta.find('destNm').text
    stop_information["route"] = eta.find('rt').text
    stop_information["estimated_times"] = []

    arrival_information["trains"][station_name][stop_id] = stop_information


def add_bus_stop_to_json(prd, stop_id):
    """Function is called if a new bus stop is identified per API Call"""
    bus_to_replace = {
        " St": '',
        " Rd": "",
        " Ave": "",
        "Town Center": "Twn Ctr"
    }
    stop_information = {}
    for key, value in bus_to_replace.items():
        destination_name = re.sub(r"\b" + key + r"\b", value,
                                  prd.find('des').text)
    stop_information["full_name"] = prd.find(
        'rt').text + " to " + destination_name
    stop_information["destination_name"] = destination_name
    stop_information["route"] = prd.find('rt').text
    stop_information["stop_name"] = prd.find('stpnm').text
    stop_information["estimated_times"] = []

    arrival_information["buses"][stop_id] = stop_information


def train_arrival_times(train_api_response):
    """Takes each Train ETA (if exists) and appends to list"""
    for eta in train_api_response.iter('eta'):
        train_stop_id = eta.find('destNm').text
        train_station_name = eta.find('staNm').text

        if train_station_name not in arrival_information["trains"]:
            add_train_station_to_json(train_station_name)

        if train_stop_id in arrival_information["trains"][train_station_name]:
            add_train_eta_to_array(eta, train_station_name, train_stop_id)
        else:
            add_train_stop_to_json(eta, train_stop_id)
            add_train_eta_to_array(eta, train_station_name, train_stop_id)


def add_train_eta_to_array(eta, station_name, stop_id):
    """Parses API Result from Train Tracker API and adds ETA's to a list"""
    if eta.find('isSch').text == "0":
        if eta.find('isApp').text == "1":
            arrival_information["trains"][station_name][stop_id][
                "estimated_times"].append("Due+")
        else:
            prediction = eta.find('prdt').text
            arrival = eta.find('arrT').text
            estimated_time = str(minutes_between(prediction, arrival))
            (arrival_information["trains"][station_name][stop_id]
             ["estimated_times"].append(estimated_time + "min+"))
    else:
        if eta.find('isApp').text == "1":
            arrival_information["trains"][station_name][stop_id][
                "estimated_times"].append("Due-")
        else:
            prediction = eta.find('prdt').text
            arrival = eta.find('arrT').text
            estimated_time = str(minutes_between(prediction, arrival))
            (arrival_information["trains"][station_name][stop_id]
             ["estimated_times"].append(estimated_time + "min-"))


def bus_eta_times(bus_api_response):
    """Takes each Bus ETA (if exists) and appends to list"""
    if bus_api_response.find('error') is None:
        for prd in bus_api_response.iter('prd'):
            stop_id = prd.find('stpid').text
            if stop_id in arrival_information["buses"]:
                add_bus_eta_to_array(prd, stop_id)
            else:
                add_bus_stop_to_json(prd, stop_id)
                add_bus_eta_to_array(prd, stop_id)


def add_bus_eta_to_array(prd, stop_id):
    """Parses API Result from Bus Tracker API and adds ETA's to a list"""
    if prd.find('prdctdn').text == "DUE":
        arrival_information["buses"][stop_id]["estimated_times"].append("Due")
    elif prd.find('prdctdn').text == "DLY":
        arrival_information["buses"][stop_id]["estimated_times"].append(
            "Delayed")
    else:
        (arrival_information["buses"][stop_id]["estimated_times"].append(
            prd.find('prdctdn').text + "min"))


def divvy_process_station_stats(station_stats, station_information):
    """Takes Station Information and Stats from API Call and gets needed information"""
    divvy_to_replace = {
        " St": '',
        " Rd": "",
        " Ave": "",
        "Town": "Twn",
        "Center": "Ctr"
    }
    for station in station_information['data']['stations']:
        station_id = station['station_id']
        if station_id in DIVVY_STATION_IDS:
            found_station_information = {}
            station_distance_long = distance.distance(
                (home_latitude, home_longitude),
                (station['lat'], station['lon'])).miles
            station_distance_short = str(round(station_distance_long,
                                               2)) + "mi"
            for key, value in divvy_to_replace.items():
                station_name = re.sub(r"\b" + key + r"\b", value,
                                      station['name'])
            found_station_information["station_name"] = station_name
            found_station_information["capacity"] = str(station['capacity'])
            found_station_information["distance"] = station_distance_short
            found_station_information["bike_numbers"] = []
            arrival_information["bicycles"][
                station['station_id']] = found_station_information

    for station in station_stats['data']['stations']:
        if station['station_id'] in DIVVY_STATION_IDS:
            arrival_information["bicycles"][
                station['station_id']]["bike_numbers"].append(
                    str(station['num_ebikes_available']) + " ebikes")
            arrival_information["bicycles"][
                station['station_id']]["bike_numbers"].append(
                    str(station['num_bikes_available']) + " classic")


def create_string_of_items(items):
    """Takes each item from list and builds a useable string"""
    string_count = 0
    string = ""
    for item in items:
        if string_count == 0:
            string = item
            string_count += 1
        elif string_count > 0 and string_count <3:
            string = string + ", " + item
            string_count += 1
    return string


def information_output_to_display(arrival_information_input):
    """Used to create structure for use when outputting data to e-ink epd"""
    display_information_output = []
    for station in arrival_information_input['trains']:
        for train in arrival_information_input['trains'][station]:
            try:
                display_information_output.append({
                    'line_1':
                    station,
                    'line_2':
                    (arrival_information['trains'][station][train]['route'] +
                     " Line to " + arrival_information['trains'][station]
                     [train]['destination_name']),
                    'line_3':
                    create_string_of_items(
                        arrival_information['trains'][station][train]
                        ["estimated_times"]),
                    'item_type':
                    "train",
                })
                arrival_information['trains'][station][train][
                    "estimated_times"] = []
            except:  # pylint: disable=bare-except
                display_information_output.append({
                    'line_1':
                    station,
                    'line_2':
                    (arrival_information['trains'][station][train]['route'] +
                     " Line to " + arrival_information['trains'][station]
                     [train]['destination_name']),
                    'line_3':
                    "No arrivals found :(",
                    'item_type':
                    "train",
                })

    for bus in arrival_information['buses']:
        try:
            display_information_output.append({
                'line_1':
                arrival_information['buses'][bus]["stop_name"],
                'line_2':
                arrival_information['buses'][bus]["full_name"],
                'line_3':
                create_string_of_items(
                    arrival_information['buses'][bus]["estimated_times"]),
                'item_type':
                "bus"
            })
        except:  # pylint: disable=bare-except
            display_information_output.append({
                'line_1':
                arrival_information['buses'][bus]["stop_name"],
                'line_2':
                arrival_information['buses'][bus]["full_name"],
                'line_3':
                "No arrivals found :(",
                'item_type':
                "bus"
            })
        arrival_information['buses'][bus]["estimated_times"] = []

    for station in arrival_information["bicycles"]:
        display_information_output.append({
            'line_1':
            str(arrival_information["bicycles"][station]
                ["station_name"]).replace("Ave", ""),
            'line_2':
            "Distance: " +
            arrival_information["bicycles"][station]["distance"],
            'line_3':
            create_string_of_items(
                arrival_information["bicycles"][station]["bike_numbers"]),
            'item_type':
            "bicycle"
        })
        arrival_information["bicycles"][station]["bike_numbers"] = []
    return display_information_output


def information_to_display(status):
    """Used to create structure for use when outputting data to e-ink epd"""
    icon_bus = Image.open("/home/pi/ctapi/icons/bus_live.png")
    icon_train = Image.open("/home/pi/ctapi/icons/train_live.png")
    icon_bicycle = Image.open("/home/pi/ctapi/icons/bicycle.png")
    corner_image_size = (25, 25)
    loop_count = 0
    while loop_count < len(status):
        image = Image.new('1', (epd.height, epd.width),
                          255)  # 255: clear the frame
        draw = ImageDraw.Draw(image)

        try:
            if status[loop_count]['item_type'] == "train":
                icon_train_resized = icon_train.resize(corner_image_size)
                image.paste(icon_train_resized, (225, 35))
            elif status[loop_count]['item_type'] == "bus":
                icon_bus_resized = icon_bus.resize(corner_image_size)
                image.paste(icon_bus_resized, (225, 35))
            elif status[loop_count]['item_type'] == "bicycle":
                icon_bicycle_resized = icon_bicycle.resize(corner_image_size)
                image.paste(icon_bicycle_resized, (225, 35))

            # Store & Draw the location 1
            item_1_line_1 = status[loop_count]['line_1']
            draw.text((1, 1), item_1_line_1, font=bold_font, fill=0)

            # Store & Draw the destination 1
            item_1_line_2 = status[loop_count]['line_2']
            draw.text((1, 20), item_1_line_2, font=standard_font, fill=0)

            # Store & Draw the ETA 1
            item_1_line_3 = status[loop_count]['line_3']
            draw.text((1, 38), item_1_line_3, font=standard_font, fill=0)

        except:  # pylint: disable=bare-except
            item_1_line_1 = ""
            item_1_line_2 = ""
            item_1_line_3 = ""
        loop_count += 1

        draw.line((0, 61, 250, 61), fill=0, width=3)

        try:
            if status[loop_count]['item_type'] == "train":
                icon_train_resized = icon_train.resize(corner_image_size)
                image.paste(icon_train_resized, (225, 97))
            elif status[loop_count]['item_type'] == "bus":
                icon_bus_resized = icon_bus.resize(corner_image_size)
                image.paste(icon_bus_resized, (225, 97))
            elif status[loop_count]['item_type'] == "bicycle":
                icon_bicycle_resized = icon_bicycle.resize(corner_image_size)
                image.paste(icon_bicycle_resized, (225, 97))

            # Store & Draw the location 1
            item_2_line_1 = status[loop_count]['line_1']
            draw.text((1, 65), item_2_line_1, font=bold_font, fill=0)

            # Store & Draw the destination 1
            item_2_line_2 = status[loop_count]['line_2']
            draw.text((1, 84), item_2_line_2, font=standard_font, fill=0)

            # Store & Draw the ETA 1
            item_2_line_3 = status[loop_count]['line_3']
            draw.text((1, 102), item_2_line_3, font=standard_font, fill=0)
        except:  # pylint: disable=bare-except
            item_2_line_1 = ""
            item_2_line_2 = ""
            item_2_line_3 = ""
        loop_count += 1
        if item_1_line_1 != "":
            print(item_1_line_1)
            print(item_1_line_2)
            print(item_1_line_3)
            print("------------------------")
        if item_2_line_1 != "":
            print(item_2_line_1)
            print(item_2_line_2)
            print(item_2_line_3)
            print("------------------------")

        # Send to Display
        epd.display(epd.getbuffer(image))

        # Wait a respectable amount of time so the display can refresh
        print("Sleeping 4 Seconds")
        time.sleep(4)


def tweet_to_display():
    """Used to output the latest CTA Tweet to the Display"""
    corner_image_size = (25, 25)
    tweet_text = re.sub(
        r'http\S+|( |(?<![a-zA-Z]))[M][o][r][e][:]( |(?![a-zA-Z]))', '',
        str(get_latest_cta_tweet()))
    tweet_text_wrapped = textwrap.wrap(tweet_text, width=25)
    icon_twitter = Image.open("/home/pi/ctapi/icons/twitter.png")
    tweet_length = len(tweet_text_wrapped)
    current_tweet_page = 1
    total_tweet_pages = math.ceil(tweet_length / 4)
    printed_lines = 0
    while printed_lines != len(
            tweet_text_wrapped) and ENABLE_TWITTER_LOOKUP is True:
        twitter_image = Image.new('1', (epd.height, epd.width),
                                  255)  # 255: clear the frame
        twitter_draw = ImageDraw.Draw(twitter_image)
        # Store & Draw the header
        tweet_line_1 = "Latest Tweet from @CTA"
        twitter_draw.text((0, 0), tweet_line_1, font=bold_font, fill=0)

        # Store & Draw Tweet
        try:
            tweet_line_2 = tweet_text_wrapped[printed_lines]
            printed_lines += 1
            twitter_draw.text((0, 20), tweet_line_2, font=tweet_font, fill=0)
        except:  # pylint: disable=bare-except
            tweet_line_2 = ""
        try:
            tweet_line_3 = tweet_text_wrapped[printed_lines]
            printed_lines += 1
            twitter_draw.text((0, 40), tweet_line_3, font=tweet_font, fill=0)
        except:  # pylint: disable=bare-except
            tweet_line_3 = ""
        try:
            tweet_line_4 = tweet_text_wrapped[printed_lines]
            printed_lines += 1
            twitter_draw.text((0, 60), tweet_line_4, font=tweet_font, fill=0)
        except:  # pylint: disable=bare-except
            tweet_line_4 = ""
        try:
            tweet_line_5 = tweet_text_wrapped[printed_lines]
            printed_lines += 1
            twitter_draw.text((0, 80), tweet_line_5, font=tweet_font, fill=0)
        except:  # pylint: disable=bare-except
            tweet_line_5 = ""
        icon_twitter = icon_twitter.resize(corner_image_size)
        twitter_image.paste(icon_twitter, (225, 97))
        try:
            tweet_line_6 = "Page " + str(current_tweet_page) + " / " + str(
                total_tweet_pages)
            twitter_draw.text((0, 100), tweet_line_6, font=tweet_font, fill=0)
        except:  # pylint: disable=bare-except
            tweet_line_6 = ""
        icon_twitter = icon_twitter.resize(corner_image_size)
        twitter_image.paste(icon_twitter, (225, 97))

        if tweet_line_1 != "":
            print(tweet_line_1)
            print(tweet_line_2)
            print(tweet_line_3)
            print(tweet_line_4)
            print(tweet_line_5)
            print(tweet_line_6)

        current_tweet_page += 1

        # Send to Display
        epd.display(epd.getbuffer(twitter_image))

        # Wait a respectable amount of time so the display can refresh
        print("Sleeping 4 Seconds")
        time.sleep(4)


print("Welcome to TrainTracker, Python/RasPi Edition!")
while True:  # Where the magic happens
    if (not REFRESH_DISPLAY) or (time.monotonic() - REFRESH_DISPLAY) > 2:
        current_time_console = "The Current Time is: " + \
            datetime.strftime(datetime.now(), "%H:%M")
        print("\n" + current_time_console)

        if TRAIN_STATION_STOP_IDS != "" and ENABLE_TRAIN_TRACKER is True:
            train_station_stpIds_split = TRAIN_STATION_STOP_IDS.split(',')
            for train_stop_id_to_check in train_station_stpIds_split:
                # try:
                response = train_api_call_to_cta(train_stop_id_to_check)
                # except:  # pylint: disable=bare-except
                # print("Error in API Call to Train Tracker")

        if BUS_STOP_STOP_IDS != "" and ENABLE_BUS_TRACKER is True:
            bus_stop_stpids_split = BUS_STOP_STOP_IDS.split(',')
            bus_stop_route_ids_split = BUS_STOP_ROUTE_IDS.split(',')
            BUS_COUNT = 0
            for bus_stop_id in bus_stop_stpids_split:
                try:
                    bus_api_call_to_cta(bus_stop_id,
                                        bus_stop_route_ids_split[BUS_COUNT])
                    BUS_COUNT += 1
                except:  # pylint: disable=bare-except
                    print("Error in API Call to Bus Tracker")

        if DIVVY_STATION_IDS != "" and ENABLE_DIVVY_STATION_CHECK is True:
            divvy_process_station_stats(divvy_api_call_station_status(),
                                        divvy_api_call_station_information())

        information_to_display(
            information_output_to_display(arrival_information))
        tweet_to_display()

        REFRESH_DISPLAY = time.monotonic()
