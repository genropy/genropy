const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

function exercise(c, cancel = false, mode = '') {
    // The shared harness hitch stub omits Dojo's partial argument binding.
    c.dojo.hitch = (scope, method, ...args) => method === undefined ? scope :
        (typeof method === 'string' ? scope[method] : method).bind(scope, ...args);
    const scheduled = [];
    c.setTimeout = callback => { scheduled.push(callback); };
    c.console = {...c.console, log() {}};
    let calls = 0;
    const trace = [];
    const result = new c.dojo.Deferred();
    const resolver = new c.gnr.GnrBagResolver({}, false, -1, () => {calls++; return result;});
    const bag = new c.gnr.GnrBag(); bag.setBackRef();
    bag.setItem('value', resolver);
    const node = bag.getNode('value');
    resolver.onloaded = function() {trace.push(['onloaded', this === node, this.getValue('static')]);};
    let events = 0;
    bag.subscribe('test', {any: () => {events++; trace.push(['event', node.getValue()]);}});
    const first = node.getValue(mode);
    const second = node.getValue(mode);
    const third = node.getValue(mode);
    assert.equal(first, result);
    assert.ok(second instanceof c.dojo.Deferred);
    assert.notEqual(first, second);
    assert.equal(calls, 1);
    assert.equal(node.getValue('static'), null);
    assert.equal(resolver.lastUpdate, null);
    second.addCallbacks(value => {trace.push(['second', value]); return value;},
        error => {trace.push(['second-cancel', error.dojoType]); return null;});
    third.addCallbacks(value => {trace.push(['third', value]); return value;},
        error => {trace.push(['third-cancel', error.dojoType]); return null;});
    if (cancel) resolver.cancelMeToo();
    result.callback(42);
    while (scheduled.length) scheduled.shift()();
    assert.equal(node.getValue(), 42);
    assert.equal(calls, 1);
    assert.equal(resolver._pendingDeferred.length, 0);
    assert.equal(resolver.lastUpdate === null, false);
    return {trace, events, state: node._status};
}

for (const [title, cancel, mode] of [['success', false, ''], ['cancellation', true, ''], ['notrigger', false, 'notrigger']]) {
    test(`queued reads match legacy: ${title}`, () => {
        const {legacy, selected} = loadPair();
        assert.deepEqual(exercise(selected, cancel, mode), exercise(legacy, cancel, mode));
    });
}

test('getters remain independent and do not queue or cache their values', () => {
    for (const c of Object.values(loadPair())) {
        let calls = 0;
        const resolver = new c.gnr.GnrBagResolver({}, true, -1, () => ++calls);
        const bag = new c.gnr.GnrBag(); bag.setItem('value', resolver);
        const node = bag.getNode('value');
        assert.equal(node.getValue(), 1);
        assert.equal(node.getValue(), 2);
        assert.equal(node.getValue('static'), null);
        assert.equal(resolver.lastUpdate, null);
        assert.equal(resolver._pendingDeferred.length, 0);
    }
});

test('Deferred rejection retains legacy state and allows explicit waiter cancellation', () => {
    for (const c of Object.values(loadPair())) {
        const result = new c.dojo.Deferred();
        const resolver = new c.gnr.GnrBagResolver({}, false, 0, () => result);
        const bag = new c.gnr.GnrBag(); bag.setItem('value', resolver);
        const node = bag.getNode('value');
        const first = node.getValue();
        const waiter = node.getValue();
        const error = new Error('load failed');
        result.errback(error);
        assert.equal(first.fired, 1);
        assert.equal(waiter.fired, -1);
        assert.equal(node._status, 'resolving');
        assert.equal(resolver.lastUpdate, null);
        resolver.cancelMeToo();
        assert.equal(waiter.fired, 1);
        assert.equal(resolver._pendingDeferred.length, 0);
        first.addErrback(() => null);
        waiter.addErrback(() => null);
    }
});

test('direct Deferred resolution retains identity and finalizes only on completion', () => {
    const {selected: c} = loadPair();
    const deferred = new c.dojo.Deferred();
    const resolver = new c.gnr.GnrBagResolver({}, false, -1, () => deferred);
    assert.equal(resolver.resolve(), deferred);
    assert.equal(resolver.lastUpdate, null);
    deferred.callback(7);
    assert.notEqual(resolver.lastUpdate, null);
    assert.equal(resolver.resolve(), 7);
    assert.equal(typeof c.GenroBagJS.BagResolver.prototype.meToo, 'undefined');
});

test('standalone resolvers attached to bridged nodes retain their native policy', () => {
    const {selected: c} = loadPair();
    let calls = 0;
    const resolver = new c.GenroBagJS.BagCbResolver({callback: () => ++calls, cacheTime: -1, asBag: false});
    const bag = new c.gnr.GnrBag(); bag.setItem('value', resolver);
    assert.equal(bag.getItem('value'), 1);
    assert.equal(bag.getItem('value'), 1);
    assert.equal(typeof resolver.meToo, 'undefined');
});
