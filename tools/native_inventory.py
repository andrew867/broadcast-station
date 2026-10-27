# SPDX-License-Identifier: Apache-2.0
"""Collect native image build/notice evidence, without starting CasparCG."""
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path


FILES = ('usr/bin/casparcg-server-2.5', 'usr/share/station/caspar-source.tar.gz',
         'usr/share/station/LICENSE-CasparCG', 'usr/share/station/LICENSING.md',
         'usr/share/station/THIRD_PARTY_NOTICES.md', 'usr/share/station/build/Dockerfile.caspar-readback',
         'usr/share/station/build/ubuntu.sources', 'usr/lib/station/LICENSE-AGPL-3.0',
         'usr/lib/casparcg-cef-142/libcef.so', 'usr/share/doc/casparcg-cef-142/copyright',
         'usr/share/station/cef/LICENSE.txt', 'usr/share/station/cef/CREDITS.html',
         'usr/share/station/cef/manifest.json', 'usr/share/station/cef/cef_version.h',
         'usr/share/station/cef/sdk-wrapper-source.tar.gz')
HELPERS = ('cef-mallinfo-compat', 'nvdec-prefer', 'uc-image-copy')


def fingerprint(path):
    if not path.is_file():
        return {'present': False}
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return {'present': True, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def collect(root=Path('/'), package_text=None):
    files = list(FILES)+['usr/lib/station/'+name+ext for name in HELPERS for ext in ('.c', '.so')]
    records = {name: fingerprint(root/name) for name in files}
    if package_text is None:
        package_text = subprocess.check_output(['dpkg-query', '-W',
            '-f=${Package}\t${Version}\t${Architecture}\t${source:Package}\t${source:Version}\n'],
            text=True, timeout=30)
    packages = []
    for line in package_text.splitlines():
        fields = line.split('\t')
        if len(fields) != 5:
            raise ValueError('Unexpected package inventory fields')
        name, version, arch, source, source_version = fields
        # Package names come from dpkg, not arbitrary file paths.
        if '/' in name or name in ('.', '..'):
            raise ValueError('Invalid package name')
        notice = root/'usr/share/doc'/name/'copyright'
        packages.append({'name': name, 'version': version, 'architecture': arch,
                         'source_package': source or name, 'source_version': source_version or version,
                         'copyright': fingerprint(notice)})
    archive = root/'usr/share/station/caspar-source.tar.gz'
    source = {'present': archive.is_file(), 'files': 0, 'patches': []}
    if archive.is_file():
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
        source.update(files=sum(m.isfile() for m in members),
                      patches=sorted(m.name for m in members if m.isfile() and m.name.endswith('.patch')))
    ndi = []
    for folder in ('usr/lib', 'usr/local/lib', 'usr/lib/x86_64-linux-gnu', 'opt/ndi/lib'):
        ndi += [p.relative_to(root).as_posix() for p in (root/folder).glob('libndi.so*')]
    return {'schema_version': 1, 'files': records, 'os_packages': packages,
            'caspar_source_archive': source, 'ndi_runtime_matches': sorted(ndi),
            'missing_expected_files': [n for n, v in records.items() if not v['present']],
            'scope': 'Read-only hashes and installed package/source metadata. Not a complete SBOM, licence clearance or a claim that CEF/Chromium transitive notices and all corresponding dependency sources are supplied.'}


if __name__ == '__main__':
    print(json.dumps(collect(), indent=2))
