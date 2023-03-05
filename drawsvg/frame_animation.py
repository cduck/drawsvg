import time

from . import video


class FrameAnimation:
    def __init__(self, draw_func=None, callback=None):
        self.frames = []
        if draw_func is None:
            draw_func = lambda d:d
        self.draw_func = draw_func
        if callback is None:
            callback = lambda d:None
        self.callback = callback

    def append_frame(self, frame):
        self.frames.append(frame)
        self.callback(frame)

    def draw_frame(self, *args, **kwargs):
        frame = self.draw_func(*args, **kwargs)
        self.append_frame(frame)
        return frame

    def save_video(self, file, **kwargs):
        video.save_video(self.frames, file, **kwargs)

    def save_spritesheet(self, file, **kwargs):
        video.save_spritesheet(self.frames, file, **kwargs)


class FrameAnimationContext:
    def __init__(self, draw_func=None, out_file=None,
                 jupyter=False, spritesheet=False, pause=False,
                 clear=True, delay=0, disable=False, video_args=None,
                 _patch_delay=0.05):
        self.jupyter = jupyter
        self.spritesheet = spritesheet
        self.disable = disable
        if self.jupyter and not self.disable:
            from IPython import display
            self._jupyter_clear_output = display.clear_output
            self._jupyter_display = display.display
            callback = self.draw_jupyter_frame
        else:
            callback = None
        self.anim = FrameAnimation(draw_func, callback=callback)
        self.out_file = out_file
        self.pause = pause
        self.clear = clear
        self.delay = delay
        if video_args is None:
            video_args = {}
        self.video_args = video_args
        self._patch_delay = _patch_delay

    def draw_jupyter_frame(self, frame):
        if self.clear:
            self._jupyter_clear_output(wait=True)
        self._jupyter_display(frame)
        if self.pause:
            # Patch.  Jupyter sometimes clears the input field otherwise.
            time.sleep(self._patch_delay)
            input('Next?')
        elif self.delay != 0:
            time.sleep(self.delay)

    def __enter__(self):
        return self.anim

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is None:
            # No error
            if self.out_file is not None and not self.disable:
                if self.spritesheet:
                    self.anim.save_spritesheet(self.out_file, **self.video_args)
                else:
                    self.anim.save_video(self.out_file, **self.video_args)


def frame_animate_video(out_file, draw_func=None, jupyter=False, **video_args):
    '''
    Returns a context manager that stores frames and saves a video when the
    context exits.

    Example:
    ```
    with frame_animate_video('video.mp4') as anim:
        while True:
            ...
            anim.draw_frame(...)
    ```
    '''
    return FrameAnimationContext(draw_func=draw_func, out_file=out_file,
                                 jupyter=jupyter, video_args=video_args)

def frame_animate_spritesheet(out_file, draw_func=None, jupyter=False,
                              **video_args):
    '''
    Returns a context manager that stores frames and saves a spritesheet when
    the context exits.

    Example:
    ```
    with frame_animate_spritesheet('sheet.png', row_length=10) as anim:
        while True:
            ...
            anim.draw_frame(...)
    ```
    '''
    return FrameAnimationContext(draw_func=draw_func, out_file=out_file,
                                jupyter=jupyter, spritesheet=True,
                                video_args=video_args)


def frame_animate_jupyter(draw_func=None, pause=False, clear=True, delay=0.1,
                          **kwargs):
    '''
    Returns a context manager that displays frames in a Jupyter notebook.

    Example:
    ```
    with frame_animate_jupyter(delay=0.5) as anim:
        while True:
            ...
            anim.draw_frame(...)
    ```
    '''
    return FrameAnimationContext(draw_func=draw_func, jupyter=True, pause=pause,
                                 clear=clear, delay=delay, **kwargs)
