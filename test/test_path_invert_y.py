'''Run tests with pytest'''

import drawsvg as draw


def test_invert_y_works_with_various_format_numbers():
    d = draw.Drawing(100, 100, context=draw.Context(invert_y=True))
    d.append(p := draw.Path(fill='none', stroke='black', stroke_width=2))
    p.M(1, 0.)  # Zero
    p.L(10, 1e-10)  # Exponential format tiny
    p.L(20, -1e-6)  # Negative exponential format tiny
    p.L(30, 1e300)  # Exponential format huge
    p.L(40, -1e250)  # Negative exponential format huge
    p.L(50, 55.555)  # Typical float
    p.L(60, -66.66666666)  # Typical negative float
    p.L(70, 77.)  # Integer but type float
    p.L(80, -88)  # Negative integer
    p.L(90, 9<<80)  # Huge integer
    p.L(100, -10<<82)  # Huge negative integer
    p.L(110, float('inf'))  # Inf
    p.L(120, float('-inf'))  # -Inf
    p.L(130, float('nan'))  # NaN

    svg_text = d.as_svg()
    # Check that all y values are negated
    print(svg_text)
    assert '1,-0.0' in svg_text  # Note it's still a float (if formatted slightly different)
    assert '10,-1e-10' in svg_text
    assert '20,1e-06' in svg_text
    assert '30,-1e+300' in svg_text
    assert '40,1e+250' in svg_text
    assert '50,-55.555' in svg_text
    assert '60,66.66666666' in svg_text
    assert '70,-77' in svg_text
    assert '80,88' in svg_text
    assert '90,-10880332376531662572355584' in svg_text
    assert '100,48357032784585166988247040' in svg_text
    assert '110,-inf' in svg_text
    assert '120,inf' in svg_text
    assert '130,nan' in svg_text  # -NaN -> NaN
