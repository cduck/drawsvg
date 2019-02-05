
import io

try:
    import cairosvg
except (ImportError, OSError):
    import warnings
    from .missing import MissingModule
    msg = 'CairoSVG will need to be installed to rasterize images: Install with `pip3 install cairosvg`'
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

