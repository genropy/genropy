const assert = require('node:assert/strict');
const {test} = require('node:test');
const vm = require('node:vm');
const {loadPair} = require('./bag_audit_harness.cjs');

function evaluatePair(source) {
    const pair = loadPair();
    const run = context => JSON.parse(vm.runInContext(
        `JSON.stringify((function(){${source}})())`, context));
    return {legacy: run(pair.legacy), selected: run(pair.selected)};
}

test('pointer expressions transform nested values and attributes', () => {
    const result = evaluatePair(`
        const bag = new gnr.GnrBag();
        const branch = new gnr.GnrBag();
        branch.setItem('beta', 3, {caption: 'hello'});
        bag.setItem('alfa', branch);
        return [
            bag.getItem('alfa.beta?=#v+"px"'),
            bag.getItem('alfa.beta?=!#v'),
            bag.getItem('alfa.beta?caption?=#v.toUpperCase()'),
            bag.get('alfa|=#v.getItem("beta")+1')
        ];
    `);
    assert.deepEqual(result.selected, result.legacy);
    assert.deepEqual(result.selected, ['3px', false, 'HELLO', 4]);
});

test('legacy access selectors retain value, attribute and nested Bag semantics', () => {
    const result = evaluatePair(`
        const bag = new gnr.GnrBag();
        const branch = new gnr.GnrBag();
        branch.setItem('beta', 3, {caption: 'hello'});
        branch.setItem('gamma', 4);
        bag.setItem('alfa', branch, {caption: 'branch'});
        return [
            bag.getItem('alfa.beta?'),
            bag.getItem('alfa.beta?#attr'),
            bag.getItem('alfa?#keys'),
            bag.getItem('alfa.beta?#node').label,
            bag.getItem('alfa?#digest:#k'),
            bag.getItem('alfa~beta'),
            bag.get('alfa~beta'),
            bag.getItem('alfa?caption'),
            bag.getItem('missing', 'fallback'),
            bag.getItem('missing', ''),
            bag.getItem('missing', 0)
        ];
    `);
    assert.deepEqual(result.selected, result.legacy);
});

test('htraverse isolates expression dots and preserves terminal tuple semantics', () => {
    const result = evaluatePair(`
        const bag = new gnr.GnrBag();
        bag.setItem('alfa', new gnr.GnrBag({beta: 'hello'}));
        const direct = bag.htraverse('alfa.beta?=#v.toUpperCase()');
        const blocked = new gnr.GnrBag({alfa: 1}).htraverse('alfa.beta?=#v');
        const parts = ['alfa', 'beta'];
        const fromArray = bag.htraverse(parts);
        const createdBag = new gnr.GnrBag({scalar: 1});
        const created = createdBag.htraverse('scalar.leaf', true);
        return [[direct.value === bag.getItem('alfa'), direct.label],
            [blocked.value, blocked.label],
            [fromArray.value === bag.getItem('alfa'), fromArray.label], parts,
            [created.value === createdBag.getItem('scalar'), created.label,
                createdBag.getItem('scalar') instanceof gnr.GnrBag]];
    `);
    assert.deepEqual(result.selected, result.legacy);
});

test('Deferred traversal applies selectors and expressions after resolution', () => {
    const result = evaluatePair(`
        const bag = new gnr.GnrBag();
        bag.setItem('alfa', null);
        const branch = new gnr.GnrBag();
        branch.setItem('beta', 2, {caption: 'hello'});
        const deferred = new dojo.Deferred();
        bag.getNode('alfa').getValue = function(){ return deferred; };
        const returned = bag.getItem('alfa.beta?caption?=#v.toUpperCase()');
        deferred.callback(branch);
        return [returned === deferred, deferred.fired, deferred.results];
    `);
    assert.deepEqual(result.selected, result.legacy);
    assert.deepEqual(result.selected, [true, 0, ['HELLO', null]]);
});

test('autocreate preserves insertion reasons and nested traversal overrides', () => {
    const result = evaluatePair(`
        const root = new gnr.GnrBag();
        const child = new gnr.GnrBag({leaf: 3});
        root.setItem('child', child);
        root.setBackRef();
        let calls = 0;
        const original = child.htraverse;
        child.htraverse = function(...args) { calls++; return original.apply(this, args); };
        const read = root.getItem('child.leaf');
        const events = [];
        root.subscribe('probe', {any: e => events.push([e.evt, e.reason, e.node.label])});
        root.htraverse('newbranch.subbranch.leaf', true);
        return {read, calls, events};
    `);
    assert.deepEqual(result.selected, result.legacy);
    assert.equal(result.selected.calls, 1);
    assert.deepEqual(result.selected.events.map(e => e[1]), ['autocreate', 'autocreate']);
});

test('parent access matches legacy at root and two nested levels', () => {
    const result = evaluatePair(`
        const root = new gnr.GnrBag();
        const child = new gnr.GnrBag();
        const grandchild = new gnr.GnrBag();
        root.setItem('child', child);
        child.setItem('grandchild', grandchild);
        root.setBackRef();
        const identify = value => value === root ? 'root' : value === child ? 'child' :
            value === grandchild ? 'grandchild' : value;
        const read = (bag, method, path) => {
            try { return identify(bag[method](path)); }
            catch (error) { return {error: error.name}; }
        };
        return [root, child, grandchild].map(bag =>
            ['get', 'getItem'].map(method =>
                ['', '#parent', '../', '../../'].map(path => read(bag, method, path))));
    `);
    assert.deepEqual(result.selected, result.legacy);
});

test('pointer grammar matches legacy across missing paths, falsy values and defaults', () => {
    const result = evaluatePair(`
        const bag = new gnr.GnrBag();
        bag.setItem('value', 0, {zero:0, no:false, text:'hello'});
        bag.setItem('branch', new gnr.GnrBag({child:4}));
        const paths = ['value', 'value?', 'value?zero', 'value?no', 'value?missing',
            'value?=#v+1', 'value?text?=#v.toUpperCase()', 'value|=#v+2',
            'value~zero', 'branch~child', 'branch?#keys', 'branch?#digest:#k',
            'missing?=#v+1', 'missing.child?=#v', 'value?=#v===0 ? "yes" : "no"'];
        return paths.map(path => [undefined, null, false, 0, '', 'fallback'].map(fallback => {
            try { const value = bag.getItem(path, fallback); return {value, type:typeof value}; }
            catch (error) { return {error:error.name}; }
        }));
    `);
    assert.deepEqual(result.selected, result.legacy);
});

test('Deferred traversal dispatches child overrides and preserves failure outcomes', () => {
    const result = evaluatePair(`
        const root = new gnr.GnrBag();
        root.setItem('child', null);
        const child = new gnr.GnrBag({leaf: 5});
        let calls = 0;
        const original = child.htraverse;
        child.htraverse = function(...args) {calls++; return original.apply(this, args);};
        const pending = new dojo.Deferred();
        root.getNode('child').getValue = () => pending;
        const returned = root.getItem('child.leaf?=#v*2');
        pending.callback(child);
        const failed = new dojo.Deferred();
        root.getNode('child').getValue = () => failed;
        const returnedFailure = root.getItem('child.leaf?=#v*2');
        failed.errback(new Error('load failed'));
        return [calls, returned === pending, pending.results[0],
            returnedFailure === failed, failed.fired, failed.results[1].message];
    `);
    assert.deepEqual(result.selected, result.legacy);
    assert.deepEqual(result.selected, [1, true, 10, true, 1, 'load failed']);
});
