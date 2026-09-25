const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

class Deferred {
    constructor() {
        this.callbacks = [];
    }

    addCallback(callback) {
        this.callbacks.push(callback);
        return this;
    }

    callback(value) {
        return this.callbacks.reduce((result, callback) => callback(result), value);
    }

    cancel() {}
}

function loadClasses(filenames = ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js'], withNamespace = true) {
    const context = {
        alert() {},
        console,
        TextEncoder, TextDecoder, Uint8Array,
        atob, btoa,
        dijit: {},
        document: {},
        File: function() {},
        genro: {isMobile: false, time36Id: () => 'generated'},
        setTimeout,
        window: {}
    };
    if (withNamespace) context.gnr = {};
    context.dojo = {
        Deferred,
        _hasResource: {},
        version: {major: 1, minor: 1},
        require() {},
        eval,
        hitch: (object, method) => method === undefined ? object :
            (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        provide() {},
        extend(constructor, members) { Object.assign(constructor.prototype, members); },
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            Declared.prototype.constructor = Declared;
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    context.genro.evaluate = expression => vm.runInContext('(' + expression + ')', context);
    vm.runInContext(readFileSync(path.join(__dirname,
        '../../dojo_libs/dojo_11/dojo_release/dojo/_base/Deferred.js'), 'utf8'), context,
    {filename: 'dojo/_base/Deferred.js'});
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const requested of filenames) {
        const selected = requested === 'gnrbag.js' && process.env.GNR_JS_BAG === 'genro-bag-js-mixin'
            ? ['genro_bagjs_bundle.js', 'gnrbag_mixin.js'] : [requested];
        for (const filename of selected) {
            vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
        }
    }
    return context;
}


test('gnrbag creates the global namespace during a clean bootstrap', () => {
    const context = loadClasses(['gnrlang.js', 'gnrbag.js'], false);

    assert.equal(typeof context.gnr, 'object');
    assert.equal(typeof context.gnr.GnrBag, 'function');
    assert.equal(typeof context.gnr.GnrBagNode, 'function');
    assert.equal(typeof context.gnr.GnrBagResolver, 'function');
    assert.ok(new context.gnr.GnrBag() instanceof context.gnr.GnrBag);
});

test('Bag classes preserve identity and metadata with selected enumerability', () => {
    const context = loadClasses();
    const {gnr} = context;
    const bag = new gnr.GnrBag();
    const node = bag.setItem('answer', 42);

    assert.ok(bag instanceof gnr.GnrBag);
    assert.ok(node instanceof gnr.GnrBagNode);
    assert.equal(node.constructor, gnr.GnrBagNode);
    assert.equal(node.declaredClass, 'gnr.GnrBagNode');
    assert.equal(bag.declaredClass, 'gnr.GnrBag');
    assert.equal(Object.prototype.propertyIsEnumerable.call(gnr.GnrBag.prototype, '_nodeFactory'),
        process.env.GNR_JS_BAG !== 'genro-bag-js-mixin');
    assert.equal(Object.prototype.propertyIsEnumerable.call(gnr.GnrBagNode.prototype, 'getValue'),
        process.env.GNR_JS_BAG !== 'genro-bag-js-mixin');
    if (process.env.GNR_JS_BAG === 'genro-bag-js-mixin') {
        assert.ok(bag instanceof context.GenroBagJS.Bag);
        assert.ok(node instanceof context.GenroBagJS.BagNode);
        assert.equal(context.GenroBagJS.TYTX.getDecimalLibrary(), 'number');
        assert.deepEqual(Array.from(bag.getNodes().map(item => item.label)), ['answer']);
    }
});

test('DomSource construction runs base initialization with the specialized node factory', () => {
    const {gnr} = loadClasses();
    const source = new gnr.GnrDomSource();
    const node = source.setItem('div', null, {mobile_hidden: true});

    assert.ok(source instanceof gnr.GnrDomSource);
    assert.ok(source instanceof gnr.GnrStructData);
    assert.ok(source instanceof gnr.GnrBag);
    assert.ok(node instanceof gnr.GnrDomSourceNode);
    assert.ok(node instanceof gnr.GnrBagNode);
    assert.equal(node.attr.mobile_hidden, undefined);
    assert.equal(node.declaredClass, 'gnr.GnrDomSourceNode');
});

test('selected adapter reads legacy typed XML envelopes', {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
    const context = loadClasses();
    const {gnr} = context;
    const recalls = [];
    context.genro.rpc = {
        remoteResolver(method, parameters, options) {
            recalls.push({method, parameters, options});
            return new gnr.GnrBagResolver({}, false, options.cacheTime);
        }
    };
    const bag = new gnr.GnrBag(
        '<GenRoBag><enabled _T="B">false</enabled><count _T="L" zero="0::L">0</count>' +
        '<nested><when _T="D">2026-09-13</when></nested>' +
        '<remote _resolver="{&quot;kwargs&quot;:{&quot;cacheTime&quot;:4}}"></remote></GenRoBag>'
    );

    assert.equal(bag.getItem('enabled'), false);
    assert.equal(bag.getItem('count'), 0);
    assert.equal(bag.getNode('count').attr.zero, 0);
    assert.ok(bag.getItem('nested') instanceof gnr.GnrBag);
    assert.equal(Object.prototype.toString.call(bag.getItem('nested.when')), '[object Date]');
    assert.equal(bag.getNode('remote').getResolver() instanceof gnr.GnrBagResolver, true);
    assert.equal(recalls.length, 1);
    assert.equal(recalls[0].method, 'resolverRecall');
    assert.equal(recalls[0].parameters.resolverPars.kwargs.cacheTime, 4);
    assert.equal(recalls[0].parameters.resolverPars.cacheTime, 0);
    assert.equal(recalls[0].options.cacheTime, 4);
});

test('selected XML keeps populated resolver branches loaded with resolved metadata',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const context = loadClasses();
        const {gnr} = context;
        context.genro.rpc = {
            remoteResolver(method, parameters, options) {
                return new gnr.GnrBagResolver({}, false, options.cacheTime);
            }
        };
        const bag = new gnr.GnrBag(
            '<GenRoBag><rows _resolver="{&quot;kwargs&quot;:{&quot;cacheTime&quot;:30}}" ' +
            '_resolvedInfo="{&quot;rowcount&quot;:1}::JS"><P_0><amount _T="L">12</amount></P_0>' +
            '</rows></GenRoBag>'
        );
        const node = bag.getNode('rows');

        assert.equal(node._status, 'loaded');
        assert.equal(node.staticValue instanceof gnr.GnrBag, true);
        assert.equal(node.staticValue.len(), 1);
        assert.equal(node.attr.rowcount, 1);
        assert.equal(Object.prototype.toString.call(node.getResolver().lastUpdate), '[object Date]');
        assert.equal(node.getValue(), node.staticValue);
    });

test('selected XML reconstructs and synchronously loads scalar relation resolvers',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const context = loadClasses();
        const {gnr} = context;
        let calls = 0;
        context.genro.getRelationResolver = (attributes, name, parentBag) => {
            assert.equal(name, 'relOne');
            assert.ok(parentBag instanceof gnr.GnrBag);
            return new gnr.GnrBagCbResolver({method: () => {
                calls += 1;
                return 'Customer label';
            }, parameters: {}});
        };
        const bag = new gnr.GnrBag(
            '<GenRoBag><customer _resolver_name="relOne" target="invc.customer.id"/>' +
            '</GenRoBag>'
        );
        const node = bag.getNode('customer');

        assert.ok(node.getResolver() instanceof gnr.GnrBagResolver);
        assert.equal(node._status, 'unloaded');
        assert.equal(node.getValue(), 'Customer label');
        assert.equal(calls, 1);
        assert.equal(node._status, 'loaded');
    });

test('selected htraverse continues through a Deferred relation branch',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr, dojo} = loadClasses();
        const deferred = new dojo.Deferred();
        const data = new gnr.GnrBag();
        data.setItem('relation', new gnr.GnrBagCbResolver({method: () => deferred, parameters: {}}));

        const result = data.getItem('relation.name');
        assert.ok(result instanceof dojo.Deferred);
        let resolved;
        result.addCallback(value => { resolved = value; return value; });
        const related = new gnr.GnrBag();
        related.setItem('name', 'Customer label');
        deferred.callback(related);
        assert.equal(resolved, 'Customer label');
        assert.equal(data.getNode('relation').staticValue, related);
    });

test('selected adapter loads RPC XML documents and preserves declared branch classes',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        class SpecializedBag extends gnr.GnrDomSource {}
        const text = value => ({nodeType: 3, nodeValue: value});
        const element = (tagName, attributes, children) => ({
            nodeType: 1,
            tagName,
            attributes: Object.entries(attributes || {}).map(([name, value]) => ({name, value})),
            childNodes: children || [],
            get textContent() {
                return this.childNodes.map(child => child.nodeValue || child.textContent || '').join('');
            }
        });
        const root = element('GenRoBag', {}, [
            element('result', {__cls: 'DOMSOURCE'}, [
                element('slotbar', {tag: 'slotbar', slots: 'left,*,right'}, []),
                element('tabroot', {_T: 'BAG'}, [])
            ])
        ]);
        const document = {nodeType: 9, documentElement: root, lastChild: root};
        const envelope = new gnr.GnrBag();

        envelope.fromXmlDoc(document, {DOMSOURCE: SpecializedBag});

        assert.ok(envelope.getItem('result') instanceof SpecializedBag);
        const slotbar = envelope.getNode('result.slotbar');
        assert.equal(slotbar.attr.slots, 'left,*,right');
        assert.equal(slotbar.currentAttributes().slots, 'left,*,right');
        assert.ok(envelope.getItem('result.tabroot') instanceof SpecializedBag);
        assert.equal(envelope.getItem('result.tabroot').len(), 0);
        assert.ok(envelope.getNode('result') instanceof gnr.GnrBagNode);
        const contextBag = new gnr.GnrBag();
        contextBag.fromXmlDoc('<GenRoBag><context><value>ok</value></context></GenRoBag>');
        assert.ok(contextBag.getItem('context') instanceof gnr.GnrBag);
    });

test('Bag notifications retain their order and parent propagation', () => {
    const {gnr} = loadClasses();
    const root = new gnr.GnrBag();
    const child = new gnr.GnrBag();
    root.setItem('child', child);
    root.setBackRef();
    const events = [];
    child.subscribe('child', {any: event => events.push(`child:${event.evt}`)});
    root.subscribe('root', {any: event => events.push(`root:${event.evt}`)});

    child.setItem('value', 1);

    assert.deepEqual(events, ['child:ins', 'root:ins']);
});

test('selected event envelopes drive the real source insertion consumer',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const context = loadClasses(['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_src.js']);
        const {gnr} = context;
        const handler = new gnr.GnrSrcHandler({});
        const destination = {};
        const built = [];
        handler.buildNode = (node, where, index) => built.push({node, where, index});

        const inserted = handler._main.setItem('div', null, {_parentDomNode: destination});

        assert.equal(built.length, 1);
        assert.equal(built[0].node, inserted);
        assert.equal(built[0].where, destination);
        assert.equal(built[0].index, 0);
        assert.equal(handler._main.index('div'), 0);
        assert.equal(handler._main.index('#0'), 0);
        handler._main.unsubscribe('sourceTriggers');
        inserted.updAttributes({nodeId: 'source_node'});
        assert.equal(handler._main.findNodeById(inserted._id), inserted);

        const events = [];
        handler._main.subscribe('payload', {any: event => events.push(event)});
        inserted.setAttr({title: 'changed'}, true, true, 'title');
        assert.equal(events[0].base, handler._main);
        assert.equal(events[0].changedAttr, 'title');
        assert.deepEqual({...events[0].changedAttributes}, {title: true});
        inserted.setValue('fired', true, null, null, true);
        assert.equal(events[1].fired, true);
    });

test('selected DomSource clear follows legacy silent and per-node delete events',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses(['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_src.js']);
        const handler = new gnr.GnrSrcHandler({});
        const deleted = [];
        handler._trigger_ins = () => {};
        handler._trigger_del = event => deleted.push(event);

        handler._main.setItem('first', null, {_parentDomNode: {}});
        handler._main.setItem('second', null, {_parentDomNode: {}});
        handler._main.clear();
        assert.equal(deleted.length, 0);

        handler._main.setItem('first', null, {_parentDomNode: {}});
        handler._main.setItem('second', null, {_parentDomNode: {}});
        handler._main.clear(true);

        assert.deepEqual(deleted.map(event => event.node.label), ['second', 'first']);
        assert.deepEqual(deleted.map(event => event.ind), [1, 0]);
        assert.ok(deleted.every(event => event.node instanceof gnr.GnrDomSourceNode));
        assert.ok(deleted.every(event => event.where === handler._main));
    });

test('Resolver subclasses initialize the base state and preserve sync and Deferred resolution', () => {
    const {gnr, dojo} = loadClasses();
    const sync = new gnr.GnrBagCbResolver({method: kw => kw.value * 2, parameters: {value: 3}}, false, 10);
    assert.ok(sync instanceof gnr.GnrBagResolver);
    assert.deepEqual({...sync._attributes}, {});
    assert.equal(sync.resolve(), 6);
    assert.equal(Object.prototype.toString.call(sync.lastUpdate), '[object Date]');

    const deferred = new dojo.Deferred();
    const asyncResolver = new gnr.GnrBagResolver({}, false, 0, () => deferred);
    const result = asyncResolver.resolve();
    assert.equal(result, deferred);
    assert.equal(asyncResolver.lastUpdate, null);
    deferred.callback('done');
    assert.equal(deferred.results[0], 'done');
    assert.equal(Object.prototype.toString.call(asyncResolver.lastUpdate), '[object Date]');
});

test('selected Bag concat moves component children without insertion events',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const content = new gnr.GnrDomSource();
        const children = new gnr.GnrDomSource();
        const existing = content.setItem('generated', null, {tag: 'div'});
        const moved = children.setItem('declared', null, {tag: 'span'});
        const events = [];
        content.subscribe('component', {any: event => events.push(event)});

        content.concat(children);

        assert.deepEqual(Array.from(content.getNodes().map(node => node.label)),
            ['generated', 'declared']);
        assert.equal(content.getNode('generated'), existing);
        assert.equal(content.getNode('declared'), moved);
        assert.equal(moved.getParentBag(), content);
        assert.equal(events.length, 0);
    });

test('selected resolver preserves static, cache, concurrency, node state and Dojo Deferred errors',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, async () => {
        const {gnr, dojo} = loadClasses();
        const bag = new gnr.GnrBag();
        bag.setBackRef();
        const deferred = new dojo.Deferred();
        let loads = 0;
        const resolver = new gnr.GnrBagResolver({}, false, -1, () => {
            loads += 1;
            return deferred;
        });
        const node = bag.setItem('remote', resolver);
        const events = [];
        bag.subscribe('test', {any: event => events.push(event)});
        assert.equal(node.parentBag, bag);
        assert.equal(bag.backref, true);

        assert.equal(node.getValue('static'), null);
        assert.equal(loads, 0);
        const first = node.getValue();
        const concurrent = node.getValue();
        assert.equal(first, deferred);
        assert.ok(concurrent instanceof dojo.Deferred);
        assert.equal(loads, 1);
        deferred.callback('loaded');
        await new Promise(resolve => setTimeout(resolve, 5));
        assert.equal(node.getValue(), 'loaded');
        assert.equal(loads, 1);
        assert.equal(node.isLoaded(), true);
        assert.equal(events.length, 1);
        assert.equal(events[0].evt, 'upd');
        assert.equal(events[0].reason, 'resolver');

        let uncachedLoads = 0;
        const uncachedNode = bag.setItem('uncached', new gnr.GnrBagResolver({}, false, 0,
            () => ++uncachedLoads));
        assert.equal(uncachedNode.getValue(), 1);
        uncachedNode.getResolver().lastUpdate = new Date(Date.now() - 1);
        assert.equal(uncachedNode.getValue(), 2);
        const expiring = new gnr.GnrBagResolver({}, false, 10, () => 'fresh');
        const expiringNode = bag.setItem('expiring', expiring);
        assert.equal(expiringNode.getValue(), 'fresh');
        expiring.lastUpdate = new Date(Date.now() - 11000);
        assert.equal(expiring.expired, true);

        const failed = new dojo.Deferred();
        const failingNode = bag.setItem('failure',
            new gnr.GnrBagResolver({}, false, 0, () => failed));
        let deliveredError;
        failingNode.getValue().addErrback(error => {
            deliveredError = error;
            return error;
        });
        const failure = new Error('rpc failed');
        failed.errback(failure);
        assert.match(deliveredError.message, /rpc failed/);
    });

test('RPC resolver subclasses retain BagResolver construction and inheritance', () => {
    const {gnr} = loadClasses(['gnrlang.js', 'gnrbag.js', 'genro_rpc.js']);
    const forwardedLoad = () => 'forwarded';
    const remote = new gnr.GnrRemoteResolver({timeout: 20}, true, 5, forwardedLoad);

    assert.ok(remote instanceof gnr.GnrBagResolver);
    assert.equal(remote.cacheTime, 5);
    assert.deepEqual({...remote._attributes}, {});
    assert.equal(remote.xhrKwargs.timeout, 20);
    assert.equal(remote.load, forwardedLoad);
    assert.equal(remote.declaredClass, 'gnr.GnrRemoteResolver');
});

test('selected FramePane-style #id insertion generates unique child labels',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const context = loadClasses();
        const {gnr} = context;
        let generatedId = 0;
        context.genro.time36Id = () => `generated_${++generatedId}`;
        const sidepane = new gnr.GnrDomSource();
        const firstKwargs = {};
        const first = sidepane.setItem('#id', new gnr.GnrDomSource(),
            {tag: 'div', frameCode: 'invoice'}, firstKwargs);
        const secondKwargs = {_position: '<'};
        const second = sidepane.setItem('#id', new gnr.GnrDomSource(),
            {tag: 'span', frameCode: 'invoice'}, secondKwargs);

        assert.notEqual(first.label, '#id');
        assert.notEqual(second.label, '#id');
        assert.notEqual(first.label, second.label);
        // Accepted unused writeback removal; returned nodes expose their labels.
        assert.equal(firstKwargs._new_label, undefined);
        assert.equal(firstKwargs._new_position, undefined);
        assert.equal(secondKwargs._new_label, undefined);
        assert.equal(secondKwargs._new_position, undefined);
        assert.equal(sidepane.getNode('#0'), second);
        assert.equal(sidepane.getNode('#1'), first);
        assert.throws(() => sidepane.setItem('#99', null), /Cannot create new node with #n syntax/);
    });

test('selected DomSource nodes support component attribute detachment',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const context = loadClasses();
        const {gnr} = context;
        context.genro.wdg = {getHandler() { return null; }};
        const source = new gnr.GnrDomSource();
        const children = source._('slotbar', 'bar', {slots: 'left,*,right'});
        const sourceNode = source.getNode('bar');
        const attributes = sourceNode.attr;

        sourceNode.attr = {};
        sourceNode.attr.tag = context.objectPop(attributes, 'tag');
        assert.equal(Object.hasOwn(attributes, 'tag'), false);
        sourceNode._value = null;
        const content = sourceNode._('div', attributes);

        assert.equal(attributes.slots, 'left,*,right');
        assert.equal(attributes.tag, 'div');
        assert.equal(sourceNode.attr.tag, 'slotbar');
        assert.equal(sourceNode.getValue('static').getNode('#0').attr.tag, 'div');
        assert.equal(children instanceof gnr.GnrDomSource, true);
    });

test('ClientCaller retains BagResolver construction and callback behavior', () => {
    const context = loadClasses(['gnrlang.js', 'gnrbag.js', 'genro.js']);
    const {gnr} = context;
    const callback = vm.runInContext('(params) => params.value', context);
    const caller = new gnr.GnrClientCaller({callback, params: {value: 7}});

    assert.ok(caller instanceof gnr.GnrBagResolver);
    assert.deepEqual({...caller._attributes}, {});
    assert.equal(caller.resolve(), 7);
    assert.equal(caller.declaredClass, 'gnr.GnrClientCaller');
});

test('selected data Bags detach cleanly from the DOM source event tree',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const oldParent = new gnr.GnrBag();
        const data = new gnr.GnrBag();
        data.setItem('root', 1);
        oldParent.setItem('old', data);
        oldParent.setBackRef();
        const source = new gnr.GnrDomSource();
        source.setItem('data_0', data, {tag: 'data'});
        source.setBackRef();
        const events = [];
        source.subscribe('source', {any: event => events.push(event)});

        data.clearBackRef();
        data.setItem('root', 2);

        assert.equal(data.getParent(), null);
        assert.equal(data.getParentNode(), null);
        assert.equal(events.length, 0);
});

test('selected DOM source attribute lookup does not resolve preceding data nodes',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        let loads = 0;
        const data = new gnr.GnrBag();
        data.setItem('root', new gnr.GnrBagResolver({}, false, 0, () => ++loads));
        const source = new gnr.GnrDomSource();
        source.setItem('data_0', data, {tag: 'data'});
        const target = source.setItem('widget', null, {tag: 'div', nodeId: 'pyref_target'});

        assert.equal(source.getNodeByAttr('nodeId', 'pyref_target'), target);
        assert.equal(loads, 0);
        assert.equal(data.getNode('root').isLoaded(), true);
        assert.equal(data.getNode('root').isExpired(), true);
        assert.equal(data.getNode('root').getValue('static'), null);
});

test('selected menu full paths round-trip against the main data root',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const dataRoot = new gnr.GnrBag();
        const main = new gnr.GnrBag();
        dataRoot.setItem('main', main);
        main.setItem('gnr.appmenu.root.customers', null, {labelClass: 'menu_entry'});
        dataRoot.setBackRef();
        const menuNode = main.getNode('gnr.appmenu.root.customers');

        const publishedPath = menuNode.getFullpath(null, true);
        const callbackNode = main.getNode(publishedPath);

        assert.equal(publishedPath, 'gnr.appmenu.root.customers');
        assert.equal(callbackNode, menuNode);
        assert.equal(callbackNode.attr.labelClass, 'menu_entry');
        assert.equal(menuNode.getFullpath('##', true), '#0.#0.#0.#0');
});

test('selected insert bubbling never reparents the inserted Bag to an ancestor',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const dataRoot = new gnr.GnrBag();
        const main = new gnr.GnrBag();
        const gnrData = new gnr.GnrBag();
        dataRoot.setItem('main', main);
        main.setItem('gnr', gnrData);
        dataRoot.setBackRef();
        dataRoot.subscribe('root', {any() {}});
        main.subscribe('main', {any() {}});
        const appmenu = new gnr.GnrBag();

        const appmenuNode = gnrData.setItem('appmenu', appmenu);

        assert.equal(appmenu.getParent(), gnrData);
        assert.equal(appmenu.getParentNode(), appmenuNode);
        assert.equal(appmenuNode.getParentBag(), gnrData);
        assert.equal(appmenu.getFullpath(null, true), 'gnr.appmenu');
});

test('selected getNode autocreate labels every insert for source-trigger suppression',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const bag = new gnr.GnrBag();
        const events = [];
        bag.subscribe('data', {any: event => events.push(event)});

        const node = bag.getNode('store.path', null, true);

        assert.equal(node.label, 'path');
        assert.deepEqual(events.map(event => event.reason), ['autocreate', 'autocreate']);
    });

test('selected adapter exposes legacy bagRealPath normalization',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();

        assert.equal(gnr.bagRealPath('main.section.#parent.sibling'), 'main.sibling');
        assert.equal(gnr.bagRealPath('main.a.b.#parent.#parent.c'), 'main.c');
        assert.equal(gnr.bagRealPath('main.section'), 'main.section');
        assert.equal(gnr.bagRealPath('#parent.section'), '#parent.section');
    });

test('selected node container supports the component popSubTagItems pipeline',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses([
            'gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_components.js'
        ]);
        const handler = new gnr.widgets.gnrwdg();
        handler.subtags = {top: 'topHandler'};
        const children = new gnr.GnrDomSource();
        children.setItem('topOne', 'first', {tag: 'framepane_top'});
        children.setItem('body', 'middle', {tag: 'div'});
        children.setItem('topTwo', 'last', {tag: 'framepane_top'});

        const result = handler.popSubTagItems('framepane', children);

        assert.deepEqual(Array.from(result.top.keys()), ['topOne', 'topTwo']);
        assert.equal(result.top.getNode('topOne').attr.tag, undefined);
        assert.equal(result.top._subtag_handler, 'topHandler');
        assert.deepEqual(Array.from(children.keys()), ['body']);
    });

test('selected slotbar cleanup removes consecutive slot nodes while iterating',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses([
            'gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_components.js'
        ]);
        const children = new gnr.GnrDomSource();
        children.setItem('firstSlot', null, {tag: 'slot'});
        children.setItem('secondSlot', null, {tag: 'slot'});
        children.setItem('button', null, {tag: 'button'});

        children.getNodes().forEach(function(node) {
            if (node.attr.tag === 'slot') children.popNode(node.label);
        });

        assert.deepEqual(Array.from(children.keys()), ['button']);
    });

test('selected copy-on-pop keeps specialized source ancestry and freeze propagation',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses(['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_src.js']);
        const handler = new gnr.GnrSrcHandler({});
        handler._trigger_ins = () => {};
        const children = new gnr.GnrDomSource();
        const bar = handler._main.setItem('bar', children, {tag: 'slotbar'});
        children.setItem('firstSlot', null, {tag: 'slot'});
        children.setItem('secondSlot', null, {tag: 'slot'});
        bar.freeze();

        children.getNodes().forEach(function(node) {
            if (node.attr.tag === 'slot') children.popNode(node.label);
        });

        assert.equal(children.len(), 0);
        assert.equal(children.getParentNode(), bar);
        assert.ok(bar instanceof gnr.GnrDomSourceNode);
        assert.equal(children._nodes._parentBag, children);
    });

test('selected slot wrapper adopts a source node without traversing its internals',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const source = new gnr.GnrDomSource();
        const slotNode = source.setItem('objTitle', 'title', {tag: 'div'});
        const resolver = new gnr.GnrBagCbResolver({method: () => 'resolved'});
        slotNode.setResolver(resolver);

        const wrapped = new gnr.GnrBag({slot: slotNode});

        assert.equal(wrapped.getNode('slot').staticValue, 'title');
        assert.equal(wrapped.getNode('slot').attr.tag, 'div');
        assert.equal(wrapped.getNode('slot').getResolver(), resolver);
        assert.equal(wrapped.getNode('slot').staticValue instanceof gnr.GnrBag, false);
        assert.equal(source.getNode('objTitle').getParentBag(), source);
    });

test('selected node attributes follow approved Python update and null policy',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const node = new gnr.GnrBag().setItem('item', 1, {old: true, keepNull: null});
        assert.equal(Object.hasOwn(node.attr, 'keepNull'), true);

        node.setAttr({next: true, nullable: null}, false);
        assert.deepEqual({...node.attr}, {old: true, next: true});
        node.setAttr({next: true, nullable: null}, false, false, false);
        assert.deepEqual({...node.attr}, {next: true, nullable: null});
        node.setAttr({next: null}, false, true, true);
        assert.deepEqual({...node.attr}, {});
    });

test('selected getItem attribute suffix returns grid metadata instead of Bag rows',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const rows = new gnr.GnrBag();
        rows.setItem('P_0.name', 'First');
        const data = new gnr.GnrBag();
        data.setItem('customers', rows, {totalrows: 37, count: 1});

        assert.equal(data.getItem('customers?totalrows'), 37);
        assert.equal(data.getItem('customers?count'), 1);
        assert.equal(data.getItem('customers?#node'), data.getNode('customers'));
        assert.equal(data.getItem('customers') instanceof gnr.GnrBag, true);
    });

test('selected source ancestry resolves FORM alternatives and inheritance boundaries',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const source = new gnr.GnrDomSource();
        const formNode = source.setItem('form', new gnr.GnrDomSource(), {
            formId: 'invoiceForm', datapath: 'invc_invoice.form', theme: 'outer'
        });
        const formBag = formNode.staticValue;
        const boundary = formBag.setItem('recordPane', new gnr.GnrDomSource(), {
            datapath: '.record', theme: 'record'
        });
        boundary.stopInherite = true;
        const field = boundary.staticValue.setItem('total', null, {tag: 'textbox'});
        source.setBackRef();

        assert.equal(field.attributeOwnerNode('formId,_fakeform'), formNode);
        assert.equal(field.attributeOwnerNode('tag', 'TEXTBOX', true), field);
        assert.equal(field.getInheritedAttributes('formId'), 'invoiceForm');
        assert.deepEqual({...field.getInheritedAttributes()}, {
            datapath: '.record', theme: 'record', tag: 'textbox'
        });
    });

test('selected query captions resolve through inner parent attribute paths',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const data = new gnr.GnrBag();
        data.setItem('query.where.c_0', null, {
            column_caption: 'Invoice number', not_caption: 'Not', op_caption: 'Equal'
        });
        data.setItem('query.queryMode', 'S', {caption: 'Search'});
        data.setBackRef();

        assert.equal(data.getItem('query.where.#parent.queryMode?caption'), 'Search');
        assert.equal(data.getItem('query.where.c_0?column_caption'), 'Invoice number');
        assert.equal(data.getItem('query.where.c_0?not_caption'), 'Not');
        assert.equal(data.getItem('query.where.c_0?op_caption'), 'Equal');
    });

test('selected getNode attribute paths preserve metadata during autocreate lookup',
    {skip: process.env.GNR_JS_BAG !== 'genro-bag-js-mixin'}, () => {
        const {gnr} = loadClasses();
        const data = new gnr.GnrBag();
        const queryMode = data.setItem('queryMode', 'S', {caption: 'Search'});

        assert.throws(() => data.getNode('queryMode?caption', true, true, null), /asTuple/);
        const result = data.getNode('queryMode?caption', false, true, null);
        assert.equal(result, queryMode);
        assert.equal(queryMode.attr.caption, 'Search');
        assert.equal(data.getNode('queryMode?caption'), queryMode);
        assert.equal(data.getNode('missing?caption', false, true, null).label, 'missing');
        assert.equal(data.getNode('missing').attr.caption, undefined);
    });
