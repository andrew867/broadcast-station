# Intel standby commissioning, 24 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

The T480s now runs a copy of the production station with four actual camera inputs, aircraft maps, news and generated music. The operator accepts occasional frame-rate dips for this standby. This is a working private installation, not qualification of unrestricted Intel workloads or a public binary release.

## Configuration and isolation

The new `tools/clone_station.py` validates the snapshot checksum, manifest and member paths before creating a separate station. It preserves the station's branding, camera definitions, calibration, settings and accounting records. It clears publishing destinations and credential references, disables providers and automatic playout, and saves the original rundown and program clock separately. The source station is not changed. The imported settings are private, not anonymized for publication.

For this installation, four feeds were enabled: two 2688 by 1520 SkyCam inputs and two 1280 by 720 NTV inputs. News, local aircraft data and aircraft metadata are enabled. Other provider settings remain preserved but inactive, with no duplicated paid-provider credentials. The standalone standby guide explains manual promotion and accounting review.

Program is 1080p30, software H.264 using `ultrafast` at 8 Mbps, with 48 kHz audio. Individual camera scenes and the two aircraft maps rotate automatically using cuts. The four-camera quad is available manually but is excluded from the automatic rotation because it is substantially slower. Intel OpenGL and hardware source-health decoding are retained; the program encoder is software, not a claim of hardware encoding.

Two manually selected test relays were installed. One sends the laptop's local program directly to a separate YouTube broadcast. The other sends it through a new, isolated MediaMTX path on the existing basement server. Both copy the already encoded video and audio. Only one route runs at a time. Neither uses the main program path or stream key. The original MediaMTX configuration was backed up; parsed configuration equality was checked after excluding the one added path. The main server was not restarted.

The operator confirmed normal picture and music on the direct YouTube route. The basement route has advancing local and upstream publishing counters; these counters alone do not establish viewer playback. Test publishing is not enabled automatically after login. The existing station login launcher and saved rundown resume remain installed. The operator's AC lid setting was verified as screen-off rather than suspend; battery policy was preserved. No new reboot was performed during this pass.

## Recorded format comparison

The measurements below are bounded recordings, not long-duration guarantees. Packet cadence, native status samples and viewer acceptance answer different questions. The RTSP recordings show large gaps that cannot all be attributed to native rendering; the transport comparison below is separate evidence.

| Workload and output | Recording | Mean video packets/s | Largest video gap | Result |
|---|---:|---:|---:|---|
| Two real cameras, 1080p30, veryfast | 120 s | 27.886 | 4.986 s | Timing failed |
| Two real cameras, 1080i59.94 | 60 s | 13.802 | 6.473 s | Timing failed |
| Two real cameras, 720p60, settled output | 60 s | 36.013 | 5.877 s | Timing failed |
| Four real cameras including quad, 720p30 | 120 s | 22.650 | 18.575 s | Timing failed |
| Four individual cameras, 1080p30, ultrafast | 120 s | 28.549 | 5.169 s | Timing failed |
| Automatic cameras/maps, 1080p30, ultrafast | 240 s | 29.383 | 4.938 s | RTSP timing failed |
| Basement RTSP receiver, current HD30 program | 60 s | 27.308 | 5.298 s | RTSP timing failed |
| Original local RTMP, current HD30 program | 60 s | 30.000 | 0.034 s maximum interval | Timing and full decode passed |

The original RTMP clip has no large picture or audio timestamp gaps, and no non-advancing timestamps. Its maximum audio interval is 22 ms at 48 kHz. This short pass does not erase earlier failures or prove that every scene renders 30 distinct pictures per second. It establishes a clean original encoded timeline during that sample.

A subsequent simultaneous 90-second comparison read RTMP and RTSP from the same local relay. RTMP passed at 30.000 packets/s, with maximum video/audio intervals of 34/22 ms and clean decoding. RTSP failed at 28.085 packets/s, with a 5.738-second picture gap and no recorded audio packets. This isolates a transport-path difference during the comparison; the precise MediaMTX/FFmpeg RTP timestamp defect is not yet established. Earlier RTSP gaps must not all be reported as rendering failures.

The private standby relays now read the original RTMP stream instead of converting it through RTSP. The laptop resolves its local relay's Docker address at each reconnect, without exposing another LAN port. The basement forwarder reads its local standby RTMP path. Both retain stream copying, bounded progress logs, stalled-output recovery and the separate test key. Only test publishing reconnected; the engine, local picture and main broadcast were preserved.

After that change, the finalized two-minute recording at the basement RTMP receiver PASSES: 1920 by 1080, 30.000 video packets/s, maximum picture interval 34 ms, 48 kHz audio with maximum interval 22 ms, no large gaps or non-advancing timestamps, and clean full decoding. Both relay progress counters advance. An earlier file copied while capture was still active is excluded from acceptance; the finalized `received-rtmp-final-120s` recording is the evidence. This closes the bounded receiver check, not YouTube client inspection or long-term thermal acceptance.

The interlaced file was verified top-field-first at 30000/1001 encoded frames per second. Native channel clocks run at 60000/1001 ticks per second, and the FFmpeg consumer interleaves fields. It did not improve this workload. The laptop panel's physical scan mode is separate from the encoder format. Likewise, 720p60 was not a successful performance fallback. The first unready 720p60 capture failed before usable video existed and is not included as a valid measurement.

Maximum sampled temperatures were 64 to 74 C across this pass, including 70 C in the four-minute automatic observation. The earlier 81 C throttling record remains in [the initial hardware acceptance](INTEL-ACCEPTANCE-20261023.md). Closing the lid has not passed a long thermal soak.

## Software validation and remaining gates

The local regression suite passes 580 tests with one Linux-only skip on Windows. Snapshot cloning has five focused checks, including source preservation, inactive destinations, manifest corruption, unknown cameras and unsafe members. New format tests distinguish native field clocks from encoded frame cadence and reject interlaced publishing through unsupported encoders. Source-release checks pass. These are local results, not a new hosted CI result.

At this morning checkpoint, the longer soak, production reboot, clean installation and dependency review were still open. The later one-hour soak, actual production reboot and clean-build/source results are now recorded in the current checklist. The RTSP defect and comfortable quad performance remain exceptions. The standby delivery path bypasses the reproduced RTSP problem. The new format options are implemented and exercised, but only the selected HD30 individual-camera workload is operator-accepted for this standby.

Main production was left on its existing application and UHD30 profile. Its bounded status check reported ready, moving video at 29.99 fps. That observation is not a new production soak.

See [standby operation](STANDBY.md), [initial hardware evidence](INTEL-ACCEPTANCE-20261023.md) and [release acceptance](ACCEPTANCE-STATUS.md).
