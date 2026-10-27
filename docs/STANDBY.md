# A second station for testing or standby

A standby is a separate station with its own output destination. It is not automatic failover. Never let two machines publish to the same ingest path at the same time.

## Copy the settings safely

Use a current-format private station snapshot with a `manifest.json` containing SHA-256 hashes of its files. Keep the snapshot private, it contains your location, source addresses and operator settings.

```sh
python3 tools/clone_station.py station-state.tar.gz "$HOME/standby-station" \
  --sha256 VERIFIED_SNAPSHOT_SHA256 --camera cam1 --camera cam2
python3 tools/stationctl.py prepare "$HOME/standby-station" --gpu intel
```

The destination must not already exist. The importer verifies the archive and every payload hash before writing. It preserves branding, camera definitions, references, calibration, rundown library, music settings and the historic accounting ledger. It disables all providers, publishing, local outputs and automatic rundown/clock startup. It removes known runtime health records and does not copy the old Compose environment, display cookie or credentials. The original rundown, clock and scene state are retained under `standby-original`.

Review the copied data before sharing it. This is a private configuration transfer, not a general-purpose anonymizer. External music libraries and generated music caches are not included. Reconcile account usage before enabling any paid API on a second station; a copied spending ledger cannot coordinate simultaneous spending by two machines.

## Commission the second machine

1. Edit its `station.json`. Set the local display, enable playout, and select its own publishing path. Start with news and a small camera selection. Keep account-based providers off until their connection and spending policies have been reviewed.
2. Choose desktop or headless operation. For desktop output, run `stationctl.py check` from the logged-in session and give the station its own display authorization. For headless output, follow [headless setup](HEADLESS.md). Give each host its own station directory.
3. Test the cameras, crawl, music, transitions and output recordings under the intended load. An encoder's advertised frame rate does not prove smooth output.
4. Enable additional public feeds and the intended rundown only after the basic load test. Keep the original station unchanged.
5. Configure a separate test stream key in a restricted file, outside the source tree and all backup selections. Confirm picture and sound at the actual receiver.

After cloning, install each required provider credential privately and enable its provider explicitly. For AIS, verify fresh position reports as well as a connected WebSocket; identity-only messages cannot place vessels on a map. A credential-free clone intentionally has no live account-based feeds.

For a deliberate promotion, stop the primary publisher first, confirm it has disconnected, then enable the intended standby destination. Repeat the reverse order when returning to the primary. Recheck current alerts, camera health and account usage before either promotion.

## HD format choices

| Setting | Native timing | Encoded video |
| --- | --- | --- |
| `1080p3000` | 30 frames/s | 1920 by 1080 progressive, 30 fps |
| `1080i5994` | 60000/1001 field ticks/s | 1920 by 1080 interlaced, 30000/1001 frames/s, top field first |
| `720p6000` | 60 frames/s | 1280 by 720 progressive, 60 fps |
| `720p3000` | 30 frames/s | 1280 by 720 progressive, 30 fps |

Changing the profile requires an engine restart. Intel profiles currently use software H.264 encoding; hardware OpenGL rendering and camera-health decoding are separate from output encoding. The optional `output.x264_preset` accepts `ultrafast`, `superfast`, `veryfast`, `faster`, `fast` and `medium`. The default is `veryfast`. Faster presets reduce compression efficiency in exchange for less CPU work, so check picture quality at the chosen bitrate.

Interlaced publishing currently requires `libx264`. The FILE consumer receives full images at the field clock; the publishing filter combines successive images into alternating fields and enables interlaced H.264 coding. This does not establish that the desktop HDMI connector is transmitting an interlaced signal. Its physical mode is controlled by the desktop/display driver. Use progressive output for the YouTube test.

Verify a recording using `tools/check_program_recording.py`, with `--fps 29.97002997` for 1080i59.94, `--fps 60` for 720p60, or `--fps 30` for the progressive 30 fps profiles. Inspect `field_order` as well as the measured packet cadence. A top-field-first flag alone is not evidence of correct temporal motion.
