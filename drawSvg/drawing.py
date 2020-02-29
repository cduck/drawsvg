
from io import StringIO
import base64

from . import Raster
from . import elements as elementsModule


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
    def draw(self, obj, **kwargs):
        if not hasattr(obj, 'writeSvgElement'):
            elements = obj.toDrawables(elements=elementsModule, **kwargs)
        else:
            assert len(kwargs) == 0
            elements = (obj,)
        self.extend(elements)
    def append(self, element):
        self.elements.append(element)
    def extend(self, iterable):
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
        idIndex = 0
        def idGen(base=''):
            nonlocal idIndex
            idStr = self.idPrefix + base + str(idIndex)
            idIndex += 1
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
        for element in self.elements:
            try:
                element.writeSvgDefs(idGen, isDuplicate, outputFile, False)
            except AttributeError:
                pass
        outputFile.write('</defs>\n')
        # Generate ids for normal elements
        prevDefSet = set(prevSet)
        for element in self.elements:
            try:
                element.writeSvgElement(idGen, isDuplicate, outputFile, True)
            except AttributeError:
                pass
        prevSet = prevDefSet
        # Write normal elements
        for element in self.elements:
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
