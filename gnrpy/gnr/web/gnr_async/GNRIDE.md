# GnrIDE — Integrated Development Environment

Genro's built-in browser IDE for editing source code, debugging Python
with breakpoints, and previewing pages in real time.

## Overview

```
Browser: /sys/gnride/{page_id}
┌──────────────────────────────────────────────────────┐
│  ┌──────┐  ┌─────────────────────────────────┐       │
│  │ File │  │  Editor Stack (tabs)            │       │
│  │ Tree │  │  ┌─────────────────────────────┐│  ┌──┐ │
│  │      │  │  │ CodeMirror + breakpoint gutter││  │DB│ │
│  │ pkg1 │  │  │                             ││  │  │ │
│  │ pkg2 │  │  │     source code             ││  │  │ │
│  │ ...  │  │  │                             ││  │  │ │
│  │      │  │  └─────────────────────────────┘│  │  │ │
│  └──────┘  │  ┌─────────────────────────────┐│  └──┘ │
│            │  │ Debugger (when active)       ││       │
│            │  │ Stack │ Output │ Variables   ││       │
│            │  └─────────────────────────────┘│       │
│            └─────────────────────────────────┘       │
└──────────────────────────────────────────────────────┘
```

## Files

| File | Role |
|------|------|
| `resources/common/gnrcomponents/gnride/gnride.py` | Python component (BaseComponent) — layout, save, validation |
| `resources/common/gnrcomponents/gnride/gnride.js` | JS class `gnr.GnrIde` — editor, debug, WebSocket handlers |
| `resources/common/gnrcomponents/gnride/gnride.css` | CSS — **empty** (no custom styles) |
| `projects/gnrcore/packages/sys/webpages/gnride.py` | Web entry point `/sys/gnride` |
| `gnrjs/gnr_d11/js/genro_extra.js` | CodeMirror widget wrapper (`gnr.widgets.codemirror`) |
| `resources/js_libs/codemirror/` | CodeMirror 5 library (vendored) |

## Architecture

GnrIDE is a **BaseComponent** (`GnrIde` class in gnride.py) that can be
embedded in any Genro page. The main instance runs at `/sys/gnride`
(visible only to `_DEV_` users).

### Component structure

```python
class GnrIde(BaseComponent):
    css_requires = 'gnrcomponents/gnride/gnride'
    js_requires = 'gnrcomponents/gnride/gnride'
```

### Layout (gi_gnrIdeFrame)

```
BorderContainer (nodeId, _activeIDE=True, debugEnabled)
├── left: File browser tree (DirectoryResolver)
│   └── Packages + Genropy root, filtered *.py,*.js,*.xml,*.html
├── right: DB structure tree (drawer, closed by default)
└── center: StackContainer
    ├── toolbar: stack buttons + "Add IDE" button
    └── mainEditor tab
        └── gi_makeEditorStack('mainEditor')
```

### Editor tabs (gi_buildEditorTab)

Each opened file gets a tab with:

```
┌── Commandbar
│   ├── For webpages: Source | Mixed | Preview + Reload
│   └── For other files: Save + Revert
├── CodeMirror editor
│   └── config: python mode, line numbers, search addon,
│       softTab keymap (spaces not tabs), breakpoint gutter
└── Status bar: file path
```

The **Save** button has Shift-click "Save As" with filename prompt.
Source validation runs server-side before writing:

- **Python**: `compile()` — catches SyntaxError with line/offset
- **XML**: `Bag()` parse — catches parse errors

### Preview (webpages only)

For files in `*/webpages/*` or `*/mobile/*` (excluding `sys`/`adm`),
the editor shows a Source/Mixed/Preview mode selector and an iframe
with the page URL. The Mixed mode splits 50/50.

**Status**: Preview reload is partially implemented (TODO at gnride.py
line 195-198 — the `gnrIde_rebuildPage` window message is commented out).

## CodeMirror integration

### Current version

**CodeMirror 5** (legacy), vendored at `resources/js_libs/codemirror/`:

- `lib/codemirror.js` — 304 KB
- Modes: python, javascript, xml, htmlmixed, htmlembedded, css, sql, rst, stex
- Addons: search, dialog, lint, overlay
- Themes: available in `theme/` directory

### Widget wrapper

**File**: `gnrjs/gnr_d11/js/genro_extra.js` (line 753)

The `gnr.widgets.codemirror` class wraps CodeMirror as a Genro widget:

- Lazy-loads `codemirror.js` + CSS on first use
- Loads modes on demand (`load_mode`)
- Loads themes on demand (`load_theme`)
- Loads addons on demand (`load_addon`)
- Defines custom keymaps (`defineKeyMap` — e.g., `softTab`)
- Binds CodeMirror value changes to Genro's data system (with 500ms debounce)
- Exposes CM instance as `sourceNode.externalWidget`

### Custom extensions for debugging

Added in `gnride.js` `onCreatedEditorDo()` (line 143):

```javascript
cm.gnrMakeMarker(conditional)   // Creates breakpoint dot marker (● red/yellow)
cm.gnrSetCurrentLine(line)      // Highlights current debug line (4 CSS classes)
cm.on("gutterClick", ...)       // Toggle breakpoint on click, condition on Shift+click
```

CSS classes used (defined in gnrbase.css, not gnride.css):

- `pdb_breakpoint` — red dot marker
- `pdb_conditional_breakpoint` — yellow dot marker
- `pdb_currentLine_wrap/background/text/gutter` — debug current line highlight

## Debugger integration

The debugger is GnrIDE's most distinctive feature. Full architecture
documented in [REMOTE_DEBUGGER.md](REMOTE_DEBUGGER.md).

### WebSocket handlers

Registered in `start()` (gnride.js line 14):

```javascript
genro.wsk.addhandler('do_pdb_out_bag',  function(data){ that.onPdbAnswer_bag(data); });
genro.wsk.addhandler('do_pdb_out_line', function(data){ that.onPdbAnswer_line(data); });
genro.wsk.addhandler('do_close_debugger', function(pdb_id){ that.closeDebugger(pdb_id); });
```

### Debug data flow

```
Breakpoint hit (GnrPdb)
  → pdb_out_bag via WebSocket
    → onPdbAnswer_bag()
      → openModuleToEditorStack(module, debugged_page_id)
      → setDebugData(stack, locals, watches)
      → selectLine(lineno)
```

### Debugger pane layout (gi_debuggerPane)

```
┌── top: Toolbar
│   └── Step over | Step in | Step out | Continue | Clear console
├── left (250px): Stack viewer
│   └── Tree with call stack frames, click navigates levels
├── right (250px): Variables inspector
│   └── TreeGrid: locals, return value, watches
├── center: Console
│   ├── Output (pre-formatted, append-only)
│   └── Command input (>>> prompt)
│       └── Prefix '!' for expressions, '/' stripped, sent as PDB command
└── bottom: empty (placeholder)
```

### Debug commands

| Button | PDB command | Method |
|--------|-------------|--------|
| Step over | `next` | `do_stepOver()` |
| Step in | `step` | `do_stepIn()` |
| Step out | `return` | `do_stepOut()` |
| Continue | `c` | `do_continue()` |
| Jump | `jump {lineno}` | `do_jump(lineno)` |
| Level | `level {n}` | `do_level(level)` |

All sent via `genro.wsk.send("pdb_command", {cmd, pdb_id})`.

### Breakpoint management

**Client** (gnride.js line 168): Gutter click toggles breakpoint marker.
Shift+click opens a prompt for a condition.

**Server** (gnrpdb.py): `setBreakpoint()` stores in `connectionStore`
under `_pdb.breakpoints.{module_key}.r_{line}`. Breakpoints persist
across page refreshes (connection-scoped, not page-scoped).

## Opening GnrIDE

### From the menu

`/sys/gnride` — opens standalone IDE window.

### From a debugged page

**File**: `gnrjs/gnr_d11/js/genro_dev.js` (line 355)

```javascript
genro.dev.openGnrIde = function() {
    // Opens /sys/gnride/{current_page_id} in a new window
    // Sets genro.ext.startingModule to current page's module
}
```

When a breakpoint is hit, the debugged page shows a floating overlay
(genro_dev.js `onDebugstep()`) with "Debug" and "Continue" buttons.
"Debug" opens GnrIDE and navigates to the breakpoint.

### Embedded usage

GnrIDE can be embedded in other pages:

```python
bc.gnrIdeFrame(region='center', nodeId='podIDE',
               datapath='main.podIDE',
               sourceFolders='/home')
```

Used in `pod_dashboard.py` with a custom source folder.

## Known issues

### 1. Empty CSS file

`gnride.css` is completely empty. All debug-related CSS classes
(`pdb_breakpoint`, `pdb_currentLine_*`) are defined in `gnrbase.css`.
The IDE itself has no custom styling — everything uses Genro defaults.

### 2. Case mismatch in attribute name

The BorderContainer uses `_activeIDE` (uppercase) but the debugger
toolbar buttons reference `_activeIde` (lowercase). Works by accident
with Dojo's case-insensitive attribute lookup.

### 3. Preview reload incomplete

The preview iframe reload via `windowMessage` is commented out
(gnride.py lines 195-198). The "Reload preview" button only resets
the iframe URL with a cache-buster parameter.

### 4. Watches not implemented

The `watches` section appears in the variables inspector but
`GnrPdb.getWatches()` is not implemented — always returns empty.

### 5. Module cache removal

On save, `checkFile_py()` (line 273) removes the module from
`sys.modules` to force reload. This is a blunt approach that may
cause issues with circular imports or modules that have
initialization side effects.

---

## Editor assessment: CodeMirror 5 vs Monaco

GnrIDE currently uses **CodeMirror 5** (legacy, unmaintained since 2023).
The question is whether to upgrade to **CodeMirror 6** or switch to
**Monaco Editor** (VS Code's editor).

### Current CodeMirror 5 usage

**What GnrIDE uses from CodeMirror**:

1. Basic editing with syntax highlighting (Python, JS, XML)
2. Line numbers gutter
3. Custom gutter for breakpoint markers
4. Line class decoration (current debug line)
5. Search addon (Ctrl+F)
6. `softTab` custom keymap (spaces instead of tab)
7. `gutterClick` event for breakpoints
8. `getValue()`/`setValue()` for source code
9. `scrollIntoView()` for debug navigation
10. `markText()` for error highlighting

**What GnrIDE does NOT use**:

- Code completion / autocomplete
- Linting / diagnostics
- Multi-cursor editing
- Code folding
- Minimap
- Diff viewer
- Language Server Protocol
- Collaborative editing

### Licensing

| Version | License | Notes |
|---------|---------|-------|
| CodeMirror 5 (current) | MIT | `resources/js_libs/codemirror/lib/codemirror.js` header |
| CodeMirror 6 | MIT | Same author (Marijn Haverbeke). Social expectation to fund maintenance for commercial use, but no legal obligation |
| Monaco Editor | MIT | Microsoft, part of VS Code |

All three options are MIT-licensed. No licensing concerns for any path.

### Option A: CodeMirror 6

| Pro | Con |
|-----|-----|
| Natural evolution, same author (MIT) | Complete API rewrite — nothing portable from CM5 |
| Lightweight (~150 KB min) | New extension system to learn |
| Modular architecture | Smaller ecosystem than Monaco |
| Mobile-friendly | No built-in autocomplete (extension needed) |
| Fits Genro's lightweight approach | No minimap |
| Easy to embed in existing layout | Community smaller than Monaco's |

**Migration effort**: The `gnr.widgets.codemirror` wrapper in
`genro_extra.js` must be completely rewritten. The CM6 API is
fundamentally different (functional state model vs. imperative).
GnrIDE's breakpoint gutter and line decorations need new
implementations using CM6's `Decoration` and `gutter` extensions.

### Option B: Monaco Editor

| Pro | Con |
|-----|-----|
| VS Code's editor — proven, feature-rich | **Heavy**: ~2-4 MB (JS + CSS + workers) |
| Built-in autocomplete, IntelliSense | Requires Web Workers for syntax |
| Built-in diff viewer | Complex API, heavy integration |
| Minimap, code folding, multi-cursor | Not designed for embedding |
| TypeScript/JSON schema support built-in | Assumes full-page ownership |
| Huge community and documentation | Overkill for current GnrIDE usage |
| Active development by Microsoft | iframe-based embedding recommended |

**Migration effort**: The Genro widget wrapper must be completely
rewritten. Monaco assumes it owns the DOM container and doesn't
play well with Genro's dynamic source tree. The Web Worker
requirement adds complexity to Genro's resource loading system.
Monaco's AMD module system may conflict with Dojo's loader.

### Recommendation

**Stay with CodeMirror** — upgrade to **CodeMirror 6** when the IDE
is actively developed further.

**Rationale**:

1. **GnrIDE's primary value is the debugger, not the editor**.
   The integrated PDB debugging with breakpoints, stack navigation,
   and variable inspection is unique. The editor itself is secondary —
   developers write code in VS Code/PyCharm and use GnrIDE for
   debugging and quick fixes.

2. **GnrIDE uses <10% of CodeMirror's capabilities**. Switching to
   Monaco would bring 4 MB of code for features that won't be used.
   CodeMirror 6's modular approach lets you load only what you need.

3. **Monaco fights Genro's architecture**. Monaco wants to own the
   page, manage its own workers, and control the DOM. CodeMirror is
   designed to be embedded — it's a DOM element you place where you
   want. This matches Genro's source tree model perfectly.

4. **Dojo loader conflict**. Monaco uses AMD modules; Dojo has its
   own AMD loader (`dojo.require`). Making them coexist is fragile
   and error-prone. CodeMirror 6 is ESM-native or can be bundled
   as a single script.

5. **CodeMirror 5 works today**. The current version is stable and
   does everything GnrIDE needs. The upgrade to CM6 can be planned
   as a separate task when new features (autocomplete, linting)
   are desired.

**If code intelligence is needed later**, consider:
- CodeMirror 6 + `@codemirror/autocomplete` + custom Python completions
- Or: keep CodeMirror for editing, add a separate LSP panel via WebSocket
  to a `pyright`/`jedi` language server (similar to JupyterLab's approach)

### Migration path to CodeMirror 6

When ready to upgrade:

1. Bundle CM6 as a single JS file (using rollup/esbuild) into
   `resources/js_libs/codemirror6/codemirror.bundle.js`
2. Rewrite `gnr.widgets.codemirror` in `genro_extra.js` to use CM6 API
3. Port breakpoint gutter using CM6 `gutter()` extension
4. Port current-line highlight using CM6 `Decoration.line()`
5. Port `gutterClick` using CM6 `EditorView.domEventHandlers`
6. Port `markText` for errors using CM6 `Decoration.mark()`
7. Keep the `softTab` keymap using CM6 `keymap.of([...])`
8. Update `gnride.js` to use new CM6 API for `scrollIntoView`,
   `getValue`, `setValue`

**Estimated surface**: ~200 lines in `genro_extra.js` + ~50 lines in
`gnride.js`. The Python side (`gnride.py`) is config-driven and needs
minimal changes (attribute names in the `codemirror()` call).
