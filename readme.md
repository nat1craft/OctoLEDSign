# Setting up a Python Workspace
- Add Folder to Workspace `D:\misc\OctoSign`
- **View | Command Palette | Python: Create Terminal**
    - Create virtual Environment: 
    `python -m venv .venv`
    - Pick **View | Command Palette | Python : Select Interpreter**
    - Select **Entire Workspace**
    - Select **Python 3.9.2 | .venv\Scripts\python.exe**
- Upgrade pip if necessary in your Python Terminal
`python -m pip install --upgrade pip`
- Add application file `app.py`
- Add logic such as:

``` python
import time
from datetime import datetime
import threading
import http.client as httplib
import json
import urllib.request
import sys
from enum import IntEnum

class App():
    def main(self):
        print("Application up and running!")

if __name__ == "__main__":
    app = App()
    app.main()
```

- Select <kbd>ctrl+shift+d</kbd> (or **Run and Debug** on left-side menu) then **Run and Debug**
- Select **Python**

# Setting up a Git Repository
- After creating your workspace (see above)...
- Type <kbd>ctrl+shift+G</kbd> to bring up the **source control** left-side menu
- Select **Publish to Github**
- Select **Publish to Github private repository.....**
- Remove the **.venv** from being published
- Make a requirements.txt file 
`pip freeze > requirements.txt`

# Cloning this repository
- open a command prompt in your folder of choice ex: `cd myprojects`
- run the following command:
    ```
    d:\myprojects> git clone https://github.com/nat1craft/OctoLEDSign
    ```

# Installing Libraries
The requirements file will list all libraries, but here are some installation steps:
- **Paho-MQTT** - used for subscribing to MQTT notifications: 
`pip install paho-mqtt`
- **[Luma LED Libaries](https://luma-led-matrix.readthedocs.io/en/latest/install.html)** : make sure you **enable SPI on your device!**
    ```
    $ sudo usermod -a -G spi,gpio pi
    $ sudo apt install build-essential python3-dev python3-pip libfreetype6-dev libjpeg-dev libopenjp2-7 libtiff5
    $ sudo python3 -m pip install --upgrade luma.led_matrix
    ```
- **[Adafruit Circuit Python Library](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi)** - use for controlling a variety of devices and IO operations
    ```
    $ sudo pip3 install --upgrade adafruit-python-shell
    $ wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
    $ sudo python3 raspi-blinka.py
    ```
- Next **[Install the CircuitPython DHT libraries](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup)**
    ```
    $ pip3 install adafruit-circuitpython-dht
    $ sudo apt-get install libgpiod2
    ```
- Note: The above CircuitPython DHT libraries appear broken. The DHT always returns error with ["A full buffer was not returned" on raspberry pi Zero](https://github.com/adafruit/Adafruit_CircuitPython_DHT/issues/33).  However, using the deprecated (non-circuitpython) library works fine. Install it by [doing the following](https://learn.adafruit.com/adafruit-io-basics-temperature-and-humidity/python-setup):
    ```
    $ sudo pip3 install --upgrade setuptools
    $ sudo pip3 install Adafruit_DHT
    ```