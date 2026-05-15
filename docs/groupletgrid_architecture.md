# groupletGrid — architecture overview

## Purpose

`groupletGrid` renders a `Bag` as N **tiles**, where each tile is a sub-form
(a "grouplet") bound to one item of the data collection. One RPC at boot to
fetch the grouplet template, zero RPC for add/remove/edit/save — the
controller is fully reactive on `_trigger_data` subscriptions.

Use cases: forms with N variable sub-records (timesheets, invoice rows,
contacts list), kanban boards, tab-organised collections of records,
spreadsheet-like inline editing with formulas.

## File layout

- `resources/common/gnrcomponents/grouplet/grouplet.py` — Python side:
  `gr_groupletGrid` struct_method, RPC handlers (`gr_getGroupletGridTemplate`,
  `gr_groupletAddrowMenu`), `GroupletGridHandler` plug.
- `resources/common/gnrcomponents/grouplet/grouplet.css` — visual layer.
- `resources/common/gnrcomponents/grouplet/grouplet_grid.js` — JS classes:
  - `gnr.GroupletGridStructAdapter` — struct mode helper.
  - `gnr.GroupletGridController` — the widget brain.
  - `gnr.GroupletGridTile` — long-lived view manager per item.

## Vocabolario

- **item** — the data node in the storebag (one record of the collection).
  Genropy convention, aligned with `formStore.getItem`, `selectionStore.items`.
- **pkey** — unique identifier of an item.
- **tile** — the view manager for one item (`GroupletGridTile` instance).
  Owns the wrapper DOM + chrome + body. Neutral name across layouts:
  in `cards` mode the tile renders as a card, in `tabs` as a chip+panel,
  in `struct` as a row.
- **chrome** — decorations the widget adds around the body: drag handle,
  delete `×`, kebab `⋮`, counter cell. Defined by the controller kwargs.
- **body** — the data-entry content of the tile: deep-cloned copy of the
  grouplet template, with widgets bound to `^.field`.

## Classes

### `gnr.GroupletGridController`

The orchestrator. Instantiated by the bootstrap `dataController` in
`grouplet.py` on `_onBuilt`, after the container DOM exists.

Responsibilities:

- Reactive dispatcher (`gnr_storepath`): listens to storebag mutations
  and calls `_renderTile(pkey)` on `ins`, `_destroyTile(pkey)` on `del`.
- Tile registry (`this.tiles`): `Map<pkey, GroupletGridTile>` parallel to
  the storebag.
- Layout management: `cards`, `tabs`, `vtabs`. Tab strip lifecycle
  (`_addTabChip`, `_removeTabChip`, `_activateTab`).
- Template caching: one RPC at boot per resource key (default key is
  `__default__`; multi-grouplet mode caches one entry per resourceField
  value).
- DnD wiring: `_wireTileDnD` adds dragstart/dragend/dragover/drop on each
  tile's wrapper; payload uses a per-dragCode `application/x-gg-<code>`
  MIME so isolated grids don't accept foreign drops.
- Action bus: single topic `groupletGrid_<nodeId>_action` routes all
  mutations (`add` / `delete` / `move` / `activate`). Cross-grid kanban
  flows pass through this topic.
- Struct mode chrome sync: header/footer alignment to row widget
  geometry via `_syncStructChromeToColumns` + ResizeObserver.
- Public API: `addItem`, `insertItemAfter`, `insertItemBefore`,
  `deleteItem`, `selectTile`, `setLayout`, `setTotalizer`, `setFormula`.

### `gnr.GroupletGridTile`

One instance per pkey, long-lived, created in `_renderTile` and destroyed
in `_destroyTile`. Owns the wrapper DOM, the chrome, and the body of one
item.

Lifecycle:

- `mount(position)` — resolve template + decorations, create wrapper
  sourceNode at `position` in `bodyContent`, freeze + mount chrome +
  mount body + unfreeze. Atomic dijit construction.
- `rebuild()` — destroy body, re-resolve template, re-mount body.
  Wrapper sourceNode preserved (drag listeners survive). Used on
  resourceField change.
- `unmount()` — popNode the wrapper label from the body Bag; framework
  tears down the dijit subtree.

Model-side proxy (item access):

- `itemNode()` → the `BagNode` of the item in the storebag.
- `itemData()` → the inner Bag holding the field values. Same instance
  the body widgets read/write via `^.field`.

View-side accessors:

- `domNode()` → the wrapper DOM element.
- `flash()` → post-DnD highlight animation.

What the Tile does **not** own:

- Tile insertion position (controller knows the global tile registry).
- Tab chip lifecycle (chip lives in the controller's tab strip).
- DnD logic (wired by controller into the wrapper's `onCreated`).
- Struct chrome sync (controller-global).
- Pending state (`_pendingActivate`, `_pendingFlash`).

### `gnr.GroupletGridStructAdapter`

Stateless helper for `struct=` mode. Translates a `gnr.Grid`-style struct
Bag into:

- `cellmap` — field → metadata (dtype, edit, format), consumed by
  `GridChangeManager` for formulas / totalize.
- header / tile-template / footer sourceRoots.
- `--gg-struct-columns` CSS variable (shared `grid-template-columns`).

Mirrors gnr.Grid's dtype → editor widget mapping. Stateless: `applyStruct`
rebuilds it in place.

## Reactive flow

```
storebag mutation (add/remove/edit by anyone)
   │
   ▼
gnr_storepath trigger fires on the bound storebag
   │
   ▼
controller.gnr_storepath(value, kw, reason)
   │
   ├─ parent_lv < 0  → newDataStore (ancestor swap)
   ├─ parent_lv = 0  → newDataStore (whole-store replace)
   ├─ parent_lv = 1  → _renderTile(pkey) / _destroyTile(pkey)
   └─ parent_lv > 1  → intra-item field change; tab-label refresh only
```

`_renderTile(pkey)`:

```
const position = this._computeTilePosition(pkey);
const tile = new gnr.GroupletGridTile(this, pkey);
tile.mount(position);
this.tiles[pkey] = tile;
this._afterTileMounted(tile);  // tab chip, pending state, struct sync
```

## Modes summary

| Mode      | When                                     | Source                |
|-----------|------------------------------------------|-----------------------|
| `resource=` | Custom grouplet template                | `gr_getGroupletGridTemplate` RPC |
| `resourceField=` | Multi-grouplet, per-item template  | One RPC per key at boot         |
| `struct=` | gnr.Grid-style struct Bag                | `GroupletGridStructAdapter`     |
| `layout='cards'` (default) | Flow-grid of tile cards | controller orchestrates flow CSS |
| `layout='tabs'`  | Horizontal tab strip + panels | tab strip in `top` slot       |
| `layout='vtabs'` | Vertical tab strip            | tab strip in `left` slot      |

## Extension points

- `setTotalizer(field, datapath)` / `setFormula(field, expression)` —
  public API for adaptive totals (always available in struct mode,
  opt-in in resource mode).
- `setLayout('cards' | 'tabs' | 'vtabs')` — runtime swap, preserves
  edits + panels.
- Action bus subscribers — external listeners can hook
  `groupletGrid_<nodeId>_action` for add/delete/move/activate events.
- Drag isolation — `dragCode=nodeId` (default) isolates; explicit shared
  value enables cross-grid moves (kanban).

## Patterns of reference

- `gnr.TimesheetViewerController` (`resources/common/gnrcomponents/timesheet_viewer/timesheet_viewer.js`)
  — controller pattern + `dataController _onBuilt` bootstrap.
- `gnr.widgets.IncludedView.registerParameters` (`gnrjs/gnr_d11/js/genro_wdg.js:2181`)
  — `_trigger_data` + `getTriggerReason` reactivity.
- `gnr.RowEditor` (`gnrjs/gnr_d11/js/genro_wdg.js:658`) — long-lived
  per-record state, attribute-based dirty tracking (`_loadedValue`,
  `_validationError`, `_newrecord`). Will inform the future pseudoForm
  microform layer on the Tile class.

## Related design docs

- `docs/groupletgrid_store_integration.html` — design of the future
  `GroupletDataStore` class, three modes (internal / proxy / adapter).
