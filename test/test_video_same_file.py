import shutil

from drawsvg.video import RasterVideo


def test_saving_a_file_backed_video_to_its_source_preserves_the_file(tmp_path):
    path = tmp_path / 'video.mp4'
    payload = b'video data to preserve'
    path.write_bytes(payload)
    video = RasterVideo(video_file=path)

    try:
        video.save_video(path)
    except shutil.SameFileError:
        pass

    assert path.read_bytes() == payload


def test_saving_file_backed_and_in_memory_videos(tmp_path):
    source = tmp_path / 'source.mp4'
    target = tmp_path / 'target.mp4'
    payload = b'complete video bytes'
    source.write_bytes(payload)
    target.write_bytes(b'an older, longer destination video')

    RasterVideo(video_file=source).save_video(target)
    assert source.read_bytes() == target.read_bytes() == payload

    RasterVideo(video_data=b'new bytes').save_video(target)
    assert target.read_bytes() == b'new bytes'
