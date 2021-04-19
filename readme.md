# What is OctoLEDSign?
This code supports an LED Matrix sign that reads information from Octoprint via [MQTT](https://mqtt.org/). The sign can display such things as the current operation (status), the extruder or bed temp, the filename, etc.   *Note: the LED panel/shelf displayed in the picture is a separate project and not part of the sign itself.*

<img src="./images/octoledsign_closeup.jpg" width="400" alt="OctoLedSign">
<img src="./images/octoledsign.jpg" width="400" alt="OctoLedSign">

# What do you need?
For this code to be useful, you will need the items listed below. 

*Note: Some items listed have affiliate links where you can purchase the products. They might provide minor income to support this project and others like it at no cost to you.*

## Infrastructure
- [Ender 3 Pro](https://amzn.to/3sp3RIh) You will need a 3d printer! I have setup the code to be very flexible about the type of printer, but it was targeted to an Ender3 (Pro). I can't say enough good about this little workhorse, especially for a beginner.  The `settings.json` file allows you to map fields to MQTT topics, so theoretically, anything that generates MQTT messages to feed the sign will work.
- You will want access to an MQTT server. 
    - For my purposes, I use [HomeAssistant](https://www.home-assistant.io/) setup with the Mosquito add-on. This is running on a dedicated raspberry-pi 3b+ and is working quite well.
- You will need [Octoprint](https://octoprint.org/) setup! For my purposes I have an octoprint server running on an old mac-mini running windows 10. The sign does not talk directly to OctoPrint. However, OctoPrint talks to the MQTT server (and the sign talks to the MQTT server).
- You will want the [Octoprint MQTT Plugin](https://plugins.octoprint.org/plugins/mqtt/) installed

## Hardware
- [Raspberry Pi Zero W](https://amzn.to/3tyssMa) (or better like [3b/3b+/4](https://amzn.to/3drVtTP)) with a power supply!

    <img src="./images/raspzerow.jpg" width="200" alt="raspberry pi zero w">


- A set of [max7219 x 4 matrix LED matrix displays](https://amzn.to/3ttKMpH).  I have purchased these from different vendors and there are very slight differences between them. Depending on the vendor, the boards used might vary in size by ~2mm.  This also slightly affects the alignment between each module in the 4-module strip. 

    *Note: You can daisy chaining multiples of these strips for a bigger sign, just update the `settings.json` file. In the base settings, it supports a sign made up of 2 of these strips; the top strip is blue and the bottom is red (each strip holds 4 arrrays, meaning 8 arrays total)*

    <img src='./images/max7219x4.jpg' alt='max7219 x 4 matrix LED' width=200> 

- **Optional:** the following components are optional.
    - [DHT22 temperature and humidity sensor](https://amzn.to/32tgreZ). If you want to monitor the air temp around the printer, then by all means add one of these to the design.  The code provided also publishes this temperature the MQTT server (if the sensor exists).  Please note that sampling this DHT22 sensor takes about 0.5 seconds. This would produce a noticeable pause in animations, so the sampling rate was dialed back to once per minute (which is more than reasonable)
    
        <img src='./images/dht22.jpg' alt='dht22 temperature/humidity sensor' width=200> 

    - [360 Degree Rotary Encoder](https://amzn.to/3gjnUFB) of your choice. This is used to control the display brightness on-the-fly, but you can eliminate this altogether if you want to set the brightness to a fixed value in the `settings.json` file.  I like these because they also act as a pushbutton switch by pressing the knob.
    
        <img src='./images/rotary.jpg' alt='360 degree rotary encoder and switch' width=200> 

### Wiring Up the Hardware
There are many ways to wire up these parts to the raspberry pi, but I have listed how I configured them below. If you google search, you will find in-depth instructions about each piece of hardware and how to wire them to the pi.  Consider these as suggestions...

<img src="./images/raspzerow.pins.jpg">

*Note: you may want/need to consolidate power and ground pins.*

<img src="./images/octoledsign_circuit.png" width=500>

- Raspberry Pi to the LED Matrix
    | Raspberry Pi Zero | max7219 |
    | ------------------|---------|
    | Pin 2   (5V Power)| VCC     |
    | Pin 6   (Ground)  | GND     |
    | Pin 19  (GPIO 10) | DIN     |
    | Pin 24  (GPIO 8)  | CS      |
    | Pin 23  (GPIO 11) | CLK     |

- Raspberry Pi to DHT22
    | Raspberry Pi Zero | dht22   |
    | ------------------|---------|
    | Pin 4  (5V Power) | VCC (+) |
    | Pin 14 (Ground)   | GND (-) |
    | Pin 7  (GPIO 4)   | OUT     |

    In the `settings.json` file, this pin is reflected using GPIO numbering like this:
    ```
        "sensors": [
            {
                "name": "RoomTemp",
                "type": "22",
                "temperature": {...
                },
                "dht": {
                    "pin_data": 4       // GPIO4 is physical pin #7
                },
                "mqtt": {...
                }
            }
        ]
    ```

- Raspberry Pi to Rotary Encoder
    | Raspberry Pi Zero | Encoder |
    | ------------------|---------|
    | Pin 20  (Ground)  | GND     |
    | Pin 1   (3V Power)| (+)     |
    | Pin 16  (GPIO 23) | SW      |
    | Pin 12  (GPIO 18) | DT      |
    | Pin 11  (GPIO 17) | CLK     |

    In the `settings.json` file, these pins are reflected using GPIO numbering like this:
    ```
        "encoder": {
            "enabled": true,
            "pin_left": 17,         // GPIO17 is physical pin #11
            "pin_right": 18,        // GPIO18 is physical pin #12
            "pin_click": 23,        // GPIO23 is physical pin #16
            "sensitivity": 20
        },
    ```

# Cloning this repository
- open a terminal in your folder of choice ex: `~/octosign`
- run the following command:
    ```
    ~/octosign $ git clone https://github.com/nat1craft/OctoLEDSign
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