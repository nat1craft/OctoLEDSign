# Class to monitor a rotary encoder and update a value.  You can either read the value when you need it, by calling current_value(), or
# you can configure a callback which will be called whenever the value changes.

import os, time, threading
COMPILE_PC = os.path.sep=="\\"

from hardware.pushbutton import *
from utils.events import *

if COMPILE_PC:
    from hardware.rpi_stubs import gpio_stubs as GPIO
else:
    import RPi.GPIO as GPIO

class RoataryEncoderEvents(Events):
        __events__ = ("on_rotate")

class RotaryEncoder(PushButton):
    UNKNOWN = None
    LEFT = 1
    RIGHT = 2

    def __init__(self, leftPin, rightPin, buttonPin=None, 
                    on_rotate=None, on_button_down=None, on_button_up=None, on_long_press=None, on_long_press_notify=None, on_very_long_press=None, on_very_long_press_notify=None, 
                    max_value=None, min_value=None, value_per_click=1, 
                    long_press_duration=3, very_long_press_duration=6, 
                    switch_bounce=100,
                    value= 0):
 
        self.leftPin = leftPin
        self.rightPin = rightPin

        self.value = value
        self.state = '00'
        self.direction = RotaryEncoder.UNKNOWN

        self.encoder_events = RoataryEncoderEvents()
        self.encoder_events.on_rotate += on_rotate

        self.max_value = max_value
        self.min_value = min_value
        self.value_per_click = value_per_click
        self.switch_bounce = switch_bounce

        super().__init__(buttonPin, 
                        on_button_down, on_button_up, on_long_press, on_long_press_notify, on_very_long_press, on_very_long_press_notify, 
                        long_press_duration, very_long_press_duration, 
                        switch_bounce)

    def to_json(self):       
        return "{{ \"button\":{0}, \"encoder\": {{ \"value\":{1}, \"max\":{2}, \"min\":{3}, \"direction\":{3} }} }}".format(super().to_json(), self.value, self.max_value, self.min_value, self.direction)


    def set_value(self,new_value):
        if self.max_value is not None:
            new_value = min(self.max_value, new_value)
        if self.min_value is not None:
            new_value = max(self.min_value, new_value)
        self.value = new_value

    def disconnect(self):
        super().disconnect()
        GPIO.remove_event_detect(self.leftPin)  
        GPIO.remove_event_detect(self.rightPin)  

    def connect(self):
        super().connect()

        GPIO.setup(self.leftPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.rightPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(self.leftPin, GPIO.BOTH, callback=self.on_rotary_transition)  
        GPIO.add_event_detect(self.rightPin, GPIO.BOTH, callback=self.on_rotary_transition)  

    def on_rotary_transition(self, channel):
        p1 = GPIO.input(self.leftPin)
        p2 = GPIO.input(self.rightPin)
        newState = "{}{}".format(p1, p2)

        if self.state == "00": # Resting position
            if newState == "01": # Turned right 1
                self.direction = RotaryEncoder.RIGHT
            elif newState == "10": # Turned left 1
                self.direction = RotaryEncoder.LEFT

        elif self.state == "01": # R1 or L3 position
            if newState == "11": # Turned right 1
                self.direction = RotaryEncoder.RIGHT
            elif newState == "00": # Turned left 1
                if self.direction == RotaryEncoder.LEFT:
                    self.update_value(self.value - self.value_per_click)

        elif self.state == "10": # R3 or L1
            if newState == "11": # Turned left 1
                self.direction = RotaryEncoder.LEFT
            elif newState == "00": # Turned right 1
                if self.direction == RotaryEncoder.RIGHT:
                    self.update_value(self.value + self.value_per_click)

        else: # self.state == "11"
            if newState == "01": # Turned left 1
                self.direction = RotaryEncoder.LEFT
            elif newState == "10": # Turned right 1
                self.direction = RotaryEncoder.RIGHT
            elif newState == "00": # Skipped an intermediate 01 or 10 state, but if we know direction then a turn is complete
                if self.direction == RotaryEncoder.LEFT:
                    self.update_value(self.value - self.value_per_click)
                elif self.direction == RotaryEncoder.RIGHT:
                    self.update_value(self.value + self.value_per_click)
                
        self.state = newState

    def value_increased(self):
        return self.direction==RotaryEncoder.RIGHT

    def value_decreased(self):
        return self.direction==RotaryEncoder.LEFT
    
    def update_value(self, new_value):
        self.set_value(new_value)
        self.encoder_events.on_rotate(self.value,self.direction)

    def current_value(self):
        return self.value