from glob import glob
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
train_station_stpId_1 = "30197" # (Used to Identify Platform Side) # Logan Square (O'Hare Bound)
train_station_stpId_2 = "30198" # (Used to Identify Platform Side) # Logan Square (Forrest Park Bound)
train_station_mapid_1 = "41020" # (Used by API) # Logan Square - Blue Line
bus_stop_code_1 = "5465" # Milwaukee & Spaulding - Southeastbound - Northwest Corner
bus_stop_code_2 = "1323" # Fullerton & Spaulding - Eastbound - Southwest Corner

# Last Known Information
train_route_1 = "Unknown"
train_route_2 = "Unknown"
bus_route_1 = "Unknown"
bus_route_2 = "Unknown"

def minutes_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y%m%d %H:%M:%S")
    d2 = datetime.strptime(d2, "%Y%m%d %H:%M:%S")
    difference = d2 - d1
    difference_in_minutes = int(difference / timedelta(minutes=1))
    return difference_in_minutes

def add_train_eta_to_array(eta):
    global train_route_1
    global train_route_2
    if eta.find('isApp').text == "1":
        if eta.find('stpId').text == train_station_stpId_1:
            arrival_times['train_direction_1'].append("Due")
        elif eta.find('stpId').text == train_station_stpId_2:
            arrival_times['train_direction_2'].append("Due")
    else:
        prediction = eta.find('prdt').text
        arrival = eta.find('arrT').text
        estimated_time = str(minutes_between(prediction, arrival))
        if eta.find('stpId').text == train_station_stpId_1:
            direction_information["train_direction_1"].append(eta.find('destNm').text)
            arrival_times['train_direction_1'].append(estimated_time + "min")
            train_route_1 = eta.find('rt').text + " Line - " + eta.find('stpDe').text
        elif eta.find('stpId').text == train_station_stpId_2:
            direction_information["train_direction_2"].append(eta.find('destNm').text)
            arrival_times['train_direction_2'].append(estimated_time + "min")
            train_route_2 = eta.find('rt').text + " Line - " + eta.find('stpDe').text

def add_bus_eta_to_array(prd):
    global bus_route_1
    global bus_route_2
    if prd.find('stpid').text == bus_stop_code_1:
            direction_information["bus_1"].append(eta.find('destNm').text)
            arrival_times["bus_1"].append(str(prd.find('prdctdn').text) + "min")
            bus_route_1 = eta.find('rt').text + " Line - " + eta.find('stpDe').text
    elif prd.find('stpid').text == bus_stop_code_2:
            direction_information["bus_2"].append(eta.find('destNm').text)
            arrival_times["bus_2"].append(str(prd.find('prdctdn').text) + "min")
            bus_route_2 = eta.find('rt').text + " Line - " + eta.find('stpDe').text
    

def parse_api_response(response):
    root = ET.fromstring(response.content)
    return root

def train_eta_times(response):
    if response.find('eta') is None:
        arrival_times["train_direction_2"].append("No service scheduled")
        arrival_times["train_direction_1"].append("No service scheduled")
    else: 
        for eta in response.iter('eta'):
            add_train_eta_to_array(eta)

def bus_eta_times(response):
    if response.find('error') is None:
        for prd in response.iter('prd'):
            direction_information["bus_1"].append(str(prd.find('rt').text) + " towards " + prd.find('des').text)
            add_bus_eta_to_array(prd)
    else:
        for error in response.iter('error'):
            arrival_times["bus_1"].append(error.find('msg').text)

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
    
def bus_api_call_to_cta(stop_code):
    api_response = requests.get("http://www.ctabustracker.com/bustime/api/v2/getpredictions?key={}&stpid={}".format(bus_api_key,stop_code))
    bus_eta_times(parse_api_response(api_response))

refresh_display = None

while True:
    if (not refresh_display) or (time.monotonic() - refresh_display) > 60:
        # Variable for storing arrival information - reset each loop
        direction_information = {"train_direction_1":[],"train_direction_2":[],"bus_1":[],"bus_2":[]}
        arrival_times = {"train_direction_1":[],"train_direction_2":[],"bus_1":[],"bus_2":[]}
        print_information = []
        
        train_api_response = train_api_call_to_cta()
        if bus_stop_code_1 != "":
            bus_api_response = bus_api_call_to_cta(bus_stop_code_1)
        if bus_stop_code_2 != "":
            bus_api_response = bus_api_call_to_cta(bus_stop_code_2)

        print("\nThe Current Time is: " + datetime.strftime(datetime.now(), "%m/%d/%Y %H:%M"))
        try:
            print_information.append("Next " + direction_information["train_direction_1"][0] + " Bound Train in: " + create_string_of_times(arrival_times["train_direction_1"]))
        except:
            print_information.append("No arrivals at: " + train_route_1)
        try:
            print_information.append("Next " + direction_information["train_direction_2"][0] + " Bound Train in: " + create_string_of_times(arrival_times["train_direction_2"]))
        except:
            print_information.append("No arrivals at: " + train_route_2)
        try:
            print_information.append("Next " + direction_information["bus_1"][0] + ": " + create_string_of_times(arrival_times["bus_1"]))
        except:
            print_information.append("No arrivals at: " + bus_route_1)
        try:
            print_information.append("Next " + direction_information["bus_2"][0] + ": " + create_string_of_times(arrival_times["bus_2"]))
        except:
            print_information.append("No arrivals at: " + bus_route_2)

        for item in print_information:
            print(item)

        refresh_display = time.monotonic()
    
    time.sleep(60)