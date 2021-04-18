import time, copy
from datetime import datetime
import threading
import sys, os

COMPILE_PC = os.path.sep=="\\"
USE_LEGACY_DHT = True

from utils.utils import *
from utils.base_threaded_loop import *

class HardwareSensor(MonitoredStateLoop):
    def __init__(self, settings, on_state_changed=None):
        super().__init__(settings,on_state_changed)
        self.sensor = None
        
