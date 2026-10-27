from skycam.transport_health import observe_loss,transport_fault

def test_loss_is_per_camera_and_not_confused_with_other_log_messages():
    rows={}
    assert not observe_loss(rows,'[path cam1] ready',100)
    assert observe_loss(rows,'WAR [path cam1] [RTSP source] 120 RTP packets lost',100)
    assert observe_loss(rows,'WAR [path cam1] [RTSP source] 3 RTP packets lost',101)
    assert rows=={'cam1':{'last_loss_at':101,'lost_packets':123}}
    assert not transport_fault(rows.get('cam2'),0,102)

def test_each_new_loss_hides_video_until_quiet_then_decoder_recovery():
    row={'last_loss_at':100}
    assert transport_fault(row,0,102)=='wait'
    assert transport_fault(row,0,106)=='reload'
    assert transport_fault(row,106,107) is None
    row['last_loss_at']=108
    assert transport_fault(row,106,109)=='wait'
