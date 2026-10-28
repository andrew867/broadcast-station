import io,json,time,xml.etree.ElementTree as ET
import pytest
from PIL import Image
from skycam.picture_history import PictureHistory
from skycam.flight_features import Spotlight,trail_segments,altitude_color,audio_levels
from skycam.feature_scenes import FeatureScenes,FeatureConfig
from skycam.radar_renderer import RadarRenderer,ASSETS

def jpeg(color='red'):
 out=io.BytesIO();Image.new('RGB',(640,360),color).save(out,format='JPEG');return out.getvalue()

def test_history_dedup_restart_age_count_and_invalid(tmp_path):
 h=PictureHistory(tmp_path,count=3,age=60,budget=50000);now=time.time()
 assert h.add(jpeg(),now-30,deduplicate=True,metadata={'source':'test','rows':[1,2]})
 assert not h.add(jpeg(),now-20,deduplicate=True)
 assert h.add(jpeg('blue'),now-15,deduplicate=True,metadata={'source':'test','rows':[1,2]})
 assert h.add(jpeg('green'),now-10,deduplicate=True)
 assert h.add(jpeg('white'),now-5,deduplicate=True)
 assert len(h.entries())==3 and len(list(tmp_path.glob('*.jpg')))==3
 restored=PictureHistory(tmp_path,count=3,age=60,budget=50000)
 assert restored.entries()==h.entries() and restored.entries()[0]['metadata']['source']=='test'
 with pytest.raises(Exception):h.add(b'bad image')
 assert len(h.entries())==3
 h.prune(now+61);assert not h.entries() and not list(tmp_path.glob('*.jpg'))

def test_history_bytes_and_camera_identical_frames_have_new_times(tmp_path):
 h=PictureHistory(tmp_path,budget=6000);now=time.time()
 for i in range(6):h.add(jpeg(),now-10+i)
 assert len(h.entries())<6
 assert sum(p.stat().st_size for p in tmp_path.glob('*.jpg'))<=6000
 with pytest.raises(ValueError):h.add(b'x'*8_000_001)

def test_trail_never_connects_missing_interval():
 points=[{'time':t,'lat':47,'lon':-52+t/10000} for t in (1,2,20,21,22,50)]
 assert [len(s) for s in trail_segments(points,50)]==[2,3]
 assert trail_segments(points,200)==[]

def test_spotlight_stable_selection_stale_manual_and_cycle():
 s=Spotlight();planes=[{'hex':'a','stale':False},{'hex':'b','stale':False}]
 assert s.select(planes,True,0)['hex']=='a'
 assert s.select(planes[::-1],True,44)['hex']=='a'
 assert s.select(planes,True,46)['hex']=='b'
 s.manual='a';assert s.select(planes,True,47)['hex']=='a'
 planes[0]['stale']=True;assert s.select(planes,True,48) is None
 assert s.select(planes,False,49) is None

def test_altitude_palette_stale_and_native_audio_scale():
 assert altitude_color({'altitude_ft':9999})!=altitude_color({'altitude_ft':10000})
 assert altitude_color({'altitude_ft':25000})!=altitude_color({'altitude_ft':24000})
 assert altitude_color({'stale':True,'altitude_ft':25000})=='#8f999f'
 root=ET.fromstring('<channel><mixer><audio><volume>2147483647</volume><volume>1073741824</volume></audio></mixer></channel>')
 levels=audio_levels(root,100);assert levels['available'] and levels['dbfs']==[0,-6.0]
 assert not audio_levels(ET.fromstring('<channel/>'))['available']

def test_radar_archive_only_downloads_no_false_cached_history(tmp_path):
 r=RadarRenderer(tmp_path,lambda:{},'east',19)
 r.accept((ASSETS/'east-reference.jpg').read_bytes(),False)
 assert r.history.entries()==[]
 r.history.add((ASSETS/'east-reference.jpg').read_bytes(),deduplicate=True)
 assert r.history.public()['frames']==1

def test_replay_uses_saved_aircraft_and_collect_requires_fresh_decoder(tmp_path,monkeypatch):
 from skycam.sources import CAMERAS
 camera=next(iter(CAMERAS));r=RadarRenderer(tmp_path,lambda:{},'east',19)
 def fail():raise AssertionError('Historical radar must not request current aircraft')
 f=FeatureScenes(tmp_path,fail,{'radar-east':r,'radar-island':r})
 r.history.add((ASSETS/'east-reference.jpg').read_bytes(),metadata={'captured_at':time.time(),'aircraft':[{'x':500,'y':300,'angle':0,'callsign':'TEST123','altitude_ft':12000,'category':'A3','stale':False}]})
 assert f.replay_image('radar-history-east',0).size==(3840,2160)
 assert r.history.entries()[0]['metadata']['aircraft'][0]['callsign']=='TEST123'
 path=f.thumbnail(camera);path.parent.mkdir(parents=True);path.write_bytes(jpeg())
 health={'checked_at':time.time(),'cameras':{camera:{'ready':False,'state':'reconnecting'}}}
 (tmp_path/'source-health.json').write_text(json.dumps(health));f.collect();assert not f.history(camera).entries()
 health['cameras'][camera]={'ready':True,'state':'ready'};(tmp_path/'source-health.json').write_text(json.dumps(health));f.last_collect=0;f.collect()
 assert len(f.history(camera).entries())==1
 assert f.confidence()['sources'][0]['fresh']
 health['checked_at']=time.time()-30;(tmp_path/'source-health.json').write_text(json.dumps(health))
 assert not f.confidence()['sources'][0]['fresh']
 with pytest.raises(ValueError):f.save(FeatureConfig(timelapse_camera='missing'))
 assert f.replay_image('camera-timelapse',1).size==(3840,2160)
def test_history_future_timestamp_and_combined_retired_budget(tmp_path):
 from skycam.picture_history import enforce_budget
 a=PictureHistory(tmp_path/'a');b=PictureHistory(tmp_path/'b');now=time.time()
 a.add(jpeg(),now-10);b.add(jpeg('blue'),now-5)
 with pytest.raises(ValueError):a.add(jpeg(),now+60)
 enforce_budget([a,b],sum(p.stat().st_size for p in (tmp_path/'b').glob('*.jpg')))
 assert a.entries()==[] and len(b.entries())==1


def test_ocean_rgba_map_writes_program_and_jpeg_preview(tmp_path,monkeypatch):
 from PIL import Image
 import time
 f=FeatureScenes(tmp_path,lambda:{}, {})
 f.ocean.base=Image.new('RGBA',(3840,2160),'#223344');f.ocean.built_at=time.time()
 monkeypatch.setattr(f.ocean,'draw',lambda data:(f.ocean.base,{}))
 path=f.path('map-ocean')
 with Image.open(path) as im:assert im.size==(1920,1080)
 with Image.open(f.folder/'map-ocean.jpg') as im:assert im.mode=='RGB' and im.size==(960,540)


def test_radar_snapshot_records_received_positions_not_claimed_observation_time(tmp_path):
 plane={'lat':47.4,'lon':-52.7,'callsign':'TEST123','hex':'abc123','altitude_ft':12000,'category':'A3','stale':False,'age_s':3,'track':90}
 r=RadarRenderer(tmp_path,lambda:{'aircraft':[plane],'healthy':True},'east',19)
 r.accept((ASSETS/'east-reference.jpg').read_bytes(),False)
 snapshot=r.aircraft_snapshot(time.time())
 assert snapshot['receiver_healthy'] is True
 assert 'radar observation time remains' in snapshot['timing']
 assert len(snapshot['aircraft'])<=1
