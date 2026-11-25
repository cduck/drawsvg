import pytest

np = pytest.importorskip('numpy')
pytest.importorskip('imageio')

from drawsvg.video import render_spritesheet


@pytest.mark.parametrize('container', [list, tuple])
def test_padding_a_spritesheet_preserves_the_input_frames(container):
    frames = container(
        np.full((2, 3, 3), color, dtype=np.uint8) for color in (10, 20, 30))
    originals = list(frames)

    sheet = render_spritesheet(frames, row_length=2)
    assert sheet.shape == (4, 6, 3)
    for tile, color in [
            (sheet[:2, :3], 10), (sheet[:2, 3:], 20),
            (sheet[2:, :3], 30), (sheet[2:, 3:], 255)]:
        np.testing.assert_array_equal(tile, np.full((2, 3, 3), color))

    assert len(frames) == len(originals)
    assert all(frame is original for frame, original in zip(frames, originals))
    # Reusing the same frames with a different layout must not export padding.
    assert render_spritesheet(frames, row_length=3).shape == (2, 9, 3)
