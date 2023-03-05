import base64
import shutil
import tempfile

def delay_import_np_imageio():
    try:
        import numpy as np
        import imageio
    except ImportError as e:
        raise ImportError(
            'Optional dependencies not installed. '
            'Install with `python3 -m pip install "drawsvg[all]"` '
            'or `python3 -m pip install "drawsvg[raster]"`. '
            'See https://github.com/cduck/drawsvg#full-feature-install '
            'for more details.'
        ) from e
    return np, imageio

from .url_encode import bytes_as_data_uri


class RasterVideo:
    def __init__(self, video_data=None, video_file=None, *, _file_handle=None,
                 mime_type='video/mp4'):
        self.video_data = video_data
        self.video_file = video_file
        self._file_handle = _file_handle
        self.mime_type = mime_type
    def save_video(self, fname):
        with open(fname, 'wb') as f:
            if self.video_file is not None:
                with open(self.video_file, 'rb') as source:
                    shutil.copyfileobj(source, f)
            else:
                f.write(self.video_data)
    @staticmethod
    def from_frames(svg_or_raster_frames, to_file=None, fps=10, *,
                    mime_type='video/mp4', file_type=None, _file_handle=None,
                    video_args=None, verbose=False):
        if file_type is None:
            file_type = mime_type.split('/')[-1]
        if to_file is None:
            # Create temp file for video
            _file_handle = tempfile.NamedTemporaryFile(suffix='.'+file_type)
            to_file = _file_handle.name
        if video_args is None:
            video_args = {}
        if file_type == 'gif':
            video_args.setdefault('duration', 1/fps)
        else:
            video_args.setdefault('fps', fps)
        save_video(
                svg_or_raster_frames, to_file, format=file_type,
                verbose=verbose, **video_args)
        return RasterVideo(
                video_file=to_file, _file_handle=_file_handle,
                mime_type=mime_type)
    def _repr_png_(self):
        if self.mime_type.startswith('image/'):
            return self._as_bytes()
        return None
    def _repr_html_(self):
        data_uri = self.as_data_uri()
        if self.mime_type.startswith('video/'):
            return (f'<video controls style="max-width:100%">'
                    f'<source src="{data_uri}" type="{self.mime_type}">'
                    f'Video unsupported.</video>')
        return None
    def _repr_mimebundle_(self, include=None, exclude=None):
        b64 = base64.b64encode(self._as_bytes())
        return {self.mime_type: b64}, {}
    def as_data_uri(self):
        return bytes_as_data_uri(self._as_bytes(), mime=self.mime_type)
    def _as_bytes(self):
        if self.video_data:
            return self.video_data
        else:
            try:
                with open(self.video_file, 'rb') as f:
                    return f.read()
            except TypeError:
                self.video_file.seek(0)
                return self.video_file.read()


def render_svg_frames(frames, align_bottom=False, align_right=False,
                      bg=(255,)*4, verbose=False, **kwargs):
    np, imageio = delay_import_np_imageio()
    if verbose:
        print(f'Rendering {len(frames)} frames: ', end='', flush=True)
    arr_frames = []
    for i, f in enumerate(frames):
        if verbose:
            print(f'{i} ', end='', flush=True)
        if hasattr(f, 'rasterize'):
            png_data = f.rasterize().png_data
        elif hasattr(f, 'png_data'):
            png_data = f.png_data
        else:
            png_data = f
        im = imageio.imread(png_data)
        arr_frames.append(im)
    max_width = max(map(lambda arr:arr.shape[1], arr_frames))
    max_height = max(map(lambda arr:arr.shape[0], arr_frames))

    def mod_frame(arr):
        new_arr = np.zeros((max_height, max_width) + arr.shape[2:],
                           dtype=arr.dtype)
        new_arr[:,:] = bg[:new_arr.shape[-1]]
        if align_bottom:
            slice0 = slice(-arr.shape[0], None)
        else:
            slice0 = slice(None, arr.shape[0])
        if align_right:
            slice1 = slice(-arr.shape[1], None)
        else:
            slice1 = slice(None, arr.shape[1])
        new_arr[slice0, slice1] = arr
        return new_arr
    return list(map(mod_frame, arr_frames))

def save_video(frames, file, verbose=False, **kwargs):
    '''
    Save a series of drawings as a GIF or video.

    Arguments:
        frames: A list of `Drawing`s or a list of `numpy.array`s.
        file: File name or file like object to write the video to.  The
            extension determines the output format.
        align_bottom: If frames are different sizes, align the bottoms of each
            frame in the video.
        align_right: If frames are different sizes, align the right edge of each
            frame in the video.
        bg: If frames are different sizes, fill the background with this color.
            (default is white: (255, 255, 255, 255))
        duration: If writing a GIF, sets the duration of each frame.
        fps: If writing a video, sets the frame rate in FPS.
        **kwargs: Other arguments to imageio.mimsave().

    '''
    np, imageio = delay_import_np_imageio()
    if not isinstance(frames[0], np.ndarray):
        frames = render_svg_frames(frames, verbose=verbose, **kwargs)
    kwargs.pop('align_bottom', None)
    kwargs.pop('align_right', None)
    kwargs.pop('bg', None)
    if verbose:
        print()
        print(f'Converting to video')
    imageio.mimsave(file, frames, **kwargs)

def render_spritesheet(frames, row_length=None, verbose=False, **kwargs):
    '''
    Save a series of drawings as a bitmap spritesheet

    Arguments:
        frames: A list of `Drawing`s or a list of `numpy.array`s.
        row_length: The length (in frames) of one row in the spritesheet.
            If not provided, all frames go on one row.
        align_bottom: If frames are different sizes, align the bottoms of each
            frame in the video.
        align_right: If frames are different sizes, align the right edge of each
            frame in the video.
        bg: If frames are different sizes, fill the background with this color.
            (default is white: (255, 255, 255, 255))
        **kwargs: Other arguments to imageio.imsave().

    '''
    np, _ = delay_import_np_imageio()
    if not isinstance(frames[0], np.ndarray):
        frames = render_svg_frames(frames, verbose=verbose, **kwargs)
    kwargs.pop('align_bottom', None)
    kwargs.pop('align_right', None)
    bg = kwargs.pop('bg', (255, 255, 255, 255))

    cols = row_length if row_length is not None else len(frames)
    rows = (len(frames) - 1) // cols + 1

    if rows * cols > len(frames):  # Unfilled final row
        empty_frame = np.zeros(frames[0].shape, dtype=frames[0].dtype)
        empty_frame[..., :] = bg[:empty_frame.shape[-1]]
        frames.extend([empty_frame] * (rows * cols - len(frames)))

    block_arrangement = []
    for row in range(rows):
        next_row_end = (row+1)*cols
        block_arrangement.append([
            [frame] for frame in frames[row*cols:next_row_end]
        ])

    spritesheet = np.block(block_arrangement)
    return spritesheet

def save_spritesheet(frames, file, row_length=None, verbose=False, **kwargs):
    '''
    Save a series of drawings as a bitmap spritesheet

    Arguments:
        frames: A list of `Drawing`s or a list of `numpy.array`s.
        file: File name or file like object to write the spritesheet to.  The
            extension determines the output format.
        row_length: The length (in frames) of one row in the spritesheet.
            If not provided, all frames go on one row.
        align_bottom: If frames are different sizes, align the bottoms of each
            frame in the video.
        align_right: If frames are different sizes, align the right edge of each
            frame in the video.
        bg: If frames are different sizes, fill the background with this color.
            (default is white: (255, 255, 255, 255))
        **kwargs: Other arguments to imageio.imsave().

    '''
    _, imageio = delay_import_np_imageio()
    spritesheet = render_spritesheet(
            frames, row_length=row_length, verbose=verbose, **kwargs)
    kwargs.pop('align_bottom', None)
    kwargs.pop('align_right', None)
    kwargs.pop('bg', None)
    imageio.imsave(file, spritesheet, **kwargs)
