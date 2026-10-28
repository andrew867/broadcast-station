# Security policy

This alpha is for a single operator on a trusted workstation or private LAN. The studio has no multi-user authentication. The Director remote uses a separate key and private-address check, but remains limited to a trusted private LAN. Internet-facing deployment, shared hosting and untrusted tenants are unsupported. Keep the default loopback binding and use an SSH tunnel for remote operation. Do not expose AMCP, Docker or source-hub ports publicly.

## Report a vulnerability

Report vulnerabilities privately using [GitHub security advisories](https://github.com/andrew867/broadcast-station/security/advisories/new). The maintainer is [@andrew867](https://github.com/andrew867). Do not place credentials, private footage, station backups or exploit details in a public issue.

Include the affected revision/image, expected and observed behavior, a minimal reproduction using synthetic inputs, impact and suggested mitigation. Use the allowlisted support report rather than raw logs. Do not test a finding against someone else's live station. The maintainer will agree on disclosure timing with the reporter; no response SLA is promised.

## Supported versions and boundaries

Only the current alpha is under development. There is no stable security-maintenance branch or automatic update mechanism. Retain known working images and settings, test updates separately, and review the current release checklist before promotion.

The controller and native engine process media from configured sources. Source URLs, uploaded media and local templates must be operator-selected. Containers run without privileges or the Docker socket, but media codecs and CEF are substantial native attack surfaces. The pinned CEF 142 runtime must not be used as a general-purpose browser. A successful vulnerability scan is not proof that all native components are safe.

Providers default to disabled; previews cannot contact feeds or take the program. Alert presentation is not a certified public-warning receiver. Disabled alert and outage adapters do not restore saved incidents for presentation. Authentication of alert messages does not establish universal coverage or regulatory compliance.

The [dependency maintenance policy](docs/DEPENDENCY-MAINTENANCE.md) defines update review, the CEF compatibility exception and reporting activation. See also [the security review](docs/SECURITY-REVIEW-20261024.md) and [current release checklist](docs/RELEASE-CHECKLIST.md).
