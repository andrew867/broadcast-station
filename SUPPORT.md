# Support and release status

This is an experimental station project. The application is available as a public source alpha. Report reproducible problems through [GitHub issues](https://github.com/andrew867/broadcast-station/issues). There is no public stable release, support SLA or automatic update service. The existing NVIDIA station has production evidence; that does not qualify every Linux machine or workload. See [acceptance status](docs/ACCEPTANCE-STATUS.md) for tested revisions and unresolved gates.

For vulnerabilities, follow [the security reporting policy](SECURITY.md). Do not put exploit details or credentials in public issues.

## Report a problem

Include the source revision or image IDs, Linux distribution, GPU/driver, output profile, affected scene and approximate local time with timezone. Describe what you expected, what happened and whether HDMI, encoded output or both were affected. Include significant CPU, GPU, storage or network load during the failure.

Use `tools/support_bundle.py` for the allowlisted diagnostic report and review it before sharing. Send recordings only when you have permission to share their content. Do not post provider keys, stream keys, display cookies, full station settings, raw environment dumps or unreviewed logs. A support bundle is not a recovery backup.

## Changes and recovery

Keep a known working image and a separate settings backup before an update. Test on a separate station first when possible. Preserve newer operator edits and paid-API usage accounting during rollback. Do not run two controllers against one engine or two publishers against the on-air destination.

The project maintainer is @andrew867. Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md). Hardware-specific failures and source-provider outages may need operator access or evidence that the project cannot obtain remotely. No response time or perpetual provider compatibility is promised.
