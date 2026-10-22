const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, navigator: {}, window: {}, document: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        isIE: 0,
        mixin: Object.assign,
        require() {},
        provide() {},
        declare(name, bases, members) {
            const base = Array.isArray(bases) ? bases[0] : bases;
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'gnrstores.js', 'genro_widgets.js', 'genro_components.js', 'genro_grid.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    return context;
}

//the dojo.Deferred the store sees: callbacks and errbacks chained, settled by the test
class Deferred {
    constructor() { this.callbacks = []; this.errbacks = []; }
    addCallback(cb) { this.callbacks.push(cb); return this; }
    addErrback(eb) { this.errbacks.push(eb); return this; }
    resolve(result) { for (const cb of this.callbacks) cb(result); }
    reject(err) { for (const eb of this.errbacks) eb(err); }
}

//a Selection store whose query is a Deferred the test settles by hand
function createStore() {
    const context = createContext();
    context.dojo.Deferred = Deferred;
    const queries = [];
    const store = Object.create(context.gnr.stores.Selection.prototype);
    Object.assign(store, {
        storeNode: {fireNode(runKwargs) { const d = new Deferred(); queries.push({runKwargs, deferred: d}); return d; }},
        isEnabledStore: () => true,
        gridBroadcast() {},
        resetFilter() {},
        onLoading() {},
        onLoaded() {}
    });
    return {store, queries};
}

test('a load asked while a query is in flight waits for it, one more run with the last kwargs', () => {
    const {store, queries} = createStore();
    store.loadData({query_reason: 'first'});
    store.loadData({query_reason: 'second'});
    store.loadData({query_reason: 'third'});
    assert.equal(queries.length, 1);
    assert.equal(store.loadingData, true);
    queries[0].deferred.resolve({attr: {totalrows: 3}});
    assert.equal(queries.length, 2);
    assert.equal(queries[1].runKwargs.query_reason, 'third');
    assert.equal(store.loadingData, true);
    queries[1].deferred.resolve({attr: {totalrows: 3}});
    assert.equal(queries.length, 2);
    assert.equal(store.loadingData, false);
});

test('a load asked while a query is in flight gets the deferred of that query', () => {
    const {store, queries} = createStore();
    const first = store.loadData();
    const queued = store.loadData();
    assert.equal(queued, first);
    assert.equal(first, queries[0].deferred);
});

test('a failed query still runs the queued load, then the store is free again', () => {
    const {store, queries} = createStore();
    store.loadData();
    store.loadData();
    queries[0].deferred.reject(new Error('boom'));
    assert.equal(queries.length, 2);
    assert.equal(store.loadingData, true);
    queries[1].deferred.reject(new Error('boom'));
    assert.equal(store.loadingData, false);
    store.loadData();
    assert.equal(queries.length, 3);
});

test('sequential loads each run their own query', () => {
    const {store, queries} = createStore();
    store.loadData();
    queries[0].deferred.resolve({});
    store.loadData();
    queries[1].deferred.resolve({});
    assert.equal(queries.length, 2);
    assert.equal(store.loadingData, false);
});
