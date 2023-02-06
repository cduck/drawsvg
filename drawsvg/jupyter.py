import dataclasses

from . import url_encode


@dataclasses.dataclass
class JupyterSvgInline:
    '''Jupyter-displayable SVG displayed inline on the Jupyter web page.'''
    svg: str
    def _repr_html_(self):
        return self.svg

@dataclasses.dataclass
class JupyterSvgImage:
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
