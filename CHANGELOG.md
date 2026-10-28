# Changelog

## 0.1.0-alpha.3, 28 October 2026

This release adds conditional information programming and a bounded private-LAN Director remote.

- Conditional rundown cues and local-hour clock rules with explicit current, cached and unavailable data states.
- Morning and evening briefings, weather timeline, NL travel, Harbour Watch, Tonight's Sky, community calendar and Last Hour replay screens.
- Honest radar-history aircraft snapshots, tied to local receipt time rather than provider observation time.
- Camera grace periods that hold a recent picture briefly, skip stale single-camera cues and retain quad layouts with loading panels.
- A private Director remote for program, rundown and safe map controls, protected by a station-local key.
- Eight default clock rules and updated broadcast presets.
- 626 isolated Linux tests, release and documentation checks, real-Chrome interface validation, and production plus Intel standby promotion without restarting either video engine.

The application baseline is source revision `a08b7bce35a5525135b1e42a5c67037d83cb7f22`. External provider data remains disabled until the operator supplies its own permitted credentials. Site-specific alert certificates, offshore AIS coverage and surveyed camera alignment remain commissioning work.

## 0.1.0-alpha.2, 27 October 2026

First public source release. The public repository starts from a reviewed export; private station history, settings, credentials and provider caches are excluded.

- Generic offline Docker preview and Linux native-station build instructions.
- Seven-page broadcast desk, scene scheduling, source recovery, data graphics and music controls.
- Headless NVIDIA and Intel operating profiles, optional desktop output and standby publishing procedures.
- Input and subprocess hardening, diagnostic redaction, provider isolation and disabled external-provider defaults.
- Source packaging, component notices, dependency locks, automated tests and release verification tools.
- Programme and interface screenshots, operator manuals, hardware acceptance records and an explicit remaining-work checklist.

The application baseline is the reviewed source revision `0a449c64f3b0f289c64b26f9349adbee100235e9`; this export adds public-release documentation and screenshots. Earlier alpha identifiers refer to private acceptance bundles, not previous public releases.

This release does not include prebuilt native engine images. Sustained UHD60, a clean persistent GPU installation with reboot, and independent security-report notification delivery remain unqualified. Consult the [release checklist](docs/RELEASE-CHECKLIST.md) before commissioning a station.
