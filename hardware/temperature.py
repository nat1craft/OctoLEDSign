import time, copy
from datetime import datetime
import threading
import sys, os

COMPILE_PC = os.path.sep=="\\"
USE_LEGACY_DHT = True

from utils.utils import *
from hardware.sensor import *

class TemperatureState():
    def __init__(self, value = 0, humidity = 0, decimals = 0, units = "°C", convert_to_fahrenheit = False):
        self.value = value
        self.humidity = humidity
        self.decimals = decimals
        self.units = units
        self.convert_to_fahrenheit = convert_to_fahrenheit

    def to_json(self):       
        return "{{ \"temperature\":{0}, \"humidity\":{1}, \"units\":\"{2}\", \"time\": \"{3}\", \"formatted_temperature\":\"{4}\", \"formatted_humidity\":\"{5}\"  }}".format(
            self.formatted(False),self.formatted_humidity(False), self.units, datetime.now().isoformat(),
            self.formatted(True), self.formatted_humidity(True))

    def convert(self, temp):
        if self.convert_to_fahrenheit:
            return temp * (9/5) + 32
        return temp

    def formatted(self, show_units = True):
        fmt_dec = ".{0}f".format(self.decimals)
        all_format = "{{0:{0}}}{1}".format(fmt_dec, self.units if show_units else "")
        return all_format.format(self.convert(self.value))

    def formatted_humidity(self, show_units = True):
        fmt_dec = ".{0}f".format(self.decimals)
        all_format = "{{0:{0}}}{1}".format(fmt_dec, "%" if show_units else "")
        return all_format.format(self.humidity)

    def __str__(self):
        fmt_dec = ".{0}f".format(self.decimals)

        if self.humidity != 0:
            all_format = "{{0:{0}}}{1} / {{1:{0}}}%".format(fmt_dec, self.units)
            return all_format.format(0 if self.value is None else self.convert(self.value),0 if self.humidity is None else self.humidity)
        else:
            all_format = "{{0:{0}}}{1}".format(fmt_dec, self.units)
            return all_format.format(self.convert(self.value))

    def concise(self, show_units):
        fmt_dec = ".{0}f".format(self.decimals)

        if self.humidity != 0:
            symbol = "+" if self.target > self.actual else "-"
            all_format = "{{0:{0}}}{1}{2}".format(fmt_dec, self.units if show_units else "", symbol)
            return all_format.format(self.convert(self.value),self.humidity)
        else:
            all_format = "{{0:{0}}}{1}".format(fmt_dec, self.units if show_units else "")
            return all_format.format(self.convert(self.value))


class TemperatureSensor(HardwareSensor):
    def __init__(self, settings, on_state_changed=None):
        super().__init__(settings,on_state_changed)
        if self.settings != None:
            self.name = self.settings["name"]
        else:
            self.name = "Unknown"
        self.mqtt_client = None
        self.state =  TemperatureState()
        self.state.name = self.name

    def update_settings(self, new_settings):
        super().update_settings(new_settings)
        with self.lock:
            if self.settings != None:
                if "name" in self.settings:
                    self.name = self.settings["name"]
                    if self.state != None:
                        self.state.name =  self.settings["name"]
                if "temperature" in self.settings:
                    if self.state != None:
                        temp_settings = self.settings["temperature"]
                        if "decimals" in temp_settings:
                            self.state.decimals = temp_settings["decimals"]
                        if "display_units" in temp_settings:
                            self.state.units = temp_settings["display_units"]
                        if "convert_to_fahrenheit" in temp_settings:
                            self.state.convert_to_fahrenheit = temp_settings["convert_to_fahrenheit"]
