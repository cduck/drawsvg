from collections import defaultdict
import dataclasses

from . import elements


@dataclasses.dataclass
class Context:
    '''Additional drawing configuration that can modify element's SVG output.'''
    invert_y: bool = False

    def drawing_creation_hook(self, d):
        '''Called by Drawing on initialization.'''
        ...

    def override_view_box(self, view_box):
        if self.invert_y:
            if isinstance(view_box, str):
                view_box = tuple(map(float, view_box.split()))
                return ' '.join(map(str, self.override_view_box(view_box)))
            x, y, w, h = view_box
            view_box = (x, -y-h, w, h)
        return view_box

    def override_args(self, args):
        args = dict(args)
        if self.invert_y:
            if 'cy' in args:
                # Flip y for circle and ellipse
                try:
                    args['cy'] = -args['cy']
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

    def write_svg_document_args(self, args, output_file):
        '''Called by Drawing during SVG output of the <svg> tag.'''
        args['viewBox'] = self.override_view_box(args['viewBox'])
        self._write_tag_args(args, output_file)

    def write_tag_args(self, args, output_file, id_map=None):
        '''Called by an element during SVG output of its tag.'''
        self._write_tag_args(
                self.override_args(args), output_file, id_map=id_map)

    def _write_tag_args(self, args, output_file, id_map=None):
        '''Called by an element during SVG output of its tag.'''
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
    def write_svg_element(self, id_map, is_duplicate, output_file, context,
                          dry_run, force_dup=False):
        raise NotImplementedError('Abstract base class')
    def get_svg_defs(self):
        return ()
    def get_linked_elems(self):
        return ()
    def write_svg_defs(self, id_map, is_duplicate, output_file, context,
                       dry_run):
        for defn in self.get_svg_defs():
            if is_duplicate(defn):
                continue
            defn.write_svg_defs(
                    id_map, is_duplicate, output_file, context, dry_run)
            if defn.id is None:
                id_map[id(defn)]
            defn.write_svg_element(
                    id_map, is_duplicate, output_file, context, dry_run,
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
    def write_svg_element(self, id_map, is_duplicate, output_file, context,
                          dry_run, force_dup=False):
        children = self.all_children()
        if dry_run:
            if is_duplicate(self) and self.id is None:
                id_map[id(self)]
            for elem in self.get_linked_elems():
                if elem.id is None:
                    id_map[id(elem.id)]
            if self.has_content:
                self.write_content(
                        id_map, is_duplicate, output_file, context, dry_run)
            if children:
                self.write_children_content(
                        id_map, is_duplicate, output_file, context, dry_run)
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
        context.write_tag_args(override_args, output_file, id_map)
        if not self.has_content and not children:
            output_file.write(' />')
        else:
            output_file.write('>')
            if self.has_content:
                self.write_content(
                        id_map, is_duplicate, output_file, context, dry_run)
            if children:
                self.write_children_content(
                        id_map, is_duplicate, output_file, context, dry_run)
            output_file.write('</')
            output_file.write(self.TAG_NAME)
            output_file.write('>')
    def write_content(self, id_map, is_duplicate, output_file, context,
                      dry_run):
        '''Override in a subclass to add data between the start and end tags.

        This will not be called if has_content is False.
        '''
        raise RuntimeError('This element has no content')
    def write_children_content(self, id_map, is_duplicate, output_file, context,
                               dry_run):
        '''Override in a subclass to add data between the start and end tags.

        This will not be called if has_content is False.
        '''
        children = self.all_children()
        if dry_run:
            for child in children:
                child.write_svg_element(
                        id_map, is_duplicate, output_file, context, dry_run)
            return
        output_file.write('\n')
        for child in children:
            child.write_svg_element(id_map, is_duplicate, output_file, context, dry_run)
            output_file.write('\n')
    def get_svg_defs(self):
        return [v for v in self.args.values()
                if isinstance(v, DrawingElement)]
    def write_svg_defs(self, id_map, is_duplicate, output_file, context,
                       dry_run):
        super().write_svg_defs(
                id_map, is_duplicate, output_file, context, dry_run)
        for child in self.all_children():
            child.write_svg_defs(
                    id_map, is_duplicate, output_file, context, dry_run)
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
    def write_content(self, id_map, is_duplicate, output_file, context,
                      dry_run):
        pass
