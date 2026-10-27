import json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from skycam.radar_renderer import ASSETS,register_image,geographic_pixels,RadarRenderer
from skycam.sources import CameraSpec
from skycam.map_scenes import MAP_SCENES
from skycam.map_renderer import MapRenderer
import pytest
import shutil

def reference():return np.array(Image.open(ASSETS/'east-reference.jpg').convert('RGB'))
def test_registration_accepts_fixed_map_and_small_shift():
    image=reference();h,stats=register_image(image,image)
    assert h is not None and stats['inliers']>100 and stats['max_shift_px']<.1
    shifted=cv2.warpAffine(image,np.float32([[1,0,3],[0,1,2]]),(960,540))
    h,stats=register_image(image,shifted)
    assert h is not None
    p=cv2.perspectiveTransform(np.float32([[[400,300]]]),h)[0,0]
    assert np.linalg.norm(p-[403,302])<1

def test_registration_rejects_wrong_picture_and_changed_layout():
    image=reference()
    assert register_image(image,np.zeros_like(image))[0] is None
    assert register_image(image,image[:400])[0] is None
    shifted=cv2.warpAffine(image,np.float32([[1,0,80],[0,1,0]]),(960,540))
    assert register_image(image,shifted)[0] is None

def test_radar_fails_closed_for_aircraft_but_still_renders_scene(tmp_path):
    data={'healthy':True,'aircraft':[{'lat':47.57,'lon':-52.8,'track':90,'callsign':'TEST','altitude_ft':10000,'trail':[]}],'theme':{}}
    r=RadarRenderer(tmp_path,lambda:data,'east',19)
    r.basemap();image,count=r.draw(data)
    assert image.size==(3840,2160) and count==0
    r.accept((ASSETS/'east-reference.jpg').read_bytes())
    image,count=r.draw(data)
    assert count==1 and r.status['alignment']=='approximate'


def test_live_radar_requires_station_calibration_not_packaged_test_picture(tmp_path,monkeypatch):
    monkeypatch.setenv('STATION_OFFLINE','0')
    data={'healthy':True,'aircraft':[{'lat':47.57,'lon':-52.8,'track':90,'callsign':'TEST','altitude_ft':10000,'trail':[]}],'theme':{}}
    r=RadarRenderer(tmp_path,lambda:data,'east',19)
    r.accept((ASSETS/'east-reference.jpg').read_bytes())
    assert r.draw(data)[1]==0 and r.status['calibration_error']
    folder=tmp_path/'radar/calibration';folder.mkdir()
    for name in ('east.json','east-reference.jpg'):shutil.copy2(ASSETS/name,folder/name)
    r=RadarRenderer(tmp_path,lambda:data,'east',19)
    r.accept((folder/'east-reference.jpg').read_bytes())
    assert r.draw(data)[1]==1 and r.status['calibration_error'] is None
    (folder/'east.json').write_text('{}')
    r=RadarRenderer(tmp_path,lambda:data,'east',19)
    r.accept((folder/'east-reference.jpg').read_bytes())
    assert r.draw(data)[1]==0 and r.status['alignment']=='unavailable'

def test_newfoundland_extent_and_reserved_scene_ids(tmp_path):
    from skycam.map_theme import LATITUDE,LONGITUDE
    r=MapRenderer(tmp_path,lambda:{},'map-island',18,zoom=7,view_scale=.85)
    assert r.point(LATITUDE,LONGITUDE)==(1920,1080)
    for lat,lon in [(51.64,-55.43),(46.65,-53.07),(47.62,-59.3)]:
        assert r.contains(*r.point(lat,lon))
    for name in MAP_SCENES:
        with pytest.raises(ValueError):CameraSpec(id=name,name='No',media_path='cam1')
