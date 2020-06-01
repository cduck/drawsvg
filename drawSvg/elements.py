
import sys
import math
import os.path
import base64
import warnings
import xml.sax.saxutils as xml
from collections import defaultdict

from . import defs

elementsModule = sys.modules[__name__]

# TODO: Support drawing ellipses without manually using Path

def writeXmlNodeArgs(args, outputFile):
    for k, v in args.items():
        if v is None: continue
        if isinstance(v, DrawingElement):
            if v.id is None:
                continue
            if k == 'xlink:href':
                v = '#{}'.format(v.id)
            else:
                v = 'url(#{})'.format(v.id)
        outputFile.write(' {}="{}"'.format(k,v))


class DrawingElement:
    ''' Base class for drawing elements

        Subclasses must implement writeSvgElement '''
    def writeSvgElement(self, idGen, isDuplicate, outputFile, dryRun,
                        forceDup=False):
        raise NotImplementedError('Abstract base class')
    def getSvgDefs(self):
        return ()
    def getLinkedElems(self):
        return ()
    def writeSvgDefs(self, idGen, isDuplicate, outputFile, dryRun):
        for defn in self.getSvgDefs():
            if isDuplicate(defn): continue
            defn.writeSvgDefs(idGen, isDuplicate, outputFile, dryRun)
            if defn.id is None:
                defn.id = idGen()
            defn.writeSvgElement(idGen, isDuplicate, outputFile, dryRun,
                                 forceDup=True)
            if not dryRun:
                outputFile.write('\n')
    def __eq__(self, other):
        return self is other

class DrawingBasicElement(DrawingElement):
    ''' Base class for SVG drawing elements that are a single node with no
        child nodes '''
    TAG_NAME = '_'
    hasContent = False
    def __init__(self, **args):
        self.args = {}
        for k, v in args.items():
            k = k.replace('__', ':')
            k = k.replace('_', '-')
            if k[-1] == '-':
                k = k[:-1]
            self.args[k] = v
        self.children = []
        self.orderedChildren = defaultdict(list)
    def checkChildrenAllowed(self):
        if not self.hasContent:
            raise RuntimeError(
                '{} does not support children'.format(type(self)))
    def allChildren(self):
        ''' Returns self.children and self.orderedChildren as a single list. '''
        output = list(self.children)
        for z in sorted(self.orderedChildren):
            output.extend(self.orderedChildren[z])
        return output
    @property
    def id(self):
        return self.args.get('id', None)
    @id.setter
    def id(self, newId):
        self.args['id'] = newId
    def writeSvgElement(self, idGen, isDuplicate, outputFile, dryRun,
                        forceDup=False):
        children = self.allChildren()
        if dryRun:
            if isDuplicate(self) and self.id is None:
                self.id = idGen()
            for elem in self.getLinkedElems():
                if elem.id is None:
                    elem.id = idGen()
            if self.hasContent:
                self.writeContent(idGen, isDuplicate, outputFile, dryRun)
            if children:
                self.writeChildrenContent(idGen, isDuplicate, outputFile,
                                          dryRun)
            return
        if isDuplicate(self) and not forceDup:
            outputFile.write('<use xlink:href="#{}" />'.format(self.id))
            return
        outputFile.write('<')
        outputFile.write(self.TAG_NAME)
        writeXmlNodeArgs(self.args, outputFile)
        if not self.hasContent and not children:
            outputFile.write(' />')
        else:
            outputFile.write('>')
            if self.hasContent:
                self.writeContent(idGen, isDuplicate, outputFile, dryRun)
            if children:
                self.writeChildrenContent(idGen, isDuplicate, outputFile,
                                          dryRun)
            outputFile.write('</')
            outputFile.write(self.TAG_NAME)
            outputFile.write('>')
    def writeContent(self, idGen, isDuplicate, outputFile, dryRun):
        ''' Override in a subclass to add data between the start and end
            tags.  This will not be called if hasContent is False. '''
        raise RuntimeError('This element has no content')
    def writeChildrenContent(self, idGen, isDuplicate, outputFile, dryRun):
        ''' Override in a subclass to add data between the start and end
            tags.  This will not be called if hasContent is False. '''
        children = self.allChildren()
        if dryRun:
            for child in children:
                child.writeSvgElement(idGen, isDuplicate, outputFile, dryRun)
            return
        outputFile.write('\n')
        for child in children:
            child.writeSvgElement(idGen, isDuplicate, outputFile, dryRun)
            outputFile.write('\n')
    def getSvgDefs(self):
        return [v for v in self.args.values()
                if isinstance(v, DrawingElement)]
    def writeSvgDefs(self, idGen, isDuplicate, outputFile, dryRun):
        super().writeSvgDefs(idGen, isDuplicate, outputFile, dryRun)
        for child in self.allChildren():
            child.writeSvgDefs(idGen, isDuplicate, outputFile, dryRun)
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return (self.TAG_NAME == other.TAG_NAME and
                    self.args == other.args and
                    self.children == other.children and
                    self.orderedChildren == other.orderedChildren)
        return False
    def appendAnim(self, animateElement):
        self.children.append(animateElement)
    def extendAnim(self, animateIterable):
        self.children.extend(animateIterable)

class DrawingParentElement(DrawingBasicElement):
    ''' Base class for SVG elements that can have child nodes '''
    hasContent = True
    def __init__(self, children=(), orderedChildren=None, **args):
        super().__init__(**args)
        self.children = list(children)
        if orderedChildren:
            self.orderedChildren.update(
                (z, list(v)) for z, v in orderedChildren.items())
        if self.children or self.orderedChildren:
            self.checkChildrenAllowed()
    def draw(self, obj, *, z=None, **kwargs):
        if obj is None:
            return
        if not hasattr(obj, 'writeSvgElement'):
            elements = obj.toDrawables(elements=elementsModule, **kwargs)
        else:
            assert len(kwargs) == 0
            elements = (obj,)
        self.extend(elements, z=z)
    def append(self, element, *, z=None):
        self.checkChildrenAllowed()
        if z is not None:
            self.orderedChildren[z].append(element)
        else:
            self.children.append(element)
    def extend(self, iterable, *, z=None):
        self.checkChildrenAllowed()
        if z is not None:
            self.orderedChildren[z].extend(iterable)
        else:
            self.children.extend(iterable)
    def writeContent(self, idGen, isDuplicate, outputFile, dryRun):
        pass

class NoElement(DrawingElement):
    ''' A drawing element that has no effect '''
    def __init__(self): pass
    def writeSvgElement(self, idGen, isDuplicate, outputFile, dryRun,
                        forceDup=False):
        pass
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return True
        return False

class Group(DrawingParentElement):
    ''' A group of drawing elements

        Any transform will apply to its children and other attributes will be
        inherited by its children. '''
    TAG_NAME = 'g'

class Raw(Group):
    ''' Any any SVG code to insert into the output. '''
    def __init__(self, content, defs=(), **kwargs):
        super().__init__(**kwargs)
        self.content = content
        self.defs = defs
    def writeContent(self, idGen, isDuplicate, outputFile, dryRun):
        if dryRun:
            return
        outputFile.write(self.content)
    def getSvgDefs(self):
        return self.defs

class Use(DrawingBasicElement):
    ''' A copy of another element

        The other element becomes an SVG def shared between all Use elements
        that reference it. '''
    TAG_NAME = 'use'
    def __init__(self, otherElem, x, y, **kwargs):
        y = -y
        if isinstance(otherElem, str) and not otherElem.startswith('#'):
            otherElem = '#' + otherElem
        super().__init__(xlink__href=otherElem, x=x, y=y, **kwargs)

class Animate(DrawingBasicElement):
    ''' Animation for a specific property of another element

        This should be added as a child of the element to animate.  Otherwise
        the other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'animate'
    def __init__(self, attributeName, dur, from_or_values=None, to=None,
                 begin=None, otherElem=None, **kwargs):
        if to is None:
            values = from_or_values
            from_ = None
        else:
            values = None
            from_ = from_or_values
        if isinstance(otherElem, str) and not otherElem.startswith('#'):
            otherElem = '#' + otherElem
        kwargs.update(attributeName=attributeName, to=to, dur=dur, begin=begin)
        kwargs.setdefault('values', values)
        kwargs.setdefault('from_', from_)
        super().__init__(xlink__href=otherElem, **kwargs)

    def getSvgDefs(self):
        return [v for k, v in self.args.items()
                if isinstance(v, DrawingElement)
                if k != 'xlink:href']

    def getLinkedElems(self):
        return (self.args['xlink:href'],)

class _Mpath(DrawingBasicElement):
    ''' Used by AnimateMotion '''
    TAG_NAME = 'mpath'
    def __init__(self, otherPath, **kwargs):
        super().__init__(xlink__href=otherPath, **kwargs)

class AnimateMotion(Animate):
    ''' Animation for the motion another element along a path

        This should be added as a child of the element to animate.  Otherwise
        the other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'animateMotion'
    def __init__(self, path, dur, from_or_values=None, to=None, begin=None,
                 otherElem=None, **kwargs):
        useMpath = False
        if isinstance(path, DrawingElement):
            useMpath = True
            pathElem = path
            path = None
        kwargs.setdefault('attributeName', None)
        super().__init__(dur=dur, from_or_values=from_or_values, to=to,
                         begin=begin, path=path, otherElem=otherElem, **kwargs)
        if useMpath:
            self.children.append(_Mpath(pathElem))

class AnimateTransform(Animate):
    ''' Animation for the transform property of another element

        This should be added as a child of the element to animate.  Otherwise
        the other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'animateTransform'
    def __init__(self, type, dur, from_or_values, to=None, begin=None,
                 attributeName='transform', otherElem=None, **kwargs):
        super().__init__(attributeName, dur=dur, from_or_values=from_or_values,
                         to=to, begin=begin, type=type, otherElem=otherElem,
                         **kwargs)

class Set(Animate):
    ''' Animation for a specific property of another element that sets the new
        value without a transition.

        This should be added as a child of the element to animate.  Otherwise
        the other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'set'
    def __init__(self, attributeName, dur, to=None, begin=None,
                 otherElem=None, **kwargs):
        super().__init__(attributeName, dur=dur, from_or_values=None,
                         to=to, begin=begin, otherElem=otherElem, **kwargs)

class Discard(Animate):
    ''' Animation configuration specifying when it is safe to discard another
        element.  E.g. when it will no longer be visible after an animation.

        This should be added as a child of the element to animate.  Otherwise
        the other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'discard'
    def __init__(self, attributeName, begin=None, **kwargs):
        kwargs.setdefault('attributeName', None)
        kwargs.setdefault('to', None)
        kwargs.setdefault('dur', None)
        super().__init__(from_or_values=None, begin=begin, otherElem=None,
                         **kwargs)

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
        '.svg': 'image/svg+xml',
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
        if embed:
            if mimeType is None and path is not None:
                ext = os.path.splitext(path)[1].lower()
                if ext in self.MIME_MAP:
                    mimeType = self.MIME_MAP[ext]
                else:
                    mimeType = self.MIME_DEFAULT
                    warnings.warn('Unknown image file type "{}"'.format(ext),
                                  Warning)
            if mimeType is None:
                mimeType = self.MIME_DEFAULT
                warnings.warn('Unspecified image type; assuming png', Warning)
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
                         xlink__href=uri, **kwargs)

class Text(DrawingParentElement):
    ''' Text

        Additional keyword arguments are output as additional arguments to the
        SVG node e.g. fill="red", font_size=20, text_anchor="middle". '''
    TAG_NAME = 'text'
    hasContent = True
    def __init__(self, text, fontSize, x, y, center=False, valign=None,
                 lineHeight=1, **kwargs):
        singleLine = isinstance(text, str)
        if '\n' in text:
            text = text.splitlines()
            singleLine = False
        if not singleLine:
            text = tuple(text)
            numLines = len(text)
        else:
            numLines = 1
        centerOffset = 0
        emOffset = 0
        if center:
            if 'text_anchor' not in kwargs:
                kwargs['text_anchor'] = 'middle'
            if valign is None:
                if singleLine:
                    # Backwards compatible centering
                    centerOffset = fontSize*0.5*center
                else:
                    emOffset = 0.4 - lineHeight * (numLines - 1) / 2
        if valign == 'middle':
            emOffset = 0.4 - lineHeight * (numLines - 1) / 2
        elif valign == 'top':
            emOffset = 1
        elif valign == 'bottom':
            emOffset = -lineHeight * (numLines - 1)
        if centerOffset:
            try:
                fontSize = float(fontSize)
            except TypeError:
                pass
            else:
                translate = 'translate(0,{})'.format(centerOffset)
                if 'transform' in kwargs:
                    kwargs['transform'] += ' ' + translate
                else:
                    kwargs['transform'] = translate
        super().__init__(x=x, y=-y, font_size=fontSize, **kwargs)
        if singleLine:
            self.escapedText = xml.escape(text)
        else:
            self.escapedText = ''
            # Text is an iterable
            for i, line in enumerate(text):
                dy = '{}em'.format(emOffset if i == 0 else lineHeight)
                self.appendLine(line, x=x, dy=dy)
    def writeContent(self, idGen, isDuplicate, outputFile, dryRun):
        if dryRun:
            return
        outputFile.write(self.escapedText)
    def writeChildrenContent(self, idGen, isDuplicate, outputFile, dryRun):
        ''' Override in a subclass to add data between the start and end
            tags.  This will not be called if hasContent is False. '''
        children = self.allChildren()
        if dryRun:
            for child in children:
                child.writeSvgElement(idGen, isDuplicate, outputFile, dryRun)
            return
        for child in children:
            child.writeSvgElement(idGen, isDuplicate, outputFile, dryRun)
    def appendLine(self, line, **kwargs):
        self.append(TSpan(line, **kwargs))

class TSpan(DrawingBasicElement):
    ''' A line of text within the Text element. '''
    TAG_NAME = 'tspan'
    hasContent = True
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.escapedText = xml.escape(text)
    def writeContent(self, idGen, isDuplicate, outputFile, dryRun):
        if dryRun:
            return
        outputFile.write(self.escapedText)

class Rectangle(DrawingBasicElement):
    ''' A rectangle

        Additional keyword arguments are output as additional arguments to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    TAG_NAME = 'rect'
    def __init__(self, x, y, width, height, **kwargs):
        try:
            y = -y-height
        except TypeError:
            pass
        super().__init__(x=x, y=y, width=width, height=height,
            **kwargs)

class Circle(DrawingBasicElement):
    ''' A circle

        Additional keyword arguments are output as additional properties to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    TAG_NAME = 'circle'
    def __init__(self, cx, cy, r, **kwargs):
        try:
            cy = -cy
        except TypeError:
            pass
        super().__init__(cx=cx, cy=cy, r=r, **kwargs)

class Ellipse(DrawingBasicElement):
    ''' An ellipse

        Additional keyword arguments are output as additional properties to the
        SVG node e.g. fill="red", stroke="#ff4477", stroke_width=2. '''
    TAG_NAME = 'ellipse'
    def __init__(self, cx, cy, rx, ry, **kwargs):
        try:
            cy = -cy
        except TypeError:
            pass
        super().__init__(cx=cx, cy=cy, rx=rx, ry=ry, **kwargs)

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
    def H(self, x): self.append('H', x)
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
        self.append('A', rx, ry, rot, int(bool(largeArc)), int(bool(sweep)), ex,
                    -ey)
    def a(self, rx, ry, rot, largeArc, sweep, ex, ey):
        self.append('a', rx, ry, rot, int(bool(largeArc)), int(bool(sweep)), ex,
                    -ey)
    def arc(self, cx, cy, r, startDeg, endDeg, cw=False, includeM=True,
            includeL=False):
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

