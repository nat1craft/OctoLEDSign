import os, time, threading
from utils.events import *

COMPILE_PC = os.path.sep=="\\"

if COMPILE_PC:
    from hardware.rpi_stubs import gpio_stubs as GPIO
else:
    import RPi.GPIO as GPIO

class PushButtonEvents(Events):
        __events__ = ("on_button_down","on_button_up","on_long_press","on_long_press_notify","on_very_long_press","on_very_long_press_notify")


class PushButton:

    def __init__(self, buttonPin=None, 
                    on_button_down=None, on_button_up=None, on_long_press=None, on_long_press_notify=None, on_very_long_press=None, on_very_long_press_notify=None, 
                    long_press_duration=3, very_long_press_duration=6, 
                    switch_bounce=100):
                    
        self.buttonPin = buttonPin
        self.switch_bounce = switch_bounce

        self.button_events = PushButtonEvents()
        self.button_events.on_button_down += on_button_down
        self.button_events.on_button_up += on_button_up
        self.button_events.on_long_press += on_long_press
        self.button_events.on_long_press_notify += on_long_press_notify
        self.button_events.on_very_long_press += on_very_long_press
        self.button_events.on_very_long_press_notify += on_very_long_press_notify

        self.long_press_duration = long_press_duration
        self.very_long_press_duration = very_long_press_duration

        self.switch_press_start = time.time()
        self.long_press_thread = None
        self.very_long_press_thread = None

        self.connect()

    def to_json(self):       
        return "{{\"state\":\"{0}\", \"time\": \"{1}\" }}".format( "closed"  if GPIO.input(self.buttonPin) == GPIO.LOW else 'open',  datetime.now().isoformat() )

    def  disconnect(self):
        GPIO.remove_event_detect(self.buttonPin) 
        self.cancel_notify_threads()
 
    def cancel_notify_threads(self):
        if self.long_press_thread != None:
            self.long_press_thread.cancel()
            self.long_press_thread = None
            
        if self.very_long_press_thread != None:
            self.very_long_press_thread.cancel()
            self.very_long_press_thread = None

    def create_notify_threads(self, channel):
        assert(self.long_press_thread==None)
        self.long_press_thread = threading.Timer(self.long_press_duration,self.on_long_press_notify,[channel])
        self.long_press_thread.start()

        assert(self.very_long_press_thread==None)
        self.very_long_press_thread = threading.Timer(self.very_long_press_duration,self.on_very_long_press_notify,[channel])
        self.very_long_press_thread.start()

    def  connect(self):
        GPIO.setup(self.buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(self.buttonPin, GPIO.BOTH, callback=self.on_switch_event, bouncetime=self.switch_bounce) 

    def on_switch_event(self,channel):
        if GPIO.input(self.buttonPin) == GPIO.LOW:
            #  button is pressed down
            self.cancel_notify_threads()
            self.switch_press_start = time.time()                        
            self.create_notify_threads(channel)
            self.button_events.on_button_down(channel)

        else:
            # button is release (up)
            elapsed =  time.time() - self.switch_press_start
            self.cancel_notify_threads()
            # notify that a long (or very long) press has finished
            if elapsed >= self.very_long_press_duration:
                self.button_events.on_very_long_press(channel) 
            elif elapsed >= self.long_press_duration:
                self.button_events.on_long_press(channel) 
            else:
                self.button_events.on_button_up(channel)

    # notifies that the long press duration has been reached
    def on_long_press_notify(self,channel):
        self.long_press_thread = None
        self.button_events.on_long_press_notify(channel)

    # notifies that the very long press duration has been reached
    def on_very_long_press_notify(self,channel):
        self.very_long_press_thread = None
        self.button_events.on_very_long_press_notify(channel)
