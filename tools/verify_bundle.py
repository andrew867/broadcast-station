# SPDX-License-Identifier: Apache-2.0
"""Verify a downloaded release bundle before optionally loading its Docker images."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def verify(folder):
    folder = Path(folder).resolve(strict=True)
    manifest = folder / 'release.json'
    if manifest.is_symlink() or manifest.stat().st_size > 1024 * 1024:
        raise ValueError('Invalid release manifest')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z0-9.]+)?', data.get('version', '')):
        raise ValueError('Unsupported release manifest')
    assets = data.get('assets', [])
    if not isinstance(assets, list) or not 1 <= len(assets) <= 500:
        raise ValueError('Invalid asset list')
    names = set()
    for asset in assets:
        name = asset.get('name', '')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,180}', name) or name in names:
            raise ValueError('Unsafe or duplicate asset name')
        names.add(name)
        path = folder / name
        expected = asset.get('sha256', '')
        if not re.fullmatch('[0-9a-f]{64}', expected) or type(asset.get('bytes')) is not int or asset['bytes'] < 0:
            raise ValueError('Invalid asset identity')
        if path.is_symlink() or not path.is_file() or path.stat().st_size != asset['bytes']:
            raise ValueError('Missing or wrong-sized asset: ' + name)
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != expected:
            raise ValueError('Checksum mismatch: ' + name)
    images = data.get('images', {})
    if set(images) != {'controller', 'engine'}:
        raise ValueError('Both image identities are required')
    for role, image in images.items():
        if image.get('asset') not in names or image.get('tag') != 'station-' + role + ':' + data['version']:
            raise ValueError('Invalid image reference')
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image.get('id', '')):
            raise ValueError('Invalid image identity')
    return data


def load_images(folder, data):
    for role in ('controller', 'engine'):
        image = data['images'][role]
        subprocess.run(['docker', 'image', 'load', '--input', str(Path(folder) / image['asset'])], check=True)
        identity = subprocess.check_output(['docker', 'image', 'inspect', image['tag'], '--format', '{{.Id}}'], text=True).strip()
        if identity != image['id']:
            raise ValueError('Loaded image identity differs: ' + role)
        # Docker's containerd backend can retain the image identity and return
        # success after reporting an unpack error. Exercise the root filesystem
        # before calling the image usable; this does not start station services.
        subprocess.run(['docker', 'run', '--rm', '--pull', 'never', '--network', 'none',
                        '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                        '--user', '65534:65534', '--entrypoint', '/bin/true', image['id']], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--load-images', action='store_true', help='Load verified images without starting containers')
    args = parser.parse_args()
    result = verify(args.folder)
    if args.load_images:
        load_images(args.folder.resolve(), result)
    print(json.dumps({'version': result['version'], 'verified_assets': len(result['assets']), 'images_loaded': args.load_images,
                      'scope': 'Integrity against the supplied manifest; not publisher authentication or hardware acceptance'}))
