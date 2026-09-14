// Rebundle a prepared Gramlot browser distribution into one module.
// Run with esbuild 0.28.2 installed in a working directory's node_modules.
import {createRequire} from 'node:module';
import {resolve, dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';
const require = createRequire(resolve('package.json'));
const {build} = require('esbuild');
const distribution = resolve(process.argv[2]);
const output = dirname(fileURLToPath(import.meta.url));
const manifest = JSON.parse(readFileSync(join(distribution, 'manifest.json')));
await build({
    entryPoints: [join(distribution, manifest.entryPoints['gramlot-page-startup'])],
    outfile: join(output, 'gramlot.min.js'), bundle: true, splitting: false,
    format: 'esm', platform: 'browser', target: ['es2022'], minify: true,
    keepNames: true, legalComments: 'inline',
    banner: {js: readFileSync(join(output, 'minigenro.js'), 'utf8')},
    plugins: [{name: 'distribution', setup(builder) {
        builder.onResolve({filter: /.*/}, args => manifest.entryPoints[args.path]
            ? {path: join(distribution, manifest.entryPoints[args.path])} : null);
    }}],
});
