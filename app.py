# pip3 freeze > requirements.txt

import time
from datetime import datetime
import threading
import http.client as httplib
import json
import urllib.request
import sys, os
import subprocess

COMPILE_PC = os.path.sep=="\\"

from utils.utils import *
from mqtt.mqtt_octoprinter import *
from mqtt.mqtt_sensor import *

if COMPILE_PC:
    from hardware.rpi_stubs import gpio_stubs as GPIO    
else:
    import RPi.GPIO as GPIO
    from hardware.dht import *

from hardware.rotary_encoder import *
from signage.display_message import *
from signage.hardware_surfaces import *
from printer_sign import *

class ShutdownRequest(IntEnum):
    NONE = 0
    REBOOT = 1
    SHUTDOWN = 2

class App():
    def __init__(self):
        self.settings = None
        self.printer_listener = MQTTPrinterThread(None, on_state_changed=self.on_printer_state_changed)
        self.sign_surface = None

        if COMPILE_PC:
            self.sensor_temp = None
        else:
             self.sensor_temp = DHTSensor(None, on_state_changed=self.on_temperature_state_changed)

        self.all_loops = []
        if self.printer_listener is not None:
            self.all_loops.append(self.printer_listener)
        if self.sensor_temp != None:
            self.all_loops.append(self.sensor_temp)

        self.mqtt_sensor_array = MQTTSensorArray(sensors=[self.sensor_temp])

        self.last_state_change = time.time()
        self.last_state = None
        self.alt_info_state = 0
        self.alt_info_max_state = 4
        self.alt_info_time = None
        self.alt_info_interval = 5
        
        self.rotary_encoder = None
        self.settings_require_save = False
        self.shutdown_request = ShutdownRequest.NONE

        self.pending_printer_state_change = None
        self.monitor_sleep_duration = 1


    def on_temperature_state_changed(self,new_state,sensor):
        #print("{0}:\t{1}".format(sensor.name, new_state))
        pass

    def on_printer_state_changed(self, new_state, printer):
        self.pending_printer_state_change = (new_state,printer)

    def process_pending_printer_state_change(self):
        if self.pending_printer_state_change is None:
            return
        
        new_state = self.pending_printer_state_change[0]
        printer = self.pending_printer_state_change[1]

        print("{0}:\t{1}".format(printer.name if printer is not None else "unknown", new_state))
        if self.last_state != None and self.last_state.state_code != new_state.state_code:
            self.alt_info_state = 0

        if self.sign_surface!=None:                
            self.sign_surface.submit_state_change(new_state=new_state,printer=printer,alt_info_state=self.alt_info_state)
            
        self.last_state_change = time.time()
        self.last_state = new_state
    
        self.pending_printer_state_change =  None

    def main(self):
        self.reload_settings()
        print("Application settings loaded.")

        try:
            if self.sign_surface is not None:
                self.sign_surface.start()

            for threaded_loop in self.all_loops:
                threaded_loop.start()

            self.mqtt_sensor_array.connect()

            self.alt_info_time = time.time()

            counter = 0
            while self.shutdown_request == ShutdownRequest.NONE:
                now = time.time()
                start_time = now

                self.process_pending_printer_state_change()

                elapsed_time = (now - self.alt_info_time) 
                if elapsed_time >= self.alt_info_interval:
                    self.alt_info_state += 1
                    if self.alt_info_state > self.alt_info_max_state:
                        self.alt_info_state = 0
                    self.alt_info_time = now
                    if self.printer_listener is not None:
                        self.printer_listener.force_state_change()
                    else:
                        dummy_state = MQQTPrinterState()
                        dummy_state.extruder.actual = 50 + counter
                        dummy_state.bed.actual = 500 - counter
                        self.on_printer_state_changed(new_state=dummy_state, printer=None)
                if self.settings_require_save:
                    self.save_settings()

                time_remaining = self.monitor_sleep_duration - (time.time() - start_time)
                if time_remaining > 0:
                    time.sleep(time_remaining)
                else:
                    print("Cannot keep up with processing rate!")
                counter += 1

        except KeyboardInterrupt:
            print("Execution stopped by user.")
        except Exception as e:
            print(e)            
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)            
        finally:  
            print("Stopping background threads...")
            if self.sign_surface is not None:
                print("Requesting display surface {0} to stop...".format(self.sign_surface.id))
                self.sign_surface.stop()                
            for threaded_loop in self.all_loops:
                threaded_loop.request_stop()
            for threaded_loop in self.all_loops:
                threaded_loop.join()
            self.mqtt_sensor_array.disconnect()
            if self.sign_surface is not None:
                while not self.sign_surface.is_stopped:
                    time.sleep(1/25)
            print("Background threads stopped.")
            if self.rotary_encoder != None:
                GPIO.cleanup()

        if self.shutdown_request != ShutdownRequest.NONE:
            self.execute_shutdown(self.shutdown_request)

    def get_settings_filename(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        return "{0}{1}settings.json".format(dir_path,os.path.sep)

    def save_settings(self):
        try:
            if self.settings == None:
                self.settings = {}
            settings_filename = self.get_settings_filename()
            with open(settings_filename,"w") as outfile:
                json.dump(self.settings,outfile)
            print("Application settings saved: {0}".format(settings_filename))            
            self.settings_require_save = False
        except Exception as e:                
            log_exception()

    def reload_settings(self):
        try:
            self.settings = {}
            settings_filename = self.get_settings_filename()
            with open(settings_filename) as file:
                self.settings = json.load(file)     
            print("Application settings loaded: {0}".format(settings_filename))            

            for threaded_loop in self.all_loops:
                threaded_loop.global_settings = self.settings

            if "printers" in self.settings:
                if self.printer_listener is not None:
                    self.printer_listener.update_settings(self.settings["printers"][0])

            if self.sensor_temp != None and "sensors" in self.settings:
                self.sensor_temp.update_settings(self.settings["sensors"][0])

            if self.rotary_encoder != None:    
                self.rotary_encoder.disconnect()                           
                self.rotary_encoder = None
            encoder_settings = self.settings["encoder"]
            encoder_enabled = encoder_settings["enabled"] == True
            if encoder_enabled:
                #GPIO.setmode(GPIO.BOARD)
                GPIO.setmode(GPIO.BCM)
                self.rotary_encoder = RotaryEncoder(
                        max_value=255, min_value=0, value_per_click=encoder_settings["sensitivity"],
                        leftPin=encoder_settings["pin_left"], rightPin=encoder_settings["pin_right"], buttonPin=encoder_settings["pin_click"],
                        on_rotate=self.on_encoder_changed, 
                        on_button_up=self.on_encoder_press, 
                        on_long_press=self.on_encoder_long_press, on_long_press_notify=self.on_encoder_long_press_notify, 
                        on_very_long_press=self.on_encoder_very_long_press, on_very_long_press_notify=self.on_encoder_very_long_press_notify)
                    
                print("encoder: enabled")
            else:
                print("encoder: disabled")

            self.mqtt_sensor_array.update_settings(None, self.settings)

            assert(self.sign_surface is None)
            display_settings = self.settings["display"]
            surface_type = display_settings["type"] if "type" in display_settings else "emulator_surface"
            if not surface_type in globals():
                err_message = "There is no surface class of the type: {0}".format(surface_type)
                raise Exception(err_message)
            else:
                print("Loading display of type: {0}".format(surface_type))
            sign_class = globals()[surface_type]            
            self.sign_surface = sign_class(json_settings=display_settings)
            if hasattr(self.sign_surface,"sensor_temp"):
                self.sign_surface.sensor_temp = self.sensor_temp
            self.sign_surface.initialize()

            app_settings = self.settings["app"] if "app" in self.settings else {}
            if  self.sign_surface != None and "display_brightness" in app_settings:
                brightness = int(app_settings["display_brightness"])
                if brightness >=  0:
                    self.sign_surface.brightness = brightness
                    
            if self.sign_surface != None and encoder_enabled and self.rotary_encoder != None:
                self.rotary_encoder.set_value(self.sign_surface.brightness)

        except Exception as e:                
            log_exception()
    
    def on_encoder_changed(self,new_value, direction):
        print("encoder: value={0}\tdirection={1}".format(new_value,"Left" if direction == RotaryEncoder.LEFT else "right"))
        if self.sign_surface != None:
            self.sign_surface.brightness = new_value
            
            if "app" not in self.settings:
                self.settings["app"] = {}
            app_settings = self.settings["app"]
            app_settings["display_brightness"] = new_value
            self.settings_require_save = True
        else:
            print("encoder: no display!")

    def on_encoder_press(self,channel):
        print("encoder: pressed")

    def on_encoder_long_press_notify(self,channel):
        print("encoder: long press notification")

    def on_encoder_long_press(self,channel):
        print("encoder: long press occurred")
        self.shutdown_request = ShutdownRequest.REBOOT

    def on_encoder_very_long_press_notify(self,channel):
        print("encoder: VERY long press notification")

    def on_encoder_very_long_press(self,channel):
        print("encoder: VERY long press occurred")
        self.shutdown_request = ShutdownRequest.SHUTDOWN

    def execute_shutdown(self, request_type):
        command = None
        command_name = None
        app_settings = self.settings["app"] if "app" in self.settings else None
        commands = app_settings["commands"] if app_settings is not None else None

        if commands is not None:
            if request_type == ShutdownRequest.REBOOT:
                command_name = "reboot"
            elif request_type == ShutdownRequest.SHUTDOWN:
                command_name = "shutdown"
            if command_name is not None:
                command = commands[command_name] if command_name in commands else None

        if command != None:
            print("encoder: {0} requested".format(command_name))
            self.execute_command(command)

    def execute_command(self, command):
        if command is not None and command != "":
            print("executing: {0}".format(command))
            process = subprocess.Popen(command.split(),stdout=subprocess.PIPE)
            output = process.communicate()[0]
            print(output)

if __name__ == "__main__":
    app = App()
    app.main()
