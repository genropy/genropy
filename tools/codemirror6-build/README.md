# CodeMirror 6 build pipeline

This directory builds the CodeMirror 6 bundle vendored at
`resources/js_libs/codemirror6/codemirror6.bundle.js`.

The bundle is produced with `esbuild` as a single IIFE that exposes
`window.CodeMirror6` (state, view, commands, search, language helpers,
seven languages and the One Dark theme).

## Why is this here?

CodeMirror 6 is distributed npm-only and consists of dozens of small packages
that share state via `prosemirror-style` peer-dependency rules. Bundling them
once in this repo means production Genropy installations need neither npm
nor a Node runtime: the result is a plain `.js` file like the legacy
CodeMirror 5 vendoring under `js_libs/codemirror/`.

## How to rebuild

You need a Node.js toolchain installed locally (any LTS, tested with Node 20).

```bash
cd tools/codemirror6-build
./build.sh
```

The script installs dependencies from `package-lock.json` (or
`package.json` on the first run), then runs `npm run build`, which invokes
`esbuild` against `entry.js`. Output lands in
`../../resources/js_libs/codemirror6/`.

## Updating CodeMirror

1. Bump versions in `package.json`.
2. Run `npm install` to refresh `package-lock.json`.
3. Run `./build.sh`.
4. Smoke-test the demo at `projects/gnrcore/packages/test/webpages/tools/codemirror6.py`.
5. Commit `package.json`, `package-lock.json`, and the rebuilt
   `resources/js_libs/codemirror6/codemirror6.bundle.js` together.

## Files

- `package.json` — declares CodeMirror 6 packages and esbuild
- `package-lock.json` — exact resolved versions for reproducible builds (committed)
- `entry.js` — bundle entry point: imports CM6 modules and exposes them on `window.CodeMirror6`
- `build.sh` — one-shot wrapper around `npm install && npm run build`
- `.gitignore` — excludes `node_modules/`
