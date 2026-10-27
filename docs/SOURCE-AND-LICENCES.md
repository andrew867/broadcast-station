# Source code and licences

The original application is AGPL-3.0-or-later, with independent Apache-2.0 tools
and separately licensed dependencies. See [licensing](../LICENSING.md) for the exact scope.

The studio and guide link to `/source`. Docker builds package the reviewed
source tree into `/app/source/station-source.tar.gz`; the HTTP route serves
that fixed artifact. It does not archive the live filesystem or expose station
settings. The archive includes source, build recipes, locks, tests, notices and
source for the bundled music worker. Runtime data, credentials, logs, caches
and Git metadata are excluded.

For development outside Docker, run:

```sh
python tools/verify_release.py
python tools/package_source.py . /tmp/station-source.tar.gz
export STATION_SOURCE_ARCHIVE=/tmp/station-source.tar.gz
```

Choose an appropriate temporary path and environment syntax on Windows. A
missing source archive produces an explicit unavailable response. Before
sharing a modified application, rebuild its archive from the modified source,
retain all licences/notices and keep source delivery available to its users.
Do not serve an old archive alongside newer application files.

The CasparCG fork preserves each native patch as a separate commit on
`station/2.5.1`: https://github.com/andrew867/casparcg-server/tree/station/2.5.1
See STATION-PATCHES.md there for review order, known qualification limits and
future upstream PR preparation. No upstream PR is implied by the fork.

The preview image does not contain CasparCG or a proprietary NDI runtime. The full
engine candidate now builds with its patched source at `/usr/share/station/caspar-source.tar.gz`
and original preload-helper sources beside their libraries in `/usr/lib/station`.
The original helpers remain under the application AGPL terms. The engine recipe also retains exact CEF/Chromium credits, SDK wrapper build
materials and runtime identity. Full CEF/Chromium and OS source archives are
collected separately. See [native dependencies](NATIVE-DEPENDENCIES.md) for
versions, hashes, build scope and source delivery requirements, and the current
release checklist for acceptance. A private build is not a public binary release.
