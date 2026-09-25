const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

test('orphaned stays in compatibility mixin and detaches without removing the node', () => {
    const {legacy, selected} = loadPair();
    assert.equal(selected.GenroBagJS.BagNode.prototype.orphaned, undefined);
    for (const {gnr} of [legacy, selected]) {
        const root = new gnr.GnrBag();
        root.setItem('branch.child.leaf', 1);
        root.setBackRef();
        const branch = root.getNode('branch');
        const value = branch.getValue('static');
        const child = value.getItem('child');
        const events = [];
        root.subscribe('watch', {any: event => events.push(event)});
        assert.equal(branch.orphaned(), branch);
        assert.equal(branch.getParentBag() == null, true);
        assert.equal(root.getNode('branch'), branch);
        assert.equal(value.hasBackRef(), false);
        assert.equal(child.hasBackRef(), false);
        value.setItem('new', 2);
        assert.equal(events.length, 0);
        assert.equal(branch.orphaned(), branch);
    }
});

test('orphaned neither resolves nor discards the node resolver', () => {
    for (const {gnr} of Object.values(loadPair())) {
        let calls = 0;
        const resolver = new gnr.GnrBagResolver({}, false, -1, () => ++calls);
        const bag = new gnr.GnrBag();
        bag.setItem('lazy', resolver);
        const node = bag.getNode('lazy');
        assert.equal(node.orphaned(), node);
        assert.equal(node.getResolver(), resolver);
        assert.equal(calls, 0);
        assert.equal(bag.getNode('lazy'), node);
    }
});
