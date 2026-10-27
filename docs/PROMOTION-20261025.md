# Controller promotion and unattended startup, 25 October 2026

This record applies to controller image `sha256:13078cc57888363627dc1b94dd18c09bd8d0358607d4dbd27fff146d0ad6a8f7` and engine image `sha256:5a164704753d9781ab47254848f490bad3b4fc8822223df1be142b84713dc5d4`. The controller was built from application revision `fa7f069f595cfc3b760d3b3e3a382a2d27c4ad54`. Later release tooling and documentation do not change those image identities.

## Production promotion

The hardened controller passed isolated startup checks on both hosts. Production was switched to the candidate, returned to its previous controller to verify rollback, then switched back to the candidate. The video engine remained running throughout that controller test. Checked operator settings, branding, music configuration, rundown and accounting policy were unchanged.

The matching engine subsequently passed an isolated NVIDIA UHD30 test with 359 decoded video frames, visible CEF graphics and non-silent 48 kHz audio. It was then promoted with the previous engine retained for rollback. HDMI configuration remained enabled. A 60-second independent RTMP receiver recording contained 1,800 video packets at 30.000 packets per second, clean decoding, no non-advancing timestamps and no audio or video gaps above the check's 100 ms threshold. Audio/video ending timestamps differed by 12 ms. These measurements establish packet continuity and stream coverage, not a perceptual lip-sync or listening verdict.

## Intel headless startup

The matching engine passed an isolated Intel HD30 graphics/video/audio check. The standby then used EGL with no desktop sockets or display environment in the engine container. Its existing separate publishing route was retained.

The first reboot exposed a host configuration fault: systemd-logind suspended the laptop with its lid closed, although the headless startup unit had succeeded. KDE's desktop lid setting did not apply without a KDE session. The system policy was changed to ignore lid closure on external power while retaining suspension on battery. The failed attempt remains part of the evidence.

After the second reboot, programme output and the current music track were observable over HTTP before the first SSH connection. Three successive advancing-output samples completed 78 seconds after the reboot request. The display manager was inactive, the default target was `multi-user.target`, user lingering was enabled, and no X11 or Wayland session existed. This is a no-login reboot test; it is not a physical power-off/on test.

The following observation lasted 30 minutes and recorded 82 samples:

| Measurement | Result |
|---|---|
| Programme unavailable or probe failure | 0 samples |
| Measured frame rate | Mean 29.99 fps; range 29.71 to 30.12 fps |
| Samples below 95% of the 30 fps target | 0 |
| Engine, controller or camera-worker start-time changes | 0 |
| Out-of-memory observations | 0 |
| Highest sampled CPU temperature | 76 degrees C |
| Decoded-source unavailability | 5 samples, without loss of programme readiness |

Source readiness and programme readiness are separate measurements. This observation does not establish uninterrupted availability of every external camera or sustained performance for arbitrary workloads.

## Dependency and package checks

The exact promoted image inventories match retained sources for all 233 controller and 269 engine OS source packages. Expected engine source/notice files are present, and the inventory found no proprietary NDI runtime. Source archives for all 31 locked Python runtime packages were retained and checked against PyPI's published digests. The PyPI version advisory metadata returned no listed vulnerabilities for those 31 versions at the review time. That check does not cover native libraries, the browser runtime, host drivers or the kernel.

The alpha bundle contains fixed image archives, source materials, inventories, notices and checksum verification tooling. Its application image includes its exact corresponding source archive. Release tooling and updated manuals are also supplied separately. Public distribution, public vulnerability-report-form verification and the final clean GPU installation remain separate acceptance steps.

See the [current checklist](RELEASE-CHECKLIST.md), [bundle installation guide](RELEASE-INSTALLATION.md) and [dependency maintenance policy](DEPENDENCY-MAINTENANCE.md).
