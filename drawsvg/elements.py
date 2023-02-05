import math
import os.path
import base64
import warnings
import xml.sax.saxutils as xml
from collections import defaultdict

from . import defs, url_encode


def write_xml_node_args(args, output_file, id_map=None):
    for k, v in args.items():
        if v is None: continue
        if isinstance(v, DrawingElement):
            mapped_id = v.id
            if id_map and id(v) in id_map:
                mapped_id = id_map[id(v)]
            if mapped_id is None:
                continue
            if k == 'xlink:href':
                v = '#{}'.format(mapped_id)
            else:
                v = 'url(#{})'.format(mapped_id)
        output_file.write(' {}="{}"'.format(k,v))


class DrawingElement:
    '''Base class for drawing elements.

    Subclasses must implement write_svg_element.
    '''
    def write_svg_element(self, id_map, is_duplicate, output_file, dry_run,
                          force_dup=False):
        raise NotImplementedError('Abstract base class')
    def get_svg_defs(self):
        return ()
    def get_linked_elems(self):
        return ()
    def write_svg_defs(self, id_map, is_duplicate, output_file, dry_run):
        for defn in self.get_svg_defs():
            if is_duplicate(defn):
                continue
            defn.write_svg_defs(id_map, is_duplicate, output_file, dry_run)
            if defn.id is None:
                id_map[id(defn)]
            defn.write_svg_element(
                    id_map, is_duplicate, output_file, dry_run, force_dup=True)
            if not dry_run:
                output_file.write('\n')
    def __eq__(self, other):
        return self is other

class DrawingBasicElement(DrawingElement):
    '''Base class for SVG drawing elements that are a single node with no child
    nodes.
    '''
    TAG_NAME = '_'
    has_content = False
    def __init__(self, **args):
        self.args = {}
        for k, v in args.items():
            k = k.replace('__', ':')
            k = k.replace('_', '-')
            if k[-1] == '-':
                k = k[:-1]
            self.args[k] = v
        self.children = []
        self.ordered_children = defaultdict(list)
    def check_children_allowed(self):
        if not self.has_content:
            raise RuntimeError(
                    '{} does not support children'.format(type(self)))
    def all_children(self):
        '''Return self.children and self.ordered_children as a single list.'''
        output = list(self.children)
        for z in sorted(self.ordered_children):
            output.extend(self.ordered_children[z])
        return output
    @property
    def id(self):
        return self.args.get('id', None)
    def write_svg_element(self, id_map, is_duplicate, output_file, dry_run,
                          force_dup=False):
        children = self.all_children()
        if dry_run:
            if is_duplicate(self) and self.id is None:
                id_map[id(self)]
            for elem in self.get_linked_elems():
                if elem.id is None:
                    id_map[id(elem.id)]
            if self.has_content:
                self.write_content(id_map, is_duplicate, output_file, dry_run)
            if children:
                self.write_children_content(
                        id_map, is_duplicate, output_file, dry_run)
            return
        if is_duplicate(self) and not force_dup:
            mapped_id = self.id
            if id_map and id(self) in id_map:
                mapped_id = id_map[id(self)]
            output_file.write('<use xlink:href="#{}" />'.format(mapped_id))
            return
        output_file.write('<')
        output_file.write(self.TAG_NAME)
        override_args = self.args
        if id(self) in id_map:
            override_args = dict(override_args)
            override_args['id'] = id_map[id(self)]
        write_xml_node_args(override_args, output_file, id_map)
        if not self.has_content and not children:
            output_file.write(' />')
        else:
            output_file.write('>')
            if self.has_content:
                self.write_content(id_map, is_duplicate, output_file, dry_run)
            if children:
                self.write_children_content(
                        id_map, is_duplicate, output_file, dry_run)
            output_file.write('</')
            output_file.write(self.TAG_NAME)
            output_file.write('>')
    def write_content(self, id_map, is_duplicate, output_file, dry_run):
        '''Override in a subclass to add data between the start and end tags.

        This will not be called if has_content is False.
        '''
        raise RuntimeError('This element has no content')
    def write_children_content(self, id_map, is_duplicate, output_file,
                               dry_run):
        '''Override in a subclass to add data between the start and end tags.

        This will not be called if has_content is False.
        '''
        children = self.all_children()
        if dry_run:
            for child in children:
                child.write_svg_element(
                        id_map, is_duplicate, output_file, dry_run)
            return
        output_file.write('\n')
        for child in children:
            child.write_svg_element(id_map, is_duplicate, output_file, dry_run)
            output_file.write('\n')
    def get_svg_defs(self):
        return [v for v in self.args.values()
                if isinstance(v, DrawingElement)]
    def write_svg_defs(self, id_map, is_duplicate, output_file, dry_run):
        super().write_svg_defs(id_map, is_duplicate, output_file, dry_run)
        for child in self.all_children():
            child.write_svg_defs(id_map, is_duplicate, output_file, dry_run)
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return (self.TAG_NAME == other.TAG_NAME and
                    self.args == other.args and
                    self.children == other.children and
                    self.ordered_children == other.ordered_children)
        return False
    def append_anim(self, animate_element):
        self.children.append(animate_element)
    def extend_anim(self, animate_iterable):
        self.children.extend(animate_iterable)
    def append_title(self, text, **kwargs):
        self.children.append(Title(text, **kwargs))

class DrawingParentElement(DrawingBasicElement):
    '''Base class for SVG elements that can have child nodes.'''
    has_content = True
    def __init__(self, children=(), ordered_children=None, **args):
        super().__init__(**args)
        self.children = list(children)
        if ordered_children:
            self.ordered_children.update(
                (z, list(v)) for z, v in ordered_children.items())
        if self.children or self.ordered_children:
            self.check_children_allowed()
    def draw(self, obj, *, z=None, **kwargs):
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
        self.check_children_allowed()
        if z is not None:
            self.ordered_children[z].append(element)
        else:
            self.children.append(element)
    def extend(self, iterable, *, z=None):
        self.check_children_allowed()
        if z is not None:
            self.ordered_children[z].extend(iterable)
        else:
            self.children.extend(iterable)
    def write_content(self, id_map, is_duplicate, output_file, dry_run):
        pass

class NoElement(DrawingElement):
    ''' A drawing element that has no effect '''
    def __init__(self):
        pass
    def write_svg_element(self, id_map, is_duplicate, output_file, dry_run,
                          force_dup=False):
        pass
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return True
        return False

class Group(DrawingParentElement):
    '''A group of drawing elements.

    Any transform will apply to its children and other attributes will be
    inherited by its children.
    '''
    TAG_NAME = 'g'

class Raw(DrawingBasicElement):
    '''Raw unescaped text to include in the SVG output.

    Special XML characters like '<' and '&' in the content may have unexpected
    effects or completely break the resulting SVG.
    '''
    has_content = True
    def __init__(self, content, defs=()):
        super().__init__()
        self.content = content
        self.defs = defs
    def write_content(self, id_map, is_duplicate, output_file, dry_run):
        if dry_run:
            return
        output_file.write(self.content)
    def get_svg_defs(self):
        return self.defs
    def check_children_allowed(self):
        raise RuntimeError('{} does not support children'.format(type(self)))

class Use(DrawingBasicElement):
    '''A copy of another element, drawn at a given position

    The referenced element becomes an SVG def shared between all Use elements
    that reference it.  Useful for drawings with many copies of similar shapes.
    Additional arguments like `fill='red'` will be used as the default for this
    copy of the shapes.
    '''
    TAG_NAME = 'use'
    def __init__(self, other_elem, x, y, **kwargs):
        if isinstance(other_elem, str) and not other_elem.startswith('#'):
            other_elem = '#' + other_elem
        super().__init__(xlink__href=other_elem, x=x, y=y, **kwargs)

class Animate(DrawingBasicElement):
    '''Animation for a specific property of another element.

    This should be added as a child of the element to animate.  Otherwise the
    referenced other element and this element must both be added to the drawing.

    Useful SVG attributes:
    - repeatCount: 0, 1, ..., 'indefinite'
    '''
    TAG_NAME = 'animate'
    def __init__(self, attributeName, dur, from_or_values=None, to=None,
                 begin=None, other_elem=None, **kwargs):
        if to is None:
            values = from_or_values
            from_ = None
        else:
            values = None
            from_ = from_or_values
        if isinstance(other_elem, str) and not other_elem.startswith('#'):
            other_elem = '#' + other_elem
        kwargs.update(attributeName=attributeName, to=to, dur=dur, begin=begin)
        kwargs.setdefault('values', values)
        kwargs.setdefault('from_', from_)
        super().__init__(xlink__href=other_elem, **kwargs)

    def get_svg_defs(self):
        return [v for k, v in self.args.items()
                if isinstance(v, DrawingElement)
                if k != 'xlink:href']

    def get_linked_elems(self):
        elem = self.args['xlink:href']
        return (elem,) if elem is not None else ()

class _Mpath(DrawingBasicElement):
    '''Used by AnimateMotion.'''
    TAG_NAME = 'mpath'
    def __init__(self, other_path, **kwargs):
        super().__init__(xlink__href=other_path, **kwargs)

class AnimateMotion(Animate):
    '''Animation for the motion of another element along a path.

    This should be added as a child of the element to animate.  Otherwise the
    referenced other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'animateMotion'
    def __init__(self, path, dur, from_or_values=None, to=None, begin=None,
                 other_elem=None, **kwargs):
        use_mpath = False
        if isinstance(path, DrawingElement):
            use_mpath = True
            path_elem = path
            path = None
        kwargs.setdefault('attributeName', None)
        super().__init__(dur=dur, from_or_values=from_or_values, to=to,
                         begin=begin, path=path, other_elem=other_elem,
                         **kwargs)
        if use_mpath:
            self.children.append(_Mpath(path_elem))

class AnimateTransform(Animate):
    '''Animation for the transform property of another element.

    This should be added as a child of the element to animate.  Otherwise the
    referenced other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'animateTransform'
    def __init__(self, type, dur, from_or_values, to=None, begin=None,
                 attributeName='transform', other_elem=None, **kwargs):
        super().__init__(attributeName, dur=dur, from_or_values=from_or_values,
                         to=to, begin=begin, type=type, other_elem=other_elem,
                         **kwargs)

class Set(Animate):
    '''Animation for a specific property of another element that sets the new
    value without a transition.

    This should be added as a child of the element to animate.  Otherwise the
    referenced other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'set'
    def __init__(self, attributeName, dur, to=None, begin=None,
                 other_elem=None, **kwargs):
        super().__init__(attributeName, dur=dur, from_or_values=None,
                         to=to, begin=begin, other_elem=other_elem, **kwargs)

class Discard(Animate):
    '''Animation configuration specifying when it is safe to discard another
    element.

    Use this when an element will no longer be visible after an animation.
    This should be added as a child of the element to animate.  Otherwise the
    referenced other element and this element must both be added to the drawing.
    '''
    TAG_NAME = 'discard'
    def __init__(self, attributeName, begin=None, **kwargs):
        kwargs.setdefault('attributeName', None)
        kwargs.setdefault('to', None)
        kwargs.setdefault('dur', None)
        super().__init__(from_or_values=None, begin=begin, other_elem=None,
                         **kwargs)

class Image(DrawingBasicElement):
    '''A linked or embedded image.'''
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
                 mime_type=None, **kwargs):
        '''
        Specify either the path or data argument.  If path is used and embed is
        True, the image file is embedded in a data URI.
        '''
        if path is None and data is None:
            raise ValueError('Either path or data arguments must be given')
        if embed:
            if mime_type is None and path is not None:
                ext = os.path.splitext(path)[1].lower()
                if ext in self.MIME_MAP:
                    mime_type = self.MIME_MAP[ext]
                else:
                    mime_type = self.MIME_DEFAULT
                    warnings.warn('Unknown image file type "{}"'.format(ext),
                                  Warning)
            if mime_type is None:
                mime_type = self.MIME_DEFAULT
                warnings.warn('Unspecified image type; assuming png', Warning)
        if data is not None:
            embed = True
        if embed and data is None:
            with open(path, 'rb') as f:
                data = f.read()
        if not embed:
            uri = path
        else:
            uri = url_encode.bytes_as_data_uri(data, mime=mime_type)
        super().__init__(x=x, y=y, width=width, height=height, xlink__href=uri,
                         **kwargs)

class Text(DrawingParentElement):
    '''A line or multiple lines of text, optionally placed along a path.

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill='red', font_size=20, letter_spacing=1.5.

    Useful SVG attributes:
    - text_anchor: start, middle, end
    - dominant_baseline: auto, central, middle, hanging, text-top, ...
    See https://developer.mozilla.org/en-US/docs/Web/SVG/Element/text

    CairoSVG bug with letter spacing text on a path: The first two letters are
    always spaced as if letter_spacing=1.
    '''
    TAG_NAME = 'text'
    has_content = True
    def __new__(cls, text, *args, path=None, id=None, _skip_check=False,
                **kwargs):
        # Check for the special case of multi-line text on a path
        # This is inconsistently implemented by renderers so we return a group
        # of single-line text on paths instead.
        if path is not None and not _skip_check:
            text, _ = cls._handle_text_argument(text, True)
            if len(text) > 1:
                # Special case
                g = Group(id=id)
                for i, line in enumerate(text):
                    subtext = [None] * len(text)
                    subtext[i] = line
                    g.append(Text(subtext, *args, path=path, _skip_check=True,
                                  **kwargs))
                return g
        return super().__new__(cls)
    def __init__(self, text, font_size, x=None, y=None, *, center=False,
                 line_height=1, line_offset=0, path=None, start_offset=None,
                 path_args=None, tspan_args=None, cairo_fix=True,
                 _skip_check=False, **kwargs):
        # Check argument requirements
        if path is None:
            if x is None or y is None:
                raise TypeError(
                        "__init__() missing required arguments: 'x' and 'y' "
                        "are required unless 'path' is specified")
        else:
            if x is not None or y is not None:
                raise TypeError(
                        "__init__() conflicting arguments: 'x' and 'y' "
                        "should not be used when 'path' is specified")
        if path_args is None:
            path_args = {}
        if start_offset is not None:
            path_args.setdefault('startOffset', start_offset)
        if tspan_args is None:
            tspan_args = {}
        on_path = path is not None

        text, single_line = self._handle_text_argument(
                text, force_multi=on_path)
        num_lines = len(text)

        # Text alignment
        if center:
            kwargs.setdefault('text_anchor', 'middle')
            if path is None and single_line:
                kwargs.setdefault('dominant_baseline', 'central')
            else:
                line_offset += 0.5
            line_offset -= line_height * (num_lines - 1) / 2
        # Text alignment on a path
        if on_path:
            if kwargs.get('text_anchor') == 'start':
                path_args.setdefault('startOffset', '0')
            elif kwargs.get('text_anchor') == 'middle':
                path_args.setdefault('startOffset', '50%')
            elif kwargs.get('text_anchor') == 'end':
                if cairo_fix and 'startOffset' not in path_args:
                    # Fix CairoSVG not drawing the last character with aligned
                    # right
                    tspan_args.setdefault('dx', -1)
                path_args.setdefault('startOffset', '100%')

        super().__init__(x=x, y=y, font_size=font_size, **kwargs)
        self._text_path = None
        if single_line:
            self.escaped_text = xml.escape(text[0])
        else:
            # Add elements for each line of text
            self.escaped_text = ''
            if path is None:
                # Text is an iterable
                for i, line in enumerate(text):
                    dy = '{}em'.format(line_offset if i == 0 else line_height)
                    self.append_line(line, x=x, dy=dy, **tspan_args)
            else:
                self._text_path = _TextPath(path, **path_args)
                assert sum(bool(line) for line in text) <= 1, (
                        'Logic error, __new__ should handle multi-line paths')
                for i, line in enumerate(text):
                    if not line:
                        continue
                    dy = '{}em'.format(line_offset + i*line_height)
                    tspan = TSpan(line, dy=dy, **tspan_args)
                    self._text_path.append(tspan)
                self.append(self._text_path)
    @staticmethod
    def _handle_text_argument(text, force_multi=False):
        # Handle multi-line text (contains '\n' or is a list of strings)
        if isinstance(text, str):
            single_line = '\n' not in text and not force_multi
            if single_line:
                text = (text,)
            else:
                text = tuple(text.splitlines())
        else:
            single_line = False
            text = tuple(text)
        return text, single_line
    def write_content(self, id_map, is_duplicate, output_file, dry_run):
        if dry_run:
            return
        output_file.write(self.escaped_text)
    def write_children_content(self, id_map, is_duplicate, output_file,
                               dry_run):
        children = self.all_children()
        for child in children:
            child.write_svg_element(id_map, is_duplicate, output_file, dry_run)
    def append_line(self, line, **kwargs):
        if self._text_path is not None:
            raise ValueError('appendLine is not supported for text on a path')
        self.append(TSpan(line, **kwargs))

class _TextPath(DrawingParentElement):
    TAG_NAME = 'textPath'
    has_content = True
    def __init__(self, path, **kwargs):
        super().__init__(xlink__href=path, **kwargs)

class _TextContainingElement(DrawingBasicElement):
    ''' A private parent class used for elements that only have plain text
        content. '''
    has_content = True
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.escaped_text = xml.escape(text)
    def write_content(self, id_map, is_duplicate, output_file, dry_run):
        if dry_run:
            return
        output_file.write(self.escaped_text)

class TSpan(_TextContainingElement):
    ''' A line of text within the Text element. '''
    TAG_NAME = 'tspan'

class Title(_TextContainingElement):
    '''A title element.

    This element can be appended with shape.append_title("Your title!"), which
    can be useful for adding a tooltip or on-hover text display to an element.
    '''
    TAG_NAME = 'title'

class Rectangle(DrawingBasicElement):
    '''A rectangle.

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    TAG_NAME = 'rect'
    def __init__(self, x, y, width, height, **kwargs):
        super().__init__(x=x, y=y, width=width, height=height, **kwargs)

class Circle(DrawingBasicElement):
    '''A circle.

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    TAG_NAME = 'circle'
    def __init__(self, cx, cy, r, **kwargs):
        super().__init__(cx=cx, cy=cy, r=r, **kwargs)

class Ellipse(DrawingBasicElement):
    '''An ellipse.

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    TAG_NAME = 'ellipse'
    def __init__(self, cx, cy, rx, ry, **kwargs):
        super().__init__(cx=cx, cy=cy, rx=rx, ry=ry, **kwargs)

class ArcLine(Circle):
    '''An arc.

    In most cases, use Arc instead of ArcLine.  ArcLine uses the
    stroke-dasharray SVG property to make the edge of a circle look like an arc.

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    def __init__(self, cx, cy, r, start_deg, end_deg, **kwargs):
        if end_deg - start_deg == 360:
            super().__init__(cx, cy, r, **kwargs)
            return
        start_deg, end_deg = (-end_deg) % 360, (-start_deg) % 360
        arc_deg = (end_deg - start_deg) % 360
        def arc_len(deg):
            return math.radians(deg) * r
        whole_len = 2 * math.pi * r
        if end_deg == start_deg:
            offset = 1
            dashes = "0 {}".format(whole_len+2)
        else:
            start_len = arc_len(start_deg)
            arc_len = arc_len(arc_deg)
            off_len = whole_len - arc_len
            offset = -start_len
            dashes = "{} {}".format(arc_len, off_len)
        super().__init__(cx, cy, r, stroke_dasharray=dashes,
                         stroke_dashoffset=offset, **kwargs)

class Path(DrawingBasicElement):
    '''An arbitrary path.

    Path Supports building an SVG path by calling instance methods corresponding
    to path commands.

    Complete descriptions of path commands:
    https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/d#path_commands

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    TAG_NAME = 'path'
    def __init__(self, d='', **kwargs):
        super().__init__(d=d, **kwargs)
    def append(self, command_str, *args):
        if len(self.args['d']) > 0:
            command_str = ' ' + command_str
        if len(args) > 0:
            command_str = command_str + ','.join(map(str, args))
        self.args['d'] += command_str
        return self
    def M(self, x, y):
        '''Start a new curve section from this point.'''
        return self.append('M', x, y)
    def m(self, dx, dy):
        '''Start a new curve section from this point (relative coordinates).'''
        return self.append('m', dx, dy)
    def L(self, x, y):
        '''Draw a line to this point.'''
        return self.append('L', x, y)
    def l(self, dx, dy):
        '''Draw a line to this point (relative coordinates).'''
        return self.append('l', dx, dy)
    def H(self, x):
        '''Draw a horizontal line to this x coordinate.'''
        return self.append('H', x)
    def h(self, dx):
        '''Draw a horizontal line to this relative x coordinate.'''
        return self.append('h', dx)
    def V(self, y):
        '''Draw a horizontal line to this y coordinate.'''
        return self.append('V', y)
    def v(self, dy):
        '''Draw a horizontal line to this relative y coordinate.'''
        return self.append('v', dy)
    def Z(self):
        '''Draw a line back to the previous m or M point.'''
        return self.append('Z')
    def C(self, cx1, cy1, cx2, cy2, ex, ey):
        '''Draw a cubic Bezier curve.'''
        return self.append('C', cx1, cy1, cx2, cy2, ex, ey)
    def c(self, cx1, cy1, cx2, cy2, ex, ey):
        '''Draw a cubic Bezier curve (relative coordinates).'''
        return self.append('c', cx1, cy1, cx2, cy2, ex, ey)
    def S(self, cx2, cy2, ex, ey):
        '''Draw a cubic Bezier curve, transitioning smoothly from the previous.
        '''
        return self.append('S', cx2, cy2, ex, ey)
    def s(self, cx2, cy2, ex, ey):
        '''Draw a cubic Bezier curve, transitioning smoothly from the previous
        (relative coordinates).
        '''
        return self.append('s', cx2, cy2, ex, ey)
    def Q(self, cx, cy, ex, ey):
        '''Draw a quadratic Bezier curve.'''
        return self.append('Q', cx, cy, ex, ey)
    def q(self, cx, cy, ex, ey):
        '''Draw a quadratic Bezier curve (relative coordinates).'''
        return self.append('q', cx, cy, ex, ey)
    def T(self, ex, ey):
        '''Draw a quadratic Bezier curve, transitioning soothly from the
        previous.
        '''
        return self.append('T', ex, ey)
    def t(self, ex, ey):
        '''Draw a quadratic Bezier curve, transitioning soothly from the
        previous (relative coordinates).
        '''
        return self.append('t', ex, ey)
    def A(self, rx, ry, rot, large_arc, sweep, ex, ey):
        '''Draw a circular or elliptical arc.

        See
        https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/d#elliptical_arc_curve
        '''
        return self.append('A', rx, ry, rot, int(bool(large_arc)),
                           int(bool(sweep)), ex, ey)
    def a(self, rx, ry, rot, large_arc, sweep, ex, ey):
        '''Draw a circular or elliptical arc (relative coordinates).

        See
        https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/d#elliptical_arc_curve
        '''
        return self.append('a', rx, ry, rot, int(bool(large_arc)),
                           int(bool(sweep)), ex, ey)
    def arc(self, cx, cy, r, start_deg, end_deg, cw=False, include_m=True,
            include_l=False):
        '''Draw a circular arc, controlled by center, radius, and start/end
        degrees.
        '''
        large_arc = (end_deg - start_deg) % 360 > 180
        start_rad, end_rad = start_deg*math.pi/180, end_deg*math.pi/180
        sx, sy = r*math.cos(start_rad), -r*math.sin(start_rad)
        ex, ey = r*math.cos(end_rad), -r*math.sin(end_rad)
        if include_l:
            self.L(cx+sx, cy+sy)
        elif include_m:
            self.M(cx+sx, cy+sy)
        return self.A(r, r, 0, large_arc ^ cw, cw, cx+ex, cy+ey)

class Lines(Path):
    '''A sequence of connected lines (or a polygon).

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    def __init__(self, sx, sy, *points, close=False, **kwargs):
        super().__init__(d='', **kwargs)
        self.M(sx, sy)
        assert len(points) % 2 == 0
        for i in range(len(points) // 2):
            self.L(points[2*i], points[2*i+1])
        if close:
            self.Z()

class Line(Lines):
    '''A simple line.

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    def __init__(self, sx, sy, ex, ey, **kwargs):
        super().__init__(sx, sy, ex, ey, close=False, **kwargs)

class Arc(Path):
    '''A circular arc.

    Additional keyword arguments are output as additional arguments to the SVG
    node e.g. fill="red", stroke="#ff4477", stroke_width=2.
    '''
    def __init__(self, cx, cy, r, start_deg, end_deg, cw=False, **kwargs):
        super().__init__(d='', **kwargs)
        self.arc(cx, cy, r, start_deg, end_deg, cw=cw, include_m=True)
