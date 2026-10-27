import json
import math
import time
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from skycam.geometry import ecef, enu_rotation, project
from skycam.calibration import solve
from skycam.models import CameraRequest
from skycam.tracking import Tracks
from tests.fixtures import scene, geodetic


def test_ecef_axes_and_enu_basis():
    assert np.allclose(ecef(0,0,0),[6378137,0,0])
    assert np.allclose(ecef(0,90,100),[0,6378237,0])
    assert np.allclose(ecef(90,0,0),[0,0,6356752.314245],atol=1e-5)
    basis=enu_rotation(47.0,-52.0)
    assert np.allclose(basis@basis.T,np.eye(3))
    assert np.linalg.det(basis)==pytest.approx(1)


def test_projection_center_and_behind():
    c={'K':[[1000,0,960],[0,1000,540],[0,0,1]],'rvec':[0,0,0],'distortion':[0]*5}
    uv,z=project([[0,0,100],[10,0,100],[0,0,-100]],c)
    assert np.allclose(uv[:2],[[960,540],[1060,540]])
    assert z[-1]<0


def test_earth_curvature_not_flat_earth():
    origin=ecef(0,0,0)
    enu=enu_rotation(0,0)@(ecef(0,1,0)-origin)
    assert enu[2] < -900


def test_calibration_recovers_pose_fov_distortion():
    req,true=scene()
    fitted=solve(req)
    assert fitted['acceptable'],fitted['warnings']
    assert fitted['rms_px']<.01
    assert fitted['validation_rms_px']<.01
    assert fitted['K'][0][0]==pytest.approx(true['K'][0][0],abs=.1)
    assert fitted['distortion'][:2]==pytest.approx(true['distortion'][:2],abs=.001)


def test_outlier_is_visible_and_blocks_approval():
    req,_=scene(outlier=True)
    fitted=solve(req)
    assert not fitted['acceptable']
    assert fitted['max_error_px']>50
    assert fitted['validation_rms_px']<5


def test_skyline_degeneracy_rejected():
    req,_=scene()
    for p in req.landmarks:
        p.y=300
    with pytest.raises(ValueError,match='coverage'):
        solve(req)


def test_provisional_site_not_approved():
    req,_=scene()
    req.site.verified=False
    req.site.geoid_separation_m=None
    fitted=solve(req)
    assert not fitted['acceptable']
    assert any('geoid' in x for x in fitted['warnings'])


def aircraft(**kw):
    return {'hex':'abc123','flight':'TEST123','lat':47.6,'lon':-52.7,'alt_geom':10000,
            'alt_baro':9500,'seen_pos':0.,'gs':200,'track':90.,'geom_rate':0.,**kw}


def test_freshness_units_interpolation_and_extrapolation():
    t=Tracks();now=time.time()
    t.ingest({'now':now-1,'aircraft':[aircraft(lon=-52.701)]},now=now-1)
    t.ingest({'now':now,'aircraft':[aircraft()]},now=now)
    a=t.positions(now-.5,now)[0]
    assert a['mode']=='interpolated'
    assert np.allclose(a['pos'],(ecef(47.6,-52.701,3048)+ecef(47.6,-52.7,3048))/2)
    b=t.positions(now+1,now+1)[0]
    assert b['mode']=='extrapolated'
    assert np.linalg.norm(b['pos']-ecef(47.6,-52.7,3048))==pytest.approx(200*.514444)
    assert t.positions(now+2.01,now+2.01)==[]
    assert t.positions(now+4,now+4)==[]
    assert t.positions(now-2,now)==[]


@pytest.mark.parametrize('bad',[{'alt_geom':None},{'alt_geom':float('nan')},{'seen_pos':8},
                              {'alt_baro':'ground'},{'mlat':['lat','lon']},{'lat':91},{'tisb':['lat']}])
def test_invalid_aircraft_suppressed(bad):
    t=Tracks();now=time.time();t.ingest({'now':now,'aircraft':[aircraft(**bad)]},now)
    assert not t.positions(now,now)


def test_feed_failure_and_frozen_timestamp():
    t=Tracks();now=time.time();t.ingest({'now':now,'aircraft':[aircraft()]},now)
    t.error='offline'
    assert not t.positions(now,now)
    with pytest.raises(ValueError,match='stale'):
        t.ingest({'now':now,'aircraft':[]},now+4)
    with pytest.raises(ValueError,match='ahead'):
        t.ingest({'now':now+10,'aircraft':[]},now)


def test_no_extrapolation_without_velocity_or_past_gap():
    t=Tracks();now=time.time();t.ingest({'now':now,'aircraft':[aircraft(geom_rate=None)]},now)
    assert t.positions(now+.5,now+.5)==[]
    assert len(t.positions(now+.1,now+.1))==1


def test_duplicate_positions_do_not_create_new_measurements():
    t=Tracks();now=time.time();t.ingest({'now':now,'aircraft':[aircraft()]},now)
    t.ingest({'now':now+1,'aircraft':[aircraft(seen_pos=1)]},now+1)
    assert len(t.history['abc123'])==1


def test_api_roundtrip_and_gates(tmp_path,monkeypatch):
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    monkeypatch.setattr(module,'DATA',tmp_path)
    client=TestClient(module.app)
    req,_=scene();body=req.model_dump()
    assert client.put('/api/cameras/test',json=body).status_code==403
    headers={'X-Skycam-Edit':'1'}
    draft=CameraRequest(name='Draft').model_dump()
    r=client.put('/api/cameras/draft',json=draft,headers=headers)
    assert r.status_code==200
    assert client.get('/api/frame/draft').json()['state']=='uncalibrated'
    draft['approved']=True
    assert client.put('/api/cameras/draft',json=draft,headers=headers).status_code==422
    body['approved']=True
    r=client.put('/api/cameras/test',json=body,headers=headers)
    assert r.status_code==200,r.text
    assert client.get('/api/cameras/test').json()['request']['approved']
    body['video_delay_s']=2
    assert client.put('/api/cameras/test',json=body,headers=headers).status_code==200
    assert len(list((tmp_path/'revisions').glob('*.json')))==1
    assert client.get('/api/frame/test').json()['labels']==[]
    assert client.put('/api/cameras/test',json=body,headers={**headers,'Origin':'https://example.org'}).status_code==403
    incomplete={**body,'approved':False,'landmarks':body['landmarks'][:2]}
    r=client.put('/api/cameras/incomplete',json=incomplete,headers=headers)
    assert r.status_code==200
    assert r.json()['calibration'] is None
    assert 'at least' in r.json()['calibration_error']


def test_live_frame_projection_and_loss(tmp_path,monkeypatch):
    import cv2
    from skycam import app as module
    from skycam.geometry import site_frame
    monkeypatch.setattr(module,'DATA',tmp_path)
    req,true=scene();req.approved=True
    result=solve(req)
    (tmp_path/'test.json').write_text(json.dumps({'request':req.model_dump(),'calibration':result}))
    origin,basis=site_frame(req.site)
    forward=cv2.Rodrigues(np.array(true['rvec']))[0][2]
    lat,lon,alt=geodetic(origin+basis.T@(forward*10000))
    t=Tracks();now=time.time()
    a=aircraft(lat=lat,lon=lon,alt_geom=alt/.3048,gs=0)
    t.ingest({'now':now-2,'aircraft':[a]},now-2)
    t.ingest({'now':now,'aircraft':[a]},now)
    monkeypatch.setattr(module,'tracks',t)
    client=TestClient(module.app)
    frame=client.get('/api/frame/test').json()
    assert frame['state']=='live'
    assert len(frame['labels'])==1
    assert frame['labels'][0]['x']==pytest.approx(640,abs=.01)
    assert frame['labels'][0]['y']==pytest.approx(360,abs=.01)
    t.error='Connection lost'
    frame=client.get('/api/frame/test').json()
    assert frame['state']=='feed_unavailable' and frame['labels']==[]


def test_synthetic_provider_schema_parses():
    path=Path(__file__).parent/'fixtures/aircraft-synthetic.json'
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    t=Tracks();t.ingest(data,now=data['now'])
    assert t.count>0
    assert len(t.history)>0
    assert len(t.positions(data['now'],now=data['now']))>0
