import time

from ..drawing import Drawing
from .drawing_widget import DrawingWidget


class AsyncAnimation(DrawingWidget):
    '''AsyncAnimation is a Jupyter notebook widget for asynchronously displaying
    an animation.

    Example:
        # Jupyter cell 1:
        widget = AsyncAnimation(fps=10)
        widget
        # [Animation is displayed here]

        # Jupyter cell 2:
        global_variable = 'a'
        @widget.set_draw_frame  # Animation above is automatically updated
        def draw_frame(secs=0):
            # Draw something...
            d = draw.Drawing(300, 40)
            d.append(draw.Text(global_variable, 20, 0, 10))
            d.append(draw.Text(str(secs), 20, 30, 10))
            return d

        # Jupyter cell 3:
        global_variable = 'b'  # Animation above now displays 'b'

    Attributes:
        fps: The animation frame rate (frames per second).
        draw_frame: A function that takes a single argument (animation time) and
            returns a Drawing.
        paused: While True, the animation will not run.  Only the current frame
            will be shown.
        disable: While True, the widget will not be interactive and the
            animation will not update.
        click_pause: If True, clicking the drawing will pause or resume the
            animation.
        mousemove_pause: If True, moving the mouse up across the drawing will
            pause the animation and moving the mouse down will resume it.
        mousemove_y_threshold: Controls the sensitivity of mousemove_pause in
            web browser pixels.
    '''

    def __init__(self, fps=10, draw_frame=None, *, paused=False, disable=False,
                 click_pause=True, mousemove_pause=False,
                 mousemove_y_threshold=10):
        self._fps = fps
        self._paused = paused
        if draw_frame is None:
            def draw_frame(secs):
                return Drawing(0, 0)
        self._draw_frame = draw_frame
        self._last_secs = 0
        self.click_pause = click_pause
        self.mousemove_pause = mousemove_pause
        self.mousemove_y_threshold = mousemove_y_threshold
        self._start_time = 0
        self._stop_time = 0
        self._y_loc = 0
        self._y_max = 0
        self._y_min = 0
        if self._paused:
            frame_delay = -1
        else:
            frame_delay = 1000 // self._fps
            self._start_time = time.monotonic()
        initial_drawing = self.draw_frame(0)
        super().__init__(initial_drawing, throttle=True, disable=disable,
                         frame_delay=frame_delay)

        # Register callbacks
        @self.mousedown
        def mousedown(self, x, y, info):
            if not self.click_pause:
                return
            self._y_min = self._y_max = self._y_loc
            self.paused = not self.paused

        @self.mousemove
        def mousemove(self, x, y, info):
            self._y_loc += info['movementY']
            if not self.mousemove_pause:
                self._y_min = self._y_max = self._y_loc
                return
            self._y_max = max(self._y_max, self._y_loc)
            self._y_min = min(self._y_min, self._y_loc)
            thresh = self.mousemove_y_threshold
            invert = thresh < 0
            thresh = max(0.01, abs(thresh))
            down_triggered = self._y_loc - self._y_min >= thresh
            up_triggered = self._y_max - self._y_loc >= thresh
            if down_triggered:
                self._y_min = self._y_loc
            if up_triggered:
                self._y_max = self._y_loc
            if invert:
                down_triggered, up_triggered = up_triggered, down_triggered
            if down_triggered:
                self.paused = False
            if up_triggered:
                self.paused = True

        @self.timed
        def timed(self, info):
            secs = time.monotonic() - self._start_time
            self.drawing = self.draw_frame(secs)
            self._last_secs = secs

        @self.on_exception
        def on_exception(self, e):
            self.paused = True

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, new_fps):
        self._fps = new_fps
        if self.paused:
            return
        self.frame_delay = 1000 // self._fps

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, new_paused):
        if bool(self._paused) == bool(new_paused):
            return
        self._paused = new_paused
        if self._paused:
            self.frame_delay = -1
            self._stop_time = time.monotonic()
        else:
            self._start_time += time.monotonic() - self._stop_time
            self.frame_delay = 1000 // self._fps

    @property
    def draw_frame(self):
        return self._draw_frame

    @draw_frame.setter
    def draw_frame(self, new_draw_frame):
        self._draw_frame = new_draw_frame
        if self.paused:
            # Redraw if paused
            self.drawing = self._draw_frame(self._last_secs)

    def set_draw_frame(self, new_draw_frame):
        self.draw_frame = new_draw_frame
        return new_draw_frame
