# Release foundation acceptance, 21 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

The clean source/web-preview foundation is complete. This is not a complete
broadcast installer or public application release. Production has not been
restarted, reconfigured or migrated by this foundation pass.

## Delivered

- Separate neutral source candidate, original demonstration pictures, configurable visible branding, and no operator credentials/settings/media.
- Read-only offline preview, denied outbound Python sockets, no feed or playout startup, localhost Compose and non-root runtime.
- AGPL-3.0-or-later application, independent Apache-2.0 tools, GPL-3.0-or-later CasparCG patches, retained third-party notices and per-file provenance.
- Immutable corresponding-source download linked from studio and guide, including build files, locks, tests and music dependency source. Live data and Git metadata are excluded.
- Exact Linux wheel hashes, pinned image digests, dated Debian/Ubuntu repositories, checksummed native release downloads, and a native build without a hidden local base tag.
- Private application repository and public CasparCG fork with the 16 patches as separate reviewable commits. No upstream PR has been filed.

## Verified results

| Check | Result | Scope |
|---|---|---|
| Windows Python suite | 487 passed in 169.80 seconds | Isolated candidate, no production engine |
| Hosted Linux suite | 487 passed in 28.99 seconds | Fresh runner with FFmpeg/espeak-ng installed |
| Restricted Linux container suite | 487 passed in 40.06 seconds | Network none, one CPU, 2 GB RAM, read-only root, temporary data |
| Preview image | Build, offline startup, blocked writes and source/image comparison passed | No GPU, display or live outputs |
| Music source | 83 archived files match locked npm installation; worker rebuild matches | Three seeded schedule comparisons were unchanged in the earlier source review |
| Source and Git history | GitLeaks and project checks passed | No detected secrets; scanners are not an absolute guarantee |
| Fonts, Leaflet and piano | Upstream/source manifest comparisons pass | Notices and comparison records retained |
| CasparCG fork | Regression tests and full Linux compile pass | No new GPU/runtime/hardware acceptance claim |
| Browser preview | Neutral studio/reference preview visually reviewed, no console errors | Prior preview review; current source link additionally checked by container smoke |

Application validation:
https://github.com/andrew867/station-release/actions/runs/39633280458
at commit 6c38930. Subsequent documentation/inventory workflow changes do not
change application behavior; their own hosted results remain visible in the
repository's Actions history.

Fork validation:
https://github.com/andrew867/casparcg-server/actions/runs/39631899777
at commit eb6e5b59f7fd5dd5e87151f0db5abad36269e745.

The application repository https://github.com/andrew867/station-release is
private. The fork is public at
https://github.com/andrew867/casparcg-server/tree/station/2.5.1 . Its final
modified source matches the independently applied patch inventory.

## Inventory and distribution limits

The package and asset inventories are evidence, not a blanket legal opinion
or complete file-level SBOM. Hosted runs retain the installed preview-image
inventory and exact local image ID. No registry image is published. Native
CasparCG/CEF/Chromium image source/notices and exact binary inventory must be
completed with full-stack packaging before distributing engine images.

The foundation completion gate covers the reviewed source and offline web
preview. It does not close every broader release-roadmap item: production
provider configuration, remote authentication, resource hardening, binary
publication and hardware acceptance remain explicitly tracked. Branding is configurable independently of the package name.

## Subsequent work

See [current acceptance status](ACCEPTANCE-STATUS.md) for tranches 2 through 4. The following paragraph records the original order, not the current implementation status.

### Original sequence

Tranche 2 is versioned station configuration and a non-destructive import
rehearsal using copied settings. Tranche 3 adds the complete Linux/GPU stack;
tranche 4 redesigns the studio; later tranches cover production cutover,
T480s/iGPU testing and public alpha. Keep this candidate separate from the
running station and do not reseed it from the production tree.
