import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('youtube_relay',Path(__file__).parents[1]/'deploy/youtube-relay.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_clock_progress_does_not_hide_frozen_video():
    p=module.Progress(0);p.update({'frame':'10','out_time_us':'1000'},1)
    p.update({'frame':'10','out_time_us':'2000'},44)
    assert not p.stalled(45,45) and p.stalled(47,45)
    p.update({'frame':'11','out_time_us':'3000'},48);assert not p.stalled(49,45)

def test_video_progress_does_not_hide_frozen_media_clock():
    p=module.Progress(0);p.update({'frame':'10','out_time_us':'1000'},1)
    p.update({'frame':'20','out_time_us':'1000'},44)
    assert p.stalled(47,45)
    p.update({'frame':'N/A','out_time_us':'N/A'},48);assert p.stalled(49,45)

def test_arguments_preserve_existing_media_settings_and_hide_secrets():
    original=['ffmpeg','-i','rtmp://127.0.0.1/skycam-program','-c','copy','-c:a','aac','-f','flv','rtmp://example.test/live/private-key']
    before=original.copy();args=module.supervised_args(original)
    assert args.count('-rw_timeout')==2 and args[-1]==original[-1] and '-c:a' in args
    assert 'private-key' not in module.redact('Error '+original[-1])
    assert original==before
