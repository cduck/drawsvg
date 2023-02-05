import base64
import io
import warnings

from .url_encode import bytes_as_data_uri

try:
    import cairosvg
except OSError as e:
    raise ImportError(
        'Failed to load CairoSVG. '
        'drawSvg will be unable to output PNG or other raster image formats. '
        'See https://github.com/cduck/drawsvg#prerequisites for more details.'
    ) from e
except ImportError as e:
    raise ImportError(
        'CairoSVG will need to be installed to rasterize images. '
        'Install with `pip3 install cairosvg`.'
    ) from e


class Raster:
    def __init__(self, png_data=None, png_file=None):
        self.png_data = png_data
        self.png_file = png_file
    def save_png(self, fname):
        with open(fname, 'wb') as f:
            f.write(self.png_data)
    @staticmethod
    def from_svg(svg_data):
        png_data = cairosvg.svg2png(bytestring=svg_data)
        return Raster(png_data)
    @staticmethod
    def from_svg_to_file(svg_data, out_file):
        cairosvg.svg2png(bytestring=svg_data, write_to=out_file)
        return Raster(None, png_file=out_file)
    def _repr_png_(self):
        if self.png_data:
            return self.png_data
        elif self.png_file:
            try:
                with open(self.png_file, 'rb') as f:
                    return f.read()
            except TypeError:
                pass
            try:
                self.png_file.seek(0)
                return self.png_file.read()
            except io.UnsupportedOperation:
                pass
    def as_data_uri(self):
        if self.png_data:
            data = self.png_data
        else:
            try:
                with open(self.png_file, 'rb') as f:
                    data = f.read()
            except TypeError:
                self.png_file.seek(0)
                data = self.png_file.read()
        return bytes_as_data_uri(data, mime='image/png')
