
from .elements import DrawingElement, DrawingParentElement


class DrawingDef(DrawingParentElement):
    ''' Parent class of SVG nodes that must be direct children of <defs> '''
    def getSvgDefs(self):
        return (self,)
    def writeSvgDefs(self, idGen, isDuplicate, outputFile):
        DrawingElement.writeSvgDefs(idGen, isDuplicate, outputFile)

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

