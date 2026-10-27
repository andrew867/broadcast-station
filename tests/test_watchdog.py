import importlib.util
from pathlib import Path
from unittest.mock import Mock

path=Path(__file__).parents[1]/'deploy/program-watchdog.py'
spec=importlib.util.spec_from_file_location('program_watchdog',path)
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
ENGINE={'Running':True,'Paused':False,'Pid':42,'StartedAt':'first'}

def ready():
    g=w.Guard(0)
    assert g.observe(0,ENGINE,True,0,True) is None
    assert g.observe(100,ENGINE,True,4000,True) is None
    return g

def test_sustained_amcp_failure_and_recovery_cooldown():
    g=ready()
    assert g.observe(105,ENGINE,True,None,False) is None
    assert g.observe(134,ENGINE,True,None,False) is None
    assert g.observe(135,ENGINE,True,None,False)=='engine'
    g.recovered(135,'engine',g.last_reason)
    assert g.observe(230,ENGINE,True,None,False) is None
    assert g.observe(260,ENGINE,True,None,False) is None
    assert 'cooldown' in g.last_reason

def test_frozen_frame_counter_triggers_but_low_fps_does_not():
    g=ready()
    for t in range(105,200,5):
        assert g.observe(t,ENGINE,True,4000+t,True) is None
    assert g.observe(239,ENGINE,True,4195,True) is None
    assert g.observe(240,ENGINE,True,4195,True)=='engine'

def test_controller_failure_does_not_restart_healthy_engine():
    g=ready()
    assert g.observe(105,ENGINE,True,4100,False) is None
    assert g.observe(135,ENGINE,True,5100,False)=='web'

def test_transient_fault_and_new_engine_get_grace():
    g=ready()
    g.observe(105,ENGINE,True,None,False)
    assert g.observe(125,ENGINE,True,5000,True) is None
    restarted={**ENGINE,'Pid':43,'StartedAt':'second'}
    assert g.observe(500,restarted,True,None,False) is None
    assert g.observe(589,restarted,True,None,False) is None

def test_manual_stop_pause_and_maintenance_are_respected():
    for state,maintenance in [({**ENGINE,'Running':False},False),({**ENGINE,'Paused':True},False),(ENGINE,True)]:
        g=ready()
        assert g.observe(500,state,False,None,False,maintenance) is None
        assert g.observe(1000,state,False,None,False,maintenance) is None
    g=ready()
    assert g.observe(500,ENGINE,False,6000,False) is None
    assert g.observe(1000,ENGINE,False,7000,False) is None

def test_restart_storm_is_limited_across_watchdog_restart():
    history=[{'at':t,'target':'engine','reason':'test'} for t in (10,210,410)]
    g=w.Guard(500,history)
    g.observe(500,ENGINE,True,5000,True)
    assert g.observe(600,ENGINE,True,5000,True) is None
    assert 'limit reached' in g.last_reason
    assert g.observe(3700,ENGINE,True,5000,True)=='engine'


def test_recovery_budget_reports_exhaustion_and_natural_expiry():
    g=w.Guard(500,[{'at':t,'target':'engine','reason':'test'} for t in (10,210,410)])
    assert g.recovery_budget(600)=={'remaining':0,'available_at':3610}
    assert g.recovery_budget(3610)=={'remaining':1,'available_at':None}
    assert g.recovery_budget(5000)=={'remaining':3,'available_at':None}

def test_recovery_commands_are_bounded_and_targeted(monkeypatch,tmp_path):
    monkeypatch.setattr(w,'RUNTIME',tmp_path)
    monkeypatch.setattr(w.subprocess,'run',Mock(return_value=Mock(stdout='',stderr='')))
    calls=[];monkeypatch.setattr(w,'run',lambda *args,**kwargs:calls.append((args,kwargs)))
    w.recover('web',True)
    assert calls==[(('docker','restart','-t','5','skycam-web'),{'timeout':35})]
    calls.clear();w.recover('engine',True)
    assert [c[0][-1] for c in calls]==['skycam-caspar','skycam-web']
    calls.clear();w.recover('engine',False)
    assert [c[0][-1] for c in calls]==['skycam-caspar']

def test_failed_control_query_revokes_old_moving_status(monkeypatch):
    from skycam import playout as p
    monkeypatch.setattr(p,'STATUS',{'output':{'moving':True,'measured_fps':40,'frames':10}})
    def fail(*args):raise TimeoutError('test timeout')
    monkeypatch.setattr(p,'info',fail)
    p.check(None)
    assert not p.STATUS['connected'] and not p.STATUS['output']['moving']
    assert p.STATUS['output']['measured_fps'] is None


def test_failed_control_does_not_restart_advancing_program():
    g=ready()
    for t in range(105,500,5):
        assert g.observe(t,ENGINE,True,None,True,delivery_advancing=True) is None
        assert 'independent program delivery' in g.last_reason
    assert g.observe(500,ENGINE,True,None,False) is None
    assert g.observe(530,ENGINE,True,None,False)=='engine'


def test_delivery_probe_needs_fresh_advancing_decoded_timestamps():
    d=w.DeliveryProbe()
    assert not d.observe(0,100)
    assert d.observe(10,110)
    assert not d.observe(31,110)
    assert not d.observe(32,None)
    assert not d.observe(33,1)
    assert d.observe(43,11)


def test_damaged_recovery_history_cannot_disable_watchdog():
    for bad in (None,{},42,'text',[None,{'at':None},{'at':float('nan')},
                                 {'at':float('inf')},{'at':True}]):
        g=w.Guard(500,bad)
        g.observe(500,ENGINE,True,1,True)
        assert g.observe(600,ENGINE,True,1,True)=='engine'


def test_history_order_duplicates_and_invalid_times_preserve_recovery_budget():
    good=[{'at':t,'target':'engine','reason':'test'} for t in (410,10,210)]
    g=w.Guard(500,good+[good[0],{'at':501,'target':'engine','reason':'future'},
        {'at':-90000,'target':'web','reason':'expired'},
        {'at':300,'target':'other','reason':'unknown'}])
    assert [h['at'] for h in g.history]==[10,210,410]
    assert g.recovery_budget(600)['remaining']==0


def test_older_web_failure_cannot_delay_engine_recovery():
    g=ready()
    assert g.observe(105,ENGINE,True,4100,False) is None
    # The web failure is older, but neither control nor delivery proves that
    # the engine is healthy. Wait for the engine timeout, not a web restart.
    assert g.observe(130,ENGINE,True,None,False) is None
    assert g.observe(135,ENGINE,True,None,False) is None
    assert g.observe(159,ENGINE,True,None,False) is None
    assert g.observe(160,ENGINE,True,None,False)=='engine'


def test_advancing_delivery_can_still_recover_web_with_amcp_unavailable():
    g=ready()
    assert g.observe(105,ENGINE,True,None,False,delivery_advancing=True) is None
    assert g.observe(135,ENGINE,True,None,False,delivery_advancing=True)=='web'
