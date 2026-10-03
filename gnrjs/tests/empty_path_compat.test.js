const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

test('empty path compatibility merges nodes and preserves unresolved resolvers', () => {
    for (const {gnr} of Object.values(loadPair())) {
        const bag = new gnr.GnrBag();
        bag.setItem('existing', 1);
        bag.setItem('child.old', 10);
        const source = new gnr.GnrBag();
        source.setItem('child.new', 20);
        let calls = 0;
        const resolver = new gnr.GnrBagCbResolver({method: () => { calls++; return 42; }});
        source.setItem('lazy', resolver, {caption: 'Lazy'});
        assert.equal(bag.setItem('', source), bag);
        assert.equal(calls, 0);
        assert.equal(bag.getNode('lazy').getResolver(), resolver);
        assert.equal(bag.getNode('lazy').attr.caption, 'Lazy');
        assert.deepEqual(Array.from(bag.getItem('child').keys()), ['new']);
        assert.equal(bag.getItem('existing'), 1);
        assert.equal(bag.setItem('', 123), bag);
        assert.equal(bag.setItem('', bag), bag);
        assert.equal(bag.len(), 3);
        assert.equal(bag.getNode(''), null);
    }
});
