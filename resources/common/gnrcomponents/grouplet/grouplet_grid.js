// ============================================================================
//  groupletGrid — controller + struct adapter
//
//  Loaded by `GroupletGridHandler` (grouplet.py:626) via `js_requires`.
//  Defines two classes on `gnr.*`:
//
//    - `gnr.GroupletGridStructAdapter`  (struct= mode helper)
//        Pure converter from a `gnr.Grid`-style struct Bag to:
//          • cellmap (for the changeManager)
//          • header / row template / footer sourceRoots
//          • shared `grid-template-columns` value
//          • per-cell horizontal alignment
//        Stateless: `applyStruct` rebuilds it in place.
//
//    - `gnr.GroupletGridController`  (the widget brain)
//        Lifecycle, row rendering, store-driven dispatch via
//        `gnr_storepath`, layout swaps (cards/tabs/vtabs), DnD,
//        action API (add/delete), and the struct= chrome sync that
//        keeps header/footer aligned to the row widget geometry.
//
//  Bootstrap dataController in `grouplet.py` instantiates the
//  controller on `_onBuilt`, after the container DOM exists.
// ============================================================================


// ============================================================================
//  GroupletGridStructAdapter (Item 12)
//
//  Pure converter from a gnr.Grid-style struct Bag into the artefacts
//  the controller needs. Once `buildRowTemplate()` returns a sourceRoot
//  it's indistinguishable from the one `_bagToDetachedSource()` produces
//  for resource= mode — the controller treats them identically.
//
//  Mapping dtype → editor widget mirrors gnr.Grid (genro_wdg.js:1038-1051).
//  Widget tags are case-sensitive (`genro.wdg.getHandler` is a registry
//  lookup): PascalCase, with the legacy `DateTextbox`/`DatetimeTextbox`
//  (lowercase `b`) spelling preserved from Grid.
// ============================================================================

gnr.GroupletGridStructAdapter = class GroupletGridStructAdapter {
    constructor(struct) {
        this.struct = struct;
        this.cells = this._walkStruct();
        this.cellmap = this._buildCellmap();
    }

    rebuild(struct) {
        // Re-walk the struct after a mutation. Only caller is
        // `applyStruct(newStruct)`, which always passes a fresh struct.
        this.struct = struct;
        this.cells = this._walkStruct();
        this.cellmap = this._buildCellmap();
    }

    _walkStruct() {
        // If the struct is invalid `rows.getNodes()` throws — preferable
        // to silently rendering zero columns, which masks a real config bug.
        const rows = this.struct.getItem('view_0.rows_0');
        const out = [];
        rows.getNodes().forEach(function(node) {
            const attr = node.attr || {};
            if (attr.hidden) return;
            const field = attr.caption_field || attr.field;
            if (!field) return;
            // Header label: respect an explicit empty `name=''` as
            // "no label" (e.g. a checkbox column). Only fall back to
            // the field when `name` is undefined.
            const hasName = (attr.name !== undefined && attr.name !== null);
            // Totalize path resolution mirrors gnr.Grid
            // (genro_grid.js:1943): `totalize=True` → auto path
            // `.totalize.<field>` (a workspace path relative to the
            // grid's sourceNode, isolated from user data). Explicit
            // string from the user is honoured as-is.
            const totalize = (attr.totalize === true)
                ? '.totalize.' + field
                : attr.totalize;
            out.push({
                _nodelabel: node.label,
                field: field,
                name: hasName ? attr.name : field,
                width: attr.width,
                dtype: attr.dtype || 'T',
                edit: attr.edit,
                format: attr.format,
                totalize: totalize,
                totalize_strict: attr.totalize_strict,
                formula: attr.formula,
                related_table: attr.related_table,
                values: attr.values,
                validate_notnull: attr.validate_notnull
            });
        });
        return out;
    }

    _buildCellmap() {
        // Shape required by GridChangeManager (genro_wdg.js).
        // `_nodelabel` is the Bag node label, used by
        // calculateFormula:2160 to resolve `formula_*` dyn params.
        // `calculated: true` gates resolveCalculatedColumns
        // (genro_wdg.js:2021) so the initial recalc pass actually
        // fires for cells with `formula=` on seeded data.
        const cellmap = {};
        this.cells.forEach(function(c) {
            const entry = {
                field: c.field,
                dtype: c.dtype,
                _nodelabel: c._nodelabel,
                _formats: c.format ? {format: c.format} : null
            };
            if (c.totalize) entry.totalize = c.totalize;
            if (c.totalize_strict) entry.totalize_strict = c.totalize_strict;
            if (c.formula) {
                entry.formula = c.formula;
                entry.calculated = true;
            }
            cellmap[c.field] = entry;
        });
        return cellmap;
    }

    columnsCSS() {
        // Translate gnr.Grid widths into CSS Grid track functions.
        //   '100%' / '*' / missing → `minmax(0, 1fr)` (flex track)
        //   anything else (em / px / rem / %) passes through.
        //
        // A literal `'100%'` would be a CSS Grid track of "100% of the
        // content box": added to the other fixed tracks it overflows
        // the container, and the browser resolves the overflow with
        // subpixel-different rounding across header / row / footer
        // because their intrinsic content widths differ — visible
        // column drift. `minmax(0, 1fr)` is deterministic across the
        // three containers given identical available width.
        //
        // If no cell ends up flex after translation, auto-promote the
        // widest fixed-em cell. Without a flex track, fixed widths
        // either undershoot (grid centres, header labels disconnect
        // from data) or overshoot (overflow + per-container drift).
        const FLEX = 'minmax(0, 1fr)';
        const tracks = this.cells.map(function(c) {
            const w = c.width;
            return (!w || w === '*' || w === '100%') ? FLEX : w;
        });
        if (!tracks.some((t) => t === FLEX)) {
            let bestIdx = 0;
            let bestVal = -Infinity;
            tracks.forEach(function(t, i) {
                const v = parseFloat(t);
                if (!isNaN(v) && v > bestVal) {
                    bestVal = v;
                    bestIdx = i;
                }
            });
            tracks[bestIdx] = FLEX;
        }
        return tracks.join(' ');
    }

    hasTotalize() {
        return this.cells.some((c) => !!c.totalize);
    }

    buildHeader() {
        // Synthetic sourceRoot for the top slot — one cell per visible
        // struct column. Static labels go through `innerHTML` (the
        // second positional arg to `_()` is the node *label*, NOT the
        // visible content — passing the column name there would make
        // it the source-tree label and leave the DOM empty).
        //
        // Empty or whitespace-only labels are rendered as `&nbsp;` so
        // the cell keeps its line height (a bare space collapses in
        // some layout passes, breaking header/sibling vertical alignment).
        const root = genro.src.newRoot();
        const hdr = root._('div', {_class: 'grouplet_grid__struct_header'});
        const Adapter = gnr.GroupletGridStructAdapter;
        this.cells.forEach(function(c) {
            const align = Adapter._alignFor(c);
            const raw = c.name || '';
            hdr._('div', {
                _class: 'grouplet_grid__struct_col_cell'
                    + ' grouplet_grid__struct_header_cell'
                    + ' grouplet_grid__struct_cell--align-' + align,
                innerHTML: (raw.trim() === '') ? ' ' : raw
            });
        });
        return root;
    }

    buildFooter() {
        // Synthetic sourceRoot for the bottom slot — only emitted when
        // at least one column declares `totalize=`. Cells without
        // totalize render as empty placeholders so the grid template
        // stays aligned column-by-column.
        //
        // Totalize cells use `innerHTML='^totalize_path'`: the genropy
        // idiom for live-bound read-only display (gnrdomsource.js:577
        // applies `format` to the resolved value). `value='^...'` would
        // only end up as a static HTML attribute, leaving the cell
        // visually empty. The path resolution (auto `.totalize.<field>`
        // vs explicit user-supplied) happens in `_walkStruct`.
        if (!this.hasTotalize()) return null;
        const root = genro.src.newRoot();
        const ftr = root._('div', {_class: 'grouplet_grid__struct_footer'});
        const Adapter = gnr.GroupletGridStructAdapter;
        this.cells.forEach(function(c) {
            const cls = 'grouplet_grid__struct_col_cell'
                + ' grouplet_grid__struct_footer_cell'
                + ' grouplet_grid__struct_cell--align-' + Adapter._alignFor(c);
            if (!c.totalize) {
                ftr._('div', {_class: cls});
                return;
            }
            const kw = {_class: cls, innerHTML: '^' + c.totalize};
            if (c.format) kw.format = c.format;
            ftr._('div', kw);
        });
        return root;
    }

    buildRowTemplate() {
        // Synthesize a sourceRoot (gnr.GnrDomSource — same type the
        // resource= flow produces via _bagToDetachedSource) holding one
        // row element with widgets as DIRECT children (no per-cell
        // wrapper — mirrors the hand-written `shopping_row` baseline).
        // Editable cells get the widget mapped from dtype+edit (same
        // table gnr.Grid uses, genro_wdg.js:1038-1051); read-only cells
        // render as plain <div> with `^.field` innerHTML binding.
        const root = genro.src.newRoot();
        const row = root._('div', {_class: 'grouplet_grid__struct_row'});
        const Adapter = gnr.GroupletGridStructAdapter;
        this.cells.forEach(function(c) {
            const tag = Adapter._resolveWidgetTag(c);
            if (tag) {
                row._(tag, Adapter._editorKwargs(c));
                return;
            }
            // Readonly cells get the alignment class so numeric
            // readonly values line up with their header/footer
            // counterparts (NumberTextBox already right-aligns
            // internally; a plain <div> needs explicit styling).
            const kw = {
                _class: 'grouplet_grid__struct_col_cell'
                    + ' grouplet_grid__struct_row_cell'
                    + ' grouplet_grid__struct_cell--align-' + Adapter._alignFor(c),
                innerHTML: '^.' + c.field
            };
            if (c.format) kw.format = c.format;
            row._('div', kw);
        });
        return root;
    }

    static _alignFor(c) {
        // Derive horizontal alignment from dtype:
        //   numeric (L/I/R/N) → right  (matches NumberTextBox default)
        //   boolean (B)       → center (matches CheckBox)
        //   everything else   → left
        // Applied as a `--align-<right|center|left>` modifier class.
        switch (c.dtype) {
            case 'L': case 'I': case 'R': case 'N': return 'right';
            case 'B': return 'center';
            default: return 'left';
        }
    }

    static _resolveWidgetTag(c) {
        // Returns null when the cell is read-only (no `edit`).
        // Otherwise mirrors gnr.Grid editor resolution at
        // genro_wdg.js:1038-1051.
        if (!c.edit) return null;
        if (typeof c.edit === 'object' && c.edit.tag) return c.edit.tag;
        if (c.related_table) return 'dbselect';
        if (c.values) {
            return c.values.indexOf(':') >= 0 ? 'filteringselect' : 'combobox';
        }
        const map = {
            L: 'NumberTextBox', I: 'NumberTextBox',
            R: 'NumberTextBox', N: 'NumberTextBox',
            D: 'DateTextbox', DH: 'DatetimeTextbox',
            H: 'TimeTextBox', B: 'CheckBox'
        };
        return map[c.dtype] || 'Textbox';
    }

    static _editorKwargs(c) {
        // Compose the editor widget kwargs: defaults (value binding +
        // marker class) ← cell-level options (related_table, values,
        // format, validate_notnull) ← `edit=dict(...)` overrides.
        // `_class` is concatenated, not overwritten, so the marker
        // survives user customisation.
        const edit = (typeof c.edit === 'object' && c.edit) ? c.edit : {};
        const {tag, _class: editClass, ...editRest} = edit;
        const kw = {
            value: '^.' + c.field,
            width: '100%',
            ...(c.related_table && {table: c.related_table}),
            ...(c.values && {values: c.values}),
            ...(c.format && {format: c.format}),
            ...(c.validate_notnull && {validate_notnull: c.validate_notnull}),
            ...editRest,
            _class: 'grouplet_grid__struct_col_cell'
                + (editClass ? ' ' + editClass : '')
        };
        return kw;
    }
};


// ============================================================================
//  GroupletGridController
// ============================================================================

gnr.GroupletGridController = class GroupletGridController {

    // ====================================================================
    //  Lifecycle — constructor, destroy
    // ====================================================================

    constructor(sourceNode, kw) {
        this.sourceNode = sourceNode;
        // bodyNode is passed in as an already-resolved sourceNode
        // (looked up via the `_gg_body` attribute marker in the bootstrap
        // dataController). The phantom `+` add button is NOT passed in:
        // the controller builds it client-side via
        // `_buildLayoutAffordances` (which also handles the tabbar in
        // tabs mode). Stored as `this.addBtnDom` (raw DOM, not a sourceNode).
        this.bodyNode = kw.bodyNode || null;
        this.addBtnDom = null;
        this.tabbarDom = null;
        this.tabstripDom = null;
        this.nodeId = sourceNode.attr.nodeId;
        // Absolute datapath of the rows Bag — resolved once against the
        // container's datapath chain (`mixin_absStorepath` does the same
        // in genro_grid.js:3066-3068).
        this.storepath = sourceNode.absDatapath(sourceNode.attr.storepath);
        console.log('[groupletGrid] constructor', {
            nodeId: this.nodeId,
            rawStorepath: sourceNode.attr.storepath,
            absStorepath: this.storepath,
            initialBag: genro.getData(this.storepath)
        });
        this.resource = kw.resource || null;
        // Item 13: multi-grouplet mode — the row template is chosen per
        // row based on the value of `resourceField` on the row data
        // (e.g. `ticket_type='commercial/offer'`). When set, the
        // controller preloads ALL grouplets under the table's folder
        // in a single RPC at boot, keyed by their resource path.
        this.resourceField = kw.resourceField || null;
        // struct= mode (Item 12): the Python side parked the
        // GnrGridStruct Bag at `structpath` (relative to the
        // container — `#WORKSPACE.struct` auto, or user-supplied).
        // The controller pulls it back via `getRelativeData` and hands
        // it to `gnr.GroupletGridStructAdapter` which owns every
        // struct-specific concern: cellmap, row template synthesis,
        // header / footer sourceRoots, columnsCSS.
        this.structpath = kw.structpath || null;
        this.structAdapter = null;
        this.handler = kw.handler || null;
        this.table = kw.table || null;
        this.grouplets_root = kw.grouplets_root;
        this.grouplet_kw = kw.grouplet_kw || {};
        this.cols = kw.cols || 1;
        this.minWidth = kw.min_width || null;
        this.gap = kw.gap || '12px';
        // Action affordances (Item 10 API):
        //   additem  : bool — phantom '+' (rendered server-side as a
        //              lightButton in body/tabbar). The controller does
        //              not build it; only used to gate maxRows logic.
        //   delitem  : bool — top-right `×` close button on each row.
        //   editmenu : false | true | dict — per-row kebab:
        //              false → no kebab
        //              true  → {addPrev, addNext} (and `delete` only when
        //                      delitem is False)
        //              dict  → custom map {entryKey: label or {label, ...}}
        //   *_kw     : prefix-capture kwargs (e.g. additem_class via
        //              additem_kwargs.class) applied to the rendered DOM.
        this.additem = (kw.additem !== false);
        this.delitem = (kw.delitem === true);
        this.editmenu = (kw.editmenu === undefined) ? false : kw.editmenu;
        this.additemKw = kw.additem_kw || {};
        this.delitemKw = kw.delitem_kw || {};
        this.editmenuKw = kw.editmenu_kw || {};
        this.defaultRow = kw.defaultRow;
        this.minRows = kw.minRows || 0;
        this.maxRows = kw.maxRows || null;
        // `counterField`: when set, the controller maintains a 1-based
        // ordinal column on every row, renumbered after add / remove /
        // drag-and-drop. Mirrors `gnr.Grid.mixin_updateCounterColumn`
        // (genro_grid.js:3657). The field is written into the row Bag
        // as `^.<counterField>` — grouplets can bind to it normally.
        this.counterField = kw.counterField || null;
        // Drag-and-drop: when `dragCode` is non-null each row gets a
        // drag handle (left side). `dragCode` is the data-transfer key —
        // only payloads with the same key are accepted as drop sources,
        // so two grids with different `dragCode` values are isolated
        // (default: dragCode = nodeId, server-side). Cross-grid sharing
        // requires explicitly passing the same dragCode.
        this.dragCode = kw.dragCode || null;
        this._dragOverRow = null;
        this._dragHandlesByPkey = {};
        // Tabs mode (Item 11): `layout='tabs'` swaps the cards body for
        // a horizontal tab strip with one chip per row. The active tab
        // shows its panel (others get `display:none` — hidden panels
        // stay mounted, subscriptions intact). `setLayout()` flips
        // between modes at runtime.
        this.layout = kw.layout || 'cards';
        this.titleField = kw.titleField || null;
        this.emptyTitle = kw.emptyTitle || _T('!!Untitled');
        this.activePkey = null;
        this._tabsByPkey = {};         // pkey -> chip DOM element
        this._pendingActivate = null; // pkey to auto-activate on next _renderTile
        // Row templates are cached per "key" — today always
        // `__default__` (single-template grid) but multi-grouplet
        // mode (Item 13 Parte A) will switch on a `resourceField`
        // value (e.g. ticket_type). `_renderTile` consults the row data
        // via `_templateKeyForItem` to pick the key.
        this.templateSources = {};      // key -> sourceRoot
        this.templateLoading = {};      // key -> [callback, ...]
        // Item 12 changeManager wiring: cellmap is populated by the
        // struct adapter (struct mode) or stays empty in resource mode
        // (user can populate via setTotalizer/setFormula).
        this.cellmap = {};
        this._changeMgr = null;
        this._cmNeedsBag = false;
        this.tiles = {};
        this._destroyed = false;
        // Single per-instance topic: every action (add, delete, ...) goes
        // through here. Menu items, footer button, programmatic API all
        // publish on this topic; the controller dispatches via _handleAction.
        this.actionTopic = 'groupletGrid_' + this.nodeId + '_action';
        this._applyResponsiveLayout();
        this._applySlotClasses();
        this._registerActionSubscription();
        this._wireContainerDnD();
        // Build the layout-specific affordances (phantom `+` button in
        // cards mode, full tabbar+`+` chip in tabs mode). Must run AFTER
        // the container DOM exists; `_onBuilt` of the bootstrap
        // dataController guarantees that.
        this._buildLayoutAffordances();
        // Instantiate changeManager BEFORE first render. In struct mode
        // this also resolves the struct adapter, mounts header/footer
        // into slot placeholders, and auto-registers totalize/formula
        // cells with the changeManager.
        this._initChangeManager();
        const that = this;
        dojo.connect(sourceNode, '_onDeleting', function() { that.destroy(); });
        // Initial render: the store-driven dispatch (`gnr_storepath`) is
        // wired by the bootstrap dataController in grouplet.py, but the
        // first build of the container does not produce a 'storepath'
        // trigger — seed the render once here. Subsequent mutations
        // flow through `gnr_storepath`; whole-store replacements call
        // `newDataStore` again from there.
        this.newDataStore();
        this._updateAddBtnState();
    }

    destroy() {
        if (this._destroyed) return;
        this._destroyed = true;
        this.sourceNode.unregisterSubscription(this.actionTopic);
        this._unwireContainerDnD();
        Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
        // Tear down the layout-specific scaffolding (tabbar / footer +
        // any surviving chip subscriptions). Safe regardless of layout.
        this._teardownLayoutAffordances();
        if (this._structResizeObserver) {
            this._structResizeObserver.disconnect();
            this._structResizeObserver = null;
        }
        this.templateSources = {};
        this.templateLoading = {};
    }

    // ====================================================================
    //  Data access — storebag, collectionStore, rowFromBagNode
    // ====================================================================

    storebag() {
        // Fresh lookup of the rows Bag on every call (no caching),
        // mirroring `gnrgrid.mixin_storebag` (genro_grid.js:3230-3236).
        return genro.getData(this.storepath);
    }

    _containerDom() {
        // Convenience accessor. `this.sourceNode` is set once in the
        // constructor and never nulled; `getDomNode` is guaranteed by
        // the framework on every sourceNode. Controller methods only
        // ever run after `_onBuilt`, so the DOM is always present.
        return this.sourceNode.getDomNode();
    }

    collectionStore() {
        // First-class store wrapper around the rows Bag — NOT an alias
        // of storebag(). `GridChangeManager.calculateFormula` calls
        // `collectionStore().updateRowNode(rowNode, updDict)` which is
        // a Grid-store method (genro_components.js:7169), NOT a GnrBag
        // method. We provide the minimal store-shaped surface here:
        //   - updateRowNode(rowNode, updDict): writes each k→v into
        //     the row's sub-Bag with lazySet (mirrors :7178).
        //   - sum(field): delegates to Bag's native sum.
        //   - getIdxFromPkey(pkey), rowByIndex(idx): used by `+=`/`%=`
        //     cumulative formulas (future).
        const bag = this.storebag();
        if (!bag) return null;
        return {
            _bag: bag,
            updateRowNode: function(rowNode, updDict) {
                const rowData = rowNode.getValue();
                if (!(rowData instanceof gnr.GnrBag)) return;
                const idx = bag.index ? bag.index(rowNode.label) : null;
                for (const k in updDict) {
                    if (!rowData.getNode(k, 'static')) {
                        rowData.setItem(k, null, null, {doTrigger: false});
                    }
                    rowData.setItem(k, updDict[k], null,
                        {doTrigger: {editedRowIndex: idx}, lazySet: true});
                }
            },
            sum: function(field, strict) {
                return bag.sum(field, strict);
            },
            getIdxFromPkey: function(pkey) {
                return bag.index ? bag.index(pkey) : null;
            },
            rowByIndex: function(idx) {
                const nodes = bag.getNodes();
                const n = nodes[idx];
                if (!n) return null;
                const v = n.getValue();
                return v instanceof gnr.GnrBag ? v.asDict() : {};
            }
        };
    }

    rowFromBagNode(rowNode, _includeAttrs) {
        // Flatten a row Bag node into a plain object the changeManager
        // can read. Matches the contract of `gnr.Grid.rowFromBagNode`
        // (genro_wdg.js used in calculateFormula:2135).
        //
        // In our world the row's data lives in its sub-Bag (the value),
        // not in attrs — `setItem(pkey, Bag(dict(qty=..., price=...)))`
        // is the canonical seeding shape. The sub-Bag children are the
        // editable fields and we need them as plain keys so
        // `funcApply('return qty*unit_price', pars,...)` resolves names.
        const pars = {};
        const v = rowNode.getValue();
        if (v instanceof gnr.GnrBag) {
            v.getNodes().forEach((child) => {
                pars[child.label] = child.getValue();
            });
        }
        return objectUpdate(pars, rowNode.attr || {});
    }

    // ====================================================================
    //  Struct chrome (Item 12) — adapter wiring, header/footer mounting,
    //  cross-track alignment, public mutation API
    // ====================================================================

    _initStructAdapter() {
        // struct= mode: the Python side parked the struct Bag at
        // `this.structpath`, relative to the container. Path types like
        // `#WORKSPACE.struct` (auto-assigned) or explicit `.foo` resolve
        // against the container's datapath / workspace ancestor.
        // `getRelativeData` honours path types; `genro.getData`
        // (absolute) does not.
        if (!this.structpath) return;
        const struct = this.sourceNode.getRelativeData(this.structpath);
        if (!(struct instanceof gnr.GnrBag)) {
            console.warn('[GG] structpath did not resolve to a Bag',
                         this.structpath, struct);
            return;
        }
        this.structAdapter = new gnr.GroupletGridStructAdapter(struct);
        this.cellmap = this.structAdapter.cellmap;
    }

    _initChangeManager() {
        // Build the struct adapter (if struct mode), then instantiate
        // `gnr.GridChangeManager` directly on the controller. The
        // changeManager reads these attributes off `grid`:
        //   sourceNode, storebag(), cellmap, datamode, structBag,
        //   collectionStore(), rowFromBagNode(rowNode, true)
        // Optional (filtered totals): _virtual, isFiltered,
        //   getSelectedRowidx, getSelectedNodes
        // Optional (gridEditor codepath, always skipped here):
        //   gridEditor, getRowEditor, masterEditColumn,
        //   currRenderedRowIndex
        // We pass a small shim object as `grid`; `gridEditor` stays
        // undefined so the editor branches at genro_wdg.js:293,322,344
        // are auto-skipped.
        this._initStructAdapter();
        this.datamode = 'bag';
        this.structBag = this.structAdapter ? this.structAdapter.struct : null;
        this._virtual = false;
        this.isFiltered = function() { return false; };
        this.getSelectedRowidx = function() { return []; };
        this.getSelectedNodes = function() { return []; };
        // `sourceNode` for the changeManager MUST be the container, NOT
        // the body. The changeManager writes `.sum_*` totals via
        // `sourceNode.setRelativeData(cell.totalize, value)`. If the
        // sourceNode were the body — whose datapath equals `storepath`
        // (i.e. the rows Bag itself) — `setRelativeData('.sum_total',x)`
        // would write INTO the rows Bag, triggering the rowLogger that
        // the changeManager subscribed to → infinite triggerINS/UPD
        // loop. Anchoring on the container puts `.sum_total` one level
        // up, sibling to the rows Bag — same shape gnr.Grid uses.
        const cmGrid = {
            sourceNode: this.sourceNode,
            storebag: () => this.storebag(),
            collectionStore: () => this.collectionStore(),
            cellmap: this.cellmap,
            datamode: this.datamode,
            structBag: this.structBag,
            _virtual: this._virtual,
            isFiltered: this.isFiltered,
            getSelectedRowidx: this.getSelectedRowidx,
            getSelectedNodes: this.getSelectedNodes,
            rowFromBagNode: (n, _) => this.rowFromBagNode(n, _)
        };
        this._changeMgr = new gnr.GridChangeManager(cmGrid);
        // GridChangeManager subscribes to `onNewDatastore` and only
        // attaches `rowLogger` to the Bag from inside that callback —
        // calling `that.grid.storebag().subscribe(...)`. If we publish
        // `onNewDatastore` now and the Bag is null (resource= mode
        // starting empty, e.g. test_1), the callback NPEs. We publish
        // lazily from `newDataStore` once a real Bag is available.
        this._cmNeedsBag = true;
        // Adapter-driven auto-registration of totalize/formula cells.
        // Server-seeded rows go through a force-resolve so initial
        // values render without waiting for an edit.
        if (this.structAdapter) {
            this.structAdapter.cells.forEach((c) => {
                if (c.totalize) {
                    this._changeMgr.addTotalizer(c.field,
                        {totalize: c.totalize});
                }
                if (c.formula) {
                    this._changeMgr.addFormulaColumn(c.field,
                        {formula: c.formula});
                }
            });
            this._mountStructSlots();
            const store = this.storebag();
            if (store && store.len() > 0) {
                this._changeMgr.resolveCalculatedColumns();
                this._changeMgr.resolveTotalizeColumns();
            }
        }
    }

    _mountStructSlots() {
        // Set `--gg-struct-columns` on the container DOM, then mount
        // header (top slot) and footer (bottom slot, if any totalize).
        // Each side targets a server-side placeholder (childname=
        // 'struct_header' / 'struct_footer') that lives inside the
        // slot's sourceNode — leaf-empty, safe to freeze/unfreeze.
        if (!this.structAdapter) return;
        const containerDom = this._containerDom();
        containerDom.style.setProperty('--gg-struct-columns',
            this.structAdapter.columnsCSS());
        const slots = this._resolveStructSlots();
        if (slots.top) {
            this._mountSlotContent(slots.top,
                this.structAdapter.buildHeader(), 'struct_header');
            // Force `has-top` directly: the slot now carries struct
            // chrome, but `_applySlotClasses` reads from `slot.children`
            // which may not reflect the just-grafted nodes yet.
            containerDom.classList.add('has-top');
        }
        const footer = this.structAdapter.buildFooter();
        if (slots.bottom && footer) {
            this._mountSlotContent(slots.bottom, footer, 'struct_footer');
            containerDom.classList.add('has-bottom');
        }
        // Re-measure column alignment on container resize: em-based
        // padding scales with the container's font-size, and the
        // intrinsic width of widget cells changes with available space.
        if (!this._structResizeObserver
                && typeof ResizeObserver !== 'undefined') {
            this._structResizeObserver = new ResizeObserver(() => {
                this._scheduleStructSync();
            });
            this._structResizeObserver.observe(containerDom);
        }
    }

    _resolveStructSlots() {
        const out = {top: null, bottom: null};
        const containerContent = this.sourceNode.getValue();
        if (!(containerContent instanceof gnr.GnrDomSource)) return out;
        containerContent.getNodes().forEach((n) => {
            const side = n.attr && n.attr.gg_side;
            if (side === 'top') out.top = n;
            else if (side === 'bottom') out.bottom = n;
        });
        return out;
    }

    _mountSlotContent(slotNode, sourceRoot, placeholderLabel) {
        // Populate the empty placeholder sourceNode (emitted server-side
        // by gr_groupletGrid via `childname='struct_header'` /
        // `'struct_footer'` inside the corresponding slot) with the
        // cells produced by the adapter.
        //
        // The placeholder is a leaf <div>: built when the container was
        // built, but with no children. `freeze → graft → unfreeze` on a
        // leaf-empty sourceNode is the same pattern `_renderTile` uses for
        // the row wrapper. The framework treats the cells as fresh
        // inserts, not as updates of pre-existing DOM.
        //
        // Idempotent: prior cells are popped so a rebuild on struct
        // mutation (controller.applyStruct) doesn't duplicate.
        const slotContent = slotNode.getValue();
        if (!(slotContent instanceof gnr.GnrDomSource)) return;
        const placeholder = slotContent.getNode(placeholderLabel);
        if (!placeholder) return;
        const placeholderContent = placeholder.getValue();
        if (!(placeholderContent instanceof gnr.GnrDomSource)) return;
        placeholderContent.getNodes().slice().forEach((n) => {
            placeholderContent.popNode(n.label);
        });
        // The adapter sourceRoot has exactly one root child (the
        // wrapper div carrying class __struct_header / __struct_footer).
        // Discard that wrapper level since the placeholder IS that
        // wrapper — graft the wrapper's inner cells directly into the
        // placeholder instead.
        placeholder.freeze();
        sourceRoot.getNodes().forEach((tileNode) => {
            const inner = tileNode.getValue();
            if (inner instanceof gnr.GnrBag) {
                inner.getNodes().forEach((cellNode) => {
                    this._graftNode(placeholderContent, cellNode);
                });
            }
        });
        placeholder.unfreeze();
    }

    _scheduleStructSync() {
        // Coalesce multiple sync requests within a frame (resize +
        // row-add + applyStruct can all fire in the same tick). The
        // actual measurement happens once, in the next animation frame,
        // when layout is settled.
        if (this._structSyncScheduled) return;
        this._structSyncScheduled = true;
        const that = this;
        requestAnimationFrame(function() {
            that._structSyncScheduled = false;
            that._syncStructChromeToColumns();
        });
    }

    _syncStructChromeToColumns() {
        // Two-step alignment:
        //
        // STEP 1 — Frame: make the header and footer containers share
        //   the same horizontal CONTENT-BOX as the row inner grid. The
        //   row lives inside `.grouplet_grid_row` which has drag/kebab
        //   spacing; the header lives in slot top, full-width of the
        //   outer card. Even with identical `grid-template-columns`,
        //   the absolute X of every track differs because the two
        //   containers start at different X. Fix by stretching the
        //   header/footer padding so their content-box coincides with
        //   `firstRow`'s outer rect. After this, the three grids
        //   resolve identical track positions automatically.
        //
        // STEP 2 — Text edge inside each column: for each column, align
        //   the header label and the readonly row cell to the VISIBLE
        //   text edge of the row's widget input. Computed relative to
        //   the column wrapper's edge (intrinsic inset) PLUS the
        //   widget's own padding/border on that side. No cross-track
        //   measurement here — each column's adjustment is local.
        if (!this.structAdapter) return;
        const containerDom = this._containerDom();
        const firstRow = containerDom.querySelector(
            '.grouplet_grid_body .grouplet_grid__struct_row');
        if (!firstRow) return;
        // Single pass over all rows: stamp the col_cell marker class on
        // every direct child (some widgets — e.g. gnrcheckbox — wrap
        // themselves at parse time, so the marker class supplied to the
        // builder lands on an inner node and the actual row child is
        // the wrap the framework added), index readonly cells by column
        // for the padding pass below, AND capture the trackEls of
        // firstRow used to drive STEP 2's per-column alignment.
        const readonlyByColumn = [];
        const trackEls = [];
        const allRows = containerDom.querySelectorAll(
            '.grouplet_grid_body .grouplet_grid__struct_row');
        allRows.forEach(function(row) {
            const isFirst = (row === firstRow);
            Array.from(row.children).forEach(function(el, i) {
                el.classList.add('grouplet_grid__struct_col_cell');
                if (isFirst) trackEls.push(el);
                if (el.classList.contains('grouplet_grid__struct_row_cell')) {
                    if (!readonlyByColumn[i]) readonlyByColumn[i] = [];
                    readonlyByColumn[i].push(el);
                }
            });
        });
        // --- STEP 1: frame header/footer onto the row inner grid's
        // CONTENT-BOX (its bounding rect minus its own padding, because
        // the row's horizontal padding is what reserves space for the
        // absolute drag handle / kebab on the row wrapper above it).
        const rowOuter = firstRow.getBoundingClientRect();
        const rowCs = getComputedStyle(firstRow);
        const rowContentLeft  = rowOuter.left  + parseFloat(rowCs.paddingLeft);
        const rowContentRight = rowOuter.right - parseFloat(rowCs.paddingRight);
        const headerEl = containerDom.querySelector(
            '.grouplet_grid__struct_header');
        const footerEl = containerDom.querySelector(
            '.grouplet_grid__struct_footer');
        const frameToRow = function(el) {
            if (!el) return;
            el.style.paddingLeft = '';
            el.style.paddingRight = '';
            const elRect = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            const padL = parseFloat(cs.paddingLeft);
            const padR = parseFloat(cs.paddingRight);
            const wantPadL = padL + (rowContentLeft  - (elRect.left  + padL));
            const wantPadR = padR + ((elRect.right - padR) - rowContentRight);
            el.style.paddingLeft  = Math.max(0, wantPadL) + 'px';
            el.style.paddingRight = Math.max(0, wantPadR) + 'px';
        };
        frameToRow(headerEl);
        frameToRow(footerEl);
        // --- STEP 2: per-column text-edge alignment.
        // Position header and footer cells absolutely at the same X /
        // width as the row column wrappers. Header/footer are
        // `position:relative`; cells become `position:absolute` with
        // `left` + `width` cloned from the row's geometry. Result: the
        // cell is physically in the same horizontal slot as the row
        // widget, regardless of grid track resolution or font-size
        // scaling. Readonly cells (which DO live inside the row grid)
        // keep their natural grid placement — only their internal
        // padding is tuned to the widget text-edge.
        if (!trackEls.length) return;
        const headerCells = containerDom.querySelectorAll(
            '.grouplet_grid__struct_header > .grouplet_grid__struct_col_cell');
        const footerCells = containerDom.querySelectorAll(
            '.grouplet_grid__struct_footer > .grouplet_grid__struct_col_cell');
        const headerLeftRef = headerEl
            ? headerEl.getBoundingClientRect().left : 0;
        const footerLeftRef = footerEl
            ? footerEl.getBoundingClientRect().left : 0;
        const Adapter = gnr.GroupletGridStructAdapter;
        this.structAdapter.cells.forEach(function(c, i) {
            const trackEl = trackEls[i];
            if (!trackEl) return;
            const trackRect = trackEl.getBoundingClientRect();
            if (trackRect.width === 0) return;
            // Text-edge inset: gap between wrapper edge and visible text
            // inside the widget input (the input has its own
            // padding+border that pushes the text inward).
            let target = trackEl;
            let bestW = 0;
            trackEl.querySelectorAll('input, textarea').forEach(function(el) {
                const r = el.getBoundingClientRect();
                if (r.width > bestW) {
                    bestW = r.width;
                    target = el;
                }
            });
            const targetRect = target.getBoundingClientRect();
            let extraLeft = 0;
            let extraRight = 0;
            if (target !== trackEl) {
                const cs = getComputedStyle(target);
                extraLeft  = parseFloat(cs.paddingLeft)  + parseFloat(cs.borderLeftWidth);
                extraRight = parseFloat(cs.paddingRight) + parseFloat(cs.borderRightWidth);
            }
            const leftInset  = Math.max(0,
                (targetRect.left - trackRect.left) + extraLeft);
            const rightInset = Math.max(0,
                (trackRect.right - targetRect.right) + extraRight);
            const align = Adapter._alignFor(c);
            let justify;
            if (align === 'right') justify = 'flex-end';
            else if (align === 'center') justify = 'center';
            else justify = 'flex-start';
            const placeAbsolute = function(el, parentLeft) {
                if (!el) return;
                el.style.position = 'absolute';
                el.style.top = '0';
                el.style.bottom = '0';
                el.style.left = (trackRect.left - parentLeft) + 'px';
                el.style.width = trackRect.width + 'px';
                el.style.boxSizing = 'border-box';
                el.style.display = 'flex';
                el.style.alignItems = 'center';
                el.style.justifyContent = justify;
                el.style.paddingLeft = (align === 'left'  ? leftInset  : 0) + 'px';
                el.style.paddingRight = (align === 'right' ? rightInset : 0) + 'px';
            };
            placeAbsolute(headerCells[i], headerLeftRef);
            placeAbsolute(footerCells[i], footerLeftRef);
            // Readonly row cells stay in the grid (they DO belong to
            // the row's track); only their padding is set so their
            // text-edge matches the editable widgets above.
            (readonlyByColumn[i] || []).forEach(function(el) {
                el.style.paddingLeft = '';
                el.style.paddingRight = '';
                if (align === 'right') el.style.paddingRight = rightInset + 'px';
                else if (align === 'left') el.style.paddingLeft = leftInset + 'px';
            });
        });
    }

    applyStruct(newStruct) {
        // Public hook for data-driven struct mutation. Re-walks the
        // struct via the adapter, invalidates the template cache,
        // remounts header/footer + CSS columns, then re-renders rows.
        // Not auto-wired today: callers must invoke explicitly.
        if (!this.structAdapter) return;
        this.structAdapter.rebuild(newStruct);
        this.cellmap = this.structAdapter.cellmap;
        if (this._changeMgr) this._changeMgr.grid.cellmap = this.cellmap;
        this.templateSources = {};
        this.templateLoading = {};
        Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
        this._mountStructSlots();
        this.newDataStore();
        this._scheduleStructSync();
    }

    setTotalizer(field, datapath) {
        // Public API: register a column for live totalization. Works in
        // BOTH resource= and struct= modes (in struct mode, cells with
        // `totalize=` auto-register; this is the manual escape hatch).
        if (!this._changeMgr) return;
        this.cellmap[field] = this.cellmap[field]
            || {field: field, _nodelabel: field};
        this.cellmap[field].totalize = datapath;
        this._changeMgr.addTotalizer(field, {totalize: datapath});
        this._changeMgr.updateTotalizer(field);
    }

    setFormula(field, expression) {
        // Public API: register a column whose value is derived live
        // from other row fields. Expression is plain JS in the context
        // of the row dict (same contract as `gnr.Grid` formula column).
        if (!this._changeMgr) return;
        this.cellmap[field] = this.cellmap[field]
            || {field: field, _nodelabel: field};
        this.cellmap[field].formula = expression;
        this.cellmap[field].calculated = true;
        this._changeMgr.addFormulaColumn(field, {formula: expression});
        this._changeMgr.recalculateOneFormula(field);
    }

    // ====================================================================
    //  Counter field — 1-based ordinal column maintained on each row
    // ====================================================================

    updateCounterColumn() {
        // Walk the rows in render order and write `^.<counterField> = k`
        // (1-based) on each row Bag. No-op when the counter field is not
        // set, or when the Bag isn't materialised yet. Pattern lifted
        // from `gnr.Grid.mixin_updateCounterColumn` (genro_grid.js:3657).
        if (!this.counterField) return;
        const bag = this.storebag();
        if (!(bag instanceof gnr.GnrBag)) return;
        const field = this.counterField;
        let k = 1;
        bag.forEach(function(node) {
            const row = node.getValue();
            if (!(row instanceof gnr.GnrBag)) {
                k += 1;
                return;
            }
            if (row.getItem(field) !== k) {
                row.setItem(field, k);
            }
            k += 1;
        }, 'static');
    }

    // ====================================================================
    //  Store dispatch & render — single entry point for storepath events
    // ====================================================================

    newDataStore() {
        // Render the grid from scratch against the current Bag at
        // `storepath`. Mirrors `gnr.Grid.mixin_newDataStore` (genro_grid.js
        // line 2886): called at construct time, on whole-Bag swap, and
        // whenever a record load lands a fresh Bag at storepath.
        // Always publish `onNewDatastore` so subscribers (e.g.
        // GridChangeManager, user dataControllers) get the same hook
        // contract as a standard genropy Grid. Guard against the
        // empty-Bag NPE in GridChangeManager's `rowLogger`: only emit
        // once the Bag is materialised.
        const bag = this.storebag();
        const hasBag = (bag instanceof gnr.GnrBag);
        if (hasBag && this._cmNeedsBag && this._changeMgr) {
            this._cmNeedsBag = false;
        }
        if (hasBag) {
            this.sourceNode.publish('onNewDatastore');
        }
        if (!hasBag || bag.len() === 0) {
            // Nothing to render — clear stale tiles if any survived.
            Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
            return;
        }
        // Renumber upfront so the initial render already shows the
        // correct counter values; widgets bound to `^.<counterField>`
        // pick them up on their first paint.
        this.updateCounterColumn();
        this._ensureTemplate(() => this._fullSync());
    }

    gnr_storepath(value, kw, trigger_reason) {
        // Single dispatch entry point for storepath-bound mutations.
        // Wired in grouplet.py's bootstrap dataController via
        //   node.externalWidget = node.gridController;
        //   node.registerDynAttr('storepath');
        //   node._setDynAttributes();
        // The framework calls us through gnrdomsource.js:1357-1363
        // (doUpdateAttrBuiltObj → externalWidget['gnr_'+attr]).
        // Pattern reference: FullCalendar in genro_extra.js:145.
        if (!kw || kw.reason === 'autocreate') return;
        const storeBag = this.storebag();
        const storeNode = storeBag && storeBag.getParentNode();
        if (!kw.node) return;
        // `parentshipLevel` (gnrbag.js:535) discriminates between:
        //   parent_lv === 0 → the rows Bag itself was replaced
        //                     (newDataStore — equivalent of
        //                     mixin_newDataStore in genro_grid.js)
        //   parent_lv === 1 → add/remove of a whole row
        //   parent_lv  > 1 → mutation INSIDE a row (field/sub-bag):
        //                    widgets bound to that field update
        //                    themselves via the standard `^.field`
        //                    binding. The controller only intervenes
        //                    here for chrome that lives OUTSIDE the
        //                    row template — namely the tab chip label
        //                    in tabs mode, which is plain DOM (no
        //                    sourceNode subscription of its own).
        const parent_lv = storeNode
            ? kw.node.parentshipLevel(storeNode)
            : 0;
        if (parent_lv < 0) {
            // An ancestor of the rows Bag was replaced — typically a
            // record load that does `setRelativeData('.record', <cluster>)`
            // wholesale. The Bag at storepath has just been swapped in
            // as part of that parent payload. Treat as newDataStore.
            this.newDataStore();
            return;
        }
        if (parent_lv === 0) {
            // Whole-store replacement: rebuild from the new Bag.
            this.newDataStore();
            return;
        }
        if (parent_lv > 1) {
            // Tabs mode label refresh: walk up the changed node's
            // parentship chain to find the row-level node (parent_lv=1)
            // and, if the mutated leaf is the titleField, repaint the
            // chip's title text. Other intra-row mutations are ignored
            // (widgets do their own binding).
            if (this._isTabsLayout() && this.titleField) {
                this._maybeRefreshTabLabel(kw.node, storeNode);
            }
            return;
        }
        // parent_lv === 1: add/remove of a whole row.
        const pkey = kw.node.label;
        if (!pkey) return;
        if (kw.evt === 'ins') {
            this._ensureTemplate(() => this._renderTile(pkey),
                                 this._templateKeyForItem(pkey));
            this.updateCounterColumn();
        } else if (kw.evt === 'del') {
            this._destroyTile(pkey);
            this.updateCounterColumn();
        }
    }

    _maybeRefreshTabLabel(changedNode, storeNode) {
        // Find the row-level ancestor of `changedNode` (the node whose
        // parent IS `storeNode`). Walk up parents until we hit it, then
        // verify the mutated leaf is exactly the titleField. We need an
        // exact match: if the user has nested data and the titleField
        // is `.name` but the change was on `.contacts.r_001.value`,
        // the leaf check filters it out.
        let cur = changedNode;
        let leafLabel = null;
        while (cur) {
            const parent = cur.getParentNode && cur.getParentNode();
            if (!parent) break;
            if (parent === storeNode) {
                // `cur` is the row node; the path from row to changed
                // leaf must be exactly `<titleField>`.
                if (leafLabel !== this.titleField) return;
                const chip = this._tabsByPkey[cur.label];
                const title = chip && chip.querySelector(
                    ':scope > .grouplet_grid_tab_title');
                if (title) title.textContent = this._readTabLabel(cur.label);
                return;
            }
            leafLabel = (leafLabel === null)
                ? cur.label
                : (cur.label + '.' + leafLabel);
            cur = parent;
        }
    }

    // ====================================================================
    //  Layout — responsive grid, slot classes, cards/tabs affordances
    // ====================================================================
    //
    //  All layout-specific DOM is built client-side, never emitted from
    //  Python. Cards mode appends a `.grouplet_grid_footer` div to the
    //  container (CSS grid-area `addbtn` parks it below the body). Tabs
    //  mode inserts a `.grouplet_grid_tabbar` between the `top` slot and
    //  the body, plus a `+` chip on its right. `setLayout()` swaps
    //  between the two without touching row panels.

    _applyResponsiveLayout() {
        if (!(this.minWidth && this.cols > 1)) return;
        // Set custom properties on the container (stable across body
        // rebuilds). CSS uses these to drive the grid layout on
        // .grouplet_grid_body.
        const container = this._containerDom();
        container.style.setProperty('--gg-cols', String(this.cols));
        container.style.setProperty('--gg-min-width', this.minWidth);
        container.style.setProperty('--gg-gap', this.gap);
        container.classList.add('gg-responsive');
    }

    _applySlotClasses() {
        // Add .has-top / .has-bottom / .has-left / .has-right when the
        // matching slot div has actual content. CSS uses these to expand
        // the grid track from 0 to auto and to reveal the slot itself.
        const container = this._containerDom();
        ['top', 'bottom', 'left', 'right'].forEach((side) => {
            const slot = container.querySelector(
                ':scope > .grouplet_grid_slot_' + side);
            if (slot && slot.children.length > 0) {
                container.classList.add('has-' + side);
            }
        });
    }

    _isTabsLayout() {
        return this.layout === 'tabs' || this.layout === 'vtabs';
    }

    _buildLayoutAffordances() {
        const containerDom = this._containerDom();
        // Always start clean — `setLayout()` removes mode classes via
        // teardown, but the constructor's first call also enters here
        // and we want idempotent behavior.
        containerDom.classList.remove(
            'grouplet_grid--tabs', 'grouplet_grid--vtabs');
        if (this._isTabsLayout()) {
            containerDom.classList.add('grouplet_grid--tabs');
            if (this.layout === 'vtabs') {
                containerDom.classList.add('grouplet_grid--vtabs');
            }
            this._buildTabbar(containerDom);
            // Re-add chips for existing rows (relevant when entering
            // tabs mode via setLayout — rows already exist).
            Object.keys(this.tiles).forEach((pkey) => {
                this._addTabChip(pkey);
            });
            // If at least one row exists and none is currently active,
            // activate the first.
            const allKeys = Object.keys(this.tiles);
            if (allKeys.length > 0 && !this.activePkey) {
                this._activateTab(allKeys[0]);
            } else if (this.activePkey && this.tiles[this.activePkey]) {
                this._setActiveTabClasses(this.activePkey);
            }
        } else {
            this._buildCardsFooter(containerDom);
        }
        this._updateAddBtnState();
    }

    _teardownLayoutAffordances() {
        // Remove the layout-specific scaffolding (footer or tabbar) and
        // wipe state. Row wrappers themselves are NOT touched — their
        // widgets / subscriptions / pending edits stay alive across a
        // layout switch.
        if (this.addBtnDom && this.addBtnDom.parentNode) {
            this.addBtnDom.parentNode.removeChild(this.addBtnDom);
        }
        this.addBtnDom = null;
        if (this.tabbarDom && this.tabbarDom.parentNode) {
            this.tabbarDom.parentNode.removeChild(this.tabbarDom);
        }
        this.tabbarDom = null;
        this.tabstripDom = null;
        // No per-chip subscriptions to detach: tab label reactivity is
        // a single branch inside `gnr_storepath` (handled by the
        // controller's existing dyn-attr subscription on `storepath`),
        // so the chips themselves carry no listeners beyond click/DnD,
        // which are removed when the DOM is destroyed.
        this._tabsByPkey = {};
        // Strip tab-active class from any surviving row wrapper.
        Object.keys(this.tiles).forEach((pkey) => {
            const entry = this.tiles[pkey];
            const live = entry && genro.nodeById(entry.tileNodeId);
            const dom = live && live.getDomNode && live.getDomNode();
            if (dom) dom.classList.remove('gg-tab-active');
        });
    }

    setLayout(newLayout) {
        // Public API: flip between 'cards', 'tabs' and 'vtabs' at
        // runtime. Row panels survive the switch (only layout-specific
        // DOM is rebuilt). Selection is preserved when going from one
        // tabs flavor to another (or cards → tabs/vtabs); going to
        // cards clears `activePkey` since there is no active concept.
        if (newLayout !== 'cards'
            && newLayout !== 'tabs'
            && newLayout !== 'vtabs') {
            console.warn('[GG] setLayout: unknown layout', newLayout);
            return;
        }
        if (newLayout === this.layout) return;
        const prevActive = this.activePkey;
        this._teardownLayoutAffordances();
        this.layout = newLayout;
        if (newLayout === 'cards') {
            this.activePkey = null;
        } else if (prevActive && this.tiles[prevActive]) {
            // Keep the previously selected row as the active tab if it
            // still exists; the build pass below will install the chip
            // and apply `.gg-tab-active`.
            this.activePkey = prevActive;
        }
        this._buildLayoutAffordances();
    }

    _buildCardsFooter(containerDom) {
        // The phantom `+` is appended to the CONTAINER (not the body)
        // so that the framework's row rendering inside the body never
        // touches it. CSS pins the footer to its own grid-area
        // (`addbtn`) so it sits directly below the body.
        if (!this.additem) return;
        const btn = document.createElement('div');
        btn.className = 'grouplet_grid_footer';
        btn.setAttribute('title', _T('!!Add row'));
        // Honor `additem_kw` (extra class / label):
        //   additem_class → appended to the class list
        //   additem_label → switches the footer to the `--labeled` variant
        //                   and renders a `<span>` next to the `+` glyph
        const extra = this.additemKw || {};
        if (extra._class) {
            btn.className += ' ' + extra._class;
        }
        const label = extra.label || '';
        if (label) {
            btn.className += ' grouplet_grid_footer--labeled';
            const span = document.createElement('span');
            span.textContent = _T(label);
            btn.appendChild(span);
        }
        const that = this;
        btn.addEventListener('click', function() {
            genro.publish(that.actionTopic, {action: 'add'});
        });
        containerDom.appendChild(btn);
        this.addBtnDom = btn;
    }

    _buildTabbar(containerDom) {
        // Insert the tabbar immediately after the `top` slot so the CSS
        // grid template-areas places it correctly (top → tabbar → center).
        const tabbar = document.createElement('div');
        tabbar.className = 'grouplet_grid_tabbar';
        const strip = document.createElement('div');
        strip.className = 'grouplet_grid_tabs';
        tabbar.appendChild(strip);
        if (this.additem) {
            const addBtn = document.createElement('div');
            addBtn.className = 'grouplet_grid_tab_add';
            addBtn.setAttribute('title', _T('!!Add row'));
            // The `+` chip is intentionally NOT draggable and NOT a
            // drop target — even when `dragCode` is set, no DnD
            // listeners are attached. Dropping a chip on the `+`
            // releases as a no-op.
            const that = this;
            addBtn.addEventListener('click', function() {
                genro.publish(that.actionTopic, {action: 'add'});
            });
            tabbar.appendChild(addBtn);
            this.addBtnDom = addBtn;
        }
        // Place the tabbar at the start of the container (after the top
        // slot if present, else first). CSS grid-template-areas pins it
        // to the `tabbar` area; document order only matters for
        // accessibility / source-reading order.
        const topSlot = containerDom.querySelector(
            ':scope > .grouplet_grid_slot_top');
        if (topSlot && topSlot.nextSibling) {
            containerDom.insertBefore(tabbar, topSlot.nextSibling);
        } else {
            containerDom.insertBefore(tabbar, containerDom.firstChild);
        }
        this.tabbarDom = tabbar;
        this.tabstripDom = strip;
    }

    // ====================================================================
    //  Tabs — chip lifecycle, activation, per-chip DnD
    // ====================================================================
    //
    //  The chip itself is the drag handle in tabs mode (no `⠿` glyph).
    //  Same data-transfer payload as `_wireTileDnD`, so cross-grid drag
    //  works between any combination of cards-mode and tabs-mode grids
    //  sharing a `dragCode`. The drop position is always "before the
    //  target chip" — same convention as cards mode.

    _addTabChip(pkey) {
        if (!this.tabstripDom) return;
        if (this._tabsByPkey[pkey]) return;
        const chip = document.createElement('div');
        chip.className = 'grouplet_grid_tab';
        chip.setAttribute('data-rowkey', pkey);
        const title = document.createElement('div');
        title.className = 'grouplet_grid_tab_title';
        title.textContent = this._readTabLabel(pkey);
        chip.appendChild(title);
        if (this.delitem) {
            const closeBtn = document.createElement('div');
            closeBtn.className = 'grouplet_grid_tab_close';
            closeBtn.textContent = '×';
            closeBtn.setAttribute('title', _T('!!Delete row'));
            const that = this;
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                genro.publish(that.actionTopic,
                    {action: 'delete', rowKey: pkey});
            });
            chip.appendChild(closeBtn);
        }
        const that0 = this;
        chip.addEventListener('click', function() {
            that0._activateTab(pkey);
        });
        // Insert at the correct position relative to existing chips,
        // mirroring the Bag order. The chip strip is always in sync
        // with the Bag thanks to the `gnr_storepath` pipeline — but
        // for the FIRST render after a fullSync we mount in Bag order.
        const bag = this.storebag();
        let inserted = false;
        if (bag instanceof gnr.GnrBag) {
            const allKeys = bag.getNodes().map((n) => n.label);
            const idx = allKeys.indexOf(pkey);
            for (let j = idx + 1; j < allKeys.length; j++) {
                if (this._tabsByPkey[allKeys[j]]) {
                    this.tabstripDom.insertBefore(
                        chip, this._tabsByPkey[allKeys[j]]);
                    inserted = true;
                    break;
                }
            }
        }
        if (!inserted) {
            this.tabstripDom.appendChild(chip);
        }
        this._tabsByPkey[pkey] = chip;
        if (this.dragCode) {
            this._wireTabDnD(chip, pkey);
        }
        // Reactive label refresh is handled by `gnr_storepath` →
        // `_maybeRefreshTabLabel` whenever the row's titleField mutates.
        // No per-chip subscription needed.
    }

    _removeTabChip(pkey) {
        const chip = this._tabsByPkey[pkey];
        if (!chip) return;
        if (this.dragCode) {
            this._unwireTabDnD(pkey);
        }
        if (chip.parentNode) chip.parentNode.removeChild(chip);
        delete this._tabsByPkey[pkey];
    }

    _readTabLabel(pkey) {
        if (!this.titleField) return pkey;
        const v = genro.getData(
            this.storepath + '.' + pkey + '.' + this.titleField);
        if (v === undefined || v === null || v === '') {
            return _T(this.emptyTitle);
        }
        return String(v);
    }

    _activateTab(pkey) {
        if (!this._isTabsLayout()) return;
        if (this.activePkey === pkey) return;
        this.activePkey = pkey;
        this._setActiveTabClasses(pkey);
        // Hook for Item 12 (form swap): publish activation on the action
        // bus. No internal subscriber for now — it is a pure extension
        // point. External listeners can use it (e.g. `+` auto-focus).
        genro.publish(this.actionTopic,
            {action: 'activate', rowKey: pkey});
    }

    _setActiveTabClasses(activePkey) {
        // Toggles `.gg-tab-active` on every chip and every row wrapper.
        // Idempotent: safe to call on every render / activation.
        Object.keys(this._tabsByPkey).forEach((rk) => {
            const chip = this._tabsByPkey[rk];
            if (!chip) return;
            chip.classList.toggle('gg-tab-active', rk === activePkey);
        });
        Object.keys(this.tiles).forEach((rk) => {
            const entry = this.tiles[rk];
            const live = entry && genro.nodeById(entry.tileNodeId);
            const dom = live && live.getDomNode && live.getDomNode();
            if (dom) dom.classList.toggle('gg-tab-active', rk === activePkey);
        });
    }

    _wireTabDnD(chipDom, pkey) {
        const that = this;
        const dataKey = 'application/x-gg-' + this.dragCode;
        const containerDom = this._containerDom();
        chipDom.setAttribute('draggable', 'true');
        const onDragStart = function(e) {
            try {
                e.dataTransfer.setData(dataKey, JSON.stringify({
                    rowKey: pkey, nodeId: that.nodeId
                }));
                e.dataTransfer.setData('text/plain', pkey);
                e.dataTransfer.effectAllowed = 'move';
            } catch (err) { /* IE/Safari quirks */ }
            try {
                const auxDragImage = document.getElementById('auxDragImage');
                if (auxDragImage) {
                    const clone = chipDom.cloneNode(true);
                    clone.classList.remove('gg-dragging', 'gg-drop-target',
                        'gg-drop-target-invalid', 'gg-just-dropped');
                    clone.style.width = chipDom.offsetWidth + 'px';
                    auxDragImage.appendChild(clone);
                    e.dataTransfer.setDragImage(clone,
                        e.clientX - chipDom.getBoundingClientRect().left,
                        e.clientY - chipDom.getBoundingClientRect().top);
                    setTimeout(function() {
                        if (clone.parentNode) {
                            clone.parentNode.removeChild(clone);
                        }
                    }, 0);
                }
            } catch (err) { /* setDragImage not supported */ }
            chipDom.classList.add('gg-dragging');
            containerDom.classList.add('gg-drag-active');
            e.stopPropagation();
        };
        const onDragEnd = function() {
            chipDom.classList.remove('gg-dragging');
            that._clearDragOver();
            containerDom.classList.remove('gg-drag-active');
        };
        const onDragOver = function(e) {
            if (chipDom.classList.contains('gg-dragging')) {
                that._clearDragOver();
                return;
            }
            const types = e.dataTransfer.types || [];
            let isValid = false;
            let isForeignGG = false;
            for (let i = 0; i < types.length; i++) {
                if (types[i] === dataKey) { isValid = true; break; }
                if (typeof types[i] === 'string'
                    && types[i].indexOf('application/x-gg-') === 0) {
                    isForeignGG = true;
                }
            }
            if (!isValid && !isForeignGG) return;
            if (isValid) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
            } else {
                e.dataTransfer.dropEffect = 'none';
            }
            that._setDragOver(chipDom, isValid);
        };
        const onDragLeave = function(e) {
            if (!chipDom.contains(e.relatedTarget)) {
                if (that._dragOverRow === chipDom) that._clearDragOver();
            }
        };
        const onDrop = function(e) {
            const raw = e.dataTransfer.getData(dataKey);
            that._clearDragOver();
            if (!raw) return;
            e.preventDefault();
            let payload;
            try { payload = JSON.parse(raw); }
            catch (err) { return; }
            if (!payload) return;
            if (payload.nodeId === that.nodeId) {
                if (payload.rowKey === pkey) return;
                genro.publish(that.actionTopic, {
                    action: 'move',
                    rowKey: payload.rowKey,
                    position: '<' + pkey
                });
                return;
            }
            const sourceCtrl = that._findSourceController(payload.nodeId);
            if (!sourceCtrl) return;
            that._doMoveTileFrom(sourceCtrl, payload.rowKey, '<' + pkey);
        };
        chipDom.addEventListener('dragstart', onDragStart);
        chipDom.addEventListener('dragend', onDragEnd);
        chipDom.addEventListener('dragover', onDragOver);
        chipDom.addEventListener('dragleave', onDragLeave);
        chipDom.addEventListener('drop', onDrop);
        // Reuse `_dragHandlesByPkey` storage — keying by pkey is unique
        // per controller, and tabs mode never has a `_wireTileDnD` peer
        // for the same row (only the chip is wired).
        this._dragHandlesByPkey[pkey] = {
            dom: chipDom,
            handlers: {dragstart: onDragStart, dragend: onDragEnd,
                       dragover: onDragOver, dragleave: onDragLeave,
                       drop: onDrop}
        };
    }

    _unwireTabDnD(pkey) {
        // Identical teardown to `_unwireTileDnD` since both store under
        // the same `_dragHandlesByPkey` key; reuse the existing method.
        this._unwireTileDnD(pkey);
    }

    // ====================================================================
    //  Action dispatch — single subscription routes every action
    // ====================================================================

    _registerActionSubscription() {
        // Single dispatch point: menu items, footer button and the public
        // controller methods all publish on `this.actionTopic` with a
        // payload describing the action. _handleAction dispatches.
        this.sourceNode.registerSubscription(
            this.actionTopic, this,
            (payload) => this._handleAction(payload),
            this.actionTopic);
    }

    _handleAction(payload) {
        if (!payload || typeof payload !== 'object') return;
        switch (payload.action) {
            case 'add':
                this._doAddItem(payload.position, payload.defaults);
                break;
            case 'delete': {
                // If no pkey is provided fall back to the currently
                // selected row — used by toolbar '−' buttons that act on
                // the selection rather than on a specific row.
                const pkey = payload.rowKey || this.selectedPkey;
                if (!pkey) return;
                this._askAndDeleteItem(pkey);
                break;
            }
            case 'move':
                this._doMoveTile(payload.rowKey, payload.position);
                break;
        }
    }

    // ====================================================================
    //  DnD — row wrappers, container drop zone, cross-instance migration
    // ====================================================================

    _wireTileDnD(tileDom, pkey) {
        // Wire HTML5 drag-and-drop directly on a row wrapper (mounted DOM).
        // Called from _renderTile after unfreeze. The drag handle inside the
        // wrapper carries `draggable="true"` so dragstart fires; here we
        // listen on the wrapper itself for dragstart/dragend (bubbled from
        // the handle) and dragover/drop (the wrapper is the drop zone).
        // Drop position is always "before the target row" — the cursor's
        // Y inside the row is irrelevant: any hit on the wrapper highlights
        // the whole card and inserts the dragged row at that index.
        const that = this;
        const dataKey = 'application/x-gg-' + this.dragCode;
        const containerDom = this._containerDom();
        const onDragStart = function(e) {
            // The handle that started the drag must belong to THIS
            // wrapper, not to a nested grid's wrapper. Without this
            // check, a dragstart on a nested row's handle would bubble
            // up and re-fire on the outer wrapper, snapshotting the
            // outer card instead of the nested row.
            const handle = e.target.closest
                ? e.target.closest('.grouplet_grid_row_drag') : null;
            if (!handle) return;
            const innermostWrapper = handle.closest('.grouplet_grid_row');
            if (innermostWrapper !== tileDom) return;
            try {
                e.dataTransfer.setData(dataKey, JSON.stringify({
                    rowKey: pkey, nodeId: that.nodeId
                }));
                // Some browsers also need a generic text payload to start.
                e.dataTransfer.setData('text/plain', pkey);
                e.dataTransfer.effectAllowed = 'move';
            } catch (err) { /* IE/Safari quirks */ }
            // Drag image = snapshot of THIS row wrapper. The clone goes
            // into the global '#auxDragImage' off-screen container,
            // becomes the browser's drag image, and is cleaned up on
            // next tick (the snapshot is captured synchronously).
            try {
                const auxDragImage = document.getElementById('auxDragImage');
                if (auxDragImage) {
                    const clone = tileDom.cloneNode(true);
                    clone.classList.remove('gg-dragging', 'gg-drop-target',
                        'gg-drop-target-invalid', 'gg-just-dropped');
                    clone.style.width = tileDom.offsetWidth + 'px';
                    // In struct mode the row's own chrome is stripped
                    // (the container card owns the border/radius). Tag
                    // the clone so CSS can re-add a self-contained card
                    // look — otherwise the drag image renders as a
                    // borderless naked strip. Also carry over the
                    // `--gg-struct-columns` CSS custom property: it's
                    // set inline on the container, but the clone sits
                    // outside the container in `#auxDragImage`, so the
                    // variable wouldn't resolve and the inner grid
                    // would collapse all widgets to a single 1fr track.
                    if (containerDom.classList.contains('grouplet_grid--struct')) {
                        // Mark the clone so CSS can restyle it as a
                        // self-contained card AND apply the inner
                        // struct grid rules — those are scoped under
                        // `.grouplet_grid--struct` which lives on the
                        // container, not on the row. Adding the same
                        // class to the clone makes the struct rules
                        // (display:grid + grid-template-columns) take
                        // effect even though the clone now lives in
                        // `#auxDragImage`, outside the container tree.
                        clone.classList.add('gg-struct-drag-clone',
                            'grouplet_grid--struct');
                        const cols = containerDom.style.getPropertyValue(
                            '--gg-struct-columns');
                        if (cols) {
                            clone.style.setProperty('--gg-struct-columns', cols);
                        }
                    }
                    auxDragImage.appendChild(clone);
                    e.dataTransfer.setDragImage(clone,
                        e.clientX - tileDom.getBoundingClientRect().left,
                        e.clientY - tileDom.getBoundingClientRect().top);
                    setTimeout(function() {
                        if (clone.parentNode) {
                            clone.parentNode.removeChild(clone);
                        }
                    }, 0);
                }
            } catch (err) { /* setDragImage not supported */ }
            tileDom.classList.add('gg-dragging');
            containerDom.classList.add('gg-drag-active');
            // Stop propagation so an outer grid's wrapper does not
            // re-process this dragstart and override the dataTransfer
            // payload + drag image with its own.
            e.stopPropagation();
        };
        const onDragEnd = function() {
            tileDom.classList.remove('gg-dragging');
            that._clearDragOver();
            containerDom.classList.remove('gg-drag-active');
        };
        const onDragOver = function(e) {
            // Distinguish valid vs invalid drops by inspecting the
            // payload's data-transfer keys (available on dragover; the
            // actual data is not). A key matching our `dataKey` → valid.
            // A different `application/x-gg-*` key → another grid with
            // a different dragCode (isolated by default) → invalid.
            // Anything else (text/plain alone, foreign drags) → ignore.
            if (tileDom.classList.contains('gg-dragging')) {
                that._clearDragOver();
                return;
            }
            const types = e.dataTransfer.types || [];
            let isValid = false;
            let isForeignGG = false;
            for (let i = 0; i < types.length; i++) {
                if (types[i] === dataKey) { isValid = true; break; }
                if (typeof types[i] === 'string'
                    && types[i].indexOf('application/x-gg-') === 0) {
                    isForeignGG = true;
                }
            }
            if (!isValid && !isForeignGG) return;
            // Calling preventDefault enables the drop; for invalid
            // payloads we DO NOT preventDefault, so the browser shows
            // the native "no drop" cursor and onDrop won't fire.
            if (isValid) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
            } else {
                e.dataTransfer.dropEffect = 'none';
            }
            that._setDragOver(tileDom, isValid);
        };
        const onDragLeave = function(e) {
            // Only clear when leaving the wrapper, not when crossing
            // into a child element.
            if (!tileDom.contains(e.relatedTarget)) {
                if (that._dragOverRow === tileDom) that._clearDragOver();
            }
        };
        const onDrop = function(e) {
            // Defensive: with dropEffect='none' the browser usually
            // suppresses onDrop, but some setups still fire it. Reading
            // by `dataKey` (our own key) ensures foreign payloads
            // produce an empty `raw` and are silently rejected.
            const raw = e.dataTransfer.getData(dataKey);
            that._clearDragOver();
            if (!raw) return;
            e.preventDefault();
            let payload;
            try { payload = JSON.parse(raw); }
            catch (err) { return; }
            if (!payload) return;
            // Same-instance drop: source and target are the same
            // controller. Drop on a row N → dragged row becomes the new
            // N (target shifts to N+1). "Append at end" is not reachable
            // via D&D — use the footer "+ Add row" or the kebab menu.
            if (payload.nodeId === that.nodeId) {
                if (payload.rowKey === pkey) return;
                genro.publish(that.actionTopic, {
                    action: 'move',
                    rowKey: payload.rowKey,
                    position: '<' + pkey
                });
                return;
            }
            // Cross-instance drop: same dragCode (already filtered by
            // matching `dataKey`) but different controllers. Resolve
            // the source controller and migrate the row directly. This
            // branch is only reached when both grids share an explicit
            // `dragCode` — server-side default keeps dragCode = nodeId,
            // so cross drops cannot happen by accident.
            const sourceCtrl = that._findSourceController(payload.nodeId);
            if (!sourceCtrl) return;
            that._doMoveTileFrom(sourceCtrl, payload.rowKey, '<' + pkey);
        };
        tileDom.addEventListener('dragstart', onDragStart);
        tileDom.addEventListener('dragend', onDragEnd);
        tileDom.addEventListener('dragover', onDragOver);
        tileDom.addEventListener('dragleave', onDragLeave);
        tileDom.addEventListener('drop', onDrop);
        // Track for teardown: the listeners are anonymous closures, so
        // we store references keyed by pkey.
        this._dragHandlesByPkey[pkey] = {
            dom: tileDom,
            handlers: {dragstart: onDragStart, dragend: onDragEnd,
                       dragover: onDragOver, dragleave: onDragLeave,
                       drop: onDrop}
        };
    }

    _unwireTileDnD(pkey) {
        const entry = this._dragHandlesByPkey[pkey];
        if (!entry) return;
        Object.keys(entry.handlers).forEach((evt) => {
            entry.dom.removeEventListener(evt, entry.handlers[evt]);
        });
        delete this._dragHandlesByPkey[pkey];
    }

    _wireContainerDnD() {
        // Container-level drop accepter: handles drops that fall OUTSIDE
        // any row wrapper (whose own listeners stop propagation). Two
        // legitimate scenarios:
        //   - Empty grid: there are no rows to drop "before", so the
        //     drop lands on free container area → first/only row.
        //   - Past the last row: dragging beyond the bottom of the row
        //     stack → append at the tail.
        // Both same-instance reorder (drag a row over the empty space
        // below it → appends) and cross-instance migration (drag from
        // another grid with same dragCode → appends) flow through here.
        // Visual cue: the whole container highlights green during the
        // dragover so the user sees "this whole grid will accept it".
        if (!this.dragCode) return;
        const containerDom = this._containerDom();
        const that = this;
        const dataKey = 'application/x-gg-' + this.dragCode;
        const onDragOver = function(e) {
            const types = e.dataTransfer.types || [];
            let isValid = false;
            for (let i = 0; i < types.length; i++) {
                if (types[i] === dataKey) { isValid = true; break; }
            }
            if (!isValid) return;
            // Highlight the container only when no row is currently the
            // dragover target — i.e. the cursor is on free space, not
            // over a row wrapper that has its own row-level highlight.
            if (that._dragOverRow) {
                containerDom.classList.remove('gg-container-drop-target');
            } else {
                containerDom.classList.add('gg-container-drop-target');
            }
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        };
        const onDragLeave = function(e) {
            // Only clear when leaving the container outright; crossing
            // into a child row should keep the container "armed".
            if (!containerDom.contains(e.relatedTarget)) {
                containerDom.classList.remove('gg-container-drop-target');
            }
        };
        const onDrop = function(e) {
            containerDom.classList.remove('gg-container-drop-target');
            // If a row wrapper inside the container handled the drop, it
            // called e.preventDefault() — skip in that case so we don't
            // re-process the same event (which would double-mutate).
            if (e.defaultPrevented) return;
            const raw = e.dataTransfer.getData(dataKey);
            if (!raw) return;
            e.preventDefault();
            let payload;
            try { payload = JSON.parse(raw); }
            catch (err) { return; }
            if (!payload) return;
            if (payload.nodeId === that.nodeId) {
                // Same-instance: append at the tail.
                that._doMoveTileSameInstance(payload.rowKey, null);
                return;
            }
            const sourceCtrl = that._findSourceController(payload.nodeId);
            if (!sourceCtrl) return;
            that._doMoveTileFrom(sourceCtrl, payload.rowKey, null);
        };
        containerDom.addEventListener('dragover', onDragOver);
        containerDom.addEventListener('dragleave', onDragLeave);
        containerDom.addEventListener('drop', onDrop);
        this._containerDnDHandlers = {
            dom: containerDom,
            handlers: {dragover: onDragOver, dragleave: onDragLeave,
                       drop: onDrop}
        };
    }

    _unwireContainerDnD() {
        const entry = this._containerDnDHandlers;
        if (!entry) return;
        Object.keys(entry.handlers).forEach((evt) => {
            entry.dom.removeEventListener(evt, entry.handlers[evt]);
        });
        this._containerDnDHandlers = null;
    }

    _doMoveTileSameInstance(pkey, position) {
        // Same-instance reorder, position can be null → append at tail.
        // Bag-only mutation; the DOM diff is done by `gnr_storepath`.
        // No guards: this only runs from a drop handler that already
        // proved the row exists in our Bag (the drag started from it).
        const dataBag = this.storebag();
        const node = dataBag.getNode(pkey);
        const rowValue = node.getValue();
        const rowAttrs = node.getAttr() || {};
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[pkey] = true;
        dataBag.popNode(pkey);
        const setKw = position ? {_position: position} : {};
        dataBag.setItem(pkey, rowValue, rowAttrs, setKw);
    }

    _setDragOver(wrapper, isValid) {
        const wantClass = isValid
            ? 'gg-drop-target' : 'gg-drop-target-invalid';
        if (this._dragOverRow === wrapper
            && wrapper.classList.contains(wantClass)) return;
        this._clearDragOver();
        wrapper.classList.add(wantClass);
        this._dragOverRow = wrapper;
    }

    _clearDragOver() {
        if (!this._dragOverRow) return;
        this._dragOverRow.classList.remove(
            'gg-drop-target', 'gg-drop-target-invalid');
        this._dragOverRow = null;
    }

    _doMoveTile(pkey, position) {
        // Reorder a row inside the rows Bag. `position` is '<targetKey'
        // or '>targetKey'. Bag-only mutation; the DOM diff is done by
        // `gnr_storepath` reacting to the `del`+`ins` trigger pair.
        // No guards: this only runs from an action published by a DnD
        // handler that already proved the row exists in our Bag.
        const dataBag = this.storebag();
        const node = dataBag.getNode(pkey);
        const rowValue = node.getValue();
        const rowAttrs = node.getAttr() || {};
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[pkey] = true;
        dataBag.popNode(pkey);
        dataBag.setItem(pkey, rowValue, rowAttrs, {_position: position});
    }

    _findSourceController(sourceNodeId) {
        // Resolves the controller of another GroupletGrid instance on
        // the same page. The controller is attached to its container
        // node by the `dataController` bootstrap in grouplet.py —
        // `node.gridController`.
        const node = genro.nodeById(sourceNodeId);
        return (node && node.gridController) || null;
    }

    _doMoveTileFrom(sourceCtrl, sourceRowKey, targetPosition) {
        // Migrate a row from another grid instance into THIS grid.
        // Bag-only mutation on source and target; each side's
        // `gnr_storepath` reacts to its own `del`/`ins` and rebuilds
        // its tiles. Cross-instance is the only special case where
        // sourceCtrl could be `this` (browser quirk on self-drop) —
        // keep that guard.
        if (sourceCtrl === this) return;
        const sourceBag = sourceCtrl.storebag();
        const targetBag = this.storebag();
        const node = sourceBag.getNode(sourceRowKey);
        const rowValue = node.getValue();
        const rowAttrs = node.getAttr() || {};
        let targetRowKey = sourceRowKey;
        if (targetBag.getNode(targetRowKey)) {
            targetRowKey = genro.time36Id();
        }
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[targetRowKey] = true;
        sourceBag.popNode(sourceRowKey);
        const setKw = targetPosition ? {_position: targetPosition} : {};
        targetBag.setItem(targetRowKey, rowValue, rowAttrs, setKw);
    }

    _flashTile(pkey) {
        // Just-dropped flash: the tile inherits the drop-target tint for
        // ~260ms then transitions back to normal. CSS handles the
        // fade-out via `transition` on background/border, so JS only
        // adds the class and removes it later. Defer one tick so the
        // tile has time to fully mount (this method may fire from a
        // post-DnD callback chained ahead of `_renderTile`).
        const that = this;
        setTimeout(function() {
            const tile = that.tiles[pkey];
            if (tile) tile.flash();
        }, 0);
    }

    // ====================================================================
    //  Row CRUD — internal sync between rows Bag and DOM
    // ====================================================================

    _fullSync() {
        const bag = this.storebag();
        const presentKeys = {};
        const toAdd = [];
        if (bag instanceof gnr.GnrBag) {
            bag.getNodes().forEach((node) => {
                presentKeys[node.label] = true;
                if (!this.tiles[node.label]) toAdd.push(node.label);
            });
        }
        Object.keys(this.tiles).forEach((pkey) => {
            if (!presentKeys[pkey]) this._destroyTile(pkey);
        });
        if (toAdd.length === 0) return;
        // Tabs mode: pre-decide which row will be active so `_renderTile`
        // can stamp `gg-tab-active` directly onto the wrapper's `_class`
        // BEFORE the wrapper is built. Without this, all wrappers mount
        // with `display:none` (CSS hides every non-active row in tabs
        // mode), and nested groupletGrids inside them — which run their
        // own `newDataStore` on `_onBuilt` — would render their
        // body subtree while detached from layout flow. By activating
        // up-front, the first wrapper is `display:block` from the very
        // first paint and its nested widgets build normally.
        if (this._isTabsLayout() && !this.activePkey && toAdd.length > 0) {
            this.activePkey = toAdd[0];
        }
        this.bodyNode.freeze();
        toAdd.forEach((pkey) => this._renderTile(pkey));
        this.bodyNode.unfreeze();
        // Active-tab classes are already applied per-row by `_renderTile` →
        // `_addTabChip` → `_setActiveTabClasses` along the active path.
        if (this.structAdapter) this._scheduleStructSync();
    }

    _renderTile(pkey) {
        if (this.tiles[pkey]) return;
        const position = this._computeTilePosition(pkey);
        const tile = new gnr.GroupletGridTile(this, pkey);
        tile.mount(position);
        this.tiles[pkey] = tile;
        this._afterTileMounted(tile);
    }

    _computeTilePosition(pkey) {
        // Derive the wrapper insertion position from the Bag itself:
        // put the wrapper right before the wrapper of the next sibling
        // tile that is already rendered, or append at the tail.
        // Works for all sources of 'ins' (action handlers, DnD,
        // external setItem) without the caller having to know.
        const bag = this.storebag();
        if (!(bag instanceof gnr.GnrBag)) return undefined;
        const allKeys = bag.getNodes().map((n) => n.label);
        const idx = allKeys.indexOf(pkey);
        for (let j = idx + 1; j < allKeys.length; j++) {
            if (this.tiles[allKeys[j]]) {
                return '<_grtile_' + allKeys[j];
            }
        }
        return undefined;
    }

    _afterTileMounted(tile) {
        // Decorations driven by controller-global state. The tile is
        // already in the DOM and registered in `this.tiles`.
        const pkey = tile.pkey;
        this._updateAddBtnState();
        // Tabs mode: also build the corresponding tab chip. The tile's
        // `_class` was pre-stamped with `gg-tab-active` if it is the
        // active one (decided by `_fullSync` before the batch freeze).
        // If the tile was just added via the `+` button
        // (`_pendingActivate === pkey`), switch the active tab to it
        // now — same UX as opening a new browser tab.
        if (this._isTabsLayout()) {
            this._addTabChip(pkey);
            const pending = this._pendingActivate === pkey;
            if (pending) {
                this._pendingActivate = null;
                this.activePkey = null;
                this._activateTab(pkey);
            } else if (!this.activePkey) {
                this._activateTab(pkey);
            } else if (this.activePkey === pkey) {
                this._setActiveTabClasses(this.activePkey);
            }
        }
        // Consume pending flash (set by `_doMoveTile*` before mutating
        // the Bag): highlight a tile that just landed via DnD.
        if (this._pendingFlash && this._pendingFlash[pkey]) {
            delete this._pendingFlash[pkey];
            this._flashTile(pkey);
        }
        if (this.structAdapter) this._scheduleStructSync();
    }

    _graftNode(parentContent, srcNode) {
        const attrs = objectUpdate({}, srcNode.attr || {});
        const tag = attrs.tag || 'div';
        delete attrs.tag;
        parentContent._(tag, srcNode.label, attrs);
        const newNode = parentContent.getNode(srcNode.label);
        const childValue = srcNode.getValue();
        if (childValue instanceof gnr.GnrBag) {
            const newContent = newNode.getValue();
            childValue.getNodes().forEach((cn) => {
                this._graftNode(newContent, cn);
            });
        } else if (childValue !== undefined && childValue !== null) {
            newNode.setValue(childValue);
        }
    }

    _destroyTile(pkey) {
        const tile = this.tiles[pkey];
        if (!tile) return;
        // Tear down DnD listeners before the DOM is destroyed.
        // In tabs mode the DnD handlers are on the chip (not the tile
        // wrapper), so the wrapper-level unwire is a no-op there — the
        // chip teardown happens in `_removeTabChip` below. In cards
        // mode the chip teardown is a no-op.
        if (this.dragCode) this._unwireTileDnD(pkey);
        // Tabs mode: drop the chip + decide next active.
        if (this._isTabsLayout()) {
            // Pre-compute the next active tab BEFORE removing the chip.
            let nextActive = null;
            if (this.activePkey === pkey) {
                const chipKeys = Object.keys(this._tabsByPkey);
                const idx = chipKeys.indexOf(pkey);
                if (idx > 0) nextActive = chipKeys[idx - 1];
                else if (chipKeys.length > 1) nextActive = chipKeys[idx + 1];
            }
            this._removeTabChip(pkey);
            if (this.activePkey === pkey) {
                this.activePkey = null;
                if (nextActive) this._activateTab(nextActive);
            }
        }
        tile.unmount();
        delete this.tiles[pkey];
        this._updateAddBtnState();
    }

    _rowCount() {
        return Object.keys(this.tiles).length;
    }

    // ====================================================================
    //  Public action API — thin publishers + private executors
    // ====================================================================
    //
    //  Every public mutator goes through `genro.publish(actionTopic,...)`.
    //  The single subscription in _registerActionSubscription dispatches
    //  via _handleAction → _doAddItem / _askAndDeleteItem. All entry points
    //  (kebab menu, footer button, programmatic calls) follow this path.

    addItem(defaults) {
        genro.publish(this.actionTopic,
                      {action: 'add', defaults: defaults || null});
    }

    insertItemAfter(pkey, defaults) {
        genro.publish(this.actionTopic, {
            action: 'add',
            position: '>' + pkey,
            defaults: defaults || null
        });
    }

    insertItemBefore(pkey, defaults) {
        genro.publish(this.actionTopic, {
            action: 'add',
            position: '<' + pkey,
            defaults: defaults || null
        });
    }

    deleteItem(pkey) {
        genro.publish(this.actionTopic,
                      {action: 'delete', rowKey: pkey});
    }

    _doAddItem(position, defaults) {
        if (this.maxRows && this._rowCount() >= this.maxRows) return;
        // Auto-create the rows Bag if it doesn't exist yet. Real case:
        // a row added to the outer grid (test_7 team) materializes a
        // `person` record without a `.contacts` sub-Bag; the first `+`
        // on the inner grid has to create it.
        let dataBag = this.storebag();
        if (!(dataBag instanceof gnr.GnrBag)) {
            dataBag = new gnr.GnrBag();
            genro.setData(this.storepath, dataBag);
        }
        const newKey = 'r_' + genro.time36Id();
        // Tabs mode: mark the new key as the one to activate when its
        // `_renderTile` fires (triggered by the Bag mutation below via
        // `gnr_storepath`). Picked up — and cleared — inside `_renderTile`.
        if (this._isTabsLayout()) this._pendingActivate = newKey;
        const rowBag = new gnr.GnrBag();
        const merged = objectUpdate({}, this.defaultRow || {});
        objectUpdate(merged, defaults || {});
        Object.keys(merged).forEach((k) => rowBag.setItem(k, merged[k]));
        if (!position) {
            dataBag.setItem(newKey, rowBag);
            return;
        }
        // `position` is a Bag _position spec: '<pkey' (before) or
        // '>pkey' (after). Falls back to '>' if no sign is given.
        const first = position.charAt(0);
        const hasSign = (first === '<' || first === '>');
        const sign = hasSign ? first : '>';
        const targetKey = hasSign ? position.substring(1) : position;
        dataBag.setItem(newKey, rowBag, null, {_position: sign + targetKey});
    }

    _askAndDeleteItem(pkey) {
        // Confirmation dialog before destroying the row. genro.dlg.ask
        // accepts a function in `actions` (funcCreate normalizes both
        // strings and functions — see th.js:20 for an in-codebase example).
        genro.dlg.ask(
            _T('!!Delete this row?'),
            _T('!!This row will be removed. Continue?'),
            {confirm: _T('!!Delete'), cancel: _T('!!Cancel')},
            {confirm: () => this._doDeleteItem(pkey)}
        );
    }

    _doDeleteItem(pkey) {
        if (this._rowCount() <= this.minRows) return;
        const dataBag = this.storebag();
        if (dataBag instanceof gnr.GnrBag) {
            dataBag.popNode(pkey);
        }
        if (this.selectedPkey === pkey) {
            this.selectedPkey = null;
        }
    }

    selectTile(pkey) {
        // In tabs/vtabs mode the active state is fully owned by
        // `_activateTab` (which manages `.gg-tab-active`) — the
        // `selected` CSS class is a cards-mode UX leftover that
        // visually conflicts with the panel chrome here.
        if (this._isTabsLayout()) return;
        if (this.selectedPkey === pkey) return;
        const domForRow = (rk) => {
            const entry = this.tiles[rk];
            const live = entry && genro.nodeById(entry.tileNodeId);
            return (live && live.getDomNode && live.getDomNode()) || null;
        };
        if (this.selectedPkey) {
            const prevDom = domForRow(this.selectedPkey);
            if (prevDom) prevDom.classList.remove('selected');
        }
        this.selectedPkey = pkey;
        const dom = domForRow(pkey);
        if (dom) dom.classList.add('selected');
    }

    _updateAddBtnState() {
        if (!this.addBtnDom) return;
        const atMax = !!(this.maxRows
                         && this._rowCount() >= this.maxRows);
        this.addBtnDom.classList.toggle('disabled', atMax);
    }

    // ====================================================================
    //  Template plumbing — namespacing, cache, source-root building
    // ====================================================================

    _namespaceFrameworkNodeIds(domSource, pkey) {
        // Append `__<gridId>__<pkey>` to nodeIds that the framework
        // generated for its own bookkeeping (groupletGrid containers
        // and their body / addbtn satellites). These nodeIds always
        // share the `grpgrid_` prefix (set server-side by
        // gr_groupletGrid when no explicit nodeId is passed).
        // Author-supplied nodeIds are NEVER touched — it's the author's
        // job to make them unique across rows if they actually use them.
        //
        // Why we still need a nodeId at all on the container, instead
        // of fully attribute-driven lookups: the action topic is
        // `groupletGrid_<nodeId>_action` (publish-subscribe), so each
        // nested grid instance must subscribe to its own topic — hence
        // a unique nodeId per row.
        const suffix = '__' + this.nodeId + '__' + pkey;
        const apply = function(n) {
            const a = n.attr;
            if (!a || typeof a.nodeId !== 'string') return;
            if (a.nodeId.indexOf('grpgrid_') === 0) a.nodeId += suffix;
        };
        domSource.getNodes().forEach((n) => {
            apply(n);
            const v = n.getValue();
            if (v instanceof gnr.GnrBag) v.walk(apply, 'static');
        });
    }

    _ensureTemplate(callback, key) {
        // Keyed template cache. `key` selects which row template to
        // resolve — `__default__` for single-template grids (struct=
        // or resource=), or a sanitized `resourceField` value
        // (e.g. `commercial_offer`) in multi-grouplet mode.
        //
        // Once `templateSources[key]` is a sourceRoot, struct= and
        // resource= modes are indistinguishable to downstream code:
        // `_renderTile` deep-copies the sourceRoot, namespaces nodeIds,
        // mounts in the body.
        key = key || '__default__';
        if (this.templateSources[key]) {
            callback();
            return;
        }
        // Multi-grouplet mode: one RPC at first call preloads ALL
        // candidate templates under the table's folder. Subsequent
        // calls for any key short-circuit on cache. We keep a single
        // shared loading queue under `__resource_field__` since the
        // RPC primes every key in one shot.
        if (this.resourceField) {
            this._ensureResourceFieldTemplates(callback);
            return;
        }
        if (this.templateLoading[key]) {
            this.templateLoading[key].push(callback);
            return;
        }
        this.templateLoading[key] = [callback];
        const flush = () => {
            const queue = this.templateLoading[key];
            delete this.templateLoading[key];
            queue.forEach((cb) => cb());
        };
        // struct= mode: no RPC roundtrip. The adapter synthesizes the
        // row template directly from the struct already loaded into
        // `this.structAdapter` at init time.
        if (this.structAdapter) {
            this.templateSources[key] = this.structAdapter.buildRowTemplate();
            flush();
            return;
        }
        // resource= / handler= mode: server-side RPC builds the
        // template Bag from the named resource.
        const params = {
            resource: this.resource,
            handler: this.handler,
            table: this.table,
            grouplets_root: this.grouplets_root,
            grouplet_kwargs: this.grouplet_kw
        };
        genro.serverCall('gr_getGroupletGridTemplate', params,
            (tplBag, error) => {
                if (error) {
                    console.error('[GG] template RPC failed', error);
                    delete this.templateLoading[key];
                    return;
                }
                this.templateSources[key] = this._bagToDetachedSource(tplBag);
                flush();
            });
    }

    _ensureResourceFieldTemplates(callback) {
        // Multi-grouplet bulk loader. The server returns a Bag whose
        // children are { label: sanitized_resource, value: template_bag,
        // attr: { resource: 'commercial/offer' } } — one entry per
        // grouplet under the table's folder. We turn each into a
        // detached sourceRoot and store under both the sanitized key
        // (label) and the original resource path, so a row whose
        // discriminator carries either form resolves correctly.
        const sharedKey = '__resource_field__';
        if (this.templateLoading[sharedKey]) {
            this.templateLoading[sharedKey].push(callback);
            return;
        }
        this.templateLoading[sharedKey] = [callback];
        const flush = () => {
            const queue = this.templateLoading[sharedKey];
            delete this.templateLoading[sharedKey];
            queue.forEach((cb) => cb());
        };
        const params = {
            table: this.table,
            grouplets_root: this.grouplets_root,
            grouplet_kwargs: this.grouplet_kw
        };
        genro.serverCall('gr_getGroupletGridTemplateMap', params,
            (mapBag, error) => {
                if (error) {
                    console.error('[GG] template map RPC failed', error);
                    delete this.templateLoading[sharedKey];
                    return;
                }
                if (!(mapBag instanceof gnr.GnrBag)) {
                    console.warn('[GG] template map payload is not a Bag',
                                 mapBag);
                    flush();
                    return;
                }
                mapBag.getNodes().forEach((node) => {
                    const tplValue = node.getValue();
                    if (!(tplValue instanceof gnr.GnrBag)) return;
                    const source = this._bagToDetachedSource(tplValue);
                    this.templateSources[node.label] = source;
                    const origResource = node.attr && node.attr.resource;
                    if (origResource) {
                        this.templateSources[origResource] = source;
                    }
                });
                flush();
            });
    }

    _templateKeyForItem(pkey) {
        // Single-template grids (struct=, plain resource=, handler=)
        // all share the `__default__` cache slot. In `resourceField=`
        // mode the row's discriminator field selects which preloaded
        // template applies (cache key = resource_path with `/` → `_`
        // to match server-side keying in gr_getGroupletGridTemplateMap).
        if (!this.resourceField) return '__default__';
        const bag = this.storebag();
        if (!(bag instanceof gnr.GnrBag)) return '__default__';
        const rowNode = bag.getNode(pkey, 'static');
        if (!rowNode) return '__default__';
        const rowValue = rowNode.getValue();
        if (!(rowValue instanceof gnr.GnrBag)) return '__default__';
        const fieldValue = rowValue.getItem(this.resourceField);
        if (!fieldValue) return '__default__';
        return String(fieldValue).replace(/\//g, '_');
    }

    _bagToDetachedSource(bag) {
        const root = genro.src.newRoot();
        if (!(bag instanceof gnr.GnrBag)) {
            console.warn('[GroupletGrid] template payload is not a Bag', bag);
            return root;
        }
        bag.getNodes().forEach((node) => {
            root.setItem(node.label, node._value,
                         objectUpdate({}, node.attr || {}));
        });
        return root;
    }
};


// gnr.GroupletGridTile — long-lived view manager for one item.
// One instance per pkey in controller.tiles. Owns wrapper + chrome + body.
// Created/destroyed by controller._renderTile / _destroyTile via the
// gnr_storepath dispatcher. See mount() for the construction sequence.

gnr.GroupletGridTile = class GroupletGridTile {

    constructor(controller, pkey) {
        this.controller = controller;
        this.pkey = pkey;
        this.tileLabel = '_grtile_' + pkey;
        this.tileNodeId = '__grpgridtile__' + controller.nodeId + '__' + pkey;
        this.templateKey = null;
        this.templateSource = null;
        this.tileNode = null;
        this.tileContent = null;
        this.tileDom = null;
        this.mounted = false;
        this.isActive = false;
        this.isDragging = false;
        this.hasDelete = false;
        this.editmenuSpec = null;
        this.dragEnabled = false;
        this.position = null;
    }

    mount(position) {
        this.position = position || null;
        this._resolveTemplate();
        this._resolveDecorations();
        this._mountWrapper();
        this.tileNode.freeze();
        this._mountChrome();
        this._mountBody();
        this.tileNode.unfreeze();
        this.mounted = true;
    }

    rebuild() {
        // Re-render body + chrome in place; wrapper sourceNode and DnD
        // listeners are preserved. Used on resourceField swap.
        if (!this.mounted) return;
        this.tileNode.freeze();
        this._destroyChrome();
        this._destroyBody();
        this._resolveTemplate();
        this._resolveDecorations();
        this._mountChrome();
        this._mountBody();
        this.tileNode.unfreeze();
    }

    unmount() {
        const bodyContent = this.controller.bodyNode.getValue('static');
        bodyContent.popNode(this.tileLabel);
        this.mounted = false;
        this.tileNode = null;
        this.tileContent = null;
        this.tileDom = null;
        this.isActive = false;
        this.isDragging = false;
    }

    flash() {
        const dom = this.domNode();
        if (!dom) return;
        dom.classList.add('gg-just-dropped');
        setTimeout(() => {
            if (this.tileDom) {
                this.tileDom.classList.remove('gg-just-dropped');
            }
        }, 260);
    }

    domNode() {
        if (this.tileDom) return this.tileDom;
        const live = this.tileNode && genro.nodeById(this.tileNodeId);
        const dom = live && live.getDomNode && live.getDomNode();
        if (dom) this.tileDom = dom;
        return dom || null;
    }

    freeze()   { this.tileNode && this.tileNode.freeze(); }
    unfreeze() { this.tileNode && this.tileNode.unfreeze(); }

    // Model-side accessors — anticipate the pseudoForm / microform layer.
    itemNode() {
        const bag = this.controller.storebag();
        if (!(bag instanceof gnr.GnrBag)) return null;
        return bag.getNode(this.pkey, 'static') || null;
    }
    itemData() {
        const node = this.itemNode();
        const value = node && node.getValue();
        return (value instanceof gnr.GnrBag) ? value : null;
    }

    _resolveTemplate() {
        this.templateKey = this.controller._templateKeyForItem(this.pkey);
        this.templateSource = this.controller.templateSources[this.templateKey];
    }

    _resolveDecorations() {
        const c = this.controller;
        this.hasDelete = !!c.delitem;
        this.dragEnabled = !!c.dragCode;
        const editmenu = c.editmenu;
        this.editmenuSpec = (editmenu && typeof editmenu === 'object'
            && Object.keys(editmenu).length > 0) ? editmenu : null;
    }

    _mountWrapper() {
        // Pre-stamp `gg-tab-active` when this tile is the active one in
        // tabs mode: without this the wrapper mounts under display:none
        // and nested widgets build in a detached layout context.
        const c = this.controller;
        const pkey = this.pkey;
        let tileClass = 'grouplet_grid_row';
        if (c._isTabsLayout() && c.activePkey === pkey) {
            tileClass += ' gg-tab-active';
            this.isActive = true;
        }
        const tile = this;
        const tileKw = {
            datapath: '.' + pkey,
            _class: tileClass,
            nodeId: this.tileNodeId,
            connect_onclick: function() { c.selectTile(pkey); }
        };
        // onCreated runs after the DOM is mounted — the right place to
        // attach the drag handle (no timing hack). HTML5-native DnD is
        // wired by the controller on the wrapper itself.
        if (this.dragEnabled) {
            tileKw.onCreated = function(domnode) {
                const tileDom = domnode.sourceNode
                    ? domnode.sourceNode.getDomNode()
                    : domnode;
                tile.tileDom = tileDom;
                const handle = document.createElement('div');
                handle.className = 'grouplet_grid_row_drag';
                handle.setAttribute('draggable', 'true');
                handle.title = _T('!!Drag to reorder');
                handle.innerHTML =
                    '<span class="grouplet_grid_drag_icon">⠿</span>';
                tileDom.appendChild(handle);
                c._wireTileDnD(tileDom, pkey);
            };
        } else {
            tileKw.onCreated = function(domnode) {
                tile.tileDom = domnode.sourceNode
                    ? domnode.sourceNode.getDomNode()
                    : domnode;
            };
        }
        const bodyContent = c.bodyNode.getValue();
        const extraKw = this.position ? {_position: this.position} : undefined;
        bodyContent._('div', this.tileLabel, tileKw, extraKw);
        this.tileNode = bodyContent.getNode(this.tileLabel);
        this.tileContent = this.tileNode.getValue();
    }

    _mountChrome() {
        this._mountDelete();
        this._mountKebab();
    }

    _destroyChrome() {
        if (!this.tileContent) return;
        const delLabel = '_grtile_del_' + this.pkey;
        const kebabLabel = '_grtile_kebab_' + this.pkey;
        if (this.tileContent.getNode(delLabel, 'static')) {
            this.tileContent.popNode(delLabel);
        }
        if (this.tileContent.getNode(kebabLabel, 'static')) {
            this.tileContent.popNode(kebabLabel);
        }
    }

    _mountDelete() {
        if (!this.hasDelete) return;
        const c = this.controller;
        const pkey = this.pkey;
        const topic = c.actionTopic;
        const delKw = objectUpdate({
            _class: 'grouplet_grid_row_delete',
            tip: _T('!!Delete row'),
            connect_onclick: "genro.publish('" + topic + "',"
                            + "{action:'delete',rowKey:'" + pkey + "'});"
        }, c.delitemKw || {});
        if (c.delitemKw && c.delitemKw._class) {
            // additive merge: keep base class.
            delKw._class = 'grouplet_grid_row_delete '
                         + c.delitemKw._class;
        }
        this.tileContent._('div', '_grtile_del_' + pkey, delKw);
        const delNode = this.tileContent.getNode('_grtile_del_' + pkey);
        delNode.getValue()._('div', 'glyph', {innerHTML: '×'});
    }

    _mountKebab() {
        // editmenu is a dict {entryKey: True | 'label' | {label,action,...}}.
        // True → built-in preset (addPrev/addNext/delete).
        // string → preset + label override.
        // dict → preset + dict merge (custom action allowed).
        const editmenu = this.editmenuSpec;
        if (!editmenu) return;
        const c = this.controller;
        const pkey = this.pkey;
        const topic = c.actionTopic;
        const presets = {
            addPrev: {
                label: _T('!!Add prev'),
                action: "genro.publish('" + topic + "',"
                      + "{action:'add',position:'<" + pkey + "'});"
            },
            addNext: {
                label: _T('!!Add next'),
                action: "genro.publish('" + topic + "',"
                      + "{action:'add',position:'>" + pkey + "'});"
            },
            'delete': {
                label: _T('!!Delete'),
                action: "genro.publish('" + topic + "',"
                      + "{action:'delete',rowKey:'" + pkey + "'});"
            }
        };
        const kebabId = '__grpgridtilemenu__' + c.nodeId + '__' + pkey;
        const kebabKw = objectUpdate({
            _class: 'grouplet_grid_row_kebab',
            tip: _T('!!Row actions'),
            nodeId: kebabId
        }, c.editmenuKw || {});
        if (c.editmenuKw && c.editmenuKw._class) {
            kebabKw._class = 'grouplet_grid_row_kebab '
                           + c.editmenuKw._class;
        }
        this.tileContent._('div', '_grtile_kebab_' + pkey, kebabKw);
        const kebabNode = this.tileContent.getNode('_grtile_kebab_' + pkey);
        const kebabContent = kebabNode.getValue();
        kebabContent._('div', 'glyph', {
            _class: 'grouplet_grid_kebab_icon',
            innerHTML: '⋮'
        });
        const menu = kebabContent._('menu', {
            modifiers: '*',
            _class: 'smallmenu grouplet_grid_row_menu'
        });
        Object.keys(editmenu).forEach((entryKey) => {
            const raw = editmenu[entryKey];
            if (raw === false || raw === null || raw === undefined) return;
            const preset = presets[entryKey] || null;
            let spec;
            if (raw === true) {
                if (!preset) return;
                spec = preset;
            } else if (typeof raw === 'string') {
                spec = objectUpdate({}, preset || {});
                spec.label = raw;
            } else if (typeof raw === 'object') {
                spec = objectUpdate({}, preset || {});
                objectUpdate(spec, raw);
            }
            if (!spec || !spec.label) return;
            menu._('menuline', spec);
        });
    }

    _mountBody() {
        // Deep-copy the template — every tile owns its own. Auto-generated
        // framework nodeIds (`grpgrid_*`) get namespaced so each tile's
        // clone is unique; author-supplied nodeIds are left untouched.
        const cloned = this.templateSource.deepCopy();
        this.controller._namespaceFrameworkNodeIds(cloned, this.pkey);
        cloned.getNodes().forEach((n) => {
            this.controller._graftNode(this.tileContent, n);
        });
    }

    _destroyBody() {
        // Pop everything except the chrome children (`_grtile_del_*` /
        // `_grtile_kebab_*`).
        if (!this.tileContent) return;
        const delLabel = '_grtile_del_' + this.pkey;
        const kebabLabel = '_grtile_kebab_' + this.pkey;
        const labelsToRemove = [];
        this.tileContent.getNodes().forEach((n) => {
            if (n.label === delLabel || n.label === kebabLabel) return;
            labelsToRemove.push(n.label);
        });
        labelsToRemove.forEach((lbl) => this.tileContent.popNode(lbl));
    }
};
