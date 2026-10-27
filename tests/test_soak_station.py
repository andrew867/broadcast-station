from tools.soak_station import summarize
from tools.soak_station import source_state
import json


def test_soak_does_not_hide_failed_probes_between_healthy_samples():
    rows=[{'at':10,'ready':True,'fps':30,'target_fps':30},
          {'at':40,'error':'Unavailable'},
          {'at':70,'ready':True,'fps':25,'target_fps':30,'unready_cameras':['cam1']}]
    result=summarize(rows,10,60,True)
    assert result['complete'] and result['probe_failures']==1 and result['not_ready_samples']==1
    assert result['low_fps_samples']==1 and result['camera_unready_samples']==1
    assert result['largest_observation_gap_seconds']==30 and result['fps_mean']==27.5
    assert 'passed' not in result


def test_soak_reports_no_coverage_instead_of_inventing_zero_fps():
    result=summarize([],10,60)
    assert result['samples']==0 and result['fps_mean'] is None and not result['complete']


def test_decoded_source_health_is_separate_from_native_playout_warmup(tmp_path):
    (tmp_path/'data').mkdir()
    (tmp_path/'data/source-health.json').write_text(json.dumps({'checked_at':100,
        'cameras':{'cam1':{'ready':True,'last_frame_at':99.9,'generation':2},
                   'cam2':{'ready':True,'last_frame_at':90,'generation':1}}}))
    state=source_state(tmp_path,{'cam1','cam2'},100.2)
    assert state['cam1']['ready'] and state['cam1']['generation']==2
    assert not state['cam2']['ready']
    result=summarize([{'at':100,'unready_cameras':['cam1'],'unready_sources':[]}],100,60)
    assert result['camera_unready_samples']==1 and result['source_unready_samples']==0
