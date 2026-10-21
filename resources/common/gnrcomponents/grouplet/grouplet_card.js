// A card: a grouplet bound to a datapath with its chrome band along one
// side — chevron, title and doc first, then kebab and checkbox — the band
// being the drag source. Used alone (groupletCard) and by groupletGrid for
// each card when chromeSide is set. The host owns the state (collapsed,
// checked, menu): the card draws it and reports the user's actions.

gnr.GroupletCard = class GroupletCard {

    // kw: {tools, rootDom: () => dom,
    //      collapse: {isCollapsed, toggle, expand}, collapsedClasses,
    //      title: (dom) => void, doc: {html: (cb) => void},
    //      checkbox: {isChecked, onClick(e), onKeydown(e)},
    //      drag: {start(e), end()}}
    constructor(kw) {
        this.tools = gnr.GroupletCard.parseTools(kw.tools);
        this.rootDom = kw.rootDom || (() => null);
        this.collapse = kw.collapse || null;
        this.collapsedClasses = kw.collapsedClasses || ['grouplet_card--collapsed'];
        this.title = kw.title || null;
        this.doc = kw.doc || null;
        this.checkbox = kw.checkbox || null;
        this.drag = kw.drag || null;
        this.bandContent = null;
        this.titleDom = null;
        this.checkDom = null;
        this.chevronDom = null;
        this._collapseAnim = null;
        this._listeners = [];
        this._invalidObserver = null;
        // set by a host whose form reports an error the DOM may not show
        this.formError = false;
    }

    static parseTools(tools) {
        // null: every tool that applies; else the ones named
        if (tools === null || tools === undefined || tools === true) return null;
        const names = Array.isArray(tools) ? tools : String(tools || '').split(',');
        return new Set(names.map((t) => t.trim()).filter(Boolean));
    }

    has(tool) {
        return !this.tools || this.tools.has(tool);
    }

    mount(content, label, fill) {
        // the band is filled detached and inserted at once: a live card is
        // not rebuilt around it
        const card = this;
        const bandContent = new gnr.GnrDomSource();
        bandContent._('div', '_spacer', {_class: 'grouplet_card_spacer'});
        if (fill) fill(bandContent);
        content._('div', label, {
            _class: 'grouplet_card_band',
            content: bandContent,
            onCreated: function(domnode) {
                const bandDom = domnode.sourceNode ? domnode.sourceNode.getDomNode() : domnode;
                if (bandDom) card.wireBand(bandDom);
            }
        });
        this.bandContent = content.getNode(label).getValue();
        return this.bandContent;
    }

    wireBand(bandDom) {
        // plain DOM in the framework band: the CSS order lays them out
        if (this.drag && this.has('drag')) {
            bandDom.setAttribute('draggable', 'true');
            this._listen(bandDom, 'dragstart', (e) => this.drag.start(e));
            this._listen(bandDom, 'dragend', () => this.drag.end());
        }
        if (this.doc && this.has('doc')) bandDom.insertBefore(this._docIcon(), bandDom.firstChild);
        if (this.title && this.has('title')) {
            bandDom.insertBefore(this._titleBox(), bandDom.firstChild);
            this.refreshTitle();
        }
        if (this.collapse && this.has('collapse')) {
            bandDom.insertBefore(this._chevron(), bandDom.firstChild);
        }
        if (this.checkbox && this.has('check')) bandDom.appendChild(this._checkbox());
        if (this.collapse) this.applyCollapsed(this.collapse.isCollapsed());
        this._watchInvalid();
    }

    _watchInvalid() {
        // a field in error anywhere in the card, open or folded, marks its
        // band: the widgets' own error classes, checked once per frame
        const root = this.rootDom();
        if (!root || typeof MutationObserver === 'undefined') return;
        let pending = false;
        this._invalidObserver = new MutationObserver(() => {
            if (pending) return;
            pending = true;
            requestAnimationFrame(() => {
                pending = false;
                this.checkInvalid();
            });
        });
        this._invalidObserver.observe(root, {subtree: true, attributes: true, attributeFilter: ['class']});
        this.checkInvalid();
    }

    checkInvalid() {
        const root = this.rootDom();
        if (!root) return;
        root.classList.toggle('grouplet_card--invalid',
                              this.formError || !!root.querySelector(gnr.GroupletCard.INVALID_SELECTOR));
    }

    _listen(dom, evt, handler) {
        dom.addEventListener(evt, handler);
        this._listeners.push([dom, evt, handler]);
    }

    _chevron() {
        const toggle = document.createElement('div');
        toggle.className = 'grouplet_card_chevron';
        toggle.setAttribute('role', 'button');
        toggle.tabIndex = 0;
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.collapse.toggle();
        });
        toggle.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            e.preventDefault();
            this.collapse.toggle();
        });
        this.chevronDom = toggle;
        gnr.GroupletCard.syncToggle(toggle, this.collapse.isCollapsed());
        return toggle;
    }

    _titleBox() {
        const title = document.createElement('div');
        title.className = 'grouplet_card_title';
        // a folded card opens from its title, as a tree node from its label
        title.addEventListener('click', () => {
            if (this.collapse && this.collapse.isCollapsed()) this.collapse.expand();
        });
        this.titleDom = title;
        return title;
    }

    _docIcon() {
        const icon = document.createElement('div');
        icon.className = 'grouplet_card_doc';
        icon.setAttribute('role', 'button');
        icon.setAttribute('aria-label', _T('!!Information'));
        icon.tabIndex = 0;
        const open = (e) => {
            e.stopPropagation();
            this.openDoc(icon);
        };
        icon.addEventListener('click', open);
        icon.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            e.preventDefault();
            open(e);
        });
        return icon;
    }

    _checkbox() {
        const box = document.createElement('input');
        box.type = 'checkbox';
        box.className = 'grouplet_card_check';
        box.setAttribute('aria-label', _T('!!Select'));
        box.checked = !!this.checkbox.isChecked();
        box.addEventListener('click', (e) => this.checkbox.onClick(e));
        box.addEventListener('keydown', (e) => {
            if (this.checkbox.onKeydown) this.checkbox.onKeydown(e);
        });
        this.checkDom = box;
        return box;
    }

    refreshTitle() {
        if (this.titleDom) this.title(this.titleDom);
    }

    setChecked(checked) {
        if (this.checkDom) this.checkDom.checked = !!checked;
    }

    openDoc(domNode) {
        const title = this.titleDom ? this.titleDom.innerHTML : '';
        this.doc.html((html) => gnr.GroupletCard.showDoc(domNode, title, html));
    }

    applyCollapsed(collapsed, animate = false) {
        const dom = this.rootDom();
        if (!dom) return;
        if (this.chevronDom) gnr.GroupletCard.syncToggle(this.chevronDom, collapsed);
        gnr.GroupletCard.fold(dom, collapsed, this.collapsedClasses, this, animate);
    }

    destroy() {
        if (this._collapseAnim) this._collapseAnim.cancel();
        if (this._invalidObserver) this._invalidObserver.disconnect();
        this._invalidObserver = null;
        this._listeners.forEach(([dom, evt, handler]) => dom.removeEventListener(evt, handler));
        this._listeners = [];
        this.titleDom = this.checkDom = this.chevronDom = null;
        this.bandContent = null;
    }

    static syncToggle(toggle, collapsed) {
        toggle.setAttribute('aria-expanded', String(!collapsed));
        toggle.setAttribute('title', collapsed ? _T('!!Expand') : _T('!!Collapse'));
    }

    static fold(dom, collapsed, classes, holder, animate) {
        // the card eases to its new height like a tree node; a folding one
        // keeps its content in view until it has closed
        if (holder._collapseAnim) holder._collapseAnim.cancel();
        const from = dom.offsetHeight;
        classes.forEach((cls) => dom.classList.toggle(cls, collapsed));
        if (!animate || !gnr.GroupletCard.animates(dom)) return;
        const to = dom.offsetHeight;
        if (from === to) return;
        if (collapsed) classes.forEach((cls) => dom.classList.remove(cls));
        dom.style.overflow = 'hidden';
        const anim = dom.animate([{height: from + 'px', boxSizing: 'border-box'},
                                  {height: to + 'px', boxSizing: 'border-box'}],
                                 {duration: 180, easing: 'ease-out'});
        holder._collapseAnim = anim;
        const done = () => {
            dom.style.overflow = '';
            if (holder._collapseAnim === anim) holder._collapseAnim = null;
        };
        anim.onfinish = () => {
            if (collapsed) classes.forEach((cls) => dom.classList.add(cls));
            done();
        };
        anim.oncancel = done;
    }

    static animates(dom) {
        if (typeof dom.animate !== 'function') return false;
        return !(typeof window !== 'undefined' && window.matchMedia
                 && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }

    static showDoc(domNode, title, html) {
        // one popup for the whole page, moved to the icon clicked
        genro.dlg.quickTooltipPane({nodeId: 'grouplet_card_doc', domNode: domNode,
                                    _class: 'grouplet_card_doc_pane'}, (pane) => {
            const box = pane._('div', {_class: 'grouplet_card_doc_box'});
            if (title) box._('div', {_class: 'grouplet_card_doc_title', innerHTML: title});
            box._('div', {_class: 'grouplet_card_doc_body', innerHTML: html || ''});
        });
        // the focus is in the popup: Esc is heard on the document while it is open
        const Card = gnr.GroupletCard;
        if (Card._docEscape) return;
        Card._docEscape = (e) => {
            if (e.key !== 'Escape') return;
            document.removeEventListener('keydown', Card._docEscape, true);
            Card._docEscape = null;
            genro.publish('grouplet_card_doc_opener_close', {evt: e});
        };
        document.addEventListener('keydown', Card._docEscape, true);
    }

    static buildKebab(host, label, editmenu, presets, kebabKw, iconClass) {
        // editmenu = {entryKey: True | 'label' | {label,action,...}}.
        // True = preset, string overrides the label, dict shallow-merges
        // over the preset.
        host._('div', label, kebabKw);
        const kebabContent = host.getNode(label).getValue();
        kebabContent._('div', 'glyph', {_class: iconClass, innerHTML: '⋮'});
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

    static compileTemplate(spec) {
        // A string, or {template, formats, sums}. `sums` = {name: 'path.field'}:
        // $name shows the field summed at any depth under the row's `path`
        // (the whole row when there is no path), kept live as rows change.
        if (!spec) return null;
        if (typeof spec === 'string') spec = {template: spec};
        const bag = new gnr.GnrBag();
        bag.setItem('main', spec.template || '', {formats: spec.formats || {}});
        // a field the row lacks shows blank, not 'undefined'
        const names = (spec.template || '').match(/\$[a-zA-Z0-9_]+/g) || [];
        const blanks = {};
        names.forEach((name) => { blanks[name.slice(1)] = ''; });
        return {bag: bag, sums: spec.sums || {}, blanks: blanks};
    }

    static renderTemplate(compiled, row, withSums = true) {
        if (!compiled || !(row instanceof gnr.GnrBag)) return '';
        const names = Object.keys(compiled.sums);
        let data = row;
        if (names.length) {
            // a flat copy: the row's own Bags are not reparented
            data = new gnr.GnrBag();
            row.getNodes().forEach((n) => {
                const v = n.getValue();
                if (!(v instanceof gnr.GnrBag)) data.setItem(n.label, v, objectUpdate({}, n.attr || {}));
            });
            names.forEach((name) => {
                data.setItem(name, withSums ? gnr.GroupletCard.deepSum(row, compiled.sums[name]) : '');
            });
        }
        return dataTemplate(compiled.bag, data, null, true, {defaults: compiled.blanks});
    }

    static evaluateOn(sourceNode, value, data) {
        // '^path' / '=path' read at the card's node, '==expr' over the card's fields
        if (typeof value !== 'string') return value;
        if (value.indexOf('==') !== 0) return sourceNode.currentFromDatasource(value);
        const names = [];
        const values = [];
        if (data instanceof gnr.GnrBag) {
            data.getNodes().forEach((n) => {
                if (!/^[A-Za-z_$][\w$]*$/.test(n.label)) return;
                names.push(n.label);
                values.push(n.getValue());
            });
        }
        return funcCreate('return ' + value.slice(2), names.join(',')).apply(sourceNode, values);
    }

    static renderDoc(compiled, row, docKw) {
        // the doc reads the card's data, and docKw for what is not there
        let data = (row instanceof gnr.GnrBag) ? row : new gnr.GnrBag();
        if (docKw && Object.keys(docKw).length) {
            data = data.deepCopy();
            Object.keys(docKw).forEach((k) => data.setItem(k, docKw[k]));
        }
        return gnr.GroupletCard.renderTemplate(compiled, data);
    }

    static renderTitle(dom, compiled, row, label) {
        // a row whose own fields are blank shows its label: its sums alone are no title
        const own = compiled && gnr.GroupletCard.renderTemplate(compiled, row, false);
        if (own && own.replace(/<[^>]*>|&nbsp;/g, '').trim()) {
            dom.innerHTML = gnr.GroupletCard.renderTemplate(compiled, row);
            return;
        }
        dom.textContent = label();
    }

    static deepSum(bag, spec) {
        const parts = String(spec).split('.');
        const field = parts.pop();
        const root = parts.length ? bag.getItem(parts.join('.')) : bag;
        let total = 0;
        const walk = (b) => b.getNodes().forEach((n) => {
            const v = n.getValue();
            if (v instanceof gnr.GnrBag) {
                walk(v);
            } else if (n.label === field) {
                const x = parseFloat(v);
                if (!isNaN(x)) total += x;
            }
        });
        if (root instanceof gnr.GnrBag) walk(root);
        return Math.round10 ? Math.round10(total) : total;
    }
};

gnr.GroupletCard.INVALID_SELECTOR = '.dijitError, .innerLblWrapper_error';


// groupletCard used alone: the host keeps the card's state in the datastore
// (the folded state and the checkbox at the caller's paths, when given, else
// in the card's workspace) and reads its data at the card's datapath. Its
// delete clears the fields of the card.

gnr.GroupletCardHost = class GroupletCardHost {

    constructor(sourceNode, kw) {
        this.sourceNode = sourceNode;
        this.kw = kw;
        this.actionTopic = 'groupletCard_' + sourceNode.attr.nodeId + '_action';
        // the caller's paths are relative to where the card was placed
        const callerNode = sourceNode.getParentNode();
        this.collapsedPath = kw.collapsedPath ? callerNode.absDatapath(kw.collapsedPath)
            : sourceNode.absDatapath('#WORKSPACE.collapsed');
        this.checkboxPath = kw.checkboxPath ? callerNode.absDatapath(kw.checkboxPath) : null;
        const Card = gnr.GroupletCard;
        this.titleTemplate = Card.compileTemplate(kw.titleTemplate) || Card.compileTemplate(kw.template);
        this.docTemplate = Card.compileTemplate(kw.doc);
        const host = this;
        this.card = new gnr.GroupletCard({
            tools: kw.tools,
            rootDom: () => sourceNode.getDomNode(),
            collapse: kw.collapsible ? {
                isCollapsed: () => host.isCollapsed(),
                toggle: () => host.setCollapsed(!host.isCollapsed()),
                expand: () => host.setCollapsed(false)
            } : null,
            title: (dom) => host.renderTitle(dom),
            doc: this.docTemplate ? {
                html: (cb) => cb(Card.renderDoc(host.docTemplate, host.data(), kw.doc_kw))
            } : null,
            checkbox: this.checkboxPath ? {
                isChecked: () => !!genro.getData(host.checkboxPath),
                onClick: (e) => genro.setData(host.checkboxPath, !!e.target.checked)
            } : null
        });
        sourceNode.registerSubscription(this.actionTopic, this, (payload) => this.handleAction(payload),
                                        this.actionTopic);
        this.card.mount(sourceNode.getValue(), '_gc_band', (band) => {
            if (this.card.has('menu')) this._mountKebab(band);
        });
    }

    data() {
        const value = genro.getData(this.sourceNode.absDatapath());
        return (value instanceof gnr.GnrBag) ? value : null;
    }

    isCollapsed() {
        return !!genro.getData(this.collapsedPath);
    }

    setCollapsed(collapsed) {
        genro.setData(this.collapsedPath, !!collapsed);
    }

    applyCollapsed(collapsed) {
        this.card.applyCollapsed(!!collapsed, true);
    }

    setFormStatus(status) {
        this.card.formError = (status === 'error');
        this.card.checkInvalid();
    }

    renderTitle(dom) {
        const kw = this.kw;
        if (kw.title) {
            dom.textContent = kw.title;
            return;
        }
        gnr.GroupletCard.renderTitle(dom, this.titleTemplate, this.data(), () => {
            const v = kw.titleField && this.sourceNode.getRelativeData('.' + kw.titleField);
            return (v === undefined || v === null || v === '') ? kw.emptyTitle : String(v);
        });
    }

    _mountKebab(band) {
        const kw = this.kw;
        const topic = this.actionTopic;
        const editmenu = objectUpdate({}, kw.editmenu || {});
        if (kw.delitem) editmenu.clear = true;
        if (!Object.keys(editmenu).length) return;
        const presets = {
            clear: {
                label: _T('!!Clear'),
                iconClass: 'iconbox trash',
                _class: 'grouplet_grid_menu_danger',
                disabled: '^#WORKSPACE.menu.clear_locked',
                action: "genro.publish('" + topic + "',{action:'clear'});"
            }
        };
        // an entry without its own action is published for the caller
        Object.keys(editmenu).forEach((key) => {
            const entry = editmenu[key];
            if (key !== 'clear' && entry && typeof entry === 'object' && !entry.action) {
                entry.action = "genro.publish('" + topic + "',{action:'" + key + "'});";
            }
        });
        const host = this;
        const kebabKw = objectUpdate({
            _class: 'grouplet_card_kebab',
            tip: _T('!!Actions'),
            connect_onmousedown: function() { host.refreshMenu(); }
        }, kw.editmenu_kw || {});
        if (kw.editmenu_kw && kw.editmenu_kw._class) {
            kebabKw._class = 'grouplet_card_kebab ' + kw.editmenu_kw._class;
        }
        gnr.GroupletCard.buildKebab(band, '_gc_kebab', editmenu, presets, kebabKw, 'grouplet_card_kebab_icon');
    }

    clearAllowed() {
        const form = this.sourceNode.getFormHandler();
        if (form && form.isDisabled()) return false;
        return !!gnr.GroupletCard.evaluateOn(this.sourceNode, this.kw.delitem, this.data());
    }

    refreshMenu() {
        // a dynamic delitem is read as the menu opens
        this.sourceNode.setRelativeData('#WORKSPACE.menu.clear_locked', !this.clearAllowed());
    }

    handleAction(payload) {
        if (!payload || payload.action !== 'clear' || !this.clearAllowed()) return;
        const title = this.card.titleDom ? this.card.titleDom.textContent : '';
        genro.dlg.ask(_T('!!Clear'), _T('!!Clear the fields of $title?').replace('$title', title),
                      {confirm: _T('!!Clear'), cancel: _T('!!Cancel')},
                      {confirm: () => this.clearFields()});
    }

    clearFields() {
        // only the values its widgets show, under the card's own data: a card
        // in a record form shares the record with the rest of the form. With
        // useForm they are in the inner form's record, saved back from there.
        const form = this.kw.formId && genro.formById(this.kw.formId);
        const root = form ? form.sourceNode.absDatapath(form.formDatapath) : this.sourceNode.absDatapath();
        const paths = new Set();
        this.sourceNode.getValue().walk((n) => {
            const value = n.attr && n.attr.value;
            if (typeof value !== 'string' || value.indexOf('^') !== 0) return;
            const path = n.absDatapath(value);
            if (path && path.indexOf(root + '.') === 0) paths.add(path);
        }, 'static');
        paths.forEach((path) => genro.setData(path, null));
    }
};
