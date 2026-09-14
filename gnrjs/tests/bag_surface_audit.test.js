const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

const classNames = ['GnrBag','GnrBagNode','GnrBagResolver','GnrBagFormula',
    'GnrBagGetter','GnrBagCbResolver','GnrDomSource','GnrDomSourceNode'];
test('every legacy Bag and DOM source prototype member remains available', () => {
    const {legacy, selected} = loadPair();
    const missing = [];
    for (const name of classNames) {
        for (let prototype = legacy.gnr[name].prototype;
             prototype && prototype !== Object.prototype;
             prototype = Object.getPrototypeOf(prototype)) {
            for (const key of Object.getOwnPropertyNames(prototype)) {
                if (!(key in selected.gnr[name].prototype)) missing.push(`${name}.${key}`);
                else if (typeof prototype[key] === 'function') {
                    assert.equal(typeof selected.gnr[name].prototype[key], 'function', `${name}.${key}`);
                }
            }
        }
    }
    assert.deepEqual(missing, []);
});

function compare(name, callback) {
    test(name, () => {
        const {legacy, selected} = loadPair();
        const run = context => JSON.stringify(callback(context));
        assert.equal(run(selected), run(legacy));
    });
}
compare('legacy object lists and HTML table formatting', c => {
    const b = new c.gnr.GnrBag();
    b.setItem('row', new c.gnr.GnrBag({name:'Alice', count:2}));
    return [b.asObjList('key'), b.asHtmlTable({headers:true,cells:true})];
});
compare('legacy string representations and empty compatibility hooks', c => {
    const b = new c.gnr.GnrBag({name:'Alice', count:2});
    return [b.__str__(), b.__str2__(), b.asString(), b.merge(), b.pathsplit()];
});
compare('node creation helpers and callback reads', c => {
    c.genro.assert = (value, message) => assert.ok(value,message);
    const b = new c.gnr.GnrBag();
    const n = b._getNode('created',true,42);
    b.rowchild('#code',{code:'row',caption:'Row'});
    return [n.label,n.getValue(),b.getAttr('row'),
        b.doWithItem('created',v=>v+1),b.doWithItem('absent',v=>v,7)];
});
compare('formula definitions with an explicitly bound evaluation parent', c => {
    const b = new c.gnr.GnrBag({a:2,b:3});
    b.defineSymbol({x:'a',y:'b'});
    b.defineFormula({total:'$x+$y'});
    const resolver = b.formula('total');
    resolver._parent = b;
    return resolver.resolve();
});
compare('modified tracking subscription lifecycle', c => {
    const b = new c.gnr.GnrBag(); b.setBackRef();
    const values = [b.get_modified()];
    b.set_modified(false); b.setItem('a',1); values.push(b.get_modified());
    b.set_modified(false); b.popNode('a'); values.push(b.get_modified());
    b.set_modified(null); b.setItem('a',2); values.push(b.get_modified());
    return values;
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

test('legacy constructor fields and globals remain addressable', () => {
    const {legacy,selected}=loadPair();
    for(const name of ['GnrBag','GnrBagNode','GnrBagResolver']) {
        const before=new legacy.gnr[name]();const after=new selected.gnr[name]();
        for(const key of Object.keys(before)) assert.ok(key in after,`${name}.${key}`);
    }
    for(const key of Object.keys(legacy.gnr)) assert.ok(key in selected.gnr,`gnr.${key}`);
});
compare('direct trigger API bubbles insertion with original location', c => {
    const root=new c.gnr.GnrBag(), child=new c.gnr.GnrBag();root.setItem('child',child);root.setBackRef();
    const events=[];root.subscribe('listen',{any:kw=>events.push([kw.evt,kw.pathlist,kw.where===child,kw.base===root])});
    child._getNode('created',true,42);
    return events;
});
compare('nested table formatting respects empty values', c => {
    c._F = value=>value==null?'':String(value);
    const b=new c.gnr.GnrBag({a:1,empty:null});
    return b.asNestedTable({omitEmpty:true},'static');
});
compare('back-reference consistency check', c => {
    const root=new c.gnr.GnrBag(),child=new c.gnr.GnrBag();root.setItem('child',child);root.setBackRef();
    return child.backrefOk();
});
compare('XML blocks preserve attributes and nested content', c => {
    const b=new c.gnr.GnrBag();b.setItem('a',1,{caption:'A'});b.setItem('child',new c.gnr.GnrBag({b:'text'}));
    return b.toXmlBlock({});
});

test('every enumerable legacy member remains visible to mixin enumeration', () => {
    const {legacy,selected}=loadPair();
    for (const name of classNames) {
        const actual=new Set();
        for (const key in selected.gnr[name].prototype) actual.add(key);
        for (const key in legacy.gnr[name].prototype) {
            assert.ok(actual.has(key),`${name}.${key}`);
        }
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
