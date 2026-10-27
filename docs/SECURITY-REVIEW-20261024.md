# Candidate security review, 24 October 2026

> Historical test record. Results apply to the revisions, hardware and workload stated below. For current support limits and remaining work, use the [release checklist](RELEASE-CHECKLIST.md).

Scope: Python/FastAPI controller, browser UI data presentation, configured providers, uploaded media, CAP alerts, file/import helpers, subprocess use and support diagnostics. This is a code review with focused adversarial checks and dependency auditing, not an independent penetration test or certification. Production remains on its accepted image until the candidate passes regression and deployment checks.

## Findings and repairs

| ID | Severity | Finding | Repair |
|---|---|---|---|
| SEC-101 | High | Pinned Pillow 12.0.0 has published advisories affecting image parsing and bundled codecs. | Update direct and hashed Linux dependencies to 13.0.0. Restrict uploaded images, radar, map tiles, references and history pictures to their supported formats before decoder selection. Re-audit the full pinned Python runtime. |
| SEC-102 | Medium | Small control APIs had no common body-size ceiling before JSON parsing. | ASGI limit of 2 MiB with a total read deadline; streamed media uses separate 16/100 MiB limits and an upload deadline. Reject invalid or duplicate length headers. |
| SEC-103 | Medium | Some provider limits were checked only after HTTPX buffered the complete reply. | Limit decompressed streaming bytes before parsing ADS-B, weather, market, outage, tide and radar replies. Existing news, CAP and document streaming limits remain. |
| SEC-104 | Medium | A disabled alert adapter could restore authenticated messages from an earlier enabled session. | Explicit adapter enablement gates cache restore, ingest and presentation. Disabled outage adapters also ignore cached incidents. Defaults remain off. |
| SEC-105 | Medium | Uploaded MP4 inspection used an in-process decoder without a time bound. | Inspect H.264 metadata and three frames in subprocesses, with 12-second deadlines, single decoder/filter threads, bounded stdout/stderr spooling, local-only protocol allowlist and dimension/rate/duration limits. |
| SEC-106 | Medium | Errors could expose a subprocess command, credential-bearing URL or local path. | Shared public-error formatter replaces command details, endpoints, credential fields and private path prefixes. Validation responses omit submitted input and exception context. Existing support bundles remain allowlisted. |
| SEC-107 | Medium | Trusted-LAN controls had same-origin protection but accepted arbitrary Host names. | Reject unconfigured DNS Host values to resist browser DNS rebinding. Numeric private/loopback hosts, internal service names and explicitly configured names remain usable. Frame embedding is restricted to the same origin. |

A bare trusted-LAN client can operate the studio by design. The request header is a browser cross-origin safeguard, not authentication. Remote Internet-facing studio access remains unsupported; use the loopback default and SSH tunnelling.

## Existing controls reviewed

- Source imports validate hashes, manifests, member types and paths; upstream patch verification rejects unsafe archives and applies patches without fuzzy matching.
- Operator file IDs use constrained names. Secret files stay outside the source tree, have owner-only permissions on Linux and are not included in support bundles.
- Production containers are non-root, read-only where supported, drop capabilities and prohibit privilege escalation. The application never mounts the Docker socket. The offline Compose preview now has the same basic container restrictions and bounded logs.
- Shell-free argument lists are used for media operations. Camera probe/capture timeouts and PDF worker CPU/memory/time bounds were retained. Media operations still trust native codecs and the selected operator files.
- CAP input is bounded, rejects DTD/entities, and validates message identity and full-document authentication. Received URLs or certificates cannot install trust anchors. Independent issuer pinning is additional to DSS and requires operator-sourced trust material. No certified Alert Ready or universal delivery claim is made.
- Provider polling is opt-in. Preview mode denies outbound Python networking and write actions. Paid API accounting and file-backed keys are retained separately from the application.
- Reviewed dynamic studio labels and news use textContent; accepted news links require HTTPS. Static innerHTML scaffolding contains no fetched values. This is a focused review, not a claim that every third-party JavaScript line has been audited.

## Validation record

Focused request, media, disabled-alert/outage, redaction and bounded-HTTP tests were added. Existing failure-containment, source-import and support-export tests remain in the suite. One Windows full-suite run hit an intermittent file-replacement PermissionError in an unchanged history-retention test; its targeted repeat passed. Final Linux/container results belong in the current release checklist.

pip-audit 2.10.1 reported 74 advisory entries for the old Pillow pin, across one affected dependency. These entries can overlap and are not described as 74 independent exploitable defects. The updated complete Python lock reports no known vulnerabilities on 24 October 2026. That result covers that advisory database and those Python package versions only, not Ubuntu packages, CEF/Chromium, kernel/drivers or all embedded libraries.

Primary references: [Pillow release notes](https://pillow.readthedocs.io/en/stable/releasenotes/) and [upstream security advisories](https://github.com/python-pillow/Pillow/security/advisories). Retained before/after audit JSON is in the private acceptance evidence.

## Remaining boundaries

CEF 142 is pinned for the tested CasparCG build. It is not a supported general-purpose browser and this review does not call its dependency tree vulnerability-free. A browser/native-runtime update requires separate compatibility and output acceptance. Native source/notice retention is a distribution task, not security clearance.

No Internet authentication system, multi-tenant isolation, malicious media sandbox guarantee, regulatory alert certification or unsupported architecture qualification was added. Enable and verify GitHub private vulnerability reporting before public publication. See [SECURITY.md](../SECURITY.md) and the [single current checklist](RELEASE-CHECKLIST.md).
