import base64
import io
import warnings

from .url_encode import bytes_as_data_uri

def delay_import_cairo():
    try:
        import cairosvg
    except OSError as e:
        raise ImportError(
            'Failed to load CairoSVG. '
            'drawSvg will be unable to output PNG or other raster image '
            'formats. '
            'See https://github.com/cduck/drawsvg#full-feature-install '
            'for more details.'
        ) from e
    except ImportError as e:
        raise ImportError(
            'CairoSVG will need to be installed to rasterize images. '
            'Install with `python3 -m pip install "drawsvg[all]"` '
            'or `python3 -m pip install "drawsvg[raster]"`. '
            'See https://github.com/cduck/drawsvg#full-feature-install '
            'for more details.'
        ) from e
    return cairosvg

def delay_import_imageio():
    try:
        import imageio
    except ImportError as e:
        raise ImportError(
            'Optional dependencies not installed. '
            'Install with `python3 -m pip install "drawsvg[all]"` '
            'or `python3 -m pip install "drawsvg[raster]"`. '
            'See https://github.com/cduck/drawsvg#full-feature-install '
            'for more details.'
        ) from e
    return imageio


class Raster:
    def __init__(self, png_data=None, png_file=None):
        self.png_data = png_data
        self.png_file = png_file
    def save_png(self, fname):
        with open(fname, 'wb') as f:
            f.write(self.png_data)
    @staticmethod
    def from_svg(svg_data):
        cairosvg = delay_import_cairo()
        png_data = cairosvg.svg2png(bytestring=svg_data)
        return Raster(png_data)
    @staticmethod
    def from_svg_to_file(svg_data, out_file):
        cairosvg = delay_import_cairo()
        cairosvg.svg2png(bytestring=svg_data, write_to=out_file)
        return Raster(None, png_file=out_file)
    @staticmethod
    def from_arr(arr, out_file=None):
        imageio = delay_import_imageio()
        if out_file is None:
            with io.BytesIO() as f:
                imageio.imwrite(f, arr, format='png')
                f.seek(0)
                return Raster(f.read())
        else:
            imageio.imwrite(out_file, arr, format='png')
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
