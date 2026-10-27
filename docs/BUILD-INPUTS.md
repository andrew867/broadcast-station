# Build inputs and verification

The candidate includes an offline preview and a separate full Linux playout stack. Both images build from source. Exact acceptance scope and current publication gates are in [the current checklist](RELEASE-CHECKLIST.md). Pinned inputs and successful builds do not imply identical image bytes or complete hardware qualification.

## Python dependencies

The runtime lock contains 31 packages; the test lock contains 39. Both target
CPython 3.13 on Linux x86_64. Every selected wheel has a SHA256 hash. The test
lock preserves every runtime wheel exactly. Docker and Linux CI install using
`--require-hashes --only-binary=:all:` and then run `pip check`.

`requirements.txt` and `requirements-test.txt` remain the human-maintained
direct requirements. After deliberately changing them, resolve inside the
same Linux base image using:

```sh
python -m pip install --dry-run --ignore-installed --only-binary=:all: \
  --report runtime-report.json -r requirements.txt
python tools/lock_from_report.py runtime-report.json requirements-linux-x86_64.lock
python -m pip install --dry-run --ignore-installed --only-binary=:all: \
  --report test-report.json -r requirements-test.txt
python tools/lock_from_report.py test-report.json requirements-test-linux-x86_64.lock
```

Review the version changes, rebuild both images and run the tests before
accepting new locks. The converter rejects a different platform, missing
hashes, source archives and artifacts outside the public PyPI file host.
Resolver reports need not be published. Windows development currently uses
direct requirements and does not have an equivalent complete hash lock.

## Music source

`skycam/assets/strudel-source/README.txt` contains working build instructions.
The fixed-directory esbuild recipe reproduces the checked-in worker without
embedding checkout paths. Its actual bundled inputs are Strudel core,
fraction.js and Kabelsalat web. SuperDough and Strudel webaudio have been
removed from the build declarations because this worker does not use them.

All 83 archived dependency files matched the locked npm installation. The
previous worker and rebuilt worker produced identical bytes for three seeded
song schedules. Only generated checkout-path labels changed in the bundle.
See `examples/music-source-verification.json`. CI verifies both the rebuilt
bundle and the archived source against a fresh `npm ci` installation.

## Engine source

`tools/verify_engine_source.py` accepts a separately downloaded upstream source
archive and a new output directory. It verifies the SHA256 declared in the
engine Dockerfile, rejects unsafe archive members, and applies the declared
patch sequence with fuzzy matching disabled. The latest October 21 check applied all
17 patches and recorded the resulting modified files in
`examples/engine-source-verification.json`.

The public fork preserves the original 16 changes and the portable camera-prefix follow-up on
`station/2.5.1`, based on upstream `v2.5.1-stable`. The final modified source
matches the verified patch application. The original 16-patch revision passed regression tests and a full Linux
compile in [fork CI](https://github.com/andrew867/casparcg-server/actions/runs/39631899777).
The compile uses the complete checksum-verified CEF SDK; installing only the
CEF runtime DEB does not provide its development headers.

The native recipe now builds its own base stage, pins the Ubuntu base digest
and dated package snapshot, and verifies both release DEB downloads. The
upstream source and CEF SDK have checksum declarations. No hidden local base
image is needed. Hardware and display qualification are recorded separately in the [acceptance register](ACCEPTANCE-STATUS.md). CEF/Chromium redistribution source/notices and a complete
native-image inventory remain mandatory before publishing engine images.
No proprietary NDI runtime is bundled.

## Assets and image inventory

Leaflet JS, CSS and its notice exactly match the published 1.9.4 npm archive.
All three font files match the Google Fonts distribution checked on October
21; their embedded family names are recorded alongside the applicable OFL
notices. The font source URLs use an upstream branch and can change, so retain
the recorded file hashes. Piano sample hashes and original-source attribution
remain in the supplied FreePats manifest.

`examples/image-inventory.json` records the most recently saved installed
preview image inventory. New hosted runs also retain an inventory artifact
with the exact image ID. These are package versions and notice hashes, not a
complete file SBOM. The preview Python base is pinned by digest; Debian and
native Ubuntu package repositories are dated snapshots in deploy/*.sources.
The native base and release downloads are pinned separately. Apt signature
verification remains enabled. These controls do not promise identical image
bytes across different builders or hardware.

## Source delivery and validation

The Docker source stage packages the reviewed tree deterministically. The
studio and guide link to `/source`, which serves that immutable archive and
never archives live settings. The container smoke test compares application
files against the source archive and verifies offline startup and denied
writes with no network, GPU or production mounts.

The hosted application workflow checks wheel locks, npm rebuild/source
matching, source and full Git history secret scans, the Python suite, Compose
configuration, image build, source-delivery smoke, and the complete suite in
a read-only container limited to one CPU and 2 GB RAM. The CI environment supplies the temporary directories and audio tools required by the tests.

Component licence assignments are recorded, with per-file asset provenance.
The application is available as a public source alpha. The full broadcast installer, native source/notice retention, production migration and bounded NVIDIA/Intel hardware checks are implemented and exercised. See the current checklist for exact scope; public delivery of prebuilt native images and their complete corresponding source collection remains separate.

The minimal Ubuntu native base has no initial CA bundle. The build copies the bundle from the digest-pinned Python base before contacting the dated Ubuntu HTTPS repository, then installs Ubuntu ca-certificates. TLS and APT signature verification remain enabled.

The seventeenth patch uses declared camera URL prefixes for freshness/keyframe recovery and native RTSP/TCP options. Its source matches the independently applied patch series. The current acceptance record identifies the matching build run. Its bounded native runtime checks and existing NVIDIA/Intel deployment checks are recorded in the current checklist.
