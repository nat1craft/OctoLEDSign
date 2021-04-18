import sys, os, copy
import time, json
import queue

from utils.events import *
from utils import *

from signage.display_support import *
from signage.display_drawing import *

class AreaUpdate_Default(IntEnum):
    BLINK = 2       # blinks per second
    SCROLL_X = 25     # pixels per second
    SCROLL_Y = 10     # pixels per second
    SIGN_FPS = 25
    # aiming for
    #SCROLL_X = 25     # pixels per second
    #SCROLL_Y = 10     # pixels per second
    #SIGN_FPS = 25
    # Not as smooth....
    # SCROLL_X = 20     # pixels per second
    # SCROLL_Y = 10     # pixels per second
    # SIGN_FPS = 10

class display_area_events(Events):
        __events__ = ("on_custom_draw", "on_pre_show", "on_post_show","on_pre_draw", "on_post_draw",\
                        "on_ready_to_consume")

class message_display_info():
    def __init__(self,message=None, time_shown=None, frame=0):
        self.message = message
        self.first_shown = time_shown
        self.frame = frame
        self.blink_last = None
        self.blink_on = False
        self.scroll_offset = None
        self.is_scrolling = False

    def expired(self, context, time_of_check):
        if self.first_shown is None:
            return False
        elif self.message is None:
            return True
        return self.message.can_interrupt(context=context,time_of_check=time_of_check) and (time_of_check - self.first_shown) > self.message.duration   


# A display_area is a portion of a display_surface. message information is clipped to this area.
# Example: I just want to show the temperature in the lower-right corner of my surface. So define an area
#          called "temp" in the lower right corner of the display_surface. Send messages to temp.
# Note: you may have overlapping areas, and the last area defined can overwrite (the overlapped portion) of
# the area beneath it
# Note: it is mainly up to the message itself to tell the area it is "done displaying". Like an animated message
# lets the area know the animation is complete. Once finished, the area will move to the next message. If no next 
# message exists, it will keep displaying the current message UNLESS the message is marked as "retain=False"
class display_area():
    def __init__(self, order=0, id=None, enabled=True, device=None,
                    left=None, top=None, width=None,height=None,
                    font_id=SignFont.DEFAULT,
                    valign=AlignY.MIDDLE, halign=AlignX.CENTER,
                    scrollable=True,
                    on_custom_draw=None
                    ):

        self.device = device
        self.message_queue = queue.Queue()
        self.current_info = None
        self.draw_ops = draw_operations()

        self.order = order
        self.enabled = enabled
        self.id = id
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.update_bounds()

        self.font_id = font_id
        self.valign = valign
        self.halign = halign
        self.scrollable = scrollable

        self.events = display_area_events()
        self.events.on_custom_draw += on_custom_draw

    def update_bounds(self):
        if self.left is None:
            self.right = None
        elif self.width is None:
            self.right = self.left
        else:
            self.right = self.left + self.width - 1

        if self.top is None:
            self.bottom = None
        elif self.height is None:
            self.bottom = self.top
        else:
            self.bottom = self.top + self.height -1

    def bounds(self):
        return [(self.left,self.top),(self.right,self.bottom)]

    def is_ready_to_consume(self, context, time_of_check):
        return self.message_queue.qsize()==0 and \
                (self.current_info is None or self.current_info.expired(context=context,time_of_check=time_of_check))
        
    def add_message(self,message):
        self.message_queue.put(message)
 
    def clear_messages(self, include_current=True):
        while not self.message_queue.empty():
            self.message_queue.get()
        if include_current and self.current_info is not None:
            self.current_info.message.retain = False

    def draw_frame(self, context):
         
        # make a copy of the context for this area
        context = copy.copy(context)
        # ... so we can fill in some area-specific settings
        context.top = self.top
        context.left = self.left
        context.width = self.width
        context.height = self.height
        context.bounds = self.bounds()
        context.draw_ops = self.draw_ops
        context.font = context.display.get_font(self.font_id)
        context.halign = self.halign
        context.valign = self.valign

        time_now = time.time()

        message_to_show = None
        if self.current_info is not None:
            expired = self.current_info.expired(context=context,time_of_check=time_now)            
            if expired:
                if self.message_queue.empty() and self.current_info.message.retain:
                    message_to_show = self.current_info.message
                    if self.current_info.is_scrolling:            
                        self.current_info.scroll_offset = None
                else:
                    message_to_show = None                    
                self.current_info.message.events.on_post_show(context=context,message=self.current_info.message)
                self.events.on_post_show(context=context,message=self.current_info.message)
            else:
                message_to_show = self.current_info.message
                    
        if (message_to_show is None or self.current_info is None) and not self.message_queue.empty() :
            message_to_show = self.message_queue.get()
            if message_to_show is not None:
                self.current_info = message_display_info(message_to_show,time_now,context.frame)
                message_to_show.events.on_pre_show(context=context)
                self.events.on_pre_show(context=context)

        if self.current_info is not None:
            self.current_info.frame = context.frame

        if message_to_show is None:
            return    

        # handle blinking and store it in the context for the message to interpret
        context.blink_on = True
        if message_to_show.blink_options.enabled:
            blink_change = self.current_info.blink_last is None or (time_now - self.current_info.blink_last) >= (1 / message_to_show.blink_options.bps)

            if blink_change:
                self.current_info.blink_last = time_now
                self.current_info.blink_on = not self.current_info.blink_on

            context.blink_on  = self.current_info.blink_on
            if blink_change:
                 message_to_show.events.on_blink_change(context,self)

        # determine if scrolling and what offsets to use
        was_scrolling = self.current_info.scroll_offset
        self.current_info.is_scrolling = message_to_show.can_scroll()

        if self.current_info.is_scrolling:            
            scroll_dir = message_to_show.scroll_options.direction
            if self.current_info.scroll_offset is None:
                # initialize scrolling
                self.current_info.scroll_offset = (0,0)
            else:
                # update scrolling offset for this frame
                context.scroll_ppf =  (message_to_show.scroll_options.pps[0] / context.fps,message_to_show.scroll_options.pps[1] / context.fps)
                increment = (scroll_dir[0]*context.scroll_ppf[0], scroll_dir[1]*context.scroll_ppf[1])
                self.current_info.scroll_offset = (self.current_info.scroll_offset[0] + increment[0], self.current_info.scroll_offset[1] + increment[1])            
            
            if scroll_dir[0] < 0:
                context.halign = AlignX.LEFT
                context.left += (context.width -1)
            elif scroll_dir[0] > 0:
                context.halign = AlignX.RIGHT
                context.left -= (context.width-1)
            if scroll_dir[1] < 0:
                context.valign = AlignY.TOP
                context.top += (context.height-1)
            elif scroll_dir[1] > 0:
                context.valign = (AlignY.BOTTOM-1)
                context.top -= context.height                            
        else:
            self.current_info.scroll_offset = None

        context.scroll_offset = (0,0) if self.current_info.scroll_offset is None else self.current_info.scroll_offset       

        if context.scroll_offset is not None:
            context.left += round(context.scroll_offset[0])
            context.top += round(context.scroll_offset[1])
        context.is_scrolling =self.current_info.is_scrolling        

        # special case to flood background of the entire viewport for inverts
        if context.is_scrolling and (message_to_show.invert or (message_to_show.blink_options.enabled and message_to_show.blink_options.invert)):            
            if (not context.blink_on and message_to_show.blink_options.invert and not message_to_show.invert) or \
                (context.blink_on and message_to_show.invert) :
                context.draw_ops.draw_rect(draw=context.draw,bounds=self.bounds(), fill="white")

        self.events.on_pre_draw(context=context)
        self.draw_message_frame(context,message_to_show)        
        self.events.on_post_draw(context=context)


    def draw_message_frame(self, context, message):
        assert(message)
        message.events.on_pre_draw(context=context,message=message)
        message.draw_frame(context)
        message.events.on_custom_draw(context=context,message=message)
        message.events.on_post_draw(context=context,message=message)
