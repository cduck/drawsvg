from .. import elements as draw


def draw_scrub(config: 'SyncedAnimationConfig', hidden=False) -> 'Group':
    hpad = config.bar_hpad
    bar_x = config.controls_x + hpad
    bar_y = config.controls_center_y
    bar_width = config.controls_width - 2*hpad
    knob_rad = config.knob_rad
    pause_width = config.pause_width
    pause_corner_rad = config.pause_corner_rad
    g = draw.Group(id='scrub', visibility='hidden' if hidden else None)
    g.append(draw.Line(
            bar_x, bar_y, bar_x+bar_width, bar_y,
            stroke=config.bar_color,
            stroke_width=config.bar_thickness,
            stroke_linecap='round'))
    progress = draw.Rectangle(
            bar_x, bar_y, 0, 0.001,
            stroke=config.bar_past_color,
            stroke_width=config.bar_thickness,
            stroke_linejoin='round')
    g.append(progress)
    g_capture = draw.Group(
            id='scrub-capture',
            data_xmin=bar_x,
            data_xmax=bar_x+bar_width,
            data_totaldur=config.total_duration,
            data_startdelay=config.start_delay,
            data_enddelay=config.end_delay,
            data_pauseonload=int(bool(config.pause_on_load)))
    g_capture.append(draw.Rectangle(
            bar_x-config.bar_thickness/2, bar_y-config.controls_height/2,
            bar_width+config.bar_thickness, config.controls_height,
            fill='rgba(255,255,255,0)'))
    knob = draw.Circle(
            bar_x, bar_y, knob_rad, fill=config.knob_fill,
            id='scrub-knob',
            visibility='hidden')
    g_capture.append(knob)
    g.append(g_capture)
    g_play = draw.Group(id='scrub-play', visibility='hidden')
    g_play.append(draw.Rectangle(
            bar_x - hpad/2 - knob_rad/2 - pause_width/2 + pause_corner_rad,
            bar_y - pause_width/2 + pause_corner_rad,
            pause_width - pause_corner_rad*2,
            pause_width - pause_corner_rad*2,
            fill=config.pause_color,
            stroke=config.pause_color,
            stroke_width=pause_corner_rad*2,
            stroke_linejoin='round'))
    g_play.append(draw.Path(fill=config.pause_icon_color)
            .M(bar_x - hpad/2 - knob_rad/2 - pause_width/4,
               bar_y - pause_width/4)
            .v(pause_width/2)
            .l(pause_width/4*2, -pause_width/4)
            .Z())
    g.append(g_play)
    g_pause = draw.Group(id='scrub-pause', visibility='hidden')
    g_pause.append(draw.Rectangle(
            bar_x - hpad/2 - knob_rad/2 - pause_width/2 + pause_corner_rad,
            bar_y - pause_width/2 + pause_corner_rad,
            pause_width - pause_corner_rad*2,
            pause_width - pause_corner_rad*2,
            fill=config.pause_color,
            stroke=config.pause_color,
            stroke_width=pause_corner_rad*2,
            stroke_linejoin='round'))
    g_pause.append(draw.Rectangle(
            bar_x - hpad/2 - knob_rad/2 - pause_width/16*3,
            bar_y - pause_width/4,
            pause_width/8,
            pause_width/2,
            fill=config.pause_icon_color))
    g_pause.append(draw.Rectangle(
            bar_x - hpad/2 - knob_rad/2 + pause_width/16,
            bar_y - pause_width/4,
            pause_width/8,
            pause_width/2,
            fill=config.pause_icon_color))
    g.append(g_pause)

    progress.add_key_frame(0, width=0)
    progress.add_key_frame(config.duration, width=bar_width)
    knob.add_key_frame(0, cx=bar_x)
    knob.add_key_frame(config.duration, cx=bar_x+bar_width)
    return g
