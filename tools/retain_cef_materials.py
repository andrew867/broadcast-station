# SPDX-License-Identifier: Apache-2.0
"""Retain the exact CEF SDK notices and wrapper sources used by the engine build."""
import argparse,ctypes,hashlib,json,shutil,tarfile
from pathlib import Path

# Runtime supplied by the SHA-256-pinned upstream noble .deb in the Dockerfile.
# Its CEF revision matches the SDK, but it is not the same binary build.
PACKAGED_RUNTIME_SHA256='82ca737b46d113285f3c6590f04984f6c70773256c90553be81651cad7a81428'


def runtime_version(path):
    library=ctypes.CDLL(str(path.resolve()))
    function=library.cef_version_info
    function.argtypes=[ctypes.c_int];function.restype=ctypes.c_int
    return [function(index) for index in range(8)]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def retain(search,destination,runtime):
    candidates=[p.parent for p in search.rglob('CREDITS.html')
                if (p.parent/'include/cef_version.h').is_file() and (p.parent/'Release/libcef.so').is_file()]
    if not candidates:raise ValueError('Exact CEF SDK and bundled Chromium credits are missing')
    sdk=candidates[0]
    version=(sdk/'include/cef_version.h').read_text()
    if '142.0.17+g60aac24' not in version:raise ValueError('Unexpected CEF SDK version')
    library_hash=sha(sdk/'Release/libcef.so')
    runtime_hash=sha(runtime)
    same_binary=runtime_hash==library_hash
    versions=None
    if not same_binary:
        if runtime_hash!=PACKAGED_RUNTIME_SHA256:
            raise ValueError('Runtime CEF differs from both pinned upstream builds')
        versions=runtime_version(runtime)
        if versions!=[142,0,17,3316,142,0,7444,176]:
            raise ValueError('Unexpected packaged CEF runtime version')
    destination.mkdir(parents=True,exist_ok=True)
    for name in ('LICENSE.txt','CREDITS.html','README.txt'):
        shutil.copyfile(sdk/name,destination/name)
    shutil.copyfile(sdk/'include/cef_version.h',destination/'cef_version.h')
    parts=('include','libcef_dll','cmake','CMakeLists.txt','LICENSE.txt','README.txt')
    with tarfile.open(destination/'sdk-wrapper-source.tar.gz','w:gz') as archive:
        for name in parts:
            if not (sdk/name).exists():raise ValueError('Missing SDK build material: '+name)
            archive.add(sdk/name,arcname=name)
    metadata={'cef':'142.0.17+g60aac24','chromium':'142.0.7444.176',
              'sdk_sha256':'1d89e19b2f446105f9a1fe6fdc96bced86249b5884241dcc4013b7c94dabf424',
              'runtime_matches_sdk':same_binary,'sdk_libcef_sha256':library_hash,
              'libcef_sha256':runtime_hash,'runtime_version':versions,
              'runtime_origin':'SDK' if same_binary else 'Pinned CasparCG noble package, distinct binary build of the same CEF/Chromium revision',
              'files':{p.name:sha(p) for p in destination.iterdir() if p.is_file()},
              'scope':'Exact SDK notices, CEF wrapper/header build sources and binary identity. Full Chromium dependency checkout is obtained separately from the pinned source recipe.'}
    (destination/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('search','destination','runtime'):parser.add_argument(name,type=Path)
    args=parser.parse_args();print(json.dumps(retain(args.search,args.destination,args.runtime),indent=2))
