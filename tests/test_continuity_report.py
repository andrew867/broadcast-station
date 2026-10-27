import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('continuity_check',Path(__file__).parents[1]/'deploy/continuity-check.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_report_does_not_hide_nested_errors_or_count_standby_as_failure():
    rows=[
        {'at':100,'scene':'map','output':{'moving':True,'measured_fps':30},
         'music':{'enabled':True,'current':'song.wav','error':'render failed'},
         'rundown':{'error':'take failed'},
         'sources':{'cam1':{'ready':True,'native_ready':False,'playout_active':False}}},
        {'at':110,'scene':'cam1','output':{'moving':True,'measured_fps':29.9},
         'music':{'enabled':True,'current':'song.wav','error':None},
         'sources':{'cam1':{'ready':False,'native_ready':False,'playout_active':True}}},
    ]
    result=module.summarize(rows,False)
    assert result['error_samples']==[{'at':100,'music_reported_error':'render failed','rundown_reported_error':'take failed'}]
    assert result['source_readiness']['cam1']['not_ready_samples']==1
    assert result['source_readiness']['cam1']['ready_samples']==1
    assert result['nonmoving_samples']==0 and result['music_status_without_current']==0

def test_bad_fps_and_missing_music_status_are_not_fake_good_measurements():
    rows=[{'at':100+i,'output':{'moving':True,'measured_fps':value},
           'music':{'enabled':True,'current':None}}
          for i,value in enumerate([float('nan'),float('inf'),'30',None,-1,True,30])]
    result=module.summarize(rows,False)
    assert result['sampled_fps']=={'min':30,'max':30,'mean':30}
    assert result['music_status_without_current']==7

def test_legacy_progress_is_recorded_without_becoming_an_error():
    note='New variation ready; changes at the next phrase boundary'
    rows=[{'at':100,'music':{'error':note}},{'at':110,'music':{'error':None,'note':note}}]
    result=module.summarize(rows,False)
    assert result['error_samples']==[]
    assert len(result['information_samples'])==2

def test_music_api_keeps_queue_information_but_reports_real_failure(tmp_path):
    from skycam.music import Music
    music=Music(tmp_path)
    music.error='Preparing generated music; existing audio continues'
    state=music.public()
    assert state['error'] is None and state['note']==music.error
    music.error='Render worker timed out'
    state=music.public()
    assert state['error']==music.error and state['note'] is None
