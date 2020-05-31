
from .elements import DrawingElement, DrawingParentElement


class DrawingDef(DrawingParentElement):
    ''' Parent class of SVG nodes that must be direct children of <defs> '''
    def getSvgDefs(self):
        return (self,)

class DrawingDefSub(DrawingParentElement):
    ''' Parent class of SVG nodes that are meant to be descendants of a Def '''
    pass

class LinearGradient(DrawingDef):
    ''' A linear gradient to use as a fill or other color

        Has <stop> nodes as children. '''
    TAG_NAME = 'linearGradient'
    def __init__(self, x1, y1, x2, y2, gradientUnits='userSpaceOnUse', **kwargs):
        yShift = 0
        if gradientUnits != 'userSpaceOnUse':
            yShift = 1
        try: y1 = yShift - y1
        except TypeError: pass
        try: y2 = yShift - y2
        except TypeError: pass
        super().__init__(x1=x1, y1=y1, x2=x2, y2=y2, gradientUnits=gradientUnits,
                         **kwargs)
    def addStop(self, offset, color, opacity=None, **kwargs):
        stop = GradientStop(offset=offset, stop_color=color,
                            stop_opacity=opacity, **kwargs)
        self.append(stop)

class RadialGradient(DrawingDef):
    ''' A radial gradient to use as a fill or other color

        Has <stop> nodes as children. '''
    TAG_NAME = 'radialGradient'
    def __init__(self, cx, cy, r, gradientUnits='userSpaceOnUse', fy=None, **kwargs):
        yShift = 0
        if gradientUnits != 'userSpaceOnUse':
            yShift = 1
        try: cy = yShift - cy
        except TypeError: pass
        try: fy = yShift - fy
        except TypeError: pass
        super().__init__(cx=cx, cy=cy, r=r, gradientUnits=gradientUnits,
                         fy=fy, **kwargs)
    def addStop(self, offset, color, opacity=None, **kwargs):
        stop = GradientStop(offset=offset, stop_color=color,
                            stop_opacity=opacity, **kwargs)
        self.append(stop)

class GradientStop(DrawingDefSub):
    ''' A control point for a radial or linear gradient '''
    TAG_NAME = 'stop'
    hasContent = False

class ClipPath(DrawingDef):
    ''' A shape used to crop another element by not drawing outside of this
        shape

        Has regular drawing elements as children. '''
    TAG_NAME = 'clipPath'

class Mask(DrawingDef):
    ''' A drawing where the gray value and transparency are used to control the
        transparency of another shape.

        Has regular drawing elements as children. '''
    TAG_NAME = 'mask'

class Filter(DrawingDef):
    ''' A filter to apply to geometry

        For example a blur filter. '''
    TAG_NAME = 'filter'

class FilterItem(DrawingDefSub):
    ''' A child of Filter with any tag name'''
    hasContent = False
    def __init__(self, tag_name, **args):
        super().__init__(**args)
        self.TAG_NAME = tag_name

class Marker(DrawingDef):
    ''' A small drawing that can be placed at the ends of (or along) a path.

        This can be used for arrow heads or points on a graph for example.

        By default, units are multiples of stroke width.'''
    TAG_NAME = 'marker'
    def __init__(self, minx, miny, maxx, maxy, scale=1, orient='auto',
                 **kwargs):
        width = maxx - minx
        height = maxy - miny
        kwargs = {
            'markerWidth': width if scale == 1 else float(width) * scale,
            'markerHeight': height if scale == 1 else float(height) * scale,
            'viewBox': '{} {} {} {}'.format(minx, -maxy, width, height),
            'orient': orient,
            **kwargs,
        }
        super().__init__(**kwargs)
