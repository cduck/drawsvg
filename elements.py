
import math
import os.path
import base64
import warnings

# TODO: Support drawing ellipses without manually using Path


class DrawingElement:
    ''' Base class for drawing elements

        Subclasses must implement writeSvgElement '''
    def writeSvgElement(self, outputFile):
        raise NotImplementedError('Abstract base class')
    def __eq__(self, other):
        return self is other

class DrawingBasicElement(DrawingElement):
    ''' Base class for SVG drawing elements that are a single node with no
        child nodes '''
    TAG_NAME = '_'
    def __init__(self, **args):
        self.args = args
    def writeSvgElement(self, outputFile):
        outputFile.write('<')
        outputFile.write(self.TAG_NAME)
        outputFile.write(' ')
        for k, v in self.args.items():
            k = k.replace('__', ':')
            k = k.replace('_', '-')
            outputFile.write('{}="{}" '.format(k,v))
        outputFile.write('/>')
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return (self.tagName == other.tagName and
                    self.args == other.args)
        return False

class NoElement(DrawingElement):
    ''' A drawing element that has no effect '''
    def __init__(self): pass
    def writeSvgElement(self, outputFile):
        pass
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return True
        return False

class Image(DrawingBasicElement):
    ''' A linked or embedded raster image '''
    TAG_NAME = 'image'
    MIME_MAP = {
        '.bm':  'image/bmp',
        '.bmp': 'image/bmp',
        '.gif': 'image/gif',
        '.jpeg':'image/jpeg',
        '.jpg': 'image/jpeg',
        '.png': 'image/png',
        '.tif': 'image/tiff',
        '.tiff':'image/tiff',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
    }
    MIME_DEFAULT = 'image/png'
    def __init__(self, x, y, width, height, path=None, data=None, embed=False,
                 mimeType=None, **kwargs):
        ''' Specify either the path or data argument.  If path is used and
            embed is True, the image file is embedded in a data URI. '''
        if path is None and data is None:
            raise ValueError('Either path or data arguments must be given')
        if mimeType is None and path is not None:
                ext = os.path.splitext(path)[1].lower()
                if ext in self.MIME_MAP:
                    mimeType = self.MIME_MAP[ext]
                else:
                    mimeType = self.MIME_DEFAULT
                    warnings.warn('Unknown image file type "{}"'.format(ext), Warning)
        if mimeType is None:
            mimeType = self.MIME_DEFAULT
            warnings.warn('Unspecified image type; assuming png'.format(ext), Warning)
        if data is not None:
            embed = True
        if embed and data is None:
            with open(path, 'rb') as f:
                data = f.read()
        if not embed:
            uri = path
        else:
            encData = base64.b64encode(data).decode()
            uri = 'data:{};base64,{}'.format(mimeType, encData)
        super().__init__(x=x, y=-y-height, width=width, height=height,
                         href=uri, **kwargs)

class Rectangle(DrawingBasicElement):
    ''' A rectangle

        Additional keyword arguments are output as additional arguments to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    TAG_NAME = 'rect'
    def __init__(self, x, y, width, height, **kwargs):
        super().__init__(x=x, y=-y-height, width=width, height=height,
            **kwargs)

class Circle(DrawingBasicElement):
    ''' A circle

        Additional keyword arguments are output as additional properties to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    TAG_NAME = 'circle'
    def __init__(self, cx, cy, r, **kwargs):
        super().__init__(cx=cx, cy=-cy, r=r, **kwargs)

class ArcLine(Circle):
    ''' An arc

        In most cases, use Arc instead of ArcLine.  ArcLine uses the
        stroke-dasharray SVG property to make the edge of a circle look like
        an arc.

        Additional keyword arguments are output as additional arguments to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    def __init__(self, cx, cy, r, startDeg, endDeg, **kwargs):
        if endDeg - startDeg == 360:
            super().__init__(cx, cy, r, **kwargs)
            return
        startDeg, endDeg = (-endDeg) % 360, (-startDeg) % 360
        arcDeg = (endDeg - startDeg) % 360
        def arcLen(deg): return math.radians(deg) * r
        wholeLen = 2 * math.pi * r
        if endDeg == startDeg:
            offset = 1
            dashes = "0 {}".format(wholeLen+2)
        #elif endDeg >= startDeg:
        elif True:
            startLen = arcLen(startDeg)
            arcLen = arcLen(arcDeg)
            offLen = wholeLen - arcLen
            offset = -startLen
            dashes = "{} {}".format(arcLen, offLen)
        #else:
        #    firstLen = arcLen(endDeg)
        #    secondLen = arcLen(360-startDeg)
        #    gapLen = wholeLen - firstLen - secondLen
        #    offset = 0
        #    dashes = "{} {} {}".format(firstLen, gapLen, secondLen)
        super().__init__(cx, cy, r, stroke_dasharray=dashes,
                         stroke_dashoffset=offset, **kwargs)

class Path(DrawingBasicElement):
    ''' An arbitrary path

        Path Supports building an SVG path by calling instance methods
        corresponding to path commands.

        Additional keyword arguments are output as additional properties to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    TAG_NAME = 'path'
    def __init__(self, d='', **kwargs):
        super().__init__(d=d, **kwargs)
    def append(self, commandStr, *args):
        if len(self.args['d']) > 0:
            commandStr = ' ' + commandStr
        if len(args) > 0:
            commandStr = commandStr + ','.join(map(str, args))
        self.args['d'] += commandStr
    def M(self, x, y): self.append('M', x, -y)
    def m(self, dx, dy): self.append('m', dx, -dy)
    def L(self, x, y): self.append('L', x, -y)
    def l(self, dx, dy): self.append('l', dx, -dy)
    def H(self, x, y): self.append('H', x)
    def h(self, dx): self.append('h', dx)
    def V(self, y): self.append('V', -y)
    def v(self, dy): self.append('v', -dy)
    def Z(self): self.append('Z')
    def C(self, cx1, cy1, cx2, cy2, ex, ey):
        self.append('C', cx1, -cy1, cx2, -cy2, ex, -ey)
    def c(self, cx1, cy1, cx2, cy2, ex, ey):
        self.append('c', cx1, -cy1, cx2, -cy2, ex, -ey)
    def S(self, cx2, cy2, ex, ey): self.append('S', cx2, -cy2, ex, -ey)
    def s(self, cx2, cy2, ex, ey): self.append('s', cx2, -cy2, ex, -ey)
    def Q(self, cx, cy, ex, ey): self.append('Q', cx, -cy, ex, -ey)
    def q(self, cx, cy, ex, ey): self.append('q', cx, -cy, ex, -ey)
    def T(self, ex, ey): self.append('T', ex, -ey)
    def t(self, ex, ey): self.append('t', ex, -ey)
    def A(self, rx, ry, rot, largeArc, sweep, ex, ey):
        self.append('A', rx, ry, rot, int(bool(largeArc)), int(bool(sweep)), ex, -ey)
    def a(self, rx, ry, rot, largeArc, sweep, ex, ey):
        self.append('a', rx, ry, rot, int(bool(largeArc)), int(bool(sweep)), ex, -ey)
    def arc(self, cx, cy, r, startDeg, endDeg, cw=False, includeM=True, includeL=False):
        ''' Uses A() to draw a circular arc '''
        largeArc = (endDeg - startDeg) % 360 > 180
        startRad, endRad = startDeg*math.pi/180, endDeg*math.pi/180
        sx, sy = r*math.cos(startRad), r*math.sin(startRad)
        ex, ey = r*math.cos(endRad), r*math.sin(endRad)
        if includeL:
            self.L(cx+sx, cy+sy)
        elif includeM:
            self.M(cx+sx, cy+sy)
        self.A(r, r, 0, largeArc ^ cw, cw, cx+ex, cy+ey)

class Lines(Path):
    ''' A sequence of connected lines (or a polygon)

        Additional keyword arguments are output as additional properties to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    def __init__(self, sx, sy, *points, close=False, **kwargs):
        super().__init__(d='', **kwargs)
        self.M(sx, sy)
        assert len(points) % 2 == 0
        for i in range(len(points) // 2):
            self.L(points[2*i], points[2*i+1])
        if close:
            self.Z()

class Line(Lines):
    ''' A line

        Additional keyword arguments are output as additional properties to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    def __init__(self, sx, sy, ex, ey, **kwargs):
        super().__init__(sx, sy, ex, ey, close=False, **kwargs)

class Arc(Path):
    ''' An arc

        Additional keyword arguments are output as additional properties to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    def __init__(self, cx, cy, r, startDeg, endDeg, cw=False, **kwargs):
        super().__init__(d='', **kwargs)
        self.arc(cx, cy, r, startDeg, endDeg, cw=cw, includeM=True)

