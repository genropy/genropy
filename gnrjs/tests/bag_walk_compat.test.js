const test = require('node:test');
const assert = require('node:assert/strict');
const {loadPair} = require('./bag_audit_harness.cjs');

test('walk and forEach preserve legacy stops, skips, kwargs and indexes', () => {
    const pair = loadPair();
    for (const context of Object.values(pair)) {
        const b = new context.gnr.GnrBag();
        b.setItem('a.skip.child', 1);
        b.setItem('a.keep', 2);
        b.setItem('tail', 3);
        const kw = {marker: 42};
        const seen = [];
        const result = b.walk((node, context, index) => {
            assert.equal(context, kw);
            seen.push([node.label, index]);
            if (node.label === 'skip') return '__continue__';
            if (node.label === 'keep') return false;
        }, 'static', kw);
        assert.equal(result, false);
        assert.deepEqual(seen, [['a', 0], ['skip', 0], ['keep', 1]]);
        const direct = [];
        assert.equal(b.forEach(node => {direct.push(node.label); return 0;}, null, kw), undefined);
        assert.deepEqual(direct, ['a']);
    }
});

test('modern forEach options retain native semantics through the mixin', () => {
    const {selected} = loadPair();
    const b = new selected.gnr.GnrBag();
    b.setItem('a.child', 1);
    b.setItem('tail', 2);
    const seen = [];
    b.forEach(node => {seen.push(node.label); return false;}, {deep: true});
    assert.deepEqual(seen, ['a', 'tail']);
});
