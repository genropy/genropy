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

differential('every legacy resolver subclass member exists and remains enumerable', ({gnr}) => {
    return ['GnrBagResolver','GnrBagFormula','GnrBagGetter','GnrBagCbResolver'].map(name => {
        const names = [];
        for (const key in gnr[name].prototype) if (key !== 'setNode' && key !== 'expired') names.push(key);
        return names.sort();
    });
});

differential('resolver constructor, cache, attributes, parent, default load and reset', ({gnr}) => {
    const resolver = new gnr.GnrBagResolver();
    const initial = [resolver.kwargs, resolver.isGetter, resolver.lastUpdate,
        resolver.getParentNode(), resolver.load(), resolver.getCacheTime()];
    resolver.setAttr({a:1}); resolver.setAttr({b:2});
    const attrs = JSON.stringify(resolver.getAttr());
    resolver.setCacheTime(-1);
    const before = readExpired(resolver);
    resolver.lastUpdate = new Date();
    const after = readExpired(resolver);
    resolver.reset();
    let hooks = 0;
    resolver.onSetResolver = () => hooks++;
    const node = {};
    resolver.setParentNode(node);
    return [initial, attrs, before, after, readExpired(resolver), resolver.getParentNode() === node, hooks];
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

differential('resolver forwards the entire legacy Bag interface', ({gnr}) => {
    const bag = new gnr.GnrBag();
    bag.setItem('a', 2, {cost:4}); bag.setItem('b', 3, {cost:5});
    bag.contains = function() { return arguments.length; };
    const resolver = new gnr.GnrBagResolver({}, false, 0, () => bag);
    return JSON.stringify([resolver.keys(),resolver.items(),resolver.values(),resolver.digest('#k'),
        resolver.sum('#v'),resolver.contains('a'),resolver.len(),resolver.resolverDescription(),
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

differential('formula resolves root and current Bag symbols including resolver references', ({gnr}) => {
    const bag = new gnr.GnrBag(); bag.setItem('a',3);
    const r = new gnr.GnrBagFormula(bag, '$x + root.getItem("a")', {}, {x:'a'});
    r._parent = bag;
    assert.throws(() => r.resolve(), /this.load is not a function/);
    return [gnr.GnrBagFormula.prototype.load.call(r),r.root===bag,r.expr];
});

test('Getter intentionally repairs legacy undefined thisWhat for node/value/attr modes', () => {
    run('legacy', ({gnr,genro}) => {
        genro.getNode = () => ({});
        assert.throws(()=>new gnr.GnrBagGetter(null,'a').load(),/thisWhat/);
    });
    run('genro-bag-js-mixin', ({gnr,genro}) => {
        const bag = new gnr.GnrBag(); bag.setItem('a',3,{caption:'A'});
        const node = bag.getNode('a'); genro.getNode = () => node;
        assert.equal(new gnr.GnrBagGetter(null,'a').load(),node);
        assert.equal(new gnr.GnrBagGetter(null,'a','value').load(),3);
        assert.equal(new gnr.GnrBagGetter(null,'a','attr').load().caption,'A');
    });
});

test('formula insertion records pre-existing failures without claiming a working formula flow', () => {
    const {legacy, selected} = loadPair();
    for (const [context, error] of [[legacy, /Maximum call stack/], [selected, /Maximum call stack/]]) {
        const bag = new context.gnr.GnrBag();
        bag.setItem('a',2); bag.defineSymbol({x:'a'}); bag.defineFormula({total:'$x+1'});
        bag.setItem('total',bag.formula('total'));
        assert.throws(()=>bag.getItem('total'), error);
    }
});

differential('resolver description respects a custom value formatter', ({gnr}) => {
    const r = new gnr.GnrBagResolver({},false,0,()=>({toString:()=> 'custom'}));
    return r.resolverDescription();
});

differential('resolver Promise is returned untouched as a non-Deferred legacy value', ({gnr}) => {
    let thenCalls = 0;
    const promiseLike = {then() {thenCalls++;}};
    const r = new gnr.GnrBagResolver({},false,0,()=>promiseLike);
    return [r.resolve() === promiseLike,thenCalls,r.lastUpdate!==null];
});

differential('resolver and callback accept inherited enumerable kwargs and Bag attributes', ({gnr}) => {
    const defaults = Object.create({inherited:3}); defaults.own = 2;
    const r = new gnr.GnrBagResolver(defaults,false,0,kw=>JSON.stringify(kw));
    const attrs = new gnr.GnrBag(); attrs.setItem('caption','A'); r.setAttr(attrs);
    const cb = new gnr.GnrBagCbResolver({method:kw=>JSON.stringify(kw),parameters:defaults});
    return [r.resolve(),JSON.stringify(r.getAttr()),cb.load({own:4})];
});

differential('resolver constructor invokes subclass cache setter after creating attributes', ({gnr}) => {
    let observed;
    class Custom extends gnr.GnrBagResolver {
        setCacheTime(value) { observed = [value, JSON.stringify(this._attributes)]; super.setCacheTime(value); }
    }
    const resolver = new Custom({},false,12);
    return [observed,resolver.cacheTime];
});
