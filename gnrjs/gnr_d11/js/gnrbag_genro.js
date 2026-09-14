/*
 * Opt-in compatibility adapter for genro-bag-js.
 * The standalone classes supply storage, collections, query and copy behavior.
 * Explicit compatibility methods preserve historical traversal, mutation,
 * serialization, resolver and event contracts used by Genro applications.
 */

if (typeof GenroBagJS == 'undefined') {
    throw new Error('genro-bag-js was selected but its browser bundle is missing');
}
if (typeof gnr == 'undefined') {
    var gnr = {};
}

(function(api) {
    var StandaloneBag = api.Bag;
    var StandaloneNode = api.BagNode;
    var StandaloneResolver = api.BagResolver;
    var NodeContainer = api.BagNodeContainer;

    function isStaticMode(mode) {
        return mode === true || mode === 'static';
    }

    function makeMethodsEnumerable(prototype, names) {
        (names || Object.getOwnPropertyNames(prototype)).forEach(function(name) {
            if (name === 'constructor') return;
            var descriptor = Object.getOwnPropertyDescriptor(prototype, name);
            if (typeof descriptor.value === 'function') {
                descriptor.enumerable = true;
                Object.defineProperty(prototype, name, descriptor);
            }
        });
    }

    gnr.GnrBagNode = class GnrBagNode extends StandaloneNode {
        constructor(parentbag, label, value, attr, resolver) {
            if (label === '#id') label = genro.time36Id();
            super(parentbag, label, resolver ? null : value, attr, resolver);
            this._id = this._counter[0] += 1;
            this.locked = false;
            this._status = 'loaded';
            this._onChangedValue = null;
        }

        get parentBag() { return this._parentBag; }
        set parentBag(value) {
            this._parentBag = value;
            this._parentbag = value;
        }
        get attr() { return this._attr; }
        set attr(value) { this._attr = value || {}; }

        getValue(mode, optkwargs) {
            mode = mode || '';
            if (!this._resolver || isStaticMode(mode) || this._status === 'loading') {
                return this._value;
            }
            if (this._resolver.isGetter) {
                return this._resolver.resolve(optkwargs, this);
            }
            if (this._status === 'resolving') {
                return this._resolver.meToo(function() {
                    return this.getValue(mode, optkwargs);
                }.bind(this));
            }
            if (this._status === 'loaded' && !this._resolver.expired() &&
                    mode.indexOf('reload') < 0) {
                return this._value;
            }

            this._status = 'resolving';
            var result = this._resolver.resolve(optkwargs, this);
            var finalize = function(value) {
                this._status = 'loading';
                this.setValue(value, mode === 'notrigger' ? false : 'resolver');
                this._status = 'loaded';
                var pending = this._resolver._pendingDeferred;
                this._resolver._pendingDeferred = [];
                if (pending.length) {
                    setTimeout(function() {
                        this._resolver.runPendingDeferred(pending);
                    }.bind(this), 1);
                }
                if (this._resolver.onloaded) this._resolver.onloaded.call(this);
                return this._value;
            }.bind(this);
            if (result instanceof dojo.Deferred) return result.addCallback(finalize);
            if (result && typeof result.then === 'function') return result.then(finalize);
            return finalize(result);
        }

        setValue(value, doTrigger, attributes, updattr, fired) {
            if (arguments.length >= 6) return super.setValue(...arguments);
            this._legacyFired = fired;
            try {
                super.setValue(value, doTrigger == null ? true : doTrigger, attributes, updattr,
                    updattr === '*',
                    doTrigger === undefined ? null : doTrigger);
            } finally {
                delete this._legacyFired;
            }
        }

        setAttr(attributes, doTrigger, updateAttr, changedAttr) {
            this._legacyChangedAttr = changedAttr;
            try {
                if (updateAttr === '*') {
                    var merged = Object.assign({}, this._attr);
                    Object.keys(attributes || {}).forEach(function(key) {
                        if (attributes[key] == null) delete merged[key];
                        else merged[key] = attributes[key];
                    });
                    return super.setAttr(merged, doTrigger !== false, false, false);
                }
                return super.setAttr(attributes, doTrigger !== false,
                    updateAttr === undefined ? false : updateAttr,
                    false);
            } finally {
                delete this._legacyChangedAttr;
            }
        }

        getStringId() { return 'n_' + this._id; }
        getParentNode() { return this.parentNode; }
        getParentBag() { return this.parentBag; }
        orphaned() {
            this.setParentBag(null);
            if (this._value instanceof gnr.GnrBag) this._value.clearBackRef();
            return this;
        }
        isChildOf(bagOrNode) {
            var node = bagOrNode instanceof gnr.GnrBagNode ?
                bagOrNode : bagOrNode.getParentNode();
            var current = this;
            var parentNode;
            do {
                parentNode = current.getParentNode();
                current = parentNode;
            } while (parentNode && parentNode !== node);
            return !isNullOrBlank(parentNode);
        }
        isAncestor(node) {
            do {
                if (node && node._id === this._id) return true;
                node = node.getParentNode();
            } while (node);
            return false;
        }
        isDescendant(node) { return node.isAncestor(this); }
        backrefOk() { return this.getParentBag().backrefOk(); }
        getValue2(mode, optkwargs) { return this.getValue('static'); }
        attributeOwnerNode(attrname, attrvalue, caseInsensitive) {
            var current = this;
            if (arguments.length === 1) {
                var names = attrname.indexOf(',') < 0 ? [attrname] : attrname.split(',');
                while (current && !names.some(function(name) {
                    return name in current.attr;
                })) current = current.getParentNode();
            } else if (caseInsensitive) {
                var expected = (attrvalue || '').toLowerCase();
                while (current && (current.attr[attrname] || '').toLowerCase() !== expected) {
                    current = current.getParentNode();
                }
            } else {
                while (current && current.attr[attrname] != attrvalue) {
                    current = current.getParentNode();
                }
            }
            return current || null;
        }
        getInheritedAttributes(attrname) {
            if (attrname) {
                var current = this;
                while (current && !current.attr[attrname]) current = current.getParentNode();
                return current ? current.attr[attrname] : null;
            }
            var inherited = {};
            var parentNode = this.getParentNode();
            if (parentNode) {
                inherited = parentNode.stopInherite ?
                    Object.assign(inherited, parentNode.attr) :
                    parentNode.getInheritedAttributes();
            }
            return Object.assign(inherited, this.attr);
        }
        setParentBag(parentbag) {
            this._parentbag = parentbag;
            this.parentBag = parentbag;
            if (this._value instanceof gnr.GnrBag) this._value.setBackRef(this, parentbag);
        }
        getFullpath(mode, root) {
            var parentBag = this.getParentBag();
            if (!parentBag) return '';
            var segment;
            if (mode === '#' || mode === '##') {
                segment = parentBag.getNodes().indexOf(this);
                if (mode === '##') segment = '#' + segment;
            } else {
                segment = this.label;
                if (parentBag.getNode(segment) !== this) {
                    segment = '#' + parentBag.getNodes().indexOf(this);
                }
            }
            var parentPath = parentBag.getFullpath(mode, root);
            return parentPath ? parentPath + '.' + segment : String(segment);
        }
        getStaticValue() { return this.staticValue; }
        setStaticValue(value) { this.staticValue = value; }
        setResolver(resolver) {
            this.resolver = resolver || null;
            if (resolver) resolver._parentNode = this;
            this._status = 'unloaded';
        }
        getResolver() { return this.resolver; }
        isLoaded() { return this._status === 'loaded'; }
        isLoading() { return this._status === 'loading'; }
        isExpired() { return this.resolver ? this.resolver.expired() : false; }
        resetResolver() { this._resolver.reset(); }
        refresh(always) {
            if (always || this.isExpired()) this.getValue('reload');
        }
        clearValue(doTrigger) {
            this.setValue(null, doTrigger);
            return this;
        }
        getAttr(label, defaultValue) {
            if (!label) return this.attr;
            return label in this.attr ? this.attr[label] : (defaultValue || null);
        }
        hasAttr(label, value) {
            if (!(label in this.attr)) return false;
            return value ? this.attr[label] == value : true;
        }
        replaceAttr(attributes) {
            this.attr = {};
            this.setAttr(attributes);
        }
        setAttribute(label, value, doTrigger) {
            var attributes = {};
            attributes[label] = value;
            return this.setAttr(attributes, doTrigger, '*', label);
        }
        updAttributes(attributes, doTrigger) {
            return this.setAttr(attributes, doTrigger, true);
        }
        delAttr(attributes) {
            return super.delAttr(...(Array.isArray(attributes) ? attributes : [attributes]));
        }
        parentshipLevel(node) {
            if (this === node) return 0;
            var parentNode = this.getParentNode();
            var level = parentNode ? parentNode.parentshipLevel(node) : -1;
            return level >= 0 ? level + 1 : level;
        }
        getFormattedValue(kwargs, mode) {
            kwargs = kwargs || {};
            var value = this.getValue(mode);
            kwargs.joiner = kwargs.joiner || '<br/>';
            kwargs.omitEmpty = 'omitEmpty' in kwargs ? kwargs.omitEmpty : true;
            if (value instanceof gnr.GnrBag) {
                value = this.attr._autoTable ?
                    value.asHtmlTable(Object.assign(kwargs, {headers: true, cells: true})) :
                    value.getFormattedValue(kwargs, mode);
            } else {
                value = this.attr._formattedValue || this.attr._displayedValue || value;
            }
            if (isNullOrBlank(value) && kwargs.omitEmpty !== false) return '';
            return (this.attr._valuelabel || this.attr.name_long || stringCapitalize(this.label)) +
                ': ' + _F(value, null, this.attr.dtype);
        }

        _toXmlBlock(kwargs) {
            var nodeValue = this.getResolver() ? this.getValue('static') : this.getValue();
            if (nodeValue instanceof gnr.GnrBag) {
                return xml_buildTag(this.label, nodeValue.toXmlBlock(kwargs),
                    Object.assign({_T: 'bag'}, this.getAttr()), true);
            }
            return xml_buildTag(this.label, nodeValue, this.getAttr());
        }

        toJSONString() {
            return {label: this.label, value: this._value, attr: this.attr}.toJSONString();
        }

        doWithValue(callback, kwargs) {
            var value = this.getValue('', kwargs);
            return value instanceof dojo.Deferred ? value.addCallback(callback) : callback(value);
        }
    };
    Object.assign(gnr.GnrBagNode.prototype, {
        declaredClass: 'gnr.GnrBagNode',
        _counter: [0]
    });
    makeMethodsEnumerable(gnr.GnrBagNode.prototype);

    gnr.GnrBag = class GnrBag extends StandaloneBag {
        constructor(source, kwargs) {
            super();
            this._parentnode = null;
            this._symbols = null;
            this._subscribers = {};
            if (source) {
                if (typeof source === 'string' && source.trim().charAt(0) === '<') {
                    this.fillFrom(StandaloneBag.fromXml(source, kwargs || {}));
                    this._normalizeLegacyXml();
                } else {
                    this.fillFrom(source);
                }
            }
        }

        get _nodes() { return this.__nodes; }
        set _nodes(value) {
            if (value instanceof NodeContainer) {
                this.__nodes = value;
                value._parentBag = this;
                return;
            }
            var container = new NodeContainer();
            (value || []).forEach(function(node) {
                container.splice(container.length, 0, node);
            });
            container._parentBag = this;
            container.forEach(function(node) { node.setParentBag(this); }, this);
            this.__nodes = container;
        }

        get nodeClass() { return this._nodeFactory || gnr.GnrBagNode; }
        _normalizeLegacyXml(clsdict) {
            this._nodes.forEach(function(node) {
                Object.keys(node.attr).forEach(function(key) {
                    var value = node.attr[key];
                    if (typeof value === 'string' && value.indexOf('::') >= 0) {
                        node.attr[key] = convertFromText(value);
                    }
                });
                var dtype = node.attr._T;
                if (dtype) {
                    delete node.attr._T;
                    if (!(node._value instanceof StandaloneBag)) {
                        node._value = convertFromText(node._value, dtype);
                        if (dtype === 'H') node.attr.dtype = dtype;
                    }
                }
                var hasResolvedBranch = node._value instanceof StandaloneBag;
                var resolvedInfo = node.attr._resolvedInfo;
                if (resolvedInfo && typeof resolvedInfo === 'object') {
                    delete node.attr._resolvedInfo;
                    Object.assign(node.attr, resolvedInfo);
                }
                if (node.attr._resolver && genro.rpc && genro.rpc.remoteResolver) {
                    try {
                        var resolverParameters = node.attr._resolver;
                        if (typeof resolverParameters === 'string') {
                            try {
                                resolverParameters = JSON.parse(resolverParameters);
                            } catch (parseError) {
                                resolverParameters = genro.evaluate(resolverParameters);
                            }
                        }
                        if (resolverParameters && resolverParameters.kwargs) {
                            var cacheTime = Object.hasOwn(node.attr, 'cacheTime') ?
                                node.attr.cacheTime : resolverParameters.kwargs.cacheTime;
                            resolverParameters.cacheTime = 0;
                            var remoteResolver = genro.rpc.remoteResolver('resolverRecall', {
                                resolverPars: resolverParameters
                            }, {cacheTime: cacheTime});
                            node.setResolver(remoteResolver);
                            if (hasResolvedBranch) {
                                node._status = 'loaded';
                                remoteResolver.lastUpdate = new Date();
                            }
                            delete node.attr._resolver;
                        }
                    } catch (error) {
                        // Unknown descriptions remain inert in node attributes.
                    }
                } else if (node.attr._resolver_name && genro.getRelationResolver) {
                    var relationResolver = genro.getRelationResolver(node.attr,
                        node.attr._resolver_name, this);
                    node.setResolver(relationResolver);
                    if (hasResolvedBranch) {
                        node._status = 'loaded';
                        relationResolver.lastUpdate = new Date();
                    }
                    delete node.attr._resolver_name;
                }
                if (node._value instanceof StandaloneBag) {
                    var className = node.attr.__cls;
                    if (className) delete node.attr.__cls;
                    var ChildClass = className && clsdict && clsdict[className];
                    var child = new (ChildClass || this.constructor)();
                    child.fillFrom(node._value);
                    node._value = child;
                    child._normalizeLegacyXml(clsdict);
                }
            }, this);
        }
        fromXmlDoc(source, clsdict) {
            var parsed;
            if (typeof source === 'string') {
                parsed = StandaloneBag.fromXml(source);
            } else {
                var root = source.nodeType === 9 ?
                    (source.documentElement || source.lastChild) : source;
                parsed = StandaloneBag._xmlElementToBag(root);
            }
            this.fillFrom(parsed);
            this._normalizeLegacyXml(clsdict);
            return this;
        }
        newNode(parentbag, label, value, attr, resolver) {
            return new this.nodeClass(parentbag, label, value, attr, resolver);
        }
        // Genro consumers expect rows even when selecting a single field.
        digest(what, condition, asColumns) {
            var columns = typeof condition === 'boolean' ? condition : asColumns;
            var result = super.digest(what, condition, asColumns);
            return !columns && typeof what === 'string' && !what.includes(',') ?
                result.map(value => [value]) : result;
        }
        attributes() { if (this.parentNode) return this.parentNode.attr; }
        resolver() { if (this.parentNode) return this.parentNode.resolver; }
        len() { return this.length; }
        getParent() { return this.parent; }
        setParent(parent) { this.parent = parent; }
        getParentNode() { return this.parentNode; }
        setParentNode(node) {
            this._parentnode = node;
            this.parentNode = node;
        }
        setBackref(node, parent) {
            this._parentnode = node || null;
            super.setBackref(node || null, parent || null);
            this._nodes.forEach(function(childNode) { childNode.setParentBag(this); }, this);
        }
        setBackRef(node, parent) { return this.setBackref(node, parent); }
        hasBackRef() { return this.backref; }
        getBackRef() { return this.backref; }

        getItem(path, dflt, mode, optkwargs) {
            if (!path) return this;
            var finalize = function(result) {
                return result.value instanceof gnr.GnrBag ?
                    result.value.get(result.label, dflt, mode, optkwargs) :
                    (dflt == null ? null : dflt);
            };
            var result = this.htraverse(path, false);
            return result instanceof dojo.Deferred ? result.addCallback(finalize) : finalize(result);
        }

        htraverse(pathlist, autocreate) {
            var curr = this;
            if (typeof pathlist === 'string') {
                var suffix = pathlist.match(/(.*?)([?|~])(.*)/);
                var cleanPath = (suffix ? suffix[1] : pathlist).replace(/\.\.\//g,
                    '#parent.');
                pathlist = smartsplit(cleanPath, '.');
                if (suffix) {
                    pathlist[pathlist.length - 1] += suffix[2] + suffix[3];
                }
            } else {
                pathlist = (pathlist || []).slice();
            }
            if (!pathlist.length) return {value: curr, label: ''};
            var label = pathlist.shift();
            while (label === '#parent' && pathlist.length) {
                curr = curr && curr.getParent();
                label = pathlist.shift();
            }
            if (!curr) return {value: null, label: null};
            if (!pathlist.length) return {value: curr, label: label};
            var index = curr.index(label);
            if (index < 0) {
                if (!autocreate) return {value: null, label: null};
                if (label.charAt(0) === '#') label = label.replace('#', '_');
                curr.setItem(label, new curr.constructor(), null,
                    {doTrigger: 'autocreate'});
                index = curr.index(label);
            }
            var finalize = function(next) {
                if (!(next instanceof gnr.GnrBag) && autocreate) {
                    next = new curr.constructor();
                    curr._nodes[index].setValue(next, false);
                }
                return next instanceof gnr.GnrBag ?
                    next.htraverse(pathlist, autocreate) :
                    {value: next, label: pathlist.join('.')};
            };
            var next = curr._nodes[index].getValue();
            return next instanceof dojo.Deferred ? next.addCallback(finalize) : finalize(next);
        }


        index(label) {
            if (!label) return -1;
            if (label.charAt(0) === '#') {
                if (label.indexOf('=') >= 0) {
                    var parts = label.slice(1).split('=');
                    var key = parts[0] || 'id';
                    var value = convertFromText(parts.slice(1).join('='));
                    for (var i = 0; i < this._nodes.length; i++) {
                        if (this._nodes[i].attr[key] == value) return i;
                    }
                    return -1;
                }
                var index = parseInt(label.slice(1));
                return index >= 0 && index < this._nodes.length ? index : -1;
            }
            for (var i = 0; i < this._nodes.length; i++) {
                if (this._nodes[i].label === label) return i;
            }
            return -1;
        }




        _pop(label, doTrigger) {
            if (doTrigger == null) doTrigger = true;
            var index = this.index(label);
            if (index < 0) return null;
            var node = this._nodes[index];
            // Legacy replaces the backing array so callers can safely remove
            // consecutive nodes while iterating the previous `_nodes` value.
            this._nodes = this._nodes.filter(function(item, itemIndex) {
                return itemIndex !== index;
            });
            if (this.backref && doTrigger) {
                this._onNodeDeleted(node, index, null, doTrigger, this);
            }
            return node;
        }

        concat(otherBag) {
            if (!otherBag) return;
            otherBag._nodes.forEach(function(node) {
                node.setParentBag(this);
                this._nodes.splice(this._nodes.length, 0, node);
            }, this);
        }
        clear(triggered) {
            if (!triggered) {
                this._nodes.splice(0, this._nodes.length);
                return;
            }
            while (this._nodes.length) {
                var index = this._nodes.length - 1;
                var node = this._nodes[index];
                this._nodes.splice(index, 1);
                if (this.backref) this._onNodeDeleted(node, index);
            }
        }
        fireItem(path, value, attributes, reason) {
            value = value == null ? true : value;
            this.setItem(path, value, attributes, {doTrigger: reason == null ? true : reason,
                fired: true});
            this.setItem(path, null, attributes, {doTrigger: false});
        }
        asObj(formatAttributes) {
            var result = {};
            this._nodes.forEach(function(node) {
                result[node.label] = node._resolver ? '**' : node.getValue();
            });
            Object.keys(formatAttributes || {}).forEach(function(key) {
                result[key] = asText(result[key], formatAttributes[key]);
            });
            return result;
        }
        setCallBackItem(path, callback, parameters, kwargs) {
            kwargs = kwargs || {};
            kwargs.method = callback;
            kwargs.parameters = parameters;
            this.setItem(path, new gnr.GnrBagCbResolver(kwargs), kwargs);
        }
        getRoot() {
            return this.parent ? this.parent.getRoot() : this;
        }
        getFullpath(mode, root) {
            if (root === true) root = this.getRoot().getItem('#0');
            if (!this.parent || this === root) return '';
            var node = this.parentNode;
            var segment = node.label;
            if (mode === '#' || mode === '##') {
                segment = String(this.parent.getNodes().indexOf(node));
                if (mode === '##') segment = '#' + segment;
            }
            var parentPath = this.parent.getFullpath(mode, root);
            return parentPath ? parentPath + '.' + segment : segment;
        }
        subscribe(subscriberId, callbacks) {
            callbacks = callbacks || {};
            return super.subscribe(subscriberId, {
                update: callbacks.upd || callbacks.update || callbacks.any,
                insert: callbacks.ins || callbacks.insert || callbacks.any,
                delete: callbacks.del || callbacks.delete || callbacks.any
            });
        }
        unsubscribe(subscriberId) {
            return super.unsubscribe(subscriberId, {any: true});
        }
        _onNodeChanged(node, pathlist, event, oldvalue, attrsDiff, reason) {
            pathlist = pathlist || [node.label];
            var changedAttr = attrsDiff ? Object.keys(attrsDiff)[0] : null;
            var oldattr = {};
            if (attrsDiff) {
                Object.keys(attrsDiff).forEach(function(key) { oldattr[key] = attrsDiff[key].old; });
            }
            var payload = {
                node: node,
                pathlist: pathlist,
                evt: 'upd',
                base: this,
                reason: reason,
                value: node._value,
                oldvalue: oldvalue,
                updattr: event !== 'upd_value',
                changedAttr: node._legacyChangedAttr || changedAttr,
                changedAttributes: attrsDiff ? Object.keys(attrsDiff).reduce(function(result, key) {
                    if (attrsDiff[key].new !== null) result[key] = true;
                    return result;
                }, {}) : undefined,
                fired: node._legacyFired,
                oldattr: oldattr
            };
            if (event !== 'upd_attrs') payload.updvalue = true;
            Object.keys(this._updSubscribers).forEach(function(key) {
                this._updSubscribers[key](payload);
            }, this);
            if (this.parent && this.parentNode) {
                this.parent._onNodeChanged(node, [this.parentNode.label].concat(pathlist),
                    event, oldvalue, attrsDiff, reason);
            }
        }
        _onNodeInserted(node, index, pathlist, reason, where) {
            pathlist = pathlist || [node.label];
            where = where || this;
            var payload = {node: node, where: where, base: this, pathlist: pathlist,
                ind: index, evt: 'ins', reason: reason};
            Object.keys(this._insSubscribers).forEach(function(key) {
                this._insSubscribers[key](payload);
            }, this);
            if (this.parent && this.parentNode) {
                this.parent._onNodeInserted(node, index,
                    [this.parentNode.label].concat(pathlist), reason, where);
            }
        }
        _onNodeDeleted(node, index, pathlist, reason, where) {
            // Standalone _pop passes reason as the third argument; the legacy
            // notification API reserves that position for the bubbling path.
            if (pathlist != null && !Array.isArray(pathlist)) {
                reason = pathlist;
                pathlist = null;
            }
            pathlist = pathlist || [node.label];
            where = where || this;
            var payload = {node: node, where: where, base: this, pathlist: pathlist,
                ind: index, evt: 'del', reason: reason};
            Object.keys(this._delSubscribers).forEach(function(key) {
                this._delSubscribers[key](payload);
            }, this);
            if (this.parent && this.parentNode) {
                this.parent._onNodeDeleted(node, index,
                    [this.parentNode.label].concat(pathlist), reason, where);
            }
        }
    };
    Object.assign(gnr.GnrBag.prototype, {
        declaredClass: 'gnr.GnrBag',
        _nodeFactory: gnr.GnrBagNode
    });
    // Compatibility entry points retained for existing applications.
    Object.assign(gnr.GnrBag.prototype, {
asHtmlTable: function(kw, mode){
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
    },

asNestedTable: function(kw,mode){
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
    },

__str2__: function(mode) {

        var mode = mode || 'static';
        var outlist = [];
        var el = null;
        var attrString = '';
        var j = 0;
        var key;
        var value = null;

        for (var i = 0; i < this._nodes.length; i++) {
            el = this._nodes[i];
            for (key in el.attr) {
                attrString = attrString + key + '=' + el.attr[key] + ' ';
            }
            if (attrString != '') {
                attrString = '||' + attrString + '||';
            }
            value = el.getValue(mode); //verificare getValue
            if (isBag(value)) {
                outlist.push(i + '-(' + value.declaredClass + ') ' + el.label + ': ' + attrString);

                if (el.visited) {
                    innerbagstr = 'visited at: ' + el.label;
                } else {
                    el.visited = true;
                    var inner = value.__str2__(mode).split('\n');
                    var auxlist = [];
                    for (var u = 0; u < inner.length; u++) {
                        var line = inner[u];
                        auxlist.push('----' + line);
                    }

                    var innerbagstr = auxlist.join('\n');
                }
                outlist.push(innerbagstr);
            } else {
                outlist.push(i + '-(' + (value.declaredClass || typeof value) + ') ' + el.label + ': ' + value.toString() + ' ' + attrString);

            }
        }
        return outlist.join('<br/>');
    },

__str__: function(mode) {

        mode = mode || 'static';
        var outlist = [];
        var el = null;
        var attrString = '';
        var j = 0;
        var key;
        var value = null;


        for (var i = 0; i < this._nodes.length; i++) {
            el = this._nodes[i];
            for (var key in el.attr) {
                attrString = attrString + key + '=' + el.attr[key] + ' ';
            }
            if (attrString != '') {
                attrString = '<' + attrString + '>';
            }
            value = el.getValue(mode); //verificare getValue
            if (isBag(value)) {
                outlist.push(i + '-(' + value.declaredClass + ') ' + el.label + ': ');

                if (el.visited) {
                    innerbagstr = 'visited at: ' + el.label;
                } else {
                    el.visited = true;
                    var inner = value.__str__(mode).split('\n');
                    var auxlist = [];
                    for (var u = 0; u < inner.length; u++) {
                        var line = inner[u];
                        auxlist.push('----' + line);
                    }

                    var innerbagstr = auxlist.join('\n');
                }
                outlist.push(innerbagstr);
            } else {
                var v = convertToText(value);
                outlist.push(i + '-(' + v[0] + ') ' + el.label + ': ' + v[1] + ' ' + attrString);

            }
        }
        return outlist.join('\n');
    },

asString: function() {
        return this.__str2__();
    },

asObjList: function(labelAs, formatAttributes) {
        formatAttributes = formatAttributes || {};
        var nodes = this._nodes;
        var result = [];
        for (var i = 0; i < nodes.length; i++) {
            var item = nodes[i].getValue().asObj(formatAttributes);
            if (labelAs) {
                item[labelAs] = nodes[i].label;
            }
            result.push(item);
        }
        return result;
    },

moveNode: function(fromPos, toPos, doTrigger) {
        if (toPos < 0) {
            return;
        }
        var doTrigger = (doTrigger == null) ? true : doTrigger;
        var destlabel = this.getNodes()[toPos].label;
        if (fromPos instanceof Array && fromPos.length > 1) {
            fromPos.sort();
            var delta = (fromPos[0] < toPos) ? 1 : 0;
            var popped = [];
            for (var i = fromPos.length - 1; i >= 0; i--) {
                popped.push(this._pop('#' + fromPos[i], doTrigger));
            }
            var toPos = this.index(destlabel) + delta;
            var bag = this;
            dojo.forEach(popped, function(n) {
                bag._insertNode(n, toPos, doTrigger);
            });
        } else {
            if (fromPos instanceof Array) {
                fromPos = fromPos[0];
            }
            if (toPos != fromPos) {
                var node = this._pop('#' + fromPos, doTrigger);
                // if(toPos>fromPos){
                //     toPos=toPos-1;
                // }
                this._insertNode(node, toPos, doTrigger);
            }
        }


    },

merge: function() {
    },

_getNode: function(label, autocreate, _default) {
        var p = this.index(label);
        var node = null;
        if (p >= 0) {
            node = this._nodes[p];
        }
        else if (autocreate) {
            node = this.newNode(this, label, /*value=*/ _default);
            var i = this._nodes.length;
            this._nodes = Array.from(this._nodes).concat(node);
            if (this._backref) {
                this.onNodeTrigger({'evt':'ins','node':node,'where':this,'ind':i,'reason':'autocreate'});
            }
        }
        return node;
    },

pathsplit: function() {
    },

rowchild: function(tag,kw){
        var label;
        if(tag.startsWith('#')){
            label = kw[tag.slice(1)];
        }else{
            label = tag+'_'+genro.time36Id();
        }
        genro.assert(label,'Missing label in this node');
        this.setItem(label,null,kw);
    },

set: function(label, value, _attributes, kwargs) {
        if (!kwargs) {
            var kwargs = {};
        }
        var resolver = null;
        var _duplicate = kwargs._duplicate || false;
        var _updattr = kwargs._updattr || false;
        var _doTrigger = true;
        if ('doTrigger' in kwargs) {
            _doTrigger = kwargs.doTrigger;
        }
        if (value instanceof gnr.GnrBagResolver) {
            resolver = value;
            value = null;
            if (objectSize(resolver.attributes) >= 0) {
                _attributes = objectUpdate({}, _attributes);
                _attributes = objectUpdate(_attributes, resolver.attributes);
            }
        }

        var i = _duplicate?-1:this.index(label);
        if (i < 0) {
            if ((label != '#id') && (label[0] == '#')) {
                //raise BagException ('Not existing index in #n syntax')
                return null;
            }
            else {
                var nodeToInsert = this.newNode(this, label, value, _attributes, resolver);
                kwargs._new_position = this._insertNode(nodeToInsert, kwargs._position, _doTrigger);
                kwargs._new_label = nodeToInsert.label;
                return nodeToInsert;
            }
        }
        else {
            var node = this._nodes[i];
            if (resolver) {
                node.setResolver(resolver);
            }
            if(kwargs.lazySet && isEqual(node._value,value)){
                var changedAttrs = changedAttrKeys(node.attr,_attributes,_updattr);
                if(!changedAttrs.length){
                    return node;
                }
                //same value, changed attributes: only the attribute listeners have to be notified.
                //changedAttr comes from here because setAttr cannot default it without changing the
                //callers that read its absence as a whole-attribute change
                node.setAttr(_attributes, _doTrigger, _updattr,
                             changedAttrs.length==1?changedAttrs[0]:null);
                return node;
            }
            node.setValue(value, _doTrigger, _attributes, _updattr,kwargs.fired);
            return node;
        }
    },

_insertNode: function(node, position, _doTrigger) {
        var n = null;
        var label;
        if (typeof(position) == 'number') {
            n = position;
        }
        else if (position == 0 || position == '<') {
            n = 0;
        } else if (!position || position == '>') {
            n = -1;
        }
        else if (position.charAt(0) == '#') {
            n = parseInt(position.slice(1));
        }
        else {
            if (position.charAt(0) == '<' || position.charAt(0) == '>') {
                label = position.slice(1);
                position = position.charAt(0);
            }
            else {
                label = position;
                position = '<';
            }
            if (label.charAt(0) == '#') {
                n = parseInt(label.slice(1));
            }
            else {
                n = this.index(label);
            }
            if (position == '>' && n >= 0) {
                n = n + 1;
            }
        }
        if (n < 0) {
            n = this._nodes.length;
        }

        this._nodes.splice(n, 0, node);

        if (this._backref && _doTrigger) {
            this.onNodeTrigger({'evt':'ins','node':node,'where':this,'ind':n, 'reason':_doTrigger});
        }
        return n;
    },

backrefOk: function(){
        return this._parentnode._parentbag===this._parent; 
    },

runTrigger: function(kw) {
        var subscribers = {upd: this._updSubscribers,
            ins: this._insSubscribers, del: this._delSubscribers}[kw.evt] || {};
        Object.keys(subscribers).forEach(function(key) { subscribers[key](kw); });
    },

onNodeTrigger: function(/*node,where,ind,pathlist*/kw) {
        //genro.debug('onNodeTrigger:',kw.evt+' - '+kw.node.label );
        kw.pathlist = kw.pathlist || [kw.node.label];
        kw.base = this;
        this.runTrigger(kw);
        if (this._parent != null) {
            kw.pathlist = [this._parentnode.label].concat(kw.pathlist);
            this._parent.onNodeTrigger(kw);
        }
    },

toXmlBlock: function(kwargs) {
        var result = new Array();
        var nodes = this._nodes;
        for (var i = 0; i < nodes.length; i++) {
            result.push(nodes[i]._toXmlBlock(kwargs));
        }
        return result.join('\n');
    },

formula: function(formula, kwargs) {
        this.setBackRef();
        if (this._symbols == null) {
            this._symbols = {};
        }
        var path = 'formula:' + formula;
        var formula = this._symbols[path] || formula;
        var result = new gnr.GnrBagFormula(this, formula, this._symbols, kwargs);
        return result;

    },

defineSymbol: function(kwargs) {
        if (this._symbols == null) {
            this._symbols = {};
        }
        objectUpdate(this._symbols, fromKwargs(kwargs));

    },

defineFormula: function(kwargs) {
        var path = null;
        if (this._symbols == null) {
            this._symbols = {};
        }
        if (!(kwargs != null)) {
            kwargs = objectUpdate({}, kwargs);
        }
        for (var key in kwargs) {
            path = 'formula:' + key;
            this._symbols[path] = kwargs[key];
        }
    },

get_modified: function() {
        return this._modified;
    },

set_modified: function(value) {
        if (value == null) {
            this._modified = null;
            this.unsubscribe('modify__');
        }
        else if (this._modified == null) {
            this.subscribe('modify__', {'any':dojo.hitch(this, '_setModified')});
        }
        this._modified = value;
    },

_setModified: function() {
        this._modified = true;
    },

getIndex: function() {
        var path = [];
        var resList = [];
        var exploredNodes = [this];
        this._deepIndex(path, resList, exploredNodes);
        return resList;
    },

_deepIndex: function(path, resList, exploredNodes) {
        var node, v;
        for (var i = 0; i < this._nodes.length; i++) {
            node = this._nodes[i];
            v = node.getValue();
            resList.push([path.concat(node.label), node]);
            if (v && typeof v._deepIndex === 'function') {
                if (arrayIndexOf(exploredNodes, v) < 0) {
                    exploredNodes.push(v);
                    v._deepIndex(path.concat(node.label), resList, exploredNodes);
                }
            }
        }
    },

getIndexList: function(asText) {
        var l = this.getIndex();
        result = [];
        for (var i = 0; i < l.length; i++) {
            result.push(l[i][0].join('.'));
        }
        if (asText) {
            return result.join('\n');
        } else {
            return result;
        }
    },

doWithItem: function(path, cb, dflt) {
        var value = this.getItem(path, dflt);
        if (value instanceof dojo.Deferred) {
            //genro.debug('Deferred adding callback (bag.doWithItem) :'+path);
            return value.addCallback(cb);
        } else {
            return cb(value);
        }
    }
    });
    // Preserve the Genro client contracts where standalone method signatures differ.
    Object.assign(gnr.GnrBag.prototype, {
        sum: function(path,strictmode) {
        var result = 0;
        var n;
        path = path || '#v';
        if (path) {
            var l = this.digest(path);
            if(strictmode && l.some(values=>isNullOrBlank(values[0]))){
                return;
            }
            for (let values of l) {
                n = values[0];
                if (typeof n == 'number') {
                    result += n;
                }else if(typeof n == 'boolean'){
                    result += n===true?1:0;
                }
            }
        }
        return result;
    },
        sort: function(pars) {
        //pars None: label ascending
        var innerCmp = function(a, b, reverse, caseInsensitive) {
            if (caseInsensitive) {
                if (typeof(a) == 'string') {
                    var a = a.toLowerCase();
                }
                if (typeof(b) == 'string') {
                    var b = b.toLowerCase();
                }
            }
            if (a == b) {
                return 0;
            }
            else if (reverse) {
                if (a < b) {
                    return 1;
                }
                else {
                    return -1;
                }
            } else {
                if (a > b) {
                    return 1;
                }
                else {
                    return -1;
                }
            }
        };
        var cmp = function(a, b, reverse, caseInsensitive){
            if(a===null && b===null){
                return 0;
            }
            if (a===null || b===null){
                var r = a===null?-1:1;
                return reverse?r*-1:r;
            }
            if((a instanceof Date) && (b instanceof Date)){
                a = a.valueOf();
                b = b.valueOf();          
            }
            return innerCmp(a, b, reverse, caseInsensitive);
        }
        var sortNodes = function(compare) {
            var nodes = Array.from(this._nodes);
            nodes.sort(compare);
            this._nodes = nodes;
        }.bind(this);
        var pars = pars || '#k:a';
        var level,what,mode,reverse,caseInsensitive;
        var levels = pars.split(',');
        levels.reverse();
        for (var i = 0; i < levels.length; i++) {
            level = levels[i];
            if (level.indexOf(':') >= 0) {
                level = level.split(':');
                what = level[0];
                mode = level[1];
            } else {
                what = level;
                mode = 'a';
            }
            what = stringStrip(what);
            mode = stringStrip(mode).toLowerCase();
            if (stringEndsWith(mode, '*')) {
                caseInsensitive = true;
                mode = mode.slice(0, -1);
            } else {
                caseInsensitive = false;
            }
            reverse = ! ((mode == 'a') || (mode == 'asc') || (mode == '>'));

            if (what == '#k') {
                sortNodes(function(a, b) {
                    return cmp(a.label, b.label, reverse, caseInsensitive);
                });
            } else if (what == '#v') {
                sortNodes(function(a, b) {
                    return cmp(a.getValue(), b.getValue(), reverse, caseInsensitive);
                });
            } else if (what.indexOf('#a') >= 0) {
                var attrname = what.slice(3);
                sortNodes(function(a, b) {
                    return cmp(a.getAttr(attrname), b.getAttr(attrname), reverse, caseInsensitive);
                });
            } else {
                sortNodes(function(a, b) {
                    return cmp(a.getValue().getItem(what), b.getValue().getItem(what), reverse, caseInsensitive);
                });
            }
        }
    },
        asDict: function(recursive,excludeNullValues) {
        var isArray = Array.prototype.some.call(this._nodes, function(n){return n.attr._autolist});
        var node,value;
        var result = isArray?[]:{};
        for (var i = 0; i < this._nodes.length; i++) {
            node = this._nodes[i];
            value = node.getValue();

            if(excludeNullValues){
                if(value===null || value instanceof gnr.GnrBag && value.len()===0){
                    continue;
                }
                
            }
            if(recursive && (value instanceof gnr.GnrBag)){
                if(recursive=='flat'){
                    objectUpdate(result,value.asDict(recursive,excludeNullValues));
                    continue;
                }else{
                    value = value.asDict(recursive,excludeNullValues);
                }
                
            }
            if(isArray){
                result.push(value);
            }else{
                if(typeof(value)!='string' || !stringEndsWith(value,'::JS')){
                    result[node.label] = value;
                }
                
            }
        }
        return result;
    },
        deepCopy: function(resolve) { return this.deepcopy(Boolean(resolve)); },
        walk: function (callback, mode, kw, notRecursive) {
        var result;
        var isStatic = isStaticMode(mode);
        var bagnodes = this.getNodes();
        for (var i = 0; ((i < bagnodes.length) && ((result == null)|| (result=='__continue__'))); i++) {
            result = callback(bagnodes[i], kw, i);
            if (result == null && !notRecursive) {
                var value = isStatic ? bagnodes[i]._value : bagnodes[i].getValue(mode);
                if (isBag(value)) {
                    result = value.walk(callback, mode, kw);
                }
            }
        }
        return result;
    },
        forEach: function(callback, mode, kw) {
        this.walk(callback, 'static', kw, true);
    },
        getFormattedValue: function(kw,mode){
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
    },
        pop: function(path, doTrigger) {
        var n = this.popNode(path, doTrigger);
        if(n){
            return n.getValue()
        }
    },
        delItem: function(path, doTrigger) {
        this.pop(path, doTrigger);
    },
        popNode: function(path, doTrigger) {
        var node = this.htraverse(path);
        var obj = node.value;
        var label = node.label;
        if (obj) {
            var n = obj._pop(label, doTrigger);
            if(n){
                return n.orphaned();
            }
        }

    },
        setItem: function(path, value, _attributes, kwargs) {
        if (arguments.length > 4) return StandaloneBag.prototype.setItem.apply(this, arguments);
        if (!kwargs) {
            var kwargs = {};
        }
        if (path == '') {
            if (isBag(value)) {
                for (var i = 0; i < value.getNodes().length; i++) {
                    var node = value.getNodes()[i];
                    var v = node.getResolver() || node.getValue();
                    this.setItem(node.label, v, node.getAttr());
                }
            }
            else if (value instanceof Object) {
                for (var i in value) {
                    this.setItem(i, value[i].valueOf());
                }
            }
            return this;
        }
        else {
            var mynode = this.htraverse(path, /*autocreate*/true);
            var cb = function(mynode, value) {
                var obj = mynode.value;
                var label = mynode.label;
                if (label.indexOf('?') >= 0) {
                    var splittedlabel = label.split('?');
                    label = splittedlabel[0];
                    var attr = splittedlabel[1];
                    var node = obj.getNode(label, false, true);
                    var auxattr = objectUpdate({}, _attributes);
                    auxattr[attr] = value;
                    var changedAttrs = changedAttrKeys(node.attr,auxattr,'*');
                    if(kwargs.lazySet && !changedAttrs.length){
                        return node;
                    }
                    var _doTrigger = true;
                    if ('doTrigger' in kwargs) {
                        _doTrigger = kwargs.doTrigger;
                    }
                    node.setAttr(auxattr, _doTrigger, '*',
                                 changedAttrs.length>1 ? null : (changedAttrs.length ? changedAttrs[0] : attr));
                    return node;
                }
                else {
                    return obj.set(label, value, _attributes, kwargs);
                }
            };
            if (mynode instanceof dojo.Deferred) {
                mynode.addCallback(cb, value);
            }
            else {
                return cb(mynode, value);
            }

        }
    },
        addItem: function(path, value, _attributes, kwargs) {
        if (!kwargs) {
            var kwargs = {};
        }
        kwargs['_duplicate'] = true;
        return this.setItem(path, value, _attributes, kwargs);
    },
        get: function(label, dflt, mode,optkwargs) {
        var result = null;
        var currnode = null;
        var currvalue = null;
        var getter;
        var m;
        if (!label) {
            currnode = this._parentnode;
            currvalue = this;
        }
        else if (label == '#parent') {
            currnode = this._parent.getNode();
        }
        else {
            m = label.match(/(.*?)([?|~])([^?|^=]*)(\??)(.*)/);

            if(m){
                label = m[1];
            } 
            var i = this.index(label);
            if (i < 0) {
                return dflt;
            }
            else {
                currnode = this._nodes[i];
            }
        }
        if (currnode) {
            currvalue = currnode.getValue(mode,optkwargs);
        }
        if (!m) {
            return currvalue;
        }
        var finalize = function(currvalue) {
            var expr = m[5];
            if(m[2]=='?'){
                var attrname = m[3];
                if(attrname){
                    if (attrname == '#attr') {return currnode.attr;}
                    if (attrname == '#keys') {return currvalue.keys();}
                    if (attrname == '#node') {return currnode;}
                    if (attrname.indexOf('#digest:')==0) {return currvalue.digest(attrname.split(':')[1]);}
                    currvalue = currnode.getAttr(attrname)
                }else if(!expr){
                    return currnode.attr;
                }
            }else if(m[2]=='~'){
                currvalue = (currnode._value instanceof gnr.GnrBag)? currnode._value.getItem(m[3]):currnode.getAttr(m[3]);
            }
            if(!expr){
                return currvalue;
            }
            if (expr.indexOf('=') == 0) {
                genro.__evalAuxValue = currvalue;
                expr = expr.slice(1).replace(/#v/g, 'genro.__evalAuxValue');
                currvalue = dojo.eval(expr);
                return currvalue;
            }        
        };
        if (currvalue instanceof dojo.Deferred) {
            //genro.debug('Deferred adding callback (bag.get) :'+label);
            return currvalue.addCallback(finalize);
        }
        else {
            return finalize(currvalue);
        }
    },
        getNode: function(path, asTuple, autocreate, _default) {
        if (!path) {
            return this.getParentNode();
        }
        /*if (path%1==0){ 
         alert('path intero')
         return this._nodes[path];
         }*/
        var mynode = this.htraverse(path, autocreate);
        /*if (mynode instanceof dojo.Deferred) {
            // console.error('deferred');
        }*/
        var obj = mynode.value;
        var label = mynode.label;
        var node = null;
        if (obj) {
            if (label.indexOf('?') >= 0) {
                var splittedlabel = label.split('?');
                label = splittedlabel[0];
                node = obj._getNode(label, autocreate);
                if (_default) {
                    node.attr[splittedlabel[1]] = _default;
                }
            } else {
                node = obj._getNode(label, autocreate, _default);
            }

            if (asTuple == true) {
                return {"obj":obj, "node":node};
            }
        }
        return node;
    },
        fillFrom: function(source,kw) {
        if (source instanceof StandaloneBag && !(source instanceof gnr.GnrBag)) {
            source.getNodes().forEach(function(node) {
                var value = node._value;
                if (value instanceof StandaloneBag) {
                    var child = new this.constructor();
                    child.fillFrom(value);
                    value = child;
                }
                this.setItem(node.label, value, Object.assign({}, node.attr));
            }, this);
            return;
        }
        var sourceType = guessDtype(source);
        var dest = this;
        if (sourceType=='AR') {
            var firstElemType = guessDtype(source[0]);
            if(firstElemType=='AR'){
                source.forEach(function(elem,idx){
                    dest.setItem(elem[0],elem[1],elem[2]);
                });
            }else if(firstElemType=='OBJ'){
                source.forEach(function(elem,idx){
                    dest.setItem('r_'+idx,new gnr.GnrBag(elem),{_autolist:true});
                });
            }
        } else if (sourceType=='X') {

            source.forEach(function(node) {
                dest.setItem(node.label, node.getValue(), objectUpdate({}, node.getAttr()));
            });
        }else if(sourceType=='T'){
            //always xml string
            var parser=new window.DOMParser();
            this.fromXmlDoc(parser.parseFromString(source,'text/xml'),genro.clsdict);
        }
        else if (sourceType=='OBJ') {
            for (var k in source) {
                var val = source[k];
                var valType = guessDtype(val);
                if(valType=='FUNC'){
                    continue;
                }else if((valType=='OBJ' || valType=='AR') && !(val instanceof StandaloneNode)){
                    val = new gnr.GnrBag(val);
                }
                this.setItem(k, val);
            }
        }
    }
    });
    Object.assign(gnr.GnrBag.prototype, {
        setAttr: function(path, attr, args) {
        this.getNode(path, false, true).setAttr(attr/*, args questa opzione non l'ho implementata nel gnrnode*/);

    },
        getAttr: function (path, attr, dflt) {
        var node = this.getNode(path);
        if (node != null) {
            return node.getAttr(attr, dflt);
        } else {
            return dflt;
        }
    },
        isEqual: function(otherbag) {
        if (!otherbag) {
            return false;
        }
        if (this == otherbag) {
            return true;
        }
        ;
        if (this._parentnode && otherbag._parentnode) {
            return this._parentnode._id == otherbag._parentnode._id;
        }
        ;
        return false;
    },
        toXml: function(kwargs) {
        if (!kwargs) {
            var kwargs = {};
        }
        var encoding = kwargs['encoding'] || "utf-8";
        var result = '<?xml version="1.0" encoding="' + encoding + '"?>\n';
        result = result + xml_buildTag('GenRoBag', this.toXmlBlock(kwargs), null, true);
        return result;
    },
        clearBackRef: function() {
        var node,value;
        if (this._backref) {
            this._backref = false;
            this._parent = null;
            this._parentnode = null;
            this._parentNode = null;
            for (var i = 0; i < this._nodes.length; i++) {
                node = this._nodes[i];
                value = node.getStaticValue();
                if (isBag(value)) {
                    value.clearBackRef();
                }
            }
        }
    }
    });
    Object.assign(gnr.GnrBag.prototype, {
        getNodeByAttr: function(attr,value,caseInsensitive) {
        var existAttr = arguments.length==1;
        var value = caseInsensitive?value.toLowerCase():value;
        var f = function(n) {
            if(attr in n.attr){
                if(existAttr || (caseInsensitive?((n.attr[attr] || '').toLowerCase()==value):(n.attr[attr]==value))){
                    return n;
                }
            }
        };
        return this.walk(f, 'static');
    },
        getNodeByValue: function(path,value){
        var nodes = this._nodes;
        var n;
        for(var i =0; i<nodes.length; i++){
            n = nodes[i];
            if(n.getValue().getItem(path)===value){
                return n;
            };
        }
        return;
    },
        findNodeById: function(id) {
        var f = function(n) {
            if (n._id == id) {
                return n;
            }
        };
        return this.walk(f, 'static');
    }
    });
    Object.assign(gnr.GnrBag.prototype, {
        getNodes: function(condition/*opzionale*/) {
        return condition?this._nodes.filter(condition):this._nodes;
    },
    });
    makeMethodsEnumerable(StandaloneBag.prototype);
    makeMethodsEnumerable(gnr.GnrBag.prototype);

    gnr.GnrBagResolver = class GnrBagResolver extends StandaloneResolver {
        constructor(kwargs, isGetter, cacheTime, load) {
            super(Object.assign({}, kwargs, {
                cacheTime: cacheTime || 0,
                readOnly: Boolean(isGetter),
                asBag: false
            }));
            this._attributes = {};
            this.setCacheTime(cacheTime || 0);
            this.kwargs = kwargs;
            this.isGetter = isGetter;
            this._pendingDeferred = [];
            if (load) this.load = load;
        }

        resolve(optkwargs, destinationNode) {
            var kwargs = objectUpdate({}, this.kwargs);
            kwargs._destFullpath = destinationNode ?
                destinationNode.getFullpath(null, genro._data) : '';
            objectUpdate(kwargs, optkwargs);
            if (this.isGetter) return this.load(kwargs);
            var finalize = function(value) {
                this._lastUpdate = Date.now();
                return value;
            }.bind(this);
            var result = this.load(kwargs, destinationNode);
            if (result instanceof dojo.Deferred) return result.addCallback(finalize);
            return finalize(result);
        }

        setParentNode(node) { this._parentNode = node; this._node = node; }
        setNode(node) {
            this.setParentNode(node);
            this.onSetResolver(node);
        }
        getParentNode() { return this._parentNode; }
        load(kwargs, callback) {}
        htraverse(kwargs) {
            return this.resolve().htraverse(kwargs.pathlist, kwargs.autocreate);
        }
        keys() { return this.resolve().keys(); }
        items() { return this.resolve().items(); }
        values() { return this.resolve().values(); }
        digest(key) { return this.resolve().digest(key || null); }
        sum(key) { return this.resolve().sum(key || null); }
        contains() { return this.resolve().contains(); }
        len() { return this.resolve().len(); }
        resolverDescription() {
            var value = this.resolve();
            // Standalone Bag adds a tree formatter where legacy inherited Object.toString.
            return value.toString === StandaloneBag.prototype.toString ?
                Object.prototype.toString.call(value) : value.toString();
        }
        getCacheTime() { return this._cacheTime; }
        setCacheTime(value) { this._cacheTime = value; }
        get lastUpdate() {
            return this._lastUpdate === null ? null : new Date(this._lastUpdate);
        }
        set lastUpdate(value) {
            this._lastUpdate = value instanceof Date ? value.getTime() : value;
        }
        expired(kwargs) {
            if (this.cacheTime < 0) return this.lastUpdate == null;
            return (new Date() - (this.lastUpdate || new Date(0))) / 1000 > this.cacheTime;
        }
        getAttr() { return this._attributes; }
        setAttr(attributes) { objectUpdate(this._attributes, attributes); }
        meToo(callback) {
            var deferred = new dojo.Deferred();
            deferred.addCallback(callback);
            this._pendingDeferred.push(deferred);
            return deferred;
        }
        runPendingDeferred(pending) {
            pending.forEach(function(deferred) { deferred.callback(); });
        }
        cancelMeToo() {
            var pending = this._pendingDeferred || [];
            this._pendingDeferred = [];
            pending.forEach(function(deferred) { deferred.cancel(); });
        }
    };
    Object.assign(gnr.GnrBagResolver.prototype, {declaredClass: 'gnr.GnrBagResolver'});
    makeMethodsEnumerable(StandaloneResolver.prototype, ['onSetResolver', 'reset']);
    makeMethodsEnumerable(gnr.GnrBagResolver.prototype);

    gnr.GnrBagFormula = class GnrBagFormula extends gnr.GnrBagResolver {
        constructor(root, expression, symbols, kwargs) {
            super(...arguments);
            this.root = root;
            symbols = objectUpdate(objectUpdate({}, symbols || {}), fromKwargs(kwargs || {}));
            this.expr = templateReplace(expression, symbols);
        }
        load() {
            var root = this.root;
            var curr = this._parent;
            return eval(this.expr);
        }
    };
    Object.assign(gnr.GnrBagFormula.prototype, {declaredClass: 'gnr.GnrBagFormula'});
    makeMethodsEnumerable(gnr.GnrBagFormula.prototype);

    gnr.GnrBagGetter = class GnrBagGetter extends gnr.GnrBagResolver {
        constructor(bag, path, what) {
            super(...arguments);
            this.path = path;
            this.what = what || 'node';
        }
        load() {
            var node = genro.getNode(this.path);
            if (this.what === 'node') return node;
            if (this.what === 'value') return node.getValue();
            if (this.what === 'attr') return node.getAttr();
        }
    };
    Object.assign(gnr.GnrBagGetter.prototype, {declaredClass: 'gnr.GnrBagGetter'});
    makeMethodsEnumerable(gnr.GnrBagGetter.prototype);

    gnr.GnrBagCbResolver = class GnrBagCbResolver extends gnr.GnrBagResolver {
        constructor(kwargs, isGetter, cacheTime) {
            super(...arguments);
            this.method = kwargs.method;
            this.parameters = kwargs.parameters;
        }
        load(kwargs) {
            return this.method.call(this, objectUpdate(objectUpdate({}, this.parameters), kwargs));
        }
    };
    Object.assign(gnr.GnrBagCbResolver.prototype, {declaredClass: 'gnr.GnrBagCbResolver'});
    makeMethodsEnumerable(gnr.GnrBagCbResolver.prototype);

    gnr.bagRealPath = function(path) {
        if (path.indexOf('#parent') > 0) {
            var parts = path.split('.');
            var result = [];
            parts.forEach(function(part) {
                if (part === '#parent') result.pop();
                else result.push(part);
            });
            return result.join('.');
        }
        return path;
    };

    function fromKwargs(kwargs) {
        var result = {};
        Object.keys(kwargs).forEach(function(key) {
            result[key] = (key.charAt(0) === '_' ? 'curr.getResolver(' : 'curr.getItem(') +
                "'" + kwargs[key] + "')";
        });
        return result;
    }

    StandaloneResolver.registerBagClass(gnr.GnrBag);
})(GenroBagJS);
