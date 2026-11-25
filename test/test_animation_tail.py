import xml.etree.ElementTree as ET

import pytest

import drawsvg as draw


@pytest.mark.parametrize('ytimes,yvalues,htimes,hvalues,expected', [
    ([0, 1, 3], [10, 20, 40], [0, 2], [2, 6], [-12, -24, -36, -46]),
    ([0, 2], [10, 30], [0, 1, 3], [2, 4, 8], [-12, -24, -36, -38]),
    ([0, 1, 2, 3], [10, 20, 30, 40],
     [0, 1, 2, 3], [2, 4, 6, 8], [-12, -24, -36, -48]),
])
def test_inverted_rectangle_keeps_both_complete_timelines(
        ytimes, yvalues, htimes, hvalues, expected):
    context = draw.Context(
        invert_y=True, animation_config=draw.SyncedAnimationConfig(duration=3))
    drawing = draw.Drawing(100, 100, context=context)
    rectangle = draw.Rectangle(0, 10, 20, 2)
    rectangle.add_attribute_key_sequence('y', ytimes, yvalues)
    rectangle.add_attribute_key_sequence('height', htimes, hvalues)
    drawing.append(rectangle)

    svg = ET.fromstring(drawing.as_svg())
    animation = svg.find(
        './/{http://www.w3.org/2000/svg}animate[@attributeName="y"]')
    assert animation is not None
    assert animation.attrib['keyTimes'] == '0;0.333;0.667;1'
    assert list(map(float, animation.attrib['values'].split(';'))) == expected

    # Export must not mutate the user's original animation.
    assert rectangle.animation_data.attr_timelines['y'].times == ytimes
    assert rectangle.animation_data.attr_timelines['y'].values == yvalues
