# SPDX-License-Identifier: Apache-2.0
"""Check the engine source checksum and patch sequence, without building or running it.

Download the URL in deploy/Dockerfile.caspar-readback separately, then supply
--archive. Only a fresh --output directory is accepted. Requires POSIX patch.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def verify(archive, output):
    recipe = (ROOT/'deploy/Dockerfile.caspar-readback').read_text(encoding='utf-8')
    digest = re.search(r"echo '([a-f0-9]{64})  server.tar.gz'", recipe).group(1)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
        raise ValueError('Upstream archive checksum mismatch')
    output.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as tar:
        total = 0
        seen = set()
        for member in tar:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or '\\' in member.name or member.name in seen:
                raise ValueError('Unsafe or duplicate source archive path')
            seen.add(member.name)
            if not (member.isdir() or member.isfile()):
                raise ValueError('Source archive links/devices are not accepted')
            total += member.size
            if total > 250_000_000:
                raise ValueError('Source exceeds extraction budget')
        tar.extractall(output, filter='data')
    source = output/'server-2.5.1-stable'
    patches = re.findall(r'patch -p1 < ../([a-z0-9-]+\.patch)', recipe)
    results = []
    for patch in patches:
        if patch == 'idle-graphics-cache.patch':
            shutil.copyfile(ROOT/'deploy/engine/idle_cache.h', source/'src/accelerator/ogl/util/idle_cache.h')
        data = (ROOT/'deploy/engine'/patch).read_bytes()
        result = subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1'],
                                cwd=source, input=data, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f'{patch}: {result.stderr.decode(errors="replace")} {result.stdout.decode(errors="replace")}')
        changed = re.findall(r'^\+\+\+ b/(\S+)', data.decode('utf-8'), re.M)
        results.append({'patch':patch, 'sha256':hashlib.sha256(data).hexdigest(), 'files':changed})
    paths = sorted({name for result in results for name in result['files']} | {'src/accelerator/ogl/util/idle_cache.h'})
    return {'scope':'Checksum and zero-fuzz patch application; no binary build or licence clearance',
            'upstream_url':re.search(r'curl -fsSL (https://\S+) -o server.tar.gz', recipe).group(1),
            'upstream_sha256':digest, 'patches':results,
            'modified_files':[{'file':name,'sha256':hashlib.sha256((source/name).read_bytes()).hexdigest()} for name in paths]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.output), indent=2))
