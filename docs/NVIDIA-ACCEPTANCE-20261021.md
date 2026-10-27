# NVIDIA candidate acceptance, 21 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

This record covers a separate test station on the existing Linux/NVIDIA host. The established production engine and publishing path were not replaced. It is not a clean-machine installation, physical HDMI acceptance or a long-duration soak.

## Tested configuration

- NVIDIA RTX 3070, 8 GiB, driver 615.78.08; the native startup log confirms NVIDIA OpenGL 4.5.
- Private Compose project, separate data, AMCP and web ports, synthetic RTSP cameras and a private relay. External providers and production credentials were absent.
- Two 640x360 synthetic sources at 30 fps; six disabled cameras exercise unavailable panels. Camera and quad scenes use the normal application graphics and scene banks.
- HD30 baseline, H.264 NVENC, stereo AAC at 48 kHz. Local desktop sound uses the PipeWire PulseAudio interface.
- CPU and memory caps bounded the candidate. A separate observer watched production every five seconds and could stop only the candidate on sustained low output cadence or low available memory.

The native image came from successful private CI run 39675452157, commit 4b49788. Its exported image-config digest is `sha256:63d08e53a927073989fb22c8bdfbdb377550c46efb8aca811408f22dfa62ae7f`. The loaded Docker manifest digest is `sha256:88f853a5b959b74a57a40e4858510019fa0a1a84f47f23d89fd5ed9d14d245eb`. Export inspection verified the matching configuration and filesystem layers; those two different digest types are not interchangeable. The compressed image SHA256 is `5b3aa32e11f816756f1e7a86c4ffc536fab8740ee8a2211d4c147a62bdbf604f`.

The subsequent native CI run 39681500856, commit 841e3c2, also passed with the actual deployment mount layout. The native patch source remains the 17-patch fork at 8b10ae69c. A local native compile had an internal GCC segmentation fault; no matching kernel OOM or hardware-error event was found. Its cause remains unresolved. The successful CI artifact, not that failed local build, supplied this acceptance image.

## Defects found and repaired

1. Full-stack Compose inherited preview-only playout from the controller image. Full-stack mode now explicitly enables playout.
2. An unquoted temporary-filesystem option containing a comma produced an invalid Docker mount. It is quoted and exercised by a real-container CI startup check.
3. The native server checks template-directory writability at startup. That directory is now writable while the root filesystem and other protected mounts remain restricted. Native CI uses the same bind-mount contract.
4. Two watchdogs could otherwise maintain separate restart budgets. A Linux advisory lock now permits only one watcher per station.
5. Desktop startup now checks maintenance again while waiting and immediately before launching.
6. An older controller failure could win over a newly unavailable engine and spend the recovery cooldown on the wrong process. Without independent advancing delivery, controller-only recovery now requires a responding engine counter. Unit tests cover both overlapping failures and the independent-delivery exception.
7. Output status always said UHD even for HD. It now reports the configured native profile.

The first hang drills exposed the recovery-priority defect and are retained as failed evidence. They are not counted as successful recovery tests. The corrected run uses the real 90-second startup grace, 180-second cooldown and three-recoveries-per-hour policy. Earlier test history was archived in the isolated test directory before the new run; production history was not reset.

## Recorded HD results

| Recording | Video samples | Measured cadence | Decode and timestamp checks |
|---|---:|---:|---|
| Baseline | 351 | 29.979 fps | Passed |
| Camera loss, recovery and scene changes | 2,499 | 30.000 fps | Passed |
| After a 12-second relay outage | 247 | 30.070 fps | Passed |

All three have stereo 48 kHz AAC, no nonadvancing timestamps and no detected large audio or video gaps within the captured packets. Subscriber startup can wait for the next keyframe, so packet-span measurements are reported rather than dividing frame count by the requested recording duration. Each file was decoded completely. Single-camera and quad frames were visually reviewed; the disconnected source retains its own unavailable panel while the remaining scene and graphics stay present.

These measurements establish the tested synthetic workload only. They do not prove real camera network quality, all transition frames, eight simultaneous camera decodes or uninterrupted listening over hours.

## Final UHD and audio checks

The controller image used for the format checks is `sha256:09ad1ed8036147485ecc2f36c7a8cf7fad78897861bc5bb00f50deaaaf666e64`. Its HD status correctly reports 1920x1080p30 and its UHD status reports 3840x2160p30.

| Recording | Size | Video samples | Measured cadence |
|---|---|---:|---:|
| Final HD | 1920x1080 | 392 | 30.001 fps |
| UHD single camera | 3840x2160 | 594 | 30.013 fps |
| UHD quad | 3840x2160 | 560 | 30.001 fps |

All passed full decoding, packet cadence and 48 kHz audio checks. The two UHD recordings were each requested for 20 seconds. Their pictures were visually reviewed. The quad has two live synthetic sources and two intentionally disabled panels, not four simultaneous UHD inputs. NVENC was configured for output; this pass does not independently qualify every input's hardware decode path.

The isolated desktop-sound recording had a -50.3 dBFS peak and no detected silence lasting 150 ms at a -80 dB threshold. The final encoded recovery recordings also passed timing and decode checks. The desktop default sink was unchanged. OpenAL did not honor the test PULSE_SINK environment variable, so only the candidate's Station-Program stream was explicitly moved to the private test sink. The initial silent sink recording and a recording crossing an injected hang are excluded from successful audio evidence. No speaker-listening or latency claim is made.

The additional UHD workload and recording analysis briefly lowered production's sampled cadence. This shared-host test is not permission to leave two production-sized stations running together. The test stack and its audio sink are removed after evidence collection; the established engine stays running.

## Recovery results

The corrected bounded run passed. An injected engine hang was recovered in about 47 seconds, including restored program readiness. The subsequent recording decoded cleanly. Maintenance suppressed recovery, a deliberate stop stayed stopped and manual resume restored output. After the real cooldown, a hung controller was recovered while the engine's start time remained unchanged. A second watchdog was rejected. The recovery history records one engine recovery and one controller recovery in the corrected run.

Application commit 2ae5cc4 passed 528 Linux tests and 528 restricted-container tests in CI run 39683590811, including the overlapping-failure regression. The private test records retain the exact image identities and timings. These fault tests establish bounded recovery from the injected cases, not immunity to all failures.

## Engine-only ticker recovery

An additional visual check reproduced a missing crawl after restarting the engine while keeping the controller alive. The controller retained its old layer state. The repair increments a graphics epoch when playout reconnects and invalidates ticker layer state on disconnect or epoch change. It reloads the bar, clock and strips without taking another scene or changing the alert schedule. Regression tests cover both an observed disconnect and one missed between ticker polls.

The before/after native recordings visually confirm the repair. The final ticker test image is `sha256:ae5d4b890be5c7aeb9ba8d06ab934faef56372a16740ec84dbc1a41741a956b9`. Its reconnect advanced graphics epoch 1 to 2. The post-restart clip decoded cleanly and had continuous audio timestamps, but contained one 131 ms video timestamp interval. That clip is not counted as a clean-cadence pass. The subsequent settled one-minute recording passed: 1,782 video packets across 59.366 seconds, measured 30.000 fps, largest video interval 34 ms, 2,813 audio packets at 48 kHz, no large gaps or nonadvancing timestamps, and clean full decoding. This does not erase the earlier recovery gap.

## Final checks and cleanup

The final ticker code at commit 6184900 passed 531 Linux tests and 531 restricted-container tests in CI run 39686811435. The earlier native build and mount-contract CI checks also passed. Local focused ticker, alert and camera-policy regressions passed 24 tests.

All candidate containers and the isolated audio sink were removed. Production's engine retained its original start time and zero restarts. Four final samples showed 29.94 to 30.04 fps with ready/moving output. Across 752 observations during the broader exercise, sampled cadence averaged 29.953 fps with a minimum of 23.17 and maximum of 33.69. There was one failed status observation and a 167-second gap between bounded observer runs. No automatic production-protection stop fired. This is sampled status evidence, not an all-frame production recording or listening proof.

## Remaining migration and release gates

The actual HDMI display and listening route, desktop logout/login and reboot, fresh production-state import, controlled cutover and rollback, and a 24-hour candidate soak remain separate gates. Rebooting the shared host or replacing its active HDMI consumer was deliberately outside this pass.

At this 21 October checkpoint the T480s was not ready. It has since been commissioned as a limited HD30 standby; see [the current checklist](RELEASE-CHECKLIST.md). Those other gates were also outstanding at that historical checkpoint; their current results belong only in the current checklist. No public application image or production migration is implied by this record.
