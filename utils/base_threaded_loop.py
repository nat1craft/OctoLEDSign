import sys, time, copy
from enum import IntEnum
import threading, queue
from threading import Thread

from utils.utils import *
from utils.events import *

class ThreadRequestCode(IntEnum):
    NOTHING = 0
    STOP = 1

class ThreadLogSeverity(IntEnum):
    NONE = 0
    INFO = 10
    SUCCESS = 20
    WARNING = 30
    ERROR = 40

class BaseQueuedItem():
    def __init__(self):
        pass

class BaseThreadedLoop(Thread):
    def __init__(self, settings, name = "Worker", interval=2, log_prefix=None, global_settings=None):
        super().__init__()
        self.lock = threading.Lock()
        self.request = ThreadRequestCode.NOTHING
        self.update_interval = interval
        self.name = name
        self.log_prefix = log_prefix
        self.queue = queue.Queue()
        self.global_settings = global_settings
        self.update_settings(settings)
        self.daemon = True

    def update_settings(self, new_settings):
        with self.lock:
            self.settings = new_settings
            if self.settings != None:
                if "update_interval" in self.settings:
                    self.update_interval =  int(self.settings["update_interval"])
                if "name" in self.settings:
                    self.name = self.settings["name"]

    def clear_items(self):
        with self.lock:
            while not self.queue.empty():
                self.queue.get()

    def add_item(self, item):
        with self.lock:
            self.queue.put(item)
        self.on_item_added(item)

    def on_item_added(self,new_item):
        pass

    def request_stop(self):
        with self.lock:
            self.request = ThreadRequestCode.STOP

    def log(self, message, severity = ThreadLogSeverity.NONE):
        prefix = self.log_prefix
        if prefix is None:
            prefix = "{0}:\t".format(self.name)
        print("{0}{1}".format(prefix, message))

    def on_interval_update(self):
        # override to internally update messages/buffers/etc.
        pass

    def on_startup(self):
        pass

    def on_shutdown(self):
        # override to cleanup, stop internal threads, or close connections
        pass

    def run(self):
        self.on_startup()
        self.log("Started")
        while True:
            start_time = time.time()
            if self.request == ThreadRequestCode.STOP:
                self.request = ThreadRequestCode.NOTHING
                self.on_shutdown()
                self.log("Stopping.")    
                break

            self.on_interval_update()

            elapsed_time = (time.time() - start_time) 
            if elapsed_time > self.update_interval:
                #self.log("Update interval is too fast. Taking longer to process than the polling interval.")
                pass
            else:
                time.sleep(self.update_interval-elapsed_time)            

class MonitoredStateEvents(Events):
        __events__ = ("on_state_changed")

class MonitoredStateLoop(BaseThreadedLoop):
    def __init__(self, settings, on_state_changed=None):
        super().__init__(settings)
        self.state = None
        self.events = MonitoredStateEvents()
        self.events.on_state_changed += on_state_changed
        
    def get_current_state(self):
        if self.state is None:
            return None
        return copy.copy(self.state)

    def force_state_change(self):
        self.events.on_state_changed(self.get_current_state(),self)

