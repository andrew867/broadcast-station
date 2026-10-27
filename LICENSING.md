# Licensing

The distribution contains components under the following licences.

* The original application, its UI, tests, example configuration, original demonstration artwork and documentation are AGPL-3.0-or-later. The root LICENSE contains that licence. This includes the application distributed with the Strudel integration.
* Independently authored utilities under tools/, the root Dockerfiles and .github/ build configuration are Apache-2.0, except where a file retains an explicit third-party licence. See LICENSES/Apache-2.0.txt.
* CasparCG-derived changes and native engine sources retain GPL-3.0-or-later and upstream notices. The fork is https://github.com/andrew867/casparcg-server, integration branch station/2.5.1. These files are not relicensed under Apache or AGPL.
* Strudel and Kabelsalat code retain AGPL-3.0-or-later. fraction.js retains MIT. The bundled dependency archive contains both; individual notices remain inside it.
* Barlow Condensed and Source Sans 3 retain OFL-1.1. Leaflet retains BSD-2-Clause. FreePats Upright Piano KW recordings retain CC0-1.0. Their notices and provenance are bundled.

This is a distribution containing multiple licences. Component licences do not grant permission to redistribute camera feeds, maps, news, financial data, alert material or music supplied by an operator. No proprietary NDI runtime is shipped.

The file inventory in examples/asset-provenance.json records each file's coverage and supporting notices. Package inventories record dependencies separately; licensing a requirements file does not relicense the packages it names. Exact upstream licence texts and notices take precedence over an inventory label.

See [source delivery](docs/SOURCE-AND-LICENCES.md) for modification and redistribution instructions. Public binaries must be accompanied by the applicable matching source and notices described in the [binary release checklist](docs/BINARY-RELEASE-CHECKLIST.md).
