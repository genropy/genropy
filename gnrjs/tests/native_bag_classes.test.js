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
        dijit: {},
        document: {},
        File: function() {},
        genro: {isMobile: false, time36Id: () => 'generated'},
        window: {}
    };
    if (withNamespace) context.gnr = {};
    context.dojo = {
        Deferred,
        version: {major: 1, minor: 1},
        require() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
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
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of filenames) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
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

test('Bag classes preserve identity, metadata, and enumerable prototype members', () => {
    const {gnr} = loadClasses();
    const bag = new gnr.GnrBag();
    const node = bag.setItem('answer', 42);

    assert.ok(bag instanceof gnr.GnrBag);
    assert.ok(node instanceof gnr.GnrBagNode);
    assert.equal(node.constructor, gnr.GnrBagNode);
    assert.equal(node.declaredClass, 'gnr.GnrBagNode');
    assert.equal(bag.declaredClass, 'gnr.GnrBag');
    assert.equal(Object.prototype.propertyIsEnumerable.call(gnr.GnrBag.prototype, '_nodeFactory'), true);
    assert.equal(Object.prototype.propertyIsEnumerable.call(gnr.GnrBagNode.prototype, 'getValue'), true);
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

test('Resolver subclasses initialize the base state and preserve sync and Deferred resolution', () => {
    const {gnr} = loadClasses();
    const sync = new gnr.GnrBagCbResolver({method: kw => kw.value * 2, parameters: {value: 3}}, false, 10);
    assert.ok(sync instanceof gnr.GnrBagResolver);
    assert.deepEqual({...sync._attributes}, {});
    assert.equal(sync.resolve(), 6);
    assert.equal(Object.prototype.toString.call(sync.lastUpdate), '[object Date]');

    const deferred = new Deferred();
    const asyncResolver = new gnr.GnrBagResolver({}, false, 0, () => deferred);
    const result = asyncResolver.resolve();
    assert.equal(result, deferred);
    assert.equal(asyncResolver.lastUpdate, null);
    assert.equal(deferred.callback('done'), 'done');
    assert.equal(Object.prototype.toString.call(asyncResolver.lastUpdate), '[object Date]');
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
