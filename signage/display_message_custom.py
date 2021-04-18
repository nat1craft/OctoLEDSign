import re
from signage.display_message import *

def custom_draw_extruder(context,message,ext_width=3, ext_height=1):
    msg_full_text = message.get_new_text()
    if msg_full_text is None:
        return

    msgs = re.split("[\xb0\xb1\xb2]",msg_full_text)
    msg_left = msgs[0]

    x_pos, y_pos, text_w_o, text_h_o  = context.draw_ops.calc_aligned_bounding_box(\
            text=msg_full_text, \
            xy=(context.left,context.top),wh=(context.width,context.height), \
            align_x=context.halign, align_y=context.valign, \
            font=context.font)

    x_pos_2, y_pos_2, text_w, text_h  = context.draw_ops.calc_aligned_bounding_box(\
            text=msg_left, \
            xy=(context.left,context.top),wh=(context.width,context.height), \
            align_x=context.halign, align_y=context.valign, \
            font=context.font)

    start_x = x_pos + (text_w -ext_width ) / 2
    start_y = context.top

    shape = [(start_x, start_y), (start_x + ext_width, start_y), (start_x + ext_width/2, start_y+ext_height),(start_x, start_y)]
    context.draw.line(shape,fill="white")

def custom_draw_bed(context,message, bed_width=5, bed_height=1, wing_percent=0.2):
    msg_full_text = message.get_new_text()
    if msg_full_text is None:
        return

    msgs = re.split("[\xb0\xb1\xb2]",msg_full_text)
    msg_partial = msgs[0]

    x_pos, y_pos, text_w_o, text_h_o  = context.draw_ops.calc_aligned_bounding_box(\
            text=msg_full_text, \
            xy=(context.left,context.top),wh=(context.width,context.height), \
            align_x=context.halign, align_y=context.valign, \
            font=context.font)

    x_pos_2, y_pos_2, text_w, text_h  = context.draw_ops.calc_aligned_bounding_box(\
            text=msg_partial, \
            xy=(context.left,context.top),wh=(context.width,context.height), \
            align_x=context.halign, align_y=context.valign, \
            font=context.font)

    start_x = x_pos + (text_w -bed_width ) / 2
    start_y = context.top

    wing_x = wing_percent * bed_width
    
    shape = [(start_x, start_y), (start_x+wing_x, start_y + bed_height),(start_x + bed_width - 2*wing_x + 1, start_y + bed_height), (start_x + bed_width, start_y)]
    #shape = [(start_x, start_y), (start_x+bed_width -1, start_y)]
    context.draw.line(shape,fill="white")


class temperature_message(character_diff_message):
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
                build_duration=.5,
                entrance_side=builder_side.BOTTOM,
                exit_side=builder_side.TOP,
                draw_glyph=None):

        super().__init__(text=text, new_text=new_text,duration=duration,invert=invert,
                            blink_options=blink_options,scroll_options=scroll_options,
                            on_pre_show=on_pre_show,on_post_show=on_post_show,
                            retain=retain,
                            angle=angle, origin=origin,
                            build_duration=build_duration,
                            entrance_side=entrance_side,
                            exit_side=exit_side
                            )
        self.draw_glyph = draw_glyph

        if not self.draw_glyph is None:
            if self.draw_glyph.upper() == "EXTRUDER":
                self.events.on_custom_draw += custom_draw_extruder
            elif self.draw_glyph.upper() == "BED":
                self.events.on_custom_draw += custom_draw_bed