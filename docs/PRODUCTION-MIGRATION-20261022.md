# Production migration, 22 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

The release package is now serving the station. The operator confirmed that HDMI and YouTube picture and sound are normal. The original installation is retained for rollback. This record supersedes earlier statements that production had not migrated.

## What changed

The live controller now uses the portable station configuration and the seven-page studio. Existing graphics, rundown, accepted generated music, references and account settings were imported. The two Sheerr cameras and NDI remain disabled. The output remains UHD30 with HDMI, desktop sound and the existing MediaMTX/YouTube route. The relay configuration was not changed.

Host recovery is station-scoped. The display service inhibits desktop blanking while this station's HDMI engine is running. Login startup refreshes display and audio access. An actual logout/login and reboot drill is still required.

NVIDIA continues to render and encode program. This hybrid host's integrated GPU decodes camera health pictures through VAAPI. That does not qualify an Intel-only laptop or imply that both GPUs encode program.

## Repairs found during acceptance

The watchdog compared a response timestamp with a time captured before its probes. A healthy controller could therefore appear to have a timestamp in the future. Two false controller recoveries occurred before the comparison was moved after the HTTP response. Their history is retained; it was not cleared to make the result look clean.

The camera health reader also exposed an older scheduling defect. Its sparse thumbnail output stalled decoded-frame delivery for roughly five seconds, falsely declaring working sources unavailable. An independent live-feed comparison measured a maximum 5.03-second gap with the old graph and 0.18 seconds with a single output. The reader now assembles complete 640x360 NV12 frames and writes a JPEG every five seconds from those frames, without a second decoder. Its 2.5-second freshness threshold is unchanged. Partial frames do not count as ready. A thumbnail write failure does not restart acquisition.

The repair passed a synthetic source test with sustained readiness between thumbnails, loss detection and recovery from generation 1 to 2. Only source-health was replaced for this repair; the running program engine and music were preserved.

## Recordings and rollback

| Check | Result and limit |
|---|---|
| Physical USB HDMI capture | Pictures recorded and visually inspected before and after migration. No replug was required. |
| Operator playback | HDMI and YouTube picture and sound confirmed normal. |
| Candidate recorded at relay | Two minutes, 3840x2160, 30.003 video packets/second, maximum interval 34 ms, clean full decode, 48 kHz audio, no detected large audio gaps. |
| Final post-repair recording | 90 seconds at the relay, 30.000 video packets/second, maximum interval 34 ms, clean decode and continuous 48 kHz audio timestamps. |
| Original stack restored | Real rollback completed. Laptop recording passed for two minutes; independent relay-local recording passed for 75 seconds. |
| Return to release package | Completed with newer candidate operator settings preserved. Original containers and data retained. |
| Earlier laptop candidate recordings | One had a 141 ms video gap; another had gaps and damaged decoding. The relay logged a slow-reader discard of 830 frames during the latter capture. These remain failed recordings, not passing acceptance evidence. |
| Studio | Live, Music and System pages inspected. Read-only navigation did not change program or accepted music settings. Earlier connection-refused browser entries correspond to the deliberate cutover/rollback windows. |

Packet timing is not a substitute for listening or visual inspection. These bounded checks do not establish uninterrupted operation over a day.

## Long observation and remaining gates

`tools/soak_station.py` records bounded status, camera freshness, service identities, recovery history and resource measurements. It records independent decoded-source readiness separately from playout's camera state, which can be warming during scene preparation. It does not open another video decoder. It records probe failures and observation gaps, and does not assign itself an automatic pass verdict. Its JSON summary distinguishes an unfinished observation from a completed duration.

The repaired application checkpoint f9e68ab passed 550 Linux tests and 550 restricted-container tests in hosted run 39779892812, including actual Compose startup and the sustained-readiness/source-recovery exercise. A later host-observer-only addition distinguishes independent source health from native layer warmup; it does not change on-air rendering or decoding.

Run it with a new private output folder:

```sh
python3 tools/soak_station.py /path/to/station /path/to/new-observation --seconds 86400 --interval 30
```

Review the results against service restart history and recordings. A process launch or an early healthy sample does not complete the 24-hour gate.

At this historical checkpoint those gates were still open. The subsequent production observation, automatic reboot recovery and T480s standby checks are recorded in [the current checklist](RELEASE-CHECKLIST.md), which also carries the current clean-install and native source/distribution status. NDI and true UHD60 remain deferred. Subsequent headless work is tracked in the current checklist.

## Recovery records

Private host paths, exact image identities, migrated state archives and rollback scripts are held in the private station handoff and backup. The state archive excludes secret values and the music library; exact runtime images and private media are separate. Never replace newer operator settings with an old snapshot merely to roll back code. Preserve the AeroAPI ledger with its policy and reconcile any later usage before restoring it.
