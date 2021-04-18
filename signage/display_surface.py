
import sys, os
COMPILE_PC = os.path.sep=="\\"

import time, json
import threading

from utils.events import *
from utils import *

from luma.core.render import canvas
from luma.core.legacy.font import proportional, tolerant, CP437_FONT, TINY_FONT
from luma.core.sprite_system import framerate_regulator

from signage.display_support import *
from signage.display_drawing import *
from signage.display_fonts import *
from signage.display_area import *
from signage.display_message import *

class display_surface_events(Events):
        __events__ = ("on_all_ready_to_consume")


# A display_surface is a collection of display_area associated with a single hardware device (like max7219)
# Each surface accepts messages destined for an individual display_area it contains, and it is the display_area's
# job to act upon the message depending how it is configured
# Note: you may have overlapping display_areas, and the last display_area defined can overwrite (the overlapped portion) of
# the area beneath it
class display_surface():
    def __init__(self,json_settings=None,id=None,fps=AreaUpdate_Default.SIGN_FPS,device=None,areas=[],muted=False):
        self.lock = threading.Lock()
        self.thread = None
        self.muted = muted
        self.id = id
        self.fps = fps
        self.device = device
        self.fonts = { SignFont.TINY: font_proportional(CUSTOM_TINY_FONT), SignFont.NORMAL : font_proportional(CP437_FONT), SignFont.LARGE : font_proportional(CP437_FONT) }
        self.current_font_id =  SignFont.TINY
        self.areas = {}
        self.set_areas(areas)
        self.draw_ops = draw_operations()
        self.__brightness_level = 128

        if json_settings is not None:
            self.create_from_settings(json_settings)
        self.stop_request = False
        self.events = display_surface_events()

    def log(self,message):
        if self.muted:
            return
        print("{0}: {1}".format(self.id,message))

    def set_brightness(self,new_value):
        self.__brightness_level = new_value
    
    def get_brightness(self,new_value):
        return self.__brightness_level

    def set_areas(self, areas):
        if areas is None:
            self.areas = {}
        else:
            for area in areas:
                self.areas[area.id] = area
    
    def has_area(self,area_id):
        return self.areas is not None and area_id in self.areas

    def create_from_settings(self,json_settings):
        if "name" in json_settings:
            self.id = json_settings["name"]
        if "fps" in json_settings:
            self.fps = json_settings["fps"]

        if "areas" in json_settings:
            self.create_areas_from_settings(json_settings["areas"])

    def create_areas_from_settings(self,json_areas):
        assert(json_areas)

        self.clear_all()
        new_areas = []
        for area_settings in json_areas:
            assert("id" in area_settings)
            area = display_area(id=area_settings["id"])
            if "enabled" in area_settings:
                area.enabled = bool(area_settings["enabled"])
            if "order" in area_settings:
                area.order = int(area_settings["order"])
            if "left" in area_settings:
                area.left =  int(area_settings["left"])
            if "top" in area_settings:
                area.top =  int(area_settings["top"])
            if "width" in area_settings:
                area.width = int(area_settings["width"])
            if "height" in area_settings:
                area.height =  int(area_settings["height"])
            if "font" in area_settings:
                area.font_id = SignFont[str(area_settings["font"]).upper()]

            if "halign" in area_settings:
                area.halign = AlignX[str(area_settings["halign"]).upper()]

            if "valign" in area_settings:
                area.valign = AlignY[str(area_settings["valign"]).upper()]

            if "scrollable" in area_settings:
                area.scrollable =  bool(area_settings["scrollable"])

            area.update_bounds()
            new_areas.append(area)

        self.set_areas(new_areas)
        for key in self.fonts.keys():
            self.fonts[key].id = key

    def __clear(self, area):
        assert(area is not None)
        area.clear_messages()

    def clear(self,area_id):
        if area_id in self.areas:
            area = self.areas[area_id]
            self.__clear(area)
        else:
            raise Exception("Area id={0} does not exist and cannot be cleared.".format(area_id))
    
    def clear_all(self):
        with self.lock:
            for area_id in self.areas.keys():
                self.clear(area_id)
    
    def queue_message(self,area_id,message,clear_existing=False):
        with self.lock:
            if self.has_area(area_id):
                area = self.areas[area_id]
                if clear_existing:
                    area.clear_messages()
                area.add_message(message)
                return True
            else:
                return False

    def get_font(self, id):
        default_font = None
        if len(self.fonts)>0:
            default_font = next(iter(self.fonts))
        if id == None:
            return default_font

        return self.fonts.get(id, default_font)

    def __request_stop(self,reason=None):
        with self.lock:
            if self.is_executing():
                if reason is not None:
                    self.log(reason)
                else:
                    self.log("Stop request received.")
                self.stop_request = True
            else:
                self.log("Stop request ignored. Already stopped.")

    def initialize(self):
        pass

    def start(self):
        if self.is_executing():
            self.log("Display is already executing. Ignoring start() command.")
            return False

        self.thread = threading.Thread(target=self.__execute_threaded)
        self.thread.daemon = True
        self.thread.start()
        return True

    def stop(self):
        self.__request_stop()

    def is_stopped(self):
        return self.thread == None
    
    def is_executing(self):
        return not self.is_stopped()

    def __execute_threaded(self):
        self.log("Started")
        regulator = framerate_regulator(self.fps)                
        frame = 0
        self.stop_request = False
        all_areas =  self.areas.values()
        while not self.stop_request:
            with regulator:
                try:
                    with canvas(self.device) as draw:
                        draw_context = custom_draw_context(device=self.device, display=self,area=None, draw=draw, fps=self.fps,frame=frame,draw_ops=self.draw_ops)
                        for area in all_areas:
                            draw_context.area = area
                            try:
                                area.draw_frame(draw_context)
                            except KeyboardInterrupt:
                                self.__request_stop("Execution stopped by user.")
                                break
                            except:
                                self.log("Error rendering area: {0}".format(area.id))
                                self.log_exception()
                                self.draw_error_area(area=area,context=draw_context)
                            finally:
                                pass
                except KeyboardInterrupt:
                    self.__request_stop("Execution stopped by user.")
                    break
                except:
                    # emulator will throw exception here about
                    # committing the canvas. So Ignore if using emulator
                    if not COMPILE_PC:
                        self.log_exception()

            frame += 1
            if frame >= self.fps:
                frame = 0
                self.log("FPS={0}".format(regulator.effective_FPS()))
                all_ready_to_consume = True
                now = time.time()
                for area in all_areas:
                    if not area.is_ready_to_consume(context=None,time_of_check=now):
                        all_ready_to_consume = False
                    else:
                        area.events.on_ready_to_consume(area)
                if all_ready_to_consume:
                    self.events.on_all_ready_to_consume(self)

        self.thread = None
        self.log("Stopped")

    def draw_error_area(self,area,context):
        self.draw_ops.draw_aligned(draw=context.draw,
                            text="!", 
                            xy=(area.left,area.top),
                            wh=(area.width,area.height),
                            fore="white",
                            font=self.get_font(SignFont.TINY),
                            invert=True)

    def log_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        self.log("Exception:\t{}, Line {}".format(filename, lineno))
        self.log( '          \t{}'.format(line.strip()))
        self.log( '          \t{}:{}'.format(type(exc_obj),exc_obj))
