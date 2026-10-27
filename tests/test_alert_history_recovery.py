import json
import pytest
from skycam.alert_presentation import AlertPresentation,read_times
from tests.test_alert_playout import alert_row
from tests.test_alerts import NOW

@pytest.mark.parametrize('damaged',[[],None,42,{'bad':None},{'bad':float('nan')},{'bad':float('inf')},{'bad':'text'}])
def test_bad_history_does_not_break_full_summary_and_cancel(tmp_path,damaged):
    row=alert_row(tmp_path);folder=tmp_path/'broadcast';folder.mkdir(exist_ok=True)
    for name in ('alert-presentation-history.json','alert-message-history.json'):
        (folder/name).write_text(json.dumps(damaged))
    state={'immediate':[row],'fresh':True}
    p=AlertPresentation(tmp_path,lambda:state,None)
    assert p.frame(NOW)['mode']=='full'
    assert p.frame(NOW+23)['mode']=='summary'
    state['immediate']=[]
    assert p.frame(NOW+24) is None

def test_valid_repeat_deadlines_retained_and_history_bounded(tmp_path):
    path=tmp_path/'history.json'
    path.write_text(json.dumps({str(i):NOW-i for i in range(700)}|{'bool':True,'future':1e100}))
    rows=read_times(path)
    assert len(rows)==512 and rows['0']==NOW and 'bool' not in rows and 'future' not in rows
