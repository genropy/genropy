const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

test('resolver compatibility forwards legacy arguments and returns while native stays minimal', () => {
    const {legacy, selected} = loadPair();
    function run(c) {
        const calls = [];
        const result = {};
        for (const method of ['keys', 'items', 'values', 'digest', 'sum', 'contains', 'len', 'htraverse']) {
            result[method] = (...args) => {calls.push([method, ...args]); return method;};
        }
        const r = new c.gnr.GnrBagResolver({}, false, 0, () => result);
        const output = [r.keys(), r.items(), r.values(), r.digest('#v'), r.sum(),
            r.contains('ignored-by-legacy'), r.len(), r.htraverse({pathlist: ['a'], autocreate: false})];
        return JSON.stringify({calls, output});
    }
    assert.equal(run(selected), run(legacy));
    for (const name of ['keys', 'items', 'values', 'digest', 'sum', 'contains', 'len', 'htraverse']) {
        assert.equal(typeof selected.GenroBagJS.BagResolver.prototype[name], 'undefined');
    }
});

test('resolver compatibility works with a real Bag and warns once', () => {
    const {selected: c} = loadPair();
    const notices = [];
    c.console = { ...c.console, warn: text => notices.push(text) };
    const bag = new c.gnr.GnrBag({a: 2, b: 3});
    const r = new c.gnr.GnrBagResolver({}, false, 0, () => bag);
    assert.deepEqual(Array.from(r.keys()), ['a', 'b']);
    assert.deepEqual(Array.from(r.values()), [2, 3]);
    assert.equal(r.sum('#v'), 5);
    assert.equal(r.len(), 2);
    assert.equal(notices.length, 1);
    assert.match(notices[0], /deprecated/);
    notices.length = 0;
    assert.deepEqual(Array.from(r.resolve().keys()), ['a', 'b']);
    assert.equal(notices.length, 0);
});
