var gnr_grouplet = {
    wizardNext: function(sourceNode, frameCode) {
        var formId = frameCode + '_step_form';
        var form = genro.formById(formId);
        if (form && !form.isValid()) {
            genro.publish('floating_message', {
                message: 'Please complete required fields',
                messageType: 'warning'
            });
            return;
        }
        if (form) {
            form.save();
        }
        var frameNode = genro.getFrameNode(frameCode);
        var idx = frameNode.getRelativeData('.step_index');
        var steps = frameNode.getRelativeData('.wizard_steps');
        var nodes = steps.getNodes();
        var currentNode = nodes[idx];
        if (currentNode) {
            genro.publish(frameCode + '_step_complete',
                {step_code: currentNode.attr.code});
        }
        if (idx >= nodes.length - 1) {
            genro.publish(frameCode + '_complete');
        } else {
            frameNode.setRelativeData('.step_index', idx + 1);
        }
    },

    wizardGoTo: function(sourceNode, targetIdx, frameCode) {
        var frameNode = genro.getFrameNode(frameCode);
        var idx = frameNode.getRelativeData('.step_index');
        var showingSummary = frameNode.getRelativeData('.wizard_showing_summary');
        if (showingSummary) {
            var editable = frameNode.getRelativeData('.summary_editable');
            if (!editable) { return; }
            frameNode.setRelativeData('.wizard_page', 'steps');
            frameNode.setRelativeData('.wizard_showing_summary', false);
        }
        if (targetIdx !== idx) {
            if (targetIdx < idx) {
                var formId = frameCode + '_step_form';
                var form = genro.formById(formId);
                if (form) {
                    form.save();
                }
            }
            frameNode.setRelativeData('.step_index', targetIdx);
        }
    },

    wizardUpdateStep: function(sourceNode, idx, completeLabel, frameCode) {
        var steps = sourceNode.getRelativeData('.wizard_steps');
        var nodes = steps.getNodes();
        var node = nodes[idx];
        if (!node) { return; }
        sourceNode.setRelativeData('.current_resource', node.attr.resource);
        var isLast = (idx >= nodes.length - 1);
        sourceNode.setRelativeData('.next_label',
            isLast ? completeLabel : nodes[idx + 1].attr.grouplet_caption);
        this._updateStepperUI(nodes, idx, frameCode);
    },

    _updateStepperUI: function(nodes, activeIdx, frameCode) {
        for (var i = 0; i < nodes.length; i++) {
            var stepNode = genro.nodeById(frameCode + '_step_' + i);
            if (!stepNode) { continue; }
            var el = stepNode.domNode;
            el.classList.remove('completed', 'active', 'pending');
            var circle = el.querySelector('.wizard_circle');
            if (i < activeIdx) {
                el.classList.add('completed');
                circle.innerHTML = '&#10003;';
            } else if (i === activeIdx) {
                el.classList.add('active');
                circle.textContent = String(i + 1);
            } else {
                el.classList.add('pending');
                circle.textContent = String(i + 1);
            }
            if (i > 0) {
                var connNode = genro.nodeById(frameCode + '_conn_' + i);
                if (connNode) {
                    connNode.domNode.classList.toggle('completed', i <= activeIdx);
                }
            }
        }
    },

    panelSelectFromCode: function(sourceNode, code) {
        if (code) {
            var menu = sourceNode.getRelativeData('.grouplet_menu');
            var node = menu.getNode(code);
            if (node) {
                sourceNode.setRelativeData('.grouplet_info', new gnr.GnrBag(node.attr));
                sourceNode.setRelativeData('.selected_resource', node.attr.resource);
            }
        }
    }
};

gnr.GroupletGridController = class GroupletGridController {
    constructor(sourceNode, kw) {
        this.sourceNode = sourceNode;
        // bodyNode is passed in as an already-resolved sourceNode
        // (looked up via the `_gg_body` attribute marker in the bootstrap
        // dataController). nodeId is read directly from the live
        // container — by the time this constructor fires, namespacing
        // (if any) has already been applied so sourceNode.attr.nodeId
        // is the per-instance unique id.
        // The phantom `+` add button is NOT passed in: the controller
        // builds it client-side via `_buildLayoutAffordances` (which
        // also handles the tabbar in tabs mode). Stored as
        // `this.addBtnDom` (raw DOM, not a sourceNode).
        this.bodyNode = kw.bodyNode || null;
        this.addBtnDom = null;
        this.tabbarDom = null;
        this.tabstripDom = null;
        this.nodeId = sourceNode.attr.nodeId;
        // Absolute datapath of the rows Bag — resolved once against the
        // container's datapath chain (`mixin_absStorepath` does the same
        // in genro_grid.js:3066-3068).
        this.storepath = sourceNode.absDatapath(sourceNode.attr.storepath);
        this.resource = kw.resource || null;
        this.handler = kw.handler || null;
        this.table = kw.table || null;
        this.grouplets_root = kw.grouplets_root;
        this.grouplet_kw = kw.grouplet_kw || {};
        this.cols = kw.cols || 1;
        this.minWidth = kw.min_width || null;
        this.gap = kw.gap || '12px';
        // Action affordances (Item 10 API):
        //   additem  : bool — phantom '+' (rendered server-side as a
        //              lightButton in body/tabbar). The controller does not
        //              build it; only used to gate maxRows logic.
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
        // Drag-and-drop: when `dragCode` is non-null each row is rendered
        // with a drag handle (left side). `dragCode` is the data-transfer
        // key — only payloads with the same key are accepted as drop
        // sources, so two grids with different `dragCode` values are
        // isolated (default behavior: dragCode = nodeId, server-side).
        // Cross-grid sharing requires explicitly passing the same dragCode.
        this.dragCode = kw.dragCode || null;
        this._dragOverRow = null;
        this._dragHandlesByRow = {};
        // Tabs mode (Item 11): `layout='tabs'` swaps the cards body for
        // a horizontal tab strip with one chip per row. The active tab
        // shows its panel (all others get `display:none` via CSS — hidden
        // panels stay mounted, subscriptions intact). `setLayout()` flips
        // between modes at runtime.
        this.layout = kw.layout || 'cards';
        this.titleField = kw.titleField || null;
        this.emptyTitle = kw.emptyTitle || _T('!!Untitled');
        this.activeRowKey = null;
        this._tabsByRow = {};         // rowKey -> chip DOM element
        this._pendingActivate = null; // rowKey to auto-activate on next _addRow
        this.templateSource = null;
        this.templateLoading = null;
        this.rows = {};
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
        const that = this;
        dojo.connect(sourceNode, '_onDeleting', function() { that.destroy(); });
        // Initial render: the store-driven dispatch (`gnr_storepath`) is
        // wired by the bootstrap dataController in grouplet.py, but the
        // first build of the container does not produce a 'storepath'
        // trigger — seed the render once here. Subsequent mutations
        // flow through `gnr_storepath`; whole-store replacements call
        // `_renderFromStore` again from there.
        this._renderFromStore();
        this._updateAddBtnState();
    }

    storebag() {
        // Fresh lookup of the rows Bag on every call (no caching),
        // mirroring `gnrgrid.mixin_storebag` (genro_grid.js:3230-3236).
        return genro.getData(this.storepath);
    }

    _renderFromStore() {
        // Render the grid from scratch against the current Bag at
        // `storepath`. Used at construct time and whenever the Bag root
        // is replaced (the gnrgrid-equivalent of `newDataStore`).
        const bag = this.storebag();
        if (!(bag instanceof gnr.GnrBag) || bag.len() === 0) {
            // Nothing to render — clear stale tiles if any survived.
            Object.keys(this.rows).forEach((rowKey) => this._removeRow(rowKey));
            return;
        }
        const that = this;
        this._ensureTemplate(function() { that._fullSync(); });
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
        //   parent_lv > 1  → mutation INSIDE a row (field/sub-bag):
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
        if (parent_lv === 0) {
            // Whole-store replacement: rebuild from the new Bag.
            this._renderFromStore();
            return;
        }
        if (parent_lv > 1) {
            // Tabs mode label refresh: walk up the changed node's
            // parentship chain to find the row-level node (parent_lv=1)
            // and, if the mutated leaf is the titleField, repaint the
            // chip's title text. Other intra-row mutations are
            // ignored (widgets do their own binding).
            if (this._isTabsLayout() && this.titleField) {
                this._maybeRefreshTabLabel(kw.node, storeNode);
            }
            return;
        }
        if (parent_lv !== 1) return;
        const rowKey = kw.node.label;
        if (!rowKey) return;
        const that = this;
        if (kw.evt === 'ins') {
            this._ensureTemplate(function() { that._addRow(rowKey); });
        } else if (kw.evt === 'del') {
            this._removeRow(rowKey);
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
                if (leafLabel === this.titleField) {
                    const chip = this._tabsByRow[cur.label];
                    if (chip) {
                        const title = chip.querySelector(
                            ':scope > .grouplet_grid_tab_title');
                        if (title) {
                            title.textContent = this._readTabLabel(cur.label);
                        }
                    }
                }
                return;
            }
            leafLabel = (leafLabel === null)
                ? cur.label
                : (cur.label + '.' + leafLabel);
            cur = parent;
        }
    }

    _applyResponsiveLayout() {
        if (!(this.minWidth && this.cols > 1)) return;
        // Set custom properties on the container (stable across body rebuilds).
        // CSS uses these to drive the grid layout on .grouplet_grid_body.
        const container = this.sourceNode && this.sourceNode.getDomNode
            && this.sourceNode.getDomNode();
        if (!container) {
            console.warn('[GG] container dom not ready for responsive');
            return;
        }
        container.style.setProperty('--gg-cols', String(this.cols));
        container.style.setProperty('--gg-min-width', this.minWidth);
        container.style.setProperty('--gg-gap', this.gap);
        container.classList.add('gg-responsive');
    }

    _applySlotClasses() {
        // Add .has-top / .has-bottom / .has-left / .has-right when the
        // matching slot div has actual content. CSS uses these to expand
        // the grid track from 0 to auto and to reveal the slot itself.
        const container = this.sourceNode && this.sourceNode.getDomNode
            && this.sourceNode.getDomNode();
        if (!container) return;
        ['top', 'bottom', 'left', 'right'].forEach((side) => {
            const slot = container.querySelector(
                ':scope > .grouplet_grid_slot_' + side);
            if (slot && slot.children.length > 0) {
                container.classList.add('has-' + side);
            }
        });
    }

    // --- Layout affordances (cards `+` footer / tabs tabbar) ---
    //
    // All layout-specific DOM is built client-side, never emitted from
    // Python. Cards mode appends a `.grouplet_grid_footer` div inside
    // the body (CSS `order:999` parks it after rows). Tabs mode inserts
    // a `.grouplet_grid_tabbar` between the `top` slot and the body
    // (CSS `grid-template-areas` pins it), plus a `+` chip on its right.
    // `setLayout()` swaps between the two without touching row panels.

    _isTabsLayout() {
        return this.layout === 'tabs' || this.layout === 'vtabs';
    }

    _buildLayoutAffordances() {
        const containerDom = this.sourceNode && this.sourceNode.getDomNode
            && this.sourceNode.getDomNode();
        if (!containerDom) return;
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
            Object.keys(this.rows).forEach((rowKey) => {
                this._addTabChip(rowKey);
            });
            // If at least one row exists and none is currently active,
            // activate the first.
            const allKeys = Object.keys(this.rows);
            if (allKeys.length > 0 && !this.activeRowKey) {
                this._activateTab(allKeys[0]);
            } else if (this.activeRowKey && this.rows[this.activeRowKey]) {
                this._setActiveTabClasses(this.activeRowKey);
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
        this._tabsByRow = {};
        // Strip tab-active class from any surviving row wrapper.
        Object.keys(this.rows).forEach((rowKey) => {
            const entry = this.rows[rowKey];
            const live = entry && genro.nodeById(entry.wrapperNodeId);
            const dom = live && live.getDomNode && live.getDomNode();
            if (dom) dom.classList.remove('gg-tab-active');
        });
    }

    setLayout(newLayout) {
        // Public API: flip between 'cards', 'tabs' and 'vtabs' at
        // runtime. Row panels survive the switch (only layout-specific
        // DOM is rebuilt). Selection is preserved when going from one
        // tabs flavor to another (or cards → tabs/vtabs); going to
        // cards clears `activeRowKey` since there is no active concept.
        if (newLayout !== 'cards'
            && newLayout !== 'tabs'
            && newLayout !== 'vtabs') {
            console.warn('[GG] setLayout: unknown layout', newLayout);
            return;
        }
        if (newLayout === this.layout) return;
        const prevActive = this.activeRowKey;
        this._teardownLayoutAffordances();
        this.layout = newLayout;
        if (newLayout === 'cards') {
            this.activeRowKey = null;
        } else {
            // Keep the previously selected row as the active tab if it
            // still exists; the build pass below will install the
            // chip and apply `.gg-tab-active`.
            if (prevActive && this.rows[prevActive]) {
                this.activeRowKey = prevActive;
            }
        }
        this._buildLayoutAffordances();
    }

    _buildCardsFooter(containerDom) {
        // The phantom `+` is appended to the CONTAINER (not to the
        // body) so that the framework's row rendering inside the body
        // never touches it. CSS pins the footer to its own grid-area
        // (`addbtn`) so it sits directly below the body, mimicking the
        // previous "in-body footer with order:999" layout.
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
        // Place the tabbar at the start of the container (after the
        // top slot if present, else first). CSS grid-template-areas
        // pins it to the `tabbar` area; document order only matters
        // for accessibility / source-reading order.
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

    // --- Tab chip lifecycle ---

    _addTabChip(rowKey) {
        if (!this.tabstripDom) return;
        if (this._tabsByRow[rowKey]) return;
        const chip = document.createElement('div');
        chip.className = 'grouplet_grid_tab';
        chip.setAttribute('data-rowkey', rowKey);
        const title = document.createElement('div');
        title.className = 'grouplet_grid_tab_title';
        title.textContent = this._readTabLabel(rowKey);
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
                    {action: 'delete', rowKey: rowKey});
            });
            chip.appendChild(closeBtn);
        }
        const that0 = this;
        chip.addEventListener('click', function() {
            that0._activateTab(rowKey);
        });
        // Insert at the correct position relative to existing chips,
        // mirroring the Bag order. The chip strip is always in sync
        // with the Bag thanks to the `gnr_storepath` pipeline — but
        // for the FIRST render after a fullSync we mount in Bag order.
        const bag = this.storebag();
        let inserted = false;
        if (bag instanceof gnr.GnrBag) {
            const allKeys = bag.getNodes().map((n) => n.label);
            const idx = allKeys.indexOf(rowKey);
            for (let j = idx + 1; j < allKeys.length; j++) {
                if (this._tabsByRow[allKeys[j]]) {
                    this.tabstripDom.insertBefore(
                        chip, this._tabsByRow[allKeys[j]]);
                    inserted = true;
                    break;
                }
            }
        }
        if (!inserted) {
            this.tabstripDom.appendChild(chip);
        }
        this._tabsByRow[rowKey] = chip;
        if (this.dragCode) {
            this._wireTabDnD(chip, rowKey);
        }
        // Reactive label refresh is handled by `gnr_storepath` →
        // `_maybeRefreshTabLabel` whenever the row's titleField mutates.
        // No per-chip subscription needed.
    }

    _removeTabChip(rowKey) {
        const chip = this._tabsByRow[rowKey];
        if (!chip) return;
        if (this.dragCode) {
            this._unwireTabDnD(rowKey);
        }
        if (chip.parentNode) chip.parentNode.removeChild(chip);
        delete this._tabsByRow[rowKey];
    }

    _readTabLabel(rowKey) {
        if (!this.titleField) return rowKey;
        const v = genro.getData(
            this.storepath + '.' + rowKey + '.' + this.titleField);
        if (v === undefined || v === null || v === '') {
            return _T(this.emptyTitle);
        }
        return String(v);
    }

    _activateTab(rowKey) {
        if (!this._isTabsLayout()) return;
        if (this.activeRowKey === rowKey) return;
        this.activeRowKey = rowKey;
        this._setActiveTabClasses(rowKey);
        // Hook for Item 12 (form swap): publish activation on the action
        // bus. No internal subscriber for now — it is a pure extension
        // point. External listeners can use it (e.g. `+` auto-focus).
        genro.publish(this.actionTopic,
            {action: 'activate', rowKey: rowKey});
    }

    _setActiveTabClasses(activeRowKey) {
        // Toggles `.gg-tab-active` on every chip and every row wrapper.
        // Idempotent: safe to call on every render / activation.
        Object.keys(this._tabsByRow).forEach((rk) => {
            const chip = this._tabsByRow[rk];
            if (!chip) return;
            chip.classList.toggle('gg-tab-active', rk === activeRowKey);
        });
        Object.keys(this.rows).forEach((rk) => {
            const entry = this.rows[rk];
            const live = entry && genro.nodeById(entry.wrapperNodeId);
            const dom = live && live.getDomNode && live.getDomNode();
            if (dom) dom.classList.toggle('gg-tab-active', rk === activeRowKey);
        });
    }

    // --- Tab DnD (mirror of _wireRowDnD with chip selectors) ---
    //
    // The chip itself is the drag handle in tabs mode (no `⠿` glyph).
    // Same data-transfer payload as `_wireRowDnD`, so cross-grid drag
    // works between any combination of cards-mode and tabs-mode grids
    // sharing a `dragCode`. The drop position is always "before the
    // target chip" — same convention as cards mode.

    _wireTabDnD(chipDom, rowKey) {
        const that = this;
        const dataKey = 'application/x-gg-' + this.dragCode;
        const containerDom = this.sourceNode && this.sourceNode.getDomNode
            && this.sourceNode.getDomNode();
        chipDom.setAttribute('draggable', 'true');
        const onDragStart = function(e) {
            try {
                e.dataTransfer.setData(dataKey, JSON.stringify({
                    rowKey: rowKey, nodeId: that.nodeId
                }));
                e.dataTransfer.setData('text/plain', rowKey);
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
            if (containerDom) containerDom.classList.add('gg-drag-active');
            e.stopPropagation();
        };
        const onDragEnd = function() {
            chipDom.classList.remove('gg-dragging');
            that._clearDragOver();
            if (containerDom) containerDom.classList.remove('gg-drag-active');
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
                if (payload.rowKey === rowKey) return;
                genro.publish(that.actionTopic, {
                    action: 'move',
                    rowKey: payload.rowKey,
                    position: '<' + rowKey
                });
                return;
            }
            const sourceCtrl = that._findSourceController(payload.nodeId);
            if (!sourceCtrl) {
                console.warn('[GG] cross drop: source ctrl not found',
                             payload.nodeId);
                return;
            }
            that._doMoveRowFrom(sourceCtrl, payload.rowKey, '<' + rowKey);
        };
        chipDom.addEventListener('dragstart', onDragStart);
        chipDom.addEventListener('dragend', onDragEnd);
        chipDom.addEventListener('dragover', onDragOver);
        chipDom.addEventListener('dragleave', onDragLeave);
        chipDom.addEventListener('drop', onDrop);
        // Reuse `_dragHandlesByRow` storage — keying by rowKey is unique
        // per controller, and tabs mode never has a `_wireRowDnD` peer
        // for the same row (only the chip is wired).
        this._dragHandlesByRow[rowKey] = {
            dom: chipDom,
            handlers: {dragstart: onDragStart, dragend: onDragEnd,
                       dragover: onDragOver, dragleave: onDragLeave,
                       drop: onDrop}
        };
    }

    _unwireTabDnD(rowKey) {
        // Identical teardown to `_unwireRowDnD` since both store under
        // the same `_dragHandlesByRow` key; reuse the existing method.
        this._unwireRowDnD(rowKey);
    }

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
                this._doAddRow(payload.position, payload.defaults);
                break;
            case 'delete': {
                // If no rowKey is provided fall back to the currently
                // selected row — used by toolbar '−' buttons that act on
                // the selection rather than on a specific row.
                const rowKey = payload.rowKey || this.selectedRowKey;
                if (!rowKey) {
                    console.info('[GG] delete: no rowKey and no selection');
                    return;
                }
                this._askAndDeleteRow(rowKey);
                break;
            }
            case 'move':
                this._doMoveRow(payload.rowKey, payload.position);
                break;
            default:
                console.warn('[GG] unknown action', payload);
        }
    }

    _wireRowDnD(wrapperDom, rowKey) {
        // Wire HTML5 drag-and-drop directly on a row wrapper (mounted DOM).
        // Called from _addRow after unfreeze. The drag handle inside the
        // wrapper carries `draggable="true"` so dragstart fires; here we
        // listen on the wrapper itself for dragstart/dragend (bubbled from
        // the handle) and dragover/drop (the wrapper is the drop zone).
        // Drop position is always "before the target row" — the cursor's
        // Y inside the row is irrelevant: any hit on the wrapper highlights
        // the whole card and inserts the dragged row at that index.
        const that = this;
        const dataKey = 'application/x-gg-' + this.dragCode;
        const containerDom = this.sourceNode && this.sourceNode.getDomNode
            && this.sourceNode.getDomNode();
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
            if (innermostWrapper !== wrapperDom) return;
            try {
                e.dataTransfer.setData(dataKey, JSON.stringify({
                    rowKey: rowKey, nodeId: that.nodeId
                }));
                // Some browsers also need a generic text payload to start.
                e.dataTransfer.setData('text/plain', rowKey);
                e.dataTransfer.effectAllowed = 'move';
            } catch (err) { /* IE/Safari quirks */ }
            // Drag image = snapshot of THIS row wrapper. The clone goes
            // into the global '#auxDragImage' off-screen container,
            // becomes the browser's drag image, and is cleaned up on
            // next tick (the snapshot is captured synchronously).
            try {
                const auxDragImage = document.getElementById('auxDragImage');
                if (auxDragImage) {
                    const clone = wrapperDom.cloneNode(true);
                    clone.classList.remove('gg-dragging', 'gg-drop-target',
                        'gg-drop-target-invalid', 'gg-just-dropped');
                    clone.style.width = wrapperDom.offsetWidth + 'px';
                    auxDragImage.appendChild(clone);
                    e.dataTransfer.setDragImage(clone,
                        e.clientX - wrapperDom.getBoundingClientRect().left,
                        e.clientY - wrapperDom.getBoundingClientRect().top);
                    setTimeout(function() {
                        if (clone.parentNode) {
                            clone.parentNode.removeChild(clone);
                        }
                    }, 0);
                }
            } catch (err) { /* setDragImage not supported */ }
            wrapperDom.classList.add('gg-dragging');
            if (containerDom) {
                containerDom.classList.add('gg-drag-active');
            }
            // Stop propagation so an outer grid's wrapper does not
            // re-process this dragstart and override the dataTransfer
            // payload + drag image with its own.
            e.stopPropagation();
        };
        const onDragEnd = function() {
            wrapperDom.classList.remove('gg-dragging');
            that._clearDragOver();
            if (containerDom) {
                containerDom.classList.remove('gg-drag-active');
            }
        };
        const onDragOver = function(e) {
            // Distinguish valid vs invalid drops by inspecting the
            // payload's data-transfer keys (available on dragover; the
            // actual data is not). A key matching our `dataKey` → valid.
            // A different `application/x-gg-*` key → another grid with
            // a different dragCode (isolated by default) → invalid.
            // Anything else (text/plain alone, foreign drags) → ignore.
            if (wrapperDom.classList.contains('gg-dragging')) {
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
            that._setDragOver(wrapperDom, isValid);
        };
        const onDragLeave = function(e) {
            // Only clear when leaving the wrapper, not when crossing into
            // a child element.
            if (!wrapperDom.contains(e.relatedTarget)) {
                if (that._dragOverRow === wrapperDom) that._clearDragOver();
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
                if (payload.rowKey === rowKey) return;
                genro.publish(that.actionTopic, {
                    action: 'move',
                    rowKey: payload.rowKey,
                    position: '<' + rowKey
                });
                return;
            }
            // Cross-instance drop: same dragCode (already filtered by
            // matching `dataKey`) but different controllers. Resolve the
            // source controller and migrate the row directly. This branch
            // is only reached when both grids share an explicit `dragCode`
            // — server-side default keeps dragCode = nodeId, so cross
            // drops cannot happen by accident.
            const sourceCtrl = that._findSourceController(payload.nodeId);
            if (!sourceCtrl) {
                console.warn('[GG] cross drop: source ctrl not found',
                             payload.nodeId);
                return;
            }
            that._doMoveRowFrom(sourceCtrl, payload.rowKey, '<' + rowKey);
        };
        wrapperDom.addEventListener('dragstart', onDragStart);
        wrapperDom.addEventListener('dragend', onDragEnd);
        wrapperDom.addEventListener('dragover', onDragOver);
        wrapperDom.addEventListener('dragleave', onDragLeave);
        wrapperDom.addEventListener('drop', onDrop);
        // Track for teardown: the listeners are anonymous closures, so we
        // store references keyed by rowKey.
        this._dragHandlesByRow[rowKey] = {
            dom: wrapperDom,
            handlers: {dragstart: onDragStart, dragend: onDragEnd,
                       dragover: onDragOver, dragleave: onDragLeave,
                       drop: onDrop}
        };
    }

    _unwireRowDnD(rowKey) {
        const entry = this._dragHandlesByRow[rowKey];
        if (!entry) return;
        Object.keys(entry.handlers).forEach((evt) => {
            entry.dom.removeEventListener(evt, entry.handlers[evt]);
        });
        delete this._dragHandlesByRow[rowKey];
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
        const containerDom = this.sourceNode && this.sourceNode.getDomNode
            && this.sourceNode.getDomNode();
        if (!containerDom) return;
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
                that._doMoveRowSameInstance(payload.rowKey, null);
                return;
            }
            const sourceCtrl = that._findSourceController(payload.nodeId);
            if (!sourceCtrl) {
                console.warn('[GG] container drop: source ctrl not found',
                             payload.nodeId);
                return;
            }
            that._doMoveRowFrom(sourceCtrl, payload.rowKey, null);
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

    _doMoveRowSameInstance(rowKey, position) {
        // Same-instance reorder, position can be null → append at tail.
        // Bag-only mutation; the DOM diff is done by `gnr_storepath`.
        const dataBag = this.storebag();
        if (!(dataBag instanceof gnr.GnrBag)) return;
        const node = dataBag.getNode(rowKey);
        if (!node) return;
        const rowValue = node.getValue();
        const rowAttrs = node.getAttr() || {};
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[rowKey] = true;
        dataBag.popNode(rowKey);
        const setKw = position ? {_position: position} : {};
        dataBag.setItem(rowKey, rowValue, rowAttrs, setKw);
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

    _doMoveRow(rowKey, position) {
        // Reorder a row inside the rows Bag. `position` is '<targetKey'
        // or '>targetKey'. Bag-only mutation; the DOM diff is done by
        // `gnr_storepath` reacting to the `del`+`ins` trigger pair.
        const dataBag = this.storebag();
        if (!(dataBag instanceof gnr.GnrBag)) {
            console.warn('[GG] _doMoveRow: no Bag at', this.storepath);
            return;
        }
        const node = dataBag.getNode(rowKey);
        if (!node) {
            console.warn('[GG] _doMoveRow: row not found', rowKey);
            return;
        }
        const rowValue = node.getValue();
        const rowAttrs = node.getAttr() || {};
        this._pendingFlash = this._pendingFlash || {};
        this._pendingFlash[rowKey] = true;
        dataBag.popNode(rowKey);
        dataBag.setItem(rowKey, rowValue, rowAttrs, {_position: position});
    }

    _findSourceController(sourceNodeId) {
        // Resolves the controller of another GroupletGrid instance on the
        // same page. The controller is attached to its container node by
        // the `dataController` bootstrap in grouplet.py — `node.gridController`.
        const node = genro.nodeById(sourceNodeId);
        return (node && node.gridController) || null;
    }

    _doMoveRowFrom(sourceCtrl, sourceRowKey, targetPosition) {
        // Migrate a row from another grid instance into THIS grid.
        // Bag-only mutation on source and target; each side's
        // `gnr_storepath` reacts to its own `del`/`ins` and rebuilds
        // its tiles.
        if (!sourceCtrl || sourceCtrl === this) return;
        const sourceBag = sourceCtrl.storebag();
        const targetBag = this.storebag();
        if (!(sourceBag instanceof gnr.GnrBag)
            || !(targetBag instanceof gnr.GnrBag)) {
            console.warn('[GG] _doMoveRowFrom: bags not found',
                         sourceCtrl.storepath, this.storepath);
            return;
        }
        const node = sourceBag.getNode(sourceRowKey);
        if (!node) {
            console.warn('[GG] _doMoveRowFrom: source row not found',
                         sourceRowKey);
            return;
        }
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

    _flashRow(rowKey) {
        // Just-dropped flash: the row inherits the drop-target tint for
        // ~260ms then transitions back to normal. CSS handles the
        // fade-out via `transition` on background/border, so JS only
        // adds the class and removes it later.
        const that = this;
        setTimeout(function() {
            const entry = that.rows[rowKey];
            const liveNode = entry && genro.nodeById(entry.wrapperNodeId);
            const dom = liveNode && liveNode.getDomNode
                && liveNode.getDomNode();
            if (!dom) return;
            dom.classList.add('gg-just-dropped');
            setTimeout(function() {
                dom.classList.remove('gg-just-dropped');
            }, 260);
        }, 0);
    }

    destroy() {
        if (this._destroyed) return;
        this._destroyed = true;
        this.sourceNode.unregisterSubscription(this.actionTopic);
        this._unwireContainerDnD();
        Object.keys(this.rows).forEach((rowKey) => this._removeRow(rowKey));
        // Tear down the layout-specific scaffolding (tabbar / footer +
        // any surviving chip subscriptions). Safe to call regardless of
        // current layout.
        this._teardownLayoutAffordances();
        this.templateSource = null;
        this.templateLoading = null;
    }

    _fullSync() {
        const bag = this.storebag();
        const presentKeys = {};
        const toAdd = [];
        if (bag instanceof gnr.GnrBag) {
            const that = this;
            bag.getNodes().forEach(function(node) {
                presentKeys[node.label] = true;
                if (!that.rows[node.label]) {
                    toAdd.push(node.label);
                }
            });
        }
        Object.keys(this.rows).forEach((rowKey) => {
            if (!presentKeys[rowKey]) {
                this._removeRow(rowKey);
            }
        });
        if (toAdd.length === 0) return;
        // Tabs mode: pre-decide which row will be active so `_addRow`
        // can stamp `gg-tab-active` directly onto the wrapper's `_class`
        // BEFORE the wrapper is built. Without this, all wrappers mount
        // with `display:none` (CSS hides every non-active row in tabs
        // mode), and nested groupletGrids inside them — which run their
        // own `_renderFromStore` on `_onBuilt` — would render their
        // body subtree while detached from layout flow. By activating
        // up-front, the first wrapper is `display:block` from the very
        // first paint and its nested widgets build normally.
        if (this._isTabsLayout() && !this.activeRowKey && toAdd.length > 0) {
            this.activeRowKey = toAdd[0];
        }
        this.bodyNode.freeze();
        toAdd.forEach((rowKey) => this._addRow(rowKey));
        this.bodyNode.unfreeze();
        // After the batch unfreeze, re-assert the active classes on
        // chip + wrapper (the per-row `_addRow` calls during the freeze
        // applied the wrapper class via `_class`, but the chip class
        // depends on the chip already existing — and chips are appended
        // inside `_addRow` too, so this is mostly a safety net for the
        // chip side and a no-op for the wrapper side).
        if (this._isTabsLayout() && this.activeRowKey) {
            this._setActiveTabClasses(this.activeRowKey);
        }
    }

    _addRow(rowKey) {
        if (this.rows[rowKey]) return;
        if (!this.templateSource) {
            console.warn('[GG] _addRow before template ready', rowKey);
            return;
        }
        // Derive the wrapper insertion position from the Bag itself: put
        // the wrapper right before the wrapper of the next sibling row
        // that already exists in the DOM, or append at the tail. Works
        // for all sources of 'ins' (action handlers, DnD, external
        // setItem) without the caller having to know.
        let position;
        const bag = this.storebag();
        if (bag instanceof gnr.GnrBag) {
            const allKeys = bag.getNodes().map((n) => n.label);
            const idx = allKeys.indexOf(rowKey);
            for (let j = idx + 1; j < allKeys.length; j++) {
                if (this.rows[allKeys[j]]) {
                    position = '<_grow_' + allKeys[j];
                    break;
                }
            }
        }
        const wrapperLabel = '_grow_' + rowKey;
        const wrapperNodeId = '__grpgridrow__' + this.nodeId + '__' + rowKey;
        // Clone the template — every row owns its own copy. Auto-generated
        // nodeIds (those starting with `grpgrid_`, used by the framework
        // itself for action-topic routing of nested groupletGrids) get
        // namespaced so each row's clone has a unique container nodeId.
        // Author-supplied nodeIds are left untouched: it's the author's
        // responsibility to make them unique if they need to be referenced
        // (typically by including `rowKey` in the nodeId or just by
        // omitting nodeId on widgets that aren't referenced).
        const cloned = this.templateSource.deepCopy();
        this._namespaceFrameworkNodeIds(cloned, rowKey);
        const bodyContent = this.bodyNode.getValue();
        if (!(bodyContent instanceof gnr.GnrDomSource)) {
            console.warn('[GG] bodyNode has no GnrDomSource', bodyContent);
            return;
        }
        const that0 = this;
        const dragCode = this.dragCode;
        // In tabs mode pre-stamp `gg-tab-active` on the wrapper when
        // this row is the one being activated, so the wrapper is born
        // visible. See the matching comment in `_fullSync` — without
        // this, every wrapper would mount under `display:none` and
        // nested widgets inside the first-active panel would build in
        // a detached layout context.
        let wrapperClass = 'grouplet_grid_row';
        if (this._isTabsLayout() && this.activeRowKey === rowKey) {
            wrapperClass += ' gg-tab-active';
        }
        const wrapperKw = {
            datapath: '.' + rowKey,
            _class: wrapperClass,
            nodeId: wrapperNodeId,
            connect_onclick: function() { that0.selectRow(rowKey); }
        };
        // onCreated runs after the DOM is mounted — the right place to
        // attach the drag handle (no timing hack needed). The handle is
        // a leaf <div> with no widget logic, so we append plain HTML
        // directly and wire native HTML5 DnD listeners on the wrapper.
        if (dragCode) {
            wrapperKw.onCreated = function(domnode) {
                const wrapperDom = domnode.sourceNode
                    ? domnode.sourceNode.getDomNode()
                    : domnode;
                if (!wrapperDom) {
                    console.warn('[GG-dnd] onCreated: no wrapperDom');
                    return;
                }
                const handle = document.createElement('div');
                handle.className = 'grouplet_grid_row_drag';
                handle.setAttribute('draggable', 'true');
                handle.title = _T('!!Drag to reorder');
                handle.innerHTML =
                    '<span class="grouplet_grid_drag_icon">⠿</span>';
                wrapperDom.appendChild(handle);
                that0._wireRowDnD(wrapperDom, rowKey);
            };
        }
        const extraKw = position ? {_position: position} : undefined;
        bodyContent._('div', wrapperLabel, wrapperKw, extraKw);
        const wrapperNode = bodyContent.getNode(wrapperLabel);
        const wrapperContent = wrapperNode.getValue();
        const topic = this.actionTopic;
        // 2a) Top-right `×` delete button (Item 10 affordance).
        //     Enabled by `delitem=True`. Always sits on top of the kebab
        //     and the row content via CSS absolute positioning.
        if (this.delitem) {
            const delKw = objectUpdate({
                _class: 'grouplet_grid_row_delete',
                tip: _T('!!Delete row'),
                connect_onclick: "genro.publish('" + topic + "',"
                                + "{action:'delete',rowKey:'" + rowKey + "'});"
            }, this.delitemKw || {});
            // Author-provided extra _class is merged additively.
            if (this.delitemKw && this.delitemKw._class) {
                delKw._class = 'grouplet_grid_row_delete '
                             + this.delitemKw._class;
            }
            wrapperContent._('div', '_grow_del_' + rowKey, delKw);
            const delNode = wrapperContent.getNode('_grow_del_' + rowKey);
            delNode.getValue()._('div', 'glyph', {innerHTML: '×'});
        }
        // 2b) Per-row kebab menu — `<div>` target with a child `<menu>`.
        //     The Python side pre-resolves `editmenu` to a dict whose keys
        //     are entry identifiers ('addPrev', 'addNext', 'delete', ...
        //     or anything custom) and whose values are:
        //       True   → use the built-in preset for that key
        //       string → custom label, action derived from preset key
        //       dict   → full menuline spec (label, action, ...)
        //     An empty dict means "no kebab".
        // Reference: genro_components.js:497 (multivalue dlg) for the
        // inline `_('menu', {modifiers:'*', ...})` shape.
        const editmenu = this.editmenu;
        const hasEditmenu = editmenu && typeof editmenu === 'object'
                            && Object.keys(editmenu).length > 0;
        if (hasEditmenu) {
            // Preset entries: keyed by the same identifiers the Python
            // side emits ('addPrev', 'addNext', 'delete'). Each returns a
            // menuline-ready spec (label + action publishing on the
            // controller's action topic).
            const presets = {
                addPrev: {
                    label: _T('!!Add prev'),
                    action: "genro.publish('" + topic + "',"
                          + "{action:'add',position:'<" + rowKey + "'});"
                },
                addNext: {
                    label: _T('!!Add next'),
                    action: "genro.publish('" + topic + "',"
                          + "{action:'add',position:'>" + rowKey + "'});"
                },
                'delete': {
                    label: _T('!!Delete'),
                    action: "genro.publish('" + topic + "',"
                          + "{action:'delete',rowKey:'" + rowKey + "'});"
                }
            };
            const kebabId = '__grpgridrowmenu__' + this.nodeId + '__' + rowKey;
            const kebabKw = objectUpdate({
                _class: 'grouplet_grid_row_kebab',
                tip: _T('!!Row actions'),
                nodeId: kebabId
            }, this.editmenuKw || {});
            if (this.editmenuKw && this.editmenuKw._class) {
                kebabKw._class = 'grouplet_grid_row_kebab '
                               + this.editmenuKw._class;
            }
            wrapperContent._('div', '_grow_kebab_' + rowKey, kebabKw);
            const kebabNode = wrapperContent.getNode('_grow_kebab_' + rowKey);
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
                if (raw === false || raw === null || raw === undefined) {
                    return;
                }
                const preset = presets[entryKey] || null;
                let spec;
                if (raw === true) {
                    if (!preset) return;        // unknown key, no preset
                    spec = preset;
                } else if (typeof raw === 'string') {
                    spec = objectUpdate({}, preset || {});
                    spec.label = raw;
                } else if (typeof raw === 'object') {
                    spec = objectUpdate({}, preset || {});
                    objectUpdate(spec, raw);
                } else {
                    return;
                }
                if (!spec.label) return;
                menu._('menuline', spec);
            });
        }
        // freeze/unfreeze on the wrapperNode so the framework builds
        // the grafted subtree (template root children → row widgets)
        // atomically in one shot.
        wrapperNode.freeze();
        cloned.getNodes().forEach((n) => {
            this._graftNode(wrapperContent, n);
        });
        wrapperNode.unfreeze();
        this.rows[rowKey] = {wrapperNodeId: wrapperNodeId};
        // Drag handle: created LAST, on a wrapper that is already mounted
        // (no enclosing freeze). This is the pattern used in
        // timesheet_viewer.js:339-362 — `draggable:true` in the struct
        // attrs is reliably reflected as the HTML attribute when the
        // parent is live, which is what the browser's native HTML5
        // dragstart needs to fire. Then we wire native DnD listeners on
        // the wrapper for dragover preview line + drop dispatch.
        // Drag handle is appended via onCreated callback (set on
        // wrapperKw above). No post-unfreeze hook needed.
        this._updateAddBtnState();
        // Tabs mode: also build the corresponding tab chip. The
        // wrapper's `_class` was pre-stamped above when this row was
        // already known to be the active one (set by `_fullSync`
        // before the batch freeze). If the row was just added via the
        // `+` button (`_pendingActivate === rowKey`), switch the
        // active tab to it now — same UX as opening a new browser
        // tab. Otherwise, if the new row was inserted as the active
        // one at fullSync time, reassert the chip class.
        if (this._isTabsLayout()) {
            this._addTabChip(rowKey);
            const pending = this._pendingActivate === rowKey;
            if (pending) {
                this._pendingActivate = null;
                // Force switch even if another tab is currently active.
                this.activeRowKey = null;
                this._activateTab(rowKey);
            } else if (!this.activeRowKey) {
                this._activateTab(rowKey);
            } else if (this.activeRowKey === rowKey) {
                // The wrapper class was pre-stamped, but the chip was
                // just created — mark it active too.
                this._setActiveTabClasses(this.activeRowKey);
            }
        }
        // Consume pending flash (set by `_doMoveRow*` before mutating
        // the Bag): highlight a row that just landed via DnD.
        if (this._pendingFlash && this._pendingFlash[rowKey]) {
            delete this._pendingFlash[rowKey];
            this._flashRow(rowKey);
        }
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

    _removeRow(rowKey) {
        const entry = this.rows[rowKey];
        if (!entry) return;
        // Tear down DnD listeners before the DOM is destroyed.
        // In tabs mode the DnD handlers are on the chip (not the row
        // wrapper), so the wrapper-level unwire is a no-op there — the
        // chip teardown happens in `_removeTabChip` below. In cards
        // mode the chip teardown is also a no-op.
        if (this.dragCode) {
            this._unwireRowDnD(rowKey);
        }
        // Tabs mode: drop the chip + decide next active.
        if (this._isTabsLayout()) {
            // Pre-compute the next active tab BEFORE removing the chip.
            let nextActive = null;
            if (this.activeRowKey === rowKey) {
                const chipKeys = Object.keys(this._tabsByRow);
                const idx = chipKeys.indexOf(rowKey);
                if (idx > 0) {
                    nextActive = chipKeys[idx - 1];
                } else if (chipKeys.length > 1) {
                    nextActive = chipKeys[idx + 1];
                }
            }
            this._removeTabChip(rowKey);
            if (this.activeRowKey === rowKey) {
                this.activeRowKey = null;
                if (nextActive) this._activateTab(nextActive);
            }
        }
        const wrapperLabel = '_grow_' + rowKey;
        const bodySource = this.bodyNode.getValue('static');
        if (bodySource && typeof bodySource.popNode === 'function') {
            // Triggered popNode on the body's source Bag: framework
            // tears down the wrapper dijit and removes the DOM subtree.
            bodySource.popNode(wrapperLabel);
        } else {
            const liveNode = genro.nodeById(entry.wrapperNodeId);
            if (liveNode && typeof liveNode._destroy === 'function') {
                liveNode._destroy();
            }
        }
        delete this.rows[rowKey];
        this._updateAddBtnState();
    }

    _rowCount() {
        return Object.keys(this.rows).length;
    }

    // --- Public API: thin publishers on the action topic ---
    // Every public mutator goes through `genro.publish(this.actionTopic, ...)`.
    // The single subscription in _registerActionSubscription dispatches via
    // _handleAction → _doAddRow / _askAndDeleteRow. All entry points
    // (kebab menu, footer button, programmatic calls) follow the same path.

    addRowAction(defaults) {
        genro.publish(this.actionTopic,
                      {action: 'add', defaults: defaults || null});
    }

    insertRowAfter(rowKey, defaults) {
        genro.publish(this.actionTopic, {
            action: 'add',
            position: '>' + rowKey,
            defaults: defaults || null
        });
    }

    insertRowBefore(rowKey, defaults) {
        genro.publish(this.actionTopic, {
            action: 'add',
            position: '<' + rowKey,
            defaults: defaults || null
        });
    }

    deleteRowAction(rowKey) {
        genro.publish(this.actionTopic,
                      {action: 'delete', rowKey: rowKey});
    }

    // --- Private executors ---

    _doAddRow(position, defaults) {
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
        // `_addRow` fires (triggered by the Bag mutation below via
        // `gnr_storepath`). Picked up — and cleared — inside `_addRow`.
        if (this._isTabsLayout()) {
            this._pendingActivate = newKey;
        }
        const rowBag = new gnr.GnrBag();
        const merged = objectUpdate({}, this.defaultRow || {});
        objectUpdate(merged, defaults || {});
        Object.keys(merged).forEach(function(k) {
            rowBag.setItem(k, merged[k]);
        });
        if (position) {
            // `position` is a Bag _position spec: '<rowKey' (before) or
            // '>rowKey' (after). Falls back to '>' if no sign is given.
            const sign = (position.charAt(0) === '<'
                          || position.charAt(0) === '>')
                ? position.charAt(0) : '>';
            const targetKey = (position.charAt(0) === '<'
                               || position.charAt(0) === '>')
                ? position.substring(1) : position;
            dataBag.setItem(newKey, rowBag, null,
                            {_position: sign + targetKey});
        } else {
            dataBag.setItem(newKey, rowBag);
        }
    }

    _askAndDeleteRow(rowKey) {
        // Confirmation dialog before destroying the row. genro.dlg.ask
        // accepts a function in `actions` (funcCreate normalizes both
        // strings and functions — see th.js:20 for an in-codebase example).
        const that = this;
        genro.dlg.ask(
            _T('!!Delete this row?'),
            _T('!!This row will be removed. Continue?'),
            {confirm: _T('!!Delete'), cancel: _T('!!Cancel')},
            {confirm: function() { that._doDeleteRow(rowKey); }}
        );
    }

    _doDeleteRow(rowKey) {
        if (this._rowCount() <= this.minRows) return;
        const dataBag = this.storebag();
        if (dataBag instanceof gnr.GnrBag) {
            dataBag.popNode(rowKey);
        }
        if (this.selectedRowKey === rowKey) {
            this.selectedRowKey = null;
        }
    }

    selectRow(rowKey) {
        // In tabs/vtabs mode the active state is fully owned by
        // `_activateTab` (which manages `.gg-tab-active`) — the
        // `selected` CSS class is a cards-mode UX leftover that
        // visually conflicts with the panel chrome here.
        if (this._isTabsLayout()) return;
        if (this.selectedRowKey === rowKey) return;
        if (this.selectedRowKey) {
            const prev = this.rows[this.selectedRowKey];
            const prevDom = prev && genro.nodeById(prev.wrapperNodeId);
            if (prevDom && prevDom.getDomNode && prevDom.getDomNode()) {
                prevDom.getDomNode().classList.remove('selected');
            }
        }
        this.selectedRowKey = rowKey;
        const entry = this.rows[rowKey];
        const liveNode = entry && genro.nodeById(entry.wrapperNodeId);
        if (liveNode && liveNode.getDomNode && liveNode.getDomNode()) {
            liveNode.getDomNode().classList.add('selected');
        }
    }

    _updateAddBtnState() {
        if (!this.addBtnDom) return;
        const atMax = !!(this.maxRows
                         && this._rowCount() >= this.maxRows);
        this.addBtnDom.classList.toggle('disabled', atMax);
    }

    _namespaceFrameworkNodeIds(domSource, rowKey) {
        // Append `__<gridId>__<rowKey>` to nodeIds that the framework
        // generated for its own bookkeeping (groupletGrid containers
        // and their body / addbtn satellites). These nodeIds always
        // share the `grpgrid_` prefix (set server-side by gr_groupletGrid
        // when no explicit nodeId is passed). Author-supplied nodeIds
        // are NEVER touched — it's the author's job to make them unique
        // across rows if they actually use them.
        // Why we still need a nodeId at all on the container, instead
        // of fully attribute-driven lookups: the action topic is
        // `groupletGrid_<nodeId>_action` (publish-subscribe), so each
        // nested grid instance must subscribe to its own topic — hence
        // a unique nodeId per row.
        const suffix = '__' + this.nodeId + '__' + rowKey;
        const apply = function(n) {
            const a = n.attr;
            if (!a || !a.nodeId) return;
            if (typeof a.nodeId === 'string'
                && a.nodeId.indexOf('grpgrid_') === 0) {
                a.nodeId = a.nodeId + suffix;
            }
        };
        domSource.getNodes().forEach(function(n) {
            apply(n);
            const v = n.getValue();
            if (v instanceof gnr.GnrBag) {
                v.walk(apply, 'static');
            }
        });
    }

    _ensureTemplate(callback) {
        if (this.templateSource) {
            callback();
            return;
        }
        if (this.templateLoading) {
            this.templateLoading.push(callback);
            return;
        }
        const that = this;
        this.templateLoading = [callback];
        const params = {
            resource: this.resource,
            handler: this.handler,
            table: this.table,
            grouplets_root: this.grouplets_root,
            grouplet_kwargs: this.grouplet_kw
        };
        genro.serverCall('gr_getGroupletGridTemplate', params,
            function(tplBag, error) {
                if (error) {
                    console.error('[GG] template RPC failed', error);
                    that.templateLoading = null;
                    return;
                }
                that.templateSource = that._bagToDetachedSource(tplBag);
                const queue = that.templateLoading;
                that.templateLoading = null;
                queue.forEach(function(cb) { cb(); });
            });
    }

    _bagToDetachedSource(bag) {
        const root = genro.src.newRoot();
        if (!(bag instanceof gnr.GnrBag)) {
            console.warn('[GroupletGrid] template payload is not a Bag', bag);
            return root;
        }
        bag.getNodes().forEach(function(node) {
            root.setItem(node.label, node._value,
                         objectUpdate({}, node.attr || {}));
        });
        return root;
    }
};
