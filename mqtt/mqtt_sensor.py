import sys, time, json, copy
from datetime import datetime
from enum import IntEnum
from operator import attrgetter
import threading

import paho.mqtt.client as mqtt 
from utils.utils import *
from utils.base_threaded_loop import *

from hardware.sensor import *
from mqtt.mqtt_broker import *

class MQTTPublisher:
    def __init__(self):
        self.name = "Pub"
        self.settings = None
        self.enabled = False
        self.global_settings = None
        self.lock = threading.Lock()
        self.broker_settings = None
        self.client = None
        self.client_connected = False

    def update_settings(self, new_settings, global_settings : None):
        with self.lock:
            self.settings = new_settings
            self.global_settings = global_settings
            if self.settings is not None and "name" in self.settings:
                self.name = self.settings["name"]
            else:
                self.name = "Pub"
            self.broker_settings = MQTTBrokerSettings(device_settings=self.settings, global_settings=global_settings)

    def log(self, message):
        prefix = "{0}:\t".format(self.name)
        print("{0}{1}".format(prefix, message))

    def is_ready():
        return not self.enabled or self.client_connected

    def disconnect(self):
        if self.client!= None:
            self.client.loop_stop(True)
            self.client = None
        self.client_connected = False

    def connect(self):
        if self.client is not None and self.client_connected:
            self.log("Attempted to connect while already connected")
            return
        
        if not self.broker_settings.enabled:
            self.log("MQTT not enabled for device")
            return 

        # Set Connecting Client ID
        self.client_connected = False
        self.client = mqtt.Client()
        self.client.username_pw_set(self.broker_settings.username, self.broker_settings.password)
        self.client.on_connect = self.on_broker_connected
        self.log("Connecting to server @ {0}:{1}".format(self.broker_settings.host, self.broker_settings.port))
        self.client.connect(self.broker_settings.host, self.broker_settings.port)
        self.client.loop_start()
        
    def on_broker_connected(self, client, userdata, flags, rc):
        if rc == 0:
            self.log("Connected to MQTT Broker @ {0}".format(self.broker_settings.host))
            self.client_connected = True            
        else:
            self.log("Failed to connect to broker @ {0}, return code {1}".format(self.broker_settings.host, rc))

    def get_base_topic(self):
        topic = None
        if self.global_settings is not None and "mqtt_brokers" in self.global_settings:
            brokers = self.global_settings["mqtt_brokers"]
            matching = get_matching_items(brokers, "id", 0 if self.broker_settings.broker_id is None else self.broker_settings.broker_id)
            if len(matching) == 0:
                self.log("Failed to identify the MQTT broker base topic.")
            else:
                settings = matching[0]
                if "publish" in settings:
                    publish_settings = settings["publish"]
                    if "base_topic" in publish_settings:
                        topic = publish_settings["base_topic"].strip()
                        if topic == "":
                            topic = None

        if topic is None:
            topic = "{0}/".format(self.name)
        else:
            topic = "{0}/{1}/".format(topic,self.name)
        return topic

class MQTTSensorArray(MQTTPublisher):
    def __init__(self, sensors = []):
        super().__init__()
        self.name = "Sensors"
        self.sensors = []
        self.attach_sensors(sensors)

    def update_settings(self, new_settings, global_settings : None):
        super().update_settings(new_settings, global_settings)
        with self.lock:
            self.name = "Sensors"

    def detach_sensors(self, list_of_sensors):
        for sensor in list_of_sensors:            
            self.detach_sensor(sensor)

    def attach_sensors(self, list_of_sensors):
        for sensor in list_of_sensors:            
            self.attach_sensor(sensor)

    def detach_sensor(self,sensor):
       with self.lock:
            if sensor is None or sensor not in self.sensors:
                return False

            sensor.events.on_state_changed -= self.on_observed_sensor_state_changed
            self.sensors.remove(sensor)
            return True

    def attach_sensor(self, sensor):        
        with self.lock:
            if sensor is None or sensor in self.sensors:
                return False

            sensor.events.on_state_changed += self.on_observed_sensor_state_changed
            self.sensors.append(sensor)
            return True

    def is_sensor_enabled(self,sensor):
        return True

    def on_observed_sensor_state_changed(self, new_state, sensor):
        # report the state change via MQTT
        if not self.client_connected:
            self.log("Sensor {0} state changed, but client not connected/ready for publishing.".format(sensor.name))
            return
        elif not self.is_sensor_enabled(sensor):
            self.log("Sensor {0} state changed, but MQTT publisher is not enabled.".format(sensor.name))
            return

        topic = "{0}{1}/state".format(self.get_base_topic(), sensor.name)
        payload = None
        serialize_op = None if new_state is None else getattr(new_state,"to_json", None)
        if callable(serialize_op):
            payload = json.dumps(json.loads(serialize_op()), indent=4)
        else:
            payload = None if new_state is None else str(new_state)
        
        if payload is None:
            self.log("no payload to publish for topic:{0}".format(topic))
        else:
            pubres = self.client.publish(topic, payload, 0, True)
            pubres.wait_for_publish()

