# SPDX-License-Identifier: Apache-2.0
"""Record installed Python dependency evidence and bundled Node licence metadata."""
from importlib import metadata
from pathlib import Path
import json
from packaging.requirements import Requirement

ROOT=Path(__file__).resolve().parents[1]

def inventory():
    pending=[]
    for line in (ROOT/'requirements.txt').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            req=Requirement(line)
            if req.marker is None or req.marker.evaluate():pending.append(req.name)
    found={};missing=[]
    while pending:
        name=pending.pop().lower().replace('_','-')
        if name in found:continue
        try:dist=metadata.distribution(name)
        except metadata.PackageNotFoundError:missing.append(name);continue
        licences=[str(p) for p in (dist.files or []) if 'license' in str(p).lower() or 'licence' in str(p).lower() or 'copying' in str(p).lower()]
        expression=dist.metadata.get('License-Expression')
        classifiers=[v for v in dist.metadata.get_all('Classifier',[]) if v.startswith('License ::')]
        found[name]={'version':dist.version,'license_expression':expression,'license_classifiers':classifiers,'notice_files':licences}
        for text in dist.requires or []:
            req=Requirement(text)
            if req.marker is None or req.marker.evaluate({'extra':''}):pending.append(req.name)
    lock=json.loads((ROOT/'skycam/assets/strudel-source/package-lock.json').read_text())
    node=[{'path':path,'version':row.get('version'),'license':row.get('license'),'integrity':row.get('integrity')} for path,row in lock.get('packages',{}).items() if path]
    result={'status':'Evidence inventory, not publication clearance or portable dependency lock',
      'python_scope':'Installed environment, runtime dependency closure with current-platform markers',
      'python':dict(sorted(found.items())),'missing_installed_dependencies':missing,'node_lock_packages':node,
      'original_application_license':'AGPL-3.0-or-later application; Apache-2.0 independent tools; see LICENSING.md',
      'copyleft_paths':{'deploy/engine':'CasparCG GPL context; see bundled licence',
      'skycam/assets/strudel-source':'AGPL-3.0-or-later declared by source package',
      'skycam/assets/*arrange.mjs':'Bundled Strudel-derived output, retains source licence obligations'},
      'remaining':['Full broadcast image inventory and binary distribution belong to the hardware/release tranches; this is the offline preview runtime closure']}
    target=ROOT/'examples/component-inventory.json';target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'python_packages':len(found),'node_packages':len(node),'missing':missing,'output':str(target)}))

if __name__=='__main__':inventory()
