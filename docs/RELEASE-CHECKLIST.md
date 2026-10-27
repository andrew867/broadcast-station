# Release status and remaining work

Updated 27 October 2026. This is the authoritative remaining-work list. Version 0.1.0-alpha.2 is the first public source alpha, with a generic Docker preview, native build instructions and screenshots. No public stable release or prebuilt native engine image is included. Dated test records describe their own revisions and do not override this checklist.

The release baseline is NVIDIA UHD30 and the limited Intel HD30 workload. Sustained UHD60 is optional performance work, not a prerequisite for this baseline release.

## Native binary and stable-release acceptance

| ID | Requirement | Completion evidence needed |
|---|---|---|
| R1 | Complete unattended hardware coverage | Completed for the tested startup modes. Intel HD30 recovered programme and music after reboot without login. NVIDIA passed four hours of headless UHD30 observation and controlled physical power-off/on with desktop autologin. Restored desktop applications initially covered HDMI; disabling saved-session restoration passed a follow-up reboot. Abrupt-loss, automatic BIOS restoration and headless physical cold-start remain outside this evidence. |
| R2 | Preserve promotion evidence | Hardened controller and matching engine promoted on production and standby. Controller rollback, unchanged operator settings, exact source identities and production receiver timing passed. Retain the previous image pair and protected state checkpoints. |
| R3 | Publish the accepted fixed artifacts | The complete bundle was verified. The frozen `0.1.0-alpha.1` installer passed upgrades on Intel standby and NVIDIA production, including unchanged operator files and independent receiver checks. The application source alpha is public. Native binary publication and public delivery of its complete corresponding source collection remain pending; the public alpha does not distribute those images. |
| R4 | Activate public reporting | The public source repository uses GitHub private vulnerability reporting. Configuration is checked during publication; an independent reporter-to-maintainer notification test remains open. CEF 142 remains an explicit compatibility/security exception, not a current browser-security claim. |
| R5 | Verify a clean GPU installation | Fresh EndeavourOS live-session Intel HD30 passed package loading, hardware EGL, generic station rendering/audio, browser checks and stop/resume. The live overlay required a separate RAM-backed Docker/containerd store; a false-success image-load check was repaired. A clean persistent installed-OS GPU test, including reboot, remains open. The live session and earlier software-rendered VM do not establish persistence. |

The [versioned bundle guide](RELEASE-INSTALLATION.md) defines installation, and the [package acceptance record](PACKAGE-ACCEPTANCE-20261026.md) records the completed upgrade tests. The [binary release checklist](BINARY-RELEASE-CHECKLIST.md) defines distribution details. The [security policy](../SECURITY.md) limits the studio to a trusted host or private LAN; Internet-facing studio access is unsupported.

Use [release validation](RELEASE-VALIDATION.md) for extended observation, physical power-off/on and clean GPU installation procedures. The [26 October soak record](SOAK-20261026.md) records the completed observation, source interruptions and acceptance limits.

The [controlled power-cycle record](POWER-CYCLE-20261026.md) covers physical PSU interruption, automatic programme recovery, independent receiver checks and the KDE session-restoration repair.

The [fresh Intel live-session record](LIVE-GPU-20261026.md) covers the clean GPU package test, installation deviations, loader repair and bounded HD30 recordings. The frozen installer needs the corrected standalone verifier until a replacement bundle is assembled; its application image pair is unchanged.

## Known technical limitations

- **RTSP relay timing:** a received RTSP stream delayed audio by 3.056 seconds in the recorded test. The root cause remains unresolved. Both accepted standby publishing routes use original RTMP; retain that path until an alternative passes receiver timing and decoding checks.
- **Performance:** sustained UHD60 and automatic Intel quad workloads are not qualified. The [NVIDIA display comparison](DISPLAY-PERFORMANCE-20261026.md) measured approximately 58 fps for camera/map and 54 fps for the observed quad in headless mode, below the 60 fps target. One headless quad source displayed its fallback, so a matched four-live-input comparison remains open. Output format selection does not guarantee that many distinct pictures per second.
- **Source and network outages:** camera readiness depends on recent decoded pictures, separately from programme readiness. Provider availability and local transport capacity remain operating constraints.
- **Standby continuity:** one 6.39 fps sample coincided with a stale camera during the four-hour run; output recovered without a restart. Repeated NTV camera 1 freshness failures also recovered independently. Their causes remain open, and Intel is not qualified for uninterrupted native 30 fps under every source failure.
- **Headless coverage:** NVIDIA UHD30 completed four hours with no sampled low-cadence events or programme stalls. Intel completed four hours with the recorded performance exception and previously passed a no-login reboot. Controlled physical startup passed on NVIDIA using desktop autologin; headless physical cold-start and AMD, ARM or other hardware remain unqualified.
- **Longer-duration resources:** NVIDIA engine memory rose by approximately 0.39 GiB during the four-hour observation without OOM or output degradation. Retain longer-duration tracking; this run is not proof against a slow leak.

## Site-specific commissioning

These items depend on external evidence or access and do not become complete through a software test alone.

| Item | Remaining requirement |
|---|---|
| Official alert trust | Independently authenticated issuer certificates and local alert lifecycle/audio acceptance. The receiver is not a certified public-warning system. |
| Offshore vessels | A position feed with the required offshore coverage and permitted reuse. AISStream connection health does not prove offshore reception. ONC access remains unconfirmed. |
| Camera and radar alignment | Surveyed camera positions, independent landmarks and validation of approximate radar alignment. |
| Optional paid flight enrichment | Confirm the account's actual price/credit terms and spending controls before enabling automatic paid requests. Keep local ADS-B primary. |
| Market timestamps | Establish independently supported quote-time/session metadata where the provider omits it. Retain explicit unknown, delayed or last-known labels meanwhile. |

## Optional development backlog

These features are deferred, not release-blocking defects. Existing controls remain available.

| Area | Potential work |
|---|---|
| Monitoring | Low-cost continuous programme/preview monitoring beyond the existing confidence stills and audio meters. |
| Contribution transport | Compare a single-encoder SRT route against the accepted RTMP route, with timing measurements and rollback. |
| Timing | Evaluate an external reference clock only if measurements show that it addresses a remaining continuity problem. |
| Camera management | Upstream MediaMTX feed management and additional permission-cleared sources. Camera catalogue editing already exists. |
| Radar history | Replay aircraft positions at the radar image's observation time instead of hiding current aircraft during historical playback. |
| Advertising | Named advertising slots, advance on video completion and controlled advertisement audio/music reduction. |
| Identity | Live branding reload and complete use of configurable colour tokens. Names and logos are already configurable. |
| Platforms and outputs | NDI as a separately licensed optional integration; sustained UHD60; broader Intel quad workloads; additional GPU/platform qualification and a complete Windows dependency lock. |

## Completed engineering scope

| Area | Recorded result |
|---|---|
| Configuration and migration | Versioned settings, private secret references, copied-state import, rollback and preservation of operator edits. |
| Studio | Seven-page desk, draft preservation, explicit on-air actions, recovery states and browser checks. |
| Production | Cutover, rollback, picture/audio confirmation, a 24-hour observation and automatic desktop-login/reboot recovery. |
| Intel standby | Four real sources in single-camera/map rotation; accepted HD30 workload with occasional dips. The latest four-hour headless observation retained one performance dip; all three scheduled receiver recordings passed. |
| Headless | NVIDIA UHD30/NVENC and Intel HD30 native EGL output, each with 359 decoded frames, visible graphics and non-silent 48 kHz audio. Separate full-station crash recovery passed at independent RTMP receivers. |
| Clean installation | Empty-cache Ubuntu 24.04 VM built the generic preview, controller and native engine without private state. Software-rendered CEF/video/audio passed bounded checks. |
| Security hardening | Bounded requests/provider replies, constrained media inspection, host validation, redaction, alert-cache isolation and safe provider defaults. |
| Native materials | Exact inventories and matching source identities for 269 engine and 233 controller OS packages; CEF/Chromium provenance and 541 bundled credit entries retained. No proprietary NDI runtime bundled. |
| Automated checks | Application CI at revision 129c77e passed 604 tests on Linux and 604 in the restricted container. Native CI at 9d322ea passed desktop and headless software-rendered picture/audio checks; only documentation changed between those revisions. These are recorded baselines, not a claim that later commits have passed. |

See the [acceptance register](ACCEPTANCE-STATUS.md) for measured workloads, failed experiments and evidence limits.

## Output qualification

| Profile | Scope |
|---|---|
| NVIDIA 2160p30 | Commissioned production with encoded recordings and local/viewer confirmation. Competing GPU and network load can affect performance. |
| Intel 1080p30 | Limited standby camera/map rotation using software H.264; not guaranteed 30 distinct pictures per second. |
| Intel quad | Manual use only in the accepted configuration; excluded from automatic rotation because of performance. |
| 1080i59.94 | Field timing and encoded interlacing verified; no performance improvement in the tested laptop workload. |
| 720p30 and 720p60 | Configurable and exercised; not established as a cure for the tested quad workload. |
| 2160p60 | Tested on RTX 3070 with and without desktop output; headless was fastest but remained below 60 fps. Not qualified for sustained production. |
