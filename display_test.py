
import sys, os, copy, math, random, re
import time, json
from datetime import datetime

COMPILE_PC = os.path.sep=="\\"

from luma.core.render import canvas
from luma.core.legacy.font import proportional, tolerant, CP437_FONT, TINY_FONT
from luma.core.sprite_system import framerate_regulator

if COMPILE_PC:
    from luma.emulator.device import emulator        
    import pygame
else:    
    from luma.led_matrix.device import max7219
    from luma.core.interface.serial import spi, noop

from signage.display_fonts import *
from signage.display_message_custom import *
from signage.hardware_surfaces import *
from printer_sign import *

if __name__ == "__main__":
    def on_toggle_invert(context,message):
        message.invert = not message.invert
         
    def get_settings_filename():
        dir_path = os.path.dirname(os.path.realpath(__file__))
        if  COMPILE_PC:
            file_path ="D:{0}MISC{0}OctoSign{0}settings.json".format(os.path.sep)
            if os.path.exists(file_path):
                return file_path
            else:
                return "C:{0}Development{0}misc{0}OctoSign{0}settings.json".format(os.path.sep)
        else:
            return "settings.json"

    def build_test_messages(sign):
        #sign.queue_message("msg",character_diff_message(text="10:01",new_text="10:02"))
        #     sign.queue_message("temp1",character_diff_message(new_text="61\xb0"))
        # elif seconds == 2:
        #     sign.queue_message("msg",character_diff_message(text="10:02",new_text="10:03"))
        #     sign.queue_message("temp1",character_diff_message(text="62\xb0",new_text="63\xb0"))
        # elif seconds == 4:
        #     sign.queue_message("msg",character_diff_message(text="10:03",new_text="10:04"))
        #     sign.queue_message("temp1",character_diff_message(text="63\xb0",new_text="64\xb0"))
        # elif seconds == 6:
        #     sign.queue_message("msg",character_diff_message(text="10:04",new_text="11:25"))
        #     sign.queue_message("temp1",character_diff_message(text="64\xb0",new_text="65\xb0"))
        # elif seconds == 8:
        #     sign.queue_message("msg",character_diff_message(text="11:25",new_text="09:32"))
        #     sign.queue_message("temp1",character_diff_message(text="65\xb0",new_text="66\xb0"))

        sign.queue_message("msg",character_animation_message(text="wow!"))
        sign.queue_message("msg",character_animation_message(text="wow!",dissolve=True))

        sign.queue_message("msg",text_message(text="hello",retain=False))        
        sign.queue_message("msg",dissolve_text_message(text="hello",retain=True, dissolve=False))        
        sign.queue_message("msg",dissolve_text_message(text="hello",retain=True))   
        sign.queue_message("msg",character_diff_message(new_text="10:01",duration=3))     
        sign.queue_message("msg",character_diff_message(text="10:02",new_text="10:03",duration=3))     
        sign.queue_message("msg",character_diff_message(text="10:03",new_text="10:04",duration=3))    
        sign.queue_message("msg",character_diff_message(text="10:04",new_text="10:05",duration=3))    
        sign.queue_message("msg",wiggle_text_message(text="wiggle", pause=3))            
        sign.queue_message("msg",text_message(text="blink",retain=False,blink_options=message_blink_options(enabled=True, invert=False)))                    
        sign.queue_message("msg",text_message(text="invert",retain=False,blink_options=message_blink_options(enabled=True, invert=True)))                    
        sign.queue_message("msg",text_message(text="1234",invert=False,retain=True,scroll_options=message_scroll_options(enabled=True,direction=(0,1))))
        sign.queue_message("msg",text_message(text="x x", scroll_options=message_scroll_options(enabled=True,direction=(-1,0))))
        sign.queue_message("msg",text_message(text="abcdefghijklmnopqrstuvwxyz123", scroll_options=message_scroll_options(enabled=True,direction=(-1,0))))
        # # long scrolling messages stress out the cpu and limit FPS to around 15 max
        # #sign.queue_message("err",text_message(text="abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ", on_post_show=on_toggle_invert, scroll_options=message_scroll_options(enabled=True,direction=(-1,0))))
        sign.queue_message("msg",text_message(text="abcdefghijklmx x", blink_options=message_blink_options(enabled=True, invert=True), scroll_options=message_scroll_options(enabled=True,direction=(-1,0))))
        sign.queue_message("msg",builder_text_message(text="wow!"))
        sign.queue_message("msg",builder_text_message(text="wow!",explode=True, explode_pause=0))
        sign.queue_message("msg",rotating_text_message(text="done", blink_options=message_blink_options(enabled=True, invert=True), pause=3))

        pass

    try:    
        # load the display surface json definition    
        settings = {}
        settings_filename = get_settings_filename()
        with open(settings_filename) as file:
            settings = json.load(file)     
        print("Application settings loaded: {0}".format(settings_filename))            

        # setup the hardware surface for the sign, as described in the settings
        sign = None
        display_settings = settings["display"]
        surface_type = display_settings["type"] if "type" in display_settings and not COMPILE_PC else "emulator_surface"
        if not surface_type in globals():
            raise Exception("There is no surface class of the type: {0}".format(surface_type))
        sign_class = globals()[surface_type]
        sign = sign_class(json_settings=display_settings)

        # load some messages for testing the surface
        build_test_messages(sign)

        # run the display surface
        sign.start()

        sleep_duration = 1
        seconds = 0
        last_time = None
        while not sign.is_stopped():
            try:
                start = time.time()
                
                # show a real-time clock
                now = datetime.now()
                if COMPILE_PC:
                    new_time = now.strftime("%I:%M:%S")
                else:
                    new_time = now.strftime("%-I:%M:%S")
                # ampm = now.strftime("%p")
                # if ampm.startswith("A"):
                #     new_time += "\x83"
                # else:
                #     new_time += "\x82"
                new_msg = temperature_message(text=last_time,new_text=new_time,draw_glyph="none")
                sign.queue_message("err",new_msg)
                last_time = new_time


                # sleep for up to a second
                remaining = sleep_duration - (time.time() - start)
                if remaining > 0:
                    time.sleep(remaining)

                seconds += sleep_duration
                print("seconds: {0}".format(seconds))
            except KeyboardInterrupt:
                print("Requesting display surface {0} to stop...".format(sign.id))
                sign.stop()                
            except Exception as error:
                raise error

    except KeyboardInterrupt:
        print("Execution stopped by user.")
    except Exception as e:
        print(e)            
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)            
    finally:  
        print("Stopping background threads...")
        print("Background threads stopped.")
