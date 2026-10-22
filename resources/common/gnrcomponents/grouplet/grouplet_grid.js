// groupletGrid — JS classes on gnr.*:
//   GroupletGridStructAdapter, GroupletGridDnD,
//   GroupletGridController, GroupletGridTile.

// Attribute keys whose value may carry a framework-generated
// `grpgrid_*` reference, rewritten per-row clone by
// `_namespaceFrameworkNodeIds`.
const NAMESPACED_ATTRS = ['nodeId', 'dragCode'];

// The printed rows live in a frame of their own, out of the page's CSS.
const PRINT_CSS = 'body{font:10pt sans-serif;margin:0}'
    + 'table{border-collapse:collapse;width:100%}'
    + 'th,td{padding:2pt 4pt;border-bottom:0.5pt solid #999;text-align:left;vertical-align:top}'
    + 'th{border-bottom-width:1pt}.num{text-align:right}tr{break-inside:avoid}';

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
    //   - drop = where the slot opened: before or after the row the
    //     pointer is over (`<target` / `>target`); without a slot (tabs)
    //     "insert-after" (`>target`, aligned with the tree).
    //
    // Internals (this commit): all listeners are `addEventListener`s
    // wired on the rendered DOM — no sourceNode `dropTarget`/`onDrag_*`
    // kwargs anywhere. Symmetric to the chip path (test_8 nested) and
    // independent of framework-side pointer-events / inherited-attrs
    // resolution.

    constructor(controller) {
        this.controller = controller;
        this.appendTargets = new Map();
    }

    dropType() {
        return 'gg_tile_' + this.controller.dragCode;
    }

    _writePayload(dataTransfer, pkey, rowKeys) {
        const c = this.controller;
        try {
            genro.dom.setInDataTransfer(dataTransfer, this.dropType(),
                {rowKey: pkey, rowKeys: rowKeys, sourceNodeId: c.nodeId});
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
            // offsetWidth counts paddings and borders: so does the clone;
            // the image is taken at once, not halfway through the row fade-in
            clone.style.boxSizing = 'border-box';
            clone.style.animation = 'none';
            clone.style.width = sourceDom.offsetWidth + 'px';
            // several rows dragged: the grabbed one shows how many
            if (opts && opts.count > 1) clone.setAttribute('data-gg-count', opts.count);
            let holder = clone;
            if (opts && opts.struct) {
                // Struct chrome is on the container, the clone is not.
                // Tag it so the cell rules still apply outside the tree.
                clone.classList.add('grouplet_grid_struct_drag_clone',
                    'grouplet_grid--struct');
                const containerDom = this.controller._containerDom();
                const cols = containerDom.style.getPropertyValue(
                    '--gg-struct-columns');
                if (cols) clone.style.setProperty('--gg-struct-columns', cols);
            } else {
                // a card is styled by the grid it sits in (paddings, band,
                // tokens): the clone gets a copy of that chain, outside the tree
                const containerDom = this.controller._containerDom();
                holder = document.createElement('div');
                holder.className = containerDom.className;
                holder.style.cssText = containerDom.style.cssText;
                const body = document.createElement('div');
                body.className = 'grouplet_grid_body';
                holder.appendChild(body);
                body.appendChild(clone);
            }
            // the browser takes the image from the screen where it lies: above
            // everything for that instant, or the page covering it comes along
            Object.assign(holder.style, {position: 'fixed', top: '0px', left: '0px',
                                         zIndex: '2147483647', pointerEvents: 'none'});
            aux.appendChild(holder);
            const rect = sourceDom.getBoundingClientRect();
            e.dataTransfer.setDragImage(clone,
                e.clientX - rect.left,
                e.clientY - rect.top);
            setTimeout(function() {
                if (holder.parentNode) holder.parentNode.removeChild(holder);
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
        const rowKeys = data.rowKeys || [data.rowKey];
        if (data.sourceNodeId === c.nodeId && rowKeys.includes(targetPkey)) return;
        genro.publish(c.actionTopic, {
            action: 'move',
            rowKey: data.rowKey,
            rowKeys: rowKeys,
            sourceNodeId: data.sourceNodeId,
            position: '>' + targetPkey
        });
    }

    _startDrag(e, dom, pkey, opts) {
        const c = this.controller;
        const rowKeys = c._dragKeys(pkey);
        if (!c._canMoveRowFrom(c, rowKeys)) {
            e.preventDefault();
            e.stopPropagation();
            return;
        }
        gnr.GroupletGridDnD.endDrag();
        this._writePayload(e.dataTransfer, pkey, rowKeys);
        this._setDragImage(e, dom, objectUpdate({count: rowKeys.length}, opts || {}));
        const doms = rowKeys.map((k) => (k === pkey) ? dom : (c.tiles[k] && c.tiles[k].domNode()))
            .filter(Boolean);
        gnr.GroupletGridDnD.source = {controller: c, rowKey: pkey, rowKeys: rowKeys, dom: dom, doms: doms};
        doms.forEach((d) => d.classList.add('draggedItem'));
        // lifted after dragstart: hiding the source now would cancel the drag
        setTimeout(() => this._lift(doms), 0);
        document.body.classList.add('drag_started');
        document.addEventListener('dragend', gnr.GroupletGridDnD.endDrag, true);
        document.addEventListener('drop', gnr.GroupletGridDnD.endDrag, true);
        document.addEventListener('keydown', gnr.GroupletGridDnD.cancelDrag, true);
        document.addEventListener('dragover', gnr.GroupletGridDnD.watchOutside, true);
        e.stopPropagation();
    }

    static cancelDrag(e) {
        if (e.key === 'Escape') gnr.GroupletGridDnD.endDrag();
    }

    static endDrag() {
        const DnD = gnr.GroupletGridDnD;
        if (DnD.receiver) DnD.receiver.dnd.clearHighlight();
        if (DnD.source) {
            (DnD.source.doms || [DnD.source.dom]).forEach((d) => d.classList.remove('draggedItem'));
        }
        DnD.source = null;
        document.body.classList.remove('drag_started');
        document.removeEventListener('dragend', DnD.endDrag, true);
        document.removeEventListener('drop', DnD.endDrag, true);
        document.removeEventListener('keydown', DnD.cancelDrag, true);
        document.removeEventListener('dragover', DnD.watchOutside, true);
        // the drop handlers run after this capture listener and still read the slot
        setTimeout(DnD.settle, 0);
    }

    clearHighlight(dom) {
        const current = gnr.GroupletGridDnD.receiver;
        if (!current || current.dnd !== this || (dom && current.dom !== dom)) return;
        current.dom.classList.remove('canBeDropped', 'cannotBeDropped');
        gnr.GroupletGridDnD.receiver = null;
    }

    _highlight(dom, allowed) {
        const current = gnr.GroupletGridDnD.receiver;
        if (current) current.dnd.clearHighlight();
        dom.classList.add(allowed ? 'canBeDropped' : 'cannotBeDropped');
        gnr.GroupletGridDnD.receiver = {dnd: this, dom: dom};
    }

    _dragOver(e, dom, atEnd = false) {
        if (!this._dataTransferHasOurType(e.dataTransfer)) return;
        const source = gnr.GroupletGridDnD.source;
        const allowed = !!source && !dom.classList.contains('draggedItem')
            && this.controller._canMoveRowFrom(source.controller, source.rowKeys || source.rowKey);
        e.stopPropagation();
        e.dataTransfer.dropEffect = allowed ? 'move' : 'none';
        const slotted = allowed && this._slotMode();
        if (slotted && !atEnd && dom !== this._bodyDom()) {
            // over a row the open slot is the feedback, the row stays as it is
            const current = gnr.GroupletGridDnD.receiver;
            if (current) current.dnd.clearHighlight();
        } else {
            this._highlight(dom, allowed);
        }
        if (slotted) this._trackSlot(e, atEnd);
        if (allowed) e.preventDefault();
    }

    _dropData(e) {
        if (!this._dataTransferHasOurType(e.dataTransfer)) return null;
        e.stopPropagation();
        e.preventDefault();
        const data = genro.dom.getFromDataTransfer(e.dataTransfer, this.dropType());
        const c = this.controller;
        const source = data && c._findSourceController(data.sourceNodeId);
        return source && c._canMoveRowFrom(source, data.rowKeys || data.rowKey) ? data : null;
    }

    tileDragStart(e, tileDom, pkey) {
        this._startDrag(e, tileDom, pkey, {
            struct: this.controller._containerDom().classList.contains('grouplet_grid--struct')
        });
    }

    tileDragEnd() {
        gnr.GroupletGridDnD.endDrag();
    }

    tileDragOver(e, tileDom) {
        this._dragOver(e, tileDom);
    }

    tileDragLeave(e, tileDom) {
        if (!tileDom.contains(e.relatedTarget)) this.clearHighlight(tileDom);
    }

    tileDrop(e, tileDom, pkey) {
        this.clearHighlight(tileDom);
        if (this._dropAtSlot(e)) return;
        const data = this._dropData(e);
        if (data) this.onDrop(data, pkey);
    }

    chipDragStart(e, chipDom, pkey) {
        this._startDrag(e, chipDom, pkey);
    }

    chipDragOver(e, chipDom) {
        this._dragOver(e, chipDom);
    }

    chipDragLeave(e, chipDom) {
        this.tileDragLeave(e, chipDom);
    }

    chipDragEnd() {
        gnr.GroupletGridDnD.endDrag();
    }

    chipDrop(e, chipDom, pkey) {
        this.tileDrop(e, chipDom, pkey);
    }

    addBtnDragOver(e) {
        // over the body the slot follows the nearest row, elsewhere (add
        // button, blank row) it opens at the tail
        this._dragOver(e, e.currentTarget, e.currentTarget !== this._bodyDom());
    }

    addBtnDragLeave(e) {
        this.tileDragLeave(e, e.currentTarget);
    }

    addBtnDrop(e) {
        this.clearHighlight(e.currentTarget);
        if (this._dropAtSlot(e)) return;
        const data = this._dropData(e);
        if (!data) return;
        const c = this.controller;
        const rowKeys = data.rowKeys || [data.rowKey];
        const own = data.sourceNodeId === c.nodeId;
        // the tail is after the last row that is not moving
        const nodes = c.dataStore.getNodes().filter((n) => !(own && rowKeys.includes(n.label)));
        const lastKey = nodes.length ? nodes[nodes.length - 1].label : null;
        if (own && (!lastKey || c.dataStore.indexOfKey(lastKey) < c.dataStore.indexOfKey(rowKeys[0]))) return;
        genro.publish(c.actionTopic, {
            action: 'move',
            rowKey: data.rowKey,
            rowKeys: rowKeys,
            sourceNodeId: data.sourceNodeId,
            position: lastKey ? ('>' + lastKey) : ''
        });
    }

    wireAppendTarget(dom, body) {
        if (!dom || this.appendTargets.has(dom)) return;
        const handlers = {
            dragover: (e) => {
                if (!body || e.target === dom) this.addBtnDragOver(e);
            },
            dragleave: (e) => this.addBtnDragLeave(e),
            drop: (e) => {
                if (!body || e.target === dom) this.addBtnDrop(e);
            }
        };
        Object.keys(handlers).forEach((name) => dom.addEventListener(name, handlers[name]));
        this.appendTargets.set(dom, handlers);
        if (body) dom.classList.add('grouplet_grid_body--drop');
    }

    unwireAppendTarget(dom) {
        this.clearHighlight(dom);
        const handlers = this.appendTargets.get(dom);
        if (!handlers) return;
        Object.keys(handlers).forEach((name) => dom.removeEventListener(name, handlers[name]));
        dom.classList.remove('grouplet_grid_body--drop');
        this.appendTargets.delete(dom);
    }

    // ====================================================================
    //  The slot: while a row is dragged a gap opens where it would land,
    //  before or after the row under the pointer; the rows around it slide
    //  aside (FLIP). The dragged rows are lifted out, their home is the
    //  slot's starting place. One slot for the page, across grids.
    // ====================================================================

    _bodyDom() {
        const node = this.controller.bodyNode;
        return (node && node.getDomNode) ? node.getDomNode() : null;
    }

    _slotMode() {
        return !this.controller._isTabsLayout() && !!this._bodyDom();
    }

    _slotRows(body) {
        // the visible rows of this grid, in their order
        const c = this.controller;
        const keys = new Map();
        Object.keys(c.tiles).forEach((k) => {
            const dom = c.tiles[k].domNode();
            if (dom) keys.set(dom, k);
        });
        return Array.from(body.children)
            .filter((dom) => keys.has(dom) && !dom.classList.contains('grouplet_grid_row--lifted'))
            .map((dom) => ({dom: dom, key: keys.get(dom)}));
    }

    _trackSlot(e, atEnd) {
        const DnD = gnr.GroupletGridDnD;
        // while the rows slide their rects are in flight: placing the slot
        // on them would bounce it
        if (DnD.steadyAt && Date.now() < DnD.steadyAt) return;
        const body = this._bodyDom();
        const rows = this._slotRows(body);
        let ref;
        let position;
        if (rows.length && !atEnd) {
            const row = DnD.nearestRow(rows, e.clientX, e.clientY);
            const before = DnD.dropsBefore(row.rect, e.clientX, e.clientY, body.clientWidth);
            ref = before ? row.dom : row.dom.nextElementSibling;
            position = (before ? '<' : '>') + row.key;
        } else if (rows.length) {
            const last = rows[rows.length - 1];
            ref = last.dom.nextElementSibling;
            position = '>' + last.key;
        } else {
            const blank = this.controller.phantomTile && this.controller.phantomTile.domNode();
            ref = (blank && blank.parentNode === body) ? blank : null;
            position = '';
        }
        this._placeSlot(body, ref, position);
    }

    _placeSlot(body, ref, position) {
        const DnD = gnr.GroupletGridDnD;
        const slot = DnD.slot;
        if (slot && slot.dom.parentNode === body && (ref === slot.dom || slot.dom.nextElementSibling === ref)) {
            slot.position = position;
            slot.dnd = this;
            return;
        }
        const dom = this._slotDom();
        DnD.flip([body, slot && slot.body], () => {
            if (slot) slot.dom.remove();
            body.insertBefore(dom, (ref === (slot && slot.dom)) ? null : ref);
            DnD.slot = {dnd: this, body: body, dom: dom, position: position};
        });
        DnD.open(dom, body);
        if (gnr.GroupletCard.animates(dom)) DnD.steadyAt = Date.now() + DnD.SLIDE_MS;
    }

    _slotDom() {
        // as tall as the lifted row, and a drop target of its own
        const DnD = gnr.GroupletGridDnD;
        const dom = document.createElement('div');
        dom.className = 'grouplet_grid_drop_slot';
        if (DnD.lift && DnD.lift.height) dom.style.height = DnD.lift.height + 'px';
        dom.addEventListener('dragover', (e) => {
            if (!this._dataTransferHasOurType(e.dataTransfer)) return;
            e.stopPropagation();
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        });
        dom.addEventListener('drop', (e) => {
            const slot = DnD.slot;
            if (slot && slot.dom === dom) slot.dnd._dropAtSlot(e);
        });
        return dom;
    }

    _lift(doms) {
        const DnD = gnr.GroupletGridDnD;
        const source = DnD.source;
        if (!source || source.controller !== this.controller || !this._slotMode()) return;
        const body = this._bodyDom();
        const home = doms.find((d) => d.parentNode === body);
        if (!home) return;
        DnD.lift = {body: body, doms: doms, home: home, height: home.offsetHeight};
        const dom = this._slotDom();
        DnD.flip([body], () => {
            body.insertBefore(dom, home);
            doms.forEach((d) => d.classList.add('grouplet_grid_row--lifted'));
            // at home a drop moves nothing
            DnD.slot = {dnd: this, body: body, dom: dom, position: null};
        });
    }

    _dropAtSlot(e) {
        // false: no slot of ours, the caller drops the old way
        const DnD = gnr.GroupletGridDnD;
        const slot = DnD.slot;
        if (!slot || slot.dnd !== this) return false;
        const data = this._dropData(e);
        const lift = DnD.lift;
        const c = this.controller;
        const rowKeys = data ? (data.rowKeys || [data.rowKey]) : [];
        const own = !!data && data.sourceNodeId === c.nodeId;
        const moves = !!data && slot.position !== null
            && !(own && rowKeys.includes(slot.position.slice(1)));
        const from = new Map();
        if (lift) {
            const rect = slot.dom.getBoundingClientRect();
            lift.doms.forEach((d) => from.set(d, rect));
        }
        DnD.flip([slot.body, lift && lift.body], () => {
            slot.dom.remove();
            if (lift) lift.doms.forEach((d) => d.classList.remove('grouplet_grid_row--lifted'));
            DnD.slot = null;
            DnD.lift = null;
            if (moves) {
                genro.publish(c.actionTopic, {
                    action: 'move',
                    rowKey: data.rowKey,
                    rowKeys: rowKeys,
                    sourceNodeId: data.sourceNodeId,
                    position: slot.position
                });
            }
        }, from);
        return true;
    }

    static nearestRow(rows, x, y) {
        // the row under the pointer, else the closest one (the gaps of a grid)
        let best = null;
        let bestDistance = Infinity;
        rows.forEach((row) => {
            const r = row.dom.getBoundingClientRect();
            const dx = Math.max(r.left - x, 0, x - r.right);
            const dy = Math.max(r.top - y, 0, y - r.bottom);
            const distance = dx * dx + dy * dy;
            if (distance < bestDistance) {
                bestDistance = distance;
                best = {dom: row.dom, key: row.key, rect: r};
            }
        });
        return best;
    }

    static dropsBefore(rect, x, y, flowWidth) {
        // cards side by side read left to right, rows top to bottom
        if (rect.width < flowWidth * 0.66) return x < rect.left + rect.width / 2;
        return y < rect.top + rect.height / 2;
    }

    static flip(bodies, mutate, from) {
        // the rows keep their place on screen across `mutate`, then slide
        // to the new one; `from` gives the start of rows that were hidden
        const items = [];
        bodies.filter(Boolean).forEach((body) => {
            Array.from(body.children).forEach((el) => {
                if (!el.classList.contains('grouplet_grid_drop_slot')) items.push(el);
            });
        });
        const before = new Map();
        items.forEach((el) => {
            before.set(el, (from && from.get(el)) || el.getBoundingClientRect());
        });
        mutate();
        if (!items.length || !gnr.GroupletCard.animates(items[0])) return;
        items.forEach((el) => {
            const a = before.get(el);
            const b = el.getBoundingClientRect();
            if (!b.width && !b.height) return;
            const dx = a.left - b.left;
            const dy = a.top - b.top;
            if (!dx && !dy) return;
            el.animate([{transform: `translate(${dx}px, ${dy}px)`}, {transform: 'none'}],
                       {duration: gnr.GroupletGridDnD.SLIDE_MS, easing: 'ease-out'});
        });
    }

    static open(dom, body) {
        // a full-width slot grows in height, one among cards fades in
        if (!gnr.GroupletCard.animates(dom)) return;
        const frames = (dom.offsetWidth >= body.clientWidth * 0.66)
            ? [{height: '0px', opacity: 0}, {height: dom.offsetHeight + 'px', opacity: 1}]
            : [{opacity: 0, transform: 'scale(0.92)'}, {opacity: 1, transform: 'none'}];
        dom.animate(frames, {duration: gnr.GroupletGridDnD.SLIDE_MS, easing: 'ease-out'});
    }

    static watchOutside(e) {
        // the pointer over no grid (dragleave cannot tell: its relatedTarget
        // is often null): the slot goes back where the rows came from
        const target = e.target;
        const inGrid = target && target.closest && target.closest('.grouplet_grid_container');
        if (!inGrid) gnr.GroupletGridDnD.slotHome();
    }

    static slotHome() {
        const DnD = gnr.GroupletGridDnD;
        const slot = DnD.slot;
        const lift = DnD.lift;
        if (!slot) return;
        if (!lift) {
            DnD.flip([slot.body], () => slot.dom.remove());
            DnD.slot = null;
            return;
        }
        if (slot.position === null) return;
        DnD.flip([slot.body, lift.body], () => {
            lift.body.insertBefore(slot.dom, lift.home);
            slot.body = lift.body;
            slot.position = null;
        });
    }

    static settle() {
        // after a drag that dropped nowhere: the slot closes, the rows come back
        const DnD = gnr.GroupletGridDnD;
        const slot = DnD.slot;
        const lift = DnD.lift;
        if (!slot && !lift) return;
        const from = new Map();
        if (slot && lift) {
            const rect = slot.dom.getBoundingClientRect();
            lift.doms.forEach((d) => from.set(d, rect));
        }
        DnD.flip([slot && slot.body, lift && lift.body], () => {
            if (slot) slot.dom.remove();
            if (lift) lift.doms.forEach((d) => d.classList.remove('grouplet_grid_row--lifted'));
        }, from);
        DnD.slot = null;
        DnD.lift = null;
    }

    destroy() {
        this.appendTargets.forEach((handlers, dom) => this.unwireAppendTarget(dom));
        this.clearHighlight();
        const source = gnr.GroupletGridDnD.source;
        if (source && source.controller === this.controller) gnr.GroupletGridDnD.endDrag();
    }

};


gnr.GroupletGridDnD.SLIDE_MS = 180;


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
        // Splice the Bag's _nodes array in place: no del/ins triggers
        // fire, so nested widgets whose datapath is anchored to the
        // moved row (e.g. inner groupletGrids on `.contacts`) keep a
        // valid parent chain. DOM mirroring is the controller's job.
        if (typeof position !== 'string') return null;
        const op = position.charAt(0);
        if (op !== '<' && op !== '>') return null;
        const targetKey = position.slice(1);
        const bag = this.getData();
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

    // Filter stubs — silent no-ops: a filter will hide tiles on top of
    // the store, never mutating the underlying Bag.
    setFilter(_cb) {}
    clearFilter() {}

    // Sort: an order on top of the Bag ({field, store}); the Bag itself is
    // reordered only with `store`, through applySortToStore.
    setSort(spec) {
        this._sortedBy = (typeof spec === 'string') ? {field: spec} : (spec || null);
    }

    clearSort() {
        this._sortedBy = null;
    }

    sortedKeys() {
        const data = this.getData();
        const nodes = (data instanceof gnr.GnrBag) ? data.getNodes() : [];
        if (!this._sortedBy) return nodes.map((n) => n.label);
        const field = this._sortedBy.field;
        const compare = gnr.GroupletGridController.naturalCompare;
        return nodes.map((n, i) => {
            const v = n.getValue();
            return {key: n.label, idx: i, value: (v instanceof gnr.GnrBag) ? v.getItem(field) : null};
        }).sort((a, b) => compare(a.value, b.value) || a.idx - b.idx).map((e) => e.key);
    }

    applySortToStore() {
        // In place, as moveRow: no del/ins triggers, nested datapaths stay valid.
        if (!this._sortedBy || !this._sortedBy.store) return false;
        const data = this.getData();
        if (!(data instanceof gnr.GnrBag)) return false;
        const order = this.sortedKeys();
        const nodes = data._nodes;
        if (order.every((k, i) => nodes[i].label === k)) return false;
        const byKey = {};
        nodes.forEach((n) => { byKey[n.label] = n; });
        nodes.splice(0, nodes.length, ...order.map((k) => byKey[k]));
        return true;
    }

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
        // True, False, or '^path' / '=path' / '==expr' (over the row's fields)
        // read as the row's menu opens
        this.delitem = kw.delitem || false;
        this.copyitem = kw.copyitem || false;
        this.editmenu = (kw.editmenu === undefined) ? false : kw.editmenu;
        this.additemKw = kw.additem_kw || {};
        this.delitemKw = kw.delitem_kw || {};
        this.copyitemKw = kw.copyitem_kw || {};
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
        // rowCheckbox: a checkbox per row and one for all, as in a mail list;
        // on cards it is the only way to select them
        this.rowCheckbox = !!(kw.rowCheckbox && Object.keys(this.selectionmenu).length);
        // Grids sharing a selectionGroup act on their selections together:
        // one count, one delete, `selection` = [{grid, rowKeys}] to actions.
        this.selectionGroup = kw.selectionGroup || null;
        if (this.selectionGroup) gnr.GroupletGridController._groupSet(this.selectionGroup).add(this);
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
        this.titleTemplate = gnr.GroupletCard.compileTemplate(kw.titleTemplate);
        this.sortField = kw.sortField || null;
        if (this.sortField) {
            this.dataStore.setSort({field: this.sortField, store: !!kw.sortStore});
        }
        this._dirtyRows = new Set();
        // collapsible cards: True starts them open, 'closed' collapsed; a
        // collapsed card shows one summary line (collapsedTemplate, else the
        // tab title). With chromeSide that line is the band's title, always
        // shown, and a collapsed card is its band.
        this.collapsible = kw.collapsible || false;
        this.chromeSide = kw.chromeSide || null;
        // the card profile (tools, doc, title): the resource's, then the
        // caller's; with resourceField each row's resource adds its own
        this.card = kw.card || {};
        this.templateCards = {};
        this._cardProfiles = {};
        this.collapsedTemplate = gnr.GroupletCard.compileTemplate(kw.collapsedTemplate)
            || this.titleTemplate;
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
            that._wireBodyDnD();
            that._refreshRowMenu(null);
            that._initChangeManager();
            that.newDataStore();
            that._mountSelectionBar();
            that._wireChromeClicks();
            that._wireClipboard();
            that._updateAddBtnState();
        });
    }

    destroy() {
        if (this._destroyed) return;
        this._destroyed = true;
        if (gnr.GroupletGridController._lastSelected === this) gnr.GroupletGridController._lastSelected = null;
        this.sourceNode.unregisterSubscription(this.actionTopic);
        if (this.selectionGroup) {
            gnr.GroupletGridController._groupSet(this.selectionGroup).delete(this);
            this._refreshGroupBars();
        }
        Object.keys(this.tiles).forEach((pkey) => this._destroyTile(pkey));
        this._unmountPhantom();
        this._unmountEntry();
        if (this._pendingForm) this._pendingForm.unregisterPendingEditor(this.nodeId);
        gnr.GroupletGridController._entryGrids.delete(this);
        const phantomBag = genro.getData(this.phantomPath);
        if (phantomBag instanceof gnr.GnrBag) {
            phantomBag.unsubscribe(this._phantomSubscriberId());
        }
        const entryBag = genro.getData(this.entryPath);
        if (entryBag instanceof gnr.GnrBag) {
            entryBag.unsubscribe(this._entrySubscriberId());
        }
        this._teardownLayoutAffordances();
        this._unwireClipboard();
        if (this.dnd) this.dnd.destroy();
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
        this.dataStore.applySortToStore();
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
            this._onRowContentChanged(kw.node, storeNode);
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

    _rowChangeOf(changedNode, storeNode) {
        // {pkey, path}: the row a nested change belongs to, and the path
        // from that row to the changed node.
        let cur = changedNode;
        let path = null;
        while (cur) {
            const parent = cur.getParentNode && cur.getParentNode();
            if (!parent) return null;
            if (parent === storeNode) return {pkey: cur.label, path: path};
            path = (path === null) ? cur.label : (cur.label + '.' + path);
            cur = parent;
        }
        return null;
    }

    _onRowContentChanged(changedNode, storeNode) {
        const change = this._rowChangeOf(changedNode, storeNode);
        if (!change || !change.pkey) return;
        if (this._isTabsLayout()) {
            if (this.titleTemplate) {
                this._scheduleRowRefresh(change.pkey);
            } else if (this.titleField && change.path === this.titleField) {
                this._refreshTabTitle(change.pkey);
            }
            if (this.sortField && change.path === this.sortField) {
                this._scheduleRowRefresh(null);
            }
        } else if (this._showsRowTitle(change.pkey)) {
            this._scheduleRowRefresh(change.pkey);
        }
    }

    _showsRowTitle(pkey) {
        // a band shows its title open or folded, a corner card only folded
        const card = this.tiles[pkey] && this.tiles[pkey].card;
        if (card) return !!card.titleDom;
        return this.collapsible && this.isCollapsed(pkey);
    }

    _scheduleRowRefresh(pkey) {
        // A template total reads the whole row: a burst of nested changes
        // (a pasted block, a moved subtree) is drawn once. null = re-sort.
        this._dirtyRows.add(pkey);
        if (this._rowRefreshScheduled) return;
        this._rowRefreshScheduled = true;
        setTimeout(() => {
            this._rowRefreshScheduled = false;
            const dirty = Array.from(this._dirtyRows);
            this._dirtyRows.clear();
            if (this._destroyed) return;
            dirty.forEach((k) => {
                if (k === null) return;
                if (this._isTabsLayout()) this._refreshTabTitle(k);
                else this._refreshRowTitle(k);
            });
            if (dirty.includes(null)) this._sortTabs();
        }, 0);
    }

    _refreshTabTitle(pkey) {
        const chip = this._tabsByPkey[pkey];
        const titleDom = chip && chip.querySelector(':scope > .grouplet_grid_tab_title');
        if (titleDom) this._renderTabTitle(titleDom, pkey);
    }

    _renderTabTitle(titleDom, pkey) {
        this._renderTitle(titleDom, this.titleTemplate, pkey);
    }

    _renderTitle(dom, compiled, pkey) {
        gnr.GroupletCard.renderTitle(dom, compiled, this.dataStore.rowValue(pkey),
                                     () => this._readTabLabel(pkey));
    }

    _tabOrder() {
        return this.dataStore.sortedKeys();
    }

    // ====================================================================
    //  Collapsible cards — collapsible=True|'closed': a card folds to one
    //  summary line, or to its band; the state is kept by row path, across
    //  re-renders
    // ====================================================================

    _collapseKey(pkey) {
        return this.storepath + '.' + pkey;
    }

    isCollapsed(pkey) {
        if (!this.collapsible) return false;
        const state = gnr.GroupletGridController._collapsedState[this._collapseKey(pkey)];
        return (state === undefined) ? this.collapsible === 'closed' : state;
    }

    setCollapsed(pkey, collapsed) {
        if (!this.collapsible || !this.dataStore.rowNode(pkey)) return;
        gnr.GroupletGridController._collapsedState[this._collapseKey(pkey)] = !!collapsed;
        this._applyCollapsed(pkey, true);
    }

    toggleCollapsed(pkey) {
        this.setCollapsed(pkey, !this.isCollapsed(pkey));
    }

    collapseAll(collapsed = true) {
        this.dataStore.getNodes().forEach((n) => this.setCollapsed(n.label, collapsed));
    }

    _applyCollapsed(pkey, animate = false) {
        const tile = this.tiles[pkey];
        const dom = tile && tile.domNode();
        if (!dom) return;
        const collapsed = this.isCollapsed(pkey);
        if (tile.card) {
            tile.card.applyCollapsed(collapsed, animate);
            return;
        }
        const toggle = dom.querySelector(':scope > .grouplet_grid_row_collapse');
        if (toggle) gnr.GroupletCard.syncToggle(toggle, collapsed);
        if (collapsed) this._refreshRowTitle(pkey);
        gnr.GroupletCard.fold(dom, collapsed, ['grouplet_grid_row--collapsed'], tile, animate);
    }

    _refreshRowTitle(pkey) {
        const tile = this.tiles[pkey];
        if (tile && tile.card) {
            tile.card.refreshTitle();
            return;
        }
        if (!this.collapsible || !this.isCollapsed(pkey)) return;
        const dom = tile && tile.domNode();
        const line = dom && dom.querySelector(':scope > .grouplet_grid_row_summaryline');
        if (!line) return;
        this._renderTitle(line, this.collapsedTemplate, pkey);
    }

    _sortTabs() {
        if (!this.sortField) return;
        if (this.dataStore.applySortToStore()) {
            this.updateCounterColumn();
            this._mirrorTileOrder();
        }
        const strip = this.tabstripDom;
        if (!strip) return;
        const chips = this._tabOrder().map((k) => this._tabsByPkey[k]).filter(Boolean);
        if (chips.every((chip, i) => strip.children[i] === chip)) return;
        chips.forEach((chip) => strip.appendChild(chip));
    }

    _mirrorTileOrder() {
        let prev = null;
        this.dataStore.getNodes().forEach((n) => {
            const dom = this.tiles[n.label] && this.tiles[n.label].domNode();
            if (!dom || !dom.parentNode) return;
            const ref = prev ? prev.nextSibling : dom.parentNode.firstChild;
            if (dom !== ref) dom.parentNode.insertBefore(dom, ref);
            prev = dom;
        });
    }

    renderTemplate(compiled, pkey, withSums = true) {
        return gnr.GroupletCard.renderTemplate(compiled, this.dataStore.rowValue(pkey), withSums);
    }

    static naturalCompare(a, b) {
        // Codes as people read them: 2 before 10, blanks last.
        const blank = (v) => v === null || v === undefined || v === '';
        if (blank(a) || blank(b)) return blank(a) - blank(b);
        if (typeof a === 'number' && typeof b === 'number') return a - b;
        return String(a).localeCompare(String(b), undefined, {numeric: true, sensitivity: 'base'});
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
            const first = this._tabOrder().find((k) => this.tiles[k]);
            if (first && !this.activePkey) {
                this._activateTab(first);
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
        if (this.dnd) {
            this.dnd.clearHighlight();
            this.dnd.unwireAppendTarget(this._dropBodyDom);
            this._dropBodyDom = null;
            this.dnd.unwireAppendTarget(this.addBtnDom);
        }
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
        if (newLayout === this.layout) return;
        return this.withPendingEntries(() => this._setLayout(newLayout));
    }

    _setLayout(newLayout) {
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
        this._wireBodyDnD();
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
        if (this.dnd) this.dnd.wireAppendTarget(this.addBtnDom);
    }

    _wireBodyDnD() {
        if (this.dnd && !this._isTabsLayout() && this.bodyNode) {
            const dom = this.bodyNode.getDomNode();
            if (this._dropBodyDom !== dom) this.dnd.unwireAppendTarget(this._dropBodyDom);
            this._dropBodyDom = dom;
            this.dnd.wireAppendTarget(dom, true);
        }
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
        this._renderTabTitle(title, pkey);
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
            that.activateTab(pkey);
        });
        // Insert before the next mounted sibling chip (tab order).
        let inserted = false;
        const allKeys = this._tabOrder();
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

    activateTab(pkey) {
        // leaving a tab first commits the entry rows inside it
        if (pkey === this.activePkey) return this._activateTab(pkey);
        return this.withPendingEntries(() => this._activateTab(pkey));
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
                if (pkey && this._multiKeys && this._multiKeys.includes(pkey)) {
                    this._deleteSelected();
                    break;
                }
                if (!pkey) return;
                this._askAndDeleteItem(pkey);
                break;
            }
            case 'copy':
                this._copyFromRow(payload.rowKey);
                break;
            case 'move': {
                // several rows land in block, in their order, after the target
                const src = payload.sourceNodeId;
                const rowKeys = payload.rowKeys || [payload.rowKey];
                let position = payload.position;
                if (src && src !== this.nodeId) {
                    const sourceCtrl = this._findSourceController(src);
                    if (!sourceCtrl || !this._canMoveRowFrom(sourceCtrl, rowKeys)) break;
                    const movedKeys = [];
                    rowKeys.forEach((k) => {
                        const moved = this._doMoveTileFrom(sourceCtrl, k, position);
                        if (moved) {
                            position = '>' + moved;
                            movedKeys.push(moved);
                        }
                    });
                    // as in a file manager the moved rows stay selected
                    if (rowKeys.length > 1) this._selectRows(movedKeys);
                } else {
                    rowKeys.forEach((k) => {
                        this._doMoveTile(k, position);
                        position = '>' + k;
                    });
                }
                break;
            }
        }
    }

    // ====================================================================
    //  DnD move dispatch — see gnr.GroupletGridDnD at the top of file.
    // ====================================================================

    gnr_setDisabled(disabled) {
        genro.dom.setDomNodeDisabled(this._containerDom(), disabled);
        if (disabled && this.dnd) this.dnd.clearHighlight();
    }

    _dragKeys(pkey) {
        // a selected row drags the whole selection of its grid, in order
        if (!(this._multiKeys && this._multiKeys.includes(pkey))) return [pkey];
        return this.dataStore.getData().keys().filter((k) => this._multiKeys.includes(k));
    }

    _canMoveRowFrom(source, rowKeys) {
        const keys = [].concat(rowKeys || []);
        if (!source || this._destroyed || source._destroyed
                || !this.dragCode || this.dragCode !== source.dragCode
                || !keys.length || keys.some((k) => !k || !source.dataStore.rowNode(k))) return false;
        for (const c of [this, source]) {
            const form = c.sourceNode.getFormHandler();
            if ((form && form.isDisabled()) || c.sourceNode.disabled
                    || c.sourceNode.getAttributeFromDatasource('disabled')) return false;
        }
        return source === this || (this.additem
            && (!this.maxRows || this.dataStore.getNodes().length + keys.length <= this.maxRows)
            && source.dataStore.getNodes().length - keys.length >= source.minRows);
    }

    _doMoveTile(pkey, position) {
        if (!this._canMoveRowFrom(this, pkey)) return;
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
        this._sortTabs();
        if (this.tiles[pkey]) this.tiles[pkey].flash();
    }

    _findSourceController(sourceNodeId) {
        const node = genro.nodeById(sourceNodeId);
        return (node && node.gridController) || null;
    }

    _doMoveTileFrom(sourceCtrl, sourceRowKey, targetPosition) {
        // Cross-instance migration. The guard catches the browser quirk
        // where a self-drop is misrouted to the source controller.
        if (sourceCtrl === this || !this._canMoveRowFrom(sourceCtrl, sourceRowKey)) return;
        // Pre-commit the target key so _pendingFlash is set before the
        // setItem trigger fires _renderTile.
        const targetBag = this.dataStore.getData();
        const targetRowKey = (targetBag && targetBag.getNode(sourceRowKey))
            ? genro.time36Id() : sourceRowKey;
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[targetRowKey] = true;
        return this.dataStore.moveRowFrom(
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
            this.activePkey = this._tabOrder().find((k) => toAdd.includes(k));
        }
        this.bodyNode.freeze();
        toAdd.forEach((pkey) => this._renderTile(pkey));
        this.bodyNode.unfreeze();
        this._wireBodyDnD();
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
            const field = this._pendingFocusField;
            this._pendingFocusEditor = null;
            this._pendingFocusField = null;
            this._focusFirstEditor(tile, editorIndex, field);
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

    _focusFirstEditor(tile, editorIndex, field) {
        // The editor at editorIndex, else the one bound to `^.<field>`
        // (additem_focus), else the first one.
        if (!tile || !tile.domNode()) return;
        const focus = function() {
            // read at focus time: mounting a lazy body renders the wrapper anew
            const dom = tile.domNode();
            if (!dom || !dom.isConnected) return;
            const editors = gnr.GroupletGridController._editors(dom);
            const node = field && tile.tileContent && tile.tileContent.walk((n) => (
                (n.widget && n.attr.value === '^.' + field) ? n : undefined
            ), 'static');
            const named = node && node.widget.focusNode;
            const target = ((editorIndex === null || editorIndex === undefined)
                ? null : editors[editorIndex]) || (editors.indexOf(named) >= 0 ? named : null);
            const el = target || editors[0];
            if (!el) return;
            gnr.GroupletGridController.focusNode(el);
            // As a native Tab would: typing replaces the default in the field.
            if (target && el.select) el.select();
        };
        // a lazy tab mounts its body in the next frame: the focus waits for it
        if (!tile.bodyMounted) {
            tile._afterBodyMount = focus;
            return;
        }
        // One tick: the widgets of a just-grafted tile are instantiated when
        // the framework drains its afterBuildCalls, after this mount returns.
        setTimeout(focus, 0);
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
                const chipKeys = this.tabstripDom
                    ? Array.from(this.tabstripDom.children).map((c) => c.getAttribute('data-rowkey'))
                    : Object.keys(this._tabsByPkey);
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
        this._pendingFocusField = (this.additemKw || {}).focus || null;
        const merged = this.defaultRowValues();
        objectUpdate(merged, defaults || {});
        if (this.phantom) this._freshRows[newKey] = objectUpdate({}, merged);
        this.dataStore.addRow(newKey, merged, position);
        this._selectRows([newKey]);
    }

    defaultRowValues() {
        // A `=path` value is read when the row is made, from the grid's
        // datapath (`=#FORM.common_values.mainProducer`), not frozen at build;
        // a `==expression` is worked out then, with `this` the grid's node,
        // over `rows` (the grid's Bag) and `grid`: `==nextCode(rows)`.
        const raw = this.defaultRow || {};
        const out = {};
        Object.keys(raw).forEach((k) => {
            let v = raw[k];
            if (typeof v === 'string' && v.indexOf('==') === 0) {
                v = funcCreate('return ' + v.slice(2), 'rows,grid').apply(this.sourceNode,
                                                                          [this.dataStore.getData(), this]);
            } else if (typeof v === 'string' && v.charAt(0) === '=') {
                v = this.sourceNode.getRelativeData(v.slice(1));
                if (v instanceof gnr.GnrBag) v = v.deepCopy();
            }
            out[k] = v;
        });
        return out;
    }

    _askAndDeleteItem(pkey) {
        if (this._deleteLocked(pkey)) {
            if (!this._delitemAllows(pkey)) {
                genro.dlg.floatingMessage(this.sourceNode, {
                    message: _T('!!This row cannot be deleted'), messageType: 'warning'});
            }
            return;
        }
        this.dataStore.deleteRowAsk(pkey);
    }

    _deleteLocked(pkey) {
        const form = this.sourceNode.getFormHandler();
        return !!(form && form.isDisabled()) || this._rowCount() <= this.minRows
            || (pkey !== undefined && !this._delitemAllows(pkey));
    }

    _delitemAllows(pkey) {
        // a dynamic delitem is read on the row's own node, when asked; a
        // static one only decides whether the row shows a delete at all
        const tile = this.tiles[pkey];
        const delitem = tile ? tile.delitem : this.delitem;
        if (typeof delitem !== 'string') return true;
        return !!(tile && tile.tileNode
                  && gnr.GroupletCard.evaluateOn(tile.tileNode, delitem, this.dataStore.rowValue(pkey)));
    }

    _cardProfile(templateKey) {
        if (!this._cardProfiles[templateKey]) {
            const profile = objectUpdate(objectUpdate({}, this.templateCards[templateKey] || {}), this.card);
            const Card = gnr.GroupletCard;
            profile.title = this.collapsedTemplate || Card.compileTemplate(profile.titleTemplate)
                || Card.compileTemplate(profile.template);
            profile.docTemplate = Card.compileTemplate(profile.doc);
            this._cardProfiles[templateKey] = profile;
        }
        return this._cardProfiles[templateKey];
    }

    _refreshRowMenu(pkey) {
        // the kebab of a selected row acts on the whole selection, and says so
        const inSelection = !!(this._multiKeys && this._multiKeys.includes(pkey));
        const count = inSelection ? this.groupSelection().reduce((n, e) => n + e.rowKeys.length, 0) : 1;
        const path = this.controllerPath + '.row_menu.';
        genro.setData(path + 'copy_label', count > 1
            ? _T('!!Copy $count rows').replace('$count', count) : _T('!!Copy'));
        genro.setData(path + 'delete_label', count > 1
            ? _T('!!Delete $count rows').replace('$count', count) : _T('!!Delete row'));
        genro.setData(path + 'delete_locked', inSelection ? this._selectionDeleteLocked() : this._deleteLocked(pkey));
    }

    selectTile(pkey) {
        // Tabs/vtabs use the active state; .selected is a cards-only
        // UX class that conflicts with the panel chrome here.
        if (this._isTabsLayout() || this._multiKeys) return;
        if (this.selectedPkey === pkey) return;
        if (this.selectedPkey && this.tiles[this.selectedPkey]) {
            const prevDom = this.tiles[this.selectedPkey].domNode();
            if (prevDom) prevDom.classList.remove('selected');
        }
        this.selectedPkey = pkey;
        if (pkey) {
            this._selAnchor = pkey;
            gnr.GroupletGridController._lastSelected = this;
        }
        const dom = this.tiles[pkey] && this.tiles[pkey].domNode();
        if (dom) dom.classList.add('selected');
    }

    _updateAddBtnState() {
        const body = this.entry && this.bodyNode && this.bodyNode.getDomNode();
        if (body) {
            body.setAttribute('data-entry-hint',
                _T('!!Fill in the fields above, then press Enter or click ↵ to add the row.'));
        }
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
        const defaults = this.defaultRowValues();
        this._blankDefaults = objectUpdate(this._blankDefaults || {}, {[path]: defaults});
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
        return this._hasEnteredValues(genro.getData(this.phantomPath),
                                      (this._blankDefaults || {})[this.phantomPath]);
    }

    _hasEnteredValues(rowBag, baseline) {
        // Computed columns are not an entry: in struct mode only the editable
        // cells count, in card mode every field but formulas and the counter.
        if (!(rowBag instanceof gnr.GnrBag)) return false;
        const defaults = baseline || this.defaultRowValues();
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
        this._freshRows[newKey] = objectUpdate({}, (this._blankDefaults || {})[this.phantomPath] || {});
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[newKey] = true;
        this._resetPhantom();
        this.dataStore.addRow(newKey, values);
    }

    _dropIfEmpty(pkey) {
        // The reverse of the promotion, for rows added since the rows were
        // loaded: one left with no entry goes away, without the dialog. A
        // loaded row emptied stays, it is deleted with its `×`. No entry is
        // measured on the defaults the row was given: a `==` default worked
        // out again may differ (the next code).
        const given = this._freshRows[pkey];
        if (this._destroyed || !this.tiles[pkey] || !given) return;
        if (this._rowCount() <= this.minRows) return;
        const form = this.sourceNode.getFormHandler();
        if (form && form.isDisabled()) return;
        if (this._hasEnteredValues(this.dataStore.rowValue(pkey), (typeof given === 'object') ? given : null)) return;
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
        this._registerPendingEditor();
        this._mountSelectionBar();
        this._syncChecks();
        this._wireChromeClicks();
        // a row grafted while the page builds gets its widgets a tick later
        setTimeout(() => this._destroyed || this._syncKept(), 0);
        this._validateEntryRequired();
        this._updateAddBtnState();
        this._scheduleStructSync();
    }

    _wireChromeClicks() {
        // header pins and select-all boxes are rebuilt with their slot
        if (this._chromeClicksWired) return;
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

    _unmountEntry() {
        if (!this.entryTile) return;
        this.entryTile.unmount();
        this.entryTile = null;
    }

    _resetEntry() {
        // Kept fields survive (Enter, Esc, record load alike) and act as
        // defaults for the next row: alone, they are no entry.
        const bag = this._resetBlankRow(this.entryPath, true);
        bag.subscribe(this._entrySubscriberId(), {any: () => {
            this._calcEntryFormulas();
            if (!this._phantomResetting) this._updateFormStatus();
        }});
        this._entryBaseline = objectUpdate({}, (this._blankDefaults || {})[this.entryPath]);
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
        this._updateFormStatus();
    }

    // ====================================================================
    //  Entry row and its form — a pending entry is a change of the form;
    //  save, dismiss and switching tab or layout commit it first
    // ====================================================================

    _registerPendingEditor() {
        gnr.GroupletGridController._entryGrids.add(this);
        const form = this.sourceNode.getFormHandler();
        if (!form || !form.registerPendingEditor || this._pendingForm === form) return;
        this._pendingForm = form;
        form.registerPendingEditor(this.nodeId, this);
    }

    _updateFormStatus() {
        // once per burst: loading a row in the entry row sets every field
        if (!this._pendingForm || this._formStatusScheduled) return;
        this._formStatusScheduled = true;
        setTimeout(() => {
            this._formStatusScheduled = false;
            const form = this._pendingForm;
            if (!this._destroyed && form.opStatus !== 'loading') form.updateStatus();
        }, 0);
    }

    hasPendingEntry() {
        // values typed in the entry row and not added yet; while a row is
        // edited there, its changes or the new row set aside meanwhile
        if (!this.entryTile || this._destroyed) return false;
        if (this._editingKey) {
            return this._entryChanged() || this._hasEnteredValues(this._entryDraft, this._entryBaseline);
        }
        return this._hasEnteredValues(genro.getData(this.entryPath), this._entryBaseline);
    }

    commitPendingEntry() {
        // true when nothing is left pending; false when a value stopped it,
        // the field flagged and focused
        if (this._editingKey && !this._entryChanged()) this._finishEntryEdit();
        // at most the edited row, then the new row set aside meanwhile
        for (let i = 0; i < 3 && this.hasPendingEntry(); i++) {
            if (!this._addEntry()) return false;
        }
        return !this.hasPendingEntry();
    }

    _entryFocusedWidget() {
        // The field with the focus in the entry row or in a popup of its
        // fields; or the one the focus has just left, which dijit blurs (and
        // so writes) up to 100ms later when a click elsewhere swallowed the
        // mousedown.
        const active = document.activeElement;
        const dom = this.entryTile && this.entryTile.domNode();
        const widget = active && dijit.getEnclosingWidget(active);
        if (dom && active && dom.contains(active)) return widget;
        const owner = widget && widget.sourceNode && widget.sourceNode.attributeOwnerNode('_gg_root');
        if (owner && owner.gridController === this) return widget;
        const last = this._entryWidget;
        return (last && last._focused && dom && last.domNode && dom.contains(last.domNode)) ? last : null;
    }

    // the form's pending editor protocol (genro_frm registerPendingEditor)
    isDestroyed() {
        return this._destroyed;
    }

    isPending() {
        return !!this._editingKey || this.hasPendingEntry() || !!this._entryFocusedWidget();
    }

    hasPendingChanges() {
        return this.hasPendingEntry();
    }

    prepareCommit() {
        // a field writes its value on blur
        const widget = this._entryFocusedWidget();
        if (widget && widget._onBlur) widget._onBlur();
    }

    commitPending() {
        return this.commitPendingEntry();
    }

    withPendingEntries(action) {
        // Runs action once the entry rows of this grid and of the grids
        // nested in it are committed; not at all if one refuses.
        const form = this.sourceNode.getFormHandler();
        if (form && form.opStatus === 'loading') return action();
        const dom = this._containerDom();
        const grids = Array.from(gnr.GroupletGridController._entryGrids).filter((g) => (
            !g._destroyed && (g === this || dom.contains(g._containerDom()))));
        if (form && form.commitPendingEditors) return form.commitPendingEditors(action, grids);
        const busy = grids.filter((g) => g.isPending());
        if (!busy.length) return action();
        busy.forEach((g) => g.prepareCommit());
        setTimeout(() => {
            if (busy.every((g) => g.commitPendingEntry())) action();
        }, 0);
    }

    focusEntry() {
        this._focusEntry();
    }

    commitEntry() {
        this._commitEntry();
    }

    wireEntryDropTarget(dom) {
        // a popup of the entry row's fields takes a drop as the row does
        if (this.dnd && dom) this.dnd.wireAppendTarget(dom);
    }

    attachEntryPopup(dom) {
        // A popup of entry fields (a tooltipPane): drop target, Enter adds
        // the row and Esc goes back to it, closing the popup in both cases.
        if (!dom) return;
        this.wireEntryDropTarget(dom);
        dom.addEventListener('keydown', (e) => {
            const field = dijit.getEnclosingWidget(e.target);
            if (field && field._isShowingNow) return;
            if (e.key !== 'Escape' && (e.key !== 'Enter' || e.shiftKey || e.isComposing
                    || e.target.tagName === 'TEXTAREA')) return;
            e.preventDefault();
            e.stopPropagation();
            if (field && field._onBlur) field._onBlur();
            const dialog = dom.closest('.dijitTooltipDialog');
            const dialogWidget = dialog && dijit.getEnclosingWidget(dialog);
            if (dialogWidget && dialogWidget.onCancel) dialogWidget.onCancel();
            if (e.key === 'Enter') this._commitEntry();
            else this._focusEntry();
        }, true);
    }

    _refreshEntryDefaults() {
        // A blank entry row picks up a `=path` default changed since it was
        // cleared; one being typed in or edited keeps what it shows.
        if (this._editingKey || this._phantomResetting) return;
        const bag = genro.getData(this.entryPath);
        const shown = (this._blankDefaults || {})[this.entryPath] || {};
        if (this._hasEnteredValues(bag, this._entryBaseline)) return;
        const now = this.defaultRowValues();
        if (Object.keys(now).some((k) => !(now[k] instanceof gnr.GnrBag) && now[k] !== shown[k])) {
            this._resetEntry();
        }
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
        if (first) gnr.GroupletGridController.focusNode(first);
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
        const invalid = this._entryInvalidField();
        if (invalid) {
            this._flagInvalidField(invalid);
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
            this._clearOtherGrids();
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

    _clickSelects(e) {
        // Cmd/Ctrl-click toggles a row, Shift-click selects a range
        return !!(e && !e._groupletSelected && (e.metaKey || e.ctrlKey || e.shiftKey)
                  && Object.keys(this.selectionmenu || {}).length);
    }

    _clickClearsSelection(e) {
        return !!(e && !e._groupletSelected && this.groupSelection().length);
    }

    _onRowClickSelect(pkey, e) {
        // As in a file list: Cmd/Ctrl toggles the row and moves the anchor,
        // Shift selects the range from the anchor in place of the selection,
        // Cmd+Shift adds the range; a row selected by a plain click counts
        const single = this.selectedPkey && this.dataStore.rowNode(this.selectedPkey) ? [this.selectedPkey] : [];
        const current = this._multiKeys ? this._multiKeys.slice() : single;
        const toggle = e.metaKey || e.ctrlKey;
        let keys;
        if (e.shiftKey && this._selAnchor && this.tiles[this._selAnchor]) {
            const range = this._keysBetween(this._selAnchor, pkey);
            keys = toggle ? current.concat(range.filter((k) => !current.includes(k))) : range;
        } else {
            keys = current.includes(pkey) ? current.filter((k) => k !== pkey) : current.concat(pkey);
            this._selAnchor = pkey;
        }
        this._clearOtherGrids();
        this._applyChecks(keys, true);
    }

    _clearOtherGrids() {
        if (!this.selectionGroup) return;
        gnr.GroupletGridController.groupMembers(this.selectionGroup)
            .filter((g) => g !== this && g._multiKeys).forEach((g) => g._applySelection([]));
    }

    _selectRows(keys) {
        // rows just made (pasted, added, moved here) become the selection:
        // one is the current row, several are ticked
        const present = keys.filter((k) => this.dataStore.rowNode(k));
        if (!present.length) return;
        this.clearSelection(true);
        if (present.length === 1) {
            this.selectTile(present[0]);
        } else {
            this._selAnchor = present[0];
            this._applyChecks(present);
        }
    }

    _onRowCheck(pkey, e, focusBar = false) {
        // a row selected by a plain click is where a Cmd/Shift-click starts from
        const single = this.selectedPkey && this.dataStore.rowNode(this.selectedPkey) ? [this.selectedPkey] : [];
        const current = this._multiKeys ? this._multiKeys.slice() : single;
        let keys;
        if (e.shiftKey && this._selAnchor && this.tiles[this._selAnchor]) {
            const range = this._keysBetween(this._selAnchor, pkey);
            keys = current.concat(range.filter((k) => !current.includes(k)));
        } else {
            keys = current.includes(pkey)
                ? current.filter((k) => k !== pkey) : current.concat(pkey);
        }
        this._selAnchor = pkey;
        this._applyChecks(keys, focusBar);
    }

    _onCheckAll() {
        const all = this.dataStore.getData().keys();
        const current = this._multiKeys || [];
        this._applyChecks(current.length === all.length ? [] : all);
    }

    _applyChecks(keys, focusBar = false) {
        if (!keys.length) {
            this._setMulti(null);
            return;
        }
        const enter = () => {
            this._finishEntryEdit();
            this._setMulti(keys, focusBar);
        };
        if (this._entryChanged()) this._commitEntry(enter);
        else enter();
    }

    _syncChecks() {
        if (!this.rowCheckbox) return;
        const keys = this._multiKeys || [];
        Object.keys(this.tiles).forEach((k) => {
            const tile = this.tiles[k];
            if (tile.card) {
                tile.card.setChecked(keys.includes(k));
                return;
            }
            const dom = tile.domNode();
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
        if (keys) gnr.GroupletGridController._lastSelected = this;
        this._containerDom().classList.toggle('grouplet_grid--multi', !!keys);
        if (keys) this.selectedPkey = null;
        Object.keys(this.tiles).forEach((k) => {
            const dom = this.tiles[k].domNode();
            if (dom) dom.classList.toggle('selected', !!keys && keys.includes(k));
        });
        this._syncChecks();
        this._refreshGroupBars();
        const bar = this.selectionNode && this.selectionNode.getDomNode();
        if (!bar || !keys) return;
        if (entering && focusBar) {
            setTimeout(() => {
                const first = bar.querySelector('[tabindex]');
                if (first) first.focus();
            }, 0);
        }
    }

    _updateSelectionBar() {
        // The count is the group's: every bar of a group acts on all of it.
        const bar = this.selectionNode && this.selectionNode.getDomNode();
        if (!bar || !this._multiKeys) return;
        const count = this.groupSelection().reduce((n, e) => n + e.rowKeys.length, 0);
        const one = count === 1;
        const countDom = bar.querySelector('.grouplet_grid_selection_count');
        if (countDom) {
            countDom.textContent = (one ? _T('!!1 row selected') : _T('!!$count rows selected'))
                .replace('$count', count);
        }
        genro.setData(this.controllerPath + '.selection_menu.delete_label',
                      (one ? _T('!!Delete 1 row') : _T('!!Delete $count rows')).replace('$count', count));
        genro.setData(this.controllerPath + '.selection_menu.delete_locked', this._selectionDeleteLocked());
    }

    _selectionDeleteLocked() {
        return this.groupSelection().some(({grid, rowKeys}) => {
            const form = grid.sourceNode.getFormHandler();
            return !!(form && form.isDisabled()) || grid._rowCount() - rowKeys.length < grid.minRows
                || rowKeys.some((k) => !grid._delitemAllows(k));
        });
    }

    _refreshGroupBars() {
        const grids = this.selectionGroup
            ? gnr.GroupletGridController.groupMembers(this.selectionGroup) : [this];
        // every grid of the group is marked while the group holds a selection
        const selecting = grids.some((g) => g._multiKeys && g._multiKeys.length);
        grids.forEach((g) => {
            const dom = g._containerDom();
            if (dom) dom.classList.toggle('grouplet_grid--selecting', selecting);
            g._updateSelectionBar();
        });
    }

    static _groupSet(code) {
        const groups = gnr.GroupletGridController._selectionGroups;
        if (!groups[code]) groups[code] = new Set();
        return groups[code];
    }

    static groupMembers(code) {
        return Array.from(gnr.GroupletGridController._groupSet(code)).filter((g) => !g._destroyed);
    }

    getSelectedKeys() {
        return this._selectedKeys();
    }

    groupSelection() {
        // [{grid, rowKeys}] of the grids in the group with a selection
        const grids = this.selectionGroup
            ? gnr.GroupletGridController.groupMembers(this.selectionGroup) : [this];
        // another grid's row edited in its entry row is no selection
        return grids.map((g) => ({grid: g, rowKeys: (g === this) ? g._selectedKeys()
                                                                  : (g._multiKeys || []).slice()}))
            .filter((e) => e.rowKeys.length);
    }

    clearSelection(wholeGroup) {
        const grids = (wholeGroup && this.selectionGroup)
            ? gnr.GroupletGridController.groupMembers(this.selectionGroup) : [this];
        grids.forEach((g) => g._applySelection([]));
    }

    _mountSelectionBar() {
        // The bar below the rows for several selected rows: the count and a
        // kebab with the `selectionmenu` entries, the delete last and apart.
        // An entry's `action` runs with `rowKeys` and `grid`.
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
        const others = specs.filter((spec) => spec.key !== 'delete');
        others.forEach((spec) => {
            const kw = {label: _T(spec.label), action: function() { c._runSelectionAction(spec); }};
            // dijit's MenuItem template takes no undefined iconClass
            if (spec.iconClass) kw.iconClass = spec.iconClass;
            menu._('menuline', kw);
        });
        if (others.length < specs.length) {
            if (others.length) menu._('menuline', {label: '-'});
            menu._('menuline', {
                label: '^' + this.controllerPath + '.selection_menu.delete_label',
                iconClass: 'iconbox trash',
                _class: 'grouplet_grid_menu_danger',
                disabled: '^' + this.controllerPath + '.selection_menu.delete_locked',
                action: function() { c._deleteSelected(); }
            });
        }
    }

    _selectionSpecs() {
        // selectionmenu = {key: true | 'label' | {label, action}}, as editmenu
        const presets = {'delete': {label: '!!Delete'},
                         copy: {label: '!!Copy', iconClass: 'iconbox copy duplicate_record'},
                         exportXls: {label: '!!Export Excel', iconClass: 'iconbox export'},
                         print: {label: '!!Print', iconClass: 'iconbox print'}};
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
        const selection = this.groupSelection();
        if (!selection.length) return;
        if (spec.key === 'delete') {
            this._deleteSelected();
            return;
        }
        const preset = {copy: 'copyRows', exportXls: 'exportRows', print: 'printRows'}[spec.key];
        if (preset && !spec.action) {
            this[preset](null, selection);
            return;
        }
        if (spec.action) {
            funcApply(spec.action, {rowKeys: this._selectedKeys(), grid: this, selection: selection},
                      this.sourceNode);
        }
    }

    _onMultiKeydown(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            this.clearSelection(true);
            this._focusEntry();
        } else if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectionmenu['delete']) {
            e.preventDefault();
            this._deleteSelected();
        }
    }

    _deleteSelected() {
        const selection = this.groupSelection();
        if (!selection.length) return;
        for (const {grid, rowKeys} of selection) {
            const form = grid.sourceNode.getFormHandler();
            if (form && form.isDisabled()) return;
            if (grid._rowCount() - rowKeys.length < grid.minRows) {
                genro.dlg.floatingMessage(grid.sourceNode, {
                    message: _T('!!At least $count rows are required').replace('$count', grid.minRows),
                    messageType: 'warning'
                });
                return;
            }
            if (rowKeys.some((k) => !grid._delitemAllows(k))) {
                genro.dlg.floatingMessage(grid.sourceNode, {
                    message: _T('!!Some of these rows cannot be deleted'), messageType: 'warning'});
                return;
            }
        }
        if (selection.length === 1) {
            selection[0].grid.dataStore.deleteRowsAsk(selection[0].rowKeys);
            return;
        }
        // one question for the whole group, each grid deletes its own rows
        const all = [].concat(...selection.map((e) => e.rowKeys));
        this.store.deleteAsk(all, null, () => {
            selection.forEach((e) => e.grid.store.deleteRows(e.rowKeys));
        });
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

    _entryInvalidField() {
        return this.entryTile.tileContent.walk((n) => (
            (n.widget && n.hasValidationError && n.hasValidationError()) ? n : undefined
        ), 'static');
    }

    _flagInvalidField(node) {
        const error = node.getValidationError();
        genro.publish('floating_message', {
            message: (node.getElementLabel() || '').trim() + ': '
                + (error ? node._resolveErrorMessage(error) : _T('!!Correct the invalid field')),
            sound: '$onerror', messageType: 'error'});
        node.widget.focus();
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
            gnr.GroupletGridController.focusNode(el);
            if (el.select) {
                el.select();
                gnr.GroupletGridController._markAutoSelected(el);
            }
        }, 0);
    }

    static _markAutoSelected(el) {
        // text the grid selected itself, not the user: Cmd/Ctrl+C there
        // still copies the row, until the field is touched
        el._ggAutoSelected = true;
        const clear = () => { el._ggAutoSelected = false; };
        el.addEventListener('mousedown', clear, {once: true});
        el.addEventListener('keydown', clear, {once: true});
    }

    static focusNode(el) {
        // A field focused again while it has the DOM focus (the entry row just
        // added) gets no focus event: dijit's focus, which a closing popup
        // hands back to its opener, is not corrected, and the field's onfocus
        // check does not run, the one that lets genro write a value typed
        // over a validation error. Without both the next value is dropped on
        // blur. dijit.focus and _refreshState do what that event would do.
        if (!dijit.focus) {
            el.focus();
            return;
        }
        dijit.focus(el);
        const widget = dijit.getEnclosingWidget(el);
        if (widget && widget._refreshState) widget._refreshState();
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
    //  to the tail, pasted into a row's field they follow that row; one
    //  row each, columns by a header naming them, else in field order
    // ====================================================================

    _onBlankPaste(e, tile) {
        this._onRowsPaste(e, tile);
    }

    _onRowsPaste(e, tile) {
        // an inner grid's row took it already
        if (e.defaultPrevented) return;
        const text = this._pastedRowsText(e);
        if (text === null) return;
        e.preventDefault();
        this._pasteRows(text, tile, e.target);
    }

    _onDocumentPaste(e) {
        // Cmd/Ctrl+V with rows selected and no field focused adds the rows
        // at the tail of the grid last selected in
        const Ctrl = gnr.GroupletGridController;
        if (e.defaultPrevented || Ctrl._lastSelected !== this) return;
        if (Ctrl._textField(document.activeElement)) return;
        if (!this.selectedPkey && !(this._multiKeys && this._multiKeys.length)) return;
        const text = this._pastedRowsText(e);
        if (text === null) return;
        e.preventDefault();
        const fields = this._firstRowFields();
        this._insertPastedRows(this._rowsFromText(text, fields, 0), null);
    }

    _pastedRowsText(e) {
        const form = this.sourceNode.getFormHandler();
        if (form && form.isDisabled()) return null;
        const text = e.clipboardData && e.clipboardData.getData('text');
        // one plain value pastes as usual: only several lines or tabs split
        return (text && (/\t/.test(text) || /\n./.test(text.trim()))) ? text : null;
    }

    _pasteRows(text, tile, target) {
        // in a field of a row the first pasted row replaces it, the others
        // follow it; the entry row editing a row counts as that row; the
        // blank rows add them all at the tail
        const fields = this._rowFields(tile);
        let start = fields.findIndex((f) => f.node.widget.domNode
            && f.node.widget.domNode.contains(target));
        if (start < 0) start = 0;
        const rows = this._rowsFromText(text, fields, start);
        let replaced = null;
        if (tile === this.entryTile) {
            replaced = this._editingKey || null;
            if (replaced) this._finishEntryEdit();
            else this._resetEntry();
        } else if (tile === this.phantomTile) {
            this._resetPhantom();
        } else {
            replaced = tile.pkey;
        }
        this._insertPastedRows(rows, replaced);
    }

    _insertPastedRows(rows, replaced) {
        let last = null;
        const pastedKeys = [];
        if (replaced && rows.length && this.dataStore.rowNode(replaced)) {
            this.dataStore.updateRow(replaced, rows[0]);
            rows = rows.slice(1);
            last = replaced;
            pastedKeys.push(replaced);
        }
        rows.forEach((values) => {
            if (this.maxRows && this._rowCount() >= this.maxRows) return;
            const key = 'r_' + genro.time36Id();
            if (this.phantom) this._freshRows[key] = true;
            this.dataStore.addRow(key, objectUpdate(this.defaultRowValues(), values),
                                  last ? '>' + last : undefined);
            last = key;
            pastedKeys.push(key);
        });
        const pasted = pastedKeys.length;
        this._selectRows(pastedKeys);
        const lastTile = last && this.tiles[last];
        if (lastTile) {
            lastTile.flash();
            const dom = lastTile.domNode();
            if (dom) dom.scrollIntoView({block: 'nearest'});
        }
        if (pasted) this._announce(_T('!!Rows pasted') + ': ' + pasted);
    }

    _rowFields(tile) {
        // The editable fields of a row, in template order, as paths
        // relative to the row (a template may write into `.extra_data.*`).
        let base = this.storepath + '.' + tile.pkey;
        if (tile === this.entryTile) base = this.entryPath;
        else if (tile === this.phantomTile) base = this.phantomPath;
        base += '.';
        const names = {};
        if (this.structAdapter) {
            this.structAdapter.cells.forEach((c) => { names[c.field] = c.name; });
        }
        const fields = [];
        if (!tile.tileContent) return fields;
        tile.tileContent.walk((n) => {
            const attr = n.attr || {};
            if (!n.widget || typeof attr.value !== 'string' || attr.value[0] !== '^') return;
            const abs = n.absDatapath(attr.value.slice(1));
            if (abs.indexOf(base) !== 0) return;
            const path = abs.slice(base.length);
            // a formlet moves `lbl` onto the field's label wrapper
            const wrapper = n.getLabelWrapper && n.getLabelWrapper();
            const lbl = attr.lbl || (wrapper && wrapper.attr.label) || attr.label;
            fields.push({
                path: path,
                node: n,
                label: lbl,
                labels: gnr.GroupletGridController._labelKeys([path, names[path], lbl])
            });
        }, 'static');
        return fields;
    }

    static _labelKeys(labels) {
        return labels.filter(Boolean).map((l) => String(l).trim().toLowerCase())
            .concat(labels.filter(Boolean).map((l) => String(_T(l)).trim().toLowerCase()))
            .filter((l, i, all) => l && all.indexOf(l) === i);
    }

    _rowsFromText(text, fields, start) {
        const Ctrl = gnr.GroupletGridController;
        let cols = fields.slice(start);
        let rows = Ctrl.parseDelimited(text);
        // a first line naming the columns is a header: the columns go by
        // name, wherever it was pasted; a column no field takes is skipped
        const first = rows.length ? rows[0].map((v) => v.trim().toLowerCase()) : [];
        const known = [].concat(...this._copyColumns(fields).map((c) => c.labels));
        if (first.some((v) => v) && first.every((v) => !v || known.indexOf(v) >= 0)) {
            cols = first.map((v) => v && fields.find((f) => f.labels.indexOf(v) >= 0));
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

    // ====================================================================
    //  Copy — rows to the clipboard as tab-separated text under a header
    //  naming the columns: the shape the paste above reads back, and a
    //  spreadsheet splits into its columns
    // ====================================================================

    copyRows(rowKeys, selection) {
        const entries = selection || [{grid: this, rowKeys: rowKeys || this._selectedKeys()}];
        const text = this._rowsAsText(entries);
        if (text === null) return;
        genro.textToClipboard(text, gnr.GroupletGridController._copiedMessage(entries));
    }

    static _copiedMessage(selection) {
        const count = selection.reduce((n, e) => n + e.rowKeys.length, 0);
        return (count === 1 ? _T('!!1 row copied') : _T('!!$count rows copied')).replace('$count', count);
    }

    _onCopy(e) {
        // Cmd/Ctrl+C copies the selected rows of the grid last selected in,
        // through the event's own clipboard, which needs no permission. A
        // field counts only in that grid, with no text selected and outside
        // its blank row; text selected on the page stays a text copy
        const Ctrl = gnr.GroupletGridController;
        if (e.defaultPrevented || !e.clipboardData || Ctrl._lastSelected !== this) return;
        // a field counts while it has the focus: the page selection may
        // linger in one the user has left
        const field = Ctrl._textField(e.target);
        if (field && typeof document !== 'undefined' && field === document.activeElement) {
            const container = this._containerDom();
            if (!container.contains(field) || Ctrl._hasTextSelection(field) || this._inBlankRow(field)) return;
        } else if (typeof window !== 'undefined' && window.getSelection && String(window.getSelection())) {
            return;
        }
        let selection = this.groupSelection();
        // a row selected by a plain click is copied alone
        if (!selection.length && this.selectedPkey && this.dataStore.rowNode(this.selectedPkey)) {
            selection = [{grid: this, rowKeys: [this.selectedPkey]}];
        }
        const text = selection.length ? this._rowsAsText(selection) : null;
        if (text === null) return;
        e.clipboardData.setData('text/plain', text);
        e.preventDefault();
        genro.dlg.floatingMessage(genro.nodeById('_gnrRoot'), {message: Ctrl._copiedMessage(selection)});
    }

    _wireClipboard() {
        // a copy starts where the page selection is, maybe in another grid,
        // a paste in a field takes its row: each grid listens on the
        // document, the last selected answers
        this._clipboardHandlers = {copy: (e) => this._onCopy(e), paste: (e) => this._onDocumentPaste(e)};
        Object.keys(this._clipboardHandlers).forEach((name) => {
            document.addEventListener(name, this._clipboardHandlers[name]);
        });
    }

    _unwireClipboard() {
        if (!this._clipboardHandlers) return;
        Object.keys(this._clipboardHandlers).forEach((name) => {
            document.removeEventListener(name, this._clipboardHandlers[name]);
        });
        this._clipboardHandlers = null;
    }

    static _textField(el) {
        return (el && el.closest && el.closest('input:not([type=checkbox]):not([type=radio]),'
            + 'textarea,[contenteditable=""],[contenteditable="true"]')) || null;
    }

    static _hasTextSelection(field) {
        if (field._ggAutoSelected) return false;
        if (typeof field.selectionStart === 'number') return field.selectionStart !== field.selectionEnd;
        return !!(typeof window !== 'undefined' && window.getSelection && String(window.getSelection()));
    }

    _inBlankRow(el) {
        const dom = (tile) => tile && tile.domNode && tile.domNode();
        const phantom = dom(this.phantomTile);
        const entry = !this._editingKey && dom(this.entryTile);
        return !!el && [phantom, entry].some((d) => d && d.contains && d.contains(el));
    }

    _copyFromRow(pkey) {
        // the kebab of a selected row copies the whole selection
        const selection = this.groupSelection();
        if (selection.some((e) => e.grid === this && e.rowKeys.includes(pkey))) {
            this.copyRows(null, selection);
        } else {
            this.copyRows([pkey]);
        }
    }

    _rowsAsText(selection) {
        const Ctrl = gnr.GroupletGridController;
        const {cols, rows} = this._selectionTable(selection);
        if (!cols.length || !rows.length) return null;
        return [cols.map((c) => c.label)].concat(rows)
            .map((l) => l.map((v) => Ctrl.copyCell(v)).join('\t')).join('\n') + '\n';
    }

    _selectionTable(selection) {
        // the copied columns, each with its dtype, and the raw values of
        // the selected rows in store order
        const Ctrl = gnr.GroupletGridController;
        const cols = this._copyColumns(this._copyFields());
        const rows = [];
        selection.forEach(({grid, rowKeys}) => {
            grid.dataStore.getData().keys().filter((k) => rowKeys.includes(k)).forEach((k) => {
                const row = grid.dataStore.rowValue(k);
                rows.push(cols.map((c) => (row instanceof gnr.GnrBag) ? row.getItem(c.path) : null));
            });
        });
        cols.forEach((c, i) => {
            if (!c.dtype || c.dtype === 'T') c.dtype = Ctrl._dtypeOf(rows.map((r) => r[i]), c.format);
        });
        return {cols, rows};
    }

    static _dtypeOf(values, format) {
        // a column with no declared type takes it from its values, so that
        // numbers and dates stay numbers and dates in the export; a format
        // keeps whole amounts decimal
        const known = values.filter((v) => v !== null && v !== undefined && v !== '');
        if (!known.length) return null;
        if (known.every((v) => v instanceof Date)) return 'D';
        if (known.every((v) => typeof v === 'boolean')) return 'B';
        if (known.every((v) => typeof v === 'number')) {
            return (known.every(Number.isInteger) && !format) ? 'L' : 'N';
        }
        return null;
    }

    _selectionOrAll(rowKeys, selection) {
        selection = selection || [{grid: this, rowKeys: rowKeys || this._selectedKeys()}];
        return selection.some((e) => e.rowKeys.length)
            ? selection : [{grid: this, rowKeys: this.dataStore.getData().keys()}];
    }

    // ====================================================================
    //  Export and print — the selected rows, or all of them, with the
    //  copied columns: an Excel file through the framework's grid export,
    //  a table printed from a hidden frame
    // ====================================================================

    exportRows(rowKeys, selection) {
        const {cols, rows} = this._selectionTable(this._selectionOrAll(rowKeys, selection));
        if (!cols.length || !rows.length) return;
        const struct = new gnr.GnrBag();
        cols.forEach((c, i) => {
            const attr = {field: 'c_' + i, name: c.label};
            if (c.dtype) attr.dtype = c.dtype;
            struct.setItem('view_0.rows_0.cell_' + i, null, attr);
        });
        const data = new gnr.GnrBag();
        rows.forEach((r, n) => {
            const attr = {};
            r.forEach((v, i) => { attr['c_' + i] = v; });
            data.setItem('r_' + n, null, attr);
        });
        genro.serverCall('app.includedViewAction',
                         {action: 'export', export_mode: 'xls', struct: struct, data: data, datamode: 'attr',
                          localized_data: true, downloadAs: this.nodeId + '_export'},
                         (url) => genro.download(url));
    }

    printRows(rowKeys, selection) {
        const Ctrl = gnr.GroupletGridController;
        const {cols, rows} = this._selectionTable(this._selectionOrAll(rowKeys, selection));
        if (!cols.length || !rows.length) return;
        const frame = document.createElement('iframe');
        frame.style.display = 'none';
        document.body.appendChild(frame);
        const doc = frame.contentDocument;
        doc.title = document.title;
        doc.head.appendChild(doc.createElement('style')).textContent = PRINT_CSS;
        const table = doc.body.appendChild(doc.createElement('table'));
        const line = (section, tag, values) => {
            const tr = section.appendChild(doc.createElement('tr'));
            values.forEach((v, i) => {
                const cell = tr.appendChild(doc.createElement(tag));
                cell.textContent = v;
                if (['N', 'L', 'I', 'R', 'F'].includes(cols[i].dtype)) cell.className = 'num';
            });
        };
        line(table.appendChild(doc.createElement('thead')), 'th', cols.map((c) => c.label));
        const body = table.appendChild(doc.createElement('tbody'));
        rows.forEach((r) => line(body, 'td', r.map((v, i) => Ctrl.printCell(v, cols[i]))));
        frame.contentWindow.addEventListener('afterprint', () => frame.remove());
        genro.dom.iFramePrint(frame);
    }

    static printCell(value, col) {
        if (value === null || value === undefined) return '';
        if (typeof value === 'boolean') return value ? '✓' : '';
        if (value instanceof Date || typeof value === 'number') {
            return String(genro.format(value, {dtype: col.dtype, format: col.format}));
        }
        return String(value);
    }

    _copyFields() {
        return this.structAdapter ? [] : this._firstRowFields();
    }

    _firstRowFields() {
        const tiles = [this.phantomTile, this.entryTile].concat(Object.values(this.tiles || {}));
        for (const tile of tiles) {
            const fields = tile ? this._rowFields(tile) : [];
            if (fields.length) return fields;
        }
        return [];
    }

    _copyColumns(fields) {
        // struct: every column, computed ones too; else the row's fields
        const Ctrl = gnr.GroupletGridController;
        if (this.structAdapter) {
            return this.structAdapter.cells.map((c) => ({
                path: c.field,
                label: String(_T((c.name || '').trim() || c.field)),
                labels: Ctrl._labelKeys([c.field, c.name]),
                dtype: c.dtype,
                format: c.format
            }));
        }
        return fields.map((f) => ({
            path: f.path,
            label: f.label ? String(_T(f.label)) : f.path,
            labels: f.labels,
            dtype: f.node && f.node.attr.dtype,
            format: f.node && f.node.attr.format
        }));
    }

    static copyCell(value) {
        // Read back by pasteValue: booleans as 1/0, dates ISO, numbers in
        // the locale without grouping.
        let t;
        if (value === null || value === undefined) t = '';
        else if (typeof value === 'boolean') t = value ? '1' : '0';
        else if (value instanceof Date) {
            t = [value.getFullYear(), value.getMonth() + 1, value.getDate()]
                .map((n, i) => String(n).padStart(i ? 2 : 4, '0')).join('-');
        } else if (typeof value === 'number') t = dojo.number.format(value, {pattern: '#0.##########'});
        else t = String(value);
        return /[\t\n\r"]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
    }

    _wirePhantomDnD(phantomDom) {
        this.dnd.wireAppendTarget(phantomDom);
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
                    if (node.attr && node.attr.card) {
                        this.templateCards[node.label] = node.attr.card;
                        if (origResource) this.templateCards[origResource] = node.attr.card;
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

gnr.GroupletGridController._selectionGroups = {};
gnr.GroupletGridController._lastSelected = null;
gnr.GroupletGridController._collapsedState = {};
gnr.GroupletGridController._entryGrids = new Set();

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
        this.hasCopy = false;
        this.editmenuSpec = null;
        this.dragEnabled = false;
        this.position = null;
        this._tileDnDHandlers = null;
        this._handleDnDHandlers = null;
        // the chrome band with chromeSide, a gnr.GroupletCard
        this.card = null;
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
        if (this._usesBand()) this._mountBand();
        else this._mountDragHandle();
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
        const focus = this._afterBodyMount;
        this._afterBodyMount = null;
        if (focus) setTimeout(focus, 0);
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
        if (this.controller.dnd) this.controller.dnd.unwireAppendTarget(this.tileDom);
        this._unwireTileDnD();
        this._unwireHandleDnD();
        if (this.card) this.card.destroy();
        this.card = null;
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
        this.profile = c._cardProfile(this.templateKey);
        this.delitem = ('delitem' in this.profile) ? this.profile.delitem : c.delitem;
        // template rows are deleted from the entry row
        this.hasDelete = !!this.delitem && !c.rowTemplate;
        this.hasCopy = !!c.copyitem && !c.rowTemplate;
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
        if (this._usesBand()) tileClass += ' grouplet_card grouplet_card--chrome-' + c.chromeSide;
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
                    && evt.target.closest('.grouplet_grid_row_delete,.grouplet_grid_row_copy,'
                        + '.grouplet_grid_row_kebab,.grouplet_grid_row_drag,'
                        + '.grouplet_grid_row_check,.grouplet_grid_row_collapse,'
                        + '.grouplet_card_chevron,.grouplet_card_doc,'
                        + '.grouplet_card_kebab,.grouplet_card_check');
                if (c.rowTemplate && !onChrome) {
                    c._onTemplateRowClick(pkey, evt);
                } else if (!onChrome && c._clickSelects(evt)) {
                    // the innermost row takes the click: the rows around it keep theirs
                    evt._groupletSelected = true;
                    c._onRowClickSelect(pkey, evt);
                } else if (!onChrome && c._clickClearsSelection(evt)) {
                    // a plain click leaves the selection for this row alone, unticked
                    evt._groupletSelected = true;
                    c.clearSelection(true);
                    c.selectTile(pkey);
                } else {
                    c.selectTile(pkey);
                }
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
            if (tile.tileDom && !tile._usesRowTemplate()) {
                tile.tileDom.addEventListener('paste', (e) => c._onRowsPaste(e, tile));
            }
            // with a band, its own onCreated places them
            if (tile._usesBand()) return;
            if (c.rowCheckbox && tile.tileDom) tile._mountCheckbox(tile.tileDom);
            if (c.collapsible && !c.rowTemplate && !c.structAdapter && tile.tileDom) {
                tile._mountCollapse(tile.tileDom);
            }
        };
        return tileKw;
    }

    _usesBand() {
        // cards gather their chrome in one band along a side, the band
        // being the drag source; line rows keep a gutter
        const c = this.controller;
        return !!c.chromeSide && !c.structAdapter && !c._isTabsLayout()
            && !this._usesRowTemplate();
    }

    _mountBand() {
        const c = this.controller;
        const pkey = this.pkey;
        const tile = this;
        const profile = this.profile;
        this.card = new gnr.GroupletCard({
            tools: profile.tools,
            rootDom: () => tile.domNode(),
            // the summary line's title, shown in the band open or folded
            title: (profile.title || c.titleField)
                ? (dom) => c._renderTitle(dom, profile.title, pkey) : null,
            doc: profile.docTemplate ? {
                html: (cb) => cb(gnr.GroupletCard.renderDoc(profile.docTemplate,
                                                             c.dataStore.rowValue(pkey), profile.doc_kw))
            } : null,
            collapsedClasses: ['grouplet_grid_row--collapsed', 'grouplet_card--collapsed'],
            collapse: c.collapsible ? {
                isCollapsed: () => c.isCollapsed(pkey),
                toggle: () => c.toggleCollapsed(pkey),
                expand: () => c.setCollapsed(pkey, false)
            } : null,
            checkbox: c.rowCheckbox ? {
                isChecked: () => !!(c._multiKeys && c._multiKeys.includes(pkey)),
                onClick: (e) => c._onRowCheck(pkey, e),
                onKeydown: (e) => { if (e.key === 'Escape') c._onMultiKeydown(e); }
            } : null,
            drag: this.dragEnabled ? {
                start: (e) => c.dnd.tileDragStart(e, tile.tileDom, pkey),
                end: () => c.dnd.tileDragEnd(tile.tileDom)
            } : null
        });
        this.card.mount(this.tileContent, '_grtile_band_' + pkey);
    }

    _chromeContent() {
        return this.card ? this.card.bandContent : this.tileContent;
    }

    _bandMenuSpec() {
        // the band's kebab: the editmenu entries, then Copy, then Delete
        // when rows can be deleted (it takes the place of the trash)
        const spec = objectUpdate({}, this.editmenuSpec || {});
        const del = spec['delete'];
        delete spec['delete'];
        if (!('copy' in spec)) spec.copy = true;
        if (this.hasDelete) spec['delete'] = (del && del !== true) ? del : true;
        return spec;
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
        box.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') c._onMultiKeydown(e);
        });
        tileDom.insertBefore(box, tileDom.firstChild);
    }

    _mountCollapse(tileDom) {
        // Plain DOM like the checkbox: the toggle and the summary line shown
        // while folded; the controller holds the state.
        const c = this.controller;
        const pkey = this.pkey;
        const toggle = document.createElement('div');
        toggle.className = 'grouplet_grid_row_collapse';
        toggle.setAttribute('role', 'button');
        toggle.tabIndex = 0;
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            c.toggleCollapsed(pkey);
        });
        toggle.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            e.preventDefault();
            c.toggleCollapsed(pkey);
        });
        const line = document.createElement('div');
        line.className = 'grouplet_grid_row_summaryline';
        line.addEventListener('click', () => c.setCollapsed(pkey, false));
        tileDom.insertBefore(line, tileDom.firstChild);
        tileDom.insertBefore(toggle, tileDom.firstChild);
        c._applyCollapsed(pkey);
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
        if (!this.card) {
            this._mountDelete();
            this._mountCopy();
        }
        this._mountKebab();
    }

    _toolClass(baseClass, tool) {
        // the right-hand tools sit side by side, slot 0 at the edge; a
        // card's kebab stays apart, halfway down the card
        const tools = [];
        if (this.controller.structAdapter && this.editmenuSpec) tools.push('kebab');
        if (this.hasDelete) tools.push('delete');
        if (this.hasCopy) tools.push('copy');
        const slot = tools.indexOf(tool);
        return slot > 0 ? baseClass + ' grouplet_grid_tool_slot_' + slot : baseClass;
    }

    _destroyChrome() {
        const content = this.tileContent && this._chromeContent();
        if (!content) return;
        const delLabel = '_grtile_del_' + this.pkey;
        const copyLabel = '_grtile_copy_' + this.pkey;
        const kebabLabel = '_grtile_kebab_' + this.pkey;
        if (content.getNode(delLabel, 'static')) {
            content.popNode(delLabel);
        }
        if (content.getNode(copyLabel, 'static')) {
            content.popNode(copyLabel);
        }
        if (content.getNode(kebabLabel, 'static')) {
            content.popNode(kebabLabel);
        }
    }

    _mountDelete() {
        if (!this.hasDelete) return;
        const c = this.controller;
        const pkey = this.pkey;
        const topic = c.actionTopic;
        const delClass = this._toolClass('grouplet_grid_row_delete', 'delete');
        const delKw = objectUpdate({
            _class: delClass,
            tip: _T('!!Delete row'),
            connect_onclick: "genro.publish('" + topic + "',"
                            + "{action:'delete',rowKey:'" + pkey + "'});"
        }, c.delitemKw || {});
        if (c.delitemKw && c.delitemKw._class) {
            delKw._class = delClass + ' ' + c.delitemKw._class;
        }
        this.tileContent._('div', '_grtile_del_' + pkey, delKw);
    }

    _mountCopy() {
        if (!this.hasCopy) return;
        const c = this.controller;
        const pkey = this.pkey;
        const topic = c.actionTopic;
        const copyClass = this._toolClass('grouplet_grid_row_copy', 'copy');
        const copyKw = objectUpdate({
            _class: copyClass,
            tip: _T('!!Copy row'),
            connect_onclick: "genro.publish('" + topic + "',"
                            + "{action:'copy',rowKey:'" + pkey + "'});"
        }, c.copyitemKw || {});
        if (c.copyitemKw && c.copyitemKw._class) {
            copyKw._class = copyClass + ' ' + c.copyitemKw._class;
        }
        this.tileContent._('div', '_grtile_copy_' + pkey, copyKw);
    }

    _mountKebab() {
        const editmenu = this.card ? this._bandMenuSpec() : this.editmenuSpec;
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
            copy: {
                label: '^' + c.controllerPath + '.row_menu.copy_label',
                iconClass: 'iconbox copy duplicate_record',
                action: "genro.publish('" + topic + "',"
                      + "{action:'copy',rowKey:'" + pkey + "'});"
            },
            'delete': {
                label: '^' + c.controllerPath + '.row_menu.delete_label',
                iconClass: 'iconbox trash',
                _class: 'grouplet_grid_menu_danger',
                // set as the menu opens: locked form, or minRows reached
                disabled: '^' + c.controllerPath + '.row_menu.delete_locked',
                action: "genro.publish('" + topic + "',"
                      + "{action:'delete',rowKey:'" + pkey + "'});"
            }
        };
        const kebabClass = this.card ? 'grouplet_card_kebab'
                                     : this._toolClass('grouplet_grid_row_kebab', 'kebab');
        const kebabKw = objectUpdate({
            _class: kebabClass,
            tip: _T('!!Row actions'),
            nodeId: '__grpgridtilemenu__' + c.nodeId + '__' + pkey,
            connect_onmousedown: function() { c._refreshRowMenu(pkey); }
        }, c.editmenuKw || {});
        if (c.editmenuKw && c.editmenuKw._class) {
            kebabKw._class = kebabClass + ' ' + c.editmenuKw._class;
        }
        gnr.GroupletCard.buildKebab(this._chromeContent(), '_grtile_kebab_' + pkey, editmenu, presets, kebabKw,
                                    this.card ? 'grouplet_card_kebab_icon' : 'grouplet_grid_kebab_icon');
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
        const bandLabel = '_grtile_band_' + this.pkey;
        const labelsToRemove = [];
        this.tileContent.getNodes().forEach((n) => {
            if (n.label === delLabel || n.label === kebabLabel || n.label === bandLabel) return;
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
        this.hasCopy = false;
        this.dragEnabled = false;
        this.editmenuSpec = null;
    }

    _usesBand() {
        return false;
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
                    if (c.dnd) c._wirePhantomDnD(tile.tileDom);
                    tile.tileDom.addEventListener('keydown',
                        (e) => c._onEntryKeydown(e), true);
                    tile.tileDom.addEventListener('focusin', (e) => {
                        c._entryWidget = dijit.getEnclosingWidget(e.target);
                        c._refreshEntryDefaults();
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
