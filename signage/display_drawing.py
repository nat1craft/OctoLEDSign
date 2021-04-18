import sys, os, math
import time, json

from utils.events import *
from utils import *

COMPILE_PC = os.path.sep=="\\"

from signage.display_support import *

class custom_draw_context:
    def __init__(self,device = None, display=None,area=None,draw=None,frame=0,fps=None,blink_on=False,draw_ops=None,
                    top=None, left=None, width=None, height=None, bounds=None, font=None):
        self.device = device
        self.display = display
        self.area = area
        self.draw = draw
        self.frame = frame
        self.fps = fps
        self.blink_on = blink_on
        self.draw_ops = draw_ops
        self.top = top
        self.left = left
        self.width = width
        self.height = height
        self.bounds = bounds
        self.font = None
        self.scroll_offset = (0,0)
        self.is_scrolling = False
        self.scroll_ppf = None
        self.halign = AlignX.CENTER
        self.valign = AlignY.MIDDLE

class DrawingResult:
    def __init__(self,points=None,text=None,start_index=None,end_index=None,start_x=None,start_y=None,end_x=None,end_y=None):
        self.points = points
        self.text_shown = text
        self.start_index = start_index
        self.end_index = end_index
        self.start_x = start_x
        self.end_x = end_x
        self.start_y = start_y
        self.end_y = end_y

class draw_operations:
    def __init__(self):
        pass

    def clip_rect(self,rect,clip_bounds=None):
        clipped = rect
        if clip_bounds is not None:
            x_start = min(rect[0],rect[2])
            x_end = max(rect[0],rect[2])
            y_start = min(rect[1],rect[3])
            y_end = max(rect[1],rect[3])

            clip_x_start = min(clip_bounds[0][0],clip_bounds[1][0])
            clip_x_end = max(clip_bounds[0][0],clip_bounds[1][0])
            clip_y_start = min(clip_bounds[0][1],clip_bounds[1][1])
            clip_y_end = max(clip_bounds[0][1],clip_bounds[1][1])

            if x_start > clip_x_end or  x_end < clip_x_start or y_start > clip_y_end or  y_end < clip_y_start:
                return None

            clipped = [(max(x_start,clip_x_start), max(y_start,clip_y_start)),(min(x_end,clip_x_end), min(y_end,clip_y_end))]

        return clipped

    def is_point_clipped(self,xy,clip_bounds=None):
        return self.get_clip_directions(xy,clip_bounds) != None

    def get_clip_directions(self,xy,clip_bounds=None):
        clipped_by = []

        if clip_bounds is None:
            return None

        clipped_x_low = xy[0] < clip_bounds[0][0]
        clipped_x_high = round(xy[0]) > clip_bounds[1][0]        
        clipped_x = clipped_x_low or clipped_x_high
        if clipped_x_low:
            clipped_by.append(ClipDirection.X_LOW)
        if clipped_x_high:
            clipped_by.append(ClipDirection.X_HIGH)
        if clipped_x:
            clipped_by.append(ClipDirection.X)

        clipped_y_low = xy[1] < clip_bounds[0][1]
        clipped_y_high = round(xy[1]) > clip_bounds[1][1]
        clipped_y =  clipped_y_low or clipped_y_high
        if clipped_y_low:
            clipped_by.append(ClipDirection.Y_LOW)
        if clipped_y_high:
            clipped_by.append(ClipDirection.Y_HIGH)
        if clipped_y:
            clipped_by.append(ClipDirection.Y)

        return None if len(clipped_by) == 0 else clipped_by

    def calc_size(self, txt, font=None, trim=True):
        """
        Calculates the bounding box of the text, as drawn in the specified font.
        This method is most useful for when the
        :py:class:`~luma.core.legacy.font.proportional` wrapper is used.
        :param txt: The text string to calculate the bounds for
        :type txt: str
        :param font: The font (from :py:mod:`luma.core.legacy.font`) to use.
        """
        src = [c for ascii_code in txt for c in font[ord(ascii_code)]]
        
        max_height = 0
        for ch in txt:
            char_height = 0
            for byte in font[ord(ch)]:
                col_height = 0
                for j in range(8):
                    # column height is determined by trimming top and bottom
                    if byte & 0x01 > 0  or (col_height > 0 and byte != 0):
                        col_height += 1
                    byte >>= 1
                # the maximum column height is the height of the character
                char_height = max(col_height,char_height)  
            # determine the maximum height from all characters  
            max_height = max(char_height,max_height)

        # remove any spacing on the last character's left side
        total_width = len(src)

        if trim:
            pos = 0
            while pos < len(src) and src[pos]==0:
                total_width -=1
                pos -= 1

            # remove any spacing on the last character's right side
            pos = len(src)-1
            while pos>=0 and src[pos]==0:
                total_width -=1
                pos -= 1

        return (total_width, max_height)

    def draw_rect(self, draw, bounds, outline=None, fill=None, clip_bounds=None, width=1):
        clipped = self.clip_rect(bounds,clip_bounds)
        if clipped is None:
            return

        draw.rectangle(clipped, outline=outline, fill=fill, width=width)

    def rotate_point(self, point, angle, originXY = (0,0)):
        if angle is None or angle == 0.0:
            return point

        pointXY = [point[0],point[1]]
        s = math.sin(angle)
        c = math.cos(angle)

        # translate point back to origin:
        pointXY[0] -= originXY[0]
        pointXY[1] -= originXY[1]

        # rotate point
        xnew = pointXY[0] * c -  pointXY[1] * s
        ynew = pointXY[0] * s +  pointXY[1] * c

        # translate point back:
        pointXY[0] = xnew + originXY[0]
        pointXY[1] = ynew + originXY[1]

        return  (int(pointXY[0]),int(pointXY[1]))
        
    def draw(self, draw, xy, text, fore="white", font=None, clip_bounds=None, angle=None, origin=None,to_array=False):
        """
        Draw a legacy font starting at :py:attr:`x`, :py:attr:`y` using the
        prescribed fill and font.
        :param draw: A valid canvas to draw the text onto.
        :type draw: PIL.ImageDraw
        :param txt: The text string to display (must be ASCII only).
        :type txt: str
        :param xy: An ``(x, y)`` tuple denoting the top-left corner to draw the
            text.
        :type xy: tuple
        :param fill: The fill color to use (standard Pillow color name or RGB
            tuple).
        :param font: The font (from :py:mod:`luma.core.legacy.font`) to use.
        """        
        result = DrawingResult(points=[] if to_array else None,start_x=xy[0],start_y=xy[1],text=None,start_index=0,end_index=None if text is None else len(text)-1)

        x, y = xy
        position = 0
        stop_x = False
        stop_y = False
        is_rotated = angle is not None and not angle==0.0

        # attempt to optimize by determining which characters will be displayed
        # given the clipping_bounds
        if is_rotated or clip_bounds is None:
            text_to_show = text
            result.start_index = 0
            result.end_index = len(text_to_show) -1            
        else:
            clip_x_start = min(clip_bounds[0][0],clip_bounds[1][0])
            clip_x_end = max(clip_bounds[0][0],clip_bounds[1][0])
            clip_y_start = min(clip_bounds[0][1],clip_bounds[1][1])
            clip_y_end = max(clip_bounds[0][1],clip_bounds[1][1])

            if x > clip_x_end or y > clip_y_end:
                return  result          
            
            clipped_x_dist = clip_x_start - x

            # characters can vary in width :( so ... figure it out one-by-one
            starting_char = 0
            starting_char_x = x  
            ending_char_x = x
            text_len = len(text)
            ending_char = text_len

            if clipped_x_dist >= 0:
                done = False
                while not done:
                    char_width = len(font[ord(text[starting_char])])
                    if starting_char_x + char_width > clip_x_start or starting_char ==text_len:
                        done = True
                    else:
                        starting_char_x += char_width
                        starting_char += 1
                        if starting_char == text_len:
                            done = True
                
                if starting_char == text_len:
                    return result

            avail_x_width = (clip_x_end - clip_x_start)
            ending_char = starting_char
            ending_char_x = starting_char_x

            done = False
            while not done:
                char_width = len(font[ord(text[ending_char])])
                if ending_char_x + char_width > clip_x_end or ending_char == text_len:
                    done = True
                else:
                    ending_char += 1
                    if ending_char == text_len:
                        done = True
                ending_char_x += char_width
            ending_char = min(ending_char,text_len)

            if starting_char >= text_len:
                return result

            text_to_show = text[starting_char:ending_char+1]
            x = starting_char_x

            result.start_index = starting_char
            result.end_index = ending_char
            result.start_x = starting_char_x
            result.end_x = ending_char_x

        result.text_shown = ""
        result.start_y = None
        result.end_y = None

        for ch in text_to_show:
            num_cols_drawn = 0
            for byte in font[ord(ch)]:
                for j in range(8):
                    if byte & 0x01 > 0:
                        point = self.rotate_point((x,  y + j),angle,origin)          
                        clipping = self.get_clip_directions(point,clip_bounds)             
                        if clipping == None:
                            if to_array:
                                result.points.append({"point": point, "color": fore, "char": ch, "position": position})
                            else:
                                draw.point(point, fill=fore)
                            result.start_y = min(result.start_y, point[1]) if result.start_y is not None else point[1]
                            result.end_y = max(result.start_y, point[1]) if result.end_y is not None else point[1]
                        elif not is_rotated:                            
                            # optimization for speed on non-rotated text
                            if ClipDirection.Y_HIGH in clipping:
                                stop_y = True
                            if ClipDirection.X_HIGH in clipping:
                                stop_x = True                                

                    byte >>= 1
                    if stop_y:
                        break
                stop_y = False
                if stop_x:
                    break
                result.end_x = x   
                if num_cols_drawn==0:
                    result.start_x = x             
                num_cols_drawn += 1
                x += 1
            if num_cols_drawn > 0:
                result.text_shown += ch
            if stop_x:
                break
            position += 1

        return result


    def draw_aligned(self, draw, text, 
                        xy, wh,
                        align_x=AlignX.CENTER, align_y = AlignY.MIDDLE, 
                        fore="white", 
                        back=None,                        
                        font=None, 
                        invert=False,
                        clip_bounds=None,
                        angle=None, origin=None,
                        to_array=False,
                        trim=True):

        bounds = [xy[0],xy[1],xy[0]+wh[0]-1,xy[1]+wh[1]-1]
        x_pos, y_pos, width, height = self.calc_aligned_bounding_box(text=text,xy=xy, wh=wh,align_x=align_x,align_y=align_y,font=font,trim=trim)

        if angle is not None and not angle == 0 and origin is None:
            o = [0,0]
            if align_x == AlignX.CENTER:
                o[0] = x_pos  + width / 2.0
            elif align_x == AlignX.LEFT:
                o[0] = x_pos
            else:
                o[0] = x_pos +  width -1
            if align_y == AlignY.MIDDLE:
                o[1] = y_pos  + height / 2.0
            elif align_y == AlignY.TOP:
                o[1] = y_pos
            else:
                o[1] = y_pos +  height -1
            origin = (o[0],o[1])

        point_array = None
        if invert:
            self.draw_rect(draw=draw,bounds=bounds, outline=fore, fill=fore, clip_bounds=clip_bounds)
            point_array = self.draw(draw, (x_pos,y_pos), text, font=font, fore=back if back is not None else "black",clip_bounds=clip_bounds,angle=angle, origin=origin,to_array=to_array)
        else:
            if back is not None:
                self.draw_rect(draw=draw,bounds=bounds, outline=back, fill=back, clip_bounds=clip_bounds)
            point_array = self.draw(draw, (x_pos,y_pos), text, font=font, fore=fore, clip_bounds=clip_bounds,angle=angle, origin=origin,to_array=to_array)
        return point_array

    def calc_aligned_bounding_box(self, text, 
                            xy, wh,
                            align_x=AlignX.CENTER, align_y = AlignY.MIDDLE,
                            font=None,
                            trim=True):

        if font == None:
            print("Unknown font id={0} specified.".format(font_id))
            return left,top,0,0

        left = xy[0]
        top = xy[1]
        width = wh[0]
        height = wh[1]
        right = left + width -1
        bottom = top + height -1

        # a hack because tiny font has 2 vertical padding lines (it is 5 high)
        # unlike NORMAL (which is 7 high)
        # really should determine exact offsets for drawing (like we do in textsize)
        # if font.id == SignFont.TINY:
        #      bottom -= 1

        if xy[0]<=0:
            s =0
            pass

        text_w, text_h = self.calc_size(text, font,trim=trim)

        x_pos = left
        if align_x == AlignX.RIGHT:
            x_pos = right - text_w 
        elif align_x == AlignX.CENTER:
            x_pos = left + (width - text_w) / 2
        
        y_pos = top
        if align_y == AlignY.BOTTOM:
            y_pos = bottom - text_h            
        elif align_y == AlignY.MIDDLE:
            y_pos = top + (height - text_h) / 2

        return math.floor(x_pos), math.floor(y_pos), text_w, text_h
