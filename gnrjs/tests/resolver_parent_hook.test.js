const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

test('legacy parent setter changes only the reference, without hooks or cache reset', () => {
    for (const [name, {gnr}] of Object.entries(loadPair())) {
        const resolver = new gnr.GnrBagResolver({}, false, 10, () => 7);
        const calls = [];
        resolver.onSetResolver = node => calls.push(node);
        resolver.lastUpdate = new Date(123456);
        const parent = new gnr.GnrBagNode(null, 'parent', null);
        resolver.setParentNode(parent);
        assert.equal(resolver.getParentNode(), parent, name);
        assert.equal(Number(resolver.lastUpdate), 123456, name);
        resolver.setParentNode(null);
        assert.equal(resolver.getParentNode(), null, name);
        assert.equal(Number(resolver.lastUpdate), 123456, name);
        assert.equal(calls.length, 0, name);
    }
});

test('node resolver assignment still invokes the hook on the receiving node', () => {
    for (const [name, {gnr}] of Object.entries(loadPair())) {
        const resolver = new gnr.GnrBagResolver({}, false, 10, () => 7);
        const calls = [];
        resolver.onSetResolver = function(node) {
            calls.push(node);
            assert.equal(this.getParentNode(), node, name);
            node.newBagRow = () => 'row';
        };
        const node = new gnr.GnrBagNode(null, 'item', null);
        resolver.setParentNode(node);
        assert.equal(node.newBagRow, undefined, name);
        node.setResolver(resolver);
        assert.equal(calls.length, 1, name);
        assert.equal(calls[0], node, name);
        assert.equal(node.newBagRow(), 'row', name);
        assert.equal(node.getResolver(), resolver, name);
    }
});
