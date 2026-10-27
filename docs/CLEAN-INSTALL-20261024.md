# Clean Linux installation acceptance, 24 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

## Starting point

A new Ubuntu 24.04 x86_64 cloud-image guest was created on the basement host, with four virtual CPUs, 8 GiB RAM and a new 70 GiB disk overlay. The official image was checked against the upstream HTTPS SHA-256 listing. This was not a GPG signature verification. The initial Docker image list was empty and is retained with the acceptance evidence.

Only host prerequisites were installed: Docker Engine/Compose/Buildx, Python, Git, FFmpeg, Xvfb and Xauthority tools. The VM received the generic release source archive and an SSH public key for access. It did not receive a private station directory, provider or publishing keys, camera references, operator music, a prebuilt controller/native image or retained build dependencies.

The guest has no assigned GPU. This proves clean source builds and software-rendered functionality separately from the existing NVIDIA and Intel hardware tests. It does not qualify a new physical GPU driver or unattended graphical login.

## Preview procedure

From the unpacked source directory, the documented command was run:

```sh
docker compose up --build -d
```

The build fetched its declared public inputs and started the generic studio. Browser review used an SSH tunnel to its loopback-bound port. The studio showed original demonstration patterns, configurable generic branding and a clear offline notice. No private feeds or settings were present. After the hardened rebuild, Graphics-page controls stayed disabled across subsequent refreshes; normal page navigation remained available. Browser console inspection reported zero errors and warnings.

The preview container uses a read-only root filesystem, dropped capabilities, no-new-privileges, bounded temporary storage and rotating logs. Its data volume contains only demonstration state. Preview mode denies outbound Python sockets and operator writes; it does not start CasparCG.

The first manual native build exposed a missing Buildx plugin in Ubuntu's basic Docker package set. Compilation succeeded, but legacy image-layer packaging was excessively slow. That run was preserved as diagnostic evidence. Buildx was installed explicitly, the prerequisite checks/manuals were corrected, and the unchanged native recipe was rerun using the supported builder. No production host packages were changed.

## Full-stack checks

The controller was built independently from the same pinned public inputs. Restricted-container regression ran without network, with a read-only root, one CPU, 2 GiB RAM and bounded temporary storage. The real full-station Compose launch check created a fresh generic station, validated its mounts/settings and started the controller with playout enabled on an internal-only Docker network. It correctly reported that no engine was connected. This checks the actual full-station configuration rather than accidentally testing offline preview mode.

The native engine was built from `deploy/Dockerfile.caspar-readback`, including the 17 CasparCG patches and exact CEF SDK. Packaging passed after correcting a false assumption that the SDK and Debian runtime libraries must be byte-identical. Both upstream builds are now pinned and their identities distinguished. The final 12-second bounded capture contains 98 decoded 1280x720 frames, non-silent 48 kHz audio and a CEF-rendered HTML graphic whose sampled colour matched the fixture. Full decoding and screenshot inspection passed. This slow software-rendered VM is not a real-time output benchmark. The first six-second HTML attempt did not meet the minimum frame count; it remains failed evidence, and the successful run allowed eight seconds of Chromium warmup before capture. The software rendering check uses synthetic colour/motion and a known 48 kHz tone, an isolated Xvfb display and a restricted engine container. It is deliberately not a GPU throughput benchmark.

## Repeat on another Linux computer

1. Install the prerequisites in [Linux deployment](LINUX-DEPLOYMENT.md). For a physical station, confirm the desktop's GPU driver and container device access using `tools/host_readiness.py`.
2. Start the generic preview with the command above and inspect the studio. No provider account is needed for this step.
3. Create a separate station directory using `tools/stationctl.py init`, select the appropriate Intel or NVIDIA profile, and review output/display settings. Providers and publishing default to off.
4. Follow the full-station check/start commands in the deployment guide. Validate synthetic picture/audio first, then add real sources and publishing credentials privately.
5. Record receiver output and complete the hardware and reboot/login checks before treating that computer as a standby or production station.

The project supports a one-command offline preview after host prerequisites. Full GPU playout additionally requires explicit device, desktop and station/output setup. No installer silently changes drivers, autologin, desktop audio or publishing destinations.

## Evidence

Private evidence contains the empty initial image list, source archive hashes, build/test logs, image inventories, browser screenshots/console results and rendered native recording. The final engine inventory has no missing expected notice/source files or NDI runtime. Its 269 source-package identities and the controller's 233 identities exactly match their retained archives.

The current source can be downloaded from the built application's `/source` route. The archive is generated from build inputs, not from the live data volume.

See [the current checklist](RELEASE-CHECKLIST.md) for final results and exceptions, [native dependencies](NATIVE-DEPENDENCIES.md) for matching source materials, and [security review](SECURITY-REVIEW-20261024.md) for the scope of hardening.
