import sys, os, copy, math, random
import time, json
from datetime import datetime

COMPILE_PC = os.path.sep=="\\"

from luma.core.render import canvas
from luma.core.legacy.font import proportional, tolerant, CP437_FONT, TINY_FONT
from luma.core.sprite_system import framerate_regulator

if COMPILE_PC:
    from luma.emulator.device import emulator, pygame as emulator_pygame        
    import pygame
else:    
    from luma.led_matrix.device import max7219
    from luma.core.interface.serial import spi, noop

from signage.display_fonts import *
from signage.display_surface import *


class emulator_surface(display_surface):
    def __init__(self,json_settings=None,id=None,fps=AreaUpdate_Default.SIGN_FPS,areas=[],muted=True,\
                    width=64, height=8, rotate=3, mode="1", transform="none", scale=6,
                    json_section="emulator"):

        # setup the hardware device
        emulator_device = None
        w, h = width, height
        r=rotate
        m=mode
        t=transform
        s=scale

        if json_settings is not None and json_section in json_settings:
            display_settings = json_settings[json_section]
            if "width" in display_settings:
                w = int(display_settings["width"])
            if "height" in display_settings:
                h = int(display_settings["height"])
            if "rotate" in display_settings:
                r = int(display_settings["rotate"])
            if "mode" in display_settings:
                m = str(display_settings["mode"])
            if "transform" in display_settings:
                t = str(display_settings["transform"])
            if "scale" in display_settings:
                s = int(display_settings["scale"])
            
        emulator_device = emulator_pygame(width=500, height=500, rotate=0, mode=m,transform=t, scale=s)
        emulator_device.scale = 100
        emulator_device.display.set_caption("abc!")
        super().__init__(json_settings=json_settings,id=id,fps=fps,areas=areas,muted=muted,device=emulator_device) 
        

class max7219_surface(display_surface):
    def __init__(self,json_settings=None,id=None,fps=AreaUpdate_Default.SIGN_FPS,areas=[],muted=True,\
                    port=0,device=0,cascaded=4,block_orientation=-90,blocks_arranged_in_reverse_order=False,contrast=128,
                    json_section="max7219"):

        # setup the hardware device
        max7219_device = None
        p=port
        d=device
        c=cascaded
        bo=block_orientation
        bro=blocks_arranged_in_reverse_order
        b=contrast

        if json_settings is not None and json_section in json_settings:
            display_settings = json_settings[json_section]
            if "port" in display_settings:
                p = int(display_settings["port"])
            if "device" in display_settings:
                d = int(display_settings["device"])
            if "cascaded" in display_settings:
                c = int(display_settings["cascaded"])
            if "block_orientation" in display_settings:
                bo = int(display_settings["block_orientation"])
            if "blocks_arranged_in_reverse_order" in display_settings:
                bro = bool(display_settings["blocks_arranged_in_reverse_order"])
            if "contrast" in display_settings:
                b = int(display_settings["contrast"])

        serial = spi(port=p, device=d, gpio=noop())
        max7219_device = max7219(serial,cascaded=c,block_orientation=bo,blocks_arranged_in_reverse_order=bro)
        max7219_device.contrast(b)
        super().__init__(json_settings=json_settings,id=id,fps=fps,areas=areas,muted=muted,device=max7219_device) 

    def set_brightness(self,new_value):
        brightness = max(min(new_value,255),0)
        super().set_brightness(brightness)
        if self.device is not None:
            self.device.contrast(brightness)
    
