# Native dependency sources and build materials

The engine contains CasparCG, CEF/Chromium, FFmpeg and operating-system libraries. The controller, music worker and MediaMTX have separate dependencies. This inventory describes exact inputs and retained materials; it is not a universal licence clearance or a claim of bit-for-bit reproducibility.

## Engine identity

| Input | Exact identity and retained evidence |
|---|---|
| CasparCG | 2.5.1-stable, source SHA-256 `c2852873153569f5df3089dfc1aeb20e9ba62dae182436ad7691a79cce5baf78`; 17 patches in recipe order and regression helper. |
| CEF SDK | 142.0.17+g60aac24, Chromium 142.0.7444.176; archive SHA-256 `1d89e19b2f446105f9a1fe6fdc96bced86249b5884241dcc4013b7c94dabf424`. |
| CEF source | Commit `60aac241478a4495bc7fd7d56160d3e378e7decd`; source archive SHA-256 `e1d9bbaf4387858ea42bf4e56653ed4b06b1cfa34d42b4896f64c1324ed7d09b`. |
| Chromium source | 142.0.7444.176 official source archive; SHA-256 `4b479012600d5e9c1cd699ecd5ef1e7d4d21c3a5379f2ba816b803b18826a41a`. |
| Runtime libcef.so | SHA-256 `82ca737b46d113285f3c6590f04984f6c70773256c90553be81651cad7a81428` for the pinned upstream noble package; its embedded version is CEF 142.0.17, commit number 3316, Chromium 142.0.7444.176. It is a distinct binary build from the SDK. |
| Ubuntu libraries | Ubuntu 24.04 base digest and dated 20261020 package snapshot pinned in `deploy/Dockerfile.caspar-readback` and `deploy/ubuntu.sources`. Exact installed source-package identities come from the built-image inventory. |
| Original preload helpers | Sources, licence and binaries retained together in `/usr/lib/station`; their compile commands are in the engine recipe. |

## Inside the engine image

`/usr/share/station/caspar-source.tar.gz` contains patched CasparCG source and patches. `/usr/share/station/build/` retains the recipe and apt source configuration. `/usr/share/station/cef/` contains the exact SDK's LICENSE.txt, full Chromium CREDITS.html, README.txt, version header, wrapper/header/CMake source archive and a SHA-256 manifest. System package notices remain in `/usr/share/doc`. The retained Chromium credits contain 541 component entries, all with notice text. `examples/cef-credits-inventory.json` records their names, homepages and notice hashes without substituting guessed SPDX identifiers.

`tools/retain_cef_materials.py` accepts either the exact SDK library or the explicitly pinned upstream package library with the expected embedded version. It rejects unknown hashes and mismatched versions. The manifest records both hashes and whether they are identical; distinct binary builds remain identified separately. The first hosted acceptance build correctly exposed this distinction, and its failure is retained. `tools/native_inventory.py` records installed binary hashes, source identities and notice hashes. An inventory alone is not a corresponding-source archive.

## Obtaining matching sources

The pinned SDK comes from [CasparCG dependencies](https://github.com/CasparCG/dependencies/releases/download/cef/cef_binary_142.0.17+g60aac24+chromium-142.0.7444.176_linux64_minimal.tar.bz2). Full CEF source is at [the exact commit](https://github.com/chromiumembedded/cef/tree/60aac241478a4495bc7fd7d56160d3e378e7decd). Chromium source is the [official 142.0.7444.176 archive](https://commondatastorage.googleapis.com/chromium-browser-official/chromium-142.0.7444.176.tar.xz). The archive is about 7.6 GB compressed. Verify the hashes above after downloading.

The upstream CEF Debian packaging for version `142.0.17~g60aac24+2-noble1` is retained from [CasparCG PPA packaging revision 814d346](https://github.com/Julusian/CasparCG-ppa/tree/814d346a2432e09dfc5d3aefaf8ba0bb14a47607/noble/cef-142/debian), archive SHA-256 `12ed6f4228d419ea57620849e1a53f7e3c297091a382a31318b5e2f42f6d15e0`. Its changelog matches the package version. This is a version-matched packaging recipe, not an attestation of the original build environment.

For Ubuntu dependencies, run `tools/collect_os_sources.py native-inventory.json destination` inside a disposable Ubuntu build container with the matching dated `deb-src` repositories. It requests exact source versions through apt's authenticated metadata, retains `.dsc`, original and packaging archives, and records per-file hashes and failures in `source-manifest.json`. A complete manifest requires every requested source package. The two custom CasparCG packages are supplied separately by the CasparCG and CEF materials above.

Do not run source collection by changing a production host's apt configuration. Do not substitute the latest package sources for the installed versions. Preserve the source manifest alongside the image inventory and compare identities again if the image is rebuilt.

## Building and distribution

The supported engine build is `docker build -f deploy/Dockerfile.caspar-readback -t station-engine:candidate .`. It rebuilds patched CasparCG and the CEF C++ wrapper against the pinned SDK; it uses the upstream prebuilt libcef runtime. Rebuilding Chromium/CEF itself is a separate, much larger build using CEF's `automate/automate-git.py`, the exact CEF commit, matching Chromium checkout and its pinned DEPS. Consult the retained CEF checkout and SDK README for the matching branch's instructions. This project has not reproduced upstream's libcef binary bit for bit and does not claim to have its original complete compiler/environment attestation.

Before distributing the engine image, make the full matching source and notices available alongside it, including the OS source archives. Retaining them privately on a build host is not public source delivery. Confirm the intended distribution includes all required material and preserve upstream notices. Do not infer permission for camera feeds, proprietary NDI, paid data or operator music from a software licence.

The controller's exact Python packages are in the hashed Linux locks; Node/music sources and locks are included in the source download. MediaMTX 1.21.2 is MIT-licensed with upstream source and installed notice. Fonts, samples, Leaflet and other assets are listed in [third-party notices](../THIRD_PARTY_NOTICES.md). The application uses AGPL-3.0-or-later, independent tools Apache-2.0 and the CasparCG fork its existing GPL terms, as described in [licensing](../LICENSING.md).

## Security and scope

CEF 142 is a compatibility pin, not a claim of current browser security. It renders controlled station graphics and must not be used for general web browsing. Native-library modernization requires separate rendering/output tests. The inventory is not a complete transitive SBOM and a clean Python advisory scan does not clear Chromium, kernel, GPU drivers or system libraries.

## Completed acceptance

The fresh Ubuntu guest built native image `sha256:5a164704753d9781ab47254848f490bad3b4fc8822223df1be142b84713dc5d4`. Linkage, patched source, every expected notice/source file, CEF graphics, decoded video and non-silent audio passed. No NDI runtime was present. All 269 engine and 233 controller OS source identities match the retained per-package manifests. The upstream packaging fix also passed [hosted native acceptance](https://github.com/andrew867/station-release/actions/runs/40142394854). Private archive retention is complete for these identified inputs; public delivery remains a publication step.

Python 3.13.16 source is retained with SHA-256 `f4b1bfb3c79b5bb11b8d228a12504163b4c0dab4d679828d8f5f26b6cb6ab35d`, matching the digest-pinned Python image's declared source hash. The image inventory records its installed licence, MediaMTX licence and binary identity, Python package notices, FFmpeg and OS package source identities.
