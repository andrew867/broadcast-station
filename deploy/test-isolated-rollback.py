"""Restore settings and code into a network-isolated controller."""
import hashlib,json,os,shutil,subprocess,tarfile,time
from pathlib import Path
root=Path('/srv/station')
deployment={'settings':json.loads(Path('/tmp/radio-final-settings.json').read_text())}
out=root/('restore-test-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));out.mkdir()
source=out/'source';source.mkdir()
for folder in ('skycam','samples','labs','deploy'):
    if not (root/'skycam'/folder).is_dir():continue
    shutil.copytree(root/'skycam'/folder,source/folder,ignore=shutil.ignore_patterns('__pycache__','node_modules','.pytest_cache'))
with tarfile.open(deployment['settings']['archive']) as archive:
    manifest=json.load(archive.extractfile('manifest.json'))
    for name,digest in manifest.items():
        path=(out/name).resolve()
        assert path.is_relative_to(out) and archive.getmember(name).isfile()
        path.parent.mkdir(parents=True,exist_ok=True)
        with archive.extractfile(name) as s,path.open('wb') as t:shutil.copyfileobj(s,t)
        with path.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
data=out/'data-web';saved=(data/'broadcast/rundown.json').read_bytes()
name='skycam-isolated-restore-'+str(int(time.time()))
args=['docker','run','-d','--name',name,'--network','none','--cpus','1','--memory','1200m','--read-only','--tmpfs','/tmp:rw,size=128m',
      '--user',f'{os.getuid()}:{os.getgid()}','-e','SKYCAM_PLAYOUT=0','-e','SKYCAM_DATA=/data',
      '-v',str(source)+':/app:ro','-v',str(data)+':/data','skycam-web:local','python','-m','uvicorn',
      'skycam.app:app','--host','127.0.0.1','--port','18765','--no-access-log']
subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
report={'folder':str(out),'container':name,'network':'none','native_engine_contact':False}
try:
    checks={}
    for _ in range(30):
        p=subprocess.run(['docker','exec',name,'python','-c',
          "import json,urllib.request; paths=['health','rundown','music','program-clock','ais','markets']; print(json.dumps({p:json.load(urllib.request.urlopen('http://127.0.0.1:18765/api/'+p,timeout=4)) for p in paths}))"],
          capture_output=True,text=True,timeout=35)
        if p.returncode==0:checks=json.loads(p.stdout);break
        time.sleep(1)
    assert checks,'Restored controller did not serve API'
    assert (data/'broadcast/rundown.json').read_bytes()==saved
    report.update(restore_passed=True,api_routes=list(checks),settings_files_verified=len(manifest),saved_rundown_unchanged=True,
                  camera_count=len(json.loads((data/'broadcast/cameras.json').read_text())['cameras']),
                  music_source=checks['music'].get('source'),music_mood=checks['music'].get('mood'))
    # Change only the restored operator copy, then prove source rollback keeps it.
    change="import json,urllib.request; req=urllib.request.Request('http://127.0.0.1:18765/api/music',data=json.dumps({'volume':0.17}).encode(),method='PUT',headers={'Content-Type':'application/json','X-Skycam-Edit':'1'}); print(json.load(urllib.request.urlopen(req))['volume'])"
    changed=subprocess.check_output(['docker','exec',name,'python','-c',change],text=True,timeout=15)
    assert float(changed.strip())==.17
    music_file=data/'broadcast/music.json'
    if not music_file.exists():music_file=data/'music.json'
    saved_music=music_file.read_bytes()
    app_file=source/'skycam/app.py';original=app_file.read_bytes()
    subprocess.run(['docker','stop','-t','5',name],capture_output=True,check=True)
    app_file.write_text('def deliberately_invalid_startup(:\n')
    try:
        subprocess.run(['docker','start',name],capture_output=True,check=True)
        for _ in range(15):
            time.sleep(.5)
            running=subprocess.check_output(['docker','inspect','-f','{{.State.Running}}',name],text=True).strip()
            if running=='false':break
        assert running=='false','Injected startup failure was not detected'
        report['injected_startup_failure_detected']=True
    finally:app_file.write_bytes(original)
    subprocess.run(['docker','start',name],capture_output=True,check=True)
    for _ in range(30):
        q=subprocess.run(['docker','exec',name,'python','-c',"import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:18765/api/music',timeout=3))['volume'])"],capture_output=True,text=True,timeout=10)
        if q.returncode==0:break
        time.sleep(.5)
    assert q.returncode==0 and float(q.stdout.strip())==.17
    assert music_file.read_bytes()==saved_music
    assert (data/'broadcast/rundown.json').read_bytes()==saved
    report.update(passed=True,source_rollback_passed=True,newer_operator_settings_preserved=True,restored_music_volume=.17)
finally:
    subprocess.run(['docker','stop','-t','5',name],capture_output=True)
    (out/'result.json').write_text(json.dumps(report,indent=2))
    Path('/tmp/isolated-rollback-result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
