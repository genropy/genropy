// groupletGrid — JS classes on gnr.*:
//   GroupletGridStructAdapter, GroupletGridDnD,
//   GroupletGridController, GroupletGridTile.

// Attribute keys whose value may carry a framework-generated
// `grpgrid_*` reference, rewritten per-row clone by
// `_namespaceFrameworkNodeIds`.
const NAMESPACED_ATTRS = ['nodeId', 'dragCode'];

gnr.GroupletGridStructAdapter = class GroupletGridStructAdapter {
    constructor(struct, controllerPath) {
        this.struct = struct;
        this.controllerPath = controllerPath;
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
        const ctrlPath = this.controllerPath;
        rows.getNodes().forEach(function(node) {
            const attr = node.attr || {};
            if (attr.hidden) return;
            //fieldcell on a foreign key emits caption_field as a relation
            //path ('@fk.<rowcaption>'): meaningful in a SQL selection,
            //unresolvable on a Bag store — always bind the real column
            const field = attr.field || attr.caption_field;
            if (!field) return;
            // Empty name='' means "no label"; only undefined falls back
            // to the field name.
            const hasName = (attr.name !== undefined && attr.name !== null);
            const totalize = (attr.totalize === true)
                ? ctrlPath + '.totalize.' + field
                : attr.totalize;
            out.push({
                _nodelabel: node.label,
                field: field,
                name: hasName ? attr.name : field,
                width: attr.width,
                min_width: attr.min_width,
                dtype: attr.dtype || 'T',
                edit: attr.edit,
                format: attr.format,
                totalize: totalize,
                totalize_strict: attr.totalize_strict,
                formula: attr.formula,
                related_table: attr.related_table,
                values: attr.values,
                validate_notnull: attr.validate_notnull,
                keepable: attr.keepable
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
        //   missing / '*' / '100%'  → minmax(0, 1fr)  (flex track),
        //                             minmax(min_width, 1fr) with a min_width
        //   anything else           passes through.
        // '100%' as a literal Grid track overflows and resolves with
        // per-container subpixel rounding — visible column drift across
        // header/row/footer; minmax(0, 1fr) is deterministic.
        // Auto-promote the widest fixed-em cell if no flex track exists,
        // otherwise the row centres while header/footer span full width.
        const FLEX = 'minmax(0, 1fr)';
        const flex = (c) => (c.min_width ? 'minmax(' + c.min_width + ', 1fr)' : FLEX);
        const tracks = this.cells.map(function(c) {
            const w = c.width;
            return (!w || w === '*' || w === '100%') ? flex(c) : w;
        });
        if (!tracks.some((t) => t.endsWith(' 1fr)'))) {
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

    buildHeader(keepPins, checkAll) {
        // Empty / whitespace-only labels render as &nbsp; to keep the
        // cell's line height (a bare space collapses in some layouts
        // and breaks header/row vertical alignment). With keepPins, a
        // `keepable` column carries the entry row's keeper as a pin;
        // checkAll adds the rows' select-all checkbox in the gutter.
        const root = genro.src.newRoot();
        const hdr = root._('div', {_class: 'grouplet_grid__struct_header'});
        if (checkAll) {
            hdr._('input', {type: 'checkbox', _class: 'grouplet_grid_check_all',
                            title: _T('!!Select all rows')});
        }
        const Adapter = gnr.GroupletGridStructAdapter;
        this.cells.forEach(function(c) {
            const align = Adapter._alignFor(c);
            const raw = c.name || '';
            const pin = (keepPins && c.keepable && c.keepable !== '*')
                ? '<span class="grouplet_grid__struct_keep" data-field="' + c.field
                    + '" title="' + _T('!!Keep this value') + '"></span>'
                : '';
            hdr._('div', {
                _class: 'grouplet_grid__struct_col_cell'
                    + ' grouplet_grid__struct_header_cell'
                    + ' grouplet_grid__struct_cell--align-' + align,
                innerHTML: ((raw.trim() === '') ? ' ' : raw) + pin
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

    buildRowTemplate(readonly, computed) {
        // Same sourceRoot shape the resource= flow produces, but
        // synthesised: widgets are direct children of the row (no
        // per-cell wrapper). Editable cells use the dtype→widget map
        // from gnr.Grid; readonly cells are plain divs with ^.field.
        // `readonly`: every cell is a readonly div (the template rows of
        // a struct grid with rowTemplate=True). `computed`: the fields
        // shown as read-only editors (the entry row's formulas).
        const root = genro.src.newRoot();
        const row = root._('div', {_class: 'grouplet_grid__struct_row'});
        const Adapter = gnr.GroupletGridStructAdapter;
        this.cells.forEach(function(c) {
            if (!readonly && computed && computed.indexOf(c.field) >= 0) {
                row._(genro.wdg.wdgByDtype(c.dtype), objectUpdate(
                    Adapter._editorKwargs(c), {readOnly: true, tabindex: -1}));
                return;
            }
            const tag = readonly ? null : Adapter._resolveWidgetTag(c);
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
            const format = c.format
                || (readonly ? gnr.GroupletGridStructAdapter.READONLY_FORMATS[c.dtype] : null);
            if (format) kw.format = format;
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
        return genro.wdg.wdgByDtype(c.dtype);
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
            error_label: c.name,
            keepable: c.keepable,
            ...editRest,
            _class: 'grouplet_grid__struct_col_cell'
                + (editClass ? ' ' + editClass : '')
        };
    }
};


// A readonly cell shows the value as text: these dtypes need a format to
// read like their editor (a bare Date prints its toString(); the date
// editor shows a four-digit year).
gnr.GroupletGridStructAdapter.READONLY_FORMATS = {
    B: 'tick',
    D: {format: 'short', fullYear: true},
    DH: 'short',
    DHZ: 'short'
};


gnr.GroupletGridDnD = class GroupletGridDnD {

    // DOM-pure HTML5 drag-and-drop dispatch shared by tile (cards/struct)
    // and chip (tabs/vtabs). Same payload key (`gg_tile_<dragCode>`),
    // same move dispatch (publishes 'move' on the controller's action
    // topic), so cross-grid drag tile↔chip works through one path.
    //
    // External contract (kept intentionally framework-compatible):
    //   - payload via `genro.dom.setInDataTransfer` with key
    //     `gg_tile_<dragCode>` and value `{rowKey, sourceNodeId}`
    //   - drop = "insert-after" (`>target`, aligned with the tree).
    //
    // Internals (this commit): all listeners are `addEventListener`s
    // wired on the rendered DOM — no sourceNode `dropTarget`/`onDrag_*`
    // kwargs anywhere. Symmetric to the chip path (test_8 nested) and
    // independent of framework-side pointer-events / inherited-attrs
    // resolution.

    constructor(controller) {
        this.controller = controller;
    }

    dropType() {
        return 'gg_tile_' + this.controller.dragCode;
    }

    _writePayload(dataTransfer, pkey) {
        const c = this.controller;
        try {
            genro.dom.setInDataTransfer(dataTransfer, this.dropType(),
                {rowKey: pkey, sourceNodeId: c.nodeId});
            dataTransfer.setData('text/plain', pkey);
            dataTransfer.effectAllowed = 'move';
        } catch (err) {}
    }

    _setDragImage(e, sourceDom, opts) {
        try {
            const aux = document.getElementById('auxDragImage');
            if (!aux || !sourceDom) return;
            const clone = sourceDom.cloneNode(true);
            clone.classList.remove('draggedItem', 'canBeDropped',
                'cannotBeDropped', 'grouplet_grid_just_dropped');
            clone.style.width = sourceDom.offsetWidth + 'px';
            if (opts && opts.struct) {
                // Struct chrome is on the container, the clone is not.
                // Tag it so the cell rules still apply outside the tree.
                clone.classList.add('grouplet_grid_struct_drag_clone',
                    'grouplet_grid--struct');
                const containerDom = this.controller._containerDom();
                const cols = containerDom.style.getPropertyValue(
                    '--gg-struct-columns');
                if (cols) clone.style.setProperty('--gg-struct-columns', cols);
            }
            aux.appendChild(clone);
            const rect = sourceDom.getBoundingClientRect();
            e.dataTransfer.setDragImage(clone,
                e.clientX - rect.left,
                e.clientY - rect.top);
            setTimeout(function() {
                if (clone.parentNode) clone.parentNode.removeChild(clone);
            }, 0);
        } catch (err) {}
    }

    _dataTransferHasOurType(dataTransfer) {
        const dropType = this.dropType();
        const types = dataTransfer.types || [];
        for (let i = 0; i < types.length; i++) {
            if (types[i] === dropType) return true;
        }
        return false;
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

    // === Tile (cards / struct) ===
    // The handle ⠿ is the drag source; the tile wrapper is the drop
    // zone. Stop propagation on dragstart so an outer tile (nested
    // grids) doesn't re-snapshot its own card.

    tileDragStart(e, tileDom, pkey) {
        this._writePayload(e.dataTransfer, pkey);
        const containerDom = this.controller._containerDom();
        const struct = containerDom.classList.contains(
            'grouplet_grid--struct');
        this._setDragImage(e, tileDom, {struct: struct});
        tileDom.classList.add('draggedItem');
        document.body.classList.add('drag_started');
        e.stopPropagation();
    }

    tileDragEnd(tileDom) {
        tileDom.classList.remove('draggedItem',
            'canBeDropped', 'cannotBeDropped');
        document.body.classList.remove('drag_started');
    }

    tileDragOver(e, tileDom) {
        if (tileDom.classList.contains('draggedItem')) {
            // Hovering the source tile itself: paint cannotBeDropped
            // briefly (selfdrop preview) but do NOT preventDefault, so
            // the drop won't fire on it.
            tileDom.classList.add('cannotBeDropped');
            return;
        }
        if (!this._dataTransferHasOurType(e.dataTransfer)) {
            // Foreign drag (different dragCode / unrelated payload):
            // leave the tile alone, let the event bubble to an outer
            // dropTarget that might handle it.
            return;
        }
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = 'move';
        tileDom.classList.add('canBeDropped');
    }

    tileDragLeave(e, tileDom) {
        if (!tileDom.contains(e.relatedTarget)) {
            tileDom.classList.remove('canBeDropped', 'cannotBeDropped');
        }
    }

    tileDrop(e, tileDom, pkey) {
        tileDom.classList.remove('canBeDropped', 'cannotBeDropped');
        const data = genro.dom.getFromDataTransfer(
            e.dataTransfer, this.dropType());
        if (!data) return;
        e.preventDefault();
        e.stopPropagation();
        this.onDrop(data, pkey);
    }

    // === Chip (tabs / vtabs) ===
    // Same shape as the tile path. Chips never carry inner widgets,
    // so the dragover logic is simpler — no struct clone tag.

    chipDragStart(e, chipDom, pkey) {
        this._writePayload(e.dataTransfer, pkey);
        this._setDragImage(e, chipDom);
        chipDom.classList.add('draggedItem');
        document.body.classList.add('drag_started');
        e.stopPropagation();
    }

    chipDragOver(e, chipDom) {
        if (chipDom.classList.contains('draggedItem')) return;
        if (!this._dataTransferHasOurType(e.dataTransfer)) {
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
        document.body.classList.remove('drag_started');
    }

    chipDrop(e, chipDom, pkey) {
        chipDom.classList.remove('canBeDropped', 'cannotBeDropped');
        const data = genro.dom.getFromDataTransfer(
            e.dataTransfer, this.dropType());
        if (!data) return;
        e.preventDefault();
        this.onDrop(data, pkey);
    }

    // === Add button ("+") — append / drop into an empty grid ===
    // Dropping a card on the "+" affordance appends it at the tail, or
    // makes it the first row when the grid is empty. The "+" is a LEAF
    // (a sibling of the rows, not an ancestor of the drag handles), so
    // listening here cannot interfere with the tiles' own drag start —
    // which is exactly why this lives on the "+" and not on the body or
    // container. Works for cards (footer "+") and tabs (tab-strip "+").

    addBtnDragOver(e) {
        if (!this._dataTransferHasOurType(e.dataTransfer)) return;
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = 'move';
        this._addBtnHighlight(true);
    }

    addBtnDragLeave() {
        this._addBtnHighlight(false);
    }

    addBtnDrop(e) {
        this._addBtnHighlight(false);
        const data = genro.dom.getFromDataTransfer(
            e.dataTransfer, this.dropType());
        if (!data || !data.rowKey) return;
        e.preventDefault();
        e.stopPropagation();
        // Append at the tail (after the last row), or no position when the
        // grid is empty (→ the moved row becomes the first one). Same
        // 'move' dispatch as onDrop; _handleAction routes self vs cross.
        const c = this.controller;
        const nodes = c.dataStore.getNodes();
        const lastKey = nodes.length ? nodes[nodes.length - 1].label : null;
        if (data.sourceNodeId === c.nodeId && data.rowKey === lastKey) return;
        genro.publish(c.actionTopic, {
            action: 'move',
            rowKey: data.rowKey,
            sourceNodeId: data.sourceNodeId,
            position: lastKey ? ('>' + lastKey) : ''
        });
    }

    _addBtnHighlight(on) {
        const c = this.controller;
        const btn = c.addBtnDom || (c.phantomTile && c.phantomTile.domNode());
        if (btn) btn.classList.toggle('canBeDropped', on);
    }
};


// ============================================================================
//  GroupletDataStore — single funnel between controller and rows Bag.
//  Thin view over the framework store built in the controller
//  constructor; `this.store()` returns `this.controller.store`.
// ============================================================================

gnr.GroupletDataStore = class GroupletDataStore {

    constructor(controller, kw) {
        this.controller = controller;
        this.storepath = kw.storepath;
        this._filtered = null;
        this._sortedBy = null;
    }

    store() {
        return this.controller.store;
    }

    // === Read ===

    getData() {
        return this.store().getData();
    }

    getNodes() {
        return this.getData().getNodes();
    }

    rowNode(rowKey) {
        return this.getData().getNode(rowKey);
    }

    rowValue(rowKey) {
        return this.getData().getItem(rowKey);
    }

    rowField(rowKey, field) {
        return genro.getData(this.storepath + '.' + rowKey + '.' + field);
    }

    rowByIndex(idx) {
        const n = this.getNodes()[idx];
        if (!n) return null;
        const v = n.getValue();
        return v instanceof gnr.GnrBag ? v.asDict() : {};
    }

    len() {
        return this.getData().len();
    }

    keyForRow(rowKey) {
        return rowKey;
    }

    indexOfKey(rowKey) {
        return this.getData().index(rowKey);
    }

    // === Mutate ===

    addRow(rowKey, data, position) {
        const dataBag = this.getData();
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
        this.getData().popNode(rowKey);
    }

    deleteRowAsk(rowKey) {
        this.deleteRowsAsk([rowKey]);
    }

    deleteRowsAsk(rowKeys) {
        // Standard delete dialog (count-verify + protect logic +
        // logical-delete UX), inherited from gnr.stores._Collection.
        this.store().deleteAsk(rowKeys);
    }

    moveRow(rowKey, position) {
        // Reorder through the Bag API without del/ins events; nested widgets
        // retain their node identity and parent chain. The controller mirrors DOM.
        if (typeof position !== 'string') return null;
        const op = position.charAt(0);
        if (op !== '<' && op !== '>') return null;
        const targetKey = position.slice(1);
        const bag = this.getData();
        const nodes = bag.getNodes();
        const fromIdx = nodes.findIndex((n) => n.label === rowKey);
        const targetIdx = nodes.findIndex((n) => n.label === targetKey);
        if (fromIdx < 0 || targetIdx < 0 || fromIdx === targetIdx) return null;
        const insertAt = targetIdx - (fromIdx < targetIdx ? 1 : 0) + (op === '>' ? 1 : 0);
        bag.moveNode(fromIdx, insertAt, false);
        return {op: op, targetKey: targetKey};
    }

    moveRowFrom(srcStore, srcKey, position, forceKey) {
        // Cross-grid migration. `forceKey` lets the caller pre-commit
        // the destination key (so e.g. _pendingFlash can be set before
        // the setItem trigger fires _renderTile).
        const sourceBag = srcStore.getData();
        const targetBag = this.getData();
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
        return this.getData().sum(field, strict);
    }

    getIdxFromPkey(pkey) {
        return this.indexOfKey(pkey);
    }

    // Phase 2 stubs — silent no-ops. Filter/sort will route through
    // `_visualOrder()` (CSS on top of the store's `_filtered` array),
    // never mutating the underlying Bag.
    setFilter(_cb) {}
    clearFilter() {}
    setSort(_spec) {}
    clearSort() {}

    isFiltered() {
        return this.store().isFiltered();
    }

    refresh() {
        // no-op until filter/sort state exists
    }

    // === Lock / changes / errors — forward to the store ===

    hasChanges() {
        return this.store().hasChanges();
    }

    hasErrors() {
        return this.store().hasErrors();
    }

    setLocked(value) {
        this.store().setLocked(value);
    }

    isLocked() {
        return this.store().isLocked();
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
        this.formulas = kw.formulas || {};
        this.totals = kw.totals || [];
        this.dragCode = kw.dragCode || null;
        // RPC path strings, not method names: serialized server-side
        // from bound public_methods so dynamic mixins resolve correctly.
        this.loaderrpc = kw.loaderrpc;
        this.mapLoaderrpc = kw.mapLoaderrpc;
        this.dnd = this.dragCode ? new gnr.GroupletGridDnD(this) : null;
        // Dedicated storeNode at controllerPath, separate from the rows
        // Bag at storepath (same technique as gnr.widgets.BagStore but
        // built programmatically: no sibling XML node needed).
        this.controllerPath = sourceNode.absDatapath(
            sourceNode.attr.controllerPath);
        // additem='phantom': a trailing blank row that becomes a real row on
        // its first entered value. Not with resourceField, whose template is
        // chosen by a value the blank row does not have yet.
        this.phantom = (kw.additem === 'phantom') && !this.resourceField;
        this._freshRows = {};
        // additem='entry': a row pinned above the rows, filled and added to
        // the tail with Enter or its add button, then cleared but for its
        // kept fields (genropy's `keepable`). Same resourceField limit as
        // the phantom.
        this.entry = (kw.additem === 'entry') && !this.resourceField;
        this.entryNode = kw.entryNode || null;
        this.entryPath = this.controllerPath + '.entry';
        this.entryTile = null;
        // With a rowTemplate the rows are read-only summaries: a click loads
        // the row in the entry row, Enter writes it back, Esc gives up;
        // Cmd/Shift+click selects several rows, to delete them together.
        this.rowTemplate = (this.entry && kw.rowTemplate) || null;
        if (this.rowTemplate && this.rowTemplate.template) {
            // {template, formats}: the compiled shape, numbers as formatted
            const tpl = new gnr.GnrBag();
            tpl.setItem('main', this.rowTemplate.template,
                        {formats: this.rowTemplate.formats || {}});
            this.rowTemplate = tpl;
        }
        this._editingKey = null;
        this._multiKeys = null;
        this._selAnchor = null;
        this.selectionNode = kw.selectionNode || null;
        this.selectionmenu = kw.selectionmenu || {};
        // rowCheckbox: a checkbox per row and one for all, as in a mail list
        this.rowCheckbox = !!(kw.rowCheckbox && this.rowTemplate);
        this.phantomPath = this.controllerPath + '.phantom';
        this.phantomTile = null;
        const storeNode = sourceNode._('dataController', {
            datapath: this.controllerPath,
            storepath: this.storepath,
            nodeId: this.nodeId + '_store'
        }).getParentNode();
        const storeKw = kw.store_kw || {};
        const storeType = storeKw.store_storeType || 'ValuesBagRows';
        this.store = new gnr.stores[storeType](storeNode, {
            identifier: storeKw.store_identifier || '_pkey',
            deleteRows: storeKw.store_deleteRows
        });
        storeNode.store = this.store;
        this.dataStore = new gnr.GroupletDataStore(this, {
            storepath: this.storepath
        });
        this._chipDnDHandlers = {};
        this.layout = kw.layout || 'cards';
        // Lazy tab bodies: build chips upfront but defer each tile body
        // (chrome + grafted template) until the tab is first activated.
        // Only meaningful for tab layouts; cards are all visible at once.
        this.lazyTabs = (kw.lazyTabs === true) && this._isTabsLayout();
        this.titleField = kw.titleField || null;
        this.emptyTitle = kw.emptyTitle || _T('!!Untitled');
        this.activePkey = null;
        this._tabsByPkey = {};
        this._pendingActivate = null;
        this._pendingFocus = null;
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
        const that = this;
        dojo.connect(sourceNode, '_onDeleting', function() { that.destroy(); });
        // Defer first render to `onBuiltCall` so the body slot is
        // attached to the DOM before tiles are created.
        genro.src.onBuiltCall(function() {
            if (that._destroyed) return;
            that._initChangeManager();
            that.newDataStore();
            that._updateAddBtnState();
        });
    }

    destroy() {
        if (this._destroyed) return;
        this._destroyed = true;
        this.sourceNode.unregisterSubscription(this.actionTopic);
        Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
        this._unmountPhantom();
        this._unmountEntry();
        const phantomBag = genro.getData(this.phantomPath);
        if (phantomBag instanceof gnr.GnrBag) {
            phantomBag.unsubscribe(this._phantomSubscriberId());
        }
        const entryBag = genro.getData(this.entryPath);
        if (entryBag instanceof gnr.GnrBag) {
            entryBag.unsubscribe(this._entrySubscriberId());
        }
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
        return this.dataStore.getData();
    }

    _containerDom() {
        return this.sourceNode.getDomNode();
    }

    collectionStore() {
        // GridChangeManager expects a store-shaped object with
        // updateRowNode / sum / getIdxFromPkey / rowByIndex; the
        // dataStore exposes exactly these names.
        return this.dataStore.getData() ? this.dataStore : null;
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
        this.structAdapter = new gnr.GroupletGridStructAdapter(
            struct, this.controllerPath);
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
        }
        this._initDeclaredTotals();
        const store = this.storebag();
        if (store && store.len() > 0) {
            this._changeMgr.resolveCalculatedColumns();
            this._changeMgr.resolveTotalizeColumns();
        }
    }

    // ====================================================================
    //  Declared formulas and totals band — `formulas=` / `totals=`, any
    //  mode (the card-mode counterpart of struct cells' formula/totalize)
    // ====================================================================

    _initDeclaredTotals() {
        const fields = Object.keys(this.formulas);
        if (!fields.length && !this.totals.length) return;
        // A formula is recalculated when a cellmap field it names changes,
        // and in card mode the cellmap starts empty: every field the
        // expressions read goes in first, formula fields included, so a
        // formula over another formula chains.
        fields.forEach((f) => {
            this._ensureCell(f);
            gnr.GroupletGridController.formulaFields(this.formulas[f])
                .forEach((dep) => this._ensureCell(dep));
        });
        fields.forEach((f) => {
            const cell = this.cellmap[f];
            cell.formula = this.formulas[f];
            cell.calculated = true;
            this._changeMgr.addFormulaColumn(f, {formula: this.formulas[f]});
        });
        this.totals.forEach((t) => {
            if (!t.field) return;
            const path = this._totalizePath(t.key);
            this._ensureCell(t.field).totalize = path;
            this._changeMgr.addTotalizer(t.field, {totalize: path});
        });
        if (this.totals.some((t) => t.formula)) {
            // a `function`, not an arrow: subscribe goes through funcApply,
            // which reads the handler's signature off its source
            const that = this;
            this.sourceNode.subscribe('onUpdateTotalize', function() {
                that._computeDerivedTotals();
            });
        }
        this._mountTotals();
    }

    _ensureCell(field) {
        this.cellmap[field] = this.cellmap[field]
            || {field: field, _nodelabel: field};
        return this.cellmap[field];
    }

    _totalizePath(key) {
        // Same namespace struct cells use for `totalize=True`.
        return this.controllerPath + '.totalize.' + key;
    }

    static formulaFields(expression) {
        // The row fields an expression reads: identifiers not reached
        // through a dot (`Math.round`) and not JS vocabulary.
        const skip = gnr.GroupletGridController._FORMULA_WORDS;
        const out = [];
        const re = /(^|[^\w.$])([A-Za-z_$][\w$]*)/g;
        let m;
        while ((m = re.exec(expression || '')) !== null) {
            if (!skip.has(m[2]) && out.indexOf(m[2]) < 0) out.push(m[2]);
        }
        return out;
    }

    _mountTotals() {
        if (!this.totals.length) return;
        const slots = this._resolveStructSlots();
        if (!slots.bottom) return;
        const root = genro.src.newRoot();
        const band = root._('div', {_class: 'grouplet_grid__totals'});
        this.totals.forEach((t) => {
            const attrs = Object.assign({}, t.attrs);
            const extraClass = objectPop(attrs, '_class');
            attrs._class = 'grouplet_grid__total'
                + (t.highlight ? ' grouplet_grid__total--highlight' : '')
                + (extraClass ? ' ' + extraClass : '');
            const item = band._('div', attrs);
            item._('div', {_class: 'grouplet_grid__total_label',
                           innerHTML: _T(t.label)});
            const valueKw = {_class: 'grouplet_grid__total_value',
                             innerHTML: '^' + this._totalizePath(t.key)};
            if (t.format) valueKw.format = t.format;
            item._('div', valueKw);
        });
        this._mountSlotContent(slots.bottom, root, 'totals');
        this._containerDom().classList.add('has-bottom');
    }

    _computeDerivedTotals() {
        // Formulas over the other totals, in declaration order, run on
        // every summed update (onUpdateTotalize) rather than as grafted
        // dataFormula nodes, which start listening after the first sums.
        const values = {};
        this.totals.forEach((t) => {
            values[t.key] = this.sourceNode.getRelativeData(
                this._totalizePath(t.key));
        });
        this.totals.forEach((t) => {
            if (!t.formula) return;
            let result = null;
            try {
                result = funcApply('return ' + t.formula, values,
                                   this.sourceNode);
            } catch (e) {
                result = null;
            }
            if (typeof result === 'number' && isFinite(result)) {
                result = Math.round10(result);
            }
            values[t.key] = result;
            this.sourceNode.setRelativeData(this._totalizePath(t.key), result);
        });
    }

    _updateCountTotals() {
        const counts = this.totals.filter((t) => t.count);
        if (!counts.length) return;
        const bag = this.storebag();
        const n = (bag instanceof gnr.GnrBag) ? bag.len() : 0;
        counts.forEach((t) => {
            this.sourceNode.setRelativeData(this._totalizePath(t.key), n);
        });
        this._computeDerivedTotals();
    }

    _resetTotals() {
        // A record with no rows Bag publishes no onNewDatastore: without
        // this the band would keep the previous record's figures.
        this.totals.forEach((t) => {
            if (t.field) {
                this.sourceNode.setRelativeData(this._totalizePath(t.key), null);
            }
        });
        this._computeDerivedTotals();
    }

    _mountStructSlots() {
        if (!this.structAdapter) return;
        const containerDom = this._containerDom();
        containerDom.style.setProperty('--gg-struct-columns',
            this.structAdapter.columnsCSS());
        const slots = this._resolveStructSlots();
        if (slots.top) {
            this._mountSlotContent(slots.top,
                this.structAdapter.buildHeader(this.entry, this.rowCheckbox), 'struct_header');
            // Force `has-top`: _applySlotClasses reads slot.children which
            // may not reflect the just-grafted nodes yet.
            containerDom.classList.add('has-top');
            this._syncChecks();
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
        // Header/footer in struct= mode live in slot-top/slot-bottom,
        // outside the row's drag/kebab insets — so their absolute X
        // differs from the row's grid tracks. This sync runs in two
        // passes:
        //   1) frame header/footer onto firstRow's content-box
        //   2) place header/footer cells absolutely over each track
        if (!this.structAdapter) return;
        const containerDom = this._containerDom();
        const entryRow = containerDom.querySelector(
            '.grouplet_grid_row--entry > .grouplet_grid__struct_row');
        const firstRow = containerDom.querySelector(
            '.grouplet_grid_body .grouplet_grid__struct_row') || entryRow;
        if (!firstRow) return;
        // Single pass stamps the col_cell marker (some widgets wrap
        // themselves so the supplied class lands on an inner node),
        // collects readonly cells per column, and captures firstRow's
        // tracks for the per-column step.
        const readonlyByColumn = [];
        const trackEls = [];
        // Readonly template rows have no input to measure the text edge on:
        // the entry row's editors give it, so values line up with it.
        const measureRow = (this.rowTemplate && entryRow) ? entryRow : firstRow;
        if (measureRow !== firstRow) {
            Array.from(measureRow.children).forEach((el) => trackEls.push(el));
        }
        const allRows = containerDom.querySelectorAll(
            '.grouplet_grid_body .grouplet_grid__struct_row');
        allRows.forEach(function(row) {
            const isFirst = (row === firstRow && measureRow === firstRow);
            Array.from(row.children).forEach(function(el, i) {
                el.classList.add('grouplet_grid__struct_col_cell');
                if (isFirst) trackEls.push(el);
                if (el.classList.contains('grouplet_grid__struct_row_cell')) {
                    if (!readonlyByColumn[i]) readonlyByColumn[i] = [];
                    readonlyByColumn[i].push(el);
                }
            });
        });
        const headerEl = containerDom.querySelector(
            '.grouplet_grid__struct_header');
        const footerEl = containerDom.querySelector(
            '.grouplet_grid__struct_footer');
        this._frameStructChromeToFirstRow(firstRow, headerEl, footerEl,
            entryRow !== firstRow ? entryRow : null);
        this._placeStructColumnCells(
            containerDom, headerEl, footerEl, trackEls, readonlyByColumn);
    }

    // STEP 1 — stretch header/footer padding so their content-box matches
    // the row's inner grid.
    _frameStructChromeToFirstRow(firstRow, headerEl, footerEl, entryEl) {
        const rowOuter = firstRow.getBoundingClientRect();
        const rowCs = getComputedStyle(firstRow);
        const rowContentLeft  = rowOuter.left  + parseFloat(rowCs.paddingLeft);
        const rowContentRight = rowOuter.right - parseFloat(rowCs.paddingRight);
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
        // the entry row sits outside the scrolling body: same tracks as rows
        frameToRow(entryEl);
    }

    // STEP 2 — place header/footer cells absolutely at the same left/width
    // as the row's column wrappers (decouples from grid track resolution /
    // font-size scaling). Readonly row cells keep grid placement; only
    // their internal padding is tuned.
    _placeStructColumnCells(containerDom, headerEl, footerEl,
                            trackEls, readonlyByColumn) {
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
        this._readonlyRowSource = null;
        this._entryRowSource = null;
        Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
        this._unmountPhantom();
        this._unmountEntry();
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
        this._freshRows = {};
        this._editingKey = null;
        this._entryDraft = null;
        this._multiKeys = null;
        this._containerDom().classList.remove('grouplet_grid--editing', 'grouplet_grid--multi');
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
        } else if (this.totals.length) {
            this._resetTotals();
        }
        this._updateCountTotals();
        if (!hasBag || bag.len() === 0) {
            this._clearBody();
            if (this.phantom || this.entry) {
                this._ensureTemplate(() => this._mountBlankRows());
            }
            return;
        }
        this._clearBody();
        this.updateCounterColumn();
        this._ensureTemplate(() => {
            this._fullSync();
            this._mountBlankRows();
        });
    }

    _clearBody() {
        // Full teardown on record load: a different record may carry a
        // different grouplet structure, so stale tiles must not be reused.
        Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
        this.activePkey = null;
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
            this._updateCountTotals();
        } else if (kw.evt === 'del') {
            this._destroyTile(pkey);
            this.updateCounterColumn();
            this._updateCountTotals();
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
                // Defensive: ensure the active tile's body exists (e.g. a
                // tabs→tabs affordance rebuild on a lazily-deferred tile).
                const activeTile = this.tiles[this.activePkey];
                if (this.lazyTabs && !activeTile.bodyMounted) {
                    this._mountBodyWhenVisible(activeTile);
                }
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
            // Cards show every tile at once, so any lazily-deferred body
            // (built only on tab activation) must be materialised now —
            // otherwise never-opened tabs would become empty cards.
            if (this.lazyTabs) {
                this.bodyNode.freeze();
                Object.keys(this.tiles).forEach((pkey) => {
                    const t = this.tiles[pkey];
                    if (t && !t.bodyMounted) t.mountBody();
                });
                this.bodyNode.unfreeze();
                if (this.structAdapter) this._scheduleStructSync();
            }
            // Cards mount synchronously above (all visible at once); drop
            // any pending visibility observers from the tabs session.
            Object.keys(this.tiles).forEach((pkey) => {
                this.tiles[pkey]._cancelPendingBody();
            });
        } else if (prevActive && this.tiles[prevActive]) {
            this.activePkey = prevActive;
        }
        this._buildLayoutAffordances();
        this._reconcileTileDnD();
        if (this.phantom || this.entry) {
            if (this._isTabsLayout()) {
                this._unmountPhantom();
                this._unmountEntry();
            } else {
                this._ensureTemplate(() => this._mountBlankRows());
            }
        }
    }

    _reconcileTileDnD() {
        // Row (tile) DnD is wired once at mount, gated on the layout at
        // that moment, and setLayout does NOT re-mount tiles. Re-sync each
        // tile with the current layout: a row is a drop target in cards /
        // struct, never in tabs (where the chip strip drives DnD). Without
        // this a grid born in tabs has no row-drop wiring after switching
        // to cards, and one born in cards leaves stale row listeners live
        // under tabs.
        if (!this.dnd) return;
        const tabs = this._isTabsLayout();
        Object.keys(this.tiles).forEach((pkey) => {
            const tile = this.tiles[pkey];
            if (!tile) return;
            if (tabs) {
                tile._unwireTileDnD();
            } else if (tile.tileDom && !tile._tileDnDHandlers) {
                tile._wireTileDnD(tile.tileDom);
            }
        });
    }

    _buildCardsFooter(containerDom) {
        // Appended to the container (grid-area `addbtn`), NOT to the
        // body — otherwise row rendering inside the body would touch it.
        if (!this.additem || this.phantom || this.entry) return;
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
        this._wireAddBtnDnD();
    }

    _wireAddBtnDnD() {
        // Native DnD on the "+" (a leaf element) so a drop there appends /
        // lands in an empty grid. The button is recreated by every layout
        // build, so this follows setLayout automatically; its listeners
        // die with the button when the footer/tabbar is torn down.
        const btn = this.addBtnDom;
        if (!this.dnd || !btn) return;
        const dnd = this.dnd;
        btn.addEventListener('dragover', (e) => dnd.addBtnDragOver(e));
        btn.addEventListener('dragleave', () => dnd.addBtnDragLeave());
        btn.addEventListener('drop', (e) => dnd.addBtnDrop(e));
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
            this._wireAddBtnDnD();
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
        const tile = this.tiles[pkey];
        // Lazy: materialize chrome + body on first activation. Set the
        // active classes first so the wrapper is display:block while the
        // body subtree is grafted — nested groupletGrids then measure
        // their geometry against a visible layout (see _fullSync note).
        const needsBody = tile && this.lazyTabs && !tile.bodyMounted;
        if (this.activePkey === pkey && !needsBody) return;
        this.activePkey = pkey;
        this._setActiveTabClasses(pkey);
        if (needsBody) {
            // _setActiveTabClasses above set the active class on both the
            // DOM and the wrapper sourceNode, so the body graft (which
            // freeze/unfreezes the wrapper) re-renders it display:block.
            // Defer to rAF so nested groupletGrids build after layout.
            this._mountBodyWhenVisible(tile);
        }
        genro.publish(this.actionTopic,
            {action: 'activate', rowKey: pkey});
    }

    _mountBodyWhenVisible(tile) {
        // Defer the body graft to the next animation frame, after style +
        // layout have applied to the now-active (display:block) wrapper, so
        // nested groupletGrids build against real geometry rather than a
        // 0-size box. Idempotent via the _bodyPending guard.
        if (!tile || tile.bodyMounted || tile._bodyPending) return;
        const that = this;
        tile._bodyPending = true;
        requestAnimationFrame(function() {
            tile._bodyPending = false;
            if (tile.bodyMounted || tile.mounted === false) return;
            tile.mountBody();
            if (that.structAdapter) that._scheduleStructSync();
        });
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
            const tile = this.tiles[rk];
            const isActive = rk === activePkey;
            const dom = tile.domNode();
            if (dom) {
                dom.classList.toggle('grouplet_grid_tab_active', isActive);
            }
            // Keep the wrapper sourceNode `_class` in sync with the DOM so a
            // later freeze/unfreeze (mountBody, rebuild) re-renders with the
            // correct active state instead of resetting to the source attrs.
            const node = tile.tileNode;
            if (node && node.attr) {
                const cls = node.attr._class || 'grouplet_grid_row';
                const has = cls.indexOf('grouplet_grid_tab_active') !== -1;
                if (isActive && !has) {
                    node.attr._class = cls + ' grouplet_grid_tab_active';
                } else if (!isActive && has) {
                    node.attr._class = cls
                        .replace(/\s*grouplet_grid_tab_active/, '');
                }
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
        const targetBag = this.dataStore.getData();
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

    _setLoading(on) {
        // Dim the body while a template loads via RPC (canonical .dimmed).
        const dom = this.bodyNode && this.bodyNode.getDomNode();
        if (!dom) return;
        dom.classList.toggle('dimmed', !!on);
    }

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
        // In lazy mode _renderTile only built wrappers: graft the body of
        // the (pre-decided) active tile so the first tab is visible.
        if (this.lazyTabs && this._isTabsLayout() && this.activePkey) {
            const activeTile = this.tiles[this.activePkey];
            if (activeTile && !activeTile.bodyMounted) {
                this._mountBodyWhenVisible(activeTile);
            }
        }
        if (this.structAdapter) this._scheduleStructSync();
    }

    _renderTile(pkey) {
        if (this.tiles[pkey]) return;
        const position = this._computeTilePosition(pkey);
        const tile = new gnr.GroupletGridTile(this, pkey);
        if (this.lazyTabs && this._isTabsLayout()) {
            tile.mountWrapperOnly(position);
        } else {
            tile.mount(position);
        }
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
        return this.phantomTile ? '<' + this.phantomTile.tileLabel : undefined;
    }

    _afterTileMounted(tile) {
        const pkey = tile.pkey;
        this._updateAddBtnState();
        this._syncChecks();
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
        // Set by _doAddItem: a row the user just asked for is a row they are
        // about to fill in, so the caret goes there. Last, after the tabs
        // branch above has mounted the body of a lazy tile.
        if (this._pendingFocus === pkey) {
            this._pendingFocus = null;
            const editorIndex = this._pendingFocusEditor;
            this._pendingFocusEditor = null;
            this._focusFirstEditor(tile, editorIndex);
        }
        if (this._pendingReveal === pkey) {
            this._pendingReveal = null;
            // An entry row adds at the tail, possibly below the scroll.
            setTimeout(() => {
                const dom = tile.domNode();
                if (dom && dom.isConnected) dom.scrollIntoView({block: 'nearest'});
            }, 0);
        }
        if (this.structAdapter) this._scheduleStructSync();
    }

    _focusFirstEditor(tile, editorIndex) {
        const dom = tile && tile.domNode();
        if (!dom) return;
        // One tick: the widgets of a just-grafted tile are instantiated when
        // the framework drains its afterBuildCalls, after this mount returns.
        setTimeout(function() {
            if (!dom.isConnected) return;
            const editors = gnr.GroupletGridController._editors(dom);
            const target = (editorIndex === null || editorIndex === undefined)
                ? null : editors[editorIndex];
            const el = target || editors[0];
            if (!el) return;
            el.focus();
            // As a native Tab would: typing replaces the default in the field.
            if (target && el.select) el.select();
        }, 0);
    }

    static _editors(tileDom) {
        return Array.from(tileDom.querySelectorAll(
            'input:not([type=hidden]):not([disabled]):not([readonly]),'
            + 'textarea:not([disabled]):not([readonly]),'
            + 'select:not([disabled])'));
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

    _reproxyForm(content) {
        // Nodes were built while the template was detached, so getFormHandler
        // cached a falsy this.form. Now that the subtree is grafted under the
        // live form, re-resolve so each form-bound widget caches this.form.
        if (!(content instanceof gnr.GnrBag)) return;
        content.walk((node) => {
            if (node._registerInForm && !node.form) {
                delete node.form;
                node._registerInForm();
            }
        }, 'static');
    }

    _unproxyForm(content) {
        // Symmetric teardown: popNode does not de-register the grafted
        // widgets from the form, so do it here before the pop.
        if (!(content instanceof gnr.GnrBag)) return;
        content.walk((node) => {
            if (node.form && node.form.unregisterChild) {
                node.form.unregisterChild(node);
            }
        }, 'static');
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
        if (this._editingKey === pkey) this._finishEntryEdit();
        if (this._multiKeys && this._multiKeys.includes(pkey)) {
            const rest = this._multiKeys.filter((k) => k !== pkey);
            this._setMulti(rest.length >= this._minMulti() ? rest : null);
        }
        tile.unmount();
        delete this.tiles[pkey];
        if (this.selectedPkey === pkey) this.selectedPkey = null;
        this._updateAddBtnState();
        this._syncChecks();
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
        this._pendingFocus = newKey;
        if (this.phantom) this._freshRows[newKey] = true;
        const merged = objectUpdate({}, this.defaultRow || {});
        objectUpdate(merged, defaults || {});
        this.dataStore.addRow(newKey, merged, position);
    }

    _askAndDeleteItem(pkey) {
        if (this._rowCount() <= this.minRows) return;
        this.dataStore.deleteRowAsk(pkey);
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
        const atMax = !!(this.maxRows
                         && this._rowCount() >= this.maxRows);
        if (this.phantom || this.entry) {
            this._containerDom().classList.toggle('grouplet_grid--at-max', atMax);
        }
        if (!this.addBtnDom) return;
        this.addBtnDom.classList.toggle('disabled', atMax);
    }

    // ====================================================================
    //  Phantom row — additem='phantom': the blank row lives at phantomPath,
    //  outside the rows Bag and the form, until a value is entered
    // ====================================================================

    _phantomSubscriberId() {
        return 'gg_phantom_' + this.nodeId;
    }

    _mountBlankRows() {
        this._mountPhantom();
        this._mountEntry();
    }

    _mountPhantom() {
        if (!this.phantom || this._destroyed || this._isTabsLayout()) return;
        this._resetPhantom();
        if (this.phantomTile) return;
        this.phantomTile = new gnr.GroupletGridPhantomTile(this);
        this.phantomTile.mount();
        this._updateAddBtnState();
        this._scheduleStructSync();
    }

    _unmountPhantom() {
        if (!this.phantomTile) return;
        this.phantomTile.unmount();
        this.phantomTile = null;
    }

    _resetPhantom() {
        const bag = this._resetBlankRow(this.phantomPath);
        bag.subscribe(this._phantomSubscriberId(),
                      {any: () => this._onPhantomChange()});
    }

    _resetBlankRow(path, keepMarked) {
        // Back to defaultRow; with keepMarked, the fields a `keepable`
        // widget has marked (_keep) keep their value. Returns the row Bag.
        let bag = genro.getData(path);
        if (!(bag instanceof gnr.GnrBag)) {
            genro.setData(path, new gnr.GnrBag());
            bag = genro.getData(path);
        }
        const defaults = this.defaultRow || {};
        const fields = bag.getNodes().map((n) => n.label);
        Object.keys(defaults).forEach((k) => {
            if (fields.indexOf(k) < 0) fields.push(k);
        });
        const kept = keepMarked ? gnr.GroupletGridController._keptValues(bag) : {};
        this._phantomResetting = true;
        try {
            fields.forEach((k) => {
                // emptied and set back, a kept value would reach its widget
                // as a change
                if (k in kept) return;
                bag.setItem(k, (k in defaults) ? defaults[k] : null);
            });
            Object.keys(kept).forEach((p) => {
                bag.setItem(p, kept[p], {_keep: true});
            });
        } finally {
            this._phantomResetting = false;
        }
        return bag;
    }

    static _keptValues(bag, prefix) {
        // {relative path: value} of the leaves marked _keep, nested included
        const out = {};
        bag.getNodes().forEach((n) => {
            const path = prefix ? prefix + '.' + n.label : n.label;
            const v = n.getValue();
            if (v instanceof gnr.GnrBag) {
                Object.assign(out, gnr.GroupletGridController._keptValues(v, path));
            } else if (n.attr && n.attr._keep) {
                out[path] = v;
            }
        });
        return out;
    }

    _phantomHasValues() {
        return this._hasEnteredValues(genro.getData(this.phantomPath));
    }

    _hasEnteredValues(rowBag, baseline) {
        // Computed columns are not an entry: in struct mode only the editable
        // cells count, in card mode every field but formulas and the counter.
        if (!(rowBag instanceof gnr.GnrBag)) return false;
        const defaults = baseline || this.defaultRow || {};
        const editable = this.structAdapter
            ? this.structAdapter.cells.filter((c) => c.edit).map((c) => c.field)
            : null;
        const computed = Object.keys(this.formulas || {})
            .concat(this.counterField ? [this.counterField] : []);
        return rowBag.getNodes().some((n) => {
            const skip = editable ? editable.indexOf(n.label) < 0
                                  : computed.indexOf(n.label) >= 0;
            return !skip && gnr.GroupletGridController._isEntry(
                n.getValue(), defaults[n.label]);
        });
    }

    static _isEntry(value, dflt) {
        // Defaults alone or an emptied field are not an entry; a nested Bag
        // (a template writing into `.extra_data.*`) is one if any leaf is.
        if (value instanceof gnr.GnrBag) {
            return value.getNodes().some((n) => gnr.GroupletGridController._isEntry(
                n.getValue(), (dflt && typeof dflt === 'object') ? dflt[n.label] : undefined));
        }
        if (value === null || value === undefined || value === '') return false;
        return (dflt === undefined) ? value !== false : value !== dflt;
    }

    _onPhantomChange() {
        if (this._phantomResetting || this._phantomPending) return;
        if (!this._phantomHasValues()) return;
        // Deferred out of the widget's own change handler, and past the
        // focus move a Tab triggers, so the caret can follow the new row.
        this._phantomPending = true;
        setTimeout(() => {
            this._phantomPending = false;
            this._promotePhantom();
        }, 0);
    }

    _promotePhantom() {
        if (this._destroyed || !this.phantomTile) return;
        if (!this._phantomHasValues()) return;
        const form = this.sourceNode.getFormHandler();
        const atMax = this.maxRows && this._rowCount() >= this.maxRows;
        if ((form && form.isDisabled()) || atMax) {
            this._resetPhantom();
            return;
        }
        const values = genro.getData(this.phantomPath).deepCopy().asDict();
        const editorIndex = this._phantomFocusedEditor();
        const newKey = 'r_' + genro.time36Id();
        if (editorIndex !== null) {
            this._pendingFocus = newKey;
            this._pendingFocusEditor = editorIndex;
        }
        this._freshRows[newKey] = true;
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[newKey] = true;
        this._resetPhantom();
        this.dataStore.addRow(newKey, values);
    }

    _dropIfEmpty(pkey) {
        // The reverse of the promotion, for rows added since the rows were
        // loaded: one left with no entry goes away, without the dialog. A
        // loaded row emptied stays, it is deleted with its `×`.
        if (this._destroyed || !this.tiles[pkey] || !this._freshRows[pkey]) return;
        if (this._rowCount() <= this.minRows) return;
        const form = this.sourceNode.getFormHandler();
        if (form && form.isDisabled()) return;
        if (this._hasEnteredValues(this.dataStore.rowValue(pkey))) return;
        delete this._freshRows[pkey];
        this.dataStore.removeRow(pkey);
    }

    _phantomFocusedEditor() {
        const dom = this.phantomTile && this.phantomTile.domNode();
        if (!dom) return null;
        const active = document.activeElement;
        if (!active || !dom.contains(active)) return null;
        const idx = gnr.GroupletGridController._editors(dom).indexOf(active);
        return idx < 0 ? null : idx;
    }

    // ====================================================================
    //  Entry row — additem='entry': filled at entryPath, outside the rows
    //  Bag and the form, added to the tail on Enter or its add button
    // ====================================================================

    _mountEntry() {
        if (!this.entry || !this.entryNode || this._destroyed
                || this._isTabsLayout()) return;
        this._resetEntry();
        if (this.entryTile) return;
        this.entryTile = new gnr.GroupletGridEntryTile(this);
        this.entryTile.mount();
        this._mountSelectionBar();
        this._syncChecks();
        if (!this._chromeClicksWired) {
            // header pins and select-all boxes are rebuilt with their slot
            this._chromeClicksWired = true;
            const container = this._containerDom();
            // a header pin leaves the focus in the entry row
            container.addEventListener('mousedown', (e) => {
                if (e.target.closest('.grouplet_grid__struct_keep')) e.preventDefault();
            });
            container.addEventListener('click', (e) => {
                if (e.target.closest('.grouplet_grid') !== container) return;
                const pin = e.target.closest('.grouplet_grid__struct_keep');
                if (pin) this._toggleKeep(pin.dataset.field);
                else if (e.target.closest('.grouplet_grid_check_all')) this._onCheckAll();
            });
        }
        // a row grafted while the page builds gets its widgets a tick later
        setTimeout(() => this._destroyed || this._syncKept(), 0);
        this._validateEntryRequired();
        this._updateAddBtnState();
        this._scheduleStructSync();
    }

    _unmountEntry() {
        if (!this.entryTile) return;
        this.entryTile.unmount();
        this.entryTile = null;
    }

    _resetEntry() {
        // Kept fields survive (Enter, Esc, record load alike) and act as
        // defaults for the next row: alone, they are no entry.
        const bag = this._resetBlankRow(this.entryPath, true);
        bag.subscribe(this._entrySubscriberId(),
                      {any: () => this._calcEntryFormulas()});
        this._entryBaseline = objectUpdate({}, this.defaultRow || {});
        const kept = gnr.GroupletGridController._keptValues(bag);
        Object.keys(kept).forEach((path) => {
            const parts = path.split('.');
            let target = this._entryBaseline;
            parts.slice(0, -1).forEach((part) => {
                if (!target[part] || typeof target[part] !== 'object') target[part] = {};
                target = target[part];
            });
            target[parts[parts.length - 1]] = kept[path];
        });
        if (this.structAdapter) {
            this.structAdapter.cells.forEach((c) => {
                if (c.keepable === '*') bag.getNode(c.field, false, true).attr._keep = true;
            });
        }
        this._syncKept();
        this._validateEntryRequired();
    }

    _validateEntryRequired() {
        // A field is required to add the row: a blank one is flagged at once,
        // red while the entry row has the focus. One tick: a just-grafted row
        // gets its widgets when the framework drains its afterBuildCalls.
        setTimeout(() => {
            if (this._destroyed || !this.entryTile || !this.entryTile.tileContent) return;
            this.entryTile.tileContent.walk((n) => {
                const attr = n.attr || {};
                if (!attr.validate_notnull || !n.widget || !n.hasValidations()
                        || !isNullOrBlank(n.getAttributeFromDatasource('value'))) return;
                this._validateEntryField(n);
            }, 'static');
        }, 0);
    }

    _validateEntryField(node) {
        // no form validates the entry row
        const result = genro.vld.validate(node, node.getAttributeFromDatasource('value'),
                                          false, true, ['notnull']);
        node.setValidationError(result);
        node.updateValidationStatus();
        return result;
    }

    _entrySubscriberId() {
        return 'gg_entry_' + this.nodeId;
    }

    _calcEntryFormulas() {
        // The entry row is no row of the store, so the change manager does
        // not see it: its formulas are worked out here as it is typed in.
        if (this._phantomResetting || this._entryCalculating || !this._changeMgr) return;
        const node = genro.getDataNode(this.entryPath);
        const formulas = this._changeMgr.formulaColumns;
        this._entryCalculating = true;
        try {
            Object.keys(formulas).forEach((field) => {
                // a counter or a running total reads the rows around it
                if (formulas[field] === '#' || /^[+%]=/.test(formulas[field])) return;
                node.getValue().setItem(field, this._changeMgr.evaluateFormula(field, node));
            });
        } finally {
            this._entryCalculating = false;
        }
    }

    _toggleKeep(field) {
        const node = genro.getData(this.entryPath).getNode(field, false, true);
        node.attr._keep = !node.attr._keep;
        this._syncKept();
    }

    _syncKept() {
        // Struct entry rows keep by header pins, not by the theme's keeper:
        // the kept state is the data node's _keep, shown on pin and input.
        const dom = this.structAdapter && this._containerDom();
        if (!dom) return;
        const bag = genro.getData(this.entryPath);
        const isKept = (field) => {
            const n = (bag instanceof gnr.GnrBag) && bag.getNode(field);
            return !!(n && n.attr._keep);
        };
        dom.querySelectorAll('.grouplet_grid__struct_keep').forEach((pin) => {
            pin.classList.toggle('grouplet_grid__struct_keep--on', isKept(pin.dataset.field));
        });
        if (!this.entryTile || !this.entryTile.tileContent) return;
        this.structAdapter.cells.forEach((c) => {
            if (!c.keepable) return;
            const node = this.entryTile.tileContent.walk((n) => (
                (n.widget && n.attr.value === '^.' + c.field) ? n : undefined
            ), 'static');
            if (node && node.widget.focusNode) {
                const kept = isKept(c.field);
                node.widget.focusNode.classList.toggle('grouplet_grid_kept', kept);
                node.widget.focusNode.tabIndex = kept ? -1 : node.widget.tabIndex;
            }
        });
    }

    _onEntryKeydown(e) {
        // Listened to in the capture phase: a closed combo swallows Enter.
        // An open dropdown owns Enter (pick) and Escape (close).
        const widget = dijit.getEnclosingWidget(e.target);
        if (widget && widget._isShowingNow) return;
        if (e.key === 'Escape') {
            e.preventDefault();
            if (this._editingKey) this._finishEntryEdit();
            else this._resetEntry();
            this._focusEntry();
        } else if (e.key === 'Enter' && !e.shiftKey && !e.isComposing
                   && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            this._commitEntry();
        }
    }

    _commitEntry(then) {
        const dom = this.entryTile && this.entryTile.domNode();
        if (!dom) return;
        // A field writes its value in _onBlur. Moving the focus to the first
        // field blurs the one typed in now, with its value, not later on the
        // cleared row. The first field keeps the focus and writes it here.
        const widget = this._entryWidget;
        const first = this._entryFocusTarget(dom);
        if (first) first.focus();
        if (widget && widget._focused && widget._onBlur && widget.domNode
                && dom.contains(widget.domNode)) {
            widget._onBlur();
        }
        setTimeout(() => {
            if (this._addEntry() && then) then();
        }, 0);
    }

    _addEntry() {
        if (this._destroyed || !this.entryTile) return false;
        const form = this.sourceNode.getFormHandler();
        if (form && form.isDisabled()) return false;
        const editing = this._editingKey;
        if (!editing && this.maxRows && this._rowCount() >= this.maxRows) return false;
        const bag = genro.getData(this.entryPath);
        if (!this._hasEnteredValues(bag, editing ? null : this._entryBaseline)) {
            this._focusEntry();
            return false;
        }
        const missing = this._entryMissingField();
        if (missing) {
            this._flagMissingField(missing);
            return false;
        }
        if (editing) {
            this.dataStore.updateRow(editing, bag.deepCopy().asDict());
            const tile = this.tiles[editing];
            this._finishEntryEdit();
            if (tile) {
                tile.flash();
                const dom = tile.domNode();
                if (dom) dom.scrollIntoView({block: 'nearest'});
            }
            this._focusEntry();
            this._announce(_T('!!Row saved'));
            return true;
        }
        const newKey = 'r_' + genro.time36Id();
        const values = bag.deepCopy().asDict();
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[newKey] = true;
        this._pendingReveal = newKey;
        this.dataStore.addRow(newKey, values);
        this._resetEntry();
        this._focusEntry();
        this._announce(_T('!!Row added'));
        return true;
    }

    _structEntryRow() {
        if (!this._entryRowSource) {
            const computed = Object.keys(this.formulas)
                .concat(this.structAdapter.cells.filter((c) => c.formula).map((c) => c.field));
            this._entryRowSource = this.structAdapter.buildRowTemplate(false, computed);
        }
        return this._entryRowSource;
    }

    _structReadonlyRow() {
        if (!this._readonlyRowSource) {
            this._readonlyRowSource = this.structAdapter.buildRowTemplate(true);
        }
        return this._readonlyRowSource;
    }

    _editRowInEntry(pkey) {
        if (!this.entryTile || pkey === this._editingKey) return;
        // Moving to another row keeps the changes made to this one.
        if (this._entryChanged()) this._commitEntry(() => this._loadRowInEntry(pkey));
        else this._loadRowInEntry(pkey);
    }

    _entryChanged() {
        return !!this._editingKey
            && genro.getData(this.entryPath).toXml() !== this._entryLoaded.toXml();
    }

    _onTemplateRowClick(pkey, e) {
        if (!(e && (e.metaKey || e.ctrlKey || e.shiftKey))) {
            this._selAnchor = pkey;
            this._applySelection([pkey]);
            return;
        }
        let keys;
        if (e.shiftKey && this._selAnchor && this.tiles[this._selAnchor]) {
            keys = this._keysBetween(this._selAnchor, pkey);
        } else {
            const current = this._selectedKeys();
            keys = current.includes(pkey)
                ? current.filter((k) => k !== pkey) : current.concat(pkey);
            this._selAnchor = pkey;
        }
        this._applySelection(keys);
    }

    _keysBetween(a, b) {
        const keys = this.dataStore.getData().keys();
        const i = keys.indexOf(a);
        const j = keys.indexOf(b);
        return keys.slice(Math.min(i, j), Math.max(i, j) + 1);
    }

    _minMulti() {
        // checkboxes select from the first row; clicks need two, one is edited
        return this.rowCheckbox ? 1 : 2;
    }

    _onRowCheck(pkey, e) {
        const current = this._multiKeys ? this._multiKeys.slice() : [];
        let keys;
        if (e.shiftKey && this._selAnchor && this.tiles[this._selAnchor]) {
            const range = this._keysBetween(this._selAnchor, pkey);
            keys = current.concat(range.filter((k) => !current.includes(k)));
        } else {
            keys = current.includes(pkey)
                ? current.filter((k) => k !== pkey) : current.concat(pkey);
        }
        this._selAnchor = pkey;
        this._applyChecks(keys);
    }

    _onCheckAll() {
        const all = this.dataStore.getData().keys();
        const current = this._multiKeys || [];
        this._applyChecks(current.length === all.length ? [] : all);
    }

    _applyChecks(keys) {
        if (!keys.length) {
            this._setMulti(null);
            return;
        }
        const enter = () => {
            this._finishEntryEdit();
            this._setMulti(keys, false);
        };
        if (this._entryChanged()) this._commitEntry(enter);
        else enter();
    }

    _syncChecks() {
        if (!this.rowCheckbox) return;
        const keys = this._multiKeys || [];
        Object.keys(this.tiles).forEach((k) => {
            const dom = this.tiles[k].domNode();
            const box = dom && dom.querySelector(':scope > .grouplet_grid_row_check');
            if (box) box.checked = keys.includes(k);
        });
        const total = this._rowCount();
        this._checkAllBoxes().forEach((box) => {
            box.checked = total > 0 && keys.length === total;
            box.indeterminate = keys.length > 0 && keys.length < total;
        });
    }

    _checkAllBoxes() {
        // In the struct header, else at the head of the selection bar.
        return Array.from(this._containerDom().querySelectorAll(
            ':scope > .grouplet_grid_slot_top > .grouplet_grid__struct_header > .grouplet_grid_check_all,'
            + ':scope > .grouplet_grid_slot_bottom > .grouplet_grid_selection'
            + ' > .grouplet_grid_selection_bar > .grouplet_grid_check_all'));
    }

    _selectedKeys() {
        if (this._multiKeys) return this._multiKeys.slice();
        return this._editingKey ? [this._editingKey] : [];
    }

    _applySelection(keys) {
        // One row is edited in the entry row; several can only be deleted.
        if (keys.length >= 2) {
            const enter = () => {
                this._finishEntryEdit();
                this._setMulti(keys);
            };
            if (this._entryChanged()) this._commitEntry(enter);
            else enter();
            return;
        }
        this._setMulti(null);
        if (keys.length) this._editRowInEntry(keys[0]);
        else this._finishEntryEdit();
    }

    _setMulti(keys, focusBar = true) {
        const entering = !!keys && !this._multiKeys;
        this._multiKeys = keys;
        this._containerDom().classList.toggle('grouplet_grid--multi', !!keys);
        if (keys) this.selectedPkey = null;
        Object.keys(this.tiles).forEach((k) => {
            const dom = this.tiles[k].domNode();
            if (dom) dom.classList.toggle('selected', !!keys && keys.includes(k));
        });
        this._syncChecks();
        const bar = this.selectionNode && this.selectionNode.getDomNode();
        if (!bar || !keys) return;
        const one = keys.length === 1;
        bar.querySelector('.grouplet_grid_selection_count').textContent =
            (one ? _T('!!1 row selected') : _T('!!$count rows selected')).replace('$count', keys.length);
        const label = bar.querySelector('.grouplet_grid_selection_delete_label');
        if (label) {
            label.textContent = (one ? _T('!!Delete 1 row') : _T('!!Delete $count rows'))
                .replace('$count', keys.length);
        }
        if (entering && focusBar) {
            setTimeout(() => {
                const first = bar.querySelector('[tabindex]');
                if (first) first.focus();
            }, 0);
        }
    }

    _mountSelectionBar() {
        // The bar below the rows for several selected rows: the count, the
        // delete preset as a button, the other `selectionmenu` entries in a
        // kebab. An entry's `action` runs with `rowKeys` and `grid`.
        const specs = this._selectionSpecs();
        if (!this.selectionNode || this._selectionBarMounted || !specs.length) return;
        this._selectionBarMounted = true;
        const c = this;
        const bar = this.selectionNode.getValue()._('div', 'bar', {
            _class: 'grouplet_grid_selection_bar',
            connect_onkeydown: function(e) { c._onMultiKeydown(e); }
        });
        if (this.rowCheckbox && !this.structAdapter) {
            bar._('input', {type: 'checkbox', _class: 'grouplet_grid_check_all',
                            title: _T('!!Select all rows')});
        }
        bar._('span', {_class: 'grouplet_grid_selection_count'});
        bar._('span', {_class: 'grouplet_grid_selection_hint',
                       innerHTML: _T('!!Esc to clear')});
        const others = specs.filter((spec) => spec.key !== 'delete');
        if (specs.length > others.length) {
            const del = bar._('div', {
                _class: 'grouplet_grid_selection_delete',
                tabindex: 0,
                connect_onclick: function() { c._deleteSelected(); }
            });
            del._('span', {_class: 'grouplet_grid_trash_glyph'});
            del._('span', {_class: 'grouplet_grid_selection_delete_label'});
        }
        if (others.length) {
            const kebab = bar._('div', {
                _class: 'grouplet_grid_selection_kebab',
                tabindex: 0,
                tip: _T('!!Actions on the selected rows')
            });
            kebab._('span', {_class: 'grouplet_grid_kebab_icon', innerHTML: '⋮'});
            const menu = kebab._('menu', {
                modifiers: '*',
                _class: 'smallmenu grouplet_grid_row_menu'
            });
            others.forEach((spec) => {
                menu._('menuline', {
                    label: _T(spec.label),
                    action: function() { c._runSelectionAction(spec); }
                });
            });
        }
    }

    _selectionSpecs() {
        // selectionmenu = {key: true | 'label' | {label, action}}, as editmenu
        const presets = {'delete': {label: '!!Delete'}};
        return Object.keys(this.selectionmenu).map((key) => {
            const raw = this.selectionmenu[key];
            let spec = null;
            if (raw === true) spec = presets[key] || null;
            else if (typeof raw === 'string') spec = objectUpdate(objectUpdate({}, presets[key] || {}), {label: raw});
            else if (raw && typeof raw === 'object') spec = objectUpdate(objectUpdate({}, presets[key] || {}), raw);
            return (spec && spec.label) ? objectUpdate({key: key}, spec) : null;
        }).filter(Boolean);
    }

    _runSelectionAction(spec) {
        const keys = this._selectedKeys();
        if (!keys.length) return;
        if (spec.key === 'delete') {
            this._deleteSelected();
            return;
        }
        if (spec.action) funcApply(spec.action, {rowKeys: keys, grid: this}, this.sourceNode);
    }

    _onMultiKeydown(e) {
        const onDelete = !!e.target.closest('.grouplet_grid_selection_delete');
        if (e.key === 'Escape') {
            e.preventDefault();
            this._applySelection([]);
            this._focusEntry();
        } else if ((e.key === 'Enter' && onDelete)
                   || ((e.key === 'Delete' || e.key === 'Backspace') && this.selectionmenu['delete'])) {
            e.preventDefault();
            this._deleteSelected();
        }
    }

    _deleteSelected() {
        const keys = this._selectedKeys();
        if (!keys.length) return;
        const form = this.sourceNode.getFormHandler();
        if (form && form.isDisabled()) return;
        if (this._rowCount() - keys.length < this.minRows) {
            genro.dlg.floatingMessage(this.sourceNode, {
                message: _T('!!At least $count rows are required').replace('$count', this.minRows),
                messageType: 'warning'
            });
            return;
        }
        this.dataStore.deleteRowsAsk(keys);
    }

    _loadRowInEntry(pkey) {
        const row = this.dataStore.rowValue(pkey);
        if (!(row instanceof gnr.GnrBag)) return;
        // A new row being typed is set aside and comes back afterwards.
        if (!this._editingKey) {
            this._entryDraft = genro.getData(this.entryPath).deepCopy();
        }
        this._fillEntry(row);
        this._entryLoaded = genro.getData(this.entryPath).deepCopy();
        this._setEditingKey(pkey);
        this._focusEntry();
    }

    _fillEntry(sourceBag) {
        const bag = this._resetBlankRow(this.entryPath);
        sourceBag.getNodes().forEach((n) => {
            const v = n.getValue();
            bag.setItem(n.label, (v instanceof gnr.GnrBag) ? v.deepCopy() : v);
        });
    }

    _finishEntryEdit() {
        if (!this._editingKey) return;
        const draft = this._entryDraft;
        this._entryDraft = null;
        this._setEditingKey(null);
        if (draft) this._fillEntry(draft);
        else this._resetEntry();
    }

    _setEditingKey(pkey) {
        this._editingKey = pkey;
        this.selectTile(pkey);
        this._containerDom().classList.toggle('grouplet_grid--editing', !!pkey);
        const dom = this.entryTile && this.entryTile.domNode();
        const btn = dom && dom.querySelector('.grouplet_grid_row_add');
        if (btn) {
            btn.setAttribute('title',
                pkey ? _T('!!Save (Enter), Esc to cancel') : _T('!!Add (Enter)'));
        }
    }

    _entryMissingField() {
        return this.entryTile.tileContent.walk((n) => {
            const attr = n.attr || {};
            if (!attr.validate_notnull || !n.widget
                    || typeof attr.value !== 'string') return;
            const v = n.getRelativeData(attr.value.replace(/^\^/, ''));
            if (v === null || v === undefined || v === '') return n;
        }, 'static');
    }

    _flagMissingField(node) {
        // a blank field shows no tooltip: the error is published
        const result = this._validateEntryField(node);
        genro.publish('floating_message', {
            message: (node.getElementLabel() || '').trim() + ': '
                + node._resolveErrorMessage(result.error),
            sound: '$onerror', messageType: 'error'});
        node.widget.focus();
    }

    _focusEntry() {
        // The next entry starts at the first field not kept.
        const tile = this.entryTile;
        const dom = tile && tile.domNode();
        if (!dom) return;
        setTimeout(() => {
            const el = this._entryFocusTarget(dom);
            if (!el) return;
            el.focus();
            if (el.select) el.select();
        }, 0);
    }

    _entryFocusTarget(dom) {
        const editors = gnr.GroupletGridController._editors(dom)
            .filter((ed) => ed.offsetParent !== null);
        return editors.find((ed) => !ed.closest('.keeper_on')
            && !ed.classList.contains('grouplet_grid_kept')) || editors[0];
    }

    _announce(text) {
        // Screen readers hear the addition without the focus moving.
        if (!this._announcer) {
            const el = document.createElement('div');
            el.className = 'grouplet_grid_announce';
            el.setAttribute('role', 'status');
            el.setAttribute('aria-live', 'polite');
            this._containerDom().appendChild(el);
            this._announcer = el;
        }
        const el = this._announcer;
        el.textContent = '';
        setTimeout(() => { el.textContent = text; }, 50);
    }

    // ====================================================================
    //  Paste — rows of CSV/TSV pasted into the phantom or the entry row go
    //  to the tail, one row each, columns in the order of its fields
    // ====================================================================

    _onBlankPaste(e, tile) {
        if (tile === this.entryTile && this._editingKey) return;
        const form = this.sourceNode.getFormHandler();
        if (form && form.isDisabled()) return;
        const text = e.clipboardData && e.clipboardData.getData('text');
        // one plain value pastes as usual: only several lines or tabs split
        if (!text || !(/\t/.test(text) || /\n./.test(text.trim()))) return;
        e.preventDefault();
        this._pasteRows(text, tile, e.target);
    }

    _pasteRows(text, tile, target) {
        const fields = this._blankRowFields(tile);
        let start = fields.findIndex((f) => f.node.widget.domNode
            && f.node.widget.domNode.contains(target));
        if (start < 0) start = 0;
        let last = null;
        let added = 0;
        this._rowsFromText(text, fields, start).forEach((values) => {
            if (this.maxRows && this._rowCount() >= this.maxRows) return;
            const key = 'r_' + genro.time36Id();
            if (this.phantom) this._freshRows[key] = true;
            this.dataStore.addRow(key, objectUpdate(
                objectUpdate({}, this.defaultRow || {}), values));
            last = key;
            added += 1;
        });
        if (tile === this.phantomTile) this._resetPhantom();
        else this._resetEntry();
        const lastTile = last && this.tiles[last];
        if (lastTile) {
            lastTile.flash();
            const dom = lastTile.domNode();
            if (dom) dom.scrollIntoView({block: 'nearest'});
        }
        if (added) this._announce(_T('!!Rows added') + ': ' + added);
    }

    _blankRowFields(tile) {
        // The editable fields of a blank row, in template order, as paths
        // relative to the row (a template may write into `.extra_data.*`).
        const base = (tile === this.entryTile ? this.entryPath : this.phantomPath) + '.';
        const names = {};
        if (this.structAdapter) {
            this.structAdapter.cells.forEach((c) => { names[c.field] = c.name; });
        }
        const fields = [];
        tile.tileContent.walk((n) => {
            const attr = n.attr || {};
            if (!n.widget || typeof attr.value !== 'string' || attr.value[0] !== '^') return;
            const abs = n.absDatapath(attr.value.slice(1));
            if (abs.indexOf(base) !== 0) return;
            const path = abs.slice(base.length);
            fields.push({
                path: path,
                node: n,
                labels: [path, names[path], attr.lbl].filter(Boolean)
                    .map((l) => String(l).trim().toLowerCase())
            });
        }, 'static');
        return fields;
    }

    _rowsFromText(text, fields, start) {
        const Ctrl = gnr.GroupletGridController;
        const cols = fields.slice(start);
        let rows = Ctrl.parseDelimited(text);
        // a first line naming the columns is a header
        const first = rows.length ? rows[0].map((v) => v.trim().toLowerCase()) : [];
        if (first.some((v) => v) && first.every((v, i) => !v
                || (cols[i] && cols[i].labels.indexOf(v) >= 0))) {
            rows = rows.slice(1);
        }
        return rows.filter((r) => r.some((v) => v.trim() !== '')).map((r) => {
            const values = {};
            r.forEach((cell, i) => {
                if (cols[i]) values[cols[i].path] = Ctrl.pasteValue(cols[i].node, cell);
            });
            return values;
        });
    }

    static parseDelimited(text) {
        // CSV/TSV: the separator is a tab if any (spreadsheet copy), else
        // `;` (Italian CSV), else `,`; double quotes wrap a field and `""`
        // escapes one inside it.
        const src = text.replace(/\r\n?/g, '\n').replace(/\n+$/, '');
        const firstLine = src.split('\n')[0];
        const sep = firstLine.indexOf('\t') >= 0 ? '\t'
            : (firstLine.indexOf(';') >= 0 ? ';' : ',');
        const rows = [];
        let row = [];
        let cell = '';
        let quoted = false;
        for (let i = 0; i < src.length; i++) {
            const ch = src[i];
            if (quoted) {
                if (ch === '"' && src[i + 1] === '"') {
                    cell += '"';
                    i += 1;
                } else if (ch === '"') {
                    quoted = false;
                } else {
                    cell += ch;
                }
            } else if (ch === '"' && cell === '') {
                quoted = true;
            } else if (ch === sep) {
                row.push(cell);
                cell = '';
            } else if (ch === '\n') {
                row.push(cell);
                rows.push(row);
                row = [];
                cell = '';
            } else {
                cell += ch;
            }
        }
        row.push(cell);
        rows.push(row);
        return rows;
    }

    static pasteValue(node, text) {
        // With the field's constraints, so numbers and dates follow the
        // locale as when typed. Not through widget.parse: the date patch
        // may set the widget's own value while parsing.
        const t = text.trim();
        if (t === '') return null;
        if ((node.attr.tag || '').toLowerCase() === 'checkbox') {
            return /^(1|x|s|si|sì|y|yes|true|v|vero)$/i.test(t);
        }
        const w = node.widget;
        const cls = (w && w.declaredClass) || '';
        const constraints = (w && w.constraints) || {};
        if (/Number|Currency/.test(cls)) {
            // a pattern with decimals rejects "12": retry on the locale alone
            let v = dojo.number.parse(t, constraints);
            if (v === null || isNaN(v)) v = dojo.number.parse(t, {locale: constraints.locale});
            return (v === null || isNaN(v)) ? null : v;
        }
        if (/Date/.test(cls)) {
            const v = dojo.date.locale.parse(t, objectUpdate({selector: 'date'}, constraints));
            if (v) return v;
            const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t);
            return iso ? new Date(+iso[1], +iso[2] - 1, +iso[3]) : null;
        }
        return t;
    }

    _wirePhantomDnD(phantomDom) {
        // Drop on the phantom appends, as the `+` does in the other modes.
        const dnd = this.dnd;
        phantomDom.addEventListener('dragover', (e) => dnd.addBtnDragOver(e));
        phantomDom.addEventListener('dragleave', () => dnd.addBtnDragLeave());
        phantomDom.addEventListener('drop', (e) => dnd.addBtnDrop(e));
    }

    // ====================================================================
    //  Template plumbing — namespacing, cache, source-root building
    // ====================================================================

    _namespaceFrameworkNodeIds(domSource, pkey) {
        // Suffix every framework-generated `grpgrid_*` reference in the
        // cloned template so each row instance is unique. Author-supplied
        // (non-`grpgrid_*`) ids are left untouched. The attribute
        // whitelist (NAMESPACED_ATTRS) avoids the O(nodes × attrs) walk.
        const suffix = '__' + this.nodeId + '__' + pkey;
        const apply = function(n) {
            const a = n.attr;
            if (!a) return;
            for (let i = 0; i < NAMESPACED_ATTRS.length; i++) {
                const k = NAMESPACED_ATTRS[i];
                const v = a[k];
                if (typeof v === 'string'
                        && v.indexOf('grpgrid_') === 0) {
                    a[k] = v + suffix;
                }
            }
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
            this._setLoading(false);
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
        this._setLoading(true);
        genro.serverCall(this.loaderrpc, params,
            (tplBag, error) => {
                if (error) {
                    console.error('[GG] template RPC failed', error);
                    delete this.templateLoading[key];
                    this._setLoading(false);
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
            this._setLoading(false);
            queue.forEach((cb) => cb());
        };
        const params = {
            table: this.table,
            grouplets_root: this.grouplets_root,
            grouplet_kwargs: this.grouplet_kw
        };
        this._setLoading(true);
        genro.serverCall(this.mapLoaderrpc, params,
            (mapBag, error) => {
                if (error) {
                    console.error('[GG] template map RPC failed', error);
                    delete this.templateLoading[sharedKey];
                    this._setLoading(false);
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

gnr.GroupletGridController._FORMULA_WORDS = new Set([
    'Math', 'Number', 'String', 'Date', 'JSON', 'parseInt', 'parseFloat',
    'isNaN', 'isFinite', 'NaN', 'Infinity', 'null', 'undefined', 'true',
    'false', 'new', 'typeof', 'instanceof', 'void', 'in', 'this']);


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
        // `mounted` = wrapper + drag handle exist; `bodyMounted` = chrome
        // and the grafted template subtree exist. With lazyTabs a tile can
        // be mounted (chip + wrapper) yet have no body until activated.
        this.bodyMounted = false;
        // True while a rAF is scheduled to graft the lazy body.
        this._bodyPending = false;
        this.isActive = false;
        this.isDragging = false;
        this.hasDelete = false;
        this.editmenuSpec = null;
        this.dragEnabled = false;
        this.position = null;
        this._tileDnDHandlers = null;
        this._handleDnDHandlers = null;
    }

    mount(position) {
        // Eager full mount (cards, and tabs without lazyTabs).
        this.mountWrapperOnly(position);
        this.mountBody();
    }

    mountWrapperOnly(position) {
        // Cheap half: wrapper + drag handle only. Used by lazyTabs to build
        // chips/wrappers upfront while deferring the expensive body graft.
        this.position = position || null;
        this._resolveTemplate();
        this._resolveDecorations();
        this._mountWrapper();
        this.tileNode.freeze();
        this._mountDragHandle();
        this.tileNode.unfreeze();
        this.mounted = true;
    }

    mountBody() {
        // Expensive half: chrome + grafted template subtree. Idempotent.
        // Called inline by mount(), or lazily by _activateTab on first show.
        if (this.bodyMounted) return;
        // A pending deferred graft is now moot (we're mounting now).
        this._cancelPendingBody();
        // The wrapper sourceNode `_class` already carries the correct active
        // state (set by _setActiveTabClasses before this graft is scheduled),
        // so the unfreeze re-render preserves display:block for the active
        // panel — no post-mount class re-assert needed.
        this.tileNode.freeze();
        this._mountChrome();
        this._mountBody();
        this.tileNode.unfreeze();
        // After unfreeze the subtree is attached under the live form, so
        // getFormHandler can resolve it: re-proxy so form-bound widgets
        // cache this.form and get cleanly unregistered on teardown.
        this.controller._reproxyForm(this.tileContent);
        this.bodyMounted = true;
    }

    rebuild() {
        // Re-render body + chrome in place (used on resourceField swap):
        // wrapper sourceNode and drag handle survive.
        if (!this.mounted) return;
        // Lazy wrapper-only tile: nothing to tear down — just build the
        // body for the first time (keeps bodyMounted coherent).
        if (!this.bodyMounted) {
            this._resolveTemplate();
            this._resolveDecorations();
            this.mountBody();
            return;
        }
        this.tileNode.freeze();
        this._destroyChrome();
        this._destroyBody();
        this._resolveTemplate();
        this._resolveDecorations();
        this._mountChrome();
        this._mountBody();
        this.tileNode.unfreeze();
    }

    _cancelPendingBody() {
        // The scheduled rAF guards on `mounted === false` / `bodyMounted`,
        // so clearing the flag is enough to neutralise a pending graft.
        this._bodyPending = false;
    }

    unmount() {
        this._cancelPendingBody();
        this._unwireTileDnD();
        this._unwireHandleDnD();
        // popNode does not propagate form de-registration to the grafted
        // widgets, so unregister them explicitly (symmetric with the
        // _reproxyForm done at mount). Otherwise they linger in the form
        // _register as orphans and break setLastSavedValues on save.
        this.controller._unproxyForm(this.tileContent);
        const bodyContent = this._hostNode().getValue('static');
        bodyContent.popNode(this.tileLabel);
        this.mounted = false;
        this.bodyMounted = false;
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
        // template rows are deleted from the entry row
        this.hasDelete = !!c.delitem && !c.rowTemplate;
        this.dragEnabled = !!c.dragCode;
        const editmenu = c.editmenu;
        this.editmenuSpec = (editmenu && typeof editmenu === 'object'
            && Object.keys(editmenu).length > 0) ? editmenu : null;
    }

    _hostNode() {
        return this.controller.bodyNode;
    }

    _mountWrapper() {
        const tileKw = this._wrapperKw();
        const bodyContent = this._hostNode().getValue();
        const extraKw = this.position ? {_position: this.position} : undefined;
        bodyContent._('div', this.tileLabel, tileKw, extraKw);
        this.tileNode = bodyContent.getNode(this.tileLabel);
        this.tileContent = this.tileNode.getValue();
    }

    _wrapperKw() {
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
            connect_onclick: function(evt) {
                const onChrome = evt && evt.target && evt.target.closest
                    && evt.target.closest('.grouplet_grid_row_delete,'
                        + '.grouplet_grid_row_kebab,.grouplet_grid_row_drag,'
                        + '.grouplet_grid_row_check');
                if (c.rowTemplate && !onChrome) c._onTemplateRowClick(pkey, evt);
                else c.selectTile(pkey);
            }
        };
        tileKw.onCreated = function(domnode) {
            tile.tileDom = domnode.sourceNode
                ? domnode.sourceNode.getDomNode()
                : domnode;
            // DnD is wired with native listeners only — no framework
            // dropTarget/onDrag_/onDrop_ kwargs. Symmetric to the chip
            // path; keeps nested grids decoupled from the outer
            // framework drag dispatch (cf. test_8 contacts).
            if (tile.dragEnabled && !c._isTabsLayout() && tile.tileDom) {
                tile._wireTileDnD(tile.tileDom);
            }
            if (c.phantom && tile.tileDom) tile._wireDropIfEmpty(tile.tileDom);
            if (c.rowCheckbox && tile.tileDom) tile._mountCheckbox(tile.tileDom);
        };
        return tileKw;
    }

    _mountCheckbox(tileDom) {
        // Plain DOM, rebuilt with the wrapper: it shows the controller's
        // selection, it holds none.
        const c = this.controller;
        const pkey = this.pkey;
        const box = document.createElement('input');
        box.type = 'checkbox';
        box.className = 'grouplet_grid_row_check';
        box.setAttribute('aria-label', _T('!!Select row'));
        box.checked = !!(c._multiKeys && c._multiKeys.includes(pkey));
        box.addEventListener('click', (e) => c._onRowCheck(pkey, e));
        tileDom.insertBefore(box, tileDom.firstChild);
    }

    _wireDropIfEmpty(tileDom) {
        // Checked once focus has settled outside the row: the cell's value
        // is committed on blur, after this focusout.
        const c = this.controller;
        const pkey = this.pkey;
        tileDom.addEventListener('focusout', () => {
            setTimeout(() => {
                if (tileDom.contains(document.activeElement)) return;
                c._dropIfEmpty(pkey);
            }, 0);
        });
    }

    _wireTileDnD(tileDom) {
        const c = this.controller;
        const dnd = c.dnd;
        const pkey = this.pkey;
        const onDragOver = (e) => dnd.tileDragOver(e, tileDom);
        const onDragLeave = (e) => dnd.tileDragLeave(e, tileDom);
        const onDrop = (e) => dnd.tileDrop(e, tileDom, pkey);
        tileDom.addEventListener('dragover', onDragOver);
        tileDom.addEventListener('dragleave', onDragLeave);
        tileDom.addEventListener('drop', onDrop);
        this._tileDnDHandlers = {
            dom: tileDom,
            handlers: {dragover: onDragOver, dragleave: onDragLeave,
                       drop: onDrop}
        };
    }

    _unwireTileDnD() {
        const entry = this._tileDnDHandlers;
        if (!entry) return;
        Object.keys(entry.handlers).forEach((evt) => {
            entry.dom.removeEventListener(evt, entry.handlers[evt]);
        });
        this._tileDnDHandlers = null;
    }

    _mountDragHandle() {
        // `⠿` drag source — sub-sourceNode for layout consistency, but
        // DnD is wired natively in `onCreated` (same model as the tile
        // drop zone above). Stays out of the framework drag dispatch.
        if (!this.dragEnabled) return;
        const pkey = this.pkey;
        const tile = this;
        const handleLabel = '_grtile_drag_' + pkey;
        this.tileContent._('div', handleLabel, {
            _class: 'grouplet_grid_row_drag',
            title: _T('!!Drag to reorder'),
            innerHTML: '<span class="grouplet_grid_drag_icon">⠿</span>',
            onCreated: function(domnode) {
                const handleDom = domnode.sourceNode
                    ? domnode.sourceNode.getDomNode()
                    : domnode;
                if (handleDom) tile._wireHandleDnD(handleDom);
            }
        });
    }

    _wireHandleDnD(handleDom) {
        const c = this.controller;
        const dnd = c.dnd;
        const pkey = this.pkey;
        const tile = this;
        handleDom.setAttribute('draggable', 'true');
        const onDragStart = (e) => dnd.tileDragStart(e, tile.tileDom, pkey);
        const onDragEnd = () => dnd.tileDragEnd(tile.tileDom);
        handleDom.addEventListener('dragstart', onDragStart);
        handleDom.addEventListener('dragend', onDragEnd);
        this._handleDnDHandlers = {
            dom: handleDom,
            handlers: {dragstart: onDragStart, dragend: onDragEnd}
        };
    }

    _unwireHandleDnD() {
        const entry = this._handleDnDHandlers;
        if (!entry) return;
        Object.keys(entry.handlers).forEach((evt) => {
            entry.dom.removeEventListener(evt, entry.handlers[evt]);
        });
        this._handleDnDHandlers = null;
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
        if (this._usesRowTemplate()) {
            const c = this.controller;
            if (c.structAdapter) {
                c._structReadonlyRow().deepCopy().getNodes().forEach((n) => {
                    c._graftNode(this.tileContent, n);
                });
            } else {
                this.tileContent._('div', '_grtile_summary_' + this.pkey, {
                    template: c.rowTemplate,
                    datasource: '^.',
                    _class: 'grouplet_grid_row_summary'
                });
            }
            return;
        }
        // Each tile owns its own template clone; framework-generated
        // nodeIds are namespaced (see _namespaceFrameworkNodeIds).
        const cloned = this.templateSource.deepCopy();
        this.controller._namespaceFrameworkNodeIds(cloned, this.pkey);
        if (!this._keepsKeepable()) {
            // a keeper on every row would keep nothing: only the entry row,
            // and a struct one keeps by its header pins
            cloned.walk((n) => {
                if (n.attr) delete n.attr.keepable;
            }, 'static');
        }
        cloned.getNodes().forEach((n) => {
            this.controller._graftNode(this.tileContent, n);
        });
    }

    _keepsKeepable() {
        return false;
    }

    _usesRowTemplate() {
        // a template, or rowTemplate=True on a struct grid
        const c = this.controller;
        return !!c.rowTemplate && (!!c.structAdapter || typeof c.rowTemplate === 'string'
                                   || c.rowTemplate instanceof gnr.GnrBag);
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


// The trailing blank row of additem='phantom'. Bound to the controller's
// phantomPath and detached from the form (parentForm:false): its cells are
// neither stored, nor validated, nor locked with the form until promoted.

gnr.GroupletGridPhantomTile = class GroupletGridPhantomTile extends gnr.GroupletGridTile {

    constructor(controller, pkey) {
        super(controller, pkey || '_phantom');
        this.stripValidations = true;
    }

    _resolveTemplate() {
        this.templateKey = '__default__';
        this.templateSource = this.controller.templateSources.__default__;
    }

    _usesRowTemplate() {
        return false;
    }

    _resolveDecorations() {
        this.hasDelete = false;
        this.dragEnabled = false;
        this.editmenuSpec = null;
    }

    _mountWrapper() {
        super._mountWrapper();
        // parentForm:false takes effect only when the wrapper is built, and
        // _reproxyForm may walk the body before that: cut the form lookup now.
        this.tileNode.form = null;
    }

    _wrapperKw() {
        const c = this.controller;
        const tile = this;
        return {
            datapath: c.phantomPath,
            parentForm: false,
            _class: 'grouplet_grid_row grouplet_grid_row--phantom',
            nodeId: this.tileNodeId,
            onCreated: function(domnode) {
                tile.tileDom = domnode.sourceNode
                    ? domnode.sourceNode.getDomNode()
                    : domnode;
                if (!tile.tileDom) return;
                if (c.dnd) c._wirePhantomDnD(tile.tileDom);
                tile.tileDom.addEventListener('paste', (e) => c._onBlankPaste(e, tile));
            }
        };
    }

    _mountBody() {
        super._mountBody();
        // The hint goes on the first required free-text field, else the
        // first free-text one, else the first field it fits.
        let first = null;
        let text = null;
        let required = null;
        this.tileContent.walk((n) => {
            const attr = n.attr || {};
            const tag = (attr.tag || '').toLowerCase();
            if (gnr.GroupletGridPhantomTile.HINT_TAGS.has(tag)) {
                first = first || n;
                if (gnr.GroupletGridPhantomTile.TEXT_TAGS.has(tag)) {
                    text = text || n;
                    if (attr.validate_notnull) required = required || n;
                }
            }
            // A required field would paint the blank row invalid.
            if (this.stripValidations) {
                Object.keys(attr).forEach((k) => {
                    if (k.indexOf('validate_') === 0) delete attr[k];
                });
            }
        }, 'static');
        const hint = required || text || first;
        if (hint && !hint.attr.placeholder) {
            hint.attr.placeholder = _T(this.controller.additemKw.label || '!!New row');
        }
    }
};

// The entry row of additem='entry': a phantom tile mounted in the entry
// slot above the rows, keeping its validations, with an add button where
// rows have their `×`.

gnr.GroupletGridEntryTile = class GroupletGridEntryTile extends gnr.GroupletGridPhantomTile {

    constructor(controller) {
        super(controller, '_entry');
        this.stripValidations = false;
    }

    _keepsKeepable() {
        return !this.controller.structAdapter;
    }

    _resolveTemplate() {
        super._resolveTemplate();
        if (this.controller.structAdapter) {
            this.templateSource = this.controller._structEntryRow();
        }
    }

    _hostNode() {
        return this.controller.entryNode;
    }

    _wrapperKw() {
        const c = this.controller;
        const tile = this;
        return {
            datapath: c.entryPath,
            parentForm: false,
            _class: 'grouplet_grid_row grouplet_grid_row--entry',
            nodeId: this.tileNodeId,
            onCreated: function(domnode) {
                tile.tileDom = domnode.sourceNode
                    ? domnode.sourceNode.getDomNode()
                    : domnode;
                if (tile.tileDom) {
                    tile.tileDom.addEventListener('keydown',
                        (e) => c._onEntryKeydown(e), true);
                    tile.tileDom.addEventListener('focusin', (e) => {
                        c._entryWidget = dijit.getEnclosingWidget(e.target);
                    });
                    tile.tileDom.addEventListener('paste', (e) => c._onBlankPaste(e, tile));
                }
            }
        };
    }

    _mountChrome() {
        const c = this.controller;
        const label = '_grtile_add_' + this.pkey;
        this.tileContent._('div', label, {
            _class: 'grouplet_grid_row_add',
            tip: _T('!!Add (Enter)'),
            connect_onclick: function() { c._commitEntry(); }
        });
        // the glyph is CSS content: `↵`, or `✓` while a row is edited
        this.tileContent.getNode(label).getValue()._('span', 'glyph', {
            _class: 'grouplet_grid_row_add_glyph'});
        // the edited template row's delete, beside the save button
        if (c.rowTemplate && c.delitem) {
            this.tileContent._('div', '_grtile_trash_' + this.pkey, {
                _class: 'grouplet_grid_row_trash',
                tip: _T('!!Delete row'),
                connect_onclick: function() { c._deleteSelected(); }
            });
        }
    }
};

gnr.GroupletGridPhantomTile.HINT_TAGS = new Set([
    'textbox', 'simpletextarea', 'dbselect', 'dbcombobox', 'combobox',
    'filteringselect']);
gnr.GroupletGridPhantomTile.TEXT_TAGS = new Set(['textbox', 'simpletextarea']);
