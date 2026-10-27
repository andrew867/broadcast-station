from skycam import playout
from skycam.alert_graphics import summary_image,emergency_rows
from skycam.broadcast import Broadcast
from skycam.native_ticker import NativeTicker
from tests.test_alert_playout import alert_row


def test_summary_is_transparent_over_the_normal_crawl(tmp_path):
    row=alert_row(tmp_path)
    for kind in ('utility','emergency'):
        image=summary_image({'kind':kind,'row':{'alert':row},'countdown':486})
        assert image.mode=='RGBA' and image.size==(3840,636)
        assert image.getchannel('A').crop((0,412,3840,636)).getbbox() is None
        assert image.getpixel((0,100))[3]==0
        assert image.getpixel((250,290))[3]==255


def test_full_summary_countdown_and_clear_do_not_restart_crawl_each_second(tmp_path,monkeypatch):
    row=alert_row(tmp_path)
    class Presentation:
        audio=None
        value={'mode':'full','kind':'utility','row':emergency_rows([row])[0],'fresh':True}
        def frame(self):return self.value
        def public(self):return {'state':self.value['mode'] if self.value else 'idle'}
    p=Presentation();calls=[]
    def command(c,**kwargs):
        calls.append(c)
        return '201 OK\r\n0.1 0.9 1.0 0.1' if c.endswith(' FILL') else '202 OK'
    monkeypatch.setattr(playout,'command',command)
    monkeypatch.setitem(playout.STATUS,'ready',True)
    ticker=NativeTicker(tmp_path,Broadcast(tmp_path),presentation=p)
    ticker.tick()
    assert 'CLEAR 1-22' in calls and not any(c.startswith('PLAY 1-22') for c in calls)
    p.value={'mode':'summary','kind':'utility','row':{'alert':row},'fresh':True,'countdown':486}
    calls.clear();ticker.tick()
    assert any(c.startswith('PLAY 1-22') for c in calls)
    p.value['countdown']=485;calls.clear();ticker.tick()
    assert any(c.startswith('PLAY 1-41') for c in calls)
    assert not any(c.startswith('CLEAR 1-') for c in calls)
    p.value={'mode':'full','kind':'utility','row':emergency_rows([row])[0],'fresh':True}
    calls.clear();ticker.tick();assert 'CLEAR 1-22' in calls
    p.value=None;calls.clear();ticker.tick()
    assert 'CLEAR 1-41' in calls and any(c.startswith('PLAY 1-22') for c in calls)
    assert not any(c.startswith(('PLAY 1-5 ','CLEAR 1-5 ','PLAY 1-10 ','CLEAR 1-10 ')) for c in calls)
