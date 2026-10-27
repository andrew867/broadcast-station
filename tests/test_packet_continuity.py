import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('packet_continuity',Path(__file__).parents[1]/'deploy/packet-continuity.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_historical_audio_gap_is_distinct_from_clean_video():
    s=module.PacketStats()
    for n in range(4):s.add('video',n/30,n)
    s.add('audio',87.082,100);s.add('audio',92.095,105)
    assert s.streams['video']['large_gaps']==0
    assert s.streams['audio']['large_gaps']==1
    assert abs(s.events[0]['seconds']-5.013)<.00001

def test_reconnect_epoch_is_not_counted_as_a_fake_timestamp_gap():
    s=module.PacketStats();s.add('audio',100,100)
    s.reset_connection();s.add('audio',0,110);s.add('audio',.021333,111)
    assert s.streams['audio']['nonincreasing']==0
    s.add('audio',.021333,112)
    assert s.streams['audio']['nonincreasing']==1
    before=s.streams['audio']['packets'];s.add('audio',float('nan'),113)
    assert s.streams['audio']['packets']==before
