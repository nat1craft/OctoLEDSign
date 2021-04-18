import sys, time, json, copy
from datetime import datetime
from enum import IntEnum
from operator import attrgetter

import paho.mqtt.client as mqtt 
from utils.utils import *
from utils.base_threaded_loop import *
from mqtt.mqtt_broker import *

class MQTTPrinterStateCode(IntEnum):
    ERROR = -100
    OFFLINE = -1
    UNKNOWN = 0
    INITIALIZING = 1
    READY = 10
    PROCESSING = 20
    CANCELLING = 30
    CANCELLED = 39
    PAUSING = 40
    PAUSED = 49
    RESUMING = 50,

class MQQTTemperatureState():
    def __init__(self, actual = 0, target = 0, decimals = 0, units = "°C", convert_to_fahrenheit = False):
        self.actual = actual
        self.target = target
        self.decimals = decimals
        self.units = units
        self.convert_to_fahrenheit = convert_to_fahrenheit

    def convert(self, temp):
        if self.convert_to_fahrenheit:
            return temp * (9/5) + 32
        return temp

    def formatted_actual(self, show_units : True):
        fmt_dec = ".{0}f".format(self.decimals)
        all_format = "{{0:{0}}}{1}".format(fmt_dec, self.units if show_units else "")
        return all_format.format(self.convert(self.actual))

    def formatted_target(self, show_units : True):
        fmt_dec = ".{0}f".format(self.decimals)
        all_format = "{{0:{0}}}{1}".format(fmt_dec, self.units if show_units else "")
        return all_format.format(self.convert(self.target))

    def __str__(self):
        fmt_dec = ".{0}f".format(self.decimals)

        if self.target != 0:
            all_format = "{{0:{0}}}{1} => {{1:{0}}}{1}".format(fmt_dec, self.units)
            return all_format.format(self.convert(self.actual),self.convert(self.target))
        else:
            all_format = "{{0:{0}}}{1}".format(fmt_dec, self.units)
            return all_format.format(self.convert(self.actual))

    def concise(self, show_units, show_direction = False):
        fmt_dec = ".{0}f".format(self.decimals)

        if self.target != 0 and show_direction:
            symbol = "+" if self.target > self.actual else "-"
            all_format = "{{0:{0}}}{1}{2}".format(fmt_dec, self.units if show_units else "", symbol)
            return all_format.format(self.convert(self.actual),self.convert(self.target))
        else:
            all_format = "{{0:{0}}}{1}".format(fmt_dec, self.units if show_units else "")
            return all_format.format(self.convert(self.actual))


class MQQTPrinterState():
    def __init__(self):
        self.name = None
        self.state_code = MQTTPrinterStateCode.UNKNOWN
        self.status = "..."
        self.bed = MQQTTemperatureState()
        self.extruder = MQQTTemperatureState()
        self.air = None
        self.progress = 0.0
        self.totalLayers = 0
        self.currentLayer = 0
        self.filename = None
        self.time_remaining = None
        self.time_est_end = None        

    def __str__(self):
        text = "Progress: {0:.0f}%".format(self.progress) 
        text += "\tExtruder: {0}".format(self.extruder)
        text += "\tBed: {0}".format(self.bed)
        text += "\tStatus: {0}".format(self.status) 
        if isinstance(self.state_code,int) and self.state_code >= MQTTPrinterStateCode.PROCESSING:
            text += "\tLayer: {0}/{1}".format(self.currentLayer,self.totalLayers) 
            if self.filename!=None and self.filename != "":
                text += "\tFile: {0}".format(self.filename) 
            if self.time_remaining!=None and self.time_remaining != "":
                text += "\t\tTime Left: {0}".format(self.time_remaining) 
        return text


class MQTTPrinterThread(MonitoredStateLoop):
    def __init__(self, settings, on_state_changed=None):
        super().__init__(settings,on_state_changed=on_state_changed)
        if self.settings != None:
            self.name = self.settings["name"]
        else:
            self.name = "Unknown"
        self.mqtt_client = None
        self.state = MQQTPrinterState()
        self.state.name = self.name
        self.broker_settings = None

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
                            self.state.bed.decimals = temp_settings["decimals"]
                            self.state.extruder.decimals = temp_settings["decimals"]
                        if "display_units" in temp_settings:
                            self.state.bed.units = temp_settings["display_units"]
                            self.state.extruder.units = temp_settings["display_units"]
                        if "convert_to_fahrenheit" in temp_settings:
                            self.state.bed.convert_to_fahrenheit = temp_settings["convert_to_fahrenheit"]
                            self.state.extruder.convert_to_fahrenheit = temp_settings["convert_to_fahrenheit"]

            self.broker_settings = MQTTBrokerSettings(device_settings=self.settings, global_settings=self.global_settings)

    def on_connected(self,client, userdata, flags, rc):
        if rc == 0:
            self.log("Connected to MQTT Broker.", ThreadLogSeverity.SUCCESS)
        else:
            self.log("Failed to connect, return code {0}".format(rc), ThreadLogSeverity.ERROR )
            return None
    
    def on_disconnected(self,client, userdata, rc):
        self.log("Disconnected from broker.")
        
    def reconnect(self):
        if self.mqtt_client != None:
            self.disconnect()

        if not self.broker_settings.enabled:
            self.log("MQTT disabled in configuration.")
            return None
        else:
            client = mqtt.Client()
            client.username_pw_set(self.broker_settings.username, self.broker_settings.password)
            client.on_connect = self.on_connected
            client.on_disconnect = self.on_disconnected
            
            host = self.broker_settings.host
            port = self.broker_settings.port
            self.log("Connecting to MQTT server @ {0}:{1}".format(host, port))
            client.connect(host,port)
            return client

    def disconnect(self):
        if self.mqtt_client != None:
            self.mqtt_client.loop_stop(True)
            self.mqtt_client = None

    def subscribe_to_events(self):
        if self.mqtt_client == None:
            return
        
        mqtt_settings = self.settings["mqtt"]
        all_fields = mqtt_settings["field_map"]

        # get unique topics so we subscribe to them just once
        unique_topics = get_unique_values(all_fields,"topic")
        for topic in unique_topics:
            self.mqtt_client.subscribe(topic, qos=1)
            self.mqtt_client.message_callback_add(topic, self.on_topic_changed)

    def on_topic_changed(self,client, userdata, message):
        json_msg = json.loads( message.payload.decode())  

        mqtt_settings = self.settings["mqtt"]
        all_fields = mqtt_settings["field_map"]

        # get fields associated with this topic
        matching_fields = get_matching_items(all_fields,"topic",message.topic) 
        state_object = self.state
        changed = False
        for field in matching_fields:
            if ("name" not in field) or (field["name"] == ""):
                self.log("Invalid name detected for fields. This value should match the fixed set of name values available.")
            else:
                state_field_name = field["name"]
                payload_field_name = field["query"] if "query" in field else state_field_name
                new_value = dictor(json_msg, payload_field_name)
                # see if we want to translate this value into something else
                if "translate" in field and field["translate"] != "":
                    lookup_list = dictor(self.settings,field["translate"])
                    default_lookup = new_value
                    if "default" in field and field["default"]!="":
                        default_lookup = field["default"]

                    if lookup_list == None:
                        self.log("Lookup list {0} for field {1} was not found.".format(field["translate"], field.name))
                    else:
                        if isinstance(new_value,str):
                            new_value = lookup_list.get(new_value.upper() if new_value != None else new_value, default_lookup)
                        else:
                            new_value = lookup_list.get(new_value if new_value != None else new_value, default_lookup)
                
                # get the associated attribute from the state object, where we wish to store this new value
                state_oject_attribute = attrgetter(state_field_name)(state_object)
                # check for a change in the value (from previous state)
                old_value = state_oject_attribute
                if new_value != old_value:
                    changed = True
                # set the state to reflect the new value
                setattr_nested(state_object, state_field_name, new_value)

        # if anything actually changed for any field, then fire off a state changed message with a copy of the state object
        if changed:
            self.force_state_change()

    def on_startup(self):
        if self.mqtt_client == None:
            self.mqtt_client = self.reconnect()
            if self.mqtt_client is not None:
                self.mqtt_client.loop_start()
                self.subscribe_to_events()

    def on_shutdown(self):
        self.disconnect()
