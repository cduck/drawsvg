from typing import Any, Callable, Dict, List, Optional, Union

import dataclasses
from collections import defaultdict

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

    def drawing_creation_hook(self, d, context):
        '''Called by Drawing on initialization.'''
        config = self._with_filled_defaults(d, context)
        if self.show_playback_progress or self.show_playback_controls:
            # Append control UI
            controls = config.controls_draw_function(
                    config, hidden=not self.show_playback_progress)
            d.append(controls, z=float('inf'))
        if self.show_playback_controls:
            # Add control JavaScript
            d.append_javascript(config.controls_js,
                                onload=config.controls_js_onload)

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
        key_times = ';'.join(
            str(max(0, min(1, round(
                    (start_delay + t) / total_duration, 3))))
            for t in self.times
        )
        values_str = ';'.join(map(str, self.values))
        if not key_times.startswith('0;'):
            key_times = '0;' + key_times
            values_str = f'{self.values[0]};' + values_str
        if not key_times.endswith(';1'):
            key_times = key_times + ';1'
            values_str = values_str + f';{self.values[-1]}'
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

    def children_with_context(self, context=None):
        return [
            timeline.as_animate_element(context.animation_config)
            for timeline in self.attr_timelines.values()
        ]


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
