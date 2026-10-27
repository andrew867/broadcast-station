# SPDX-License-Identifier: Apache-2.0
"""Installed Linux image inventory. Metadata evidence, not a licence clearance."""
import hashlib,json,platform,subprocess,sys
from importlib import metadata
from pathlib import Path

def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=20).stdout.strip()
def inventory():
    packages=[]
    for line in command('dpkg-query','-W','-f=${Package}\t${Version}\t${Architecture}\t${source:Package}\t${source:Version}\n').splitlines():
        name,version,arch,source,source_version=line.split('\t');notice=Path('/usr/share/doc')/name/'copyright'
        packages.append({'name':name,'version':version,'architecture':arch,'source_package':source or name,'source_version':source_version or version,'copyright_file':str(notice) if notice.is_file() else None,'copyright_sha256':hashlib.sha256(notice.read_bytes()).hexdigest() if notice.is_file() else None})
    python=[]
    for dist in sorted(metadata.distributions(),key=lambda d:d.metadata['Name'].lower()):
        notices=[]
        for file in dist.files or []:
            if any(token in str(file).lower() for token in ('license','copying','notice')):
                path=dist.locate_file(file)
                if path.is_file():notices.append({'path':str(file),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        python.append({'name':dist.metadata['Name'],'version':dist.version,'license_expression':dist.metadata.get('License-Expression'),'notices':notices})
    runtime_files={}
    for name in ('/usr/local/bin/mediamtx','/usr/share/doc/mediamtx/LICENSE',sys.executable,
                 '/usr/local/lib/python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'/LICENSE.txt'):
        path=Path(name)
        if path.is_file():
            with path.open('rb') as stream:runtime_files[name]={'bytes':path.stat().st_size,'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
        else:runtime_files[name]={'missing':True}
    return {'scope':'Installed OS/Python package metadata and notice hashes, not a complete file SBOM or legal clearance',
      'runtime_files':runtime_files,
      'python_runtime':sys.version,'machine':platform.machine(),'os_release':Path('/etc/os-release').read_text(),
      'node':command('node','--version'),'ffmpeg':command('ffmpeg','-version').splitlines()[0],
      'os_packages':packages,'python_packages':python}
if __name__=='__main__':print(json.dumps(inventory(),indent=2))
