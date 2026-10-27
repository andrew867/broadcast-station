# SPDX-License-Identifier: Apache-2.0
"""Deterministic foundation checks, no feeds or credentials required."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','.venv','__pycache__','node_modules','.pytest_cache','.test-state','data','evidence'}

def verify(root=ROOT):
    errors=[];files=0
    # Build byte patterns without embedding a real installation address in this tool.
    old_hosts=[bytes(parts) for parts in ([49,48,46,50,48,49,46,49,46,49,48,49],
      [49,48,46,50,48,49,46,49,46,55,55],[49,48,46,54,52,46,54,52,46,49,52,57])]
    for path in root.rglob('*'):
        if any(part in SKIP for part in path.relative_to(root).parts):continue
        if path.is_symlink():errors.append((str(path.relative_to(root)),'symlink'));continue
        if not path.is_file():continue
        files+=1;data=path.read_bytes()
        if path.suffix in {'.key','.pem','.pfx','.p12'} or path.name=='.env':errors.append((str(path.relative_to(root)),'secret-file'))
        if any(host in data for host in old_hosts):errors.append((str(path.relative_to(root)),'private-station-address'))
        if re.search(rb'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',data):errors.append((str(path.relative_to(root)),'private-key-marker'))
        if re.search(rb'(?:rtsp|rtmp|https?)://[^\s/"<>]+:[^\s/@"<>]+@',data.replace(b'https://user:pass@example.com',b'PUBLIC_INVALID_URL_FIXTURE')):errors.append((str(path.relative_to(root)),'credential-in-url'))
    samples=root/'skycam/assets/piano-kw'
    for sample in json.loads((samples/'manifest.json').read_text())['samples']:
        if hashlib.sha256((samples/sample['file']).read_bytes()).hexdigest()!=sample['sha256']:
            errors.append((sample['file'],'piano-hash'))
    for file in ('skycam/assets/piano-kw/cc0.txt','skycam/assets/strudel-source/LICENSE',
      'skycam/static/vendor/LEAFLET-LICENSE.txt','skycam/static/fonts/Barlow-OFL.txt',
      'skycam/static/fonts/SourceSans3-OFL.txt','deploy/engine/LICENSE-CasparCG'):
        if not (root/file).is_file():errors.append((file,'missing-notice'))
    if errors:raise SystemExit(json.dumps({'errors':errors},indent=2))
    print(json.dumps({'files_checked':files,'private_station_addresses_absent':True,'credential_url_scan':True,
      'piano_hashes_verified':True,'required_notices_present':True,
      'scope':'Foundation checks only, not full secret/license clearance'},indent=2))

if __name__=='__main__':verify()
