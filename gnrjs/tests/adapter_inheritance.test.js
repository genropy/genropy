const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

test('collection methods are inherited from the standalone Bag', () => {
    const {selected} = loadPair();
    for (const name of ['items', 'keys', 'values', 'columns', 'update', 'delParentRef', 'getResolver']) {
        assert.equal(Object.hasOwn(selected.gnr.GnrBag.prototype, name), false, name);
        assert.equal(selected.gnr.GnrBag.prototype[name], selected.GenroBagJS.Bag.prototype[name], name);
        const visible = [];
        for (const key in new selected.gnr.GnrBag()) visible.push(key);
        assert.equal(visible.includes(name), false, `${name} must retain native non-enumerability`);
    }
});

test('no-op resolver hooks and cache reset are inherited from standalone', () => {
    const {selected} = loadPair();
    for (const name of ['onSetResolver', 'reset']) {
        assert.equal(Object.hasOwn(selected.gnr.GnrBagResolver.prototype, name), false, name);
        assert.equal(selected.gnr.GnrBagResolver.prototype[name],
            selected.GenroBagJS.BagResolver.prototype[name], name);
        const visible = [];
        for (const key in new selected.gnr.GnrBagResolver()) visible.push(key);
        assert.equal(visible.includes(name), false, `${name} must retain native non-enumerability`);
    }
});

test('digest keeps row shape, callable filtering, columns and resolver behavior', () => {
    const {selected} = loadPair();
    const bag = new selected.gnr.GnrBag();
    let calls = 0;
    bag.setItem('remote', new selected.gnr.GnrBagCbResolver({method: () => ++calls}, false, 60));
    assert.deepEqual(JSON.parse(JSON.stringify(bag.digest('#__v'))), [[null]]);
    assert.equal(calls, 0);
    assert.deepEqual(JSON.parse(JSON.stringify(bag.digest('#v'))), [[1]]);
    assert.equal(calls, 1);
    bag.setItem('second', 2);
    assert.deepEqual(JSON.parse(JSON.stringify(bag.digest('#v', n => n.label === 'second'))), [[2]]);
    assert.deepEqual(JSON.parse(JSON.stringify(bag.digest('#v', null, true))), [[1, 2]]);
});
