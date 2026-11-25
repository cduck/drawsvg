import xml.etree.ElementTree as ET

import pytest

import drawsvg as draw


@pytest.mark.parametrize('command', ['A', 'a'])
@pytest.mark.parametrize('rotation,reflected', [(45, -45), (-30, 30), (0, 0)])
@pytest.mark.parametrize('large_arc,sweep', [(False, True), (True, False)])
def test_invert_y_reflects_rotated_elliptical_arcs(
        command, rotation, reflected, large_arc, sweep):
    drawing = draw.Drawing(200, 200, context=draw.Context(invert_y=True))
    path = draw.Path().M(10, 20)
    getattr(path, command)(30, 50, rotation, large_arc, sweep, 100, 80)
    drawing.append(path)

    svg = ET.fromstring(drawing.as_svg())
    output = svg.find('{http://www.w3.org/2000/svg}path').attrib['d']
    assert output == (
        f'M10,-20 {command}30,50,{reflected},'
        f'{int(large_arc)},{int(not sweep)},100,-80')

    # The original path is still usable with the default coordinate system.
    normal = draw.Drawing(200, 200)
    normal.append(path)
    normal_svg = ET.fromstring(normal.as_svg())
    assert normal_svg.find('{http://www.w3.org/2000/svg}path').attrib['d'] == (
        f'M10,20 {command}30,50,{rotation},'
        f'{int(large_arc)},{int(sweep)},100,80')
