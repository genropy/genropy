/* Genro framework bridges. General Bag behavior is inherited from genro-bag-js. */
if (typeof GenroBagJS === 'undefined') throw new Error('genro-bag-js bundle is required');
if (typeof gnr === 'undefined') var gnr = {};

(function(api) {
    // Legacy duplicate labels require insertion of existing nodes. Keep this
    // bridge here; the standalone container has no array facade.
    function spliceNodes(bag, start, count, ...nodes) {
        const container = bag._nodes;
        const list = container._list;
        const append = start === list.length && count === 0;
        const removed = list.splice(start, count, ...nodes);
        if (append) {
            for (const node of nodes) {
                if (!Object.hasOwn(container._dict, node.label)) container._dict[node.label] = node;
            }
        } else {
            for (const label of new Set([...removed, ...nodes].map(node => node.label))) {
                const first = list.find(node => node.label === label);
                if (first) container._dict[label] = first;
                else delete container._dict[label];
            }
        }
        return removed;
    }
    let nextNodeId = 0;
    let lazySetWarningShown = false;
    let callbackItemWarningShown = false;
    const sourceNodeCacheIds = new WeakMap();
    let nextSourceNodeCacheId = 0;
    // Keep the framework's pointer suffix separate from the hierarchical path.
    // In particular, dots in expressions such as #v.toUpperCase() are not Bag
    // separators. This is the grammar used by the original GenroJS Bag.
    const legacyAccessPattern = /(.*?)([?|~])([^?|^=]*)(\??)(.*)/;

    function legacyHtraverse(bag, pathlist, autocreate) {
        let curr = bag;
        if (typeof pathlist === 'string') {
            if (pathlist.indexOf('.') < 0 && pathlist.indexOf('?') < 0 &&
                    pathlist.indexOf('~') < 0 && pathlist.indexOf('/') < 0 &&
                    pathlist !== '#parent') {
                return {value: curr, label: pathlist};
            }
            const suffix = pathlist.match(/(.*?)([?|~])(.*)/);
            if (suffix) {
                pathlist = smartsplit(suffix[1].replace(/\.\.\//g, '#parent.'), '.');
                pathlist[pathlist.length - 1] += suffix[2] + suffix[3];
            } else {
                pathlist = smartsplit(pathlist.replace(/\.\.\//g, '#parent.'), '.');
            }
            if (!pathlist) return {value: curr, label: ''};
        }
        let label = pathlist.shift();
        while (label === '#parent' && pathlist) {
            curr = curr.getParent();
            label = pathlist.shift();
        }
        if (pathlist.length === 0) return {value: curr, label};
        let index = curr.index(label);
        if (index < 0) {
            if (!autocreate) return {value: null, label: null};
            if (label && label.charAt(0) === '#') label = label.replace('#', '_');
            curr.setItem(label, new curr.constructor(), null, {doTrigger: 'autocreate'});
            index = curr.index(label);
        }
        const finalize = newcurr => {
            let isbag = newcurr instanceof api.Bag;
            if (autocreate && !isbag) {
                newcurr = new curr.constructor();
                curr._nodes._list[index].setValue(newcurr, false);
                isbag = true;
            }
            if (isbag) return newcurr.htraverse(pathlist, autocreate);
            return {value: newcurr, label: pathlist.join('.')};
        };
        const newcurr = curr._nodes._list[index].getValue();
        return newcurr instanceof dojo.Deferred ? newcurr.addCallback(finalize) : finalize(newcurr);
    }

    function loadLegacyArray(target, source) {
        if (Array.isArray(source[0])) {
            for (const row of source) target.setItem(row[0], row[1], row[2]);
        } else if (source.length && typeof source[0] === 'object') {
            source.forEach((row, i) => target.setItem('r_' + i,
                new gnr.GnrBag(row), {_autolist: true}));
        }
    }

    gnr.GenropyNodeMixin = Base => class extends Base {
        constructor(parent, label, value, attributes, resolver, nodeTag, xmlTag,
            removeNullAttributes = true) {
            super(parent, label === '#id' ? genro.time36Id() : label,
                resolver ? null : value, attributes, resolver, nodeTag, xmlTag, removeNullAttributes);
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
        getInheritedAttributes(attrname) {
            if (attrname) {
                let node = this;
                while (node && !node.attr[attrname]) node = node.getParentNode();
                return node ? node.attr[attrname] : null;
            }
            const parent = this.getParentNode();
            const inherited = parent
                ? (parent.stopInherite ? objectUpdate({}, parent.attr) : parent.getInheritedAttributes())
                : {};
            return objectUpdate(inherited, this.attr);
        }
        attributeOwnerNode(attrname, attrvalue, caseInsensitive) {
            const names = arguments.length === 1 ? attrname.split(',') : null;
            let node = this;
            while (node) {
                if (names ? names.some(name => name in node.attr)
                    : caseInsensitive
                        ? (node.attr[attrname] || '').toLowerCase() === (attrvalue || '').toLowerCase()
                        : node.attr[attrname] == attrvalue) return node;
                node = node.getParentNode();
            }
            return null;
        }
        setParentBag(value) { this.parentBag = value; }
        orphaned() {
            this.parentBag = null;
            const value = this.staticValue;
            if (value instanceof api.Bag) value.clearBackref();
            return this;
        }
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
        getValue2() { return this.getValue('static'); }
        getValue(mode, options, kwargs) {
            // Extended native attribute queries retain their own parsing path.
            if (typeof mode === 'boolean' && options != null) {
                return super.getValue(mode, options, kwargs);
            }
            const legacyMode = typeof mode === 'boolean' ? (mode ? 'static' : '') : (mode || '');
            const resolver = this.resolver;
            if (!resolver || legacyMode.includes('static') || this._status === 'loading') {
                return this.staticValue;
            }
            const parameters = typeof mode === 'boolean' ? kwargs : options;
            // Standalone resolver instances retain the standalone resolution
            // policy. The Dojo queue belongs only to legacy resolver bridges.
            if (!(resolver instanceof gnr.GnrBagResolver)) {
                return super.getValue(false, null, parameters || {});
            }
            if (resolver.isGetter || resolver.readOnly) return resolver.resolve(parameters, this);
            if (this._status === 'resolving') return resolver.meToo(() => this.getValue2());
            if (this._status === 'loaded' && !resolver.expired && !legacyMode.includes('reload')) {
                return this.staticValue;
            }
            this._status = 'resolving';
            const result = resolver.resolve(parameters, this);
            const finalize = value => {
                this._status = 'loading';
                this.setValue(value, legacyMode === 'notrigger' ? false : 'resolver');
                this._status = 'loaded';
                if (resolver._pendingDeferred.length) {
                    const pending = resolver._pendingDeferred;
                    resolver._pendingDeferred = [];
                    setTimeout(() => resolver.runPendingDeferred(pending), 1);
                }
                if (resolver.onloaded) resolver.onloaded.call(this);
                return this.staticValue;
            };
            return result instanceof dojo.Deferred ? result.addCallback(finalize) : finalize(result);
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
        _toXmlBlock(kwargs) {
            // Legacy XML carries the cached value, without invoking resolvers.
            const value = this.resolver ? this.getValue(true) : this.getValue();
            const tag = this.xmlTag || this.label;
            return value instanceof api.Bag
                ? xml_buildTag(tag, (value.toXmlBlock || gnr.GnrBag.prototype.toXmlBlock).call(value, kwargs),
                    objectUpdate({_T: 'bag'}, this.attr), true)
                : xml_buildTag(tag, value, this.attr);
        }
        getFullpath(mode, root) {
            const parent = this.parentBag;
            if (!parent) return null;
            if (root === true) root = parent.root.getItem('#0');
            const numeric = mode === '#' || mode === '##';
            if (!numeric) {
                const boundary = root instanceof api.Bag ? root : parent.root;
                // Native relativePath uses labels. Verify they identify these
                // nodes before delegating, including previously imported duplicates.
                let current = this;
                while (current && current.parentBag &&
                        current.parentBag.getNode(current.label) === current) {
                    if (current.parentBag === boundary) return boundary.relativePath(this);
                    current = current.parentNode;
                }
            }
            let label = this.label;
            if (numeric || parent.getNode(label) !== this) {
                const index = parent.getNodes().indexOf(this);
                label = mode === '#' ? String(index) : '#' + index;
            }
            const parentPath = parent === root ? '' : parent.getFullpath(mode, root);
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
        constructor(source = null, ...args) {
            const xml = typeof source === 'string' && source.trimStart().startsWith('<');
            super(Array.isArray(source) || xml ? null : source, ...args);
            if (Array.isArray(source)) loadLegacyArray(this, source);
            else if (xml) this.fromXmlDoc(source, genro.clsdict);
        }
        rowchild(tag, kw) {
            if (!Object.hasOwn(this.constructor, '_rowchildWarningShown')) {
                console.warn('Bag.rowchild is deprecated; use setItem with explicit label and attributes.');
                this.constructor._rowchildWarningShown = true;
            }
            const label = tag.startsWith('#') ? kw[tag.slice(1)] : tag + '_' + genro.time36Id();
            genro.assert(label, 'Missing label in this node');
            this.setItem(label, null, kw);
        }
        fillFrom(source) {
            if (!Object.hasOwn(this.constructor, '_fillFromWarningShown')) {
                console.warn('Bag.fillFrom is deprecated; decode the source and use replace(Bag).');
                this.constructor._fillFromWarningShown = true;
            }
            if (source == null) return this;
            const prepared = this.createChildBag();
            if (source instanceof api.Bag) return this.replace(source);
            if (Array.isArray(source)) {
                loadLegacyArray(prepared, source);
            } else if (typeof source === 'string') {
                prepared.fromXmlDoc(new DOMParser().parseFromString(source, 'text/xml'), genro.clsdict);
            } else {
                prepared._loadSource(source);
            }
            return this.replace(prepared);
        }
        walk(callback, mode, kw, notRecursive) {
            if (!this.constructor._walkDeprecationShown) {
                console.warn('Bag.walk is deprecated; use forEach(callback, {deep: true}).');
                this.constructor._walkDeprecationShown = true;
            }
            const isStatic = typeof mode === 'boolean' ? mode : !!(mode && mode.indexOf('static') >= 0);
            let lastResult;
            const stopped = api.Bag.prototype.forEach.call(this, (node, ignored, index) => {
                lastResult = callback(node, kw, index);
                if (lastResult === '__continue__') return false;
                // Wrap falsey results so the native visitor can propagate a stop.
                return lastResult == null ? null : {value: lastResult};
            }, {static: isStatic, deep: !notRecursive});
            return stopped ? stopped.value : lastResult;
        }
        forEach(callback, options, kw) {
            if (options && typeof options === 'object') {
                return api.Bag.prototype.forEach.call(this, callback, options);
            }
            // Legacy forEach always visits only direct nodes, in static mode.
            this.walk(callback, 'static', kw, true);
        }
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
                spliceNodes(this, this.length, 0, node);
            }
        }
        findNodeById(id) {
            return api.Bag.prototype.forEach.call(this, node => node._id == id ? node : undefined, {deep: true}) || undefined;
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
        getIndexList(asText = false) {
            const paths = this.getIndex().map(([parts]) => parts.join('.'));
            return asText ? paths.join('\n') : paths;
        }
        get_modified() { return this._modified; }
        moveNode(from, to, trigger = true) {
            if (to < 0) return;
            trigger = trigger == null ? true : trigger;
            const destination = this.getNode(to).label;
            const insert = (node, index) => {
                node.setParentBag(this);
                spliceNodes(this, index, 0, node);
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
            return this._importWireBag(parsed, clsdict, true);
        }
        toXml(kwargs = {}) {
            kwargs = kwargs || {};
            const encoding = kwargs.encoding || 'utf-8';
            return '<?xml version="1.0" encoding="' + encoding + '"?>\n' +
                xml_buildTag('GenRoBag', this.toXmlBlock(kwargs), null, true);
        }
        toXmlBlock(kwargs) {
            return this.getNodes().map(node =>
                (node._toXmlBlock || gnr.GnrBagNode.prototype._toXmlBlock).call(node, kwargs)).join('\n');
        }
        fromTytxDoc(source, clsdict = {}) {
            return this._importWireBag(api.Bag.fromTytx(source, 'json'), clsdict, false);
        }
        toTytxParameter() {
            return this.toTytx('json') + '::BAGTYTX';
        }
        _importWireBag(parsed, clsdict, xml) {
            const normalizeTransportValue = value => {
                if (value instanceof Number) return value.valueOf();
                if (Array.isArray(value)) return value.map(normalizeTransportValue);
                if (value && Object.getPrototypeOf(value) === Object.prototype) {
                    return Object.fromEntries(Object.entries(value).map(
                        ([key, item]) => [key, normalizeTransportValue(item)]));
                }
                return value;
            };
            const remoteResolverParameters = resolver => {
                const marker = resolver && resolver.payload;
                if (typeof marker !== 'string' || !marker.startsWith('::RSLV:')) return null;
                try {
                    const data = JSON.parse(marker.slice(7));
                    if (!data || typeof data.resolver_module !== 'string' ||
                        typeof data.resolver_class !== 'string') return null;
                    return {
                        resolvermodule: data.resolver_module,
                        resolverclass: data.resolver_class,
                        args: data.args || [],
                        kwargs: data.kwargs || {}
                    };
                } catch (e) {
                    return null;
                }
            };
            const append = (target, sourceBag) => {
                for (const node of sourceBag) {
                    const attributes = Object.fromEntries(Object.entries(node.attr).map(
                        ([key, value]) => [key, normalizeTransportValue(value)]));
                    for (const key of Object.keys(attributes)) {
                        if (xml && typeof attributes[key] === 'string' && attributes[key].includes('::')) {
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
                    } else {
                        value = normalizeTransportValue(value);
                        if (xml && (dtype || typeof value === 'string' && value.includes('::'))) {
                            value = convertFromText(value, dtype);
                            if (dtype === 'H') attributes.dtype = dtype;
                        }
                    }
                    const portableResolver = remoteResolverParameters(node.resolver);
                    const resolverDescription = attributes._resolver || portableResolver;
                    const resolverName = attributes._resolver_name;
                    const resolvedInfo = attributes._resolvedInfo;
                    delete attributes._resolver;
                    delete attributes._resolver_name;
                    delete attributes._resolvedInfo;
                    let resolver;
                    if (resolverDescription) {
                        const parameters = typeof resolverDescription === 'string' ? genro.evaluate(resolverDescription) : resolverDescription;
                        const rawCacheTime = 'cacheTime' in attributes ? attributes.cacheTime :
                            (parameters.kwargs.cacheTime ?? parameters.kwargs.cache_time);
                        // Python uses False for infinite cache; GenroJS uses -1.
                        const cacheTime = portableResolver && rawCacheTime === false ? -1 : rawCacheTime;
                        parameters.cacheTime = 0;
                        resolver = genro.rpc.remoteResolver('resolverRecall', {resolverPars:parameters}, {cacheTime});
                    } else if (resolverName) {
                        resolver = genro.getRelationResolver(attributes, resolverName, target);
                    }
                    const inserted = target.addItem(node.label,
                        resolver && !(value instanceof api.Bag) ? resolver : value, attributes,
                        {nodeTag: node.nodeTag, xmlTag: node.xmlTag});
                    if (resolver && !(value instanceof api.Bag)) inserted._status = 'unloaded';
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
        get(label, fallback, mode, options) {
            let match;
            let node = null;
            let value = null;
            if (!label) {
                node = this.parentNode;
                value = this;
            } else if (label === '#parent') {
                node = this.getParent().getNode();
            } else {
                match = label.match(legacyAccessPattern);
                if (match) label = match[1];
                const index = this.index(label);
                if (index < 0) return fallback;
                node = this._nodes._list[index];
            }
            if (node) value = node.getValue(mode, options);
            if (!match) return value;
            const finalize = current => {
                const expression = match[5];
                if (match[2] === '?') {
                    const attrname = match[3];
                    if (attrname) {
                        if (attrname === '#attr') return node.attr;
                        if (attrname === '#keys') return current.keys();
                        if (attrname === '#node') return node;
                        if (attrname.indexOf('#digest:') === 0) {
                            return current.digest(attrname.split(':')[1]);
                        }
                        current = node.getAttr(attrname);
                    } else if (!expression) {
                        return node.attr;
                    }
                } else if (match[2] === '~') {
                    current = node._value instanceof api.Bag
                        ? node._value.getItem(match[3]) : node.getAttr(match[3]);
                }
                if (!expression) return current;
                if (expression.indexOf('=') === 0) {
                    genro.__evalAuxValue = current;
                    return dojo.eval(expression.slice(1).replace(/#v/g, 'genro.__evalAuxValue'));
                }
            };
            return value instanceof dojo.Deferred ? value.addCallback(finalize) : finalize(value);
        }
        htraverse(pathlist, autocreate) {
            return legacyHtraverse(this, pathlist, autocreate);
        }
        getItem(path, fallback, mode, options) {
            fallback = fallback == '' ? fallback : fallback || null;
            if (!path) return this;
            const finalize = result => result.value instanceof api.Bag
                ? result.value.get(result.label, fallback, mode, options) : fallback;
            const result = this.htraverse(path);
            return result instanceof dojo.Deferred ? result.addCallback(finalize) : finalize(result);
        }
        getNode(path, reserved, autocreate, fallback) {
            if (reserved === true) {
                throw new TypeError('getNode no longer supports asTuple; use getNode(path) for the node');
            }
            return super.getNode(path, true, autocreate, fallback);
        }
        setItem(path, value, attributes, options = {}) {
            if (arguments.length > 4 || (options != null && typeof options !== 'object')) {
                return super.setItem(...arguments);
            }
            if (path === '') {
                if (value instanceof api.Bag) {
                    for (const node of value.getNodes()) {
                        this.setItem(node.label, node.getResolver() || node.getValue(), node.attr);
                    }
                } else if (value !== null && typeof value === 'object') {
                    for (const key in value) {
                        this.setItem(key, value[key] == null ? value[key] : value[key].valueOf());
                    }
                }
                return this;
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
                options.doTrigger !== false, null, options.nodeTag);
        }
        addItem(path, value, attributes, options = {}) {
            const policy = options.duplicate_policy ?? 'rename_warn';
            if (policy !== 'rename_warn' && policy !== 'error') {
                throw new RangeError("duplicate_policy must be 'rename_warn' or 'error'");
            }
            const [bag, requestedLabel] = this._htraverse(path, true);
            let label = requestedLabel;
            if (Object.hasOwn(bag._nodes._dict, label)) {
                if (policy === 'error') throw new Error('Bag label already exists: ' + label);
                let suffix = 1;
                while (Object.hasOwn(bag._nodes._dict, requestedLabel + '__dup_' + suffix)) suffix++;
                label = requestedLabel + '__dup_' + suffix;
                console.warn('GenroJS Bag: addItem renamed duplicate ' + requestedLabel +
                    ' to ' + label + ' (deprecated).');
            }
            const node = new bag.nodeClass(bag, label, value, attributes, null,
                options.nodeTag, options.xmlTag ?? (label !== requestedLabel ? requestedLabel : null));
            const index = bag._nodes._parsePosition(options._position);
            spliceNodes(bag, index, 0, node);
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
            const container = this._nodes;
            const nodes = this.getNodes();
            const notify = trigger && this.backref;
            // Empty storage without detaching: subscribers still need the origin.
            // Container.clear() detaches in 0.5.1 but leaves that to Bag in 0.5.2.
            container._list.length = 0;
            for (const label of Object.keys(container._dict)) delete container._dict[label];
            const detach = node => {
                // A subscriber may have reinserted or moved the node.
                if (node.parentBag === this && this._nodes._dict[node.label] !== node) {
                    node.parentBag = null;
                }
            };
            try {
                for (let i = nodes.length - 1; i >= 0; i--) {
                    const node = nodes[i];
                    try {
                        if (notify) this._onNodeDeleted(node, i, [node.label], null);
                    } finally {
                        detach(node);
                    }
                }
            } finally {
                // Also release unnotified nodes if a subscriber throws.
                for (const node of nodes) detach(node);
            }
        }
        fireItem(path, value = true, attributes, reason = true) {
            value = value == null ? true : value;
            let node = this.getNode(path);
            if (node) node.setValue(value, reason, attributes, false, true);
            else node = this.setItem(path, value, attributes, {doTrigger: reason});
            node.setValue(null, false);
        }
        // Framework equality identifies the Bag location, not equal contents.
        isEqual(otherbag) {
            if (!otherbag) return false;
            if (this === otherbag) return true;
            if (this._parentnode && otherbag._parentnode) {
                return this._parentnode._id == otherbag._parentnode._id;
            }
            return false;
        }
        deepCopy(resolve) { return this.deepcopy(Boolean(resolve)); }
        getNodeByAttr(attr, value, caseInsensitive = false, deep_first = true) {
            return super.getNodeByAttr(attr, value, caseInsensitive, deep_first);
        }
        asDict(recursive = false, excludeNullValues = false) {
            const convert = bag => {
                const nodes = bag.getNodes();
                const result = nodes.some(node => node.attr._autolist) ? [] : {};
                const put = (key, value) => Object.defineProperty(result, key, {
                    value, enumerable: true, writable: true, configurable: true
                });
                for (const node of nodes) {
                    let value = node.getValue();
                    const isBag = value instanceof api.Bag;
                    if (excludeNullValues && (value === null || isBag && value.len() === 0)) continue;
                    if (recursive && isBag) {
                        value = convert(value);
                        if (recursive === 'flat') {
                            for (const key of Object.keys(value)) put(key, value[key]);
                            continue;
                        }
                    }
                    if (Array.isArray(result)) result.push(value);
                    else if (typeof value !== 'string' || !value.endsWith('::JS')) put(node.label, value);
                }
                return result;
            };
            return convert(this);
        }
        digest(what = null, condition = null, asColumns = false) {
            const columns = typeof condition === 'boolean' ? condition : asColumns;
            const result = super.digest(what, condition, asColumns);
            const singleField = Array.isArray(what) ? what.length === 1 :
                typeof what === 'string' && what.trim() !== '' && what.split(',').length === 1;
            if (!columns && singleField) {
                console.warn('GenroJS Bag.digest: single-field row wrapping is deprecated; use query(what, condition) for a flat result.');
                return result.map(value => [value]);
            }
            return result;
        }
        sort(key) {
            if (typeof key === 'function') return super.sort(key);
            const translated = (key || '#k:a').split(',').map(level => {
                const [criterion, rawMode = 'a'] = level.split(':');
                let mode = rawMode.trim();
                if (/^[adAD]$/.test(mode)) return criterion.trim() + ':' + mode;
                mode = mode.toLowerCase();
                const insensitive = mode.endsWith('*');
                if (insensitive) {
                    console.warn('Bag.sort: * is deprecated; use a/d for case-insensitive sorting and A/D for case-sensitive sorting.');
                    mode = mode.slice(0, -1);
                }
                const ascending = mode === 'a' || mode === 'asc' || mode === '>';
                const direction = ascending ? 'a' : 'd';
                return criterion.trim() + ':' + (insensitive ? direction : direction.toUpperCase());
            }).join(',');
            return super.sort(translated);
        }
    };

    gnr.GenropyResolverMixin = Base => class extends Base {
        get isGetter() { return this.readOnly; }
        set isGetter(value) { this._readOnly = value; }
        get lastUpdate() { return this._lastUpdate == null ? null : new Date(this._lastUpdate); }
        set lastUpdate(value) { this._lastUpdate = value == null ? null : Number(value); }
        _finalize(value) {
            // Dojo 1.1 Deferred is not a Promise/thenable. Complete the native
            // cache only when the Deferred resolves, retaining its identity.
            if (value instanceof dojo.Deferred) {
                return value.addCallback(result => super._finalize(result));
            }
            return super._finalize(value);
        }
        resolve(options, destinationNode) {
            const parameters = objectUpdate({}, this.kwargs);
            parameters._destFullpath = destinationNode ? destinationNode.getFullpath(null, genro._data) : '';
            if (options) objectUpdate(parameters, options);
            if (this.isGetter) return this.load(parameters);
            const result = this.load(parameters, destinationNode);
            const finalize = value => { this.lastUpdate = new Date(); return value; };
            return result instanceof dojo.Deferred ? result.addCallback(finalize) : finalize(result);
        }
        meToo(callback) {
            const pending = new dojo.Deferred();
            pending.addCallback(callback);
            this._pendingDeferred.push(pending);
            return pending;
        }
        runPendingDeferred(pending) {
            for (const deferred of pending) deferred.callback();
        }
        cancelMeToo() {
            const pending = this._pendingDeferred || [];
            this._pendingDeferred = [];
            for (const deferred of pending) deferred.cancel();
        }
        _resolvedBagCompat() {
            if (!Object.hasOwn(this.constructor, '_bagDelegationWarningShown')) {
                console.warn('Resolver Bag delegation is deprecated; use resolver.resolve() explicitly.');
                this.constructor._bagDelegationWarningShown = true;
            }
            return this.resolve();
        }
        keys() { return this._resolvedBagCompat().keys(); }
        items() { return this._resolvedBagCompat().items(); }
        values() { return this._resolvedBagCompat().values(); }
        digest(key) { return this._resolvedBagCompat().digest(key || null); }
        sum(key) { return this._resolvedBagCompat().sum(key || null); }
        len() { return this._resolvedBagCompat().len(); }
        contains() { return this._resolvedBagCompat().contains(); }
        htraverse(kwargs) {
            return this._resolvedBagCompat().htraverse(kwargs.pathlist, kwargs.autocreate);
        }
        _computeEffectiveFingerprint(kwargs) {
            const sourceNode = kwargs._sourceNode;
            if (!sourceNode || typeof sourceNode !== 'object') return super._computeEffectiveFingerprint(kwargs);
            if (!sourceNodeCacheIds.has(sourceNode)) sourceNodeCacheIds.set(sourceNode, ++nextSourceNodeCacheId);
            return super._computeEffectiveFingerprint({...kwargs,
                _sourceNode: sourceNodeCacheIds.get(sourceNode)});
        }
        constructor(kwargs = {}, isGetter = false, cacheTime = 0, load) {
            // Preserve legacy enumerable inputs, but retain the base's merged,
            // filtered parameter object and all changes made by init().
            super({...objectUpdate({}, kwargs), readOnly: isGetter, cacheTime, asBag: false});
            this._pendingDeferred = [];
            if (load) this.load = load;
        }
        getParentNode() { return this._node; }
        // Legacy reference assignment is not a resolver attachment operation.
        setParentNode(node) { this._node = node; }
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
            super(kwargs, isGetter, cacheTime);
            this.method = kwargs.method;
            this.parameters = kwargs.parameters;
        }
        // Temporary legacy parameter merge; review scope is recorded as R01.
        load(kwargs) {
            const parameters = objectUpdate({}, this.parameters);
            objectUpdate(parameters, kwargs);
            return this.method.call(this, parameters);
        }
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
