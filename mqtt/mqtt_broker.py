import sys, time, json, copy
from datetime import datetime
from enum import IntEnum

import paho.mqtt.client as mqtt 
from utils.utils import *

MQTT_DEFAULT_PORT = 1883

class MQTTBrokerSettings:
    def __init__(self, username = None, password= None, host=None, port=MQTT_DEFAULT_PORT, device_settings = None, global_settings = None):
        self.enabled = True
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.broker_id = None

        if device_settings is not None or global_settings is not None:
            self.from_settings(device_settings,global_settings)

    def reset(self):
        self.enabled = True
        self.username = None
        self.password = None
        self.host = None
        self.port = MQTT_DEFAULT_PORT
        self.broker_id = None

    def from_settings(self, device_settings, global_settings):
        self.reset()
        broker_settings = None
        if device_settings is not None:
            if "mqtt" in device_settings:
                device_mqtt_settings = device_settings["mqtt"]
                self.enabled = device_mqtt_settings["enabled"] if "enabled" in device_mqtt_settings else True
                self.broker_id = device_mqtt_settings["broker_id"] if "broker_id" in device_mqtt_settings else None

                if self.broker_id is None or global_settings is None:
                    broker_settings = device_mqtt_settings
                else:
                    brokers = global_settings["mqtt_brokers"] if "mqtt_brokers" in global_settings  else None
                    if brokers is None:
                        broker_settings = device_mqtt_settings
                    else:
                        broker_settings = brokers[self.broker_id]

        elif global_settings is not None:            
            brokers = global_settings["mqtt_brokers"] if "mqtt_brokers" in global_settings  else None
            if brokers is not None:
                broker_settings = brokers[0]

        if broker_settings is not None:
            self.enabled = broker_settings["enabled"] if "enabled" in broker_settings else True
            self.username = broker_settings["user"] if "user" in broker_settings else None
            self.password = broker_settings["password"] if "password" in broker_settings else None
            self.host = broker_settings["host"] if "host" in broker_settings else None
            self.port = int(broker_settings["port"]) if "port" in broker_settings else MQTT_DEFAULT_PORT



