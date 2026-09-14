const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

const legacyMethods = [
    'getStringId', 'isExpired', 'isLoaded', 'isLoading', 'getParentNode',
    'getParentBag', 'orphaned', 'isChildOf', 'setParentBag', 'getFullpath',
    'backrefOk', 'getValue2', 'getFormattedValue', 'getValue', 'clearValue',
    'setValue', 'refresh', 'getStaticValue', 'setStaticValue', 'setResolver',
    'getResolver', 'resetResolver', 'getAttr', 'getInheritedAttributes',
    'isAncestor', 'isDescendant', 'attributeOwnerNode', 'hasAttr',
    'replaceAttr', 'setAttribute', 'updAttributes', 'setAttr', 'delAttr',
    '_toXmlBlock', 'toJSONString', 'doWithValue', 'parentshipLevel'
];

test('selected GnrBagNode exposes every legacy method with matching arity', () => {
    const {legacy, selected} = loadPair();
    for (const name of legacyMethods) {
        assert.equal(typeof selected.gnr.GnrBagNode.prototype[name], 'function', name);
        assert.equal(selected.gnr.GnrBagNode.prototype[name].length,
            legacy.gnr.GnrBagNode.prototype[name].length, name);
    }
});

test('selected GnrBagNode constructor preserves legacy identity and resolver state', () => {
    const {legacy, selected} = loadPair();
    const snapshots = [];
    for (const context of [legacy, selected]) {
        const resolver = new context.gnr.GnrBagResolver({cacheTime: 10});
        const node = new context.gnr.GnrBagNode(null, '#id', 'ignored', {nullable: null}, resolver);
        assert.equal(node.label, 'generated');
        assert.equal(node._value, null);
        assert.equal(node._parentbag, null);
        assert.equal(node._resolver, resolver);
        snapshots.push({status: node._status, locked: node.locked,
            callback: node._onChangedValue, nullable: node.attr.nullable});
    }
    assert.deepEqual(snapshots[1], snapshots[0]);
});

test('selected ancestry preserves graph behavior and orphaned parent is null', () => {
    const {legacy, selected} = loadPair();
    const snapshots = [];
    for (const context of [legacy, selected]) {
        const root = new context.gnr.GnrBag();
        root.setItem('branch.child', 1);
        root.setBackRef();
        const branch = root.getNode('branch');
        const child = root.getNode('branch.child');
        assert.equal(child.isChildOf(branch), true);
        assert.equal(branch.isAncestor(child), true);
        assert.equal(child.isDescendant(branch), true);
        assert.equal(child.parentshipLevel(branch), 1);
        assert.equal(branch.getValue('static').hasBackRef(), true);
        assert.equal(branch.orphaned(), branch);
        snapshots.push(branch.getParentBag());
        assert.equal(branch.getValue('static').hasBackRef(), false);
    }
    assert.equal(snapshots[0], undefined);
    assert.equal(snapshots[1], null);
});

test('selected GnrBagNode attribute edge cases match legacy truthy defaults', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        const node = new context.gnr.GnrBagNode(null, 'item', 1,
            {zero: 0, empty: '', flag: false, remove: 1});
        assert.equal(node.getAttr('missing', 0), null);
        assert.equal(node.hasAttr('zero', 1), false);
        assert.equal(node.hasAttr('zero', 0), true);
        node.delAttr('remove,empty');
        assert.deepEqual({...node.attr}, {zero: 0, flag: false});
        node.replaceAttr({next: 2});
        assert.deepEqual({...node.attr}, {next: 2});
    }
});

test('selected GnrBagNode refresh and reset delegate with legacy conditions', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        const node = new context.gnr.GnrBagNode(null, 'item', 1);
        const calls = [];
        node.isExpired = () => false;
        node.getValue = mode => calls.push(mode);
        node.refresh(false);
        node.refresh(true);
        assert.deepEqual(calls, ['reload']);
        assert.throws(() => node.resetResolver());
    }
});

test('selected GnrBagNode formatting and XML serialization match legacy', () => {
    const {legacy, selected} = loadPair();
    const results = [];
    for (const context of [legacy, selected]) {
        const scalar = new context.gnr.GnrBagNode(null, 'amount', '12',
            {name_long: 'Amount'});
        const child = new context.gnr.GnrBag({value: 1});
        child.asHtmlTable = kwargs => `table:${kwargs.headers}:${kwargs.cells}`;
        const table = new context.gnr.GnrBagNode(null, 'rows', child, {_autoTable: true});
        results.push({
            formatted: scalar.getFormattedValue(),
            table: table.getFormattedValue(),
            xml: scalar._toXmlBlock({})
        });
        assert.throws(() => scalar.toJSONString(), /toJSONString/);
    }
    assert.deepEqual(results[1], results[0]);
});

test('selected GnrBagNode setValue preserves callback order, fired value and return', () => {
    const {legacy, selected} = loadPair();
    const snapshots = [];
    for (const context of [legacy, selected]) {
        const bag = new context.gnr.GnrBag({item: 1});
        bag.setBackRef();
        const node = bag.getNode('item');
        const log = [];
        node._onChangedValue = () => log.push('callback');
        bag.subscribe('audit', {upd: event => log.push(`event:${event.fired}`)});

        const returned = node.setValue(2, true, null, null, true);
        snapshots.push({value: node.getValue('static'), returned, log});
    }
    assert.deepEqual(snapshots[1], snapshots[0]);
});

test('selected GnrBagNode replacement leaves the old subtree independent', () => {
    const {selected} = loadPair();
    const oldValue = new selected.gnr.GnrBag({child: 1});
    const bag = new selected.gnr.GnrBag();
    bag.setItem('item', oldValue);
    bag.setBackRef();
    const events = [];
    bag.subscribe('watch', {any: event => events.push(event)});
    bag.getNode('item').setValue('replacement', false);
    assert.equal(oldValue._parent, null);
    assert.equal(oldValue._parentNode, null);
    assert.equal(oldValue.getNode('child').getParentBag(), oldValue);
    oldValue.setItem('child', 2);
    assert.equal(events.length, 0);
});

test('selected value callback matches legacy arguments, timing and silent updates', () => {
    const {legacy, selected} = loadPair();
    for (const trigger of [true, false, null, {source: 'relation'}]) {
        for (const value of [1, 2]) {
            const snapshots = [];
            for (const context of [legacy, selected]) {
                const bag = new context.gnr.GnrBag({item: 1});
                bag.setBackRef();
                const node = bag.getNode('item');
                const log = [];
                node._onChangedValue = function(n, next, old, cause) {
                    log.push({receiver: this === node, node: n === node,
                        next, old, cause, current: n.getValue('static'), caption: n.attr.caption});
                };
                bag.subscribe('watch', {upd: () => log.push('event')});
                node.setValue(value, trigger, {caption: 'ready'});
                snapshots.push(log);
            }
            assert.deepEqual(snapshots[1], snapshots[0]);
        }
    }
});

test('selected setValue returns undefined with both adapter and standalone signatures', () => {
    const {selected} = loadPair();
    const bag = new selected.gnr.GnrBag({item: 1});
    const node = bag.getNode('item');
    assert.equal(node.setValue(2), undefined);
    assert.equal(node.getValue('static'), 2);
    assert.equal(node.setValue(3, false, null, null, true, null), undefined);
    assert.equal(node.getValue('static'), 3);
});

test('fireItem matches legacy assignment, event and silent reset sequence', () => {
    const {legacy, selected} = loadPair();
    const snapshots = [];
    for (const context of [legacy, selected]) {
        const bag = new context.gnr.GnrBag({command: null});
        bag.setBackRef();
        const node = bag.getNode('command');
        const log = [];
        node._onChangedValue = (n, value, oldvalue, trigger) => {
            log.push({kind: 'callback', value, oldvalue, trigger, current: n.getValue('static')});
        };
        bag.subscribe('watch', {upd: e => log.push({kind: 'event', value: e.value,
            fired: e.fired, current: node.getValue('static')})});
        bag.fireItem('command', 42);
        snapshots.push({log, final: node.getValue('static')});
    }
    assert.deepEqual(snapshots[1], snapshots[0]);
    assert.deepEqual(snapshots[1].log.map(e => e.kind), ['callback', 'event', 'callback']);
    assert.equal(snapshots[1].final, null);
});

test('initial loaded status still resolves a fresh resolver on first access', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        let calls = 0;
        const resolver = new context.gnr.GnrBagCbResolver({method: () => ++calls}, false, 60);
        const node = new context.gnr.GnrBagNode(null, 'item', null, null, resolver);
        assert.equal(node.isLoaded(), true);
        assert.equal(calls, 0);
        assert.equal(node.isExpired(), true);
        assert.equal(node.getValue(), 1);
        assert.equal(calls, 1);
        assert.equal(node.isLoaded(), true);
        assert.equal(node.getValue(), 1);
        assert.equal(calls, 1);
    }
});
