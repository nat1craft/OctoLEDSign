import sys, os, math, random
import time, json

from utils.events import *
from utils import *

from signage.display_support import *
from signage.display_drawing import *
from signage.display_fonts import *
from signage.display_area import *
from signage.display_message import *


class display_message_events(Events):
        __events__ = ("on_custom_draw","on_pre_show", "on_post_show","on_pre_draw", "on_post_draw","on_scroll_complete","on_blink_change")


class message_blink_options():
    def __init__(self,enabled=False,blinks_per_second=AreaUpdate_Default.BLINK,invert=False):
        self.enabled = enabled
        self.bps = blinks_per_second
        self.invert = invert

class message_scroll_options():
    def __init__(self,enabled=False,pixels_per_second=(AreaUpdate_Default.SCROLL_X,AreaUpdate_Default.SCROLL_Y) , scroll_type= SignScroll.AUTO, direction=(0,0)):
        self.enabled = enabled
        self.pps = pixels_per_second
        self.type = scroll_type
        self.direction = direction  # (0,0)=None, (-1,0)=Left, (0,-1) = Up, (1,1)=Diagonal right and down

class base_display_message():
    def __init__(self, 
                text = None,
                duration = 3,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None,
                on_post_show = None, 
                retain=True):

        self.text = text
        self.duration = duration
        self.invert = invert
        self.blink_options = blink_options if blink_options is not None else message_blink_options()
        self.scroll_options = scroll_options if scroll_options is not None else message_scroll_options()
        self.retain = retain

        self.events = display_message_events()
        self.events.on_pre_show += on_pre_show
        self.events.on_post_show += on_post_show
        
    def get_text(self):
        return self.text

    def custom_draw(self, context, message):
        self.events.on_custom_draw(context,message)

    def draw_frame(self,context):
        pass

    def can_interrupt(self,context,time_of_check = time.time()):
        return True

    def can_scroll(self):
        return self.scroll_options is not None and \
            self.scroll_options.enabled and \
            not self.scroll_options.direction == (0,0) and \
            (not self.scroll_options.pps[0] == 0.0 or not self.scroll_options.pps[0] == 0.0)

class text_message(base_display_message):
    def __init__(self, 
                text = None,
                duration = 3,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None,
                on_post_show = None, 
                retain=True,
                angle=None,
                origin=None):

        super().__init__(text=text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain)
        self.angle = angle
        self.origin = origin
        self.scroll_init = False
        self.scrolling_finished = True

    def can_interrupt(self,context,time_of_check = time.time()):
        return super().can_interrupt(context=context,time_of_check=time_of_check) and self.scrolling_finished

    def draw_frame(self,context):
        super().draw_frame(context)

        if context.is_scrolling and not self.scroll_init:
            self.scroll_init = True
            self.scrolling_finished = False

        text_to_show = self.get_text()
        result = None
        if text_to_show is not None:

            if context.blink_on:
                result = context.draw_ops.draw_aligned(
                                draw=context.draw, 
                                text=text_to_show, 
                                xy = (context.left,context.top),
                                wh = (context.width,context.height),
                                align_x=context.halign, align_y=context.valign,
                                font=context.font,
                                invert=self.invert,
                                clip_bounds=context.bounds,
                                angle=self.angle,
                                origin=self.origin,
                                trim= not context.is_scrolling)
            else:
                if self.blink_options.enabled:
                    if self.blink_options.invert:
                        result = context.draw_ops.draw_aligned(
                                        draw=context.draw, 
                                        text=text_to_show, 
                                        xy = (context.left,context.top),
                                        wh = (context.width,context.height),
                                        align_x=context.halign, align_y=context.valign,
                                        font=context.font,
                                        invert=not self.invert,
                                        clip_bounds=context.bounds,
                                        angle=self.angle,
                                        origin=self.origin,
                                        trim= not context.is_scrolling)

        if context.is_scrolling:
            was_finished = self.scrolling_finished
            self.scrolling_finished = result==None or result.text_shown is None or result.text_shown == ""
            if was_finished != self.scrolling_finished:
                self.events.on_scroll_complete(context=context,message=self)
        else:
            self.scrolling_finished = True

class rotating_text_message(text_message):
    def __init__(self, 
                text = None,
                duration = 3,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None,
                on_post_show=None,
                retain=True,
                rps=0.5,
                origin=None,
                pause=None):

        super().__init__(text=text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain,
                            angle=None, origin=origin)
        self.rps = rps
        self.pause_duration = pause
        self.pause_time = None

    def can_interrupt(self,context,time_of_check = time.time()):
        return self.pause_duration == 0.0 or (self.pause_time is not None)

    def draw_frame(self,context):

        now = time.time()
        if self.pause_time is not None:
            if now > self.pause_time:
                self.pause_time = None

        if self.pause_time is not None:
            super().draw_frame(context)
            return

        rotations_per_sec = self.rps
        angle_per_second = math.radians(360) * rotations_per_sec
        angle_per_frame = angle_per_second / context.fps
        if self.angle is None:
            self.angle = 0.0
        self.angle += angle_per_frame
        if self.angle > math.radians(360):
            if self.pause_duration is not None and not self.pause_duration == 0.0:
                self.pause_time = now + self.pause_duration
                self.angle = 0
            else:
                self.angle -= math.radians(360)

        super().draw_frame(context)

class wiggle_text_message(rotating_text_message):
    def __init__(self, 
                text = None,
                duration = 3,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None,
                on_post_show=None,
                retain=True,
                rps=6,
                wiggle_distance=math.radians(20),
                wiggle_count = 4,
                pause=None):

        super().__init__(text=text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain,
                            rps=rps, 
                            origin=None,
                            pause=pause)
        self.wiggle_distance = wiggle_distance
        self.wiggle_count = wiggle_count
        self.current_direction = 1.0
        self.num_bumps = 0

    def draw_frame(self,context):

        now = time.time()
        if self.pause_time is not None:
            if now > self.pause_time:
                self.pause_time = None
                self.num_bumps = 0

        if self.pause_time is not None:
            super().draw_frame(context)
            return

        rotations_per_sec = self.rps
        angle_per_second = (self.wiggle_distance * 2) * rotations_per_sec
        angle_per_frame = angle_per_second / context.fps
        if self.angle is None:
            self.angle = 0.0

        self.angle += self.current_direction * angle_per_frame

        if self.angle > self.wiggle_distance or self.angle < -1 * self.wiggle_distance:
            self.current_direction *= -1.0
            self.num_bumps += 1
            self.angle += 2*self.current_direction * angle_per_frame

        if self.num_bumps > 0 and self.num_bumps % self.wiggle_count == 0:
            if self.pause_duration is not None and not self.pause_duration == 0.0:
                self.pause_time = now + self.pause_duration
                self.angle = 0

        text_message.draw_frame(self,context)

class builder_side(IntEnum):
    LEFT = 1
    TOP = 2
    RIGHT = 3
    BOTTOM = 4

class builder_text_message(text_message):
    def __init__(self, 
                text = None,
                duration = 3,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None, 
                on_post_show=None,
                retain=True,
                angle=None,
                origin=None,
                build_duration=1,
                random_build_speed=True,
                allowed_sides = [builder_side.LEFT, builder_side.TOP,builder_side.RIGHT, builder_side.BOTTOM],
                random_xy = (True,True),
                explode=False,
                explode_pause=1):

        super().__init__(text=text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain,
                            angle=angle, origin=origin)
        self.build_duration = build_duration
        self.random_build_speed = random_build_speed
        self.point_buffer = None
        self.build_speed_variance = 0
        self.allowed_sides = allowed_sides
        self.random_xy = random_xy
        self.explode = explode
        self.explode_pause = explode_pause
        self.explode_pause_end = None
        self.animation_post_show = False

    def distance(self,xy1, xy2):
        return math.sqrt( (xy2[0]-xy1[0]) * (xy2[0]-xy1[0]) +  (xy2[1]-xy1[1]) *  (xy2[1]-xy1[1]))
    
    def get_start_pos(self, context, dest_point, side):
        rand_x = context.bounds[0][0] + random.uniform(0,1) * (context.bounds[1][0] - context.bounds[0][0]) if self.random_xy[0] else dest_point[0]
        rand_y = context.bounds[0][1] + random.uniform(0,1) * (context.bounds[1][1] - context.bounds[0][1]) if self.random_xy[1] else dest_point[1]
        if side == builder_side.TOP:
            return (rand_x,context.bounds[0][1]-1)
        elif side == builder_side.BOTTOM:
            return (rand_x,context.bounds[0][1] + context.bounds[1][1] +1 )
        elif side == builder_side.LEFT:
            return (context.bounds[0][0]-1, rand_y)
        else:
            return (context.bounds[0][0] + context.bounds[1][0] +1, rand_y)

    def can_interrupt(self, context,time_of_check = time.time()):
        is_paused = self.explode and self.explode_pause_end > time_of_check
        return is_paused or self.animation_post_show

    def draw_frame(self,context):
        now = time.time()
        
        if self.point_buffer is None:
            self.animation_post_show = False
            text_to_show = self.get_text()
            if text_to_show is not None:
                draw_result = context.draw_ops.draw_aligned(
                                draw=context.draw, 
                                text=text_to_show, 
                                xy = (context.left,context.top),
                                wh = (context.width,context.height),
                                align_x=context.halign, align_y=context.valign,
                                font=context.font,
                                invert=self.invert,
                                clip_bounds=context.bounds,
                                angle=self.angle,
                                origin=self.origin,
                                to_array=True)

                self.point_buffer = draw_result.points
                # initialize the points to be drawn
                for point_info in self.point_buffer:
                    point_info["finished"] = False
                    dest_point = point_info["point"]
                    start_point = self.get_start_pos(context,dest_point=dest_point, side=random.choice(self.allowed_sides))
                    if self.explode:
                        dest_point = start_point
                        start_point = point_info["point"]
                        point_info["point"] = dest_point
                    point_info["current"] = start_point
                    min_speed = ( (dest_point[0]-start_point[0]) / self.build_duration, (dest_point[1] - start_point[1]) / self.build_duration  )                        
                    speed_randomness = random.uniform(0,self.build_speed_variance)
                    rand_speed = ( min_speed[0] * (1 + speed_randomness), min_speed[1]* (1 + speed_randomness))

                    point_info["frame_velocity"] = (rand_speed[0] / context.fps, rand_speed[1] / context.fps) # gives pixels/frame

                    pause_offset = self.explode_pause if self.explode else 0
                    if not rand_speed[0] == 0:
                        point_info["end_time"] = now + pause_offset + (dest_point[0]-start_point[0]) / rand_speed[0]
                    elif not rand_speed[1] == 0:
                        point_info["end_time"] = now + pause_offset + (dest_point[1]-start_point[1]) / rand_speed[1]
                    else:
                        point_info["end_time"] = now + pause_offset

        if self.explode and self.explode_pause_end is None:
            self.explode_pause_end = now + self.explode_pause

        num_points_moving = 0
        for point_info in self.point_buffer:
            dest_point = point_info["point"]
            if point_info["finished"] == True:
                if not context.draw_ops.is_point_clipped(dest_point,clip_bounds=context.bounds):
                    context.draw.point(dest_point, fill=point_info["color"])
            else:
                num_points_moving += 1
                is_paused = self.explode and self.explode_pause_end > now                
                last_point = point_info["current"]
                if is_paused:
                    if not context.draw_ops.is_point_clipped(last_point,clip_bounds=context.bounds):
                        context.draw.point(last_point, fill=point_info["color"])
                else:
                    velocity = point_info["frame_velocity"]
                    new_point = (last_point[0] + velocity[0], last_point[1] + velocity[1])
                    if point_info["end_time"] <= now:
                        new_point = dest_point
                        point_info["finished"] = True
                    if not context.draw_ops.is_point_clipped(new_point,clip_bounds=context.bounds):
                        context.draw.point(new_point, fill=point_info["color"])
                    point_info["current"] = new_point

        self.animation_post_show = num_points_moving == 0

class dissolve_text_message(text_message):
    def __init__(self, 
                text = None,
                duration = 3,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None, 
                on_post_show=None,
                retain=True,
                angle=None,
                origin=None,
                build_duration=1,
                dissolve=True,
                dissolve_pause=0):

        super().__init__(text=text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain,
                            angle=angle, origin=origin)
        self.build_duration = build_duration
        self.point_buffer = None
        self.temp_buffer = None

        self.build_speed_variance = 0
        self.dissolve = dissolve
        self.dissolve_pause = dissolve_pause
        self.dissolve_pause_end = None
        self.animation_post_show = False

    def can_interrupt(self, context,time_of_check = time.time()):
        is_paused = self.dissolve and self.dissolve_pause_end > time_of_check
        return is_paused or self.animation_post_show

    def draw_frame(self,context):
        now = time.time()
        
        if self.point_buffer is None:
            self.animation_post_show = False
            text_to_show = self.get_text()
            if text_to_show is not None:
                draw_result = context.draw_ops.draw_aligned(
                                draw=context.draw, 
                                text=text_to_show, 
                                xy = (context.left,context.top),
                                wh = (context.width,context.height),
                                align_x=context.halign, align_y=context.valign,
                                font=context.font,
                                invert=self.invert,
                                clip_bounds=context.bounds,
                                angle=self.angle,
                                origin=self.origin,
                                to_array=True)

                self.point_buffer = draw_result.points
                # initialize the points to be drawn
                for point_info in self.point_buffer:
                    rand_speed = random.uniform(0,1) * self.build_duration
                    pause_offset = self.dissolve_pause if self.dissolve else 0
                    point_info["action_time"] = now + rand_speed + pause_offset
            
            if not self.dissolve:
                self.temp_buffer = self.point_buffer
                self.point_buffer = []

        if self.dissolve:
            if self.dissolve_pause_end is None:
                self.dissolve_pause_end = now + self.dissolve_pause

            to_remove = []
            for point_info in self.point_buffer: 
                if point_info["action_time"] > now:
                    context.draw.point(point_info["point"], fill=point_info["color"])
                else:
                    to_remove.append(point_info)        
            
            for point_info in to_remove:
                self.point_buffer.remove(point_info)
            self.animation_post_show = len(self.point_buffer)==0
        else:
            to_remove = []
            for point_info in self.temp_buffer: 
                if point_info["action_time"] <= now:
                    self.point_buffer.append(point_info)
                    to_remove.append(point_info)                           

            for point_info in to_remove:
                self.temp_buffer.remove(point_info)
            
            for point_info in self.point_buffer:                 
                context.draw.point(point_info["point"], fill=point_info["color"])

            self.animation_post_show = self.temp_buffer is None or len(self.temp_buffer)==0

class character_points:
    def __init__(self, character, string_pos=0, origin=None, color="white", points=None, destination=None, extents=None, size=None ):
        self.character = character
        self.string_pos = string_pos
        self.origin = origin        # left,top
        self.extents = extents      # right,bottom
        self.size = size            # width,height
        self.color=color
        self.points = [] if points is None else points
        
        self.destination = destination
        self.finished = False
        self.current_origin = None
        self.velocity = None
        self.end_time = None
    
    def __str__(self):
        return "{0} @ {1} => {2} points".format("None" if self.character is None else self.character, string_pos, len(self.points))

    def generate_relative_points(self):
        min_point = (None,None)
        max_point = (None,None)
        for point in self.points:
            min_point = ( point[0] if min_point[0] is None else min(point[0], min_point[0]), point[1] if min_point[1] is None else min(point[1], min_point[1])   )
            max_point = ( point[0] if max_point[0] is None else max(point[0], max_point[0]), point[1] if max_point[1] is None else max(point[1], max_point[1])   )

        self.origin = min_point
        self.extents = max_point
        self.size = (max_point[0]-min_point[0],max_point[1] - min_point[1])

        relative_points = []
        for point in self.points:
            relative_points.append((point[0] - self.origin[0], point[1] - self.origin[1]))
        self.points = relative_points

    def draw(self,context, origin=None,clip_bounds=None):    
        o = origin if origin is not None else self.origin    
        for relative_point in self.points:
            absolute_point = (o[0] + relative_point[0], o[1] + relative_point[1])
            if not context.draw_ops.is_point_clipped(absolute_point,clip_bounds=clip_bounds):
                context.draw.point(absolute_point, fill=self.color)        

class character_animation_message(text_message):
    def __init__(self, 
                text = None,
                duration = 3,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None, 
                on_post_show=None,
                retain=True,
                angle=None,
                origin=None,
                build_duration=1,
                dissolve=False,
                dissolve_pause=0,
                allowed_sides = [builder_side.LEFT, builder_side.TOP,builder_side.RIGHT, builder_side.BOTTOM],
                random_xy = (True,True)
                ):

        super().__init__(text=text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain,
                            angle=angle, origin=origin)
        self.build_duration = build_duration
        self.characters = None

        self.build_speed_variance = 0
        self.dissolve = dissolve
        self.dissolve_pause = dissolve_pause
        self.dissolve_pause_end = None
        self.animation_post_show = False
        self.allowed_sides = allowed_sides
        self.random_xy = random_xy

    def can_interrupt(self, context,time_of_check = time.time()):
        is_paused = self.dissolve and self.dissolve_pause_end > time_of_check
        return is_paused or self.animation_post_show

    def get_character_positions(self,point_buffer):
        buffer = {}
        if not point_buffer is None:
            # group all points by their position/letter
            for point in point_buffer:
                string_pos = int(point["position"])
                letter = str(point["char"])
                color = str(point["color"])
                xy = point["point"]

                if not string_pos in buffer:
                    character = character_points(character=letter,string_pos=string_pos,color=color)
                    buffer[string_pos] = character
                else:
                    character = buffer[string_pos]
                character.points.append(xy)

            # determine the bounds of each letter and make the collection
            # of points "offsets" from the "origin" of the letter instead
            # of absolute point values
            for character in buffer.values():
                character.generate_relative_points()
            
        return buffer

    def get_start_pos(self, context, character, side, dest_point):
        rand_x = context.bounds[0][0] + random.uniform(0,1) * (context.bounds[1][0] - context.bounds[0][0]) if self.random_xy[0] else dest_point[0]
        rand_y = context.bounds[0][1] + random.uniform(0,1) * (context.bounds[1][1] - context.bounds[0][1]) if self.random_xy[1] else dest_point[1]
        if side == builder_side.TOP:
            return (rand_x,context.bounds[0][1] - character.size[1] -1 )
        elif side == builder_side.BOTTOM:
            return (rand_x,context.bounds[0][1] + context.bounds[1][1] + character.size[1] + 1)
        elif side == builder_side.LEFT:
            return (context.bounds[0][0] - character.size[0] -1, rand_y)
        else:
            return (context.bounds[0][0] + context.bounds[1][0] + character.size[0]+1, rand_y)

    def draw_frame(self,context):
        now = time.time()
        
        if self.characters is None:
            self.animation_post_show = False
            text_to_show = self.get_text()
            if text_to_show is not None:
                draw_result = context.draw_ops.draw_aligned(
                                draw=context.draw, 
                                text=text_to_show, 
                                xy = (context.left,context.top),
                                wh = (context.width,context.height),
                                align_x=context.halign, align_y=context.valign,
                                font=context.font,
                                invert=self.invert,
                                clip_bounds=context.bounds,
                                angle=self.angle,
                                origin=self.origin,
                                to_array=True)

                self.characters = self.get_character_positions(draw_result.points)

                # initialize the points to be drawn
                for character in self.characters.values():
                    character.finished = False
                    dest_point = character.origin
                    start_point = self.get_start_pos(context,character=character, side=random.choice(self.allowed_sides), dest_point=dest_point)
                    if self.dissolve:
                        dest_point = start_point
                        start_point = character.origin
                        character.origin = dest_point
                    character.current_origin = start_point
                    min_speed = ( (dest_point[0]-start_point[0]) / self.build_duration, (dest_point[1] - start_point[1]) / self.build_duration  )                        
                    speed_randomness = random.uniform(0,self.build_speed_variance)
                    rand_speed = ( min_speed[0] * (1 + speed_randomness), min_speed[1]* (1 + speed_randomness))

                    character.velocity = (rand_speed[0] / context.fps, rand_speed[1] / context.fps) # gives pixels/frame

                    pause_offset = self.dissolve_pause if self.dissolve else 0
                    if not rand_speed[0] == 0:
                        character.end_time = now + pause_offset + (dest_point[0]-start_point[0]) / rand_speed[0]
                    elif not rand_speed[1] == 0:
                        character.end_time = now + pause_offset + (dest_point[1]-start_point[1]) / rand_speed[1]
                    else:
                        character.end_time = now + pause_offset
                    character.destination = dest_point

        if self.dissolve and self.dissolve_pause_end is None:
            self.dissolve_pause_end = now + self.dissolve_pause

        num_points_moving = 0
        for character in self.characters.values():
            dest_point = character.origin
            if character.finished:
                character.draw(context=context, origin=dest_point,clip_bounds=context.bounds)
            else:
                num_points_moving += 1
                is_paused = self.dissolve and self.dissolve_pause_end > now                
                last_point = character.current_origin
                if is_paused:
                    character.draw(context=context, origin=last_point,clip_bounds=context.bounds)
                else:
                    new_point = (last_point[0] + character.velocity[0], last_point[1] + character.velocity[1])
                    if character.end_time <= now:
                        new_point = dest_point
                        character.finished = True
                    character.draw(context=context, origin=new_point,clip_bounds=context.bounds)
                    character.current_origin = new_point

        self.animation_post_show = num_points_moving == 0

class character_diff_info:
    def __init__(self,position, new_char=None,old_char=None,start_time=None,end_time=None):
        self.position = position
        self.new_char = new_char
        self.old_char = old_char
        self.start_time = start_time
        self.end_time = end_time

    def are_different(self):
        if self.new_char is None:
            return False
        if self.old_char is None:
            return True
        if self.old_char.character != self.new_char.character or self.old_char.origin != self.new_char.origin \
            or self.old_char.extents != self.new_char.extents or self.old_char.color != self.new_char.color:
            return True      
        return False

class character_diff_message(character_animation_message):
    def __init__(self, 
                text = None,
                new_text = None,
                duration = .75,
                invert = False,
                blink_options = None,
                scroll_options = None,
                on_pre_show = None, 
                on_post_show=None,
                retain=True,
                angle=None,
                origin=None,
                random_offset=0,
                build_duration=.75,
                entrance_side=builder_side.BOTTOM,
                exit_side=builder_side.TOP
                ):

        super().__init__(text=text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain,
                            angle=angle, origin=origin,
                            random_xy=(False,False),
                            build_duration=build_duration
                            )
        self.new_text = new_text
        self.new_characters = None
        self.character_diffs = None
        self.random_offset = random_offset
        self.entrance_side = entrance_side
        self.exit_side = exit_side
        self.pending_text = None

    def get_new_text(self):
        return self.new_text

    def update(self,new_text):
        self.pending_text = new_text

    def calc_char_movement(self,context,character,side,move_to_side=True, time_of_check = None):

        if move_to_side:
            start_point = character.origin
            character.current_origin = character.origin
            dest_point = self.get_start_pos(context, character, side, start_point)
        else:
            start_point = self.get_start_pos(context, character, side, character.origin)
            character.current_origin = start_point
            dest_point = character.origin
        character.destination = (round(dest_point[0]),round(dest_point[1]))

        anim_duration = self.build_duration
        min_speed = ( (dest_point[0]-start_point[0]) / anim_duration, (dest_point[1] - start_point[1]) / anim_duration  )                        
        speed_randomness = random.uniform(0,self.random_offset)
        rand_speed = ( min_speed[0] * (1 + speed_randomness), min_speed[1]* (1 + speed_randomness))
        character.velocity = (rand_speed[0] / context.fps, rand_speed[1] / context.fps) # gives pixels/frame

        now = time_of_check if time_of_check is not None else time.time()
        if not rand_speed[0] == 0:
            character.end_time = now + (dest_point[0]-start_point[0]) / rand_speed[0]
        elif not rand_speed[1] == 0:
            character.end_time = now + (dest_point[1]-start_point[1]) / rand_speed[1]
        else:
            character.end_time = now 
          
    def update_char_movement(self,context, character, move_to_side=True, time_of_check = None):
        now = time_of_check if time_of_check is not None else time.time()

        if character.finished:
            if not move_to_side:
                character.draw(context=context, origin=character.origin,clip_bounds=context.bounds)
        else:
            last_point = character.current_origin
            new_point = (last_point[0] + character.velocity[0], last_point[1] + character.velocity[1])
            rounded = (round(new_point[0]),round(new_point[1]))
            if character.end_time <= now or rounded == character.destination:
                character.finished = True
            character.draw(context=context, origin=new_point,clip_bounds=context.bounds)
            character.current_origin = new_point
        return not character.finished

    def draw_frame(self,context):
        now = time.time()
                
        if self.characters is None and self.new_characters is None:
            self.animation_post_show = False

            text_to_show = self.get_text()
            if text_to_show is not None:
                draw_result = context.draw_ops.draw_aligned(
                                draw=context.draw, 
                                text=text_to_show, 
                                xy = (context.left,context.top),
                                wh = (context.width,context.height),
                                align_x=context.halign, align_y=context.valign,
                                font=context.font,
                                invert=self.invert,
                                clip_bounds=context.bounds,
                                angle=self.angle,
                                origin=self.origin,
                                to_array=True)

                self.characters = self.get_character_positions(draw_result.points)

            new_text_to_show = self.get_new_text()
            if new_text_to_show is not None:
                draw_result = context.draw_ops.draw_aligned(
                                draw=context.draw, 
                                text=new_text_to_show, 
                                xy = (context.left,context.top),
                                wh = (context.width,context.height),
                                align_x=context.halign, align_y=context.valign,
                                font=context.font,
                                invert=self.invert,
                                clip_bounds=context.bounds,
                                angle=self.angle,
                                origin=self.origin,
                                to_array=True)

                self.new_characters = self.get_character_positions(draw_result.points)

            self.character_diffs = {}
            num_chars = max(0 if self.characters is None else len(self.characters),0 if self.new_characters is None else len(self.new_characters))
            for i in range(num_chars):
                old_char = self.characters[i] if self.characters is not None and i in self.characters else None
                new_char = self.new_characters[i] if self.new_characters is not None and i in self.new_characters else None                
                info = character_diff_info(position=i,new_char=new_char, old_char=old_char)
                self.character_diffs[i] = info
                if info.are_different():
                    if info.old_char is not None:
                        self.calc_char_movement(context=context,character=info.old_char,side=self.exit_side,move_to_side=True,time_of_check=now)
                    if info.new_char is not None:
                        self.calc_char_movement(context=context,character=info.new_char,side=self.entrance_side,move_to_side=False,time_of_check=now)

        num_chars_moving = 0
        for diff in self.character_diffs.values():
            if not diff.are_different() or diff.new_char is None:
                if diff.old_char is not None:
                    diff.old_char.draw(context=context, origin=diff.old_char.origin,clip_bounds=context.bounds)
            else:
                if diff.old_char is not None and self.update_char_movement(context=context,character=diff.old_char,move_to_side=True,time_of_check=now):
                    num_chars_moving += 1
                if self.update_char_movement(context=context,character=diff.new_char,move_to_side=False,time_of_check=now):
                    num_chars_moving += 1

        self.animation_post_show = num_chars_moving == 0

        if self.animation_post_show and self.pending_text is not None:
            self.new_text = self.pending_text
            self.pending_text = None
            self.characters = None

