import json
from skycam.rundown import Rundown, RundownConfig, Cue
from skycam.readiness import snapshot, program_moving

def configured(path):
    r=Rundown(path,lambda *_:None)
    r.save(RundownConfig(resume_after_restart=True,cues=[Cue(camera='cam1'),Cue(camera='quad')]))
    return r

def test_restart_waits_for_output_and_resumes_saved_cue(tmp_path):
    r=configured(tmp_path);r.action('start');r.action('next')
    calls=[];ready=[False]
    restarted=Rundown(tmp_path,lambda *args:calls.append(args),recovery_ready=lambda:ready[0])
    assert restarted.resume_pending and not restarted.enabled
    restarted.advance_due();assert not calls
    ready[0]=True;restarted.advance_due()
    assert restarted.enabled and restarted.index==1 and calls[0][0]=='quad'
    restarted.advance_due();assert len(calls)==1

def test_manual_pause_cancels_restart_intent(tmp_path):
    r=configured(tmp_path);r.action('start');r.pause()
    restarted=Rundown(tmp_path,lambda *_:None)
    assert not restarted.enabled and not restarted.resume_pending

def test_pause_while_waiting_cancels_pending_resume(tmp_path):
    r=configured(tmp_path);r.action('start')
    calls=[];restarted=Rundown(tmp_path,lambda *args:calls.append(args))
    restarted.pause();restarted.advance_due()
    assert not calls and not restarted.resume_pending
    assert not Rundown(tmp_path,lambda *_:None).resume_pending

def test_disabled_recovery_and_corrupt_intent_start_paused(tmp_path):
    r=Rundown(tmp_path,lambda *_:None);r.action('start')
    assert not Rundown(tmp_path,lambda *_:None).resume_pending
    r=configured(tmp_path);r.intent_path.write_text('{broken')
    assert not Rundown(tmp_path,lambda *_:None).resume_pending

def test_recovery_retries_failed_takes_without_disabling_rotation(tmp_path,monkeypatch):
    r=configured(tmp_path);r.action('start')
    def failed(*_):raise RuntimeError('Engine temporarily busy')
    restarted=Rundown(tmp_path,failed);restarted.advance_due()
    assert restarted.enabled and restarted.error=='Engine temporarily busy'
    restarted.apply=lambda *_:None;restarted.deadline=0;restarted.advance_due()
    assert restarted.enabled and not restarted.error

def test_health_does_not_claim_stale_counter_is_moving():
    status={'connected':True,'ready':True,'checked_at':100,'output':{'moving':True,'measured_fps':60}}
    assert program_moving(status,101)
    assert not program_moving(status,106)
    d=snapshot(status,{'healthy':True},{'ready':True,'updated_at':100},{},{},106)
    assert d['state']=='attention'
    assert d['checks'][0]['level']=='error'
    assert 'Waiting' in d['checks'][1]['detail']

def test_missing_camera_and_low_cadence_are_reported_without_stopping_output():
    p={'connected':True,'ready':True,'checked_at':100,'output':{'moving':True,'measured_fps':40},
       'cameras':{c:{'native_ready':True} for c in ['cam1','cam2','cam4']}}
    d=snapshot(p,{'healthy':True},{'ready':True,'updated_at':100},{'enabled':True,'current':'song.wav'},{'enabled':True},101)
    checks={c['id']:c for c in d['checks']}
    assert d['state']=='limited' and checks['program']['level']=='ok'
    assert checks['cadence']['level']=='warning' and checks['cam3']['level']=='warning'
    assert 'selectable' in checks['cam3']['detail']
