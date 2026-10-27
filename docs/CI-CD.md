# Builds, checks and deployment

GitHub Actions builds and checks release candidates. It does not deploy to either live station. No station credentials, provider keys or publishing keys are required by these workflows.

## Application checks

`Release foundation` runs on pushes, pull requests and manual dispatch. It validates workflow syntax, manual links, embedded help sections, the published settings schema, dependency locks, music rebuild and source delivery; scans source and history for secrets; runs the Linux tests; builds the controller; exercises the offline preview, full-station controller mounts and synthetic camera recovery; and repeats the tests inside a restricted container.

The `preview-image-inventory` artifact contains the image inventory and identifier, test report, build logs and workflow validation log. Upload runs even after failure, so partial evidence is available. A partial artifact is not a passing build. Logs from a step that was never reached will not exist. GitHub also retains the ordinary job log.

## Native engine checks

`Native deployment candidate` runs on pushes and pull requests affecting native build inputs, the deployment files, the smoke-test helpers, Compose engine mounts, Docker context exclusions or packaged licences. A documentation-only change outside that set does not rebuild the engine. Manual dispatch can test any selected branch.

It builds the pinned engine and patch series, checks linkage and retained source/notices, then decodes a recording containing native video, visible HTML graphics and audio on an isolated software OpenGL display and through headless software EGL without X11. Both paths must render the HTML marker and non-silent audio. This establishes functional operation, not physical-GPU or real-time performance acceptance.

`native-image-inventory` retains the build log, inventory and smoke-test evidence, including partial results on failure. The separate CasparCG fork has its own compile checks; those do not replace this packaged-image test.

Both workflows cancel superseded runs of the same workflow, event and branch or pull request. A push does not cancel a manually requested image build. Bash pipeline failures remain failures even when output is copied into an artifact log. Workflow validation uses a checksum-pinned actionlint release; other Actions are pinned to commits.

## Running checks again

Use the repository's **Actions** page, select the workflow and choose **Run workflow**, then select the candidate branch. The workflow must exist on the default branch for GitHub to expose its manual-dispatch entry point. A new dispatch entry added only on a development branch becomes available after normal merge to the default branch. Existing runs can also be rerun directly.

For private hardware acceptance only, the native workflow offers `retain_private_image`. It saves the tested Docker image and a checksum for three days, and only when the repository is private. Ordinary evidence lasts 30 days. This is a private test handoff, not a public image release. Retain accepted evidence in the project backup before GitHub artifacts expire.

## Deployment and release boundary

1. Select a candidate revision whose application checks pass and whose native inputs have a matching passing engine build. Record the image identifiers and checksums.
2. Save current station settings and the working images. Keep private settings and keys outside the candidate source package.
3. Test the candidate on an isolated station or the standby with an independent publishing destination. Review picture, music, transitions, recovery and the supported hardware workload.
4. Promote through the documented migration process with the saved image and settings available for rollback. A successful CI run alone does not authorize automatic changes to an on-air station.
5. Before public binary distribution, complete the [release checklist](RELEASE-CHECKLIST.md), deliver matching sources and notices, and activate the public security reporting route.

There is deliberately no unattended production deployment or public container push in these workflows. The supported installation and migration steps are in [Linux deployment](LINUX-DEPLOYMENT.md) and [migration validation](MIGRATION-VALIDATION.md).
