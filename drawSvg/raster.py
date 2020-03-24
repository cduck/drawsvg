
import base64
import io
import warnings
from .missing import MissingModule


try:
    import cairosvg
except OSError as e:
    msg = (
        'Failed to import CairoSVG. '
        'drawSvg will be unable to output PNG or other raster image formats. '
        'See https://github.com/cduck/drawSvg#prerequisites for more details.\n'
        'Original OSError: {}'.format(e)
    )
    cairosvg = MissingModule(msg)
    warnings.warn(msg, RuntimeWarning)
except ImportError as e:
    msg = (
        'CairoSVG will need to be installed to rasterize images: Install with `pip3 install cairosvg`\n'
        'Original ImportError: {}'.format(e)
    )
    cairosvg = MissingModule(msg)
    warnings.warn(msg, RuntimeWarning)


class Raster:
    def __init__(self, pngData=None, pngFile=None):
        self.pngData = pngData
        self.pngFile = pngFile
    def savePng(self, fname):
        with open(fname, 'wb') as f:
            f.write(self.pngData)
    @staticmethod
    def fromSvg(svgData):
        pngData = cairosvg.svg2png(bytestring=svgData)
        return Raster(pngData)
    @staticmethod
    def fromSvgToFile(svgData, outFile):
        cairosvg.svg2png(bytestring=svgData, write_to=outFile)
        return Raster(None, pngFile=outFile)
    def _repr_png_(self):
        if self.pngData:
            return self.pngData
        elif self.pngFile:
            try:
                with open(self.pngFile, 'rb') as f:
                    return f.read()
            except TypeError:
                pass
            try:
                self.pngFile.seek(0)
                return self.pngFile.read()
            except io.UnsupportedOperation:
                pass
    def asDataUri(self):
        if self.pngData:
            data = self.pngData
        else:
            try:
                with open(self.pngFile, 'rb') as f:
                    data = f.read()
            except TypeError:
                self.pngFile.seek(0)
                data = self.pngFile.read()
        b64 = base64.b64encode(data)
        return 'data:image/png;base64,' + b64.decode(encoding='ascii')
