# ProseMirror build pipeline

This folder produces the ProseMirror bundle vendored into Genropy at
`resources/js_libs/prosemirror/prosemirror.bundle.js`.

The bundle exposes `window.ProseMirror.*` with the core primitives used
by the Genropy `pane.proseMirror(...)` widget and by future widgets
(Milkdown, TipTap) that rely on the same engine.

## What's inside the bundle

State / model / view / transform primitives:

- `EditorState`, `Plugin`, `PluginKey`, `Transaction`, `Selection`,
  `TextSelection`, `NodeSelection`, `AllSelection`
- `EditorView`, `Decoration`, `DecorationSet`
- `Schema`, `Node`, `Mark`, `Fragment`, `Slice`, `NodeRange`,
  `DOMParser`, `DOMSerializer`
- `Transform`, `Step`, `ReplaceStep`, `AddMarkStep`, `RemoveMarkStep`

Commands and keymaps:

- `baseKeymap`, `chainCommands`, `toggleMark`, `setBlockType`, `wrapIn`,
  `lift`, `joinUp`, `joinDown`, `selectAll`, `deleteSelection`, ...
- `keymap`
- `history`, `undo`, `redo`, history keymap (Mod-z, Mod-y / Mod-Shift-z)
- `inputRules`, `textblockTypeInputRule`, `wrappingInputRule`,
  `smartQuotes`, `emDash`, `ellipsis`
- `dropCursor`, `gapCursor`

Pre-built schemas and helpers:

- `schemas.basic` (paragraph, blockquote, heading 1-6, hr, code_block,
  text, image, hard_break + bold, italic, code, link)
- `schemas.list` (ordered_list, bullet_list, list_item) plus
  `addListNodes(...)` to compose lists into a custom schema
- `splitListItem`, `liftListItem`, `sinkListItem`

## Rebuild

```bash
cd tools/prosemirror-build
./build.sh
```

The script installs dependencies (uses `package-lock.json` if present,
otherwise `npm install`) and runs esbuild in IIFE mode to produce a
single self-contained file.

## Updating dependencies

Bump the versions in `package.json`, run `npm install` to regenerate
`package-lock.json`, then run `./build.sh` to produce a fresh bundle.
Commit the updated lockfile and the rebuilt bundle.
