# Giojo.js — Source Map

Initial analysis of the Dojo Toolkit 1.1.2 source code adopted as Giojo.js.

## Overview

- **3 libraries**, **2140 files**, **~17MB** of source code
- Original version: Dojo Toolkit v1.1.2 (2008)
- Module system: `dojo.require()` / `dojo.provide()` (pre-AMD, pre-ES modules)

---

## src/dojo/ (172 files) — Core Foundation

Base JavaScript library: utilities, DOM, events, animations, data binding.

### Key modules

| Module | Files | Purpose |
|--------|-------|---------|
| `_base/` | 22 | Core: lang, declare, connect, Deferred, array, query, event, xhr, NodeList, fx, html, json |
| `cldr/` | 56 | Internationalization data (locale, plurals, currencies) |
| `nls/` | 24 | Localization strings (20+ languages) |
| `dnd/` | 11 | Drag & Drop |
| `data/` | 10 | Data store abstraction (Read, Write, Identity, Notification APIs) |
| `resources/` | 13 | CSS, images, static assets |
| `date/` | 2 | Date utilities (locale, ISO 8601) |
| `io/` | 2 | I/O utilities (script, iframe) |
| `rpc/` | 3 | RPC frameworks |
| `_firebug/` | 7 | Firebug console debugger integration |

### Standalone utilities
`number.js`, `colors.js`, `currency.js`, `string.js`, `parser.js`, `regexp.js`, `cookie.js`, `i18n.js`, `back.js`, `behavior.js`

---

## src/dijit/ (863 files) — UI Widgets

Complete UI widget library for building rich web applications.

### Key modules

| Module | Files | Purpose |
|--------|-------|---------|
| `themes/` | 490 | CSS themes: soria, nihilo, tundra, a11y, RTL variants |
| `form/` | 103 | Form widgets: Button, CheckBox, TextBox, Select, ComboBox, DatePicker, Spinner, Slider, etc. |
| `nls/` | 87 | Localized UI strings (20+ languages) |
| `_editor/` | 83 | Rich text editor with plugin system |
| `layout/` | 13 | Layout containers: BorderContainer, TabContainer, StackContainer, AccordionContainer, ContentPane |
| `templates/` | 10 | HTML templates (dojoAttachPoint pattern) |
| `_base/` | 10 | Base mixins: _Widget, _Templated, _Container, focus, place, popup, wai |
| `_tree/` | 6 | Tree data model and DnD |
| `demos/` | 31 | Demo/test files |

### Standalone widgets
`Dialog.js`, `Menu.js`, `Tree.js`, `Tooltip.js`, `ColorPalette.js`, `ProgressBar.js`, `TitlePane.js`, `Toolbar.js`, `InlineEditBox.js`, `Editor.js`

### Note
**490 files (57%) are CSS themes** — major candidate for cleanup/consolidation.

---

## src/dojox/ (1104 files) — Extended / Experimental

Advanced and experimental components. Many are likely unused by GenroPy.

### Key modules (likely used by GenroPy)

| Module | Files | Purpose |
|--------|-------|---------|
| `grid/` | 89 | Advanced data grid with virtualization |
| `charting/` | 59 | Chart/graph library (2D, 3D) |
| `gfx/` | 80 | Graphics library (SVG, Canvas, Silverlight renderers) |
| `layout/` | 46 | Advanced layout widgets |
| `data/` | 106 | Extended data stores (Csv, Html, Xml, Opml, etc.) |
| `form/` | 15 | Form extensions |
| `fx/` | 36 | Advanced animations/effects |
| `widget/` | 102 | Miscellaneous advanced widgets |

### Modules likely unused (legacy/obsolete)

| Module | Files | Purpose |
|--------|-------|---------|
| `flash/` | 9 | Flash integration |
| `av/` | 9 | Audio/video (Flash-based) |
| `storage/` | 19 | Storage providers (Flash, WHATWG, Google Gears) |
| `off/` | 18 | Offline support (Google Gears) |
| `sketch/` | 20 | Drawing/sketching widget |
| `presentation/` | 12 | Presentation/slideshow framework |
| `_sql/` | 4 | SQL support (Google Gears) |
| `cometd/` | 4 | Comet/Bayeux protocol |
| `gfx3d/` | 23 | 3D graphics |
| `highlight/` | 51 | Syntax highlighting |

### Utility modules

| Module | Files | Purpose |
|--------|-------|---------|
| `encoding/` | 35 | Crypto/encoding (base64, SHA, MD5) |
| `string/` | 13 | String utilities |
| `collections/` | 19 | Data structures |
| `lang/` | 23 | Language extensions |
| `validate/` | 13 | Form validation |
| `dtl/` | 63 | Django Template Language port |
| `wire/` | 55 | Declarative wiring (MVC-like) |
| `rpc/` | 48 | RPC frameworks (JSON-RPC, AMF) |
| `image/` | 37 | Image widgets (Lightbox, Gallery, SlideShow) |
| `analytics/` | 13 | Analytics tracking |
| `color/` | 8 | Color utilities |
| `date/` | 6 | Date extensions |
| `uuid/` | 7 | UUID generation |
| `timing/` | 7 | Timing utilities |
| `jsonPath/` | 5 | JSONPath querying |
| `math/` | 4 | Math utilities |
| `xml/` | 2 | XML utilities |
| `crypto/` | 4 | Cryptography |
| `help/` | 4 | Help system |
| `io/` | 8 | I/O extensions |

---

## Recurring Patterns

| Pattern | Meaning |
|---------|---------|
| `nls/` directories | Localization (20-30 languages per library) |
| `themes/` in dijit | 5 CSS themes with RTL variants |
| `_base/` | Private implementation mixins |
| `templates/` | HTML templates using dojoAttachPoint |
| `resources/` | CSS, images, static assets |
| `tests/`, `demos/` | Test and example files |
| `*.compressed.js` | Minified build artifacts (should be removed from src) |

---

## Next Steps

- [ ] Identify which modules are actually used by GenroPy (cross-reference with `gnrjs/`)
- [ ] Remove dead modules (Flash, Gears, Silverlight, etc.)
- [ ] Remove build artifacts (`.compressed.js`) from source tree
- [ ] Consolidate CSS themes (keep only those used)
- [ ] Map GenroPy customizations vs original Dojo code
