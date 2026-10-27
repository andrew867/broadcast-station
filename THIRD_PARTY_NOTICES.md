# Third-party inventory

| Component | Evidence | Disposition |
|---|---|---|
| MediaMTX 1.21.2 | Dockerfile pins the upstream Linux archive SHA-256; installed notice at /usr/share/doc/mediamtx/LICENSE | MIT; unmodified private camera fan-out binary, source at https://github.com/bluenviron/mediamtx/tree/v1.21.2 |
| CasparCG 2.5.1 and local modifications | deploy/engine/LICENSE-CasparCG, 17 patches, public fork and STATION-PATCHES.md | GPL-3.0-or-later; source application, regression tests and full Linux compile pass; binary distribution review remains a later gate |
| CEF 142 / Chromium 142.0.7444.176 | Exact SDK LICENSE.txt, CREDITS.html, version header, wrapper sources and runtime identity retained by the engine build; full matching sources recorded in docs/NATIVE-DEPENDENCIES.md | CEF BSD-style licence and Chromium component licences; retain the complete credits and matching sources with binary distribution. |
| Ubuntu / Debian system libraries, FFmpeg and codecs | Exact binary/source package versions and installed copyright notices in image inventories; authenticated source archive manifests collected separately | Component-specific licences, including copyleft components; package metadata alone does not replace corresponding source delivery. |
| Strudel and Kabelsalat | skycam/assets/strudel-source/LICENSE, dependency source archive and package lock | AGPL-3.0-or-later; 83 archived files match locked npm packages; deterministic worker rebuild; application distributed under AGPL-3.0-or-later |
| fraction.js | fraction-LICENSE and notice within the dependency archive | MIT; original notice retained |
| FreePats Upright Piano KW | skycam/assets/piano-kw/readme.txt, cc0.txt, manifest.json | CC0-1.0; source provenance and sample hashes retained |
| Barlow Condensed and Source Sans 3 | skycam/static/fonts/*OFL.txt | OFL-1.1; three files match upstream Google Fonts; family mapping recorded |
| Leaflet | skycam/static/vendor/LEAFLET-LICENSE.txt | BSD-2-Clause; JS, CSS and notice match upstream 1.9.4 archive |
| Python and Node packages | Linux wheel locks, npm lock, examples/component-inventory.json | Exact selected versions and notice locations recorded; packages retain their own licences |
| Original demo patterns | samples/ and synthetic radar JPGs | AGPL-3.0-or-later; no camera photographs copied |

NDI proprietary runtime, operator music, private recordings, screenshots, tile caches, provider credentials and live settings are excluded. Provider permissions are not transferable through the application's licence. See LICENSING.md for original-code scope.

The preview image inventory records installed OS/Python versions and notice hashes. It is metadata evidence, not a complete file-level SBOM or a claim that all future binary distributions are cleared. Public container publication must include matching dependency source/notices and retain exact image digests. See docs/NATIVE-DEPENDENCIES.md for exact retained sources and docs/RELEASE-CHECKLIST.md for current build, hardware and publication gates.

Detailed music, engine, font and Leaflet comparison records are in examples/*-verification.json. See docs/BUILD-INPUTS.md for the tested build scope.
