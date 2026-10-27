# Reliability acceptance, 24 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

This is bounded acceptance of the current NVIDIA production and Intel standby configurations. It is not a promise of uninterrupted service or sustained UHD60.

## Standby original-RTMP path

The T480s ran four real sources, individual camera/map scenes, news and music for 3,612 seconds. There were 162 health observations, with a largest interval of 22.874 seconds. Program was ready in every observation. Mean reported rendering cadence was 29.712 fps; the range was 24.89 to 30.30 fps, with nine low-cadence observations. Maximum recorded CPU temperature was 73 C.

All five station containers retained their start times and zero restart counts. No OOM kill was reported. The single decoded-source failure was cam2, whose latest picture was 5.721 seconds old. At that observation the on-air ntv-cam2 scene remained ready and moving at 29.96 fps. The next observation recovered. This establishes an independently recovering source event during continued program operation; it does not establish the upstream cause of that camera interruption.

Three approximately one-minute original-RTMP recordings, near the start, middle and end, passed complete decoding. Each measured 30.000 video packets per second, maximum video timestamp interval 34 ms, and 48 kHz AAC with maximum audio interval 22 ms. No large timestamp gaps or duplicate video timestamps were found. Frames inspected from the first and last recordings showed aligned camera graphics and ticker without the previously reported downward smear.

These were three bounded recordings, not a continuous hour-long capture. Packet cadence can include repeated pictures. The laptop remains accepted for individual HD30 scenes with occasional rendering dips; quad and sustained 720p60 are not qualified. This pass did not include a new end-to-end YouTube listening confirmation.

## Production reboot

The pre-reboot station settings were archived and verified. After a real reboot, the boot ID changed, KDE autologin ran the configured station launcher, the saved rundown resumed and the watchdog/display services returned without a manual start. The station configuration hash remained unchanged. Native output reported UHD30, moving frames and non-silent stereo audio.

A subsequent one-minute recording at the basement MediaMTX receiver passed full decoding at 3840 by 2160 progressive, 30.000 video packets per second, with maximum 34 ms video and 22 ms audio timestamp intervals. Audio was 48 kHz and non-silent. A captured radar frame showed aircraft, ticker and clock. Physical TV and YouTube client confirmation after this specific reboot remains an operator observation, separate from these automated checks.

## RTSP exception

The previous simultaneous comparison showed clean original RTMP, while RTSP conversion produced approximately 28.085 video packets per second, a 5.738-second gap and absent audio in that recording. A fresh simultaneous 60-second comparison on 24 October had continuous packet cadence on both protocols, but RTSP audio began 3.056 seconds after its first video picture. RTMP audio covered the entire recording. The recording checker now includes stream-start and end coverage, so steady cadence alone cannot hide this failure. Both standby publishing routes now consume original RTMP. The longer RTMP test above passes, but the exact RTSP defect is unresolved. Do not restore RTSP to the publishing chain based solely on a working player connection.

For investigation, capture both transports concurrently from the same encoded source and compare stream declarations, audio packet counts, timestamps and decoder errors. Keep source and receiver versions, workload and network evidence with the captures. Avoid changing the working on-air route to investigate this exception.

## Evidence and reproduction

Private acceptance evidence is retained under `outputs/release-acceptance-20261024`: `standby-soak/summary.json`, `samples.jsonl`, `recordings.json`, three captures, production reboot JSON and the post-reboot recording/report. These contain local station details and are not bundled into the public source archive.

Use `tools/check_program_recording.py` for bounded receiver files and the procedures in [the current checklist](RELEASE-CHECKLIST.md) to keep source health, native frame progression and encoded delivery separate. Do not convert a camera reconnect warning into a renderer restart unless independent native evidence supports it.

## Upstream timing lead

MediaMTX [issue 6300](https://github.com/bluenviron/mediamtx/issues/6300), still open when reviewed on 24 October, describes per-track NTP anchoring and RTCP sender-report offsets when shared-timeline RTMP/SRT sources interleave audio behind video. That mechanism is consistent with the measured delayed RTSP audio while original RTMP is clean. It is a plausible upstream cause, not proof that every observed gap came from that issue. No unreviewed server patch or protocol change was deployed on air. Keep the RTMP publishing workaround until a separately tested upstream correction passes repeated join and long-running coverage checks.
