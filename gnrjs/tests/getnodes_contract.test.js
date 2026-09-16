const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const {loadPair} = require('./bag_audit_harness.cjs');
const source = fs.readFileSync(path.resolve(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js'), 'utf8');
const body = source.split('    moveRow(rowKey, position) {')[1].split('\n    moveRowFrom(')[0];
const move = new Function('rowKey', 'position', body.slice(0, body.lastIndexOf('}')));

test('grouplet reordering uses Bag API in both legacy and new modes', () => {
    const pair = loadPair();
    for (const context of [pair.legacy, pair.selected]) {
        for (const [key, position, expected] of [
            ['a', '>c', 'bca'], ['c', '<a', 'cab'], ['a', '<c', 'bac'],
            ['c', '>a', 'acb'], ['a', '<b', 'abc'], ['b', '>a', 'abc']
        ]) {
            const bag = new context.gnr.GnrBag({a: 1, b: 2, c: 3});
            bag.setBackRef(); const node = bag.getNode(key); let events = 0;
            bag.subscribe('test', {any: () => events++});
            move.call({getData: () => bag}, key, position);
            assert.equal(bag.keys().join(''), expected);
            assert.equal(bag.getNode(key), node);
            assert.equal(node.getParentBag(), bag);
            assert.equal(events, 0);
        }
    }
});
test('new mixin returns a list snapshot of shared nodes', () => {
    const {selected} = loadPair(); const bag = new selected.gnr.GnrBag({a: 1, b: 2});
    const nodes = bag.getNodes(); nodes.pop();
    assert.equal(bag.len(), 2);
    nodes[0].setValue(3);
    assert.equal(bag.getItem('a'), 3);
    bag.setItem('c', 4);
    assert.equal(nodes.length, 1);
});
