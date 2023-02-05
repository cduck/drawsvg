from io import StringIO
from collections import defaultdict
import random
import string

from . import Raster
from . import types, elements as elements_module, jupyter



SVG_START = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     '''
SVG_END = '</svg>'
SVG_CSS_FMT = '<style><![CDATA[{}]]></style>'
SVG_JS_FMT = '<script><![CDATA[{}]]></script>'


class Drawing:
    '''
    A vector drawing.

    Append shapes and other elements with `.append()`.  The default coordinate
    system origin is at the top-left corner with x-values increasing to the
    right and y-values increasing downward.

    Supports Jupyter: If a Drawing is the last line of a cell, it will be
    displayed as an SVG below.
    '''
    def __init__(self, width, height, origin=(0,0), context: types.Context=None,
                 id_prefix='d', **svg_args):
        assert float(width) == width
        assert float(height) == height
        if context is None:
            context = types.Context()
        self.width = width
        self.height = height
        if isinstance(origin, str):
            self.view_box = {
                'center': (-width/2, -height/2, width, height),
                'top-left': (0, 0, width, height),
                'top-right': (-width, 0, width, height),
                'bottom-left': (0, -height, width, height),
                'bottom-right': (-width, -height, width, height),
            }[origin]
        else:
            origin = tuple(origin)
            assert len(origin) == 2
            self.view_box = origin + (width, height)
        self.elements = []
        self.ordered_elements = defaultdict(list)
        self.other_defs = []
        self.css_list = []
        self.js_list = []
        self.pixel_scale = 1
        self.render_width = None
        self.render_height = None
        self.context = context
        self.id_prefix = str(id_prefix)
        self.svg_args = {}
        for k, v in svg_args.items():
            k = k.replace('__', ':')
            k = k.replace('_', '-')
            if k[-1] == '-':
                k = k[:-1]
            self.svg_args[k] = v
        self.context.drawing_creation_hook(self)
    def set_render_size(self, w=None, h=None):
        self.render_width = w
        self.render_height = h
        return self
    def set_pixel_scale(self, s=1):
        self.render_width = None
        self.render_height = None
        self.pixel_scale = s
        return self
    def calc_render_size(self):
        if self.render_width is None and self.render_height is None:
            return (self.width * self.pixel_scale,
                    self.height * self.pixel_scale)
        elif self.render_width is None:
            s = self.render_height / self.height
            return self.width * s, self.render_height
        elif self.render_height is None:
            s = self.render_width / self.width
            return self.render_width, self.height * s
        else:
            return self.render_width, self.render_height
    def draw(self, obj, *, z=None, **kwargs):
        '''Add any object that knows how to draw itself to the drawing.

        This object must implement the `to_drawables(**kwargs)` method
        that returns a `DrawingElement` or list of elements.
        '''
        if obj is None:
            return
        if not hasattr(obj, 'write_svg_element'):
            elements = obj.to_drawables(**kwargs)
        else:
            assert len(kwargs) == 0
            elements = obj
        if hasattr(elements, 'write_svg_element'):
            self.append(elements, z=z)
        else:
            self.extend(elements, z=z)
    def append(self, element, *, z=None):
        '''Add any `DrawingElement` to the drawing.

        Do not append a `DrawingDef` referenced by other elements.  These are
        included automatically.  Use `.append_def()` for an unreferenced
        `DrawingDef`.
        '''
        if z is not None:
            self.ordered_elements[z].append(element)
        else:
            self.elements.append(element)
    def extend(self, iterable, *, z=None):
        if z is not None:
            self.ordered_elements[z].extend(iterable)
        else:
            self.elements.extend(iterable)
    def insert(self, i, element):
        self.elements.insert(i, element)
    def remove(self, element):
        self.elements.remove(element)
    def clear(self):
        self.elements.clear()
    def index(self, *args, **kwargs):
        return self.elements.index(*args, **kwargs)
    def count(self, element):
        return self.elements.count(element)
    def reverse(self):
        self.elements.reverse()
    def draw_def(self, obj, **kwargs):
        if not hasattr(obj, 'write_svg_element'):
            elements = obj.to_drawables(**kwargs)
        else:
            assert len(kwargs) == 0
            elements = obj
        if hasattr(elements, 'write_svg_element'):
            self.append_def(elements)
        else:
            self.other_defs.extend(elements)
    def append_def(self, element):
        self.other_defs.append(element)
    def append_title(self, text, **kwargs):
        self.append(elements_module.Title(text, **kwargs))
    def append_css(self, css_text):
        self.css_list.append(css_text)
    def append_javascriipt(self, js_text, onload=None):
        if onload:
            if self.svg_args.get('onload'):
                self.svg_args['onload'] = f'{self.svg_args["onload"]};{onload}'
            else:
                self.svg_args['onload'] = onload
        self.js_list.append(js_text)
    def all_elements(self):
        '''Return self.elements and self.ordered_elements as a single list.'''
        output = list(self.elements)
        for z in sorted(self.ordered_elements):
            output.extend(self.ordered_elements[z])
        return output
    def as_svg(self, output_file=None, randomize_ids=False):
        if output_file is None:
            with StringIO() as f:
                self.as_svg(f, randomize_ids=randomize_ids)
                return f.getvalue()
        img_width, img_height = self.calc_render_size()
        svg_args = dict(
                width=img_width, height=img_height,
                viewBox=' '.join(map(str, self.view_box)))
        svg_args.update(self.svg_args)
        output_file.write(SVG_START)
        self.context.write_svg_document_args(svg_args, output_file)
        output_file.write('>\n')
        if self.css_list:
            output_file.write(SVG_CSS_FMT.format('\n'.join(self.css_list)))
            output_file.write('\n')
        if self.js_list:
            output_file.write(SVG_JS_FMT.format('\n'.join(self.js_list)))
            output_file.write('\n')
        output_file.write('<defs>\n')
        # Write definition elements
        id_prefix = self.id_prefix
        id_prefix = self._random_id() if randomize_ids else self.id_prefix
        id_index = 0
        def id_gen(base=''):
            nonlocal id_index
            id_str = f'{id_prefix}{base}{id_index}'
            id_index += 1
            return id_str
        id_map = defaultdict(id_gen)
        prev_set = set((id(defn) for defn in self.other_defs))
        def is_duplicate(obj):
            nonlocal prev_set
            dup = id(obj) in prev_set
            prev_set.add(id(obj))
            return dup
        for element in self.other_defs:
            if hasattr(element, 'write_svg_element'):
                element.write_svg_element(
                        id_map, is_duplicate, output_file, self.context, False)
                output_file.write('\n')
        all_elements = self.all_elements()
        for element in all_elements:
            if hasattr(element, 'write_svg_defs'):
                element.write_svg_defs(
                        id_map, is_duplicate, output_file, self.context, False)
        output_file.write('</defs>\n')
        # Generate ids for normal elements
        prev_def_set = set(prev_set)
        for element in all_elements:
            if hasattr(element, 'write_svg_element'):
                element.write_svg_element(
                        id_map, is_duplicate, output_file, self.context, True)
        prev_set = prev_def_set
        # Write normal elements
        for element in all_elements:
            if hasattr(element, 'write_svg_element'):
                element.write_svg_element(
                        id_map, is_duplicate, output_file, self.context, False)
                output_file.write('\n')
        output_file.write(SVG_END)
    @staticmethod
    def _random_id(length=8):
        return (random.choice(string.ascii_letters)
                + ''.join(random.choices(
                    string.ascii_letters+string.digits, k=length-1)))
    def save_svg(self, fname, encoding='utf-8'):
        with open(fname, 'w', encoding=encoding) as f:
            self.as_svg(output_file=f)
    def save_png(self, fname):
        self.rasterize(to_file=fname)
    def rasterize(self, to_file=None):
        if to_file:
            return Raster.from_svg_to_file(self.as_svg(), to_file)
        else:
            return Raster.from_svg(self.as_svg())
    def _repr_svg_(self):
        '''Display in Jupyter notebook.'''
        return self.as_svg(randomize_ids=True)
    def display_inline(self):
        '''Display inline in the Jupyter web page.'''
        return jupyter.JupyterSvgInline(self.as_svg(randomize_ids=True))
    def display_iframe(self):
        '''Display within an iframe the Jupyter web page.'''
        w, h = self.calc_render_size()
        return jupyter.JupyterSvgFrame(self.as_svg(), w, h)
    def display_image(self):
        '''Display within an img in the Jupyter web page.'''
        return jupyter.JupyterSvgImage(self.as_svg())
