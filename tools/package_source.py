# SPDX-License-Identifier: Apache-2.0
"""Package the reviewed source tree, never a working station's data directory."""
import argparse
import gzip
import io
import tarfile
from pathlib import Path

SKIP = {'.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache', '.test-state',
        'data', 'runtime', 'history', 'evidence', 'secrets', 'backups', 'dist', 'build'}
SECRET = {'.key', '.pem', '.p12', '.pfx', '.pyc', '.log'}


def package(root, output):
    root, output = root.resolve(), output.resolve()
    files = []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if any(part in SKIP for part in rel.parts):continue
        if path.is_symlink():raise ValueError(f'Symlink in source tree: {rel}')
        if not path.is_file() or path.resolve() == output:continue
        if path.suffix in SECRET or path.name.startswith('.env'):
            raise ValueError(f'Secret/runtime file in source tree: {rel}')
        files.append((path, rel))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w') as tar:
            for path, rel in files:
                data = path.read_bytes()
                info = tarfile.TarInfo('station-source/'+rel.as_posix())
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                tar.addfile(info, io.BytesIO(data))
    return len(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'Packaged {package(args.root, args.output)} source files')
