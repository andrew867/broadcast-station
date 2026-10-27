# Native binary release evidence

The application source and CasparCG patch fork are public. No prebuilt native engine image is included in the source alpha. Installed notices and a successful build do not by themselves close the binary distribution review.

## Inventory the exact image

Run the inventory inside the trusted built image, without starting the engine:

```sh
docker image inspect station-engine:candidate --format '{{.Id}}'
docker run --rm -i --network none --read-only --entrypoint python3 \
  station-engine:candidate - < tools/native_inventory.py > native-inventory.json
```

The report hashes the native executable, CEF library, patched source archive, build recipe, helper source/binaries and expected notices. It records installed Debian package versions, source package names/versions and copyright-file hashes. It also checks common locations for a proprietary NDI runtime. It does not mount a station directory or need a GPU/display.

## Items required before publishing an image

- Match the executable and helper binaries to a reproducible build record and the corresponding source archive. Preserve the exact image digest, base digests, downloads and patch order.
- Review the full CEF/Chromium component and notice set. The CEF package's short wrapper copyright file is not evidence that every bundled Chromium dependency has been reviewed.
- Map installed dependency binaries to their source packages and retain the source/build material required for the chosen distribution. Package names and copyright hashes are an inventory, not the source payload itself.
- Resolve missing expected notice/source files and undocumented libraries. Keep exception decisions explicit and reviewed.
- Confirm that no proprietary NDI runtime, operator credentials, private camera pictures, programme recordings or paid-provider material entered the image or source archive.
- Test the supplied source/build instructions from a clean checkout and confirm that the source-download artifact matches the shipped application.
- Publish the support limits, tested hardware/profile matrix, restore instructions and known issues alongside any eventual release.

The native inventory tool makes these checks repeatable; it deliberately does not output a redistribution-approved flag. Current acceptance limits are listed in [acceptance status](ACCEPTANCE-STATUS.md).

## Current source retention

See [native dependencies](NATIVE-DEPENDENCIES.md) for the exact CEF SDK/runtime comparison, full Chromium credits, wrapper sources, CEF/Chromium source archive hashes and exact-version OS source collection. On 24 October, all 269 engine and 233 controller source packages were downloaded successfully, with per-file hashes. Their identities match the final clean-image inventories exactly. The clean native image has no missing expected source/notice files or NDI runtime, and visible CEF graphics/video/audio acceptance passed. Repeat the identity comparison whenever an image is rebuilt. Public delivery remains separate from private retention.
