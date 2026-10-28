# Jodit vendoring

This directory pins the Jodit release vendored at `resources/js_libs/jodit/`
and used by the `joditEditor` widget (`gnrjs/gnr_d11/js/genro_editors.js`).

Jodit ships a ready UMD build, so nothing is bundled here: `build.sh` copies
`es2021/jodit.min.js`, `es2021/jodit.min.css` and `LICENSE.txt` (MIT) from the
npm package and appends the Genropy CSS overrides to the stylesheet. The
HTML source view does not use Jodit's Ace integration: the widget plugs in the
CodeMirror 6 bundle vendored at `resources/js_libs/codemirror6/`.

## How to rebuild

You need a Node.js toolchain installed locally.

```bash
cd tools/jodit-build
./build.sh
```

## Updating Jodit

1. Bump the version in `package.json`.
2. Run `npm install` to refresh `package-lock.json`.
3. Run `./build.sh`.
4. Check the demo at `projects/gnrcore/packages/test/webpages/tools/jodit.py`,
   in particular the legacy markup and source view cases, and run
   `node --test gnrjs/tests/jodit_editor.test.js`.
5. Commit `package.json`, `package-lock.json` and `resources/js_libs/jodit/` together.
