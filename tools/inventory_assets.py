# SPDX-License-Identifier: Apache-2.0
"""Track file provenance and the approved mixed-licence scope."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'data','evidence','node_modules','__pycache__','.git','.test-state','.pytest_cache'}
def main():
 rows=[]
 for p in sorted(ROOT.rglob('*')):
  rel=p.relative_to(ROOT);name=rel.as_posix()
  if not p.is_file() or any(x in EXCLUDE for x in rel.parts) or name in {'examples/asset-provenance.json','examples/image-inventory.json'}:continue
  scope='Project source/documentation';license='AGPL-3.0-or-later';review='Original application scope approved by maintainer';evidence=['LICENSE','LICENSING.md']
  if name.startswith('tools/') or name.startswith('.github/') or name in {'Dockerfile','Dockerfile.test'}:
   scope='Independent original build/review tool';license='Apache-2.0';review='Maintainer-approved independent tool scope';evidence=['LICENSES/Apache-2.0.txt','LICENSING.md']
  elif name.startswith('skycam/assets/piano-kw/'):
   scope='FreePats Upright Piano KW';license='CC0-1.0';review='Notice and source manifest retained';evidence=['skycam/assets/piano-kw/cc0.txt','skycam/assets/piano-kw/manifest.json']
  elif name=='skycam/assets/strudel-source/dependencies-source.tgz':
   scope='Bundled Strudel/Kabelsalat/fraction dependency source';license='AGPL-3.0-or-later AND MIT';review='Per-package licence notices retained inside archive';evidence=['examples/music-source-verification.json','skycam/assets/strudel-source/README.txt']
  elif name=='skycam/assets/strudel-source/fraction-LICENSE':
   scope='fraction.js notice';license='MIT';review='Upstream notice retained';evidence=[name]
  elif name.startswith('skycam/assets/strudel-source/') or (name.startswith('skycam/assets/') and name.endswith('arrange.mjs')):
   scope='Strudel arrangement integration';license='AGPL-3.0-or-later';review='Source archive and seeded rebuild verified; combined application distributed under AGPL';evidence=['skycam/assets/strudel-source/LICENSE','skycam/assets/strudel-source/package-lock.json']
  elif name.startswith('deploy/engine/') or name.startswith('deploy/Dockerfile.caspar'):
   scope='CasparCG native build/changes';license='GPL-3.0-or-later';review='Checksum-pinned native source and ordered patch series; build and distribution gates recorded separately';evidence=['deploy/engine/LICENSE-CasparCG']
  elif name.startswith('skycam/static/fonts/'):
   scope='Bundled typefaces';license='OFL-1.1';review='Family mapping and upstream file hashes verified; OFL notices retained';evidence=['skycam/static/fonts/Barlow-OFL.txt','skycam/static/fonts/SourceSans3-OFL.txt']
  elif name.startswith('skycam/static/vendor/'):
   scope='Leaflet';license='BSD-2-Clause';review='JS, CSS and notice match upstream Leaflet 1.9.4 archive';evidence=['skycam/static/vendor/LEAFLET-LICENSE.txt']
  elif name.startswith('samples/') or name.endswith('radar-east-reference.jpg') or name.endswith('radar-island-reference.jpg'):
   scope='Original synthetic demonstration fixture';review='Original synthetic asset under application AGPL licence'
  rows.append({'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':scope,'license_context':license,'review':review,'evidence':evidence})
 result={'scope':'File-by-file provenance and approved source licence coverage; dependency packages retain their own licences','files':rows}
 (ROOT/'examples/asset-provenance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'files':len(rows),'unassigned':sum(r['license_context']=='Unassigned' for r in rows)}))
if __name__=='__main__':main()
