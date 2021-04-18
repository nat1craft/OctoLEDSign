import time, copy
from datetime import datetime
import threading
import sys, os

COMPILE_PC = os.path.sep=="\\"
USE_LEGACY_DHT = True

from utils.utils import *
from hardware.temperature import *

if COMPILE_PC:
    from hardware.rpi_stubs import gpio_stubs as GPIO    
else:
    import RPi.GPIO as GPIO
    import board

    if USE_LEGACY_DHT:
        import Adafruit_DHT
    else:
        import adafruit_dht

class DHTEvents(MonitoredStateEvents):
     __events__ = ("on_state_changed","on_temperature_changed","on_humidity_changed")

class DHTSensor(TemperatureSensor):
    def __init__(self, settings, pin_data=0, sensor_model=Adafruit_DHT.DHT22,
                    on_state_changed=None, on_temperature_changed=None, on_humidity_changed=None,interval=30):
        super().__init__(settings,on_state_changed=on_state_changed)
        # the DHT can take ~ 0.5 seconds to read, and cause big hiccups in processing power
        # it is best to ready infrequently to avoid this
        self.update_interval = interval
        self.events = DHTEvents()
        self.events.on_state_changed += on_state_changed
        self.events.on_temperature_changed += on_temperature_changed
        self.events.on_humidity_changed += on_humidity_changed

        self.state = TemperatureState()
        self.pin_data = pin_data
        self.sensor_model = sensor_model

    def update_settings(self, new_settings):
        super().update_settings(new_settings)
        with self.lock:
            if self.settings != None:
                if "dht" in self.settings:
                    if "pin_data" in self.settings["dht"]:
                            self.pin_data =  int(self.settings["dht"]["pin_data"])

    def on_startup(self):
        try:
            if USE_LEGACY_DHT:
                self.sensor = self.sensor_model
            else:
                self.sensor = adafruit_dht.DHT22(data_pin, use_pulseio=False)
            
        except:
            self.sensor = None
            log_exception()

    def on_shutdown(self):
        self.disconnect()

    def disconnect(self):
        if not COMPILE_PC:
            if self.sensor is not None:
                if USE_LEGACY_DHT:
                    pass
                else:
                    self.sensor.exit()
                
                self.sensor = None

    def on_interval_update(self):
        if not COMPILE_PC:
            if self.sensor is not None:
                try:    

                    # Note: this can take 0.5 seconds 
                    if USE_LEGACY_DHT:
                        new_humidity, new_temperature = Adafruit_DHT.read_retry(sensor=self.sensor,pin=self.pin_data) # GPIO4 is pin #7
                    else:            
                        new_humidity = self.sensor.humidity
                        new_temperature = self.sensor.temperature

                    old_state = str(self.state)
                    humid_changed =  new_humidity != self.state.humidity
                    temp_changed = new_temperature != self.state.value
                    self.state.humidity = new_humidity
                    self.state.value = new_temperature
                    state_changed = old_state != str(self.state)
                    if state_changed:
                        self.force_state_change()
                    if humid_changed:
                        self.events.on_humidity_changed(self.state.humidity,self)
                    if temp_changed:
                        self.events.on_temperature_changed(self.state.value, self)
                        
                except RuntimeError as error:
                    self.log(error.args[0], ThreadLogSeverity.ERROR)                    
                except Exception as error:
                    log_exception()
                    if self.sensor is not None:
                        self.disconnect()
                        self.log("Critical problem communicating with {0}. Disconnected.".format(self.name), ThreadLogSeverity.ERROR)

