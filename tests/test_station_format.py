from datetime import datetime,timezone,timedelta
from pathlib import Path
import json,math
import pytest
from skycam.markets import Markets,oil_rows,fx_rows
from skycam.commercial import Commercial,CommercialWrite,CommercialConfig,Advertisement,Sponsor
from skycam.rundown_library import LibraryConflict,RundownLibrary
from skycam.rundown import Rundown
from skycam.program_clock import ProgramClock
from skycam.format_defaults import apply,public,FormatWrite
from skycam.notices import Notice
from skycam.community_cards import notice_image,notice_pages,markets_image
from PIL import Image

def test_oil_dates_missing_negative_and_reciprocal(tmp_path):
    html="<tr><td class='B6'>2025 Dec-29 to Jan-2</td>"+''.join("<td class='B3'>"+v+"</td>" for v in ['-1','NA','60.00','','61.25'])+'</tr>'
    rows=oil_rows(html);assert rows==[{'date':'2025-12-29','value':-1},{'date':'2025-12-31','value':60},{'date':'2026-01-02','value':61.25}]
    with pytest.raises(ValueError):oil_rows('<html>changed upstream</html>')
    fx=fx_rows({'observations':[{'d':'2026-10-15','FXUSDCAD':{'v':'1.25'}},{'d':'2026-10-16','FXUSDCAD':{'v':'1.20'}},{'d':'2026-10-17','FXUSDCAD':{'v':'nan'}}]})
    now=datetime(2026,10,17,tzinfo=timezone.utc).timestamp();m=Markets(tmp_path);m.values={'fx':{'rows':fx,'checked_at':now},'wti':{'rows':rows,'checked_at':now}}
    d=m.public(now);a=d['cards'][0]
    assert a['value']==pytest.approx(1/1.20) and a['change']==pytest.approx(1/1.20-1/1.25)
    assert not d['cards'][1]['available'] and d['cards'][1]['value'] is None
    assert markets_image(d).size==(3840,2160)
    m.errors['fx']='offline';assert m.public(now)['cards'][0]['cached']
    assert not m.public(now+8*86400)['cards'][0]['available']

def image_asset(c,tmp_path):
    p=tmp_path/'wide.png';Image.new('RGBA',(800,200),'orange').save(p)
    return c.import_file(p,'wide.png')

def test_commercial_approval_expiry_assets_and_conflicts(tmp_path):
    c=Commercial(tmp_path);row=image_asset(c,tmp_path)
    assert not c.eligible('advertisement')
    conf=CommercialConfig(advertisement=Advertisement(asset_id=row['id'],enabled=True),sponsor=Sponsor(asset_id=row['id'],enabled=True,scenes=['cam1']))
    c.save(CommercialWrite(expected_revision=0,config=conf));assert c.eligible('advertisement')
    assert c.sponsor_image('cam1').getbbox() and c.sponsor_image('map').getbbox() is None
    assert c.image().size==(3840,2160)
    with pytest.raises(LibraryConflict):c.save(CommercialWrite(expected_revision=0,config=conf))
    with pytest.raises(ValueError):c.delete(row['id'])
    conf.advertisement.ends_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    c.save(CommercialWrite(expected_revision=1,config=conf));assert not c.eligible('advertisement')
    restored=Commercial(tmp_path);assert restored.revision==2 and not restored.eligible('advertisement')
    with pytest.raises(ValueError):Advertisement(starts_at=datetime(2026,1,1))
    bad=tmp_path/'bad.txt';bad.write_text('not an image')
    with pytest.raises(ValueError):c.import_file(bad,'bad.txt')
    c.save(CommercialWrite(expected_revision=2,config=CommercialConfig()));c.delete(row['id']);assert not c.items

def test_sponsor_lives_in_scene_bank_and_expired_ad_replaced(tmp_path,monkeypatch):
    from skycam import playout
    c=Commercial(tmp_path);a=image_asset(c,tmp_path)
    conf=CommercialConfig(advertisement=Advertisement(asset_id=a['id'],enabled=True),sponsor=Sponsor(asset_id=a['id'],enabled=True,scenes=['cam1']))
    c.save(CommercialWrite(expected_revision=0,config=conf));calls=[]
    monkeypatch.setattr(playout,'command',lambda text,*a,**k:calls.append(text))
    monkeypatch.setattr(playout,'STATUS',{'ready':True});monkeypatch.setattr(playout,'_bank',3);monkeypatch.setattr(playout,'_camera','cam1')
    c.decorate(2,'cam1');assert calls[-1].startswith('PLAY 2-18 ')
    # The artwork filename contains cam1-<hash>, which can itself start cam1-18.
    # Check the AMCP target, not an incidental substring in that filename.
    c.tick();assert any(x.startswith('PLAY 3-18 ') for x in calls) and not any(x.split()[1]=='1-18' for x in calls)
    monkeypatch.setattr(playout,'_camera','advertisement');c.tick();c.config.advertisement.enabled=False;c.tick()
    assert any(x.startswith('PLAY 3-10 ') for x in calls)

def test_qr_link_validated_and_decodes_without_losing_text():
    import cv2,numpy as np
    url='https://example.com/community';text=' '.join('word'+str(i) for i in range(140))
    n=Notice(title='Off-air preview',text=text,url=url)
    rows=notice_pages([n.model_dump(mode='json')]);assert ' '.join(l for r in rows for l in r['lines'])==text
    im=notice_image(rows[0]);decoded,_,_=cv2.QRCodeDetector().detectAndDecode(np.array(im.crop((3000,1040,3580,1600))))
    assert decoded==url
    for bad in ['javascript:alert(1)','https://user:pass@example.com','not a URL']:
        with pytest.raises(ValueError):Notice(title='test',text='message',url=bad)

def test_format_apply_collision_settings_backup_and_stale_rejection(tmp_path):
    calls=[];r=Rundown(tmp_path,lambda *a:calls.append(a));l=RundownLibrary(tmp_path);c=ProgramClock(tmp_path,l.export)
    state=public(r,c,l);body=FormatWrite(preset_id='sky-tour',expected_rundown_hash=state['rundown_hash'],expected_clock_revision=0,expected_library_revision=0)
    result=apply(tmp_path,r,c,l,body)
    assert r.enabled and c.config.enabled and Path(result['backup']).exists()
    assert all(x.camera!='weather' for x in r.config.cues)
    assert [(x.id,x.every_minutes,x.offset_minutes,x.condition,x.hours,x.include_alerts) for x in c.config.rules]==[
        ('short-weather',10,0,'always',[],False),('extended-weather',20,0,'always',[],True),
        ('power-outages',15,13,'power-outages',[],False),('morning-briefing',60,0,'always',[6,7,8,9],False),
        ('evening-briefing',60,0,'always',[17,18,19,20,21],False),('travel-exceptions',15,7,'travel-exceptions',[],False),
        ('community-calendar',60,25,'always',[8,12,16,20],False),('local-information',30,5,'always',[],False)]
    with pytest.raises(LibraryConflict):apply(tmp_path,r,c,l,body)

def test_format_write_failure_rolls_back(tmp_path,monkeypatch):
    r=Rundown(tmp_path,lambda *a:None);l=RundownLibrary(tmp_path);c=ProgramClock(tmp_path,l.export);s=public(r,c,l);old=r.config.model_dump()
    monkeypatch.setattr(c,'save',lambda body:(_ for _ in ()).throw(OSError('disk error')))
    with pytest.raises(OSError):apply(tmp_path,r,c,l,FormatWrite(preset_id='sky-tour',expected_rundown_hash=s['rundown_hash'],expected_clock_revision=0,expected_library_revision=0))
    assert not l.public()['items'] and not c.config.enabled and r.config.model_dump()==old and not r.enabled

def test_commercial_api_guard_and_upload_preview(tmp_path,monkeypatch):
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    from fastapi.testclient import TestClient
    from io import BytesIO
    c=Commercial(tmp_path);monkeypatch.setattr(module,'commercial',c);client=TestClient(module.app)
    data=BytesIO();Image.new('RGB',(120,80),'orange').save(data,format='PNG')
    assert client.post('/api/commercial/assets?name=art.png',content=data.getvalue()).status_code==403
    reply=client.post('/api/commercial/assets?name=art.png',content=data.getvalue(),headers={'X-Skycam-Edit':'1'})
    assert reply.status_code==200 and len(c.items)==1 and not c.eligible('advertisement')
    assert client.get('/api/maps/advertisement/image').headers['content-type']=='image/png'

def test_prepared_camera_reused_and_video_paused_muted_before_take(tmp_path,monkeypatch):
    from skycam import playout
    from skycam.broadcast import BroadcastState
    calls=[];monkeypatch.setattr(playout,'_ready',True);monkeypatch.setattr(playout,'_bank',2);monkeypatch.setattr(playout,'_prepared',None)
    monkeypatch.setattr(playout,'DIRECT_MEDIA',{});monkeypatch.setattr(playout,'DIRECT_OVERLAY',{});monkeypatch.setattr(playout,'SCENE_DECORATE',None);monkeypatch.setattr(playout,'DECORATION_KEY',None)
    monkeypatch.setattr(playout,'command',lambda text,*a,**k:calls.append(text))
    for name in ('ensure_inputs','prime_inputs','release_unused'):monkeypatch.setattr(playout,name,lambda *a:None)
    monkeypatch.setattr(playout,'render',lambda state:tmp_path/'blank.png')
    state=BroadcastState(camera='cam1');first=playout.prepare('cam1',state);count=len(calls)
    assert playout.prepare('cam1',state) is first and len(calls)==count
    monkeypatch.setattr(playout,'DIRECT_MEDIA',{'advertisement':lambda:{'path':'/workspace/data-web/commercial/assets/test.mp4','video':True,'loop':False}})
    playout.prepare('advertisement',BroadcastState(camera='advertisement'))
    assert any(s.startswith('LOAD 3-10 ') and 'SCALE_MODE FIT' in s for s in calls)
    assert 'MIXER 3-10 VOLUME 0' in calls and not any(s=='PLAY 3-10' for s in calls)

def test_market_cache_shape_and_tide_extrema_expiry(tmp_path):
    from skycam.tides import Tides,parse,image
    from skycam.storage import save_json
    save_json(tmp_path/'broadcast'/'markets-cache.json',[])
    assert not any(r['available'] for r in Markets(tmp_path).public()['cards'])
    m=Markets(tmp_path);m.values={'fx':{'rows':[{'date':'bad','value':0}],'checked_at':'bad'},'wti':[]}
    assert not any(r['available'] for r in m.public()['cards'])
    start=datetime(2026,10,17,tzinfo=timezone.utc)
    rows=[{'eventDate':(start+timedelta(hours=6*i)).isoformat(),'value':v,'qcFlagCode':'1'} for i,v in enumerate([.6,1.3,.7,1.2,.8,1.4])]
    events=parse(rows);assert [e['kind'] for e in events]==['HIGH','LOW','HIGH','LOW']
    t=Tides(tmp_path);t.events=events;t.checked_at=start.timestamp()
    assert len(t.public(start.timestamp())['events'])==4
    assert image(t.public(start.timestamp())).size==(3840,2160)
    assert not t.public(start.timestamp()+49*3600)['available']
    rows[2]['qcFlagCode']='3'
    assert all(e['at']!=rows[2]['eventDate'] for e in parse(rows))
    with pytest.raises(ValueError):parse([{'eventDate':start.isoformat(),'value':float('nan'),'qcFlagCode':'1'}])


def test_information_block_leaves_room_before_next_weather_slot():
 from skycam.format_defaults import BLOCKS
 cues=BLOCKS['Local information']
 assert {'harbour-watch','community-calendar'} <= {row[0] for row in cues}
 assert sum(row[1] for row in cues)+len(cues)*4 < 300
