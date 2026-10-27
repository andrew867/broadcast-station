# Historical acceptance register, superseded

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

Current status: [release checklist](RELEASE-CHECKLIST.md). Statements below retain their original checkpoint scope.

# Acceptance evidence register

Current status: [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md).

The [Intel standby follow-up](INTEL-STANDBY-20261024.md) now records four real inputs, a copied station, direct and basement test delivery routes, and the operator's acceptance of occasional HD30 dips. The direct YouTube picture and music were confirmed normal. A simultaneous comparison found clean original RTMP timing but gaps and missing audio through RTSP. The standby relays now bypass that conversion. This does not close full Intel or public-release acceptance.

The release package is now on air. Physical HDMI capture and operator confirmation passed. Real rollback to the original stack and return to the release package were exercised without discarding newer operator settings. See [production migration](PRODUCTION-MIGRATION-20261022.md) for recordings, repairs and limits. The [24-hour soak review](SOAK-REVIEW-20261023.md) confirms stable sampled program output and no container restarts, but intermittent camera delivery remains unresolved. Automatic production reboot/login subsequently passed on 24 October. Historical evidence below retains its original test scope.

## Completed software work

- Tranche 1: neutral source export, component-specific licences, source delivery, pinned builds, CI and a public CasparCG patch fork.
- Tranche 2: versioned station configuration, private file-backed credentials, output/channel generation and a non-destructive importer. A real copied station snapshot passed isolated Windows and Linux startup checks, including all eight reference images and disabled camera settings.
- Tranche 3 implementation: separate full-stack Compose files, NVIDIA and experimental Intel profiles, source fan-out/health services, independent recovery, bounded logs/map cache, optional desktop sound and desktop-login resume. Native and controller images build from source. Isolated NVIDIA HD30/UHD30 and recovery acceptance passed; remaining hardware and migration gates are listed below.
- Tranche 4 implementation: seven route-backed studio pages, persistent status, preserved drafts, scene search and explicit take/apply controls. Laptop/tablet browser acceptance passed with disposable data and outbound access blocked. Controller disconnect and initial scene-list failure recovered in browser checks. Final on-air resource checks remain open.

## Evidence and its limits

| Check | Evidence | What it establishes |
|---|---|---|
| Native image build | GitHub run 39675452157, source commit 4b49788 | 17-patch build and software OpenGL recording pass: 179 frames at 1280x720, non-silent 48 kHz audio, clean decode; not GPU qualification |
| Hosted application check | GitHub run 39686811435, application commit 6184900 | Source/history scans, 531 Linux tests and 531 restricted-container tests, offline image and synthetic source recovery |
| Actual Compose startup | Network-isolated host test and hosted release check | Real temporary mounts and controller startup pass with playout enabled; no engine or GPU in this check |
| Source outage test | Isolated image on the production host, no external network or GPU | Synthetic RTSP source became ready, became unavailable after publisher termination, then returned with generation 1 to 2 and a confidence picture |
| NVIDIA output and recovery | docs/NVIDIA-ACCEPTANCE-20261021.md | Bounded HD/UHD synthetic recordings, PipeWire signal, source/relay/hang/ticker recovery; physical HDMI, real-source workload and soak remain separate |
| Copied-settings migration | docs/MIGRATION-VALIDATION.md | Safe import and startup, not production cutover |
| Browser tasks | docs/STUDIO-GUIDE.md | Draft retention, save behavior, navigation, search and screenshots at 1366x900, 1024x768 and 768x900 |
| Startup/audio implementation | Focused config/deployment/startup tests | Maintenance suppression, prebuilt resume, optional audio, matched channel clocks and retained host ports; no actual reboot or sound-sink claim |

The retained native image-config digest is sha256:63d08e53a927073989fb22c8bdfbdb377550c46efb8aca811408f22dfa62ae7f. The earlier software-OpenGL recording was visually inspected; the current repeat passed the same synthetic checks. A local native build encountered an internal GCC segmentation fault, with no matching kernel OOM/hardware-error entry found. Its cause is unresolved. The CI build passed, and its exact tested image is used for hardware acceptance rather than treating the failed local compile as successful.

Actual deployment checks found and fixed three launch defects missed by configuration-only checks: a comma split an unquoted temporary-filesystem option, the native server rejected a read-only templates directory, and the full stack inherited the image's preview-only playout default. Native CI now exercises the actual deployment bind mounts. A real-container launch check now runs in CI with external networking blocked. Desktop startup now respects maintenance enabled while it is waiting, and a station accepts only one watchdog process. Linux advisory-lock behavior was exercised on the host. Windows application tests passed 522 cases before the Linux-only lock test; its focused follow-up passed 26 with that one case skipped on Windows.

A real engine-only restart reproduced and then verified the repair for disappearing ticker layers. The settled one-minute final recording passed at 30.000 fps with clean audio timing. One earlier post-restart clip had a 131 ms video interval; it remains documented rather than counted as a timing pass. These isolated checks preceded the completed production migration on 22 October.

## Open gates at the time of this record

See [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md). The evidence above is dated; it is not a second current-status register.

NDI, true UHD60, headless rendering and other explicitly deferred features remain deferred. Existing accepted production audio and presentation are preserved. A successful build is not evidence of uninterrupted output, and the established station's soak does not count as a candidate soak.

The portable camera-policy fork at 8b10ae69c passed its regression and complete Linux compile in run 39665210531. Independent zero-fuzz application of all 17 patches matches the fork.

An allowlisted support-report tool now collects selected flags/counts and optional container state while excluding raw logs, endpoint addresses, names, credentials and media. Its tests passed and it was exercised against the copied settings snapshot.
