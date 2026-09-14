/* Genro framework bridges. General Bag behavior is inherited from genro-bag-js. */
if (typeof GenroBagJS === 'undefined') throw new Error('genro-bag-js bundle is required');
if (typeof gnr === 'undefined') var gnr = {};

(function(api) {
    let nextNodeId = 0;
    let lazySetWarningShown = false;
    let callbackItemWarningShown = false;
    const sourceNodeCacheIds = new WeakMap();
    let nextSourceNodeCacheId = 0;
    const staticMode = mode => mode === true || mode === 'static';

    gnr.GenropyNodeMixin = Base => class extends Base {
        constructor(parent, label, value, attributes, resolver) {
            super(parent, label === '#id' ? genro.time36Id() : label,
                resolver ? null : value, attributes, resolver);
            this._id = ++nextNodeId;
            this.locked = false;
            this._status = 'loaded';
        }
        get _parentbag() { return this.parentBag; }
        get attr() { return super.attr; }
        set attr(value) { this._attr = value; }
        set _parentbag(value) { this.parentBag = value; }
        getParentBag() { return this.parentBag; }
        getParentNode() { return this.parentNode; }
        setParentBag(value) { this.parentBag = value; }
        getStringId() { return 'n_' + this._id; }
        getStaticValue() { return this.staticValue; }
        setStaticValue(value) { this.staticValue = value; }
        clearValue(trigger) {
            this.setValue(null, trigger);
            return this;
        }
        getResolver() { return this.resolver; }
        setResolver(value) { this.resolver = value; this._status = value ? 'unloaded' : 'loaded'; }
        isLoaded() { return this._status === 'loaded'; }
        isLoading() { return this._status === 'loading'; }
        isExpired() { return this.resolver ? this.resolver.expired : false; }
        refresh(always) {
            if (always || this.isExpired()) this.getValue('reload');
        }
    getFormattedValue(kw,mode) {
        var v = this.getValue(mode);
        kw = kw || {};
        kw.joiner = kw.joiner || '<br/>';
        kw.omitEmpty = 'omitEmpty' in kw? kw.omitEmpty : true;
        if(v instanceof gnr.GnrBag){
            if(this.attr._autoTable){
                v = v.asHtmlTable(objectUpdate(kw,{headers:true,cells:true}));
            }else{
                v = v.getFormattedValue(kw,mode);
            }
            
        }else{
            v = this.attr._formattedValue || this.attr._displayedValue || v;
        }
        return (!isNullOrBlank(v) || !kw.omitEmpty)?((this.attr._valuelabel || this.attr.name_long || stringCapitalize(this.label)) +': ' +_F(v,null,this.attr.dtype)):''; 
    }
        getValue(mode, options, kwargs) {
            const isStatic = staticMode(mode);
            if (typeof mode === 'string' && mode.includes('reload') && this.resolver) this.resolver.reset();
            const tracksLoad = this.resolver && !isStatic;
            if (tracksLoad) this._status = 'resolving';
            const complete = value => { if (tracksLoad) this._status = 'loaded'; return value; };
            const failed = error => { if (tracksLoad) this._status = 'unloaded'; throw error; };
            try {
                const result = typeof mode === 'boolean' ? super.getValue(mode, options, kwargs) :
                    super.getValue(isStatic, null, options || {});
                return result && typeof result.then === 'function' ? result.then(complete, failed) : complete(result);
            } catch (error) { return failed(error); }
        }
        setValue(value, trigger, attributes, merge, fired) {
            if (arguments.length > 5) return super.setValue(...arguments);
            const previous = this._fired;
            this._fired = fired;
            try {
                return super.setValue(value, trigger == null ? true : trigger,
                    attributes, merge, false, trigger);
            } finally {
                this._fired = previous;
            }
        }
        setAttribute(name, value, trigger) { this.setAttr({[name]: value}, trigger, true); }
        updAttributes(attributes, trigger) { this.setAttr(attributes, trigger, true, false); }
        replaceAttr(attributes) { this.setAttr(attributes, true, false, false); }
        getFullpath(mode, root) {
            if (!this.parentBag || this.parentBag === root) return this.label;
            const index = this.parentBag._nodes.indexOf(this);
            const label = mode === '##' ? '#' + index : mode === '#' ? String(index) :
                this.parentBag.getNode(this.label) === this ? this.label : '#' + index;
            const parentPath = this.parentBag.getFullpath(mode, root);
            return parentPath ? parentPath + '.' + label : label;
        }
        isChildOf(ancestor) {
            const target = ancestor instanceof api.Bag ? ancestor.parentNode : ancestor;
            for (let node = this.parentNode; node; node = node.parentNode) {
                if (node === target) return true;
            }
            return false;
        }
        isAncestor(node) { return node === this || node.isChildOf(this); }
        isDescendant(node) { return this.isChildOf(node); }
        parentshipLevel(ancestor) {
            let level = 0;
            for (let node = this; node; node = node.getParentNode(), level++) {
                if (node === ancestor) return level;
            }
            return -1;
        }
    };

    // Translate subscriptions at the boundary; retain standalone event propagation.
    gnr.GenropyEventsMixin = Base => class extends Base {
        subscribe(id, callbacks = {}) {
            const wrap = callback => callback && (event => {
                const kind = event.evt.startsWith('upd') ? 'upd' : event.evt;
                const payload = {...event, evt: kind, base: this,
                    value: event.node._value, fired: event.node._fired};
                if (kind === 'upd') {
                    payload.updattr = event.evt !== 'upd_value';
                    if (event.evt !== 'upd_attrs') payload.updvalue = true;
                    const changes = Object.keys(event.attrs_diff || {});
                    payload.changedAttr = changes.length === 1 ? changes[0] : null;
                    payload.changedAttributes = Object.fromEntries(changes.map(key => [key, true]));
                    payload.oldattr = {...event.node.attr};
                    for (const key of changes) payload.oldattr[key] = event.attrs_diff[key].old;
                } else {
                    payload.where = event.where || event.node.parentBag;
                    if (kind === 'ins') payload.pathlist = [...event.pathlist, event.node.label];
                }
                return callback(payload);
            });
            return super.subscribe(id, {
                update: wrap(callbacks.upd || callbacks.update || callbacks.any),
                insert: wrap(callbacks.ins || callbacks.insert || callbacks.any),
                delete: wrap(callbacks.del || callbacks.delete || callbacks.any)
            });
        }
        // Deletion needs the original container after the node has been detached.
        _onNodeDeleted(node, index, path = null, reason = null, where = this) {
            path = path || [node.label];
            const event = {node, ind: index, pathlist: path, reason, where, evt: 'del'};
            for (const callback of Object.values(this._delSubscribers)) callback(event);
            if (this.parent && this.parentNode) {
                this.parent._onNodeDeleted(node, index, [this.parentNode.label, ...path], reason, where);
            }
        }
        unsubscribe(id, options = {any: true}) { return super.unsubscribe(id, options); }
    };

    // Presentation helpers remain in GenroJS, outside the data library.
    gnr.GenropyFormattingMixin = Base => class extends Base {
    asHtmlTable(kw, mode){
        kw = kw || {};
        var datamode = kw.datamode || 'bag';
        var tableClass = kw.tableClass || 'selectable formattedBagTable';
        var firstRow = datamode == 'bag' ? this.getItem('#0') : new gnr.GnrBag(this.getAttr('#0'));
        var cells;
        if(kw.cells === true){
            cells = firstRow ? firstRow.keys() : [];
        }else if(typeof kw.cells === 'string'){
            cells = kw.cells.split(',');
        }else{
            cells = kw.cells || [];
        }
        var parts = ['<table class="' + tableClass + '">'];
        if(kw.headers && firstRow){
            var headerLabels = kw.headers;
            if(headerLabels === true){
                headerLabels = [];
                firstRow.forEach(function(n){
                    headerLabels.push(n.attr._valuelabel || n.attr.name_long || stringCapitalize(n.label));
                });
            }else if(typeof headerLabels === 'string'){
                headerLabels = headerLabels.split(',');
            }
            parts.push('<thead><tr>');
            dojo.forEach(headerLabels, function(th){
                parts.push('<th>' + th + '</th>');
            });
            parts.push('</tr></thead>');
        }
        parts.push('<tbody>');
        this.forEach(function(n){
            var bag = datamode == 'bag' ? n._value : new gnr.GnrBag(n.attr);
            var rowParts = ['<tr>'];
            dojo.forEach(cells, function(cell){
                var cellConf = kw[cell] || {};
                var vnode = bag ? bag.getNode(cell) : null;
                var v = '';
                var tdClass = '';
                if(vnode){
                    v = vnode._value;
                    if(v instanceof gnr.GnrBag){
                        v = v.getFormattedValue(kw, mode);
                    }else if(isNullOrBlank(v)){
                        v = '';
                    }else{
                        var dtype = cellConf.dtype || vnode.attr.dtype || guessDtype(v);
                        var fmt = typeof cellConf === 'string' ? cellConf : cellConf.format;
                        v = fmt ? _F(v, fmt, dtype) : (vnode.attr._formattedValue || vnode.attr._displayedValue || v);
                        if(dtype == 'N' || dtype == 'L'){
                            tdClass = ' class="num"';
                        }
                    }
                }
                if(cellConf.width){
                    v = '<div style="width:' + cellConf.width + '">' + v + '</div>';
                }
                rowParts.push('<td' + tdClass + '>' + v + '</td>');
            });
            rowParts.push('</tr>');
            parts.push(rowParts.join(''));
        }, 'static');
        parts.push('</tbody></table>');
        return parts.join('');
    }
    asNestedTable(kw,mode){
        var rows = [];
        this.forEach(function(n){
            var v =  n.getValue(mode);
            if(v instanceof gnr.GnrBag){
                v = n.attr._autoTable?v.asHtmlTable({headers:true,cells:true}):v.asNestedTable(kw,mode);
            }
            if(kw.omitEmpty && isNullOrBlank(v)){
                return;
            }
            if (!n.attr._autolist){
                rows += '<tr><td class="_bagformat_lbl">'+n.label+'</td>';
            }
            rows += '<td class="_bagformat_value">'+_F(v,null,n.attr.dtype)+'</td></tr>';
        },mode);
        return '<table class="nestedBagTable"><tbody>'+rows+'</tbody></table>';
    }
    getFormattedValue(kw,mode){
        kw = kw || {};
        kw.omitEmpty = 'omitEmpty' in kw? kw.omitEmpty:true;
        if(this._parentnode && this._parentnode.attr.format_bag_cells){
            return this.asHtmlTable(objectExtract(this._parentnode.attr,'format_bag_*',true));
        }else if(kw.cells){
            return this.asHtmlTable(kw);
        }else if(kw.nested){
            return this.asNestedTable(kw,mode);
        }
        var r = [];
        kw.joiner = kw.joiner || '<br/>';
        var fv;
        this.forEach(function(n){
            if(n.label[0]!='_'){
                fv = n.getFormattedValue(kw,mode);
                if(kw.omitEmpty && isNullOrBlank(fv)){
                    return;
                }
                r.push(fv);
            }
        },mode);
        return r.join(kw.joiner);
    }    };

    gnr.GenropyBagMixin = Base => class extends Base {
        asObj(formatAttributes) {
            const result = {};
            for (const node of this) result[node.label] = node.resolver ? '**' : node.getValue();
            for (const key in formatAttributes) result[key] = asText(result[key], formatAttributes[key]);
            return result;
        }
        concat(bag) {
            if (!bag) return;
            for (const node of [...bag]) {
                node.setParentBag(this);
                this._nodes.splice(this.length, 0, node);
            }
            for (const node of [...this].reverse()) this._nodes._dict[node.label] = node;
        }
        findNodeById(id) {
            return this.walk(node => node._id == id ? node : undefined, true) || undefined;
        }
        getIndex() {
            const result = [], visited = new Set([this]);
            const visit = (bag, path) => {
                for (const node of bag) {
                    const nodePath = [...path, node.label];
                    const value = node.getValue();
                    result.push([nodePath, node]);
                    if (value instanceof api.Bag && !visited.has(value)) {
                        visited.add(value);
                        visit(value, nodePath);
                    }
                }
            };
            visit(this, []);
            return result;
        }
        get_modified() { return this._modified; }
        moveNode(from, to, trigger = true) {
            if (to < 0) return;
            trigger = trigger == null ? true : trigger;
            const destination = this._nodes[to].label;
            const insert = (node, index) => {
                node.setParentBag(this);
                this._nodes.splice(index, 0, node);
                for (const item of [...this].reverse()) this._nodes._dict[item.label] = item;
                if (this.backref && trigger !== false) this._onNodeInserted(node, index, null, trigger);
            };
            if (Array.isArray(from) && from.length > 1) {
                const positions = [...from].sort((a, b) => a - b);
                const delta = positions[0] < to ? 1 : 0;
                const nodes = positions.reverse().map(index => this._pop('#' + index, trigger));
                const index = this.index(destination) + delta;
                for (const node of nodes) insert(node, index);
            } else {
                const index = Array.isArray(from) ? from[0] : from;
                if (index !== to) insert(this._pop('#' + index, trigger), to);
            }
        }
        fromXmlDoc(source, clsdict = {}) {
            const parsed = typeof source === 'string' ? api.Bag.fromXml(source) :
                api.Bag._xmlElementToBag(source.nodeType === 9 ? source.documentElement : source);
            const append = (target, sourceBag) => {
                for (const node of sourceBag) {
                    const attributes = {...node.attr};
                    for (const key of Object.keys(attributes)) {
                        if (typeof attributes[key] === 'string' && attributes[key].includes('::')) {
                            attributes[key] = convertFromText(attributes[key]);
                        }
                    }
                    const dtype = attributes._T;
                    const Class = clsdict && clsdict[attributes.__cls] || target.constructor;
                    delete attributes._T;
                    delete attributes.__cls;
                    let value = node.getValue(true);
                    if (value instanceof api.Bag) {
                        const child = new Class();
                        append(child, value);
                        value = child;
                    } else if (dtype || typeof value === 'string' && value.includes('::')) {
                        value = convertFromText(value, dtype);
                        if (dtype === 'H') attributes.dtype = dtype;
                    }
                    const resolverDescription = attributes._resolver;
                    const resolverName = attributes._resolver_name;
                    const resolvedInfo = attributes._resolvedInfo;
                    delete attributes._resolver;
                    delete attributes._resolver_name;
                    delete attributes._resolvedInfo;
                    let resolver;
                    if (resolverDescription) {
                        const parameters = genro.evaluate(resolverDescription);
                        const cacheTime = 'cacheTime' in attributes ? attributes.cacheTime : parameters.kwargs.cacheTime;
                        parameters.cacheTime = 0;
                        resolver = genro.rpc.remoteResolver('resolverRecall', {resolverPars:parameters}, {cacheTime});
                    } else if (resolverName) {
                        resolver = genro.getRelationResolver(attributes, resolverName, target);
                    }
                    const inserted = target.addItem(node.label, resolver && !(value instanceof api.Bag) ? resolver : value, attributes);
                    if (resolver && value instanceof api.Bag) {
                        inserted.setResolver(resolver);
                        inserted._status = 'loaded';
                        resolver.cachedValue = value;
                        resolver._lastUpdate = Date.now();
                        Object.assign(inserted.attr, resolvedInfo);
                        const effective = {...resolver.kwargs};
                        for (const [key, item] of Object.entries(inserted.attr)) {
                            if (!resolver.constructor.internalParams.has(key) && !(key in effective)) effective[key] = item;
                        }
                        resolver._lastEffectiveFingerprint = resolver._computeEffectiveFingerprint(effective);
                    }
                }
            };
            append(this, parsed);
        }
        get nodeClass() { return this._nodeFactory || gnr.GnrBagNode; }
        get _parentnode() { return this.parentNode; }
        set _parentnode(value) { this.parentNode = value; }
        len() { return this.length; }
        index(label) { return this._nodes.index(label); }
        getParent() { return this.parent; }
        getParentNode() { return this.parentNode; }
        getRoot() { return this.root; }
        getFullpath(mode, root) {
            if (root === true) root = this.getRoot().getItem('#0');
            return this === root || !this.parentNode ? '' : this.parentNode.getFullpath(mode, root);
        }
        setBackRef(node, parent) { return this.setBackref(node, parent); }
        clearBackRef() { return this.clearBackref(); }
        hasBackRef() { return this.backref; }
        getBackRef() { return this.backref; }
        attributes() { return this.parentNode ? this.parentNode.attr : undefined; }
        resolver() { return this.parentNode ? this.parentNode.resolver : undefined; }
        getItem(path, fallback, mode, options) {
            const expressionAt = typeof path === 'string' ? path.indexOf('?=') : -1;
            if (expressionAt >= 0) {
                const value = this.getItem(path.slice(0, expressionAt), fallback, mode, options);
                const evaluate = funcCreate('return (' + path.slice(expressionAt + 2).replace(/#v/g, 'value') + ');', 'value');
                return value && typeof value.then === 'function' ? value.then(evaluate) : evaluate(value);
            }
            const result = super.getItem(path, fallback, staticMode(mode), options);
            return result;
        }
        getNode(path, asTuple, autocreate, fallback) {
            const node = super.getNode(path, true, autocreate, fallback);
            return asTuple ? {obj: node && node.parentBag, node} : node;
        }
        setItem(path, value, attributes, options = {}) {
            if (arguments.length > 4 || (options != null && typeof options !== 'object')) {
                return super.setItem(...arguments);
            }
            options = options || {};
            if (typeof path === 'string') path = path.replace(/(^|\.)#id$/, (_, prefix) => prefix + genro.time36Id());
            if (options.lazySet && !lazySetWarningShown) {
                lazySetWarningShown = true;
                console.warn('GenroJS Bag: lazySet is ignored; using the new Bag change detection.');
            }
            for (const name of ['_duplicate', 'fired']) {
                if (options[name]) throw new Error('Mixin Bag: setItem option not yet bridged: ' + name);
            }
            return super.setItem(path, value, attributes, options._position,
                options._updattr, false, options.doTrigger, false,
                options.doTrigger !== false);
        }
        addItem(path, value, attributes, options = {}) {
            const [bag, label] = this._htraverse(path, true);
            const node = new bag.nodeClass(bag, label, value, attributes);
            const index = bag._nodes._parsePosition(options._position);
            bag._nodes.splice(index, 0, node);
            // Legacy label lookup selects the first duplicate in display order.
            for (const item of [...bag._nodes].reverse()) bag._nodes._dict[item.label] = item;
            if (bag.backref && options.doTrigger !== false) {
                bag._onNodeInserted(node, index, null, options.doTrigger);
            }
            return node;
        }
        // Deprecated GenroJS spelling/signature; keep parameters and node attrs.
        setCallBackItem(path, callback, parameters, kwargs) {
            if (!callbackItemWarningShown) {
                callbackItemWarningShown = true;
                console.warn('GenroJS Bag: setCallBackItem is deprecated. Migrate to setCallbackItem(path, callback, options), handling node attributes explicitly.');
            }
            const attributes = {...kwargs, method: callback, parameters};
            const resolver = new gnr.GnrBagCbResolver(attributes);
            this.setItem(path, resolver, attributes);
        }
        _pop(label, trigger = true) {
            const index = this._nodes.index(label);
            const node = this._nodes.pop(label);
            if (node) {
                const remaining = [...this._nodes].find(item => item.label === node.label);
                if (remaining) this._nodes._dict[node.label] = remaining;
            }
            if (node && this.backref && trigger !== false) {
                this._onNodeDeleted(node, index, [node.label], trigger);
            }
            return node;
        }
        pop(path, trigger) {
            const node = this.popNode(path, trigger);
            return node ? node.getValue() : undefined;
        }
        delItem(path, trigger) { return this.pop(path, trigger); }
        clear(trigger = false) {
            for (let i = this.length - 1; i >= 0; i--) this._pop('#' + i, trigger);
        }
        fireItem(path, value = true, attributes, reason = true) {
            value = value == null ? true : value;
            let node = this.getNode(path);
            if (node) node.setValue(value, reason, attributes, false, true);
            else node = this.setItem(path, value, attributes, {doTrigger: reason});
            node.setValue(null, false);
        }
        deepCopy(resolve) { return this.deepcopy(Boolean(resolve)); }
    };

    gnr.GenropyResolverMixin = Base => class extends Base {
        _computeEffectiveFingerprint(kwargs) {
            const sourceNode = kwargs._sourceNode;
            if (!sourceNode || typeof sourceNode !== 'object') return super._computeEffectiveFingerprint(kwargs);
            if (!sourceNodeCacheIds.has(sourceNode)) sourceNodeCacheIds.set(sourceNode, ++nextSourceNodeCacheId);
            return super._computeEffectiveFingerprint({...kwargs,
                _sourceNode: sourceNodeCacheIds.get(sourceNode)});
        }
        constructor(kwargs = {}, isGetter = false, cacheTime = 0, load) {
            super({...kwargs, readOnly: isGetter, cacheTime, asBag: false});
            this.kwargs = kwargs;
            if (load) this.load = load;
        }
        getParentNode() { return this._node; }
        setParentNode(node) { this.setNode(node); }
        get kwargs() { return this._kw; }
        set kwargs(value) { this._kw = value; }
        getCacheTime() { return this.cacheTime; }
        setCacheTime(value) { this.cacheTime = value; }
    };

    gnr.GnrBagNode = gnr.GenropyNodeMixin(api.BagNode);
    gnr.GnrBag = gnr.GenropyBagMixin(gnr.GenropyFormattingMixin(gnr.GenropyEventsMixin(api.Bag)));
    gnr.GnrBagResolver = gnr.GenropyResolverMixin(api.BagResolver);
    gnr.GnrBagCbResolver = class extends gnr.GnrBagResolver {
        constructor(kwargs = {}, isGetter, cacheTime) {
            super({...kwargs.parameters, ...kwargs}, isGetter, cacheTime);
            this.method = kwargs.method;
        }
        load(kwargs) { return this.method(kwargs); }
    };
    for (const name of ['GnrBagNode', 'GnrBag', 'GnrBagResolver', 'GnrBagCbResolver']) {
        Object.defineProperty(gnr[name].prototype, 'declaredClass', {
            value: 'gnr.' + name, writable: true, configurable: true
        });
    }
    api.BagResolver.registerBagClass(gnr.GnrBag);
})(GenroBagJS);

gnr.bagRealPath = function(path) {
    if (path.indexOf('#parent') > 0) {
        var lpath = path.split('.');
        path = [];
        for (var i = 0; i < lpath.length; i++) {
            if (lpath[i] != '#parent') {
                path.push(lpath[i]);
            } else {
                path.pop();
            }
        }
        path = path.join('.');
    }
    return path;
};
