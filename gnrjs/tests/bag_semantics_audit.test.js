const assert = require('node:assert/strict');
const {test} = require('node:test');
const vm = require('node:vm');
const {loadPair} = require('./bag_audit_harness.cjs');

function parity(name, scenario) {
    test(name, () => {
        const pair = loadPair();
        const run = context => JSON.parse(vm.runInContext(
            `JSON.stringify((function(){${scenario}})())`, context));
        assert.deepEqual(run(pair.selected), run(pair.legacy));
    });
}

parity('digest retains row shape, columns flag, static values and field access', `
 const b=new gnr.GnrBag(); b.setItem('a', new gnr.GnrBag({x:2}), {q:3}); b.setItem('b', new gnr.GnrBag({x:4}), {q:5});
 return [b.digest('#k'), b.digest('#a.q',true), b.digest('x'), b.digest('#v.x'), b.columns('q',true)];
`);
test('sum follows the shared strict contract instead of legacy coercion', () => {
    const {selected: {gnr}} = loadPair();
    const bag = new gnr.GnrBag({a: 2, b: true, c: '9', d: null});
    assert.equal(bag.sum(), 3);
    assert.throws(() => bag.sum('#v', true), {name: 'TypeError'});
    assert.equal(bag.sum('#v', true, n => n.label !== 'c'), null);
    assert.equal(bag.sum('#v', true, n => ['a', 'b'].includes(n.label)), 3);
});

for (const mode of ['a','a*','d','d*','asc','desc','>','<']) {
    parity('sort preserves legacy mode '+mode, `
 const b=new gnr.GnrBag(); b.setItem('b','z'); b.setItem('A','a'); b.setItem('c',null); b.setItem('B','B');
 b.sort('#k:${mode}'); const k=b.keys(); b.sort('#v:${mode}'); return [k,b.keys()];
`);
}
parity('sort uses nested Bag fields', `
 const b=new gnr.GnrBag(); b.setItem('a',new gnr.GnrBag({x:2})); b.setItem('b',new gnr.GnrBag({x:1})); b.sort('x'); return b.keys();
`);
parity('asDict supports recursive, flat, null exclusion and executable text filtering', `
 const b=new gnr.GnrBag(); b.setItem('Branch', new gnr.GnrBag({x:2})); b.setItem('empty',new gnr.GnrBag()); b.setItem('null',null); b.setItem('script','code::JS');
 return [b.asDict(true), b.asDict('flat'), b.asDict(true,true)];
`);
parity('asDict supports automatic lists', `
 const b=new gnr.GnrBag(); b.setItem('a',1,{_autolist:true}); b.setItem('b',2); return b.asDict(true);
`);
test('addItem renames duplicate labels and retains both values', () => {
    const {selected: {gnr}} = loadPair();
    const bag = new gnr.GnrBag();
    bag.addItem('a', 1); bag.addItem('a', 2);
    assert.deepEqual(Array.from(bag.keys()), ['a', 'a__dup_1']);
    assert.deepEqual(Array.from(bag.values()), [1, 2]);
});

parity('setItem empty path merges values and attribute paths retain value', `
 const b=new gnr.GnrBag(); b.setItem('a',1,{x:2}); b.setItem('',new gnr.GnrBag({b:3})); b.setItem('a?y',4); return [b.keys(),b.getItem('a'),b.getAttr('a')];
`);
parity('lazySet and fired provide legacy event metadata', `
 const b=new gnr.GnrBag(); b.setBackRef(); b.setItem('a',1,{x:2}); let events=[];
 b.subscribe('x',{any:k=>events.push([k.evt,k.fired,k.updvalue,k.updattr,k.changedAttr])});
 b.setItem('a',1,{x:2},{lazySet:true}); b.setItem('a',1,{x:3},{lazySet:true}); b.fireItem('a',4);
 return [events,b.getItem('a')];
`);
test('pop and delItem preserve suppression and returns with null for a detached parent', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        const bag = new context.gnr.GnrBag();
        bag.setBackRef();
        bag.setItem('a', 1);
        bag.setItem('c', 3);
        const events = [];
        bag.subscribe('watch', {any: event => events.push(event.evt)});
        assert.equal(bag.pop('a', false), 1);
        const node = bag.popNode('c', false);
        assert.equal(node.getValue('static'), 3);
        assert.equal(bag.pop('absent'), undefined);
        assert.equal(bag.delItem('absent'), undefined);
        assert.equal(bag.getNode('a'), null);
        assert.equal(bag.getNode('c'), null);
        assert.equal(node.getParentBag(), context === selected ? null : undefined);
        assert.deepEqual(events, []);
    }
});
parity('update static mode still replaces null and merges attributes', `
 const b=new gnr.GnrBag(); b.setItem('a',1,{x:2}); const other=new gnr.GnrBag(); other.setItem('a',null,{y:3}); b.update(other,'static'); return [b.getItem('a'), b.getAttr('a')];
`);
test('update replaces content and reports only the effective change with its reason', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        const bag = new context.gnr.GnrBag();
        bag.setBackRef();
        bag.setItem('a', new context.gnr.GnrBag({x: 1, y: 2}));
        const source = new context.gnr.GnrBag();
        source.setItem('a', new context.gnr.GnrBag({x: 3}), {__replace: true});
        const events = [];
        bag.subscribe('watch', {any: event => events.push(event)});
        bag.update(source, null, 'audit');
        assert.deepEqual(Array.from(bag.getItem('a').keys()), ['x']);
        assert.equal(bag.getItem('a.x'), 3);
        assert.deepEqual({...source.getAttr('a')}, {});
        assert.deepEqual(events.map(e => e.reason), context === selected ? ['audit'] : ['audit', 'audit']);
        if (context === selected) {
            assert.equal(events[0].updvalue, true);
            assert.equal(events[0].updattr, false);
        }
    }
});
test('deepCopy preserves each implementation collision labels and independent nested Bags', () => {
    const pair = loadPair();
    for (const [name, context] of Object.entries(pair)) {
        const result = JSON.parse(vm.runInContext(`JSON.stringify((()=>{
            const b=new gnr.GnrBag(); b.addItem('a',new gnr.GnrBag({x:1})); b.addItem('a',2);
            const c=b.deepCopy(); c.getItem('#0').setItem('x',3);
            return [c.keys(), c.getItem('#0.x'), b.getItem('#0.x'), c.getItem('#1'),
                c.getNode('#1').xmlTag || null];
        })())`, context));
        // The active mixin now uses Python's rename-on-collision contract.
        assert.deepEqual(result, name === 'legacy'
            ? [['a', 'a'], 3, 1, 2, null]
            : [['a', 'a__dup_1'], 3, 1, 2, 'a']);
    }
});
parity('walk and forEach pass kwargs and index and honor early return', `
 const b=new gnr.GnrBag(); b.setItem('a',new gnr.GnrBag({x:1})); b.setItem('b',2); let visited=[];
 const result=b.walk((n,kw,i)=>{visited.push([n.label,kw.token,i]);return n.label==='a'?'__continue__':n.label==='b'?'stop':null;},'static',{token:5});
 let first=[]; b.forEach((n,kw,i)=>{first.push([n.label,kw.token,i]);return 'stop';},null,{token:6}); return [visited,result,first];
`);
test('fillFrom replaces contents while array construction retains legacy rows', () => {
    for (const [name, context] of Object.entries(loadPair())) {
        const result = JSON.parse(vm.runInContext(`JSON.stringify((()=>{
            const b=new gnr.GnrBag(); b.setItem('old',1); b.fillFrom({fresh:2});
            const list=new gnr.GnrBag([{x:1},{x:2}]);
            return [b.keys(),list.keys(),list.asDict(true)];
        })())`, context));
        assert.deepEqual(result, [name === 'legacy' ? ['old', 'fresh'] : ['fresh'],
            ['r_0', 'r_1'], [{x:1}, {x:2}]]);
    }
});
parity('items retain named key/value entries', `const b=new gnr.GnrBag({a:1,b:2}); return b.items();`);
test('setAttr autocreates nodes and preserves existing attributes by default', () => {
    const {selected: {gnr}} = loadPair();
    const bag = new gnr.GnrBag();
    bag.setAttr('a', {x: 1}); bag.setAttr('a', {y: 2});
    assert.deepEqual(Array.from(bag.keys()), ['a']);
    assert.deepEqual({...bag.getAttr('a')}, {x: 1, y: 2});
    assert.equal(bag.getAttr('missing'), null);
});

test('getNode retains attribute lookup but removes tuple lookup in the mixin', () => {
    for (const [kind, context] of Object.entries(loadPair())) {
        const b = new context.gnr.GnrBag();
        b.setItem('a', 1, {id: 'target'});
        assert.equal(b.getItem('#id=target'), 1);
        assert.equal(b.getNode('#id=target').label, 'a');
        if (kind === 'legacy') {
            const missing = b.getNode('missing', true);
            assert.equal(missing.obj, b);
            assert.equal(missing.node, null);
        } else {
            assert.throws(() => b.getNode('missing', true), /no longer supports asTuple/);
            assert.equal(b.getNode('missing'), null);
        }
    }
});
parity('XML serialization retains GenRoBag wrapper and legacy dtype encoding', `
 const b=new gnr.GnrBag(); b.setItem('a',1,{flag:true}); b.setItem('child',new gnr.GnrBag({x:'hello'})); return b.toXml();
`);
test('clearBackRef removes node backrefs in the new contract, unlike legacy JS', () => {
    for (const [kind, context] of Object.entries(loadPair())) {
        const b = new context.gnr.GnrBag();
        b.setBackRef();
        b.setItem('a', new context.gnr.GnrBag({x: 1}));
        const branch = b.getNode('a');
        const child = b.getItem('a');
        const leaf = child.getNode('x');
        b.clearBackRef();
        assert.equal(b.getBackRef(), false);
        assert.equal(child.getBackRef(), false);
        assert.equal(child.getParentNode(), null);
        assert.equal(branch.getParentBag(), kind === 'legacy' ? b : null);
        assert.equal(leaf.getParentBag(), kind === 'legacy' ? child : null);
        // Clearing upward links does not remove or replace the contained nodes.
        assert.equal(b.getNode('a'), branch);
        assert.equal(child.getNode('x'), leaf);
        assert.equal(child.getItem('x'), 1);
        b.setBackRef();
        assert.equal(branch.getParentBag(), b);
        assert.equal(leaf.getParentBag(), child);
        assert.equal(child.getParentNode(), branch);
    }
});
test('getNodeByAttr mixin retains legacy order and permits explicit level priority', () => {
    const pair = loadPair();
    for (const [kind, context] of Object.entries(pair)) {
        const b = new context.gnr.GnrBag();
        const child = new context.gnr.GnrBag();
        child.setItem('deep', 1, {match: 'yes'});
        b.setItem('branch', child);
        b.setItem('sibling', 2, {match: 'yes'});
        const expected = 'deep';
        if (kind === 'selected') {
            assert.equal(b.getNodeByAttr('match', 'yes', false, false).label, 'sibling');
        }
        assert.equal(b.getNodeByAttr('match', 'yes').label, expected);
        assert.equal(b.getNodeByAttr('match').label, expected);
        b.popNode('sibling');
        assert.equal(b.getNodeByAttr('match', 'yes').label, 'deep');
    }
});
parity('getNodeByValue traverses nested fields', `
 const b=new gnr.GnrBag(); b.setItem('a',new gnr.GnrBag({nested:{field:1}})); return b.getNodeByValue('nested.field',1).label;
`);
test('getNodes intentionally snapshots structure and retains filtering', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        const bag = new context.gnr.GnrBag({a: 1, b: 2});
        assert.equal(bag.getNodes() === bag._nodes, context === legacy);
        assert.equal(bag.getNodes(n => n.label === 'b')[0], bag.getNode('b'));
    }
});
test('root Bag uses null for its absent parent and preserves other absent accessors', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        const bag = new context.gnr.GnrBag();
        assert.equal(bag.getParent(), context === selected ? null : undefined);
        assert.equal(bag.attributes(), undefined);
        assert.equal(bag.resolver(), undefined);
    }
});
parity('clear sends reverse deletion positions without an invented reason', `
 const b=new gnr.GnrBag({a:1,b:2}); let events=[]; b.subscribe('x',{any:k=>events.push([k.evt,k.node.label,k.ind,k.reason])}); b.clear(true); return [events,b.len()];
`);

test('attribute-only events omit updvalue while value events include true', () => {
    const {legacy, selected} = loadPair();
    for (const context of [legacy, selected]) {
        const bag = new context.gnr.GnrBag({item: 1});
        bag.setBackRef();
        const events = [];
        bag.subscribe('watch', {any: event => events.push(event)});
        bag.getNode('item').setAttr({caption: 'changed'}, true, true);
        assert.equal(events.length, 1);
        assert.equal(Object.hasOwn(events[0], 'updvalue'), false);
        bag.getNode('item').setValue(2);
        assert.equal(events.length, 2);
        assert.equal(Object.hasOwn(events[1], 'updvalue'), true);
        assert.equal(events[1].updvalue, true);
    }
});
