# Controlled power-cycle recovery, 26 October 2026

The NVIDIA production station recovered its UHD30 network programme and music after an orderly shutdown, a physical PSU power interruption and manual startup. The operator confirmed switching the PSU off and on and pressing the power button. This qualifies the tested desktop-autologin startup path; it is not an abrupt-loss, automatic BIOS power-restoration or headless cold-start test.

## Procedure and evidence

The original station settings were checkpointed on the host with restricted permissions and archive integrity checked. The fixed `0.1.0-alpha.1` engine/controller image pair, programme format, boot identity, enabled services and settings hashes were recorded before shutdown.

An independent receiver on the relay host observed healthy UHD video and 48 kHz audio before shutdown, then loss of the stream, followed by recovery. No post-start SSH connection to the production host occurred before that recovered recording completed.

The station launcher recorded successful startup approximately 41 seconds after the reported Linux boot time. The first recovered eight-second receiver clip completed approximately 66 seconds after that boot time. Its first decoded image was black during startup; frame analysis found a 0.6-second black interval followed by visible camera-quad graphics. A later frame from the same clip showed the live quad and ticker. These are bounded observations, not an exact first-picture latency or startup-time guarantee.

The host had a new boot ID. The station configuration, branding, generated Compose environment and native configuration hashes matched their pre-test values. Both immutable image IDs were unchanged. The rundown was enabled, programme frames were advancing at approximately 30 fps, native audio was present, and the watchdog and display helper were active.

A subsequent 90-second network recording passed full decoding, measured 30.000 video packets per second and contained non-silent 48 kHz audio. No large audio/video timestamp gaps or nonadvancing timestamps were found. Stream coverage passed. Representative camera and graphics frames were inspected.

## Desktop-session repair

The first physical HDMI capture showed a restored Roblox window covering the programme. CasparCG's programme window was running at the configured secondary-display coordinates. Network output was unaffected.

KDE was changed to `loginMode=emptySession`, and the operator-authorized Brave and Sober/Roblox processes were closed. Automatic login and explicit station/OpenRGB startup entries were retained. A new capture then showed the programme correctly.

A follow-up normal reboot checked the new desktop policy. The reboot SSH command ended unexpectedly before the initial observer started, so read-only SSH diagnostics were used during boot. This follow-up is therefore not evidence of recovery before any SSH connection. The original physical-cycle recording remains the independent evidence for that condition.

After the follow-up reboot, KDE retained `emptySession`, Brave and Sober were absent, the station launcher reported success, and the watchdog/display helper were active. UHD30 programme and native audio were advancing. USB capture showed the camera, lower third and ticker without manual window changes, with a non-silent low-level audio signal.

## Scope and remaining checks

- The attached USB device advertises recording modes up to 1920x1080 at approximately 60 fps. Its capture verifies HDMI layout and signal, not native 4K recording. Network recordings verify UHD30 output independently.
- The operator reported that firmware likely restores the previous power state and had started automatically after an earlier outage. Firmware configuration was not inspected. Manual startup in this controlled test does not establish automatic restoration after an unexpected outage.
- The controlled shutdown does not test filesystem survival under sudden power loss, UPS behavior or every camera/network failure.
- The follow-up verified the empty-session fix through a normal reboot, not a second physical power interruption.
- Clean supported-GPU OS installation remains open. The current hardware installations and a clean software-rendered VM do not substitute for that test.

See the [release checklist](RELEASE-CHECKLIST.md), [extended observation](SOAK-20261026.md) and [validation procedure](RELEASE-VALIDATION.md) for the remaining acceptance scope.
