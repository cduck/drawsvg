# drawSvg

A Python 3 library for programmatically generating SVG images (vector drawings) and rendering them or displaying them in a Jupyter notebook.

Most common SVG tags are supported and others can easily be added by writing a small subclass of `DrawableBasicElement` or `DrawableParentElement`.

An interactive [Jupyter notebook](https://jupyter.org) widget, `drawSvg.widgets.DrawingWidget`, is included that can update drawings based on mouse events.

# Install

drawSvg is available on PyPI:

```
$ pip3 install drawSvg
```

## Prerequisites

Cairo needs to be installed separately. When Cairo is installed, drawSvg can output PNG or other image formats in addition to SVG. See platform-specific [instructions for Linux, Windows, and macOS from Cairo](https://www.cairographics.org/download/). Below are some examples for installing Cairo on Linux distributions and macOS.

**Ubuntu**

```
$ sudo apt-get install libcairo2
```

**macOS**

Using [homebrew](https://brew.sh/):

```
$ brew install cairo
```

# Examples

### Basic drawing elements
```python
import drawSvg as draw

d = draw.Drawing(200, 100, origin='center', displayInline=False)

# Draw an irregular polygon
d.append(draw.Lines(-80, -45,
                    70, -49,
                    95, 49,
                    -90, 40,
                    close=False,
            fill='#eeee00',
            stroke='black'))

# Draw a rectangle
r = draw.Rectangle(0,0,40,50, fill='#1248ff')
r.appendTitle("Our first rectangle")  # Add a tooltip
d.append(r)

# Draw a circle
d.append(draw.Circle(-40, -10, 30,
            fill='red', stroke_width=2, stroke='black'))

# Draw an arbitrary path (a triangle in this case)
p = draw.Path(stroke_width=2, stroke='green',
              fill='black', fill_opacity=0.5)
p.M(-30,5)  # Start path at point (-30, 5)
p.l(60,30)  # Draw line to (60, 30)
p.h(-70)    # Draw horizontal line to x=-70
p.Z()       # Draw line to start
d.append(p)

# Draw multiple circular arcs
d.append(draw.ArcLine(60,-20,20,60,270,
            stroke='red', stroke_width=5, fill='red', fill_opacity=0.2))
d.append(draw.Arc(60,-20,20,60,270,cw=False,
            stroke='green', stroke_width=3, fill='none'))
d.append(draw.Arc(60,-20,20,270,60,cw=True,
            stroke='blue', stroke_width=1, fill='black', fill_opacity=0.3))

# Draw arrows
arrow = draw.Marker(-0.1, -0.5, 0.9, 0.5, scale=4, orient='auto')
arrow.append(draw.Lines(-0.1, -0.5, -0.1, 0.5, 0.9, 0, fill='red', close=True))
p = draw.Path(stroke='red', stroke_width=2, fill='none',
              marker_end=arrow)  # Add an arrow to the end of a path
p.M(20, -40).L(20, -27).L(0, -20)  # Chain multiple path operations
d.append(p)
d.append(draw.Line(30, -20, 0, -10,
            stroke='red', stroke_width=2, fill='none',
            marker_end=arrow))  # Add an arrow to the end of a line

d.setPixelScale(2)  # Set number of pixels per geometry unit
#d.setRenderSize(400,200)  # Alternative to setPixelScale
d.saveSvg('example.svg')
d.savePng('example.png')

# Display in Jupyter notebook
d.rasterize()  # Display as PNG
d  # Display as SVG
```

[![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example1.png)](https://github.com/cduck/drawSvg/blob/master/examples/example1.svg)

### Gradients
```python
import drawSvg as draw

d = draw.Drawing(1.5, 0.8, origin='center')

d.draw(draw.Rectangle(-0.75,-0.5,1.5,1, fill='#ddd'))

# Create gradient
gradient = draw.RadialGradient(0,-0.35,0.7*10)
gradient.addStop(0.5/0.7/10, 'green', 1)
gradient.addStop(1/10, 'red', 0)

# Draw a shape to fill with the gradient
p = draw.Path(fill=gradient, stroke='black', stroke_width=0.002)
p.arc(0,-0.35,0.7,30,120)
p.arc(0,-0.35,0.5,120,30,cw=True, includeL=True)
p.Z()
d.append(p)

# Draw another shape to fill with the same gradient
p = draw.Path(fill=gradient, stroke='red', stroke_width=0.002)
p.arc(0,-0.35,0.75,130,160)
p.arc(0,-0.35,0,160,130,cw=True, includeL=True)
p.Z()
d.append(p)

# Another gradient
gradient2 = draw.LinearGradient(0.1,-0.35,0.1+0.6,-0.35+0.2)
gradient2.addStop(0, 'green', 1)
gradient2.addStop(1, 'red', 0)
d.append(draw.Rectangle(0.1,-0.35,0.6,0.2,
                        stroke='black', stroke_width=0.002,
                        fill=gradient2))

# Display
d.setRenderSize(w=600)
d
```

[![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example2.png)](https://github.com/cduck/drawSvg/blob/master/examples/example2.svg)

### Duplicate geometry and clip paths
```python
import drawSvg as draw

d = draw.Drawing(1.4, 1.4, origin='center')

# Define clip path
clip = draw.ClipPath()
clip.append(draw.Rectangle(-.25,.25-1,1,1))

# Draw a cropped circle
c = draw.Circle(0,0,0.5, stroke_width='0.01', stroke='black',
                         fill_opacity=0.3, clip_path=clip,
                         id='circle')
d.append(c)

# Make a transparent copy, cropped again
g = draw.Group(opacity=0.5, clip_path=clip)
g.append(draw.Use('circle', 0.25,0.1))
d.append(g)

# Display
d.setRenderSize(400)
d.rasterize()
```

[![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example3.png)](https://github.com/cduck/drawSvg/blob/master/examples/example3.svg)

### Text following a path

```python
import drawSvg as draw
import math

len_x = 300
len_y = 300

d = draw.Drawing(len_x, len_y, origin='center')

# radii of the circles
R = 85
r = 65
rr = r - 10 # nested circle radius

# x, y are None when path argument provided for Text node
x = None
y = None

# centering circles around the whole canvas
ox = 0
oy = (len_y - (R*math.sin(math.pi/6) + R + 2*r))/2

# top right circle
cx = ox + R*math.cos(math.pi/6)
cy = oy + R*math.sin(math.pi/6)

ix = cx-r
iy = cy

fx = cx+r
fy = cy

path = draw.Path(stroke='lightblue', fill='none')
path.M(ix, iy)
path.A(r, r, 90, 1, 1, fx, fy)
path.A(r, r, 90, 1, 1, ix, iy)
d.append(path)

d.append(draw.Circle(ix, iy, 1, stroke='blue'))
text = draw.Text('text on a closed path with 10% offset and increased letter spacing', 10, path=path, startOffset='10%', letter_spacing=1.5)
d.append(text)

# top left circle
cx = ox + R*math.cos(5*math.pi/6)
cy = oy + R*math.sin(5*math.pi/6)

ix = cx-r
iy = cy

fx = cx+r
fy = cy

path = draw.Path(stroke='lightblue', fill='none')
path.M(ix, iy)
path.A(r, r, 90, 1, 1, fx, fy)
path.A(r, r, 90, 1, 1, ix, iy)
d.append(path)
d.append(draw.Circle(ix, iy, 1, stroke='blue'))

text = draw.Text(
    [
        'just some text on a closed path',
        'with multiple lines'],
    10, path=path)
d.append(text)

# bottom circle
cx = ox + R*math.cos(3*math.pi/2)
cy = oy + R*math.sin(3*math.pi/2)

ix = cx-r
iy = cy

fx = cx+r
fy = cy

path = draw.Path(stroke='lightblue', fill='none')
path.M(ix, iy)
path.A(r, r, 90, 1, 1, fx, fy)
path.A(r, r, 90, 1, 1, ix, iy)
d.append(path)

d.append(draw.Circle(ix, iy, 1, stroke='blue'))
text = draw.Text('just some centered text around 75% offset', 10, path=path, text_anchor='middle', startOffset='75%', dy=7)
d.append(text)

# text on an arbitrary path
ix = -len_x/2
iy = -len_y/4

path = draw.Path(stroke='red', fill='none')
path.M(ix, iy).C(-len_x/4, len_y, len_x/3, -len_y, len_x-len_x/6, len_y/2)
d.append(path)
d.append(draw.Circle(ix, iy, 1, stroke='blue'))

text = draw.Text('it can be used for any path element, including paths that are not closed\nand automatically shifts the path for consecutive lines', 10, path=path, dy=1)
d.append(text)

text = draw.Text('this is just a regular text without any path', 10, x=0, y=len_y/2-10, text_anchor='middle')
d.append(text)

text = draw.Text('regular text with increased letter spacing', 10, x=0, y=-len_y/2+7, text_anchor='middle', letter_spacing=1.25)
d.append(text)

d.rasterize()
```

[![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example8.png)](https://github.com/cduck/drawSvg/blob/master/examples/example8.svg)

### Implementing other SVG tags
```python
import drawSvg as draw

# Subclass DrawingBasicElement if it cannot have child nodes
# Subclass DrawingParentElement otherwise
# Subclass DrawingDef if it must go between <def></def> tags in an SVG
class Hyperlink(draw.DrawingParentElement):
    TAG_NAME = 'a'
    def __init__(self, href, target=None, **kwargs):
        # Other init logic...
        # Keyword arguments to super().__init__() correspond to SVG node
        # arguments: stroke_width=5 -> stroke-width="5"
        super().__init__(href=href, target=target, **kwargs)

d = draw.Drawing(1, 1.2, origin='center')

# Create hyperlink
hlink = Hyperlink('https://www.python.org', target='_blank',
                  transform='skewY(-30)')
# Add child elements
hlink.append(draw.Circle(0,0,0.5, fill='green'))
hlink.append(draw.Text('Hyperlink',0.2, 0,0, center=0.6, fill='white'))

# Draw and display
d.append(hlink)
d.setRenderSize(200)
d
```

[![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example4.png)](https://github.com/cduck/drawSvg/blob/master/examples/example4.svg)

### Animation with the SVG Animate Tag
```python
import drawSvg as draw

d = draw.Drawing(200, 200, origin='center')

# Animate the position and color of circle
c = draw.Circle(0, 0, 20, fill='red')
# See for supported attributes:
# https://developer.mozilla.org/en-US/docs/Web/SVG/Element/animate
c.appendAnim(draw.Animate('cy', '6s', '-80;80;-80',
                          repeatCount='indefinite'))
c.appendAnim(draw.Animate('cx', '6s', '0;80;0;-80;0',
                          repeatCount='indefinite'))
c.appendAnim(draw.Animate('fill', '6s', 'red;green;blue;yellow',
                          calcMode='discrete',
                          repeatCount='indefinite'))
d.append(c)

# Animate a black circle around an ellipse
ellipse = draw.Path()
ellipse.M(-90, 0)
ellipse.A(90, 40, 360, True, True, 90, 0)  # Ellipse path
ellipse.A(90, 40, 360, True, True, -90, 0)
ellipse.Z()
c2 = draw.Circle(0, 0, 10)
# See for supported attributes:
# https://developer.mozilla.org/en-US/docs/Web/SVG/Element/animateMotion
c2.appendAnim(draw.AnimateMotion(ellipse, '3s',
                                 repeatCount='indefinite'))
# See for supported attributes:
# https://developer.mozilla.org/en-US/docs/Web/SVG/Element/animateTransform
c2.appendAnim(draw.AnimateTransform('scale', '3s', '1,2;2,1;1,2;2,1;1,2',
                                    repeatCount='indefinite'))
d.append(c2)

d.saveSvg('animated.svg')  # Save to file
d  # Display in Jupyter notebook
```

[![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/animated-fix-github.svg?sanitize=true)](https://github.com/cduck/drawSvg/blob/master/examples/animated.svg)

### Interactive Widget
```python
import drawSvg as draw
from drawSvg.widgets import DrawingWidget
import hyperbolic.poincare.shapes as hyper  # pip3 install hyperbolic

# Create drawing
d = draw.Drawing(2, 2, origin='center')
d.setRenderSize(500)
d.append(draw.Circle(0, 0, 1, fill='orange'))
group = draw.Group()
d.append(group)

# Update the drawing based on user input
click_list = []
def redraw(points):
    group.children.clear()
    for x1, y1 in points:
        for x2, y2 in points:
            if (x1, y1) == (x2, y2): continue
            p1 = hyper.Point.fromEuclid(x1, y1)
            p2 = hyper.Point.fromEuclid(x2, y2)
            if p1.distanceTo(p2) <= 2:
                line = hyper.Line.fromPoints(*p1, *p2, segment=True)
                group.draw(line, hwidth=0.2, fill='white')
    for x, y in points:
        p = hyper.Point.fromEuclid(x, y)
        group.draw(hyper.Circle.fromCenterRadius(p, 0.1),
                   fill='green')
redraw(click_list)

# Create interactive widget and register mouse events
widget = DrawingWidget(d)
@widget.mousedown
def mousedown(widget, x, y, info):
    if (x**2 + y**2) ** 0.5 + 1e-5 < 1:
        click_list.append((x, y))
    redraw(click_list)
    widget.refresh()
@widget.mousemove
def mousemove(widget, x, y, info):
    if (x**2 + y**2) ** 0.5 + 1e-5 < 1:
        redraw(click_list + [(x, y)])
    widget.refresh()
widget
```

![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example5.gif)

### Animation with Python
```python
import drawSvg as draw

# Draw a frame of the animation
def draw_frame(t):
    d = draw.Drawing(2, 6.05, origin=(-1,-1.05))
    d.setRenderSize(h=300)
    d.append(draw.Rectangle(-2, -2, 4, 8, fill='white'))
    d.append(draw.Rectangle(-1, -1.05, 2, 0.05, fill='brown'))
    t = (t + 1) % 2 - 1
    y = 4 - t**2 * 4
    d.append(draw.Circle(0, y, 1, fill='lime'))
    return d

with draw.animate_jupyter(draw_frame, delay=0.05) as anim:
# Or:
#with draw.animate_video('example6.gif', draw_frame, duration=0.05
#                       ) as anim:
    # Add each frame to the animation
    for i in range(20):
        anim.draw_frame(i/10)
    for i in range(20):
        anim.draw_frame(i/10)
    for i in range(20):
        anim.draw_frame(i/10)
```

![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example6.gif)

### Asynchronous Animation in Jupyter
```python
# Jupyter cell 1:
import drawSvg as draw
from drawSvg.widgets import AsyncAnimation
widget = AsyncAnimation(fps=10)
widget
# [Animation is displayed here (click to pause)]

# Jupyter cell 2:
global_variable = 'a'
@widget.set_draw_frame  # Animation above is automatically updated
def draw_frame(secs=0):
    # Draw something...
    d = draw.Drawing(100, 40)
    d.append(draw.Text(global_variable, 20, 0, 10))
    d.append(draw.Text('{:0.1f}'.format(secs), 20, 30, 10))
    return d

# Jupyter cell 3:
global_variable = 'b'  # Animation above now displays 'b'
```

![Example output image](https://raw.githubusercontent.com/cduck/drawSvg/master/examples/example7.gif)
