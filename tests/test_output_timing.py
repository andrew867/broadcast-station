import pytest
from skycam.output_timing import program_fps,transition_frames

def test_transition_duration_is_preserved_for_both_profiles():
    assert transition_frames(30,30)==15
    assert transition_frames(30,60)==30
    assert transition_frames(0,30)==0

def test_native_profile_is_authoritative_and_unknown_format_is_rejected(tmp_path):
    p=tmp_path/'config.xml'
    p.write_text('<configuration><channels><channel><video-mode>2160p3000</video-mode></channel></channels></configuration>')
    assert program_fps(p)==30
    p.write_text(p.read_text().replace('2160p3000','2160p6000'));assert program_fps(p)==60
    p.write_text(p.read_text().replace('2160p6000','unknown'))
    with pytest.raises(ValueError):program_fps(p)

@pytest.mark.parametrize('mode,expected', [('1080p3000','1920x1080p30'),('2160p3000','3840x2160p30'),('2160p6000','3840x2160p60')])
def test_status_format_matches_configured_output(mode,expected):
    from skycam.output_timing import output_format
    assert output_format(mode)==expected


@pytest.mark.parametrize('mode,clock,encoded', [('720p3000',30,30),('720p6000',60,60),('1080i5994',60000/1001,30000/1001)])
def test_fallback_clock_and_encoder_cadence(mode,clock,encoded):
    from skycam.output_timing import clock_fps,encoded_fps,publishing_video
    from skycam.station_config import StationConfig
    from tools.station_config import engine_config
    from pathlib import Path
    import xml.etree.ElementTree as ET
    config=StationConfig(output={'profile':mode,'encoder':'libx264'})
    xml=ET.fromstring(engine_config(config,Path(__file__).parents[1]/'deploy/casparcg.config'))
    assert xml.findtext('./channels/channel/video-mode')==mode
    assert clock_fps(mode)==clock and encoded_fps(mode)==encoded
    assert abs(transition_frames(60,clock)/clock-1)<.02
    if mode=='1080i5994':
        assert all(c.findtext('video-mode').endswith('5994') for c in xml.findall('./channels/channel'))
        assert 'tinterlace=mode=interleave_top' in publishing_video(mode)[0]
        assert '+ilme+ildct' in publishing_video(mode)[1]
        with pytest.raises(ValueError):StationConfig(output={'profile':mode,'publish':True,'encoder':'h264_nvenc'})
