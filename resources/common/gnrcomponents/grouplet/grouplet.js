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
        this.bodyNode = genro.nodeById(kw.bodyNodeId);
        this.nodeId = kw.nodeId;
        if (typeof sourceNode.registerDynAttr === 'function') {
            sourceNode.registerDynAttr('storepath');
        }
        this.storepath = sourceNode.attr.storepath || null;
        this.valuepath = this.bodyNode
            ? this.bodyNode.absDatapath('.')
            : null;
        this.resource = kw.resource || null;
        this.handler = kw.handler || null;
        this.table = kw.table || null;
        this.grouplets_root = kw.grouplets_root;
        this.grouplet_kw = kw.grouplet_kw || {};
        this.cols = kw.cols || 1;
        this.minWidth = kw.min_width || null;
        this.gap = kw.gap || '12px';
        this.addEnabled = kw.addEnabled;
        this.removeEnabled = kw.removeEnabled;
        this.defaultRow = kw.defaultRow;
        this.minRows = kw.minRows || 0;
        this.maxRows = kw.maxRows || null;
        this.addBtnNodeId = kw.addBtnNodeId || null;
        // Drag-and-drop: when `dragCode` is non-null each row is rendered
        // with a drag handle (left side). `dragCode` is the data-transfer
        // key — only payloads with the same key are accepted as drop
        // sources, so two grids with different `dragCode` values are
        // isolated (default behavior: dragCode = nodeId, server-side).
        // Cross-grid sharing requires explicitly passing the same dragCode.
        this.dragCode = kw.dragCode || null;
        this._dragOverRow = null;
        this._dragHandlesByRow = {};
        this.templateSource = null;
        this.templateLoading = null;
        this.rows = {};
        this._destroyed = false;
        // Single per-instance topic: every action (add, delete, ...) goes
        // through here. Menu items, footer button, programmatic API all
        // publish on this topic; the controller dispatches via _handleAction.
        this.actionTopic = 'groupletGrid_' + this.nodeId + '_action';
        console.log('[GG] init', this.nodeId, 'valuepath=', this.valuepath,
                    'cols=', this.cols, 'min_width=', this.minWidth);
        this._applyResponsiveLayout();
        this._applySlotClasses();
        this._registerTriggers();
        this._registerActionSubscription();
        const that = this;
        dojo.connect(sourceNode, '_onDeleting', function() { that.destroy(); });
        const initialBag = this.valuepath
            ? genro.getData(this.valuepath)
            : null;
        if (initialBag instanceof gnr.GnrBag) {
            this._onDataChange({evt: 'init', _synthetic: true});
        }
        this._updateAddBtnState();
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

    _registerTriggers() {
        if (!this.bodyNode) {
            console.warn('[GroupletGrid] cannot register triggers: bodyNode is null');
            return;
        }
        this.bodyNode.registerSubscription(
            '_trigger_data', this,
            (kw) => this._onDataChange(kw),
            'groupletGrid_' + this.nodeId);
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
            const handle = e.target.closest
                ? e.target.closest('.grouplet_grid_row_drag') : null;
            if (!handle) return;
            try {
                e.dataTransfer.setData(dataKey, JSON.stringify({
                    rowKey: rowKey, nodeId: that.nodeId
                }));
                // Some browsers also need a generic text payload to start.
                e.dataTransfer.setData('text/plain', rowKey);
                e.dataTransfer.effectAllowed = 'move';
            } catch (err) { /* IE/Safari quirks */ }
            // Drag image = snapshot of the whole row wrapper, not just
            // the handle. Pattern from genro_grid.js:2199-2211: clone the
            // node into the global '#auxDragImage' container, point the
            // browser's setDragImage at it, then remove on next tick
            // (the snapshot is captured synchronously).
            try {
                const auxDragImage = document.getElementById('auxDragImage');
                if (auxDragImage) {
                    const clone = wrapperDom.cloneNode(true);
                    clone.classList.remove('gg-dragging', 'gg-drop-target',
                        'gg-drop-target-invalid', 'gg-just-dropped');
                    // Match the original width so the preview is sized
                    // correctly even though the clone is in a detached
                    // off-screen container.
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
            if (!payload || payload.nodeId !== that.nodeId) return;
            if (payload.rowKey === rowKey) return;
            // Drop on a row N → dragged row becomes the new N (target
            // shifts to N+1). "Append at end" is not reachable via D&D —
            // use the footer "+ Add row" or the kebab menu for that.
            genro.publish(that.actionTopic, {
                action: 'move',
                rowKey: payload.rowKey,
                position: '<' + rowKey
            });
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
        // Reorder a row inside the data Bag (and the body source Bag).
        // `position` is '<targetKey' or '>targetKey'. Implementation:
        // remove the row from both Bags, then re-insert at the requested
        // position with the original data.
        const dataBag = this.valuepath ? genro.getData(this.valuepath) : null;
        if (!(dataBag instanceof gnr.GnrBag)) {
            console.warn('[GG] _doMoveRow: no Bag at', this.valuepath);
            return;
        }
        const node = dataBag.getNode(rowKey);
        if (!node) {
            console.warn('[GG] _doMoveRow: row not found', rowKey);
            return;
        }
        // Snapshot the row data + attrs so the reinsertion is a faithful
        // copy. The row Bag is moved by reference, so attrs survive.
        const rowValue = node.getValue();
        const rowAttrs = node.getAttr() || {};
        // 1) data Bag: pop + re-set with _position. This keeps the row's
        // sub-Bag identity (and any subscribers wired against it).
        dataBag.popNode(rowKey);
        dataBag.setItem(rowKey, rowValue, rowAttrs, {_position: position});
        // 2) body source Bag: same dance for the wrapper. _removeRow +
        // _addRow rebuilds the wrapper at the right position. The wrapper
        // label is `_grow_<rowKey>`; the position must be translated.
        const targetKey = position.substring(1);
        const sign = position.charAt(0);
        this._removeRow(rowKey);
        this._addRow(rowKey, sign + '_grow_' + targetKey);
        // Just-dropped flash: the new row inherits the drop-target tint
        // for ~260ms then transitions back to normal. The CSS handles
        // the fade-out via `transition` on background/border, so JS only
        // needs to add the class and remove it later.
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
        if (this.bodyNode) {
            this.bodyNode.unregisterSubscription(
                'groupletGrid_' + this.nodeId);
        }
        if (this.sourceNode) {
            this.sourceNode.unregisterSubscription(this.actionTopic);
        }
        Object.keys(this.rows).forEach((rowKey) => this._removeRow(rowKey));
        this.templateSource = null;
        this.templateLoading = null;
    }

    _onDataChange(kw) {
        let reason;
        if (kw && kw._synthetic) {
            reason = 'init';
        } else {
            const absPath = this.valuepath || this.bodyNode.absDatapath('.');
            reason = this.bodyNode.getTriggerReason(absPath, kw);
            if (!reason) return;
        }
        const that = this;
        this._ensureTemplate(function() {
            if (reason === 'init' || reason === 'node' || reason === 'value') {
                that._fullSync();
            } else if (reason === 'child') {
                that._handleChildChange(kw);
            }
        });
    }

    _fullSync() {
        const bag = this.valuepath ? genro.getData(this.valuepath) : null;
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
        this.bodyNode.freeze();
        toAdd.forEach((rowKey) => this._addRow(rowKey));
        this.bodyNode.unfreeze();
    }

    _handleChildChange(kw) {
        const evt = kw && kw.evt;
        const node = kw && kw.node;
        if (!node || !node.label) return;
        if (evt === 'ins') {
            this._addRow(node.label);
        } else if (evt === 'del') {
            this._removeRow(node.label);
        }
    }

    _addRow(rowKey, position) {
        if (this.rows[rowKey]) return;
        if (!this.templateSource) {
            console.warn('[GG] _addRow before template ready', rowKey);
            return;
        }
        const wrapperLabel = '_grow_' + rowKey;
        const wrapperNodeId = '__grpgridrow__' + this.nodeId + '__' + rowKey;
        const cloned = this.templateSource.deepCopy();
        this._namespaceNodeIds(cloned, rowKey);
        const bodyContent = this.bodyNode.getValue();
        if (!(bodyContent instanceof gnr.GnrDomSource)) {
            console.warn('[GG] bodyNode has no GnrDomSource', bodyContent);
            return;
        }
        // 1) Aggiungo il wrapper (blocchetto card) come figlio del bodyNode.
        //    Layout interno della riga: 2 colonne via CSS-grid → contenuto +
        //    kebab laterale (gestito interamente dal CSS).
        //    `position` (es. '>_grow_r_002') colloca il wrapper subito dopo
        //    il sibling indicato; senza, append in coda.
        const that0 = this;
        const dragCode = this.dragCode;
        const wrapperKw = {
            datapath: '.' + rowKey,
            _class: 'grouplet_grid_row',
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
                console.log('[GG-dnd] handle appended (onCreated)',
                    'rowKey=', rowKey,
                    'draggable=', handle.getAttribute('draggable'));
                that0._wireRowDnD(wrapperDom, rowKey);
            };
        }
        const extraKw = position ? {_position: position} : undefined;
        bodyContent._('div', wrapperLabel, wrapperKw, extraKw);
        const wrapperNode = bodyContent.getNode(wrapperLabel);
        const wrapperContent = wrapperNode.getValue();
        // 2) Per-row kebab menu — `<div>` target with a child `<menu>`.
        //    Pattern: `gnr.widgets.Menu` (genro_widgets.js Menu widget) with
        //    `connectToParent:true` (default) auto-binds the menu to its
        //    parent DOM node via `bindDomNode`. `modifiers:'*'` opens the
        //    menu on plain left-click (instead of right-click only).
        //    Items: "Insert below" + "Delete row" via menuline children.
        //    Reference: genro_components.js:497 (multivalue dlg) for the
        //    inline `_('menu', {modifiers:'*', ...})` shape.
        const showInsert = !!this.addEnabled;
        const showRemove = !!this.removeEnabled;
        if (showInsert || showRemove) {
            const kebabId = '__grpgridrowmenu__' + this.nodeId + '__' + rowKey;
            wrapperContent._('div', '_grow_kebab_' + rowKey, {
                _class: 'grouplet_grid_row_kebab',
                tip: _T('!!Row actions'),
                nodeId: kebabId
            });
            const kebabNode = wrapperContent.getNode('_grow_kebab_' + rowKey);
            const kebabContent = kebabNode.getValue();
            // Inner glyph (three dots) — plain unicode character so it
            // inherits font + color from the theme.
            kebabContent._('div', 'glyph', {
                _class: 'grouplet_grid_kebab_icon',
                innerHTML: '⋮'
            });
            // Menu as child of the kebab — auto-binds to kebab DOM node.
            // Items publish on the controller's action topic; the
            // controller dispatches via _handleAction.
            const menu = kebabContent._('menu', {
                modifiers: '*',
                _class: 'smallmenu grouplet_grid_row_menu'
            });
            const topic = this.actionTopic;
            if (showInsert) {
                menu._('menuline', {
                    label: _T('!!Add prev'),
                    action: "genro.publish('" + topic + "',"
                          + "{action:'add',position:'<" + rowKey + "'});"
                });
                menu._('menuline', {
                    label: _T('!!Add next'),
                    action: "genro.publish('" + topic + "',"
                          + "{action:'add',position:'>" + rowKey + "'});"
                });
            }
            if (showRemove) {
                menu._('menuline', {
                    label: _T('!!Delete'),
                    action: "genro.publish('" + topic + "',"
                          + "{action:'delete',rowKey:'" + rowKey + "'});"
                });
            }
        }
        // 3) Freeze → graft dello stampino (i children top-level del template
        //    clonato) → unfreeze. Il framework costruisce atomicamente
        //    tutta la subtree con label/widget completi. Il content del
        //    grouplet finisce nella prima colonna del CSS-grid della riga.
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
        if (this.dragCode) {
            this._unwireRowDnD(rowKey);
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
        // Append (no `position`) or insert at `position` (e.g. '>r_002').
        // Mutates the data Bag, then the body source Bag at the matching
        // position so the DOM lands where the data sits.
        if (this.maxRows && this._rowCount() >= this.maxRows) return;
        const dataBag = this.valuepath ? genro.getData(this.valuepath) : null;
        if (!(dataBag instanceof gnr.GnrBag)) {
            console.warn('[GG] _doAddRow: no Bag at', this.valuepath);
            return;
        }
        const newKey = 'r_' + genro.time36Id();
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
            this._addRow(newKey, sign + '_grow_' + targetKey);
        } else {
            dataBag.setItem(newKey, rowBag);
            this._addRow(newKey);
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
        const dataBag = this.valuepath ? genro.getData(this.valuepath) : null;
        if (dataBag instanceof gnr.GnrBag) {
            dataBag.popNode(rowKey);
        }
        this._removeRow(rowKey);
        if (this.selectedRowKey === rowKey) {
            this.selectedRowKey = null;
        }
    }

    selectRow(rowKey) {
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
        if (!this.addBtnNodeId) return;
        const node = genro.nodeById(this.addBtnNodeId);
        if (!node || !node.domNode) return;
        const atMax = !!(this.maxRows
                         && this._rowCount() >= this.maxRows);
        node.domNode.classList.toggle('disabled', atMax);
    }

    _namespaceNodeIds(domSource, rowKey) {
        const suffix = '__' + this.nodeId + '__' + rowKey;
        const apply = function(n) {
            if (n.attr && n.attr.nodeId) {
                n.attr.nodeId = n.attr.nodeId + suffix;
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
