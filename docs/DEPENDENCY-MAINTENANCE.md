# Dependency maintenance

The `0.1.0-alpha.1` candidate targets controlled graphics and operator-selected media on a trusted Linux workstation or private LAN. It is not a maintained browser distribution or a supported Internet-facing service. No stable branch is supported yet.

## Current exceptions

| Component | Current decision | Required follow-up |
|---|---|---|
| CEF / Chromium 142.0.7444.176 | Retained for CasparCG compatibility. Its age is a known security limitation; rendering tests do not establish current browser security. | Update the SDK and runtime together, rebuild the wrapper and engine, then repeat desktop/headless graphics, transitions, audio, receiver and reboot tests. Review upstream security changes before public stable support. |
| Dated OS package snapshots | Used to preserve exact binary/source correspondence. A snapshot is not an update service. | Review distribution security notices, advance the snapshot deliberately, rebuild both images and recollect exact matching sources. |
| Host kernel and GPU drivers | Supplied by the operator's Linux distribution. | Maintain them through the supported distribution and repeat output checks after changes. They are outside the container dependency inventory. |
| NDI | No proprietary runtime is included in the release bundle. | Treat any later installation as a separate licensed integration with its own security and maintenance review. |

CEF advises applications to stay current because Chromium vulnerabilities can also affect CEF built from the same Chromium version. Chromium publishes frequent security updates. The compatibility pin therefore remains an explicit exception, not a claim that network isolation fixes browser vulnerabilities. See [CEF security updates](https://github.com/chromiumembedded/cef#security-updates) and [Chromium update guidance](https://chromium.googlesource.com/chromium/src/+/main/docs/security/updates.md).

## Release review

Before promoting a candidate:

1. Record the source revision, base image digests, SDK/runtime identities and installed package inventories for the exact images.
2. Check Python and JavaScript dependency advisories and the applicable distribution, CEF/Chromium, FFmpeg and MediaMTX security notices. Record the check date and scope. A successful Python audit does not clear native code or host drivers.
3. For a finding, record the affected component/version, advisory, input path, mitigation, upgrade decision and acceptance test. If impact cannot be established, mark it unresolved rather than dismissing it.
4. Rebuild from locked inputs in an isolated environment. Keep matching source archives, build recipes and upstream notices with the images.
5. Test with providers disabled and synthetic inputs first. Then qualify the intended GPU workload on standby, including picture/audio at an independent receiver. Keep the previous image pair and settings checkpoint available for rollback.
6. Publish the supported versions, unresolved exceptions and required operator actions with the release. Do not advertise a security-maintenance commitment that the project cannot provide.

A critical issue affecting the supported use should pause promotion until mitigation is verified. Operators should disable an affected adapter, source or template when a safe update is unavailable. Do not silently widen the supported exposure to accommodate remote control.

## Reporting activation

The public source alpha directs reports to the private GitHub security-advisory form linked in [the security policy](../SECURITY.md). Publication checks verify the repository setting. An independent non-administrator submission and actual maintainer notification delivery have not been exercised. Do not publish a dummy vulnerability to test notifications.

GitHub's reporting form is available for public repositories. Preparing its configuration in a private repository does not prove that the form works. See [GitHub's reporting configuration](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).
