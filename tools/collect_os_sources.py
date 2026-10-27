# SPDX-License-Identifier: Apache-2.0
"""Download exact Debian/Ubuntu source packages from configured authenticated apt repositories.

Run in a disposable build container with matching deb-src repositories, never on
a live station. This downloads source archives; it does not install or build them.
"""
import argparse,hashlib,json,re,subprocess,time
from pathlib import Path

CUSTOM={'casparcg-server-2.5','casparcg-cef-142'}


def packages(inventory):
    result=set()
    for row in inventory['os_packages']:
        name=row['source_package'];version=row['source_version']
        if name in CUSTOM:continue
        if not re.fullmatch(r'[a-z0-9][a-z0-9+.-]{0,100}',name) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+:~_-]{0,150}',version):
            raise ValueError('Invalid source package identity')
        result.add((name,version))
    return sorted(result)


def collect(inventory,destination):
    destination.mkdir(parents=True,exist_ok=True);rows=[]
    identities=packages(inventory)
    for name,version in identities:
        folder=destination/name;folder.mkdir(exist_ok=True)
        with (folder/'fetch.log').open('w') as log:
            try:
                code=subprocess.run(['apt-get','-o','Acquire::Retries=2','source','--download-only','--only-source',name+'='+version],cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=600).returncode
            except subprocess.TimeoutExpired:code=124
        files={}
        for path in folder.iterdir():
            if path.is_file() and path.name!='fetch.log':
                with path.open('rb') as stream:files[path.name]={'sha256':hashlib.file_digest(stream,'sha256').hexdigest(),'bytes':path.stat().st_size}
        row={'source_package':name,'source_version':version,'exit_code':code,'files':files,
             'downloaded':code==0 and any(n.endswith('.dsc') for n in files)}
        rows.append(row)
        report={'created_at':time.time(),'requested':len(identities),'processed':len(rows),'complete':len(rows)==len(identities) and all(r['downloaded'] for r in rows),'packages':rows,'separate_sources':sorted(CUSTOM)}
        temporary=destination/'source-manifest.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(destination/'source-manifest.json')
        print(name,version,'OK' if row['downloaded'] else 'FAILED',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('inventory',type=Path);parser.add_argument('destination',type=Path);args=parser.parse_args()
    report=collect(json.loads(args.inventory.read_text()),args.destination)
    raise SystemExit(0 if report['complete'] else 1)
