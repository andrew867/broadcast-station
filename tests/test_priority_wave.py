import io
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from skycam.alert_presentation import AlertPresentation,PresentationConfig
from skycam.alert_graphics import emergency_image,summary_image,identity
from skycam.alerts import Alerts,HOSTS
from skycam.camera_tools import CameraTools
from skycam.sources import CameraCatalog
from skycam.notices import NoticeBoard,Notice,NoticeWrite
from skycam.community_cards import notice_pages,notice_image,CommunityCards
from skycam import playout
from tests.test_alerts import message,NOW
from tests.test_alert_playout import alert_row


def test_alert_full_summary_repeat_and_cancel(tmp_path):
    state={'immediate':[alert_row(tmp_path)],'fresh':True}
    p=AlertPresentation(tmp_path,lambda:state,None)
    f=p.frame(NOW);assert f['mode']=='full'
    assert emergency_image(f['row']).size==(3840,636)
    f=p.frame(NOW+23);assert f['mode']=='summary' and f['countdown']==600
    assert summary_image(f).size==(3840,636)
    assert p.frame(NOW+622)['mode']=='summary'
    assert p.frame(NOW+623)['mode']=='full'
    state['immediate']=[];assert p.frame(NOW+624) is None
    # A completed message retains its repeat deadline across a controller reload.
    state['immediate']=[alert_row(tmp_path)]
    q=AlertPresentation(tmp_path,lambda:state,None)
    assert q.frame(NOW+24)['mode']=='summary'


def test_queue_new_messages_and_utility_priority(tmp_path):
    from tests.test_outages import provider
    o=provider(tmp_path);o.checked_at=NOW
    for row in o.rows:row['start']=NOW-3600
    state={'immediate':[],'fresh':True}
    p=AlertPresentation(tmp_path,lambda:state,lambda:o.public(NOW))
    assert p.frame(NOW)['kind']=='utility'
    first=alert_row(tmp_path);state['immediate']=[first]
    assert p.frame(NOW+1)['kind']=='emergency'
    second={**first,'identifier':'two','received_at':first.get('received_at',NOW)+1}
    state['immediate'].append(second)
    assert p.frame(NOW+2)['row']['alert']['identifier']==first['identifier']
    assert p.frame(NOW+24)['row']['alert']['identifier']=='two'
    assert p.frame(NOW+47)['kind']=='emergency'  # No utility preemption during summary.
    state['immediate']=[];o.error='stale'
    assert p.frame(NOW+48) is None


def test_bilingual_identity_and_unverified_state(tmp_path):
    a=Alerts(tmp_path,lambda _: {'verified':True})
    raw=message('bilingual',immediate='yes')
    start=raw.index(b'<info>');end=raw.index(b'</info>')+len(b'</info>')
    french=raw[start:end].replace(b'en-CA',b'fr-CA').replace(b'Fixture area',b'Region de test')
    a.ingest(raw.replace(b'</alert>',french+b'</alert>'),HOSTS[0],NOW)
    rows=a.public(NOW)['immediate'];assert len(rows)==1
    assert {r['language'] for r in rows}=={'en-CA'}
    assert a.public(NOW)['language_excluded']==1
    assert len(next(iter(a.items.values()))['blocks'])==2
    assert len({identity(r) for r in rows})==1


def test_alert_audio_stop_and_disable_restore(tmp_path):
    class Audio:
        def __init__(self):self.playing=False;self.stops=0
        def prepare(self,*args):pass
        def ready(self,key):return True
        def play(self,*args):self.playing=True
        def public(self):return {'duration':50}
        def stop(self):self.playing=False;self.stops+=1
    a=Audio();state={'immediate':[alert_row(tmp_path)],'fresh':True}
    p=AlertPresentation(tmp_path,lambda:state,None,a)
    p.frame(NOW);p.frame(NOW+1);assert a.playing
    assert p.frame(NOW+25)['mode']=='full'
    p.save(PresentationConfig(audio_enabled=False));assert not a.playing
    state['immediate']=[];assert p.frame(NOW+26) is None


def png(size=(1920,1080)):
    out=io.BytesIO();Image.new('RGB',size,'#557799').save(out,format='PNG');return out.getvalue()


def test_reference_native_size_retained_and_path_safe(tmp_path):
    catalog=CameraCatalog(tmp_path);catalog.cameras['cam3'].update(width=1920,height=1080);tools=CameraTools(tmp_path,catalog)
    row=tools.store('cam3',png());assert row['origin']=='uploaded reference'
    assert catalog.cameras['cam3']['reference']==row['reference']
    with Image.open(tools.folder/row['reference']) as image:assert image.size==(1920,1080)
    with pytest.raises(ValueError):tools.store('cam3',png((320,240)))
    with pytest.raises(ValueError):tools.store('../../escape',png())
    with pytest.raises(Exception):tools.store('cam3',b'not an image')


def test_camera_probe_reports_metadata_without_mutation(tmp_path,monkeypatch):
    from types import SimpleNamespace
    c=CameraCatalog(tmp_path);c.cameras['cam3'].update(width=1920,height=1080,enabled=True);t=CameraTools(tmp_path,c)
    monkeypatch.setattr('skycam.camera_tools.subprocess.run',lambda *a,**kw:SimpleNamespace(stdout=json.dumps({'streams':[{'width':1280,'height':720,'r_frame_rate':'30000/1001','codec_name':'h264'}]}).encode()))
    d=t.probe('cam3');assert d['fps']==pytest.approx(29.97003)
    assert c.cameras['cam3']['width']==1920


def test_capture_rejects_decoder_errors(tmp_path,monkeypatch):
    from types import SimpleNamespace
    t=CameraTools(tmp_path,CameraCatalog(tmp_path));t.catalog.cameras['cam3']['enabled']=True
    monkeypatch.setattr('skycam.camera_tools.subprocess.run',lambda *a,**kw:SimpleNamespace(stdout=png(),stderr=b'corrupt decoded frame'))
    with pytest.raises(ValueError):t.capture('cam3')
    assert not list(t.folder.glob('*.png'))


def test_notice_artwork_preview_approval_and_expiry(tmp_path):
    b=NoticeBoard(tmp_path);asset=b.upload(png())
    n=Notice(title='Community poster',image_id=asset['image_id'],credit='Fixture author')
    b.save(NoticeWrite(expected_revision=0,notice=n));assert not b.active()
    n=n.model_copy(update={'approved':True})
    b.save(NoticeWrite(expected_revision=1,notice=n));pages=notice_pages(b.active())
    assert len(pages)==1 and pages[0]['image']
    im=notice_image(pages[0],b.assets);assert im.size==(3840,2160)
    n=n.model_copy(update={'text':'Full text is retained too.'})
    assert len(notice_pages([n.model_dump(mode='json')]))==2
    with pytest.raises(ValueError):b.image_path('../anything')
    with pytest.raises(ValueError):Notice(title='Empty')
    expired=n.model_copy(update={'ends_at':datetime(2000,1,1,tzinfo=timezone.utc)})
    assert not expired.active(datetime.now(timezone.utc))


def test_lunar_full_new_and_card(tmp_path):
    from skycam.moon_card import public,image
    full=public(datetime(2024,3,25,12,tzinfo=timezone.utc))
    new=public(datetime(2024,4,8,12,tzinfo=timezone.utc))
    assert full['illumination']>.98 and new['illumination']<.02
    assert image(full).size==(3840,2160)
    assert CommunityCards(tmp_path).path('moon').exists()


def test_warm_music_boundaries_song_variation_and_level():
    from skycam.generative_music import samples,RATE
    from skycam.study_songs import SONG_FRAMES,compose,warm_instrument
    for at in (RATE*20,SONG_FRAMES-1000,SONG_FRAMES+1000):
        a=samples(at,4000,247,'warm')
        b=np.concatenate((samples(at,1733,247,'warm'),samples(at+1733,2267,247,'warm')))
        assert np.array_equal(a,b) and np.isfinite(a).all()
        assert .002<np.sqrt(np.mean(a*a)) and np.abs(a).max()<.68
        assert np.abs(np.diff(a,axis=0)).max()<.12
    songs=[compose(247,i,True) for i in range(3)]
    assert len({s.title for s in songs})==3 and len({s.progression for s in songs})==3
    assert len({n.pitch for n in songs[0].events if n.kind in ('velvet','reed','softlead')})>=12
    assert warm_instrument.cache_info().maxsize==128


def test_helicopter_category_is_not_guessed():
    from skycam.tracking import Tracks
    t=Tracks();a={'hex':'abc123','flight':'HELI TEST','lat':47.5,'lon':-52.7,'alt_geom':2000,'seen_pos':0}
    t.ingest({'now':NOW,'aircraft':[a]},NOW)
    assert t.history['abc123'][-1]['category']==''
    t.ingest({'now':NOW+1,'aircraft':[{**a,'category':'A7'}]},NOW+1)
    assert t.history['abc123'][-1]['category']=='A7'


def test_update_finishes_current_then_replacement(tmp_path):
    first=alert_row(tmp_path)
    state={'immediate':[first],'fresh':True}
    p=AlertPresentation(tmp_path,lambda:state,None)
    p.frame(NOW)
    second={**first,'identifier':'updated','message_type':'Update',
            'references':[[first['sender'],first['identifier'],first['sent']]]}
    state['immediate']=[second]
    assert p.frame(NOW+5)['row']['alert']['identifier']==first['identifier']
    assert p.frame(NOW+23)['row']['alert']['identifier']=='updated'
    state['immediate']=[]
    assert p.frame(NOW+24) is None


def test_utility_frame_identity_does_not_change_with_clock(tmp_path):
    from tests.test_outages import provider
    o=provider(tmp_path);o.checked_at=NOW
    for row in o.rows:row['start']=NOW-3600
    p=AlertPresentation(tmp_path,lambda:{'immediate':[]},lambda:o.public(NOW))
    a=p.candidates(NOW)[0]['alert'];b=p.candidates(NOW+1)[0]['alert']
    assert identity(a)==identity(b)


def test_signal_first_only_shared_between_languages_and_restart(tmp_path,monkeypatch):
    from skycam.alert_audio import AlertAudio
    from concurrent.futures import Future
    class Music:
        def set_duck(self,value):pass
    class Pool:
        def __init__(self):self.calls=[]
        def submit(self,fn,key,alert,first):
            self.calls.append(first);f=Future();f.set_result((tmp_path/'voice.wav',15));return f
    monkeypatch.setattr(playout,'command',lambda *a,**kw:'202 OK')
    a=AlertAudio(tmp_path,Music());a.pool.shutdown();a.pool=Pool()
    row=alert_row(tmp_path);a.prepare('english',row);assert a.first
    assert a.play('english',.65);a.stop()
    a.prepare('english',row);assert not a.first
    with pytest.raises(ValueError,match='English only'):a.prepare('french',{**row,'language':'fr-CA'})
    b=AlertAudio(tmp_path,Music());b.pool.shutdown();b.pool=Pool()
    b.prepare('english',row);assert not b.first
    b.prepare('utility',{**row,'utility':True});assert not b.first


def test_marine_split_areas_separate_issue_times_and_staleness(tmp_path):
    from skycam.marine import parse,Marine,pages,image
    raw=(Path(__file__).parent/'fixtures/marine-synthetic.xml').read_bytes()
    data=parse(raw);now=data['groups'][0]['issued_at']+3600
    m=Marine(tmp_path);m.data={**data,'checked_at':now}
    d=m.public(now);assert d['available'] and len(d['groups'])==2
    assert d['groups'][0]['warnings']==['Gale warning'] and not d['groups'][1]['warnings']
    rows=pages(d);assert len(rows)==4 and rows[0]['issued_at']!=rows[1]['issued_at']
    assert image(d,0).size==(3840,2160)
    assert not m.public(now+5401)['available']
    m.data['checked_at']=now+24*3600;assert not m.public(now+24*3600)['available']
    with pytest.raises(ValueError):parse(raw.replace(b'East Coast</area>',b'Wrong Coast</area>'))
    with pytest.raises(ValueError):parse(b'<!DOCTYPE foo []>'+raw)


def test_audio_producer_clock_and_deadline(tmp_path):
    class Audio:
        def __init__(self):self.done=False;self.error=None;self.playing=False
        def public(self):return {'duration':30}
        def prepare(self,*a):pass
        def ready(self,*a):return True
        def play(self,*a):self.playing=True
        def stop(self):self.playing=False
        def complete(self):return self.done
    a=Audio();state={'immediate':[alert_row(tmp_path)],'fresh':True}
    p=AlertPresentation(tmp_path,lambda:state,None,a)
    p.frame(NOW);p.frame(NOW+1)
    assert p.frame(NOW+33)['mode']=='full' and a.playing
    a.done=True;assert p.frame(NOW+40)['mode']=='summary' and not a.playing
    p.frame(NOW+640);p.frame(NOW+641);a.done=False
    assert p.frame(NOW+735)['mode']=='summary' and not a.playing and 'deadline' in a.error


def test_artwork_cleanup_keeps_saved_and_recent(tmp_path):
    import os,time
    b=NoticeBoard(tmp_path);saved=b.upload(png());old=b.upload(png());recent=b.upload(png())
    b.save(NoticeWrite(expected_revision=0,notice=Notice(title='Saved',image_id=saved['image_id'])))
    for asset in (saved,old):os.utime(b.image_path(asset['image_id']),(time.time()-90000,)*2)
    assert b.clean_unused()['removed']==1
    assert b.image_path(saved['image_id']).exists() and b.image_path(recent['image_id']).exists()
