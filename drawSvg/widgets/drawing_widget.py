from ipywidgets import widgets
from traitlets import Unicode, Bool, Int


# Register front end javascript
from IPython import display
from . import drawing_javascript
display.display(display.Javascript(drawing_javascript.javascript))
del drawing_javascript


class DrawingWidget(widgets.DOMWidget):
    _view_name = Unicode('DrawingView').tag(sync=True)
    _view_module = Unicode('drawingview').tag(sync=True)
    _view_module_version = Unicode('0.1.0').tag(sync=True)
    _image = Unicode().tag(sync=True)
    _mousemove_blocked = Int(0).tag(sync=True)
    _frame_blocked = Int(0).tag(sync=True)
    throttle = Bool(True).tag(sync=True)
    disable = Bool(False).tag(sync=True)
    frame_delay = Int(-1).tag(sync=True)

    def __init__(self, drawing, throttle=True, disable=False, frame_delay=-1):
        '''
        DrawingWidget is an interactive Jupyter notebook widget.  It works
        similarly to displaying a Drawing as a cell output but DrawingWidget
        can register callbacks for user mouse events.  Within a callback modify
        the drawing then call .refresh() to update the output in real time.

        Arguments:
            drawing: The initial Drawing to display.  Call .refresh() after
                modifying or just assign a new Drawing.
            throttle: If True, limit the rate of mousemove events.  For drawings
                with many elements, this will significantly reduce lag.
            disable: While True, mouse events will be disabled.
            frame_delay: If greater than or equal to zero, a timed callback will
                occur frame_delay milliseconds after the previous drawing
                update.
        '''
        super().__init__()
        self.throttle = throttle
        self.disable = disable
        self.frame_delay = frame_delay
        self.drawing = drawing
        self.mousedown_callbacks = []
        self.mousemove_callbacks = []
        self.mouseup_callbacks = []
        self.timed_callbacks = []
        self.exception_callbacks = []

        self.on_msg(self._receive_msg)

    @property
    def drawing(self):
        return self._drawing

    @drawing.setter
    def drawing(self, drawing):
        self._drawing = drawing
        self.refresh()

    def refresh(self):
        '''
        Redraw the displayed output with the current value of self.drawing.
        '''
        self._image = self.drawing.asSvg()

    def _receive_msg(self, _, content, buffers):
        if not isinstance(content, dict):
            return
        name = content.get('name')
        callbacks = {
            'mousedown': self.mousedown_callbacks,
            'mousemove': self.mousemove_callbacks,
            'mouseup': self.mouseup_callbacks,
            'timed': self.timed_callbacks,
        }.get(name, ())
        try:
            if callbacks:
                if name == 'timed':
                    self._call_handlers(callbacks, content)
                else:
                    self._call_handlers(callbacks, content.get('x'),
                                        content.get('y'), content)
        except BaseException as e:
            suppress = any(
                handler(self, e)
                for handler in self.exception_callbacks
            )
            if not suppress:
                raise
        finally:
            if name == 'timed':
                self._frame_blocked += 1
            else:
                self._mousemove_blocked += 1


    def mousedown(self, handler, remove=False):
        '''
        Register (or unregister) a handler for the mousedown event.

        Arguments:
            remove: If True, unregister, otherwise register.
        '''
        self.on_msg
        self._register_handler(
            self.mousedown_callbacks, handler, remove=remove)

    def mousemove(self, handler, remove=False):
        '''
        Register (or unregister) a handler for the mousemove event.

        Arguments:
            remove: If True, unregister, otherwise register.
        '''
        self._register_handler(
            self.mousemove_callbacks, handler, remove=remove)

    def mouseup(self, handler, remove=False):
        '''
        Register (or unregister) a handler for the mouseup event.

        Arguments:
            remove: If True, unregister, otherwise register.
        '''
        self._register_handler(
            self.mouseup_callbacks, handler, remove=remove)

    def timed(self, handler, remove=False):
        '''
        Register (or unregister) a handler for the timed event.

        Arguments:
            remove: If True, unregister, otherwise register.
        '''
        self._register_handler(
            self.timed_callbacks, handler, remove=remove)

    def on_exception(self, handler, remove=False):
        '''
        Register (or unregister) a handler for exceptions in other handlers.

        If any handler returns True, the exception is suppressed.

        Arguments:
            remove: If True, unregister, otherwise register.
        '''
        self._register_handler(
            self.exception_callbacks, handler, remove=remove)

    def _register_handler(self, callback_list, handler, remove=False):
        if remove:
            callback_list.remove(handler)
        else:
            callback_list.append(handler)

    def _call_handlers(self, callback_list, *args, **kwargs):
        for callback in callback_list:
            callback(self, *args, **kwargs)
