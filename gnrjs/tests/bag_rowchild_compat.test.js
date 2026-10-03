const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

test('rowchild preserves legacy Bag label rules, attributes and return value', () => {
    const {legacy, selected} = loadPair();
    for (const c of [legacy, selected]) {
        c.genro.assert = (value, message) => assert.ok(value, message);
        c.genro.time36Id = () => 'generated';
        const bag = new c.gnr.GnrBag();
        const attrs = {field: 'amount', caption: 'Amount', dtype: 'N'};
        assert.equal(bag.rowchild('#field', attrs), undefined);
        assert.equal(bag.getItem('amount'), null);
        assert.equal(bag.getAttr('amount', 'dtype'), 'N');
        assert.deepEqual(attrs, {field: 'amount', caption: 'Amount', dtype: 'N'});
        assert.equal(bag.rowchild('row', {caption: 'Generated'}), undefined);
        assert.deepEqual(Array.from(bag.keys()), ['amount', 'row_generated']);
        bag.rowchild('#field', {field: 'amount', caption: 'Replaced'});
        assert.equal(bag.getAttr('amount', 'caption'), 'Replaced');
        assert.throws(() => bag.rowchild('#missing', {}), /Missing label/);
        assert.equal(typeof bag.child, 'undefined');
    }
    assert.equal(typeof selected.GenroBagJS.Bag.prototype.rowchild, 'undefined');
});
