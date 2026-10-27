from skycam.camera_rotation import CameraRotation,RotationConfig


def setup(tmp_path):
    clock=[1000.]
    cameras={'cam1':{'enabled':True},'cam2':{'enabled':False}}
    policy=CameraRotation(tmp_path,cameras,lambda:clock[0],lambda:clock[0])
    return clock,cameras,policy


def picture(clock):
    return {'checked_at':clock[0],'cameras':{'cam1':{'ready':True,'last_frame_at':clock[0]}}}


def test_disabled_skips_even_when_loss_policy_disabled(tmp_path):
    clock,cameras,p=setup(tmp_path)
    p.save(RotationConfig(skip_unavailable=False))
    assert not p.eligible('cam2')
    assert p.eligible('quad') and p.eligible('map') and p.eligible('cam1')


def test_loss_grace_and_continuous_recovery(tmp_path):
    clock,cameras,p=setup(tmp_path)
    p.sample({});clock[0]+=179;p.sample({});assert p.eligible('cam1')
    clock[0]+=1;p.sample({});assert not p.eligible('cam1')
    for i in range(10):
        clock[0]+=1;p.sample(picture(clock));assert not p.eligible('cam1')
    clock[0]+=1;p.sample(picture(clock));assert p.eligible('cam1')


def test_recovery_blip_or_monitor_gap_does_not_restore(tmp_path):
    clock,cameras,p=setup(tmp_path)
    p.sample({});clock[0]+=180;p.sample({})
    p.sample(picture(clock));clock[0]+=9;p.sample(picture(clock))
    assert not p.eligible('cam1')
    clock[0]+=1;p.sample({});clock[0]+=1;p.sample(picture(clock))
    assert not p.eligible('cam1')


def test_connection_without_recent_frame_is_not_ready(tmp_path):
    clock,cameras,p=setup(tmp_path)
    p.sample({'checked_at':1000,'cameras':{'cam1':{'ready':True,'last_frame_at':1}}})
    clock[0]+=180;p.sample({'checked_at':1000,'cameras':{'cam1':{'ready':True,'last_frame_at':clock[0]}}})
    assert not p.eligible('cam1')


def test_policy_roundtrip_and_bad_health_file(tmp_path):
    clock,cameras,p=setup(tmp_path)
    p.save(RotationConfig(unavailable_after_s=30))
    q=CameraRotation(tmp_path,cameras,lambda:clock[0],lambda:clock[0])
    assert q.config.unavailable_after_s==30
    q.health_path.write_text('[]');q.sample();clock[0]+=30;q.sample()
    assert not q.eligible('cam1')
