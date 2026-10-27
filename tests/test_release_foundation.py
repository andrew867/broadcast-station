import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from skycam.branding import Branding, branded_html


def test_brand_fields_validate_and_remain_independent():
    b=Branding(product_name='Control Desk',station_name='Local Channel',station_short='LOCAL')
    assert b.product_name!=b.station_name and b.station_short=='LOCAL'
    assert b.fingerprint()!=Branding().fingerprint()
    for values in ({'accent':'red;display:none'}, {'logo_asset':'../secret.png'},
                   {'logo_asset':'https://example.com/logo.png'}, {'station_name':'line\nbreak'},
                   {'product_name':' '}, {'unknown':'oops'}):
        with pytest.raises(ValueError):Branding(**values)


def test_brand_html_escapes_operator_text(tmp_path,monkeypatch):
    import skycam.branding as module
    monkeypatch.setattr(module,'BRAND',Branding(product_name='<script>alert(1)</script>'))
    page=tmp_path/'index.html';page.write_text('<title>[[product_name]]</title>')
    content=branded_html(page).body.decode()
    assert '<script>' not in content and '&lt;script&gt;' in content


def test_offline_guard_rejects_tcp_dns_and_datagram_in_child():
    script='''from skycam.network_policy import install_offline_guard
import socket
install_offline_guard()
calls=[lambda:socket.getaddrinfo('example.com',80),
 lambda:socket.socket().connect(('127.0.0.1',5250)),
 lambda:socket.socket().connect_ex(('192.0.2.10',8554)),
 lambda:socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b'x',('192.0.2.10',53))]
for call in calls:
 try:call()
 except OSError as error:assert 'disabled' in str(error)
 else:raise AssertionError('Outbound request escaped offline mode')
'''
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr


def test_offline_app_lifespan_has_no_background_feed_tasks(tmp_path):
    script='''import asyncio
from skycam.app import app,lifespan,playout
async def check():
 before=set(asyncio.all_tasks())
 async with lifespan(app):
  assert not playout.ENABLED
  assert set(asyncio.all_tasks())==before
asyncio.run(check())
'''
    env={**os.environ,'SKYCAM_DATA':str(tmp_path),'STATION_OFFLINE':'1','SKYCAM_PLAYOUT':'1'}
    result=subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,timeout=25)
    assert result.returncode==0,result.stderr


def test_sample_assets_are_demo_not_private_photographs():
    from PIL import Image
    root=Path(__file__).resolve().parents[1]
    for path in (root/'samples').glob('*.png'):
        with Image.open(path) as im:
            assert im.size==(1280,720) and im.getpixel((10,10))==(64,93,107)


def test_native_brand_change_invalidates_graphic_cache(tmp_path,monkeypatch):
    from skycam import graphics
    from skycam.broadcast import BroadcastState
    monkeypatch.setattr(graphics,'DATA',tmp_path)
    first=graphics.render(BroadcastState(camera='cam1'))
    monkeypatch.setattr(graphics,'BRAND',Branding(station_short='REPLACED'))
    second=graphics.render(BroadcastState(camera='cam1'))
    assert first!=second and first.read_bytes()!=second.read_bytes()


def test_offline_http_rejects_source_actions():
    import asyncio
    import httpx
    from skycam.app import app
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/source-catalog/cam1/probe',headers={'x-skycam-edit':'1'})
            assert response.status_code==503 and 'read-only' in response.json()['detail']
            assert (await client.get('/api/branding')).json()['product_name']=='Station'
    asyncio.run(check())


def test_long_station_wordmark_fits_ticker():
    from PIL import Image,ImageDraw
    from skycam.graphics import fit
    draw=ImageDraw.Draw(Image.new('RGB',(560,224)))
    text='W'*24
    face=fit(draw,text,68,340,minimum=12)
    assert draw.textlength(text,font=face)<=340
