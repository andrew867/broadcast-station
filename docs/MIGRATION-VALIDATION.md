# Portable settings and migration validation

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

## Radar calibration repair, 23 October 2026

Live radar overlays require the station's paired model and reference picture in `data/radar/calibration`: `east.json`, `east-reference.jpg`, `island.json` and `island-reference.jpg`. These private provider pictures are not distributed as application defaults. The packaged images are synthetic offline fixtures and cannot establish alignment against live weather imagery.

When importing a legacy station, supply `--radar-calibration /path/to/legacy/skycam/radar` alongside any camera `--references` directory. The importer validates both pairs, preserves their bytes and hashes, and reports missing radar assets explicitly. Include this calibration directory in station backups. Missing or invalid calibration leaves weather visible and aircraft hidden with an alignment status; it does not substitute the test fixture or guess aircraft locations.

The production migration initially omitted these four files, suppressing aircraft on both radar slides. Restoring the original pairs matched hundreds of fixed image features on the current provider images. The controller repair preserves the existing calibration geometry and its approximate-position qualification, rather than weakening the changed-layout checks.

21 October 2026. Configuration import and isolated migration checks passed.

- Versioned station JSON and generated schema reject unknown fields, unsupported output clocks, invalid timezones and credential-bearing URLs.
- Provider groups require explicit enablement; regional adapters declare their Newfoundland scope. Secret files stay outside the source and source-download artifact.
- An allowlisted, manifest-verified copy of the production snapshot imported into a new directory. Existing destinations are refused, and dry-run does not write.
- 47 files, eight camera definitions, two quads, eight reference images, music selections and the paid-API accounting database were retained. Runtime caches and control history were excluded. The report records no changed or missing operator files.
- Isolated Windows and Linux application startup passed. Seven operator/status routes returned 200; Windows checked all eight reference images and offline write rejection. Linux used a read-only application mount, one CPU, 2 GB RAM, no network and no GPU. Disabled cameras stayed disabled.
- 499 Windows tests passed in 90.24 seconds. Hosted Linux/image checks are recorded separately when finished.

This proves import and offline startup, not live output, a migration cutover or hardware throughput. The canonical graphics canvas remains UHD; the native output profile can be HD30. Regional labels and adapters are not a worldwide data service. At this test date, storage enforcement and production cutover had not been evaluated.

Independent source eligibility was deployed to the existing controller. Automatically scheduled single-camera scenes become ineligible after 180 seconds without fresh decoded frames and return after 10 seconds of continuous recovery. Disabled cameras are immediately ineligible. Quad scenes and manual selection remain available. The engine, music settings and active rundown were preserved.
