const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

// Historical fixtures may still expose a method; the current property contract
// is checked independently in expired_property.test.js.
function readExpired(resolver) {
    return typeof resolver.expired === 'function' ? resolver.expired() : resolver.expired;
}

function run(mode, body) { return body(loadPair()[mode === 'legacy' ? 'legacy' : 'selected']); }
function differential(name, body) {
    test(name, () => {
        const legacy = run('legacy', body);
        const selected = run('genro-bag-js-mixin', body);
        assert.deepEqual(selected, legacy);
    });
}

test('resolver subclasses retain supported public members without enumerability requirements', () => {
    const {legacy, selected} = loadPair();
    const accepted = require('./bag_accepted_removals.cjs');
    for (const name of ['GnrBagResolver', 'GnrBagCbResolver']) {
        for (const key in legacy.gnr[name].prototype) {
            if (key.startsWith('_') || accepted.members[name].includes(key)) continue;
            assert.ok(key in selected.gnr[name].prototype, `${name}.${key}`);
        }
        for (const key of accepted.members[name]) assert.equal(selected.gnr[name].prototype[key], undefined);
    }
});


differential('resolver negative cache expiration and reset preserve legacy behavior', ({gnr}) => {
    const resolver = new gnr.GnrBagResolver();
    resolver.setCacheTime(-1);
    const before = readExpired(resolver);
    resolver.lastUpdate = new Date();
    const after = readExpired(resolver);
    resolver.reset();
    return [before, after, readExpired(resolver)];
});


differential('resolve kwargs override destination/static and preserve caller objects', ({gnr}) => {
    const defaults = {a:1};
    const options = {a:2, static:true, _destFullpath:'override'};
    const resolver = new gnr.GnrBagResolver(defaults, false, 3, function(kw, node) {
        return [JSON.stringify(kw), node.marker, this === resolver];
    });
    const result = resolver.resolve(options, {marker:5,getFullpath:()=> 'actual'});
    return [result, JSON.stringify(defaults), JSON.stringify(options), resolver.lastUpdate !== null];
});

differential('getter resolution leaves timestamp unchanged and omits destination argument', ({gnr}) => {
    const r = new gnr.GnrBagResolver({}, true, 1, function(kw) {return arguments.length;});
    return [r.resolve(), r.lastUpdate];
});

differential('resolver forwards supported legacy Bag collection operations', ({gnr}) => {
    const bag = new gnr.GnrBag();
    bag.setItem('a', 2, {cost:4}); bag.setItem('b', 3, {cost:5});
    bag.contains = function() { return arguments.length; };
    const resolver = new gnr.GnrBagResolver({}, false, 0, () => bag);
    return JSON.stringify([resolver.keys(),resolver.items(),resolver.values(),resolver.digest('#k'),
        resolver.sum('#v'),resolver.contains('a'),resolver.len(),
        resolver.htraverse({pathlist:['a'],autocreate:false}).label]);
});

differential('resolver Deferred finalization, pending callbacks and cancellation', ({gnr,dojo}) => {
    const d = new dojo.Deferred();
    const r = new gnr.GnrBagResolver({},false,0,()=>d);
    const out = r.resolve();
    const before = r.lastUpdate;
    d.callback(12);
    let calls = 0;
    r.meToo(()=> calls++); r.meToo(()=> calls++);
    r.runPendingDeferred(r._pendingDeferred);
    const pending = r.meToo(()=> calls++);
    r.cancelMeToo();
    r._pendingDeferred = undefined;
    r.cancelMeToo();
    return [out===d,before,r.lastUpdate!==null,calls,pending.fired,r._pendingDeferred.length];
});

differential('callback resolver merges parameters, kwargs and call-time overrides with bound receiver', ({gnr}) => {
    let r;
    const method = function(kw) {return [this===r,kw.a,kw.b,kw.c,kw._destFullpath];};
    r = new gnr.GnrBagCbResolver({method,parameters:{a:1,b:2},b:3},false,-1);
    return [r.resolve({c:4}),r.cacheTime,readExpired(r)];
});

test('retired formula, getter and description APIs remain absent', () => {
    const {selected: {gnr}} = loadPair();
    assert.equal(gnr.GnrBagFormula, undefined);
    assert.equal(gnr.GnrBagGetter, undefined);
    const bag = new gnr.GnrBag();
    for (const name of ['formula', 'defineFormula', 'defineSymbol']) assert.equal(bag[name], undefined);
    let calls = 0;
    const resolver = new gnr.GnrBagResolver({}, false, 0, () => ++calls);
    assert.equal(resolver.resolverDescription, undefined);
    assert.equal(calls, 0);
});

differential('resolver Promise is returned untouched as a non-Deferred legacy value', ({gnr}) => {
    let thenCalls = 0;
    const promiseLike = {then() {thenCalls++;}};
    const r = new gnr.GnrBagResolver({},false,0,()=>promiseLike);
    return [r.resolve() === promiseLike,thenCalls,r.lastUpdate!==null];
});

differential('base resolver accepts inherited enumerable kwargs', ({gnr}) => {
    const defaults = Object.create({inherited:3}); defaults.own = 2;
    const r = new gnr.GnrBagResolver(defaults,false,0,kw=>JSON.stringify(kw));
    return r.resolve();
});


test('resolver constructor initializes cache without invoking the legacy method override', () => {
    function observe({gnr}) {
        const calls = [];
        class Custom extends gnr.GnrBagResolver {
            setCacheTime(value) { calls.push(value); super.setCacheTime(value); }
        }
        const resolver = new Custom({}, false, 12);
        const initial = [calls.slice(), resolver.cacheTime];
        resolver.setCacheTime(5);
        return {initial, calls, cacheTime: resolver.cacheTime};
    }
    assert.deepEqual(run('legacy', observe), {
        initial: [[12], 12], calls: [12, 5], cacheTime: 5
    });
    assert.deepEqual(run('genro-bag-js-mixin', observe), {
        initial: [[], 12], calls: [5], cacheTime: 5
    });
});

test('approved resolver defaults remain normalized instead of legacy undefined (D20)', () => {
    const {legacy, selected} = loadPair();
    const before = new legacy.gnr.GnrBagResolver();
    assert.equal(before.kwargs, undefined);
    assert.equal(before.isGetter, undefined);
    assert.equal(before.getParentNode(), undefined);
    assert.equal(before.load(), undefined);

    const current = new selected.gnr.GnrBagResolver();
    assert.deepEqual({...current.kwargs}, {});
    assert.equal(current.isGetter, false);
    assert.equal(current.getParentNode(), null);
    assert.equal(current.load(), null);
    assert.equal(current.getCacheTime(), before.getCacheTime());
    assert.equal(current.lastUpdate, before.lastUpdate);
});
