from tools.check_program_recording import cadence,coverage


def test_late_audio_is_not_hidden_by_steady_packet_cadence():
    video={'first_timestamp':.633,'last_timestamp':59.967}
    audio={'first_timestamp':3.689,'last_timestamp':59.988}
    assert not coverage(video,audio)['passed']
    audio['first_timestamp']=0
    assert coverage(video,audio)['passed']
    audio['last_timestamp']=55
    assert not coverage(video,audio)['passed']


def packets(kind,times,duration):
    return [{'codec_type':kind,'pts_time':str(t),'duration_time':str(duration)} for t in times]


def test_video_reports_missing_picture_intervals_and_reordered_pts():
    normal=packets('video',[0,2/30,1/30,3/30],1/30)
    assert cadence(normal,'video')['passed']
    damaged=normal+packets('video',[1],1/30)
    result=cadence(damaged,'video')
    assert not result['passed'] and result['large_gaps']==1
    assert result['largest_gap_seconds']==.9


def test_audio_uses_packet_duration_and_detects_reset_or_gap():
    normal=packets('audio',[0,.021333,.042666],.021333)
    assert cadence(normal,'audio')['passed']
    assert not cadence(normal+packets('audio',[.5],.021333),'audio')['passed']
    assert not cadence(normal+packets('audio',[0],.021333),'audio')['passed']


def test_missing_or_invalid_timestamps_do_not_pass():
    assert not cadence([], 'audio')['passed']
    assert not cadence(packets('audio',[float('nan'),float('inf')],.02),'audio')['passed']


def test_even_but_slow_video_does_not_pass_target_rate():
    result=cadence(packets('video',[i/20 for i in range(100)],.05),'video',30)
    assert not result['passed'] and not result['expected_rate_met']
    assert result['large_gaps']==0
