# ctapi

## Overview
This project is used to display the nearest train at a specific L stop in Chicao, IL. The project runs on a Raspberry Pi and the display used is the [e-ink bonnet from Adafruit](https://www.adafruit.com/product/4687).

The display shows the following information:
* Destination of the train - example(s) being "O'Hare" & "Forrest Park"
* The current time - example being "mm/dd/yy HH:mm"
* Which line the train is running on - example being "Blue"
* The arrival time of the nearest train - example being "5min"

## Installation
* Create API access token on the [CTA Transit Tracker developer site](https://www.transitchicago.com/developers/traintracker/) and [CTA Bus developer site](https://www.transitchicago.com/developers/bustracker/) (optional)
* Clone the repository on your Raspberry Pi with the following `git clone https://github.com/brandonmcfadd/ctapi.git`
* Change into the working directory of the cloned repository `cd ctapi`
* Create a virtual environment to work in `python3 -m venv .`
* Activate the virtual environment `source bin/activate`
* Install the required dependencies `pip install -r requirements.txt`
* Create a file named `.env` in your directory with the following content 
* `TRAIN_API_KEY = 'YOUR_TRANSIT_API_KEY'`
* `BUS_API_KEY = 'YOUR_TRANSIT_API_KEY'` (optional)
* Run the main program `python3 main.py`

## Configuration
* To change the station being displayed modify the Station/Stop Information in `main.py` with the station code(s) you want to use.
* Station codes can be found on the following [site](https://data.cityofchicago.org/Transportation/CTA-System-Information-List-of-L-Stops/8pix-ypme) from the City of Chicago's Data Portal.

![metropi](./images/metropi.png)
