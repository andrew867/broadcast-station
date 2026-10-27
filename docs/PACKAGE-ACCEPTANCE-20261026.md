# Versioned package upgrade acceptance

## Artifact identity

The private `0.1.0-alpha.1` runtime installer was installed on the Intel standby first, then on NVIDIA production. The installer SHA-256 is `1105a9deacb73b777a53fbf0bba7a4e9cc2e167d663326d665a42fa1850925f7`.

The release source is revision `c02a916a55424b69277db163ddde4c6de9db8fa1`. The controller image embeds application revision `fa7f069f595cfc3b760d3b3e3a382a2d27c4ad54`; the later release revision adds documentation and verification tooling. The complete corresponding-source collection remains separate from the smaller runtime installer.

| Component | Immutable image identity |
|---|---|
| Controller | `sha256:13078cc57888363627dc1b94dd18c09bd8d0358607d4dbd27fff146d0ad6a8f7` |
| Engine | `sha256:5a164704753d9781ab47254848f490bad3b4fc8822223df1be142b84713dc5d4` |

## Upgrade procedure

Each host received the frozen installer. Its archive digest and all ten manifest assets were verified before the Docker images were loaded. Both loaded image identities matched the manifest. The release source was extracted into a permanent directory, and the existing station directory was retained.

The documented `prepare`, `check` and `resume` sequence completed without rebuilding images. Compared operator configuration files remained unchanged, including branding, rundown, music settings and flight-enrichment budget policy. Startup entries and recovery services now use the versioned release directory. Existing publishing routes were preserved. Verified settings and database checkpoints and the preceding image pair remain available for rollback.

## Intel standby

The packaged station ran at 1920 by 1080 progressive, 30 fps, with EGL rendering and software H.264 encoding. It had no X11, Wayland or desktop-audio mounts.

- The corrected no-login reboot test confirmed moving programme and current music after 83 seconds, before the first SSH login. The display manager remained inactive; the first session inventory contained the user service manager and the inspection SSH session, with no graphical session.
- A three-minute observation averaged 29.98 fps, with sampled rates from 29.80 to 30.10. There were no failed programme probes or unavailable programme samples. One native camera warmup observation occurred without a decoded-source outage.
- A separate three-minute receiver recording decoded cleanly at 30.00 fps, with non-silent 48 kHz audio and no large audio or video timestamp gaps.
- Decoded camera and aircraft-map frames were visually inspected. Programme graphics and the news ticker were present.
- Studio and guide requests succeeded, the automatic rundown resumed, and AISStream was connected with recent position reports.

The first reboot-check helper mishandled an initially null frame counter and labelled subsequent successful HTTP observations as failures. The helper was corrected, the original observations retained, and the reboot check repeated. That diagnostic error was not a station startup failure.

## NVIDIA production

Production resumed at 3840 by 2160 progressive, 30 fps, with its desktop HDMI and desktop audio options retained. A separate one-minute receiver recording decoded cleanly at 30.00 fps, with non-silent 48 kHz audio and no large audio or video timestamp gaps.

After the separate [UHD60 display comparison](DISPLAY-PERFORMANCE-20261026.md), production returned to its original UHD30 configuration. Another 90-second receiver recording passed, and the physical HDMI programme picture was inspected through USB capture. The rundown, desktop display helper and watchdog were running normally.

## Acceptance limits

These results establish the private package upgrade path on the two existing installations. They do not establish installation on a clean GPU operating system, a physical power-off/on recovery test, or sustained UHD60 performance. Receiver timestamp checks establish cadence and decoding integrity; they do not prove perceptual audio quality, lip sync or 30 distinct camera exposures each second.

See the [release checklist](RELEASE-CHECKLIST.md) for the remaining public-release requirements.
