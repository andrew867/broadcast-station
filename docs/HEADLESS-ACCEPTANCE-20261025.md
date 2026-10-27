# Headless acceptance, 25 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

The existing NVIDIA and Intel engine images render through EGL without an X11 socket, desktop authentication file, Wayland environment or PipeWire socket. The application now selects desktop or headless Compose profiles explicitly. Desktop remains the default, and both on-air stations retain their HDMI configuration.

## Recorded checks

| Check | Result |
|---|---|
| NVIDIA RTX 3070 native UHD30 | 359 decoded 3840 x 2160 frames; NVENC; visible HTML marker; non-silent 48 kHz audio; clean decoding. |
| Intel T480s native HD30 | 359 decoded 1920 x 1080 frames; Intel Mesa OpenGL; libx264; visible HTML marker; non-silent 48 kHz audio; clean decoding. |
| Software EGL, no X server | 187 decoded 720p frames; visible HTML; non-silent 48 kHz audio. Functional coverage only, below real-time speed. |
| NVIDIA complete station | Started through the installed headless user service; switched daylight to Moon; process crash triggered one Docker restart; controller restored Moon graphics and music. Before/after recordings contained 441/389 frames and decoded cleanly; the recovered output was received over RTMP with H.264 and AAC. |
| Intel complete station | Started through the installed headless user service; switched daylight to Moon; process crash triggered one Docker restart; controller restored scene and music. Recordings contained 451/389 frames. Recovered H.264/AAC output was received over RTMP and decoded cleanly. |

Both complete-station checks use 720p30 alongside the existing live stations. They use separate ports, directories and Compose projects, disabled external providers, generic graphics and a local 48 kHz test tone. Their temporary services and containers are removed afterwards. They do not replace either on-air station or publish to YouTube.

A first recovery experiment used `docker kill`, which counts as a manual container stop and suppresses Docker's restart policy. That attempt failed to recover and is retained as a test-method failure. The corrected crash test verifies the isolated container identity, kills its host process, then observes Docker restart and application restoration.

## Boundaries

These are bounded recordings and recovery checks, not a long headless soak. Both computers had their normal desktop sessions running elsewhere; the test containers did not have access to those sessions. Cold boot with no user login has not been measured. The startup service and documented user-lingering setup support that deployment, but a service definition alone is not boot acceptance. AMD, ARM and other GPU/driver combinations remain untested. Intel quad and sustained UHD60 remain outside the accepted performance scope.

Hardware evidence, screenshots and recordings are retained in the private `headless-20261025` acceptance bundle. The generic software test is also part of the native GitHub workflow. See [headless installation](HEADLESS.md) and the [current release checklist](RELEASE-CHECKLIST.md).
