# SPDX-License-Identifier: Apache-2.0
"""Make a platform-specific, wheel-only hash lock from pip's resolver report."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def render(report):
    env = report['environment']
    if (env['sys_platform'], env['platform_machine'], env['python_version']) != ('linux', 'x86_64', '3.13'):
        raise ValueError('This lock target is Linux x86_64 / CPython 3.13 only')
    rows = []
    for item in report['install']:
        metadata, download = item['metadata'], item['download_info']
        url = urlsplit(download['url'])
        digest = download.get('archive_info', {}).get('hashes', {}).get('sha256', '')
        name, version = metadata['name'], metadata['version']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or not re.fullmatch(r'[A-Za-z0-9_.+!-]+', version):
            raise ValueError('Invalid package identity')
        if url.scheme != 'https' or url.hostname != 'files.pythonhosted.org' or url.username or not url.path.endswith('.whl'):
            raise ValueError(f'Unexpected artifact for {name}')
        if not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise ValueError(f'Missing SHA256 for {name}')
        rows.append(f'{name}=={version} --hash=sha256:{digest}')
    if not rows:
        raise ValueError('Empty resolution')
    return '# Generated from pip --dry-run --ignore-installed --only-binary=:all: --report\n# Target: Linux x86_64, CPython 3.13. Regenerate and test deliberately.\n' + '\n'.join(sorted(rows, key=str.lower)) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    text = render(json.loads(args.report.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding='utf-8', newline='\n')
