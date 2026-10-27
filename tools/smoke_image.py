# SPDX-License-Identifier: Apache-2.0
"""Check a built preview image with no network, GPU or production mounts."""
import argparse
import subprocess
import uuid


def run(*args):
    result=subprocess.run(args,check=True,capture_output=True,text=True)
    return result.stdout.strip()


def main(image):
    name='station-preview-'+uuid.uuid4().hex[:12]
    run('docker','run','--detach','--name',name,'--network','none','--cpus','1','--memory','1g',
        '--read-only','--tmpfs','/tmp:rw,size=128m','--tmpfs','/app/data:uid=10001,gid=10001',image)
    try:
        script='''import urllib.request,urllib.error,json,time,tarfile,io,hashlib
from pathlib import Path
for _ in range(30):
 try:
  mode=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/release-mode',timeout=2));break
 except OSError:time.sleep(1)
else:raise RuntimeError('Preview startup timed out')
assert mode=={'offline':True,'playout':False,'release_ready':False},mode
html=urllib.request.urlopen('http://127.0.0.1:8765/studio').read().decode()
assert 'href="/source"' in html
try:urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/api/source-catalog/cam1/probe',data=b'',headers={'x-skycam-edit':'1'}))
except urllib.error.HTTPError as error:assert error.code==503
else:raise AssertionError('Preview accepted a write')
data=urllib.request.urlopen('http://127.0.0.1:8765/source').read()
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 names=archive.getnames()
 assert 'station-source/LICENSE' in names
 assert 'station-source/requirements-linux-x86_64.lock' in names
 assert 'station-source/skycam/assets/strudel-source/dependencies-source.tgz' in names
 assert not any('/data/' in name or '/.git/' in name or name.endswith('.key') for name in names)
 for relative in ('skycam/app.py','skycam/source_delivery.py','skycam/assets/strudel-arrange.mjs'):
  assert archive.extractfile('station-source/'+relative).read()==Path('/app',relative).read_bytes()
print(json.dumps({'offline_startup':True,'writes_blocked':True,'source_matches_image':True,'source_files':len(names),'source_sha256':hashlib.sha256(data).hexdigest()}))
'''
        print(run('docker','exec',name,'python','-c',script))
    finally:
        run('docker','rm','-f',name)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',nargs='?',default='station-foundation:test')
    main(parser.parse_args().image)
