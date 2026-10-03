const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

for (const entry of ['load', 'resolve']) {
    test(`callback ${entry} merges live defaults and inherited parameters without mutating inputs`, () => {
        for (const [name, {gnr}] of Object.entries(loadPair())) {
            const defaults = Object.assign(Object.create({inherited: 3}), {a: 1, b: 2});
            let receiver;
            const resolver = new gnr.GnrBagCbResolver({parameters: defaults,
                method: function(kw) { receiver = this; return kw; }});
            const options = Object.assign(Object.create({fromCall: 9}), {b: 4});
            const first = resolver[entry](options);
            assert.deepEqual([first.a, first.b, first.inherited, first.fromCall], [1, 4, 3, 9], name);
            assert.equal(receiver, resolver, name);
            assert.deepEqual({...defaults}, {a: 1, b: 2}, name);
            assert.deepEqual({...options}, {b: 4}, name);
            defaults.a = 8;
            assert.equal(resolver[entry](options).a, 8, name);
            resolver.parameters = {a: 10};
            const replaced = resolver[entry]({b: null});
            assert.equal(replaced.a, 10, name);
            assert.equal(replaced.b, null, name);
            assert.equal(replaced.inherited, undefined, name);
        }
    });
}
test('callback without defaults accepts omitted call parameters', () => {
    for (const [name, {gnr}] of Object.entries(loadPair())) {
        const resolver = new gnr.GnrBagCbResolver({method: kw => kw});
        assert.deepEqual({...resolver.load()}, {}, name);
    }
});
