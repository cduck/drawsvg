
from io import StringIO
import base64
import urllib.parse
import re
from collections import defaultdict

from . import Raster
from . import elements as elementsModule


STRIP_CHARS = ('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11'
               '\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f')


class Drawing:
    ''' A canvas to draw on

        Supports iPython: If a Drawing is the last line of a cell, it will be
        displayed as an SVG below. '''
    def __init__(self, width, height, origin=(0,0), idPrefix='d',
                 displayInline=True, **svgArgs):
        assert float(width) == width
        assert float(height) == height
        self.width = width
        self.height = height
        if origin == 'center':
            self.viewBox = (-width/2, -height/2, width, height)
        else:
            origin = tuple(origin)
            assert len(origin) == 2
            self.viewBox = origin + (width, height)
        self.viewBox = (self.viewBox[0], -self.viewBox[1]-self.viewBox[3],
                        self.viewBox[2], self.viewBox[3])
        self.elements = []
        self.orderedElements = defaultdict(list)
        self.otherDefs = []
        self.pixelScale = 1
        self.renderWidth = None
        self.renderHeight = None
        self.idPrefix = str(idPrefix)
        self.displayInline = displayInline
        self.svgArgs = {}
        for k, v in svgArgs.items():
            k = k.replace('__', ':')
            k = k.replace('_', '-')
            if k[-1] == '-':
                k = k[:-1]
            self.svgArgs[k] = v
        self.idIndex = 0
    def setRenderSize(self, w=None, h=None):
        self.renderWidth = w
        self.renderHeight = h
        return self
    def setPixelScale(self, s=1):
        self.renderWidth = None
        self.renderHeight = None
        self.pixelScale = s
        return self
    def calcRenderSize(self):
        if self.renderWidth is None and self.renderHeight is None:
            return (self.width * self.pixelScale,
                    self.height * self.pixelScale)
        elif self.renderWidth is None:
            s = self.renderHeight / self.height
            return self.width * s, self.renderHeight
        elif self.renderHeight is None:
            s = self.renderWidth / self.width
            return self.renderWidth, self.height * s
        else:
            return self.renderWidth, self.renderHeight
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
        if z is not None:
            self.orderedElements[z].append(element)
        else:
            self.elements.append(element)
    def extend(self, iterable, *, z=None):
        if z is not None:
            self.orderedElements[z].extend(iterable)
        else:
            self.elements.extend(iterable)
    def insert(self, i, element):
        self.elements.insert(i, element)
    def remove(self, element):
        self.elements.remove(element)
    def clear(self):
        self.elements.clear()
    def index(self, *args, **kwargs):
        self.elements.index(*args, **kwargs)
    def count(self, element):
        self.elements.count(element)
    def reverse(self):
        self.elements.reverse()
    def drawDef(self, obj, **kwargs):
        if not hasattr(obj, 'writeSvgElement'):
            elements = obj.toDrawables(elements=elementsModule, **kwargs)
        else:
            assert len(kwargs) == 0
            elements = (obj,)
        self.otherDefs.extend(elements)
    def appendDef(self, element):
        self.otherDefs.append(element)
    def allElements(self):
        ''' Returns self.elements and self.orderedElements as a single list. '''
        output = list(self.elements)
        for z in sorted(self.orderedElements):
            output.extend(self.orderedElements[z])
        return output
    def asSvg(self, outputFile=None):
        returnString = outputFile is None
        if returnString:
            outputFile = StringIO()
        imgWidth, imgHeight = self.calcRenderSize()
        startStr = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{}" height="{}" viewBox="{} {} {} {}"'''.format(
            imgWidth, imgHeight, *self.viewBox)
        endStr = '</svg>'
        outputFile.write(startStr)
        elementsModule.writeXmlNodeArgs(self.svgArgs, outputFile)
        outputFile.write('>\n<defs>\n')
        # Write definition elements
        def idGen(base=''):
            idStr = self.idPrefix + base + str(self.idIndex)
            self.idIndex += 1
            return idStr
        prevSet = set((id(defn) for defn in self.otherDefs))
        def isDuplicate(obj):
            nonlocal prevSet
            dup = id(obj) in prevSet
            prevSet.add(id(obj))
            return dup
        for element in self.otherDefs:
            try:
                element.writeSvgElement(idGen, isDuplicate, outputFile, False)
                outputFile.write('\n')
            except AttributeError:
                pass
        allElements = self.allElements()
        for element in allElements:
            try:
                element.writeSvgDefs(idGen, isDuplicate, outputFile, False)
            except AttributeError:
                pass
        outputFile.write('</defs>\n')
        # Generate ids for normal elements
        prevDefSet = set(prevSet)
        for element in allElements:
            try:
                element.writeSvgElement(idGen, isDuplicate, outputFile, True)
            except AttributeError:
                pass
        prevSet = prevDefSet
        # Write normal elements
        for element in allElements:
            try:
                element.writeSvgElement(idGen, isDuplicate, outputFile, False)
                outputFile.write('\n')
            except AttributeError:
                pass
        outputFile.write(endStr)
        if returnString:
            return outputFile.getvalue()
    def saveSvg(self, fname):
        with open(fname, 'w') as f:
            self.asSvg(outputFile=f)
    def savePng(self, fname):
        self.rasterize(toFile=fname)
    def rasterize(self, toFile=None):
        if toFile:
            return Raster.fromSvgToFile(self.asSvg(), toFile)
        else:
            return Raster.fromSvg(self.asSvg())
    def _repr_svg_(self):
        ''' Display in Jupyter notebook '''
        if not self.displayInline:
            return None
        return self.asSvg()
    def _repr_html_(self):
        ''' Display in Jupyter notebook '''
        if self.displayInline:
            return None
        prefix = b'data:image/svg+xml;base64,'
        data = base64.b64encode(self.asSvg().encode())
        src = (prefix+data).decode()
        return '<img src="{}">'.format(src)
    def asDataUri(self, strip_chars=STRIP_CHARS):
        ''' Returns a data URI with base64 encoding. '''
        data = self.asSvg()
        search = re.compile('|'.join(strip_chars))
        data_safe = search.sub(lambda m: '', data)
        b64 = base64.b64encode(data_safe.encode())
        return 'data:image/svg+xml;base64,' + b64.decode(encoding='ascii')
    def asUtf8DataUri(self, unsafe_chars='"', strip_chars=STRIP_CHARS):
        ''' Returns a data URI without base64 encoding.

            The characters '#&%' are always escaped.  '#' and '&' break parsing
            of the data URI.  If '%' is not escaped, plain text like '%50' will
            be incorrectly decoded to 'P'.  The characters in `strip_chars`
            cause the SVG not to render even if they are escaped. '''
        data = self.asSvg()
        unsafe_chars = (unsafe_chars or '') + '#&%'
        replacements = {
            char: urllib.parse.quote(char, safe='')
            for char in unsafe_chars
        }
        replacements.update({
            char: ''
            for char in strip_chars
        })
        search = re.compile('|'.join(map(re.escape, replacements.keys())))
        data_safe = search.sub(lambda m: replacements[m.group(0)], data)
        return 'data:image/svg+xml;utf8,' + data_safe
