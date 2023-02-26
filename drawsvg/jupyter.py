import dataclasses

from . import url_encode
from . import raster


class _Rasterizable:
    def rasterize(self, to_file=None):
        if to_file is not None:
            return raster.Raster.from_svg_to_file(self.svg, to_file)
        else:
            return raster.Raster.from_svg(self.svg)

@dataclasses.dataclass
class JupyterSvgInline(_Rasterizable):
    '''Jupyter-displayable SVG displayed inline on the Jupyter web page.'''
    svg: str
    def _repr_html_(self):
        return self.svg

@dataclasses.dataclass
class JupyterSvgImage(_Rasterizable):
    '''Jupyter-displayable SVG displayed within an img tag on the Jupyter web
    page.
    '''
    svg: str
    def _repr_html_(self):
        uri = url_encode.svg_as_utf8_data_uri(self.svg)
        return '<img src="{}">'.format(uri)

@dataclasses.dataclass
class JupyterSvgFrame:
    '''Jupyter-displayable SVG displayed within an HTML iframe.'''
    svg: str
    width: float
    height: float
    mime: str = 'image/svg+xml'
    def _repr_html_(self):
        uri = url_encode.svg_as_data_uri(self.svg, mime=self.mime)
        return (f'<iframe src="{uri}" width="{self.width}" '
                f'height="{self.height}" style="border:0" />')
