# SPDX-License-Identifier: Apache-2.0
"""Verify the shipped music source archive and optionally an npm ci installation."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def verify(installed=None):
    evidence = json.loads((ROOT/'examples/music-source-verification.json').read_text(encoding='utf-8'))
    bundle = ROOT/'skycam/assets/strudel-arrange.mjs'
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == evidence['bundle_sha256'], 'Bundle digest mismatch'
    expected = {row['file']:row['sha256'] for row in evidence['archived_source_files']}
    seen = set()
    total = 0
    with tarfile.open(ROOT/'skycam/assets/strudel-source/dependencies-source.tgz') as archive:
        for item in archive:
            name = PurePosixPath(item.name)
            assert not name.is_absolute() and '..' not in name.parts and '\\' not in item.name, 'Unsafe archive path'
            if item.isdir():
                continue
            assert item.isfile() and item.name not in seen, 'Non-file or duplicate archive member'
            total += item.size
            assert total <= 5_000_000, 'Source archive exceeds its review budget'
            content = archive.extractfile(item).read()
            assert hashlib.sha256(content).hexdigest() == expected.get(item.name), f'Source digest mismatch: {item.name}'
            if installed:
                assert (installed/item.name).read_bytes() == content, f'npm/source mismatch: {item.name}'
            seen.add(item.name)
    assert seen == expected.keys(), 'Source manifest membership mismatch'
    return {'source_files':len(seen), 'expanded_bytes':total, 'bundle_hash_verified':True,
            'npm_installation_compared':bool(installed)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', type=Path, help='node_modules from npm ci')
    print(json.dumps(verify(parser.parse_args().installed), indent=2))
