// Build in a fixed working directory so checkout paths cannot affect the bundle.
import {build} from 'esbuild';
import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const cwd = fileURLToPath(new URL('.', import.meta.url));
const target = new URL('../strudel-arrange.mjs', import.meta.url);
const result = await build({absWorkingDir:cwd, entryPoints:['arrange.mjs'],
  bundle:true, platform:'node', format:'esm', write:false, metafile:true});
const bytes = Buffer.from(result.outputFiles[0].contents);
if (process.argv.includes('--check')) {
  if (!bytes.equals(await readFile(target))) throw new Error('Bundled arrangement differs from its source rebuild');
} else await writeFile(target, bytes);
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),
  inputs:Object.keys(result.metafile.inputs), matched:process.argv.includes('--check')}));
