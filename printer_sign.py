import sys, os, copy, math, random
import time, json
from datetime import datetime

from utils.utils import *
from signage.display_message_custom import *
from signage.hardware_surfaces import *
from mqtt.mqtt_octoprinter import *

COMPILE_PC = os.path.sep=="\\"

if COMPILE_PC:
    TIME_FORMAT = "%H:%M"
else:
    TIME_FORMAT = "%-I:%M%P"

class printer_sign(emulator_surface):  #max7219_surface
    def __init__(self,json_settings=None,id=None,fps=AreaUpdate_Default.SIGN_FPS,areas=[],muted=True,\
                    port=0,device=0,cascaded=4,block_orientation=-90,blocks_arranged_in_reverse_order=False,contrast=128,\
                    json_section="max7219",\
                    sensor_temp=None):
        
        if COMPILE_PC:
            print("Overriding and loading emulator")
            super().__init__(json_settings=json_settings,id=id,fps=fps,areas=areas,muted=muted,json_section="emulator")
        else:
            super().__init__(json_settings=json_settings,id=id,fps=fps,areas=areas,muted=muted,\
                        port=port,device=device,cascaded=cascaded,block_orientation=block_orientation,blocks_arranged_in_reverse_order=blocks_arranged_in_reverse_order,contrast=contrast,\
                        json_section=json_section)

        self.sensor_temp = sensor_temp
        self.pending_messages = None
        
        self.last_text_for_area = {}

    def initialize(self):
        super().initialize()
        self.pending_messages = {}
        for area in self.areas.values():
            area.events.on_ready_to_consume += self.on_area_ready_to_consume
            self.pending_messages[area.id] = None
            self.last_text_for_area[area.id] = None

    def on_area_ready_to_consume(self,area):
        if area is None or not self.has_area(area.id):
            return
        if area.id in self.pending_messages:
            pending_msg = self.pending_messages[area.id]
            if pending_msg is not None:
                if is_iterable(pending_msg):
                    first = True
                    for sub_msg in pending_msg:
                        self.queue_message(area.id,sub_msg,clear_existing=first)
                        first = False
                else:
                    self.queue_message(area.id,pending_msg,clear_existing=True)
            del self.pending_messages[area.id]

    def submit_state_change(self, new_state, printer, alt_info_state=0):        
        show_temps = True
        state = new_state
        now = datetime.now()

        main_message = None
        main_message_blink = False
        main_message_build = False
        err_message = None
        err_message_major = False

        #state.state_code = MQTTPrinterStateCode.PROCESSING        
        if state.state_code == MQTTPrinterStateCode.ERROR:
            if alt_info_state % 2 == 0:
                main_message = printer.name if printer is not None else "unknown"
            err_message = "error"
            err_message_major = True
        elif state.state_code == MQTTPrinterStateCode.OFFLINE:
            if alt_info_state == 1:
                main_message = printer.name if printer is not None else "unknown"
                main_message_build = True
            elif alt_info_state == 2 and  self.sensor_temp is not None:                     
                state.air = self.sensor_temp.state
            else:
                main_message = now.strftime(TIME_FORMAT)
            err_message = "Offline"
        elif state.state_code == MQTTPrinterStateCode.READY:
            if alt_info_state == 1:
                main_message = printer.name if printer is not None else "unknown"
                main_message_build = True
            elif alt_info_state == 2 and self.sensor_temp is not None:
                state.air = self.sensor_temp.state
            else:
                main_message = now.strftime(TIME_FORMAT)
        elif int(state.state_code) == MQTTPrinterStateCode.PROCESSING:
            is_warming_up = (state.extruder.target!=0 and (state.extruder.target-state.extruder.actual)>5) or (state.bed.target!=0 and (state.bed.target-state.bed.actual)>5)
            if is_warming_up:
                if alt_info_state <=1 and self.sensor_temp is not None:
                    state.air = self.sensor_temp.state
                else:
                    main_message = "warming"
                    main_message_build = True
            else:
                if alt_info_state == 1:
                    main_message = "{0:.0f}%".format(state.progress)
                elif alt_info_state == 2:
                    main_message = "{0}/{1}".format(state.currentLayer, state.totalLayers)                
                elif alt_info_state == 3 and state.time_remaining != "-":
                    main_message = "{0}".format(state.time_remaining)
                elif alt_info_state == 4 and self.sensor_temp is not None:
                    state.air = self.sensor_temp.state
        elif state.state_code == MQTTPrinterStateCode.CANCELLING or  state.state_code == MQTTPrinterStateCode.CANCELLING:
            main_message_blink = True
            main_message = "cancelled"
        else:
            if alt_info_state == 4 or state.status is None or state.status == "":
                main_message = now.strftime(TIME_FORMAT)
            else:
                main_message = state.status

        if state.air is not None:
            main_message = "\x7F\x7F {0}".format(state.air.formatted())
            self.pending_messages["msg"] = text_message(text=main_message,blink_options=message_blink_options(enabled=main_message_blink))
        elif main_message is not None:
            if main_message != self.last_text_for_area["msg"]:
                if main_message_build:
                    self.pending_messages["msg"] = [
                        builder_text_message(text=main_message,blink_options=message_blink_options(enabled=main_message_blink)),
                        builder_text_message(text=main_message,blink_options=message_blink_options(enabled=main_message_blink),explode=True, explode_pause=3)
                    ]
                else:
                    self.pending_messages["msg"] = text_message(text=main_message,blink_options=message_blink_options(enabled=main_message_blink))

        if err_message is not None:
            if self.last_text_for_area["err"] is None or not self.last_text_for_area["err"] == err_message:
                self.pending_messages["msg"] = text_message(text=err_message,blink_options=message_blink_options(enabled=True, invert=err_message_major))
            show_temps = False
            self.clear("temp1")
            self.clear("temp2")
        else:
            self.clear("err")
            

        if show_temps:
            max_chars = "%.4s"
            ext_msg = max_chars % state.extruder.concise(show_units=True)
            bed_msg = max_chars % state.bed.concise(show_units=True)

            if not self.last_text_for_area["temp1"] == ext_msg:
                self.pending_messages["temp1"] = temperature_message(text=self.last_text_for_area["temp1"],new_text=ext_msg,draw_glyph="extruder")
                self.last_text_for_area["temp1"] = ext_msg
            if not self.last_text_for_area["temp2"] == bed_msg:
                self.pending_messages["temp2"] = temperature_message(text=self.last_text_for_area["temp2"],new_text=bed_msg,draw_glyph="bed")
                self.last_text_for_area["temp2"] = bed_msg

        self.last_text_for_area["msg"] = main_message
        self.last_text_for_area["err"] = err_message

