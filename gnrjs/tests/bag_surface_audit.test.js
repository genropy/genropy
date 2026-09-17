const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

const accepted = require('./bag_accepted_removals.cjs');
const classNames = ['GnrBagResolver', 'GnrBagCbResolver'];
test('documented removed classes and public members stay absent', () => {
    const {legacy, selected} = loadPair();
    for (const name of accepted.classes) {
        assert.equal(typeof legacy.gnr[name], 'function', name);
        assert.equal(selected.gnr[name], undefined, name);
    }
    for (const [name, members] of Object.entries(accepted.members)) {
        for (const member of members) {
            assert.equal(typeof legacy.gnr[name].prototype[member], 'function', `${name}.${member}`);
            assert.equal(selected.gnr[name].prototype[member], undefined, `${name}.${member}`);
        }
    }
});
for (const name of classNames) {
    test(`${name} retains all other legacy public prototype members`, () => {
        const {legacy, selected} = loadPair();
        const missing = new Set();
        for (let prototype = legacy.gnr[name].prototype;
             prototype && prototype !== Object.prototype;
             prototype = Object.getPrototypeOf(prototype)) {
            for (const key of Object.getOwnPropertyNames(prototype)) {
                if (key === 'constructor' || key.startsWith('_') || accepted.members[name].includes(key)) continue;
                if (!(key in selected.gnr[name].prototype)) missing.add(`${name}.${key}`);
                else if (typeof prototype[key] === 'function') {
                    assert.equal(typeof selected.gnr[name].prototype[key], 'function', `${name}.${key}`);
                }
            }
        }
        assert.deepEqual([...missing], []);
    });
}

function compare(name, callback) {
    test(name, () => {
        const {legacy, selected} = loadPair();
        const run = context => JSON.stringify(callback(context));
        assert.equal(run(selected), run(legacy));
    });
}
compare('legacy HTML table formatting', c => {
    const b = new c.gnr.GnrBag();
    b.setItem('row', new c.gnr.GnrBag({name:'Alice', count:2}));
    return b.asHtmlTable({headers:true,cells:true});
});
test('selected Bag replaces legacy __str__ with native text rendering', () => {
    const {legacy, selected} = loadPair();
    assert.equal(typeof legacy.gnr.GnrBag.prototype.__str__, 'function');
    const bag = new selected.gnr.GnrBag({name:'Alice', count:2});
    assert.equal(bag.__str__, undefined);
    for (const render of ['toString', 'toStringTree']) {
        const text = bag[render]();
        assert.equal(typeof text, 'string');
        for (const part of ['name', 'Alice', 'count', '2']) assert.ok(text.includes(part));
    }
});
test('merge remains absent in selected JavaScript Bag pending shared API review', () => {
    const {legacy, selected} = loadPair();
    const oldBag = new legacy.gnr.GnrBag({a:1});
    assert.equal(oldBag.merge(new legacy.gnr.GnrBag({a:2})), undefined);
    assert.equal(oldBag.getItem('a'), 1);
    assert.equal(new selected.gnr.GnrBag().merge, undefined);
});
test('pathsplit placeholder is intentionally absent from selected JavaScript Bag', () => {
    const {legacy, selected} = loadPair();
    const oldBag = new legacy.gnr.GnrBag({a:1});
    assert.equal(oldBag.pathsplit('a.b'), undefined);
    assert.equal(oldBag.getItem('a'), 1);
    assert.equal(new selected.gnr.GnrBag().pathsplit, undefined);
});
compare('public node creation and rowchild helpers', c => {
    c.genro.assert = (value, message) => assert.ok(value,message);
    const b = new c.gnr.GnrBag();
    b.setItem('created',42);
    const n = b.getNode('created');
    b.rowchild('#code',{code:'row',caption:'Row'});
    return [n.label,n.getValue(),b.getAttr('row')];
});
test('removed automatic modification tracking does not reappear after mutations', () => {
    const {selected: {gnr}} = loadPair();
    const bag = new gnr.GnrBag(); bag.setBackRef();
    assert.equal(bag.set_modified, undefined);
    const before = bag.get_modified();
    bag.setItem('a', 1); bag.popNode('a');
    assert.equal(bag.get_modified(), before);
});

compare('moveNode order and insert/delete notifications', c => {
    const b = new c.gnr.GnrBag({a:1,b:2,c:3});b.setBackRef();
    const events=[];b.subscribe('capture',{any:kw=>events.push([kw.evt,kw.node.label,kw.ind])});
    b.moveNode(0,2,true);
    return [b.keys(),events];
});
compare('index enumeration of nested Bags', c => {
    const b = new c.gnr.GnrBag();b.setItem('branch',new c.gnr.GnrBag());
    return [b.getIndex().map(x=>[x[0],x[1].label]),b.getIndexList(),b.getIndexList(true)];
});
test('index enumeration handles scalar and null leaves', () => {
    const {selected:c}=loadPair();const b=new c.gnr.GnrBag({a:1,b:null});
    assert.equal(JSON.stringify(b.getIndexList()), '["a","b"]');
});

test('supported globals remain available without retired resolver classes', () => {
    const {legacy, selected} = loadPair();
    for (const name of Object.keys(legacy.gnr)) {
        if (!accepted.classes.includes(name)) assert.ok(name in selected.gnr, `gnr.${name}`);
    }
});

compare('public insertion bubbles with original location', c => {
    const root=new c.gnr.GnrBag(), child=new c.gnr.GnrBag();root.setItem('child',child);root.setBackRef();
    const events=[];root.subscribe('listen',{any:kw=>events.push([kw.evt,kw.pathlist,kw.where===child,kw.base===root])});
    child.setItem('created',42);
    return events;
});
compare('nested table formatting respects empty values', c => {
    c._F = value=>value==null?'':String(value);
    const b=new c.gnr.GnrBag({a:1,empty:null});
    return b.asNestedTable({omitEmpty:true},'static');
});
test('public insertion and removal maintain parent links without backrefOk', () => {
    const {selected: {gnr}} = loadPair();
    const root = new gnr.GnrBag(), child = new gnr.GnrBag({leaf: 1});
    root.setItem('child', child); root.setBackRef();
    const node = root.getNode('child');
    assert.equal(node.getParentBag(), root);
    assert.equal(child.getParentNode(), node);
    assert.equal(child.getNode('leaf').getParentBag(), child);
    root.popNode('child');
    assert.equal(node.getParentBag(), null);
    assert.equal(child.getParentNode(), null);
    assert.equal(child.getNode('leaf').getParentBag(), child);
});

compare('XML blocks preserve attributes and nested content', c => {
    const b=new c.gnr.GnrBag();b.setItem('a',1,{caption:'A'});b.setItem('child',new c.gnr.GnrBag({b:'text'}));
    return b.toXmlBlock({});
});

test('native inherited methods stay callable without legacy enumeration', () => {
    const {selected} = loadPair();
    for (const name of ['keys', 'items', 'values', 'update']) {
        assert.equal(typeof selected.gnr.GnrBag.prototype[name], 'function');
        assert.equal(Object.getOwnPropertyDescriptor(selected.GenroBagJS.Bag.prototype, name).enumerable, false);
    }
});

test('selected update uses the library implementation without a semantic override', () => {
    const {selected}=loadPair();
    assert.equal(selected.gnr.GnrBag.prototype.update, selected.GenroBagJS.Bag.prototype.update);
    const source=new selected.gnr.GnrBag({value:null});
    const target=new selected.gnr.GnrBag({value:1});
    target.update(source,'static');
    assert.equal(target.getItem('value'),null);
});
