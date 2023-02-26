from typing import Any, Callable, Dict, List, Optional, Union

import dataclasses
from collections import defaultdict
from numbers import Number

from .. import elements, types
from . import playback_control_ui, playback_control_js


@dataclasses.dataclass
class SyncedAnimationConfig:
    # Animation settings
    duration: float
    start_delay: float = 0
    end_delay: float = 0
    repeat_count: Union[int, str] = 'indefinite'
    fill: str = 'freeze'
    freeze_frame_at: Optional[float] = None

    # Playback controls
    show_playback_progress: bool = False
    show_playback_controls: bool = False  # Adds JavaScript to the drawing
    pause_on_load: bool = False
    controls_width: Optional[float] = None
    controls_height: float = 20
    controls_x: Optional[float] = None
    controls_center_y: Optional[float] = None

    # Playback control style
    bar_thickness: float = 4
    bar_hpad: float = 32
    bar_color: str = '#ccc'
    bar_past_color: str = '#05f'
    knob_rad: float = 6
    knob_fill: str = '#05f'
    pause_width: float = 16
    pause_corner_rad: float = 4
    pause_color: str = '#05f'
    pause_icon_color: str = '#eee'

    # Advanced configuration
    controls_js: str = 'DEFAULT'
    controls_js_onload: str = playback_control_js.SVG_ONLOAD
    controls_draw_function: Callable[['SyncedAnimationConfig', bool], 'Group'
            ] = playback_control_ui.draw_scrub

    @property
    def total_duration(self):
        return self.start_delay + self.duration + self.end_delay

    def extra_css(self, d, context):
        return []

    def extra_javascript(self, d, context):
        config = self._with_filled_defaults(d, context)
        if self.show_playback_controls:
            return [config.controls_js]
        return []

    def extra_onload_js(self, d, context):
        config = self._with_filled_defaults(d, context)
        if self.show_playback_controls:
            return [config.controls_js_onload]
        return []

    def extra_drawing_elements(self, d, context):
        config = self._with_filled_defaults(d, context)
        if self.show_playback_progress or self.show_playback_controls:
            # Control UI
            controls = config.controls_draw_function(
                    config, hidden=not self.show_playback_progress)
            return [controls]
        return []

    def _with_filled_defaults(self, d, context):
        # By default place the controls along the bottom edge
        width = d.view_box[2]
        x = d.view_box[0]
        if context.invert_y:
            y = d.view_box[1] + self.controls_height/2
        else:
            y = d.view_box[1] + d.view_box[3] - self.controls_height/2
        js = playback_control_js.SVG_JS_CONTENT
        if self.controls_width is not None:
            width = self.controls_width
            x += (d.view_box[2] - width) / 2
        if self.controls_x is not None:
            x = self.controls_x
        if self.controls_center_y is not None:
            y = self.controls_center_y
        if self.controls_js != 'DEFAULT':
            js = self.controls_js
        return dataclasses.replace(
                self, controls_width=width, controls_x=x, controls_center_y=y,
                controls_js=js)

    def override_args(self, args, lcontext):
        if (self.freeze_frame_at is not None
                and hasattr(lcontext.element, 'animation_data')):
            args = dict(args)
            data = lcontext.element.animation_data
            args.update(data.interpolate_at_time(self.freeze_frame_at))
        return args


@dataclasses.dataclass
class AnimatedAttributeTimeline:
    name: str
    animate_attrs: Optional[Dict[str, Any]] = None
    times: List[float] = dataclasses.field(default_factory=list)
    values: List[Any] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.name = types.normalize_attribute_name(self.name)

    def append(self, time, value):
        if self.times and time < self.times[-1]:
            raise ValueError('out-of-order key frame times')
        self.times.append(time)
        self.values.append(value)

    def extend(self, times, values):
        if len(times) != len(values):
            raise ValueError('times and values lists are mismatched lengths')
        if len(self.times) and len(times) and times[0] < self.times[-1]:
            raise ValueError('out-of-order key frame times')
        if list(times) != sorted(times):
            raise ValueError('out-of-order key frame times')
        self.times.extend(times)
        self.values.extend(values)

    def interpolate_at_time(self, at_time):
        return linear_interpolate_value(self.times, self.values, at_time)

    def as_animate_element(self, config: Optional[SyncedAnimationConfig]=None):
        if config is not None:
            total_duration = (
                    config.start_delay + config.duration + config.end_delay)
            start_delay = config.start_delay
            repeat_count = config.repeat_count
            fill = config.fill
        else:
            total_duration = self.times[-1]
            start_delay = 0
            repeat_count = 1
            fill = 'freeze'
        dur_str = f'{total_duration}s'
        values = self.values
        times = self.times
        key_times = ';'.join(
            str(max(0, min(1, round(
                    (start_delay + t) / total_duration, 3))))
            for t in times
        )
        values_str = ';'.join(map(str, values))
        if not key_times.startswith('0;'):
            key_times = '0;' + key_times
            values_str = f'{values[0]};' + values_str
        if not key_times.endswith(';1'):
            key_times = key_times + ';1'
            values_str = values_str + f';{values[-1]}'
        attrs = dict(
                dur=dur_str,
                values=values_str,
                keyTimes=key_times,
                repeatCount=repeat_count,
                fill=fill)
        attrs.update(self.animate_attrs or {})
        anim = elements.Animate(self.name, **attrs)
        return anim


class AnimationHelperData:
    def __init__(self):
        self.attr_timelines = {}

    def add_key_frame(self, time, animation_args=None, **attr_values):
        for attr, val in attr_values.items():
            attr = types.normalize_attribute_name(attr)
            timeline = self.attr_timelines.get(attr)
            if timeline is None:
                timeline = AnimatedAttributeTimeline(attr, animation_args)
                self.attr_timelines[attr] = timeline
            timeline.append(time, val)

    def add_attribute_key_sequence(self, attr, times, values, *,
                                   animation_args=None):
        attr = types.normalize_attribute_name(attr)
        timeline = self.attr_timelines.get(attr)
        if timeline is None:
            timeline = AnimatedAttributeTimeline(attr, animation_args)
            self.attr_timelines[attr] = timeline
        timeline.extend(times, values)

    def interpolate_at_time(self, at_time):
        return {
            name: timeline.interpolate_at_time(at_time)
            for name, timeline in self.attr_timelines.items()
        }

    def _timelines_adjusted_for_context(self, lcontext=None):
        all_timelines = dict(self.attr_timelines)
        if lcontext is not None and lcontext.context.invert_y:
            # Invert cy, y1, y2, ...
            for name, timeline in self.attr_timelines.items():
                if name != 'y' and lcontext.context.is_attr_inverted(name):
                    inv_timeline = AnimatedAttributeTimeline(
                            timeline.name, timeline.animate_attrs,
                            timeline.times, [-v for v in timeline.values])
                    all_timelines[name] = inv_timeline
            # Invert -y - height
            y_attrs = None
            if 'height' in all_timelines.keys():
                height_timeline = all_timelines['height']
                htimes = height_timeline.times
                hvalues = height_timeline.values
                y_attrs = height_timeline.animate_attrs
            else:
                height_timeline = None
                htimes = [0]
                hvalues = [lcontext.element.args.get('height', 0)]
            if 'y' in all_timelines.keys():
                y_timeline = all_timelines['y']
                ytimes = y_timeline.times
                yvalues = y_timeline.values
                y_attrs = y_timeline.animate_attrs
            else:
                y_timeline = None
                ytimes = [0]
                yvalues = [lcontext.element.args.get('y', 0)]
            if y_timeline is not None or height_timeline is not None:
                ytimes, yvalues = _merge_timeline_inverted_y_values(
                        ytimes, yvalues, htimes, hvalues,
                        linear_interpolate_value, linear_interpolate_value)
                if ytimes is not None:
                    y_timeline = AnimatedAttributeTimeline(
                            'y', y_attrs, ytimes, yvalues)
                    all_timelines['y'] = y_timeline
        return all_timelines

    def children_with_context(self, lcontext=None):
        if (lcontext is not None
                and lcontext.context.animation_config is not None
                and lcontext.context.animation_config.freeze_frame_at
                    is not None):
            return []  # Don't animate if frame is frozen
        all_timelines = self._timelines_adjusted_for_context(lcontext)
        return [
            timeline.as_animate_element(lcontext.context.animation_config)
            for timeline in all_timelines.values()
        ]


def linear_interpolate_value(times, values, at_time):
    if len(times) == 0:
        return 0
    idx = sum(t <= at_time for t in times)
    if idx >= len(times):
        return values[-1]
    elif idx <= 0:
        return values[0]
    elif at_time == times[idx-1]:
        return values[idx-1]
    elif isinstance(values[idx], Number) and isinstance(values[idx-1], Number):
        fraction = (at_time-times[idx-1]) / (times[idx]-times[idx-1])
        return values[idx-1] * (1-fraction) + (values[idx] * fraction)
    else:
        return values[idx-1]

def _merge_timeline_inverted_y_values(ytimes, yvalues, htimes, hvalues,
                                      yinterpolate, hinterpolate):
    if len(yvalues) == 1:
        try:
            return htimes, [-yvalues[0]-h for h in hvalues]
        except TypeError:
            return None, None
    elif len(hvalues) == 1:
        try:
            return ytimes, [-y-hvalues[0] for y in yvalues]
        except TypeError:
            return None, None
    elif ytimes == htimes:
        try:
            return ytimes, [-y-h for y, h in zip(yvalues, hvalues)]
        except TypeError:
            return None, None
    try:
        # Offset y-value by height if invert_y
        # Merge key_times for y and height animations
        new_times = []
        new_values = []
        hi = yi = 0
        inf = float('inf')
        ht = htimes[0] if len(htimes) else inf
        yt = ytimes[0] if len(ytimes) else inf
        while ht < inf and yt < inf:
            if yt < ht:
                h_val = hinterpolate(htimes, hvalues, yt)
                new_times.append(yt)
                new_values.append(-yvalues[yi] - h_val)
                yi += 1
            elif ht < yt:
                y_val = yinterpolate(ytimes, yvalues, ht)
                new_times.append(ht)
                new_values.append(-y_val - hvalues[hi])
                hi += 1
            else:
                new_times.append(yt)
                new_values.append(-yvalues[yi] - hvalues[hi])
                yi += 1
                hi += 1
            yt = ytimes[yi] if yi < len(ytimes) else inf
            ht = htimes[hi] if hi < len(htimes) else inf
        return new_times, new_values
    except TypeError:
        return None, None

def animate_element_sequence(times, element_sequence):
    '''Animate a list of elements to appear one-at-a-time in sequence.

    Elements should already be added to the drawing before using this.
    '''
    for i, elem in enumerate(element_sequence):
        if elem is None:
            continue  # Draw nothing during this time
        key_times = [times[i]]
        values = ['visible']
        if i > 0:
            key_times.insert(0, times[i-1])
            values.insert(0, 'hidden')
        if i < len(element_sequence) - 1:
            key_times.append(times[i+1])
            values.append('hidden')
        elem.add_attribute_key_sequence('visibility', key_times, values)

def animate_text_sequence(container, times: List[float], values: List[str],
                          *text_args, kwargs_list=None, **text_kwargs):
    '''Animate a sequence of text to appear one-at-a-time in sequence.

    Multiple `Text` elements will be appended to the given `container`.
    '''
    if kwargs_list is None:
        kwargs_list = [None] * len(values)
    new_elements = []
    for val, current_kw in zip(values, kwargs_list):
        kwargs = dict(text_kwargs)
        if current_kw is not None:
            kwargs.update(current_kw)
        new_elements.append(elements.Text(val, *text_args, **kwargs))
    animate_element_sequence(times, new_elements)
    container.extend(new_elements)
