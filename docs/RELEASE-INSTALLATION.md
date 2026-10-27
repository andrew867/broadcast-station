# Install the versioned alpha bundle

This document describes the separately assembled native binary bundle used for maintainer acceptance. Those images are not assets of the public source alpha. Public users should begin with the [source release quick start](../README.md#try-the-desk) or [Linux source build](LINUX-DEPLOYMENT.md).

The `0.1.0-alpha.1` bundle is a private installation-test candidate for x86-64 Linux. It has not completed the final clean GPU installation test and is not a public stable release. Use the [release checklist](RELEASE-CHECKLIST.md) for current acceptance limits.

## Prerequisites

Install Python 3.11 or later, Docker Engine with Compose, and the host GPU driver as described in [Linux deployment](LINUX-DEPLOYMENT.md). The station user must be able to run Docker. NVIDIA also requires NVIDIA Container Toolkit. Intel requires a usable `/dev/dri/renderD128` device. Keep at least 10 GiB free for images, settings and runtime files; storing all corresponding source archives requires substantially more space.

The packaged images contain the application and engine dependencies. Loading them does not require a native build toolchain. The supplied default configuration uses generic assets, disables providers and does not publish a stream. It contains no station credentials or private camera configuration.

## Verify and load

Obtain the complete bundle through the maintainer's trusted release channel. Keep `release.json`, all listed assets and `verify_bundle.py` in the same directory. Check the manifest checksum against the value supplied through that trusted channel before running the verifier. Checksums detect changed bytes; a manifest downloaded from an untrusted source does not authenticate its publisher.

```sh
python3 verify_bundle.py /path/to/bundle
python3 verify_bundle.py /path/to/bundle --load-images
```

The verifier checks every listed file's size and SHA-256 digest. The second command loads the two images, checks their immutable image IDs and starts a short `/bin/true` probe in each image with no network, a read-only filesystem and no capabilities. It does not start station services, change Docker settings or replace operator configuration. This probe catches extraction failures that Docker can report while still returning a matching image ID.

The original frozen `0.1.0-alpha.1` verifier checked image IDs only. When testing that bundle, use the corrected verifier from the reviewed source checkout against the unchanged bundle. Keep the original manifest and assets intact. Its successful load message alone does not establish that Docker extracted usable container filesystems.

Extract the verified application archive into a new directory:

```sh
mkdir station-release-0.1.0-alpha.1
tar -xzf /path/to/bundle/station-source-0.1.0-alpha.1.tar.gz -C station-release-0.1.0-alpha.1
cd station-release-0.1.0-alpha.1/station-source
export STATION_CONTROLLER_IMAGE=station-controller:0.1.0-alpha.1
export STATION_ENGINE_IMAGE=station-engine:0.1.0-alpha.1
python3 tools/stationctl.py prepare "$HOME/station" --gpu intel
```

Use `--gpu nvidia` on an NVIDIA host. Keep the versioned image variables in the shell while performing the first check; the launcher saves them in the station's `compose.env`. Use `resume` with prebuilt images. `start` intentionally invokes a source build and is not the binary-bundle installation path.

## Configure and start

Review `$HOME/station/station.json`. For a first headless test, enable `output.playout`, set `output.headless` to true, and leave `output.hdmi`, `output.desktop_audio`, `output.publish` and all providers false. Use HD30/libx264 on the Intel standby profile. Keep the studio bound to loopback unless private LAN access is needed.

NVIDIA UHD30 is the production release baseline. Select `2160p3000` on the qualified NVIDIA hardware; selecting `2160p6000` does not establish sustained UHD60 support. The generic configuration remains conservative and must be reviewed for the intended host.

```sh
python3 tools/stationctl.py check "$HOME/station" --gpu intel
python3 tools/stationctl.py resume "$HOME/station" --gpu intel
```

Open `http://127.0.0.1:8765/studio` locally, or through an SSH tunnel. Select an information scene and confirm programme readiness. Configure a credential-free monitor destination or a local recording to verify decoded video and audio before adding live sources. See [hardware acceptance](HARDWARE-ACCEPTANCE.md) for the test record to retain.

Enable [headless boot startup](HEADLESS.md) only after the first output test passes. On a laptop, review the system lid policy as well as KDE's policy; a desktop preference may not apply when no desktop session exists. Do not disable battery protection to keep a station running.

For desktop HDMI and speaker monitoring, use the [desktop installation instructions](LINUX-DEPLOYMENT.md) and run the first check from the logged-in desktop. Do not mix desktop mounts with headless mode.

## Source materials and rollback

The bundle contains exact image inventories, build inputs, notices and corresponding source archives. `chromium-parts.json` lists the ordered pieces and final digest of the large Chromium source archive. After verifying each piece, concatenate them in listed order and verify the reconstructed archive against its recorded SHA-256. These files are for source availability and rebuilding; they are not required by a running station.

Keep the previous release directory, image IDs and a verified station-state checkpoint before an upgrade. Restore the previous image references and resume from its matching release directory if acceptance fails. Do not overwrite current settings with defaults or erase accounting history. Secrets and music libraries require their own protected backup.
