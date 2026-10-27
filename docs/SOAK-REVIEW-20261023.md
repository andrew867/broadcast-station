# Production soak review, 23 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

The bounded 24-hour observation from 22 October 12:49 UTC to 23 October 12:49 UTC completed with 2,670 samples. Program status stayed ready, with no failed program probes, no non-moving observations and no samples below 95% of the target frame rate. Measured frame rate ranged from 29.4 to 30.62, averaging 30.0026. The largest observation interval was 35.55 seconds.

This establishes sustained sampled program health, not perfect camera delivery or continuous audio/video acceptance. The separate recordings and operator listening checks remain the playback evidence.

## Camera delivery

| Source | Unready observations | Observed groups | Longest span between unready observations |
|---|---:|---:|---:|
| West | 46 | 3 | 1,260 seconds |
| North | 45 | 2 | 1,260 seconds |
| NTV 1 | 63 | 25 | 130 seconds |
| NTV 2 | 3 | 2 | 32 seconds |
| NTV 3 | 74 | 64 | 33 seconds |
| NTV 4 | 175 | 137 | 65 seconds |

Every group ended with a later ready observation. These are sampled groups, not exact outage counts or durations. Single unready observations have no measurable duration. Decoder generation changes also show reconnects between observations, so this table cannot account for every interruption. Source readiness and native scene warmup are reported separately.

Later daytime measurements found slow-reader drops, TCP retransmissions and high latency across the powerline network. That evidence explains a current delivery problem but does not prove the cause of every overnight camera interruption. Additional GPU activity was reported later that day. Its overlap with the daytime measurements was not established and is not attributed to the completed soak.

## Resources and recovery

All five container start timestamps remained unchanged throughout the soak, with zero Docker restarts, no OOM reports and no not-running observations. Watchdog history remained unchanged; its two earlier controller recoveries predate the soak and are not counted as overnight events.

Engine memory began at about 1.13 GiB, peaked at 1.66 GiB and ended at 1.39 GiB. Controller memory began at 1.21 GiB, peaked at 1.48 GiB and ended at 1.11 GiB. Source health ended near 337 MiB and the source hub near 60 MiB. These samples do not establish a monotonic leak.

Docker block-write counters increased by about 50.74 GB for the controller and 3.64 GB for source health. This measures writes over time, not retained file size. Map and radar frames were regenerated as uncompressed bitmaps on disk. A follow-up changes those temporary frames to fast lossless PNG and reuses the resized image for the confidence preview. A local radar-frame comparison preserved every RGBA pixel and reduced one frame from 8.29 MB to 3.55 MB, at a higher encoding cost. Host measurements are required before claiming an overall performance improvement.

## Repeat the review

Run from the source checkout:

```sh
python tools/review_soak.py /path/to/soak/samples.jsonl --output /path/to/review.json
```

The tool runs offline. It separates missing probes from ready/unready states, splits groups at gaps over 60 seconds by default, records service start changes and counter resets, and excludes watchdog events older than the observation. It does not issue an automatic acceptance verdict. Keep reports private because they include station camera identifiers, container names and recovery reasons.

## Remaining acceptance work

1. Improve or limit competing traffic on the powerline network, then repeat camera delivery measurements.
2. Observe long-term write volume and CPU after the lossless-frame update. The host benchmark preserved every pixel, reducing one real map frame from 8.29 MB to 1.00 MB and two radar frames to about 2.7 MB. In a one-CPU test container PNG encoding took about 143 ms for the map and 230 to 238 ms for radar, versus 4 to 5 ms for BMP. The update also removes a duplicate resize. This trades encoding work for lower disk writes; it does not increase the refresh rate or promise lower CPU use.
3. Hosted regression is now complete at application commit e5945c0: run 40043696464 passed 559 Linux tests, 559 restricted-container tests, image startup, synthetic source loss/recovery and source/history checks. Windows passed 558 with one Linux-only skip. The two previous attempts stalled downloading libavcodec60 from the hosted Ubuntu mirror and reached the job timeout before tests. The corrected runner mirror and bounded network timeouts passed; those cancelled runs remain recorded as cancelled.
4. Qualify actual reboot and desktop login recovery in an appropriate window. The later engine restart is outside this soak and has not been attributed to a watchdog action.
5. Keep Intel/T480s, clean-host operator acceptance and native binary distribution clearance open.

## Deployment evidence

The controller update was deployed around 00:14 UTC on 24 October, still the evening of 23 October locally. Only studio was replaced. Engine start stayed 23 October 21:09:46 UTC, unchanged by this update. Controller image ID is `sha256:ac52cc57404293c101866e0819cc29c4758b2f577d2dbac2cc84269df0576637`, tagged `station-controller:stability-20261023` and `station-controller:candidate`.

The first deployment attempt automatically restored the previous controller because the acceptance helper compared unavailable startup telemetry with a number. The helper was corrected to wait for four consecutive valid readings; the second attempt passed at 30.00 to 30.10 fps. This was a deployment-check defect, not evidence of a production frame-rate failure.

The live radar and island map previews were visually reviewed. Radar showed 21 aircraft and a healthy receiver; the native radar channel reported an image producer reading the new PNG path. The browser's only console error was the missing favicon. Private evidence, complete observations, deployment details and screenshots are retained outside the public source package.
