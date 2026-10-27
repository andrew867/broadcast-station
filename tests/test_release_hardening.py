import shutil,subprocess
from pathlib import Path
import pytest
from skycam.media_probe import video_poster
from skycam.alerts import Alerts,HOSTS
from tests.test_alerts import message,NOW

def test_disabled_alerts_do_not_restore_or_present_saved_messages(tmp_path):
    live=Alerts(tmp_path,verifier=lambda _: {'verified':True})
    live.ingest(message(expires='2099-10-17T18:00:00Z'),HOSTS[0],NOW);live.persist()
    disabled=Alerts(tmp_path,enabled=False,verifier=lambda _: pytest.fail('Disabled receiver verified an alert'))
    disabled.ingest(message(),HOSTS[0],NOW)
    assert not disabled.items and not disabled.public(NOW)['alerts'] and not disabled.public(NOW)['immediate']
    assert disabled.public(NOW)['automatic_playout'] is False


def test_disabled_outages_ignore_saved_incidents(tmp_path):
    import json,asyncio
    from skycam.outages import Outages
    (tmp_path/'broadcast').mkdir()
    (tmp_path/'broadcast/outages-cache.json').write_text(json.dumps({'rows':[{'private':'old incident'}],'checked_at':NOW}))
    disabled=Outages(tmp_path,enabled=False)
    asyncio.run(disabled.refresh())
    assert disabled.public(NOW)['active']==[] and disabled.banner(NOW) is None


def test_error_messages_exclude_command_lines_and_endpoints():
    from skycam.public_errors import public_error
    assert public_error(subprocess.CalledProcessError(1,['ffmpeg','private-stream']))=='Media operation failed'
    assert public_error(FileNotFoundError('/home/operator/private'))=='Local service or file operation failed'
    message=public_error(ValueError('Failed https://example.com/path?token=PRIVATE token=SECRET /home/operator/key'))
    assert all(part not in message for part in ('PRIVATE','SECRET','operator'))

def test_video_timeout_has_no_decoder_details(tmp_path,monkeypatch):
    def fail(*args,**kwargs):raise subprocess.TimeoutExpired(['secret-media-url'],12)
    monkeypatch.setattr('skycam.media_probe.bounded_process',fail)
    with pytest.raises(ValueError,match='time limit') as error:video_poster(tmp_path/'upload.mp4')
    assert 'secret' not in str(error.value)


def test_decoder_output_and_runtime_are_bounded():
    import sys
    from skycam.media_probe import bounded_process
    with pytest.raises(ValueError,match='output exceeds'):
        bounded_process([sys.executable,'-c','import sys;sys.stdout.write("x"*1000000)'],1000)
    with pytest.raises(subprocess.TimeoutExpired):
        bounded_process([sys.executable,'-c','import time;time.sleep(30)'],1000,timeout=.1)

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_real_h264_upload_is_bounded_and_decodes(tmp_path):
    path=tmp_path/'test.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x180:r=30','-t','1.2','-c:v','libx264','-threads','1',str(path)],check=True,timeout=20)
    w,h,fps,duration,poster=video_poster(path)
    assert (w,h)==(320,180) and fps==30 and 1<=duration<2 and poster.size==(1920,1080)


def test_validation_errors_do_not_echo_submitted_values(monkeypatch):
    import asyncio,httpx
    from skycam.app import app
    monkeypatch.setenv('STATION_OFFLINE','0')
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver') as client:
            result=await client.post('/api/solve',headers={'X-Skycam-Edit':'1'},json={'width':'PRIVATE_INPUT_VALUE'})
            assert result.status_code==422 and 'PRIVATE_INPUT_VALUE' not in result.text
            assert all('input' not in row and 'ctx' not in row for row in result.json()['detail'])
    asyncio.run(check())
