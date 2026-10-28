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

//a dojo 1.x style Deferred: one chain, a thrown callback turns into the error path, late callbacks run at once
class Deferred {
    constructor() { this.chain = []; this.fired = false; this.value = undefined; }
    addCallback(cb) { return this.addCallbacks(cb, null); }
    addErrback(eb) { return this.addCallbacks(null, eb); }
    addCallbacks(cb, eb) {
        this.chain.push({cb, eb});
        if (this.fired) this.run();
        return this;
    }
    callback(value) { this.fired = true; this.value = value; this.run(); }
    errback(err) { this.fired = true; this.value = err instanceof Error ? err : new Error(err); this.run(); }
    run() {
        while (this.chain.length) {
            const {cb, eb} = this.chain.shift();
            const handler = this.value instanceof Error ? eb : cb;
            if (!handler) continue;
            try { this.value = handler(this.value); } catch (error) { this.value = error; }
        }
    }
}

//a Selection store whose query is a Deferred the test settles by hand
function createStore({onLoaded = () => {}} = {}) {
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
        onLoaded
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
    queries[0].deferred.callback({attr: {totalrows: 3}});
    assert.equal(queries.length, 2);
    assert.equal(queries[1].runKwargs.query_reason, 'third');
    assert.equal(store.loadingData, true);
    queries[1].deferred.callback({attr: {totalrows: 3}});
    assert.equal(queries.length, 2);
    assert.equal(store.loadingData, false);
});

test('a queued caller is called back only when the queued reload has landed', () => {
    const seen = [];
    const {store, queries} = createStore({onLoaded(r) { seen.push('loaded:' + r.tag); }});
    const first = store.loadData();
    first.addCallback(() => { seen.push('first callback'); });
    const queued = store.loadData();
    assert.equal(store.loadData(), queued);
    assert.notEqual(queued, first);
    queued.addCallback(() => { seen.push('queued callback'); });
    queries[0].deferred.callback({tag: 'old'});
    assert.deepEqual(seen, ['loaded:old', 'first callback']);
    queries[1].deferred.callback({tag: 'fresh'});
    assert.deepEqual(seen, ['loaded:old', 'first callback', 'loaded:fresh', 'queued callback']);
});

test('a failed query unlocks the store, still runs the queued load and fails its deferred too', () => {
    const {store, queries} = createStore();
    store.loadData();
    const queued = store.loadData();
    const outcome = [];
    queued.addErrback(err => { outcome.push(err.message); return err; });
    queries[0].deferred.errback(new Error('boom'));
    assert.equal(queries.length, 2);
    assert.equal(store.loadingData, true);
    queries[1].deferred.errback(new Error('boom again'));
    assert.equal(store.loadingData, false);
    assert.deepEqual(outcome, ['boom again']);
    store.loadData();
    assert.equal(queries.length, 3);
});

test('a callback that throws after the query landed does not unlock the queued reload', () => {
    let fail = true;
    const {store, queries} = createStore({onLoaded() { if (fail) { fail = false; throw new Error('render failed'); } }});
    store.loadData();
    store.loadData();
    queries[0].deferred.callback({});
    assert.equal(queries.length, 2);
    assert.equal(store.loadingData, true);
    store.loadData();
    assert.equal(queries.length, 2);
    queries[1].deferred.callback({});
    assert.equal(queries.length, 3);
});

test('sequential loads each run their own query', () => {
    const {store, queries} = createStore();
    store.loadData();
    queries[0].deferred.callback({});
    store.loadData();
    queries[1].deferred.callback({});
    assert.equal(queries.length, 2);
    assert.equal(store.loadingData, false);
});
