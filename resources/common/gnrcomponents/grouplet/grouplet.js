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
        this.gridId = kw.gridId;
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
        this.emptyNodeId = kw.emptyNodeId || null;
        this.addBtnNodeId = kw.addBtnNodeId || null;
        this.templateSource = null;
        this.templateLoading = null;
        this.rows = {};
        this._destroyed = false;
        console.log('[GG] init', this.gridId, 'valuepath=', this.valuepath,
                    'cols=', this.cols, 'min_width=', this.minWidth);
        this._applyResponsiveLayout();
        this._registerTriggers();
        const that = this;
        dojo.connect(sourceNode, '_onDeleting', function() { that.destroy(); });
        const initialBag = this.valuepath
            ? genro.getData(this.valuepath)
            : null;
        if (initialBag instanceof gnr.GnrBag) {
            this._onDataChange({evt: 'init', _synthetic: true});
        }
        this._updateEmptyState();
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

    _registerTriggers() {
        if (!this.bodyNode) {
            console.warn('[GroupletGrid] cannot register triggers: bodyNode is null');
            return;
        }
        this.bodyNode.registerSubscription(
            '_trigger_data', this,
            (kw) => this._onDataChange(kw),
            'groupletGrid_' + this.gridId);
    }

    destroy() {
        if (this._destroyed) return;
        this._destroyed = true;
        if (this.bodyNode) {
            this.bodyNode.unregisterSubscription(
                'groupletGrid_' + this.gridId);
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

    _addRow(rowKey) {
        if (this.rows[rowKey]) return;
        if (!this.templateSource) {
            console.warn('[GG] _addRow before template ready', rowKey);
            return;
        }
        const wrapperLabel = '_grow_' + rowKey;
        const wrapperNodeId = '__grpgridrow__' + this.gridId + '__' + rowKey;
        const cloned = this.templateSource.deepCopy();
        this._namespaceNodeIds(cloned, rowKey);
        const bodyContent = this.bodyNode.getValue();
        if (!(bodyContent instanceof gnr.GnrDomSource)) {
            console.warn('[GG] bodyNode has no GnrDomSource', bodyContent);
            return;
        }
        // 1) Aggiungo il wrapper (blocchetto card) come figlio del bodyNode.
        const that0 = this;
        bodyContent._('div', wrapperLabel, {
            datapath: '.' + rowKey,
            _class: 'grouplet_grid_row',
            nodeId: wrapperNodeId,
            connect_onclick: function() { that0.selectRow(rowKey); }
        });
        const wrapperNode = bodyContent.getNode(wrapperLabel);
        const wrapperContent = wrapperNode.getValue();
        if (this.removeEnabled) {
            const that = this;
            wrapperContent._('div', '_grow_del_' + rowKey, {
                _class: 'grouplet_grid_remove_btn',
                nodeId: '__grpgridrowdel__' + this.gridId + '__' + rowKey,
                tip: '!!Remove row',
                connect_onclick: function() { that.deleteRowAction(rowKey); }
            });
        }
        // 2) Freeze → graft dello stampino (i children top-level del template
        //    clonato) → unfreeze. Il framework costruisce atomicamente
        //    tutta la subtree con label/widget completi.
        wrapperNode.freeze();
        cloned.getNodes().forEach((n) => {
            this._graftNode(wrapperContent, n);
        });
        wrapperNode.unfreeze();
        this.rows[rowKey] = {wrapperNodeId: wrapperNodeId};
        this._updateEmptyState();
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
        this._updateEmptyState();
        this._updateAddBtnState();
    }

    _rowCount() {
        return Object.keys(this.rows).length;
    }

    addRowAction(defaults) {
        if (this.maxRows && this._rowCount() >= this.maxRows) return;
        const dataBag = this.valuepath ? genro.getData(this.valuepath) : null;
        if (!(dataBag instanceof gnr.GnrBag)) {
            console.warn('[GG] addRow: no Bag at', this.valuepath);
            return;
        }
        const newKey = 'r_' + genro.time36Id();
        // 1) Bag dei dati: aggiungi la sub-bag della riga con i defaultRow
        const rowBag = new gnr.GnrBag();
        const merged = objectUpdate({}, this.defaultRow || {});
        objectUpdate(merged, defaults || {});
        Object.keys(merged).forEach(function(k) {
            rowBag.setItem(k, merged[k]);
        });
        dataBag.setItem(newKey, rowBag);
        // 2) Bag src del bodyNode: aggiungi il wrapper, framework costruisce il DOM
        this._addRow(newKey);
    }

    deleteRowAction(rowKey) {
        if (this._rowCount() <= this.minRows) return;
        // 1) Bag dei dati: rimuovi la sub-bag della riga
        const dataBag = this.valuepath ? genro.getData(this.valuepath) : null;
        if (dataBag instanceof gnr.GnrBag) {
            dataBag.popNode(rowKey);
        }
        // 2) Bag src del bodyNode: rimuovi il wrapper, framework distrugge il DOM
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

    _updateEmptyState() {
        if (!this.emptyNodeId) return;
        const node = genro.nodeById(this.emptyNodeId);
        if (!node || !node.domNode) return;
        const isEmpty = (this._rowCount() === 0);
        node.domNode.style.display = isEmpty ? '' : 'none';
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
        const suffix = '__' + this.gridId + '__' + rowKey;
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
