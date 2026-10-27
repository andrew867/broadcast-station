Strudel 1.2.6 arrangement worker, AGPL-3.0-or-later.

From this directory, using Node.js and npm:
  npm ci --ignore-scripts --no-audit --no-fund
  npm run verify
To deliberately regenerate ../strudel-arrange.mjs after editing arrange.mjs:
  npm run build

build.mjs fixes the working directory so absolute checkout paths do not change
the output. esbuild 0.25.12 and all dependencies are pinned by package-lock.json.
Only @strudel/core is used for scheduling. SuperDough and @strudel/webaudio are
not part of this runtime or build. This worker does not synthesize audio.

dependencies-source.tgz contains 83 unmodified files from @strudel/core 1.2.6,
fraction.js 5.3.4, @kabelsalat/core 0.4.0 and @kabelsalat/web 0.4.1, including
their source and licence notices. All 83 files matched npm ci byte for byte.
fraction.js is MIT; the other three packages declare AGPL-3.0-or-later.
The installed build tool esbuild is MIT and is fetched by npm ci, not included
as a binary in the release source. Keep its npm integrity lock.

From the repository root, verify the archive and installed package comparison:
  python tools/verify_music_source.py --installed skycam/assets/strudel-source/node_modules

The application and this integration are distributed under AGPL-3.0-or-later.
Dependencies retain the licences above. See LICENSING.md at the repository root
for component boundaries and docs/SOURCE-AND-LICENCES.md for source delivery.
