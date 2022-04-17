import requests # Used for API Calls
import xml.etree.ElementTree as ET # Used to Parse API Response
from datetime import datetime,timedelta # Used for converting Prediction from Current Time
import time # Used to Get Current Time
import os # Used to Load Env Var
from dotenv import load_dotenv # Used to Load Env Var

# Load .env variables
load_dotenv()

# API Keys
train_api_key = os.getenv('TRAIN_API_KEY')
bus_api_key = os.getenv('BUS_API_KEY')

# Station/Stop Information
logan_square_ohare_stpid = "30197" # Logan Square (O'Hare Bound)
logan_square_forrest_park_stpid = "30198" # Logan Square (Forrest Park Bound)
train_station_mapid_1 = "41020" # Logan Square
bus_stop_code_1 = "5465" # Milwaukee & Spaulding - Southeastbound - Northwest Corner

def minutes_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y%m%d %H:%M:%S")
    d2 = datetime.strptime(d2, "%Y%m%d %H:%M:%S")
    difference = d2 - d1
    difference_in_minutes = int(difference / timedelta(minutes=1))
    return difference_in_minutes

def add_train_eta_to_array(eta):
    if eta.find('isApp').text == "1":
        if eta.find('stpId').text == logan_square_ohare_stpid:
            arrival_times['ohare'].append("Due")
        elif eta.find('stpId').text == logan_square_forrest_park_stpid:
            arrival_times['forrest_park'].append("Due")
    else:
        prediction = eta.find('prdt').text
        arrival = eta.find('arrT').text
        estimated_time = str(minutes_between(prediction, arrival))
        if eta.find('stpId').text == logan_square_ohare_stpid:
            arrival_times['ohare'].append(estimated_time + "min")
        elif eta.find('stpId').text == logan_square_forrest_park_stpid:
            arrival_times['forrest_park'].append(estimated_time + "min")

def add_bus_eta_to_array(prd):
    arrival_times["76_bus"].append(str(prd.find('prdctdn').text) + "min")

def parse_api_response(response):
    root = ET.fromstring(response.content)
    return root

def train_eta_times(response):
    for eta in response.iter('eta'):
        add_train_eta_to_array(eta)

def bus_eta_times(response):
    if response.find('error') is None:
        for prd in response.iter('prd'):
            add_bus_eta_to_array(prd)
    else:
        for error in response.iter('error'):
            arrival_times["76_bus"].append(error.find('msg').text)

def create_string_of_times(times):
    count = 0
    for item in times:
        if count == 0:
            string = item
            count += 1
        elif count == 1:
            string = string + ", " + item
    return string
        

def train_api_call_to_cta():
    api_response = requests.get("http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key={}&mapid={}".format(train_api_key,train_station_mapid_1))
    train_eta_times(parse_api_response(api_response))
    
def bus_api_call_to_cta():
    api_response = requests.get("http://www.ctabustracker.com/bustime/api/v2/getpredictions?key={}&stpid={}".format(bus_api_key,bus_stop_code_1))
    bus_eta_times(parse_api_response(api_response))

refresh_display = None

while True:
    if (not refresh_display) or (time.monotonic() - refresh_display) > 60:
        # Variable for storing arrival information - reset each loop
        arrival_times = {"ohare":[],"forrest_park":[],"76_bus":[]}

        train_api_response = train_api_call_to_cta()
        bus_api_response = bus_api_call_to_cta()

        print("\nThe Current Time is: " + datetime.strftime(datetime.now(), "%m/%d/%Y %H:%M"))
        print("Next O'Hare Bound Train in: " + create_string_of_times(arrival_times["ohare"]))
        print("Next Forrest Park Bound Train in: " + create_string_of_times(arrival_times["forrest_park"]))
        print("Next 76 Bus Arrival Times: " + create_string_of_times(arrival_times["76_bus"]))

        refresh_display = time.monotonic()
    
    time.sleep(60)