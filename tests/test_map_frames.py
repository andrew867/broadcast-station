from PIL import Image, ImageDraw
from skycam.map_renderer import MapRenderer
from skycam import playout


def test_map_frame_is_lossless_and_old_frames_stay_bounded(tmp_path, monkeypatch):
    source = Image.new('RGBA', (1920, 1080), (12, 25, 34, 255))
    ImageDraw.Draw(source).rectangle((20, 20, 600, 100), fill=(240, 250, 220, 190))
    renderer = MapRenderer(tmp_path, lambda: {'healthy': True})
    renderer.base = source
    monkeypatch.setattr(renderer, 'basemap', lambda: None)
    monkeypatch.setattr(renderer, 'draw', lambda data: (source, 2))
    monkeypatch.setattr(playout, 'ENABLED', True)
    commands = []
    monkeypatch.setattr(playout, 'command', commands.append)
    monkeypatch.setattr(playout, 'heartbeat', lambda scene: None)
    # Migration cleanup must also remove retained frames in the old format.
    (renderer.frames/'frame-1.bmp').write_bytes(b'old fixture')
    for _ in range(6): renderer.tick()
    frames = list(renderer.frames.glob('frame-*.*'))
    assert len(frames) == 4 and all(p.suffix == '.png' for p in frames)
    with Image.open(frames[-1]) as loaded:
        assert loaded.convert('RGBA').tobytes() == source.tobytes()
    assert frames[-1].stat().st_size < 1920*1080*4/10
    assert any('.png"' in cmd for cmd in commands)
    assert (renderer.frames/'preview.jpg').is_file()
    assert renderer.status['aircraft_in_view'] == 2
