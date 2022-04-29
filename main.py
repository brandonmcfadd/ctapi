"""ctapi by Brandon McFadden - Github: https://github.com/brandonmcfadd/ctapi"""
import os  # Used to Load Env Var
import json  # Used to maintain
import time  # Used to Get Current Time
# Used for converting Prediction from Current Time
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET  # Used to Parse API Response
import adafruit_requests
from adafruit_magtag.magtag import MagTag
from adafruit_display_shapes.line import Line

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("Secrets are kept in secrets.py, please add them there!")
    raise

magtag = MagTag()
magtag.network.connect()

magtag.add_text(
    text_font="/fonts/AmericanSans-Bold-14.pcf",
    text_position=(
        8,
        8,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Station/Stop Name 1

magtag.add_text(
    text_font="/fonts/AmericanSans-14.pcf",
    text_position=(
        8,
        48,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Direction 1

magtag.add_text(
    text_font="/fonts/AmericanSansItalic-12.pcf",
    text_position=(
        198,
        48,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Estimated Times 1

magtag.append(
    Line(0, (magtag.graphics.display.height // 2) - 1,
         magtag.graphics.display.width,
         (magtag.graphics.display.height // 2) - 1, 0xFF0000))
magtag.append(
    Line(0, (magtag.graphics.display.height // 2) - 0,
         magtag.graphics.display.width,
         (magtag.graphics.display.height // 2) - 0, 0xFF0000))
magtag.append(
    Line(0, (magtag.graphics.display.height // 2) + 1,
         magtag.graphics.display.width,
         (magtag.graphics.display.height // 2) + 1, 0xFF0000))

magtag.add_text(
    text_font="/fonts/AmericanSans-Bold-14.pcf",
    text_position=(
        8,
        8,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Station/Stop Name 2

magtag.add_text(
    text_font="/fonts/AmericanSans-14.pcf",
    text_position=(
        8,
        80,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Direction 2

magtag.add_text(
    text_font="/fonts/AmericanSansItalic-12.pcf",
    text_position=(
        198,
        80,
    ),
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)  # Estimated Times 2

magtag.graphics.set_background("/bmps/background.bmp")

# API Keys
train_api_key = secrets["TRAIN_API_KEY"]
bus_api_key = secrets["BUS_API_KEY"]

# API URL's
TRAIN_TRACKER_URL = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key={}&stpid={}"
BUS_TRACKER_URL = "http://www.ctabustracker.com/bustime/api/v2/getpredictions?key={}&stpid={}&rt={}"

# Station/Stop Information for Trains/Buses - Bus Stop Items must contain equal number of items
# Enter the train station #'s to lookup
TRAIN_STATION_STOP_IDS = "30197,30198"

# Enter the bus stop #'s for the stops you want estimated times for
BUS_STOP_STOP_IDS = "5465,1323"
# Enter the corresponding bus route # you want for each bus_stop_id
BUS_STOP_ROUTE_IDS = "76,74"

# Last Known Information (used if API returns no arrival times) - Updated on successful API call
last_known_route_information = json.loads('{"trains":{},"buses":{}}')


def train_api_call_to_cta(stop_id):
    """Gotta talk to the CTA and get Train Times"""
    api_response = requests.get(
        TRAIN_TRACKER_URL.format(train_api_key, stop_id))
    train_eta_times(parse_api_response(api_response))
    return api_response


def bus_api_call_to_cta(stop_code, route_code):
    """Gotta talk to the CTA and get Bus Times"""
    api_response = requests.get(
        BUS_TRACKER_URL.format(bus_api_key, stop_code, route_code))
    bus_eta_times(parse_api_response(api_response))
    return api_response


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
    last_known_route_information["trains"][station_name] = station_information


def add_train_stop_to_json(eta, stop_id):
    """Function is called if a new train stop is identified per API Call"""
    stop_information = {}
    last_known_info = {}
    station_name = eta.find('staNm').text

    last_known_info["name"] = eta.find(
        'rt').text + " Line towards " + eta.find('destNm').text
    stop_information["full_name"] = eta.find(
        'rt').text + " Line towards " + eta.find('destNm').text
    stop_information["destination_name"] = eta.find('destNm').text
    stop_information["route"] = eta.find('rt').text
    stop_information["estimated_times"] = []

    last_known_route_information["trains"][station_name] = last_known_info
    arrival_information["trains"][station_name][stop_id] = stop_information


def add_bus_stop_to_json(prd, stop_id):
    """Function is called if a new bus stop is identified per API Call"""
    stop_information = {}
    last_known_info = {}

    stop_information["full_name"] = prd.find(
        'rt').text + " towards " + prd.find('des').text
    stop_information["destination_name"] = prd.find('des').text
    stop_information["route"] = prd.find('rt').text
    stop_information["stop_name"] = prd.find('stpnm').text
    stop_information["estimated_times"] = []

    last_known_info["name"] = prd.find('rt').text + " towards " + prd.find(
        'des').text

    arrival_information["buses"][stop_id] = stop_information
    last_known_route_information["buses"][stop_id] = last_known_info


def train_eta_times(train_api_response):
    """Takes each Train ETA (if exists) and appends to list"""
    for eta in train_api_response.iter('eta'):
        train_stop_id = eta.find('stpId').text
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
    if eta.find('isApp').text == "1":
        arrival_information["trains"][station_name][stop_id][
            "estimated_times"].append("Due")
    else:
        prediction = eta.find('prdt').text
        arrival = eta.find('arrT').text
        estimated_time = str(minutes_between(prediction, arrival))
        (arrival_information["trains"][station_name][stop_id]
         ["estimated_times"].append(estimated_time + "min"))


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


def create_string_of_times(times):
    """Takes each ETA from list and builds a useable string"""
    string_count = 0
    for item in times:
        if string_count == 0:
            string = item
            string_count += 1
        elif string_count == 1:
            string = string + ", " + item
    return string


def information_output_to_display(arrival_information_input):
    """Used to create structure for use when outputting data to e-ink display"""
    display_information_output = []
    for station in arrival_information_input['trains']:
        for train in arrival_information_input['trains'][station]:
            display_information_output.append({
                'station_name':
                station,
                'line_and_destination':
                (arrival_information['trains'][station][train]['route'] +
                 " Line to " + arrival_information['trains'][station][train]
                 ['destination_name']),
                'estimated_times':
                create_string_of_times(arrival_information['trains'][station]
                                       [train]["estimated_times"])
            })

    for bus in arrival_information['buses']:
        display_information_output.append({
            'station_name':
            arrival_information['buses'][bus]["stop_name"],
            'line_and_destination':
            arrival_information['buses'][bus]["full_name"],
            'estimated_times':
            create_string_of_times(
                arrival_information['buses'][bus]["estimated_times"])
        })
    return display_information_output


REFRESH_DISPLAY = None

while True:  # Where the magic happens
    if (not REFRESH_DISPLAY) or (time.monotonic() - REFRESH_DISPLAY) > 15:
        # Variable for storing arrival information - reset each loop
        arrival_information = json.loads('{"trains":{},"buses":{}}')
        display_information = []

        if TRAIN_STATION_STOP_IDS != "":
            train_station_stpIds_split = TRAIN_STATION_STOP_IDS.split(',')
            for train_stop_id_to_check in train_station_stpIds_split:
                try:
                    response = train_api_call_to_cta(train_stop_id_to_check)
                except:  # pylint: disable=bare-except
                    print("Error in API Call to Train Tracker")

        if BUS_STOP_STOP_IDS != "":
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

        cta_status = information_output_to_display(arrival_information)

        LOOP_COUNT = 0
        while LOOP_COUNT < len(cta_status):
            try:
                magtag.set_text(cta_status[LOOP_COUNT]['line_and_destination'],
                                0, False)
                magtag.set_text(cta_status[LOOP_COUNT]['station_name'], 1,
                                False)
                magtag.set_text(cta_status[LOOP_COUNT]['estimated_times'], 2,
                                False)
            except:  # pylint: disable=bare-except
                magtag.set_text("", 0, False)
                magtag.set_text("", 1, False)
                magtag.set_text("", 2, False)
            LOOP_COUNT += 1
            try:
                magtag.set_text(cta_status[LOOP_COUNT]['line_and_destination'],
                                3, False)
                magtag.set_text(cta_status[LOOP_COUNT]['station_name'], 4,
                                False)
                magtag.set_text(cta_status[LOOP_COUNT]['estimated_times'], 5,
                                False)
            except:  # pylint: disable=bare-except
                magtag.set_text("", 3, False)
                magtag.set_text("", 4, False)
                magtag.set_text("", 5, False)
            LOOP_COUNT += 1

            magtag.refresh()

            # Wait a respectable amount of time so the display can refresh
            time.sleep(15)

        REFRESH_DISPLAY = time.monotonic()
