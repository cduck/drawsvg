from typing import Optional, Sequence, Union

from collections import defaultdict
import dataclasses

from . import elements
from .native_animation import SyncedAnimationConfig, AnimationHelperData


@dataclasses.dataclass(frozen=True)
class Context:
    '''Additional drawing configuration that can modify element's SVG output.'''
    invert_y: bool = False
    animation_config: Optional[SyncedAnimationConfig] = None

    def extra_prepost_drawing_elements(self, d):
        pre, post = [], []
        if self.animation_config:
            post.extend(self.animation_config.extra_drawing_elements(
                    d, context=self))
        return pre, post

    def extra_css(self, d):
        if self.animation_config:
            return self.animation_config.extra_css(d, context=self)
        return []

    def extra_javascript(self, d):
        if self.animation_config:
            return self.animation_config.extra_javascript(d, context=self)
        return []

    def extra_onload_js(self, d):
        if self.animation_config:
            return self.animation_config.extra_onload_js(d, context=self)
        return []

    def override_view_box(self, view_box):
        if self.invert_y:
            if isinstance(view_box, str):
                view_box = tuple(map(float, view_box.split()))
                return ' '.join(map(str, self.override_view_box(view_box)))
            x, y, w, h = view_box
            view_box = (x, -y-h, w, h)
        return view_box

    def is_attr_inverted(self, name):
        return self.invert_y and name in ('y', 'cy', 'y1', 'y2')

    def override_args(self, args):
        args = dict(args)
        if self.invert_y:
            for y_like_arg in ('cy', 'y1', 'y2'):
                if y_like_arg in args:
                    # Flip y for circle, ellipse, line, gradient, etc.
                    try:
                        args[y_like_arg] = -args[y_like_arg]
                    except TypeError:
                        pass
            if 'y' in args:
                # Flip y for most elements
                try:
                    args['y'] = -args['y']
                    if 'height' in args:
                        args['y'] -= args['height']
                except TypeError:
                    pass
            if 'viewBox' in args:
                # Flip y for SVG, marker, or other viewBox
                try:
                    args['viewBox'] = self.override_view_box(args['viewBox'])
                except (TypeError, ValueError):
                    pass
            if 'd' in args:
                # Flip y for paths
                try:
                    new_commands = []
                    for cmd in args['d'].split():
                        name = cmd[:1]
                        vals = [float(s) if '.' in s else int(s)
                                for s in  cmd[1:].split(',') if s]
                        if name in 'vV':
                            vals = [-y for y in vals]
                        elif name in 'hH':
                            pass
                        elif name in 'aA':
                            if len(vals) >= 7:
                                vals[6] = -vals[6]
                                vals[4] = int(bool(not vals[4]))
                        else:
                            vals[1::2] = [-y for y in vals[1::2]]
                        val_str = ','.join(map(str, vals))
                        new_commands.append(name + val_str)
                    args['d'] = ' '.join(new_commands)
                except (TypeError, ValueError):
                    pass
            if ('cx' in args and 'cy' in args and 'r' in args
                    and 'stroke-dashoffset' in args
                    and 'stroke-dasharray' in args):
                # Flip ArcLine (drawn with stroke-dasharray)
                try:
                    length = float(
                            args['stroke-dasharray'].split(maxsplit=1)[0])
                    offset = float(args['stroke-dashoffset'])
                    offset = length - offset
                    args['stroke-dashoffset'] = offset
                except KeyError: pass
                except (TypeError, ValueError, IndexError):
                    pass
                    raise
        return args

    def write_svg_document_args(self, d, args, output_file):
        '''Called by Drawing during SVG output of the <svg> tag.'''
        args['viewBox'] = self.override_view_box(args['viewBox'])
        onload_list = self.extra_onload_js(d)
        onload_list.extend(args.get('onload', '').split(';'))
        onload = ';'.join(onload_list)
        if onload:
            args['onload'] = onload
        self._write_tag_args(args, output_file)

    def _write_tag_args(self, args, output_file, id_map=None):
        '''Called by an element during SVG output of its tag.'''
        for k, v in args.items():
            if v is None: continue
            if isinstance(v, DrawingElement):
                mapped_id = v.id
                if id_map is not None and id(v) in id_map:
                    mapped_id = id_map[id(v)]
                if mapped_id is None:
                    continue
                if k == 'xlink:href':
                    v = '#{}'.format(mapped_id)
                else:
                    v = 'url(#{})'.format(mapped_id)
            output_file.write(' {}="{}"'.format(k,v))


@dataclasses.dataclass(frozen=True)
class LocalContext:
    context: Context
    element: 'DrawingElement'
    parent: Union['DrawingElement', 'Drawing']
    siblings: Sequence['DrawingElement'] = ()

    def write_tag_args(self, args, output_file, id_map=None):
        '''Called by an element during SVG output of its tag.'''
        if self.context.animation_config is not None:
            args = self.context.animation_config.override_args(args, self)
        self.context._write_tag_args(
                self.context.override_args(args), output_file, id_map=id_map)


class DrawingElement:
    '''Base class for drawing elements.

    Subclasses must implement write_svg_element.
    '''
    def write_svg_element(self, id_map, is_duplicate, output_file, lcontext,
                          dry_run, force_dup=False):
        raise NotImplementedError('Abstract base class')
    def get_svg_defs(self):
        return ()
    def get_linked_elems(self):
        return ()
    def write_svg_defs(self, id_map, is_duplicate, output_file, lcontext,
                       dry_run):
        for defn in self.get_svg_defs():
            local = LocalContext(lcontext.context, defn, self, ())
            if is_duplicate(defn):
                continue
            defn.write_svg_defs(
                    id_map, is_duplicate, output_file, local, dry_run)
            if defn.id is None:
                id_map[id(defn)]
            defn.write_svg_element(
                    id_map, is_duplicate, output_file, local, dry_run,
                    force_dup=True)
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
            self.args[normalize_attribute_name(k)] = v
        self.children = []
        self.ordered_children = defaultdict(list)
        self.animation_data = AnimationHelperData()
        self._cached_context = None
        self._cached_extra_children_with_context = None
    def check_children_allowed(self):
        if not self.has_content:
            raise RuntimeError(
                    '{} does not support children'.format(type(self)))
    def _extra_children_with_context_avoid_recompute(self, lcontext=None):
        if (self._cached_extra_children_with_context is not None
                and self._cached_context == lcontext.context):
            return self._cached_extra_children_with_context
        self._cached_context = lcontext.context
        self._cached_extra_children_with_context = (
                self.extra_children_with_context(lcontext))
        return self._cached_extra_children_with_context
    def extra_children_with_context(self, lcontext=None):
        return self.animation_data.children_with_context(lcontext)
    def all_children(self, lcontext=None):
        '''Return self.children and self.ordered_children as a single list.'''
        output = list(self.children)
        for z in sorted(self.ordered_children):
            output.extend(self.ordered_children[z])
        output.extend(
                self._extra_children_with_context_avoid_recompute(lcontext))
        return output
    @property
    def id(self):
        return self.args.get('id', None)
    def write_svg_element(self, id_map, is_duplicate, output_file, lcontext,
                          dry_run, force_dup=False):
        children = self.all_children(lcontext=lcontext)
        if dry_run:
            if is_duplicate(self) and self.id is None:
                id_map[id(self)]
            for elem in self.get_linked_elems():
                if elem.id is None:
                    id_map[id(elem.id)]
            if self.has_content:
                self.write_content(
                        id_map, is_duplicate, output_file, lcontext, dry_run)
            if children is not None and len(children):
                self.write_children_content(
                        id_map, is_duplicate, output_file, lcontext, dry_run)
            return
        if is_duplicate(self) and not force_dup:
            mapped_id = self.id
            if id_map is not None and id(self) in id_map:
                mapped_id = id_map[id(self)]
            output_file.write('<use xlink:href="#{}" />'.format(mapped_id))
            return
        output_file.write('<')
        output_file.write(self.TAG_NAME)
        override_args = self.args
        if id(self) in id_map:
            override_args = dict(override_args)
            override_args['id'] = id_map[id(self)]
        lcontext.write_tag_args(override_args, output_file, id_map)
        if not self.has_content and (children is None or len(children) == 0):
            output_file.write(' />')
        else:
            output_file.write('>')
            if self.has_content:
                self.write_content(
                        id_map, is_duplicate, output_file, lcontext, dry_run)
            if children is not None and len(children):
                self.write_children_content(
                        id_map, is_duplicate, output_file, lcontext, dry_run)
            output_file.write('</')
            output_file.write(self.TAG_NAME)
            output_file.write('>')
    def write_content(self, id_map, is_duplicate, output_file, lcontext,
                      dry_run):
        '''Override in a subclass to add data between the start and end tags.

        This will not be called if has_content is False.
        '''
        raise RuntimeError('This element has no content')
    def write_children_content(self, id_map, is_duplicate, output_file,
                               lcontext, dry_run):
        '''Override in a subclass to add data between the start and end tags.

        This will not be called if has_content is False.
        '''
        children = self.all_children(lcontext=lcontext)
        if dry_run:
            for child in children:
                local = LocalContext(lcontext.context, child, self, children)
                child.write_svg_element(
                        id_map, is_duplicate, output_file, local, dry_run)
            return
        output_file.write('\n')
        for child in children:
            local = LocalContext(lcontext.context, child, self, children)
            child.write_svg_element(
                    id_map, is_duplicate, output_file, local, dry_run)
            output_file.write('\n')
    def get_svg_defs(self):
        return [v for v in self.args.values()
                if isinstance(v, DrawingElement)]
    def write_svg_defs(self, id_map, is_duplicate, output_file, lcontext,
                       dry_run):
        super().write_svg_defs(
                id_map, is_duplicate, output_file, lcontext, dry_run)
        children = self.all_children(lcontext=lcontext)
        for child in children:
            local = LocalContext(lcontext.context, child, self, children)
            child.write_svg_defs(
                    id_map, is_duplicate, output_file, local, dry_run)
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
        self.children.append(elements.Title(text, **kwargs))
    def add_key_frame(self, time, animation_args=None, **attr_values):
        self._cached_extra_children_with_context = None
        self.animation_data.add_key_frame(
                time, animation_args=animation_args, **attr_values)
    def add_attribute_key_sequence(self, attr, times, values, *,
                                   animation_args=None):
        self._cached_extra_children_with_context = None
        self.animation_data.add_attribute_key_sequence(
                attr, times, values, animation_args=animation_args)


class DrawingParentElement(DrawingBasicElement):
    '''Base class for SVG elements that can have child nodes.'''
    has_content = True
    def __init__(self, children=(), ordered_children=None, **args):
        super().__init__(**args)
        self.children = list(children)
        if ordered_children is not None and len(ordered_children):
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
            if len(kwargs) > 0:
                raise ValueError('unexpected kwargs')
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
    def write_content(self, id_map, is_duplicate, output_file, lcontext,
                      dry_run):
        pass


def normalize_attribute_name(name):
    name = name.replace('__', ':')
    name = name.replace('_', '-')
    if name[-1] == '-':
        name = name[:-1]
    return name
