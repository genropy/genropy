// groupletGrid — see docs/groupletgrid_architecture.md
// Three classes on gnr.*: GroupletGridStructAdapter,
// GroupletGridDnD, GroupletGridController, GroupletGridTile.

gnr.GroupletGridStructAdapter = class GroupletGridStructAdapter {
    constructor(struct) {
        this.struct = struct;
        this.cells = this._walkStruct();
        this.cellmap = this._buildCellmap();
    }

    rebuild(struct) {
        this.struct = struct;
        this.cells = this._walkStruct();
        this.cellmap = this._buildCellmap();
    }

    _walkStruct() {
        const rows = this.struct.getItem('view_0.rows_0');
        const out = [];
        rows.getNodes().forEach(function(node) {
            const attr = node.attr || {};
            if (attr.hidden) return;
            const field = attr.caption_field || attr.field;
            if (!field) return;
            // Empty name='' means "no label"; only undefined falls back
            // to the field name.
            const hasName = (attr.name !== undefined && attr.name !== null);
            // totalize=true → auto path '.totalize.<field>' (mirrors
            // gnr.Grid at genro_grid.js:1943); strings pass through.
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
        // Shape expected by GridChangeManager. `_nodelabel` resolves
        // formula_* dyn params; `calculated:true` lets the initial
        // resolveCalculatedColumns pass run on seeded data.
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
        // Width translation:
        //   missing / '*' / '100%'  → minmax(0, 1fr)  (flex track)
        //   anything else           passes through.
        // '100%' as a literal Grid track overflows and resolves with
        // per-container subpixel rounding — visible column drift across
        // header/row/footer; minmax(0, 1fr) is deterministic.
        // Auto-promote the widest fixed-em cell if no flex track exists,
        // otherwise the row centres while header/footer span full width.
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
        // Empty / whitespace-only labels render as &nbsp; to keep the
        // cell's line height (a bare space collapses in some layouts
        // and breaks header/row vertical alignment).
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
        // Only emitted if at least one column has totalize=. Non-total
        // cells become empty placeholders so the columns stay aligned.
        // The `innerHTML='^path'` form is the genropy idiom for live
        // read-only display with `format` applied to the resolved value.
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
        // Same sourceRoot shape the resource= flow produces, but
        // synthesised: widgets are direct children of the row (no
        // per-cell wrapper). Editable cells use the dtype→widget map
        // from gnr.Grid; readonly cells are plain divs with ^.field.
        const root = genro.src.newRoot();
        const row = root._('div', {_class: 'grouplet_grid__struct_row'});
        const Adapter = gnr.GroupletGridStructAdapter;
        this.cells.forEach(function(c) {
            const tag = Adapter._resolveWidgetTag(c);
            if (tag) {
                row._(tag, Adapter._editorKwargs(c));
                return;
            }
            // Readonly cells need the explicit alignment class
            // (NumberTextBox right-aligns natively, a plain div doesn't).
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
        switch (c.dtype) {
            case 'L': case 'I': case 'R': case 'N': return 'right';
            case 'B': return 'center';
            default: return 'left';
        }
    }

    static _resolveWidgetTag(c) {
        // null for readonly cells. Mirrors gnr.Grid editor resolution.
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
        // Layered kwargs: defaults < cell-level options < edit=dict(...).
        // _class is concatenated so the marker class survives overrides.
        const edit = (typeof c.edit === 'object' && c.edit) ? c.edit : {};
        const {tag, _class: editClass, ...editRest} = edit;
        return {
            value: '^.' + c.field,
            width: '100%',
            table: c.related_table,
            values: c.values,
            format: c.format,
            validate_notnull: c.validate_notnull,
            ...editRest,
            _class: 'grouplet_grid__struct_col_cell'
                + (editClass ? ' ' + editClass : '')
        };
    }
};


gnr.GroupletGridDnD = class GroupletGridDnD {

    constructor(controller) {
        this.controller = controller;
    }

    dropType() {
        return 'gg_tile_' + this.controller.dragCode;
    }

    onDrag(dragInfo, dragValues, pkey, tileNodeId) {
        // tileNodeId rewrites dragInfo.nodeId before setDragSourceInfo
        // so selfdrop fires on the tile, not on the handle sub-sourceNode.
        const c = this.controller;
        const dropType = this.dropType();
        if (tileNodeId) dragInfo.nodeId = tileNodeId;
        dragValues[dropType] = {rowKey: pkey, sourceNodeId: c.nodeId};
        try {
            const aux = document.getElementById('auxDragImage');
            const sourceDom = tileNodeId
                ? (c.tiles[pkey] && c.tiles[pkey].domNode())
                : (c._tabsByPkey[pkey]
                    && c._tabsByPkey[pkey].getDomNode());
            if (!aux || !sourceDom) return;
            const clone = sourceDom.cloneNode(true);
            clone.classList.remove('draggedItem', 'canBeDropped',
                'cannotBeDropped', 'grouplet_grid_just_dropped');
            clone.style.width = sourceDom.offsetWidth + 'px';
            const containerDom = c._containerDom();
            if (tileNodeId
                && containerDom.classList.contains('grouplet_grid--struct')) {
                // Struct chrome is on the container; the clone lives in
                // #auxDragImage, so the struct rules must travel with it.
                clone.classList.add('grouplet_grid_struct_drag_clone',
                    'grouplet_grid--struct');
                const cols = containerDom.style.getPropertyValue(
                    '--gg-struct-columns');
                if (cols) clone.style.setProperty('--gg-struct-columns', cols);
            }
            aux.appendChild(clone);
            dragInfo.dragImageNode = clone;
            const rect = sourceDom.getBoundingClientRect();
            dragInfo.event.dataTransfer.setDragImage(clone,
                dragInfo.event.clientX - rect.left,
                dragInfo.event.clientY - rect.top);
            setTimeout(function() {
                if (clone.parentNode) clone.parentNode.removeChild(clone);
            }, 0);
        } catch (err) {}
    }

    onDrop(data, targetPkey) {
        // Drop = insert-after, like the tree (th_tree.py:152).
        const c = this.controller;
        if (!data || !data.rowKey) return;
        if (data.sourceNodeId === c.nodeId && data.rowKey === targetPkey) return;
        genro.publish(c.actionTopic, {
            action: 'move',
            rowKey: data.rowKey,
            sourceNodeId: data.sourceNodeId,
            position: '>' + targetPkey
        });
    }

    // Chip bridge: plain DOM, no sourceNode kwargs. Wraps dragstart/over/
    // leave/end/drop so cross-grid drag with tiles uses the same dropType.

    chipDragStart(e, chipDom, pkey) {
        const c = this.controller;
        const dropType = this.dropType();
        try {
            genro.dom.setInDataTransfer(e.dataTransfer, dropType,
                {rowKey: pkey, sourceNodeId: c.nodeId});
            e.dataTransfer.setData('text/plain', pkey);
            e.dataTransfer.effectAllowed = 'move';
        } catch (err) {}
        try {
            const aux = document.getElementById('auxDragImage');
            if (aux) {
                const clone = chipDom.cloneNode(true);
                clone.classList.remove('draggedItem',
                    'canBeDropped', 'cannotBeDropped',
                    'grouplet_grid_just_dropped');
                clone.style.width = chipDom.offsetWidth + 'px';
                aux.appendChild(clone);
                const rect = chipDom.getBoundingClientRect();
                e.dataTransfer.setDragImage(clone,
                    e.clientX - rect.left,
                    e.clientY - rect.top);
                setTimeout(function() {
                    if (clone.parentNode) clone.parentNode.removeChild(clone);
                }, 0);
            }
        } catch (err) {}
        chipDom.classList.add('draggedItem');
        e.stopPropagation();
    }

    chipDragOver(e, chipDom) {
        const dropType = this.dropType();
        if (chipDom.classList.contains('draggedItem')) return;
        const types = e.dataTransfer.types || [];
        let isValid = false;
        for (let i = 0; i < types.length; i++) {
            if (types[i] === dropType) { isValid = true; break; }
        }
        if (!isValid) {
            e.dataTransfer.dropEffect = 'none';
            chipDom.classList.add('cannotBeDropped');
            return;
        }
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        chipDom.classList.add('canBeDropped');
    }

    chipDragLeave(e, chipDom) {
        if (!chipDom.contains(e.relatedTarget)) {
            chipDom.classList.remove('canBeDropped', 'cannotBeDropped');
        }
    }

    chipDragEnd(chipDom) {
        chipDom.classList.remove('draggedItem',
            'canBeDropped', 'cannotBeDropped');
    }

    chipDrop(e, chipDom, pkey) {
        const dropType = this.dropType();
        chipDom.classList.remove('canBeDropped', 'cannotBeDropped');
        const data = genro.dom.getFromDataTransfer(e.dataTransfer, dropType);
        if (!data) return;
        e.preventDefault();
        this.onDrop(data, pkey);
    }
};


// ============================================================================
//  GroupletDataStore — widget data model
// ============================================================================
//
// Single funnel between the controller and the rows Bag. The controller
// never touches `genro.getData(storepath)` / `bag.popNode` / `bag.setItem`
// directly; it talks to `this.dataStore.X()`.
//
// Phase 1 (current): mode 'internal' only — wraps the storepath Bag.
// Filter/sort/lock/changes APIs are stubbed with console.warn so callers
// that creep in early are visible.
//
// Phase 2 will add mode 'proxy' (sibling BagStore / ValuesBagRows) and
// 'adapter' (AttributesBagRows / dataSelection). The controller-facing
// surface stays the same; only the dispatch internals change.
//
// See docs/groupletgrid_store_integration.html for the full design.

gnr.GroupletDataStore = class GroupletDataStore {

    constructor(controller, kw) {
        this.controller = controller;
        this.storepath = kw.storepath;
        this.identifier = kw.identifier || null;
        this._filtered = null;
        this._sortedBy = null;
    }

    // === Read ===

    bag() {
        return genro.getData(this.storepath);
    }

    ensureBag() {
        // Nested grids inside a freshly-created parent record may have
        // no rows Bag yet; materialise it on demand.
        let b = this.bag();
        if (!(b instanceof gnr.GnrBag)) {
            b = new gnr.GnrBag();
            genro.setData(this.storepath, b);
        }
        return b;
    }

    getNodes() {
        // Phase 1: forwards bag().getNodes() (visual order == Bag order).
        // Phase 2 will apply `_filtered` / sort transparently — same
        // convention as gnr.Grid using storebag().getNodes() throughout.
        const b = this.bag();
        return (b instanceof gnr.GnrBag) ? b.getNodes() : [];
    }

    rowNode(rowKey) {
        const b = this.bag();
        return (b instanceof gnr.GnrBag) ? b.getNode(rowKey) : null;
    }

    rowValue(rowKey) {
        const b = this.bag();
        return (b instanceof gnr.GnrBag) ? b.getItem(rowKey) : null;
    }

    rowField(rowKey, field) {
        return genro.getData(this.storepath + '.' + rowKey + '.' + field);
    }

    rowByIndex(idx) {
        const nodes = this.getNodes();
        const n = nodes[idx];
        if (!n) return null;
        const v = n.getValue();
        return v instanceof gnr.GnrBag ? v.asDict() : {};
    }

    len() {
        const b = this.bag();
        return (b instanceof gnr.GnrBag) ? b.len() : 0;
    }

    keyForRow(rowKey) {
        return rowKey;
    }

    indexOfKey(rowKey) {
        const b = this.bag();
        return (b instanceof gnr.GnrBag && b.index) ? b.index(rowKey) : -1;
    }

    // === Mutate ===

    addRow(rowKey, data, position) {
        const dataBag = this.ensureBag();
        const rowBag = new gnr.GnrBag();
        const merged = objectUpdate({}, data || {});
        Object.keys(merged).forEach((k) => rowBag.setItem(k, merged[k]));
        if (!position) {
            dataBag.setItem(rowKey, rowBag);
            return;
        }
        const first = position.charAt(0);
        const hasSign = (first === '<' || first === '>');
        const sign = hasSign ? first : '>';
        const targetKey = hasSign ? position.substring(1) : position;
        dataBag.setItem(rowKey, rowBag, null, {_position: sign + targetKey});
    }

    removeRow(rowKey) {
        const b = this.bag();
        if (b instanceof gnr.GnrBag) b.popNode(rowKey);
    }

    deleteRowAsk(rowKey) {
        const that = this;
        genro.dlg.ask(
            _T('!!Delete this row?'),
            _T('!!This row will be removed. Continue?'),
            {confirm: _T('!!Delete'), cancel: _T('!!Cancel')},
            {confirm: () => that.controller._doDeleteItem(rowKey)}
        );
    }

    moveRow(rowKey, position) {
        // Splice the Bag's _nodes array in place: no del/ins triggers
        // fire, so nested widgets whose datapath is anchored to the
        // moved row (e.g. inner groupletGrids on `.contacts`) keep a
        // valid parent chain. DOM mirroring is the controller's job.
        if (typeof position !== 'string') return null;
        const op = position.charAt(0);
        if (op !== '<' && op !== '>') return null;
        const targetKey = position.slice(1);
        const bag = this.bag();
        if (!(bag instanceof gnr.GnrBag)) return null;
        const nodes = bag._nodes;
        const fromIdx = nodes.findIndex((n) => n.label === rowKey);
        const targetIdx = nodes.findIndex((n) => n.label === targetKey);
        if (fromIdx < 0 || targetIdx < 0 || fromIdx === targetIdx) return null;
        const [moved] = nodes.splice(fromIdx, 1);
        let insertAt = nodes.findIndex((n) => n.label === targetKey);
        if (op === '>') insertAt += 1;
        nodes.splice(insertAt, 0, moved);
        return {op: op, targetKey: targetKey};
    }

    moveRowFrom(srcStore, srcKey, position, forceKey) {
        // Cross-grid migration. `forceKey` lets the caller pre-commit
        // the destination key (so e.g. _pendingFlash can be set before
        // the setItem trigger fires _renderTile).
        const sourceBag = srcStore.bag();
        const targetBag = this.ensureBag();
        const node = sourceBag.getNode(srcKey);
        if (!node) return null;
        const rowValue = node.getValue();
        const rowAttrs = node.getAttr() || {};
        let targetRowKey = forceKey || srcKey;
        if (!forceKey && targetBag.getNode(targetRowKey)) {
            targetRowKey = genro.time36Id();
        }
        sourceBag.popNode(srcKey);
        const setKw = position ? {_position: position} : {};
        targetBag.setItem(targetRowKey, rowValue, rowAttrs, setKw);
        return targetRowKey;
    }

    updateRow(rowKey, dict) {
        // Grid-store-shaped `updateRowNode`: patch N fields atomically
        // with `editedRowIndex` in the doTrigger so the changeManager's
        // rowLogger can cascade formula/totalize recalcs.
        const rowNode = this.rowNode(rowKey);
        if (!rowNode) return;
        const rowData = rowNode.getValue();
        if (!(rowData instanceof gnr.GnrBag)) return;
        const idx = this.indexOfKey(rowKey);
        for (const k in dict) {
            if (!rowData.getNode(k, 'static')) {
                rowData.setItem(k, null, null, {doTrigger: false});
            }
            rowData.setItem(k, dict[k], null,
                {doTrigger: {editedRowIndex: idx}, lazySet: true});
        }
    }

    // === GridChangeManager bridge (store-shaped wrapper) ===
    // The literal `collectionStore()` used to expose exactly these names;
    // keeping them lets `cmGrid.collectionStore = () => this.dataStore`
    // drop in unchanged.

    updateRowNode(rowNode, updDict) {
        if (!rowNode) return;
        this.updateRow(rowNode.label, updDict);
    }

    sum(field, strict) {
        const b = this.bag();
        return (b instanceof gnr.GnrBag) ? b.sum(field, strict) : 0;
    }

    getIdxFromPkey(pkey) {
        return this.indexOfKey(pkey);
    }

    // === Phase 2 stubs — visible if any path uses them today ===

    setFilter(_cb) {
        console.warn('[GroupletDataStore] setFilter() — Phase 2');
    }

    clearFilter() {
        console.warn('[GroupletDataStore] clearFilter() — Phase 2');
    }

    setSort(_spec) {
        console.warn('[GroupletDataStore] setSort() — Phase 2');
    }

    clearSort() {
        console.warn('[GroupletDataStore] clearSort() — Phase 2');
    }

    isFiltered() {
        return false;
    }

    refresh() {
        // no-op until filter/sort state exists
    }

    hasChanges() {
        console.warn(
            '[GroupletDataStore] hasChanges() requires an external '
            + 'store (Phase 2)');
        return false;
    }

    hasErrors() {
        console.warn(
            '[GroupletDataStore] hasErrors() requires an external '
            + 'store (Phase 2)');
        return false;
    }

    setLocked(_v) {
        console.warn(
            '[GroupletDataStore] setLocked() requires an external '
            + 'store (Phase 2)');
    }

    isLocked() {
        return false;
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
        this.bodyNode = kw.bodyNode || null;
        this.addBtnDom = null;
        this.tabbarDom = null;
        this.tabstripDom = null;
        this.nodeId = sourceNode.attr.nodeId;
        this.storepath = sourceNode.absDatapath(sourceNode.attr.storepath);
        this.resource = kw.resource || null;
        this.resourceField = kw.resourceField || null;
        this.structpath = kw.structpath || null;
        this.structAdapter = null;
        this.handler = kw.handler || null;
        this.table = kw.table || null;
        this.grouplets_root = kw.grouplets_root;
        this.grouplet_kw = kw.grouplet_kw || {};
        this.cols = kw.cols || 1;
        this.minWidth = kw.min_width || null;
        this.gap = kw.gap || '12px';
        this.additem = (kw.additem !== false);
        this.delitem = (kw.delitem === true);
        this.editmenu = (kw.editmenu === undefined) ? false : kw.editmenu;
        this.additemKw = kw.additem_kw || {};
        this.delitemKw = kw.delitem_kw || {};
        this.editmenuKw = kw.editmenu_kw || {};
        this.defaultRow = kw.defaultRow;
        this.minRows = kw.minRows || 0;
        this.maxRows = kw.maxRows || null;
        this.counterField = kw.counterField || null;
        this.dragCode = kw.dragCode || null;
        this.dnd = this.dragCode ? new gnr.GroupletGridDnD(this) : null;
        this.dataStore = new gnr.GroupletDataStore(this, {
            storepath: this.storepath,
            identifier: kw.identifier || null
        });
        this._chipDnDHandlers = {};
        this.layout = kw.layout || 'cards';
        this.titleField = kw.titleField || null;
        this.emptyTitle = kw.emptyTitle || _T('!!Untitled');
        this.activePkey = null;
        this._tabsByPkey = {};
        this._pendingActivate = null;
        this.templateSources = {};
        this.templateLoading = {};
        this.cellmap = {};
        this._changeMgr = null;
        this._cmNeedsBag = false;
        this.tiles = {};
        this._destroyed = false;
        this.actionTopic = 'groupletGrid_' + this.nodeId + '_action';
        this._applyResponsiveLayout();
        this._applySlotClasses();
        this._registerActionSubscription();
        this._buildLayoutAffordances();
        this._initChangeManager();
        const that = this;
        dojo.connect(sourceNode, '_onDeleting', function() { that.destroy(); });
        // The first container build emits no 'storepath' trigger, so we
        // seed the initial render here; later mutations flow through
        // `gnr_storepath`.
        this.newDataStore();
        this._updateAddBtnState();
    }

    destroy() {
        if (this._destroyed) return;
        this._destroyed = true;
        this.sourceNode.unregisterSubscription(this.actionTopic);
        Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
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
        return this.dataStore.bag();
    }

    _containerDom() {
        return this.sourceNode.getDomNode();
    }

    collectionStore() {
        // GridChangeManager expects a store-shaped object with
        // updateRowNode / sum / getIdxFromPkey / rowByIndex; the
        // dataStore exposes exactly these names.
        return this.dataStore.bag() ? this.dataStore : null;
    }

    rowFromBagNode(rowNode, _includeAttrs) {
        // Row fields live in the sub-Bag (the value), not in attrs:
        // `setItem(pkey, Bag(dict(qty=..., price=...)))` is the
        // canonical seeding shape and formulas need them as plain keys.
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
    //  Struct chrome — adapter wiring, header/footer mounting,
    //  cross-track alignment, public mutation API
    // ====================================================================

    _initStructAdapter() {
        // structpath may be a typed path (`#WORKSPACE.struct`); only
        // `getRelativeData` honours those, `genro.getData` doesn't.
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
        this._initStructAdapter();
        this.datamode = 'bag';
        this.structBag = this.structAdapter ? this.structAdapter.struct : null;
        this._virtual = false;
        this.isFiltered = function() { return false; };
        this.getSelectedRowidx = function() { return []; };
        this.getSelectedNodes = function() { return []; };
        // sourceNode MUST be the container, not the body: totals are
        // written via setRelativeData, and on the body (whose datapath
        // is storepath) that would write inside the rows Bag and loop
        // through the rowLogger.
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
        // GridChangeManager.rowLogger attaches inside the onNewDatastore
        // callback; if the Bag is still null at this point, publishing
        // now would NPE. newDataStore publishes it once data is in.
        this._cmNeedsBag = true;
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
        if (!this.structAdapter) return;
        const containerDom = this._containerDom();
        containerDom.style.setProperty('--gg-struct-columns',
            this.structAdapter.columnsCSS());
        const slots = this._resolveStructSlots();
        if (slots.top) {
            this._mountSlotContent(slots.top,
                this.structAdapter.buildHeader(), 'struct_header');
            // Force `has-top`: _applySlotClasses reads slot.children which
            // may not reflect the just-grafted nodes yet.
            containerDom.classList.add('has-top');
        }
        const footer = this.structAdapter.buildFooter();
        if (slots.bottom && footer) {
            this._mountSlotContent(slots.bottom, footer, 'struct_footer');
            containerDom.classList.add('has-bottom');
        }
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
        // Idempotent populate of the server-emitted placeholder. Pop
        // existing children first so a struct mutation (applyStruct)
        // doesn't duplicate.
        const slotContent = slotNode.getValue();
        if (!(slotContent instanceof gnr.GnrDomSource)) return;
        const placeholder = slotContent.getNode(placeholderLabel);
        if (!placeholder) return;
        const placeholderContent = placeholder.getValue();
        if (!(placeholderContent instanceof gnr.GnrDomSource)) return;
        placeholderContent.getNodes().slice().forEach((n) => {
            placeholderContent.popNode(n.label);
        });
        // Skip the adapter's wrapper level: the placeholder IS that
        // wrapper, so we graft the wrapper's children directly.
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
        // Coalesce concurrent requests (resize + row-add + applyStruct)
        // into one measurement on the next animation frame.
        if (this._structSyncScheduled) return;
        this._structSyncScheduled = true;
        const that = this;
        requestAnimationFrame(function() {
            that._structSyncScheduled = false;
            that._syncStructChromeToColumns();
        });
    }

    _syncStructChromeToColumns() {
        // STEP 1: stretch header/footer padding so their content-box
        // matches the row's inner grid (header lives in slot-top,
        // outside the row's drag/kebab insets — different absolute X).
        // STEP 2: per-column padding so header label / readonly cell
        // align to the row widget's visible text edge.
        if (!this.structAdapter) return;
        const containerDom = this._containerDom();
        const firstRow = containerDom.querySelector(
            '.grouplet_grid_body .grouplet_grid__struct_row');
        if (!firstRow) return;
        // Single pass stamps the col_cell marker (some widgets wrap
        // themselves so the supplied class lands on an inner node),
        // collects readonly cells per column, and captures firstRow's
        // tracks for the per-column step.
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
        // --- STEP 1: frame header/footer onto firstRow's content-box.
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
        // --- STEP 2: place header/footer cells absolutely at the same
        // left/width as the row's column wrappers (decouples from grid
        // track resolution / font-size scaling). Readonly row cells keep
        // grid placement; only their internal padding is tuned.
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
            // Text-edge inset: wrapper-edge → widget-text-edge.
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
            (readonlyByColumn[i] || []).forEach(function(el) {
                el.style.paddingLeft = '';
                el.style.paddingRight = '';
                if (align === 'right') el.style.paddingRight = rightInset + 'px';
                else if (align === 'left') el.style.paddingLeft = leftInset + 'px';
            });
        });
    }

    applyStruct(newStruct) {
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
        // Called on construct, on whole-Bag swap, and on record load.
        // Publishes onNewDatastore (GridChangeManager.rowLogger attaches
        // there) only once the Bag is materialised, to avoid the NPE.
        const bag = this.storebag();
        const hasBag = (bag instanceof gnr.GnrBag);
        if (hasBag && this._cmNeedsBag && this._changeMgr) {
            this._cmNeedsBag = false;
        }
        if (hasBag) {
            this.sourceNode.publish('onNewDatastore');
        }
        if (!hasBag || bag.len() === 0) {
            Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
            return;
        }
        this.updateCounterColumn();
        this._ensureTemplate(() => this._fullSync());
    }

    gnr_storepath(value, kw, trigger_reason) {
        // Single entry point for storepath-bound mutations. Wired in
        // grouplet.py via `registerDynAttr('storepath')` + framework
        // dyn-attr dispatch (gnrdomsource.js:1357-1363).
        // parentshipLevel discriminates:
        //   < 0: ancestor swap (record load) → newDataStore
        //   = 0: rows Bag replaced            → newDataStore
        //   = 1: whole row add/remove
        //   > 1: intra-row mutation — widgets self-bind; we only
        //        intervene for the tabs chip label (plain DOM).
        if (!kw || kw.reason === 'autocreate') return;
        const storeBag = this.storebag();
        const storeNode = storeBag && storeBag.getParentNode();
        if (!kw.node) return;
        const parent_lv = storeNode
            ? kw.node.parentshipLevel(storeNode)
            : 0;
        if (parent_lv <= 0) {
            this.newDataStore();
            return;
        }
        if (parent_lv > 1) {
            if (this._isTabsLayout() && this.titleField) {
                this._maybeRefreshTabLabel(kw.node, storeNode);
            }
            return;
        }
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
        // Walk up to the row-level node, then check the mutated leaf
        // path equals exactly `titleField` (filter out nested noise).
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
                const titleDom = chip && chip.querySelector(
                    ':scope > .grouplet_grid_tab_title');
                if (titleDom) {
                    titleDom.textContent = this._readTabLabel(cur.label);
                }
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

    _applyResponsiveLayout() {
        if (!(this.minWidth && this.cols > 1)) return;
        const container = this._containerDom();
        container.style.setProperty('--gg-cols', String(this.cols));
        container.style.setProperty('--gg-min-width', this.minWidth);
        container.style.setProperty('--gg-gap', this.gap);
        container.classList.add('grouplet_grid_responsive');
    }

    _applySlotClasses() {
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
        containerDom.classList.remove(
            'grouplet_grid--tabs', 'grouplet_grid--vtabs');
        if (this._isTabsLayout()) {
            containerDom.classList.add('grouplet_grid--tabs');
            if (this.layout === 'vtabs') {
                containerDom.classList.add('grouplet_grid--vtabs');
            }
            this._buildTabbar(containerDom);
            // Re-add chips for rows that already exist (setLayout entry).
            Object.keys(this.tiles).forEach((pkey) => {
                this._addTabChip(pkey);
            });
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
        // Drop the layout chrome only; row wrappers and their widgets
        // survive across a setLayout swap.
        if (this.addBtnDom && this.addBtnDom.parentNode) {
            this.addBtnDom.parentNode.removeChild(this.addBtnDom);
        }
        this.addBtnDom = null;
        Object.keys(this._tabsByPkey).forEach((pkey) => {
            if (this.dragCode) this._unwireTabDnD(pkey);
        });
        if (this.tabbarDom && this.tabbarDom.parentNode) {
            this.tabbarDom.parentNode.removeChild(this.tabbarDom);
        }
        this.tabbarDom = null;
        this.tabstripDom = null;
        this._tabsByPkey = {};
        Object.keys(this.tiles).forEach((pkey) => {
            const dom = this.tiles[pkey].domNode();
            if (dom) dom.classList.remove('grouplet_grid_tab_active');
        });
    }

    setLayout(newLayout) {
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
            this.activePkey = prevActive;
        }
        this._buildLayoutAffordances();
    }

    _buildCardsFooter(containerDom) {
        // Appended to the container (grid-area `addbtn`), NOT to the
        // body — otherwise row rendering inside the body would touch it.
        if (!this.additem) return;
        const btn = document.createElement('div');
        btn.className = 'grouplet_grid_footer';
        btn.setAttribute('title', _T('!!Add row'));
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
        // Plain DOM, not a sourceNode subtree: mutating the container's
        // Bag during init would recurse into buildNode and reset the
        // framework's afterBuildCalls drain.
        const tabbar = document.createElement('div');
        tabbar.className = 'grouplet_grid_tabbar';
        const strip = document.createElement('div');
        strip.className = 'grouplet_grid_tabs';
        tabbar.appendChild(strip);
        if (this.additem) {
            const addBtn = document.createElement('div');
            addBtn.className = 'grouplet_grid_tab_add';
            addBtn.setAttribute('title', _T('!!Add row'));
            const that = this;
            addBtn.addEventListener('click', function() {
                genro.publish(that.actionTopic, {action: 'add'});
            });
            tabbar.appendChild(addBtn);
            this.addBtnDom = addBtn;
        }
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

    _addTabChip(pkey) {
        if (!this.tabstripDom) return;
        if (this._tabsByPkey[pkey]) return;
        const that = this;
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
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                genro.publish(that.actionTopic,
                    {action: 'delete', rowKey: pkey});
            });
            chip.appendChild(closeBtn);
        }
        chip.addEventListener('click', function() {
            that._activateTab(pkey);
        });
        // Insert before the next mounted sibling chip (Bag order).
        let inserted = false;
        const allKeys = this.dataStore.getNodes().map((n) => n.label);
        const idx = allKeys.indexOf(pkey);
        for (let j = idx + 1; j < allKeys.length; j++) {
            if (this._tabsByPkey[allKeys[j]]) {
                this.tabstripDom.insertBefore(
                    chip, this._tabsByPkey[allKeys[j]]);
                inserted = true;
                break;
            }
        }
        if (!inserted) this.tabstripDom.appendChild(chip);
        this._tabsByPkey[pkey] = chip;
        if (this.dragCode) {
            this._wireTabDnD(chip, pkey);
        }
    }

    _removeTabChip(pkey) {
        const chip = this._tabsByPkey[pkey];
        if (!chip) return;
        if (this.dragCode) this._unwireTabDnD(pkey);
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
        genro.publish(this.actionTopic,
            {action: 'activate', rowKey: pkey});
    }

    _setActiveTabClasses(activePkey) {
        // Toggles `.grouplet_grid_tab_active` on every chip and every row
        // wrapper. Idempotent: safe to call on every render / activation.
        Object.keys(this._tabsByPkey).forEach((rk) => {
            const chip = this._tabsByPkey[rk];
            if (!chip) return;
            chip.classList.toggle(
                'grouplet_grid_tab_active', rk === activePkey);
        });
        Object.keys(this.tiles).forEach((rk) => {
            const dom = this.tiles[rk].domNode();
            if (dom) {
                dom.classList.toggle(
                    'grouplet_grid_tab_active', rk === activePkey);
            }
        });
    }

    _wireTabDnD(chipDom, pkey) {
        // Chip is plain DOM, so DnD goes through native listeners that
        // forward to gnr.GroupletGridDnD (same payload + same move
        // dispatch as the declarative tile path → cross-grid works).
        const dnd = this.dnd;
        chipDom.setAttribute('draggable', 'true');
        const onDragStart = (e) => dnd.chipDragStart(e, chipDom, pkey);
        const onDragOver = (e) => dnd.chipDragOver(e, chipDom);
        const onDragLeave = (e) => dnd.chipDragLeave(e, chipDom);
        const onDragEnd = () => dnd.chipDragEnd(chipDom);
        const onDrop = (e) => dnd.chipDrop(e, chipDom, pkey);
        chipDom.addEventListener('dragstart', onDragStart);
        chipDom.addEventListener('dragover', onDragOver);
        chipDom.addEventListener('dragleave', onDragLeave);
        chipDom.addEventListener('dragend', onDragEnd);
        chipDom.addEventListener('drop', onDrop);
        this._chipDnDHandlers[pkey] = {
            dom: chipDom,
            handlers: {dragstart: onDragStart, dragover: onDragOver,
                       dragleave: onDragLeave, dragend: onDragEnd,
                       drop: onDrop}
        };
    }

    _unwireTabDnD(pkey) {
        const entry = this._chipDnDHandlers && this._chipDnDHandlers[pkey];
        if (!entry) return;
        Object.keys(entry.handlers).forEach((evt) => {
            entry.dom.removeEventListener(evt, entry.handlers[evt]);
        });
        delete this._chipDnDHandlers[pkey];
    }

    // ====================================================================
    //  Action dispatch — single subscription routes every action
    // ====================================================================

    _registerActionSubscription() {
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
                // Toolbar '−' buttons omit rowKey; fall back to selection.
                const pkey = payload.rowKey || this.selectedPkey;
                if (!pkey) return;
                this._askAndDeleteItem(pkey);
                break;
            }
            case 'move': {
                const src = payload.sourceNodeId;
                if (src && src !== this.nodeId) {
                    const sourceCtrl = this._findSourceController(src);
                    if (sourceCtrl) {
                        this._doMoveTileFrom(sourceCtrl, payload.rowKey,
                                             payload.position);
                    }
                } else {
                    this._doMoveTile(payload.rowKey, payload.position);
                }
                break;
            }
        }
    }

    // ====================================================================
    //  DnD move dispatch — see gnr.GroupletGridDnD at the top of file.
    // ====================================================================

    _doMoveTile(pkey, position) {
        // dataStore.moveRow splices the Bag's _nodes in place (no del/ins
        // triggers) so nested widgets keep a valid datapath chain; the
        // tile/chip DOM is mirrored here.
        const move = this.dataStore.moveRow(pkey, position);
        if (!move) return;
        const op = move.op;
        const targetKey = move.targetKey;
        // Move the tile DOM in the body to mirror the new Bag order.
        const movedDom = this.tiles[pkey] && this.tiles[pkey].domNode();
        if (movedDom && movedDom.parentNode) {
            const bodyDom = movedDom.parentNode;
            const targetDom = this.tiles[targetKey]
                && this.tiles[targetKey].domNode();
            if (targetDom) {
                const ref = (op === '>')
                    ? targetDom.nextSibling
                    : targetDom;
                bodyDom.insertBefore(movedDom, ref);
            }
        }
        // Tabs mode: move the chip in lockstep.
        const movedChip = this._tabsByPkey[pkey];
        const targetChip = this._tabsByPkey[targetKey];
        if (movedChip && targetChip && movedChip.parentNode) {
            const ref = (op === '>')
                ? targetChip.nextSibling
                : targetChip;
            movedChip.parentNode.insertBefore(movedChip, ref);
        }
        this.updateCounterColumn();
        if (this.tiles[pkey]) this.tiles[pkey].flash();
    }

    _findSourceController(sourceNodeId) {
        const node = genro.nodeById(sourceNodeId);
        return (node && node.gridController) || null;
    }

    _doMoveTileFrom(sourceCtrl, sourceRowKey, targetPosition) {
        // Cross-instance migration. The guard catches the browser quirk
        // where a self-drop is misrouted to the source controller.
        if (sourceCtrl === this) return;
        // Pre-commit the target key so _pendingFlash is set before the
        // setItem trigger fires _renderTile.
        const targetBag = this.dataStore.bag();
        const targetRowKey = (targetBag && targetBag.getNode(sourceRowKey))
            ? genro.time36Id() : sourceRowKey;
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[targetRowKey] = true;
        this.dataStore.moveRowFrom(
            sourceCtrl.dataStore, sourceRowKey, targetPosition, targetRowKey);
    }

    _flashTile(pkey) {
        // Defer one tick: this may fire ahead of _renderTile finishing.
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
        const presentKeys = {};
        const toAdd = [];
        this.dataStore.getNodes().forEach((node) => {
            presentKeys[node.label] = true;
            if (!this.tiles[node.label]) toAdd.push(node.label);
        });
        Object.keys(this.tiles).forEach((pkey) => {
            if (!presentKeys[pkey]) this._destroyTile(pkey);
        });
        if (toAdd.length === 0) return;
        // Pre-decide the active tab so its wrapper mounts with
        // display:block: otherwise nested groupletGrids inside hidden
        // tabs would build their body subtree while detached from layout
        // and miscalculate their geometry.
        if (this._isTabsLayout() && !this.activePkey && toAdd.length > 0) {
            this.activePkey = toAdd[0];
        }
        this.bodyNode.freeze();
        toAdd.forEach((pkey) => this._renderTile(pkey));
        this.bodyNode.unfreeze();
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
        // Insert before the next already-mounted sibling, else append.
        // Works uniformly for all sources of 'ins' (action handlers,
        // DnD, external setItem).
        const allKeys = this.dataStore.getNodes().map((n) => n.label);
        const idx = allKeys.indexOf(pkey);
        for (let j = idx + 1; j < allKeys.length; j++) {
            if (this.tiles[allKeys[j]]) {
                return '<_grtile_' + allKeys[j];
            }
        }
        return undefined;
    }

    _afterTileMounted(tile) {
        const pkey = tile.pkey;
        this._updateAddBtnState();
        if (this._isTabsLayout()) {
            this._addTabChip(pkey);
            // A tile added via the `+` button becomes active immediately
            // (same UX as opening a new browser tab).
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
        // _pendingFlash is set by _doMoveTile* before the Bag mutation
        // so the just-landed tile can flash on first paint.
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
        if (this._isTabsLayout()) {
            // Pre-compute next active before removing the current chip.
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
    //  Public action API — thin publishers on the action bus
    // ====================================================================

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
        const newKey = 'r_' + genro.time36Id();
        // Tabs: the row's _renderTile runs from the gnr_storepath
        // trigger below; _afterTileMounted clears _pendingActivate.
        if (this._isTabsLayout()) this._pendingActivate = newKey;
        const merged = objectUpdate({}, this.defaultRow || {});
        objectUpdate(merged, defaults || {});
        this.dataStore.addRow(newKey, merged, position);
    }

    _askAndDeleteItem(pkey) {
        this.dataStore.deleteRowAsk(pkey);
    }

    _doDeleteItem(pkey) {
        if (this._rowCount() <= this.minRows) return;
        this.dataStore.removeRow(pkey);
        if (this.selectedPkey === pkey) {
            this.selectedPkey = null;
        }
    }

    selectTile(pkey) {
        // Tabs/vtabs use the active state; .selected is a cards-only
        // UX class that conflicts with the panel chrome here.
        if (this._isTabsLayout()) return;
        if (this.selectedPkey === pkey) return;
        if (this.selectedPkey && this.tiles[this.selectedPkey]) {
            const prevDom = this.tiles[this.selectedPkey].domNode();
            if (prevDom) prevDom.classList.remove('selected');
        }
        this.selectedPkey = pkey;
        const dom = this.tiles[pkey] && this.tiles[pkey].domNode();
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
        // Suffix only the framework-generated `grpgrid_*` nodeIds so
        // each row instance is unique on the action bus
        // (`groupletGrid_<nodeId>_action`). Author-supplied nodeIds are
        // left as is.
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
        // key = '__default__' for single-template grids, otherwise the
        // sanitised resourceField value (multi-grouplet mode).
        key = key || '__default__';
        if (this.templateSources[key]) {
            callback();
            return;
        }
        // resourceField mode: a single RPC preloads every template under
        // the table's folder, so all keys share one loading queue.
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
        if (this.structAdapter) {
            this.templateSources[key] = this.structAdapter.buildRowTemplate();
            flush();
            return;
        }
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
        // Key = sanitised resource_path ('/' → '_'), matching the server
        // keying in gr_getGroupletGridTemplateMap.
        if (!this.resourceField) return '__default__';
        const rowValue = this.dataStore.rowValue(pkey);
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


// One GroupletGridTile per pkey in controller.tiles. Owns wrapper +
// chrome + body. Lifecycle is driven by controller._renderTile /
// _destroyTile from the gnr_storepath dispatcher.

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
        this._mountDragHandle();
        this._mountChrome();
        this._mountBody();
        this.tileNode.unfreeze();
        this.mounted = true;
    }

    rebuild() {
        // Re-render body + chrome in place (used on resourceField swap):
        // wrapper sourceNode and drag handle survive.
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
        dom.classList.add('grouplet_grid_just_dropped');
        setTimeout(() => {
            if (this.tileDom) {
                this.tileDom.classList.remove('grouplet_grid_just_dropped');
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
        // Pre-stamp the active class so the wrapper mounts with
        // display:block in tabs mode (nested widgets need layout).
        const c = this.controller;
        const pkey = this.pkey;
        const tile = this;
        let tileClass = 'grouplet_grid_row';
        if (c._isTabsLayout() && c.activePkey === pkey) {
            tileClass += ' grouplet_grid_tab_active';
            this.isActive = true;
        }
        const tileKw = {
            datapath: '.' + pkey,
            _class: tileClass,
            nodeId: this.tileNodeId,
            connect_onclick: function() { c.selectTile(pkey); }
        };
        // Tile is a drop target only in cards/struct layout — in tabs
        // mode the row's panel is the active content area, the drop
        // belongs to the chip strip above.
        if (this.dragEnabled && !c._isTabsLayout()) {
            const dropType = c.dnd.dropType();
            tileKw.dropTarget = true;
            tileKw.dropTypes = dropType;
            // selfdrop fires here because dnd.onDrag rewrote
            // dragInfo.nodeId to the tile's; returning false makes the
            // framework apply .cannotBeDropped and reject the drop.
            tileKw.dropTargetCb = function(dropInfo) {
                return !dropInfo.selfdrop;
            };
            tileKw['onDrop_' + dropType] = function(dropInfo, data) {
                c.dnd.onDrop(data, pkey);
            };
        }
        tileKw.onCreated = function(domnode) {
            tile.tileDom = domnode.sourceNode
                ? domnode.sourceNode.getDomNode()
                : domnode;
        };
        const bodyContent = c.bodyNode.getValue();
        const extraKw = this.position ? {_position: this.position} : undefined;
        bodyContent._('div', this.tileLabel, tileKw, extraKw);
        this.tileNode = bodyContent.getNode(this.tileLabel);
        this.tileContent = this.tileNode.getValue();
    }

    _mountDragHandle() {
        // `⠿` drag source as a child sourceNode of the tile.
        if (!this.dragEnabled) return;
        const c = this.controller;
        const pkey = this.pkey;
        const tile = this;
        const dropType = c.dnd.dropType();
        const handleLabel = '_grtile_drag_' + pkey;
        this.tileContent._('div', handleLabel, {
            _class: 'grouplet_grid_row_drag',
            draggable: true,
            title: _T('!!Drag to reorder'),
            innerHTML: '<span class="grouplet_grid_drag_icon">⠿</span>',
            ['onDrag_' + dropType]: function(dragValues, dragInfo) {
                c.dnd.onDrag(dragInfo, dragValues, pkey, tile.tileNodeId);
            }
        });
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
            delKw._class = 'grouplet_grid_row_delete '
                         + c.delitemKw._class;
        }
        this.tileContent._('div', '_grtile_del_' + pkey, delKw);
        const delNode = this.tileContent.getNode('_grtile_del_' + pkey);
        delNode.getValue()._('div', 'glyph', {innerHTML: '×'});
    }

    _mountKebab() {
        // editmenu = {entryKey: True | 'label' | {label,action,...}}.
        // True = preset (addPrev/addNext/delete), string overrides the
        // label, dict shallow-merges over the preset.
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
        // Each tile owns its own template clone; framework-generated
        // nodeIds are namespaced (see _namespaceFrameworkNodeIds).
        const cloned = this.templateSource.deepCopy();
        this.controller._namespaceFrameworkNodeIds(cloned, this.pkey);
        cloned.getNodes().forEach((n) => {
            this.controller._graftNode(this.tileContent, n);
        });
    }

    _destroyBody() {
        // Pop everything except the chrome children.
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
