dojo.declare('gnr.RecordPickerSelection', null, {
    constructor: function(multiple, maximum) {
        this.multiple = multiple;
        this.maximum = multiple ? maximum : 1;
        this.keys = [];
    },
    setValue: function(value) {
        var keys = value === null || value === undefined || value === '' ? [] :
            (Array.isArray(value) ? value : (this.multiple ? String(value).split(',') : [value]));
        this.keys = Array.from(new Set(keys.map(String)));
        if (!this.multiple) { this.keys = this.keys.slice(0, 1); }
    },
    toggle: function(key, checked) {
        key = String(key);
        if (!checked) {
            this.keys = this.keys.filter(function(k) { return k !== key; });
        } else if (!this.keys.includes(key)) {
            if (!this.multiple) { this.keys = [key]; }
            else if (!this.maximum || this.keys.length < this.maximum) { this.keys.push(key); }
        }
    },
    value: function() { return this.multiple ? this.keys.join(',') : (this.keys[0] || null); }
});

dojo.declare('gnr.RecordPicker', null, {
    constructor: function(sourceNode, domNode) {
        this.sourceNode = sourceNode;
        this.domNode = domNode;
        this.config = sourceNode.attr.picker_config;
        this.selection = new gnr.RecordPickerSelection(this.config.multiSelect, this.config.maxSelect);
        this.records = new Map();
        this.localKeys = [];
        this.candidates = [];
        this.query = '';
        this.revision = 0;
        this.generation = 0;
        this.ready = false;
        this.loading = false;
        this.hydrating = false;
        this.build();
        dojo.connect(sourceNode, '_onDeleting', this, 'destroy');
    },
    element: function(tag, className, text, parent) {
        var node = document.createElement(tag);
        if (className) { node.className = className; }
        if (text !== undefined) { node.textContent = text; }
        if (parent) { parent.appendChild(node); }
        return node;
    },
    button: function(text, parent, handler, className) {
        var button = this.element('button', className || '', text, parent);
        button.type = 'button';
        button.addEventListener('click', handler);
        return button;
    },
    build: function() {
        var that = this;
        this.domNode.classList.add('record_picker_' + this.config.layout);
        this.domNode.classList.toggle('record_picker_with_preview', !!this.config.preview);
        if (this.config.boxHeight) {
            this.domNode.classList.add('record_picker_fixed');
            this.domNode.style.setProperty('--record-picker-box-height',
                typeof this.config.boxHeight === 'number' ? this.config.boxHeight + 'px' : this.config.boxHeight);
        }
        if (this.config.cols) {
            this.domNode.classList.add('record_picker_columns');
            this.domNode.style.setProperty('--record-picker-columns', this.config.cols);
        }
        var search = this.element('label', 'rp_search', _T('!!Search'), this.domNode);
        this.input = this.element('input', '', undefined, search);
        this.input.type = 'search';
        this.input.placeholder = _T('!!Type to find candidates');
        this.input.addEventListener('input', function() {
            that.query = this.value;
            that.revision++;
            clearTimeout(that.timer);
            if (that.config.table && that.query.trim()) {
                that.loading = true;
                that.candidates = [];
                that.render();
                that.timer = setTimeout(function() { that.search(); }, that.config.delay);
            } else { that.search(); }
        });
        var viewport = this.element('div', 'rp_viewport', undefined, this.domNode);
        this.status = this.element('div', 'rp_status', '', viewport);
        this.status.setAttribute('role', 'status');
        this.retry = this.button(_T('!!Retry'), viewport, function() { that.reload(); }, 'rp_retry');
        this.body = this.element('div', 'rp_body', undefined, viewport);
        this.list = this.element('div', 'rp_candidates', undefined, this.body);
        this.list.setAttribute('role', 'group');
        this.list.setAttribute('aria-label', _T('!!Candidates'));
        if (this.config.preview) {
            this.preview = this.element('div', 'rp_preview selectable', undefined, this.body);
            this.preview.setAttribute('role', 'region');
            this.preview.setAttribute('aria-label', _T('!!Record preview'));
        }
        var footer = this.footer = this.element('div', 'rp_footer', undefined, viewport);
        this.summary = this.element('div', 'rp_summary', undefined, footer);
        this.chips = this.element('div', 'rp_chips', undefined, footer);
        var actions = this.element('div', 'rp_actions', undefined, footer);
        if (this.config.multiSelect) {
            this.selectShown = this.button(_T('!!Select displayed candidates'), actions, function() {
                that.candidates.forEach(function(key) {
                    if (that.available(key)) { that.selection.toggle(key, true); }
                });
                that.peek = that.selection.keys.slice(-1)[0];
                that.writeSelection();
                that.render();
            });
        }
        this.render();
    },
    setDisabled: function(disabled) { this.disabled = !!disabled; this.render(); },
    setValue: function(value) {
        var previous = this.selection.value();
        this.selection.setValue(value);
        if (previous !== this.selection.value()) {
            this.peek = this.selection.keys.slice(-1)[0];
            if (this.ready) { this.hydrate(); }
            this.writeOutputs();
        }
        this.render();
    },
    setQuery: function(params) {
        this.queryParams = params;
        this.ready = true;
        this.reload();
    },
    rows: function(bag) {
        var that = this, rows = [];
        if (!bag) { return rows; }
        bag.getNodes().forEach(function(node) {
            var value = node.getValue();
            var row = objectUpdate({}, node.attr);
            if (value instanceof gnr.GnrBag) { objectUpdate(row, value.asDict()); }
            var key = row[that.config.table ? '_pkey' : that.config.identifier];
            if (key !== null && key !== undefined) { rows.push([String(key), row]); }
        });
        return rows;
    },
    setStore: function(store) {
        this.records = new Map(this.rows(store));
        this.localKeys = Array.from(this.records.keys());
        this.ready = true;
        this.search();
        this.writeOutputs();
    },
    request: function(params, success, failure) {
        var config = this.config;
        var kwargs = objectUpdate({dbtable:config.table, columns:config.columns,
            auxColumns:config.auxColumns, hiddenColumns:config.hiddenColumns || config.columns,
            rowcaption:config.rowcaption, notnull:true, weakCondition:false,
            limit:config.limit + 1, _sourceNode:this.sourceNode}, this.queryParams);
        objectUpdate(kwargs, params);
        var settled = false;
        var deferred = genro.rpc.remoteCall('app.dbSelect', kwargs, 'bag', 'POST', null, function(result, error) {
            settled = true;
            if (result instanceof gnr.GnrBagNode) { result = result.getValue(); }
            if (error || !(result instanceof gnr.GnrBag)) { failure(); }
            else { success(result); }
        });
        deferred.addErrback(function(error) {
            if (!settled) { failure(); }
            return error;
        });
    },
    reload: function() {
        if (!this.ready) { return; }
        clearTimeout(this.timer);
        this.revision++;
        this.generation++;
        this.error = false;
        if (this.config.table) {
            this.records.clear();
            this.candidates = [];
            this.hydrate();
        }
        this.search();
    },
    hydrate: function() {
        if (!this.config.table) { return; }
        var that = this, generation = this.generation;
        var revision = this.hydrationRevision = (this.hydrationRevision || 0) + 1;
        var keys = this.selection.keys.filter(function(key) { return !that.records.has(key); });
        this.hydrating = !!keys.length;
        if (!keys.length) { return; }
        var condition = (this.queryParams || {}).condition;
        this.request({_querystring:'*', limit:keys.length,
            condition:(condition ? '(' + condition + ') AND ' : '') + '$pkey IN :_picker_keys',
            _picker_keys:keys}, function(bag) {
            if (that.destroyed || generation !== that.generation || revision !== that.hydrationRevision) { return; }
            that.rows(bag).forEach(function(pair) { that.records.set(pair[0], pair[1]); });
            that.hydrating = false; that.writeOutputs(); that.render();
        }, function() {
            if (that.destroyed || generation !== that.generation || revision !== that.hydrationRevision) { return; }
            that.hydrating = false; that.error = true; that.render();
        });
    },
    search: function() {
        if (!this.ready) { return; }
        var that = this, query = this.query.trim(), revision = ++this.revision;
        this.error = false;
        if (!query) {
            this.candidates = [];
            this.more = false;
            this.loading = false;
            this.render();
            return;
        }
        if (!this.config.table) {
            var tokens = this.normalize(query).split(/\s+/).filter(Boolean);
            var matches = this.localKeys.filter(function(key) {
                var row = that.records.get(key);
                var fields = (that.config.columns || that.config.captionField).split(',');
                var text = that.normalize(fields.map(function(field) { return row[field.trim().replace(/^\$/, '')] || ''; }).join(' '));
                return tokens.every(function(token) { return text.includes(token); });
            });
            this.candidates = matches;
            this.more = false;
            this.loading = false;
            this.render();
            return;
        }
        this.loading = true;
        this.renderStatus();
        this.request({_querystring:query}, function(bag) {
            if (that.destroyed || revision !== that.revision) { return; }
            var rows = that.rows(bag);
            that.more = rows.length > that.config.limit;
            var keys = rows.slice(0, that.config.limit).map(function(pair) {
                that.records.set(pair[0], pair[1]); return pair[0];
            });
            that.candidates = keys;
            var keep = new Set(that.candidates.concat(that.selection.keys));
            that.records.forEach(function(row, key) { if (!keep.has(key)) { that.records.delete(key); } });
            that.loading = false;
            that.render();
        }, function() {
            if (that.destroyed || revision !== that.revision) { return; }
            that.loading = false; that.error = true; that.render();
        });
    },
    normalize: function(value) { return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); },
    available: function(key) {
        var row = this.records.get(key);
        return row && !row._is_invalid_item;
    },
    caption: function(key) {
        var row = this.records.get(key);
        return row ? String(row[this.config.captionField] || key) : key;
    },
    template: function(node, row, template, key) {
        if (template) { node.innerHTML = dataTemplate(template, new gnr.GnrBag(row)); }
        else { node.textContent = this.caption(key); }
    },
    renderStatus: function() {
        var message = this.error ? _T('!!Unable to load candidates. Retry the search.') :
            this.loading || this.hydrating ? _T('!!Loading candidates…') :
            this.candidates.length ? _T('!!Results') + ': ' + this.candidates.length : '';
        if (!this.loading && !this.error && this.more) { message += ' · ' + _T('!!More matches available; refine your search'); }
        this.status.textContent = message;
        this.status.hidden = !message;
        this.retry.hidden = !this.error;
        this.list.setAttribute('aria-busy', this.loading ? 'true' : 'false');
    },
    select: function(key, checked) {
        if (this.disabled || (checked && !this.available(key))) { return; }
        this.selection.toggle(key, checked);
        if (checked && this.selection.keys.includes(key)) { this.peek = key; }
        else if (!this.selection.keys.includes(this.peek)) { this.peek = this.selection.keys.slice(-1)[0]; }
        this.writeSelection();
        this.render();
    },
    render: function() {
        var that = this, active = document.activeElement;
        var focused = this.domNode.contains(active) && active.dataset.focus;
        this.input.disabled = this.disabled;
        this.list.replaceChildren();
        var empty = !this.candidates.length && !this.loading && !this.error && (this.config.boxHeight || this.query.trim());
        this.list.classList.toggle('rp_empty', !!empty);
        if (empty) { this.element('div', 'rp_empty_message', _T(this.config.emptyMessage, true), this.list); }
        this.candidates.forEach(function(key, index) {
            var row = that.records.get(key), selected = that.selection.keys.includes(key);
            var item = that.element('div', 'rp_candidate' + (selected ? ' rp_selected' : ''), undefined, that.list);
            var label, input;
            if (that.config.multiSelect || that.config.showRadio) {
                label = that.element('label', 'rp_choice', undefined, item);
                input = that.element('input', '', undefined, label);
                input.type = that.config.multiSelect ? 'checkbox' : 'radio';
                input.name = that.sourceNode.attr.nodeId + '_choice';
                input.checked = selected;
                input.addEventListener('change', function() { that.select(key, this.checked); });
            } else {
                label = input = that.button('', item, function() { that.select(key, true); }, 'rp_choice');
                input.setAttribute('aria-pressed', selected ? 'true' : 'false');
            }
            input.dataset.focus = 'choice:' + key;
            input.setAttribute('aria-label', that.caption(key));
            input.disabled = that.disabled || !that.available(key) || (that.config.multiSelect && !selected &&
                that.selection.maximum && that.selection.keys.length >= that.selection.maximum);
            item.classList.toggle('rp_disabled', !!input.disabled);
            var content = that.element('div', 'rp_content', undefined, label);
            content.id = that.sourceNode.attr.nodeId + '_candidate_' + index;
            input.setAttribute('aria-describedby', content.id);
            that.template(content, row, that.config.template, key);
        });
        var showSelected = this.config.showSelected && this.selection.keys.length;
        this.footer.hidden = !showSelected && (!this.config.multiSelect || !this.candidates.length);
        this.footer.classList.toggle('rp_with_selection', !!showSelected);
        this.summary.hidden = !showSelected;
        this.chips.hidden = !showSelected;
        this.summary.textContent = _T('!!Selected') + ': ' + this.selection.keys.length +
            (this.config.maxSelect ? ' / ' + this.config.maxSelect : '');
        this.chips.replaceChildren();
        this.selection.keys.forEach(function(key) {
            var text = that.caption(key) + (that.available(key) ? '' : ' · ' + _T('!!Unavailable'));
            var chip = that.button(text + ' ×', that.chips, function() {
                that.select(key, false); that.input.focus();
            }, 'rp_chip');
            chip.disabled = that.disabled;
            chip.setAttribute('aria-label', _T('!!Remove') + ' ' + text);
        });
        if (this.selectShown) { this.selectShown.disabled = this.disabled || this.loading || !this.candidates.length; }
        this.renderPreview();
        this.renderStatus();
        if (focused) {
            Array.from(this.list.querySelectorAll('[data-focus]')).some(function(node) {
                if (node.dataset.focus === focused) { node.focus(); return true; }
                return false;
            });
        }
    },
    renderPreview: function() {
        if (!this.preview) { return; }
        var key = this.peek, row = this.records.get(key);
        this.preview.replaceChildren();
        this.preview.classList.toggle('rp_preview_empty', !row);
        if (!row) {
            this.element('div', 'rp_empty_message', _T('!!Select an item to preview'), this.preview);
            return;
        }
        this.element('div', 'rp_preview_title', this.caption(key), this.preview);
        var content = this.element('div', 'rp_preview_content', undefined, this.preview);
        this.template(content, row, this.config.previewTemplate || this.config.template, key);
    },
    writeOutputs: function() {
        if (!this.config.selectedRecord && !this.config.selectedCaption) { return; }
        var that = this, records = new gnr.GnrBag();
        this.selection.keys.forEach(function(key, index) {
            var row = that.records.get(key);
            if (row) { records.setItem('r_' + index, new gnr.GnrBag(row), {_pkey:key}); }
        });
        var captions = this.selection.keys.map(function(key) { return that.caption(key); }).join(', ');
        var selected = this.config.multiSelect ? records : (records.getItem('#0') || null);
        if (this.config.selectedRecord) { this.sourceNode.setRelativeData(this.config.selectedRecord.replace(/^[\^=]/, ''), selected); }
        if (this.config.selectedCaption) { this.sourceNode.setRelativeData(this.config.selectedCaption.replace(/^[\^=]/, ''), captions); }
    },
    writeSelection: function() {
        this.writeOutputs();
        this.sourceNode.setRelativeData(this.config.checkedId.slice(1), this.selection.value());
    },
    destroy: function() {
        clearTimeout(this.timer);
        this.destroyed = true;
        this.revision++; this.generation++;
    }
});
