# Intel laptop acceptance, 23 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

This is the historical first-install record. The [24 October standby follow-up](INTEL-STANDBY-20261024.md) supersedes its final operating state and pending listening confirmation, while retaining the failures below.

The first T480s installation is running on an isolated station. Public hardware qualification remains pending until the recording, recovery and real-source checks below are complete. This test does not change the existing broadcast.

## Observed host and installation

- EndeavourOS x86-64, Intel UHD Graphics 620, 16 GB shared system memory and a 1920 by 1080 local panel.
- Desktop OpenGL: accelerated Intel Mesa, core version 4.6. This host report is separate from native-container renderer evidence.
- Docker Engine 29.6.1 and Compose 5.1.4, with an existing working desktop and PipeWire audio socket.
- Private native image imported from the retained, checksummed archive. Controller rebuilt from the previously verified dependency image with an identical Python lockfile and current source. This is not a clean public-registry build.
- Program format 1080p30, libx264 output at 8 Mbps, local display and a private relay confined to the test station. External providers and paid credentials remain disabled. Generated music uses the warm preset, now at volume 0.35 after the operator reported low output.
- Four independent camera readers initially receive local 720p30 synthetic video. A native composited still confirms all four pictures, labels and the program ticker.

## Defects exposed and repaired

1. Intel initialization previously retained the NVIDIA encoder default. New Intel stations select libx264 and HD30; existing operator configuration is preserved.
2. A host with `card1` but no `card0` produced duplicate Compose supplementary groups. The Intel OpenGL client now receives the render group without guessing the primary display-card group.
3. The container's Intel driver could decode H.264 but rejected `scale_vaapi` video processing. Intel health decoding keeps VAAPI, then downloads and resizes the small preview on the CPU. The other hardware-scaling profile retains its existing behavior.
4. Rapid camera inventory updates could leave MediaMTX using an earlier registry. Its upstream watcher ignores reload events within one second. The writer now coalesces changes and spaces complete configuration replacements by at least two seconds. The final registry remains pending until written, so it is not silently lost. [Upstream watcher source](https://github.com/bluenviron/mediamtx/blob/v1.21.2/internal/confwatcher/confwatcher.go).
5. The watchdog stopped reading an AMCP response at the first closing `channel` tag, including nested tags inside a fragmented reply. Both watchdog readers now wait for a complete XML document. Fragmented-reply regression tests exercise both implementations.

## Acceptance record

The local regression suite passes 567 tests, with one Linux-only test skipped on Windows; the subsequent XML-reader fix passes 32 focused watchdog checks including two new fragmented-reply cases. Hosted run 40048421135 passed the initial Intel/camera fix, including Linux and restricted-container tests and an image build. Host readiness, actual Compose startup, hardware-decoded source frames and native scene composition are observed.

The five-minute private recording passes at 1920 by 1080 and 30.000 video packets per second. The largest video interval is 37 ms, audio is 48 kHz, neither stream has a large timestamp gap and full decoding is clean. A sampled transition contact sheet shows a complete camera scene changing to the daylight card with the ticker preserved. The operator confirms the local picture is normal; music was audible but too quiet, so its test volume was raised from 0.10 to 0.35.

Rapid disable/enable edits recovered all sources without restarting the fan-out or changing the untouched camera's reader generation. A deliberate 20-second interruption of the synthetic publisher recovered all four decoded feeds about eight seconds after restoration. The thermal observation includes these deliberate faults and deployments, so it is an exercised run rather than a clean unattended soak.

Native startup logs confirm Intel OpenGL 4.6 with Mesa 25.2.8 inside the container. A stopped controller recovered automatically in about 60 seconds while the engine remained running. A separately stopped engine recovered in about 50 seconds through the normal watchdog policy. Both tests used SIGSTOP on the isolated laptop containers, with the normal recovery cooldown retained.

The 30-minute exercised observation completed with 98 samples. It includes deliberate outages, recovery tests, deployments and recording verification, so it is not an unattended soak. Maximum sampled temperature was 81 C; the CPU package thermal-throttle counter increased from 1,732 to 5,980. Program samples ranged from 7.48 to 34.55 fps, averaging 28.14, with 17 low-rate samples and three failed probes. These results do not qualify sustained HD30.

Adding one 2688 by 1520 real camera alongside three synthetic readers exposed insufficient headroom and intermittent source delivery. The two-minute recording decodes cleanly but FAILS continuity: one roughly 5.05-second gap affects both audio and video, and its average packet rate is 28.741 fps. Quad rendering subsequently fell to about 15 to 23 fps. The interruption's cause is not established by this recording alone. Keep the failure in the acceptance record.

The optional desktop audio mount now refuses to create a directory when its source socket is absent. A real Compose invocation using an intentionally absent socket was rejected and left the path absent. The engine was recreated with that mount before the reboot test. On actual reboot and manual KDE login, the boot ID changed, the display cookie changed, the login launcher reported started after the new boot, both user services became active, and the program resumed with a 48 kHz PipeWire sink input. No manual station start was issued after reboot. Production was not rebooted.

The desktop indexer was repeatedly working while the test folder held changing media. Only that folder was excluded from Baloo indexing; general desktop search remains enabled. Recording verification now uses one decoding/filter thread and subsequent output is checked off-host to avoid competing with playout. Post-reboot recording and listening at the adjusted volume are reported separately when complete. A clean intended-workload thermal soak remains open.

The full public binary notice/source review and a clean-clone operator installation remain separate release gates. See [first-run procedure](LAPTOP-ACCEPTANCE.md) and [current acceptance status](ACCEPTANCE-STATUS.md).

## Post-reboot performance follow-up

The one-minute mixed-source recording after reboot also fails: 16.279 video packets per second, 110 large picture intervals, two large audio gaps and non-advancing timestamps. Its decode is clean, which does not make its timing acceptable. Excluding desktop indexing did not solve this workload.

The Intel health checker now selects every third already decoded frame before GPU download and CPU resizing. No fps conversion or stale-frame duplication is used. On the real GPU, source-health CPU fell from roughly 190 percent to roughly 80 to 95 percent, and recent decoded frames were still observed for all four sources. A real FFmpeg regression check emits exactly ten frames from a thirty-frame synthetic input. This is a resource improvement, not qualification of the whole station: the subsequent mixed-camera observation still fails sustained HD30. Very low-rate source feeds should use a stride of one.

The complete local suite passes 570 tests with one Linux-only skip; an additional actual-FFmpeg sampling test also passes. An earlier run from the parent workspace failed three child-process imports because it used the wrong working directory. Running from the application root resolved those failures without changing application code.

The laptop is returned to four local synthetic feeds for the next baseline recording. The mixed-source configuration and all failed recordings are retained privately. Production configuration and images are unchanged by this hardware pass.
A controller-only update followed by replacement of the source fan-out exposed a separate recovery defect. Native camera counters stopped, while independent health frames remained fresh. For a producer adopted after controller restart, no retry timestamp existed, so the retirement check used the current time on every pass and its eight-second grace period never elapsed. The fix gives an adopted producer one fixed deadline; a regression test advances time past that deadline and requires its release without touching program or music. Hardware recovery is checked separately after deployment.

Hosted run 40051426444 failed an unrelated sponsor test: its assertion searched the whole command for `1-18`, which also occurs when a `sponsor-cam1-` artwork hash begins with `18`. The check now examines the AMCP target token. That failure is retained; it was not an on-air sponsor-layer change.

## Final checkpoint

The adopted-decoder fix recovered all four native pictures on the laptop without restarting its engine. The actual composited quad was inspected and contains all four test pictures and the ticker. The subsequent 90-second synthetic recording PASSES: 1920 by 1080, 30.004 video packets per second, maximum video interval 34 ms, 48 kHz audio with maximum interval 22 ms, no large gaps or non-advancing timestamps, and clean full decode. This closes the short synthetic recovery baseline, not the failed larger live-camera workload or a long thermal soak.

Application checkpoint 70f9a5d passes 572 local tests with one Linux-only skip. Hosted run 40052025988 passes its Linux tests, restricted-container tests, image build, deployment smoke checks and synthetic recovery. The native engine image is unchanged. The laptop controller image is sha256:bae6a27dc2dbecf89fe7cc768965bd9ceabb5eb10e86d5ce0a569cfdd39d0950; its source-health/fan-out image is sha256:6681db17e9e4e62442029f306f1101256c52073ab41c974107e8c9b38c73785d from the preceding Intel checkpoint. Their relevant health/fan-out code is identical. Private image bases and retained source archives are still required; no public-registry install is claimed.

The test relay's single-file configuration bind did not adopt the restored source automatically. Its explicit restart restored the local synthetic route. That private test interruption is distinct from production and from the application camera-hub directory mount. A visually blank slate recording taken before the recovery fix is retained as failed visual evidence even if its packet timing is regular.

Still open: operator listening confirmation after increasing laptop music volume, a sustained intended-camera workload within the Intel host's thermal budget, clean long-duration Intel acceptance, production reboot/login, and the public binary and clean-install gates. Production remained running at UHD30; the latest bounded check was 30.07 fps with no reported playout error.
