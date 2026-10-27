# Contributing

Develop against a separate checkout and data directory with offline mode enabled. Do not run a development controller against an on-air engine or publishing destination. Fixtures must use synthetic data and original demonstration artwork, without credentials, private settings, camera captures or provider caches.

## Local checks

On Linux x86_64, create a Python 3.13 virtual environment and install:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements-test-linux-x86_64.lock
python tools/verify_release.py
python tools/verify_docs.py
python -m pytest tests -q
```

Install FFmpeg and espeak-ng for audio tests. Windows development uses `requirements-test.txt`; this dependency path does not have a complete transitive hash lock. Tests require neither provider credentials nor a running engine. See [build inputs](docs/BUILD-INPUTS.md) for dependency updates and music/native builds.

Changes to scheduling, source recovery or timing need tests that exercise failure and recovery. Interface changes need browser checks at desktop and narrow widths. A successful build does not qualify GPU performance. Record the revision, environment, workload and limits of hardware tests.

Keep visible branding configurable and preserve stable scene, configuration and API identifiers. Update the relevant manual when behavior changes. Write documentation about the software: procedures, expected results and limitations. Keep implementation discussions and dated measurements in their designated records.

Contributions must follow the component licences in [LICENSING.md](LICENSING.md), retain third-party notices and record asset provenance. Do not include material without redistribution rights. No contributor agreement or copyright transfer is assumed. Report vulnerabilities through [SECURITY.md](SECURITY.md), not a public issue.
