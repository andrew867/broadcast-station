# Release validation

The baseline release profiles are NVIDIA UHD30 and Intel HD30. UHD60, automatic Intel quad rotation and other GPU families remain outside the accepted workload. The [release checklist](RELEASE-CHECKLIST.md) records current results.

## Extended observation

Use the same image IDs, output profile and representative rundown throughout an observation. Record the station configuration before testing. Keep the normal recovery watchdog active; a maintenance marker suppresses recovery and must not remain in place during the measurement.

Record at least four hours of native frame progression, programme readiness, decoded-source freshness, container start times, restart counts, memory, CPU and GPU temperature where available. Use the read-only observer:

```sh
python3 tools/soak_station.py /path/to/station /path/to/new-evidence \
  --gpu nvidia --seconds 14400 --interval 30
python3 tools/review_soak.py /path/to/new-evidence/samples.jsonl \
  --output /path/to/new-evidence/review.json
```

Check the tool's help for the installed revision before use. A new evidence directory prevents accidental replacement of a previous run. Run the observer as a supervised host service if it must survive an SSH disconnect.

At an independent receiver, save bounded recordings near the start, middle and end. Check each with [the recording procedure](HARDWARE-ACCEPTANCE.md#picture-and-sound), inspect camera, map and transition frames, and listen to music. Retain missing or failed recordings as failures of coverage. Packet cadence can include repeated pictures and is not a measurement of distinct rendered frames.

Separate these observations:

- A stale camera with continuing programme frames is a source event.
- A stalled native frame counter is a playout event.
- Advancing native frames with a failed receiver can indicate a publishing, network or receiver event.
- A low sampled rate is a performance observation, even when encoded timestamps remain regular.

Record all restarts and recovery actions. Repeated source or programme failures require investigation; averaging them away does not establish acceptance. A source that recovers at the next sample has a bounded observation gap, not a precisely measured outage duration.

When testing a temporary headless configuration, preserve the original display settings and provide an independent timed restore before stopping the desktop. Verify desktop picture/audio and the original rundown after restoration.

## Physical power-off/on recovery

Perform this during an attended maintenance window with access to the power button and display. A remote reboot establishes reboot recovery only.

1. Save a verified settings checkpoint, record the boot ID and image IDs, and confirm the intended boot target, Docker startup, station startup and watchdog services.
2. Shut down normally. Once the operating system has halted, remove and restore power where appropriate, then start the host. Record whether startup was manual or automatic after power restoration. A laptop battery must be accounted for when describing the test.
3. For headless acceptance, do not log into a desktop or start the station manually. Observe the receiver before connecting through SSH, so a login cannot be mistaken for the startup trigger.
4. Record the first received picture and audio, total recovery time, new boot ID, active services and unchanged operator settings.
5. Check the selected rundown, music, source reconnection and independent receiver timing.

This controlled test does not establish filesystem survival during an abrupt power loss. BIOS power-restoration behavior, UPS behavior and unexpected-loss recovery need their own evidence if claimed.

## Clean GPU installation

Use a spare disk, fresh installation or otherwise disposable supported Linux system. Do not erase a commissioned station to satisfy this check.

1. Record the OS image, installation date, GPU, kernel and driver. Confirm that no previous station files, images, native build dependencies or private settings were retained.
2. Install only the documented [host prerequisites](RELEASE-INSTALLATION.md#prerequisites). Record any additional package or manual intervention required.
3. Verify the complete frozen bundle against a trusted manifest digest. Load its images using the [versioned installation procedure](RELEASE-INSTALLATION.md#verify-and-load), then confirm both immutable image IDs.
4. Prepare a new station with generic assets. Keep providers and external publishing disabled. Configure headless UHD30 on the qualified NVIDIA hardware or HD30/libx264 on Intel.
5. Follow the guide as written. Verify native GPU rendering rather than software fallback, visible graphics and non-silent 48 kHz audio. Use an isolated local output or separate private receiver destination.
6. Test startup without login, a bounded observation and rollback. Record every deviation from the instructions before calling installation complete.

A clean software-rendered VM and an upgrade on an existing GPU host answer different questions. Neither substitutes for this test.

### Live-USB alternative

A fresh live Linux session can provide useful clean-host GPU installation evidence without replacing an installed station. Boot the live environment rather than its installer. Keep installed station filesystems unmounted, install host prerequisites in the live session, and load only the verified generic release artifacts. Record the ISO identity, kernel, actual GPU driver, Docker storage location and every additional setup step.

Check available RAM and writable space before loading images. Compressed archive sizes are not the expanded image or runtime memory requirement. Use an explicitly selected disposable USB filesystem or adequate temporary storage for Docker and station state. Do not silently place those files on the installed station's disk. Preserve evidence externally before leaving the session.

This can qualify the clean-host driver, package-loading and rendering path for the tested live distribution. An ephemeral live session cannot establish that an installed station's configuration and startup services survive reboot. Record persistent installation/startup acceptance separately. Retained user settings, images or native build dependencies invalidate a claim of a clean starting environment.

## Evidence record

Keep the following fields with each result:

| Field | Required detail |
|---|---|
| Artifact | Bundle version, manifest checksum, source revision and both image IDs |
| Host | OS, kernel, GPU, driver, rendering backend and output profile |
| Workload | Sources, scenes, audio mode, receiver route and competing host load |
| Timing | Start/end times, sample interval, missing coverage and actual recovery time |
| Results | Native cadence, receiver timing/decoding, visual review, listening, restarts and source events |
| Restoration | Final output mode, services, rundown, music and configuration differences |
| Decision | Accepted scope, unresolved failures and evidence location |

Publish only sanitized summaries. Keep credentials, private configuration and programme recordings in the station's protected evidence archive.
