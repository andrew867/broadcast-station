# Deployment and studio candidate evidence

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

21 October 2026. Intermediate deployment and studio verification; the full acceptance sequence had not completed.

- The portable controller image built on Linux. A synthetic RTSP source passed initial decoded readiness, source-loss detection and recovery to a new decoder generation. A confidence JPEG was produced. The container had no external network or GPU, one CPU and 2 GB RAM.
- 503 Windows tests passed in 93.36 seconds after the deployment changes. Disabled-by-default demonstration cameras required existing probe/recovery fixtures to enable the camera explicitly.
- The full-stack Compose files, pinned MediaMTX binary, private camera fan-out, optional NVIDIA/Intel device profiles, launch validation, host preflight, rotating logs and conservative picture-cache maintenance are implemented.
- The host watchdog wrapper uses the existing bounded guard and candidate Compose project IDs. Observe-only mode is the default. Full output failure and restart drills remain open.
- Studio navigation is in browser acceptance: seven pages, persistent status, searchable scene list, retained form nodes and pending-edit warning. Browser review found and fixed an inherited grid-width rule and a detached-node lookup error.

Open gates: native image build/link checks for this snapshot; full-stack GPU picture/audio recordings; source/relay and watchdog fault drills; desktop session/reboot recovery; complete studio acceptance; fresh backup. Production migration, candidate 24-hour soak and actual T480s qualification have not occurred. Nothing here qualifies UHD60 or Intel output performance.
