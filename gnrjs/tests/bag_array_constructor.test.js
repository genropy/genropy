const assert = require('node:assert/strict');
const {test} = require('node:test');
const vm = require('node:vm');
const {loadPair} = require('./bag_audit_harness.cjs');
const plain = value => JSON.parse(JSON.stringify(value));

test('array record construction matches legacy labels, values and autolist metadata', () => {
    const {legacy, selected} = loadPair();
    const input = [{name: 'Anna', count: 0}, {name: 'Mario', count: 2}];
    for (const context of [legacy, selected]) {
        const {gnr} = context;
        const source = vm.runInContext(JSON.stringify(input), context);
        const bag = new gnr.GnrBag(source);
        assert.deepEqual(Array.from(bag.keys()), ['r_0', 'r_1']);
        assert.equal(bag.getItem('r_0.name'), 'Anna');
        assert.equal(bag.getItem('r_0.count'), 0);
        assert.equal(bag.getNode('r_1').attr._autolist, true);
        assert.ok(bag.getItem('r_0') instanceof gnr.GnrBag);
        assert.deepEqual(plain(bag.asDict(true)), input);
        bag.getItem('r_0').setItem('name', 'Changed');
        assert.equal(source[0].name, 'Anna');
        assert.equal(new gnr.GnrBag([]).len(), 0);
    }
});

test('tuple construction matches legacy replacement, order and attributes', () => {
    for (const context of Object.values(loadPair())) {
        const bag = vm.runInContext(`new gnr.GnrBag([['a', 1, {caption: 'First'}],
            ['b', 2], ['a', 3, {caption: 'Updated'}]])`, context);
        assert.deepEqual(Array.from(bag.keys()), ['a', 'b']);
        assert.equal(bag.getItem('a'), 3);
        assert.equal(bag.getNode('a').attr.caption, 'Updated');
    }
});

test('array decoding preserves specialized source nodes and constructor emits no deprecation', () => {
    const {selected: c} = loadPair();
    const warnings = [];
    c.console = {...c.console, warn: message => warnings.push(message)};
    const source = new c.gnr.GnrDomSource([['pane', null, {tag: 'div'}]]);
    assert.ok(source.getNode('pane') instanceof c.gnr.GnrDomSourceNode);
    assert.equal(source.getNode('pane').attr.tag, 'div');
    assert.deepEqual(warnings, []);
    assert.equal(c.GenroBagJS.Bag.prototype.fillFrom, undefined);
});
