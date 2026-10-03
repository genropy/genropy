const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadClasses} = require('./bag_audit_harness.cjs');
const load = () => loadClasses(['gnrlang.js', 'genro_bagjs_bundle.js', 'gnrbag_mixin.js', 'gnrdomsource.js']);

test('mixin uses native inheritance with no reserve adapter or enumerable-method patch', () => {
    const c = load();
    const bag = new c.gnr.GnrBag();
    assert.ok(bag instanceof c.GenroBagJS.Bag);
    for (const name of ['items', 'keys', 'values', 'columns', 'update', 'deepcopy']) {
        assert.equal(bag[name], c.GenroBagJS.Bag.prototype[name], name);
        assert.equal(Object.getOwnPropertyDescriptor(c.GenroBagJS.Bag.prototype, name).enumerable, false);
    }
    assert.equal(c.GenroBagJS.Bag.prototype.asHtmlTable, undefined);
});

test('getIndexList derives resolved paths and text from getIndex', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag();
    let calls = 0;
    bag.setItem('customer', new gnr.GnrBagCbResolver({method: () => {
        calls++;
        const child = new gnr.GnrBag();
        child.setItem('name', 'Ada');
        child.setItem('empty', new gnr.GnrBag());
        return child;
    }}, false, 60));
    bag.setItem('tail', null);
    const expected = ['customer', 'customer.name', 'customer.empty', 'tail'];
    assert.equal(calls, 0);
    assert.deepEqual(Array.from(bag.getIndexList()), expected);
    assert.equal(calls, 1);
    assert.equal(bag.getIndexList(true), expected.join('\n'));
    assert.deepEqual(Array.from(bag.getIndexList()),
        Array.from(bag.getIndex(), ([parts]) => parts.join('.')));
    assert.deepEqual(Array.from(new gnr.GnrBag().getIndexList()), []);
    assert.equal(new gnr.GnrBag().getIndexList(true), '');
    const shared = new gnr.GnrBag({leaf: 1});
    const aliases = new gnr.GnrBag();
    aliases.setItem('a', shared);
    aliases.setItem('b', shared);
    assert.deepEqual(Array.from(aliases.getIndexList()), ['a', 'a.leaf', 'b']);
});

test('actual DOM source builder creates specialized nodes and consistent parent aliases', () => {
    const {gnr, genro} = load();
    genro.wdg = {getHandler: () => null};
    const source = new gnr.GnrDomSource();
    source.setBackRef();
    const content = source._('div', 'panel', {caption: 'Panel'});
    content._('span', 'title', {innerHTML: 'Title'});
    const node = source.getNode('panel.title');
    assert.ok(node instanceof gnr.GnrDomSourceNode);
    assert.ok(content instanceof gnr.GnrDomSource);
    assert.equal(node._parentbag, content);
    assert.equal(content._parentnode, source.getNode('panel'));
    assert.equal(node.getFullpath(), 'panel.title');
    assert.equal(node.isChildOf(source.getNode('panel')), true);
});

test('framework event boundary preserves actual mutation and silent reset semantics', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({item: 1});
    const events = [];
    bag.subscribe('binding', {upd: event => events.push(event)});
    bag.setItem('item', 2, {caption: 'New'});
    assert.equal(events.length, 1);
    assert.equal(events[0].evt, 'upd');
    assert.equal(events[0].updvalue, true);
    assert.equal(events[0].updattr, true);
    assert.equal(events[0].base, bag);
    assert.equal(events[0].value, 2);
    assert.equal(events[0].oldvalue, 1);
    events.length = 0;
    bag.fireItem('item', 42);
    assert.equal(events.length, 1);
    assert.equal(events[0].fired, true);
    assert.equal(events[0].value, 42);
    assert.equal(bag.getItem('item'), null);
});

test('mixin resolves synchronous callbacks through standalone cache and supports static reads', () => {
    const {gnr} = load();
    let calls = 0;
    const bag = new gnr.GnrBag();
    bag.setItem('remote', new gnr.GnrBagCbResolver({method: () => ++calls}, false, 60));
    assert.equal(bag.getItem('remote', null, 'static'), null);
    assert.equal(calls, 0);
    assert.equal(bag.getItem('remote'), 1);
    assert.equal(bag.getItem('remote'), 1);
    assert.equal(calls, 1);
});

test('removed tuple lookup fails explicitly and unsupported kwargs do not silently change meaning', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({item: 1});
    assert.throws(() => bag.getNode('item', true), /no longer supports asTuple/);
    assert.equal(bag.getNode('item').getValue(), 1);
    assert.equal(bag.getNode('missing'), null);
    assert.equal(bag.getNode('created', false, true, 42).getValue(), 42);
    assert.equal(bag.getNode('item', 'static').getValue(), 1);
    assert.throws(() => bag.setItem('item', 2, null, {_duplicate: true}), /not yet bridged/);
    assert.equal(bag.getItem('item'), 1);
});

test('nested insertion and deletion envelopes retain location, path and reason', () => {
    const {gnr} = load();
    const root = new gnr.GnrBag();
    const child = new gnr.GnrBag();
    root.setItem('branch', child);
    const events = [];
    root.subscribe('source', {any: e => events.push(e)});
    child.setItem('leaf', 1);
    assert.deepEqual(Array.from(events[0].pathlist), ['branch', 'leaf']);
    assert.equal(events[0].where, child);
    assert.equal(events[0].base, root);
    const node = child.popNode('leaf', 'remove');
    assert.deepEqual(Array.from(events[1].pathlist), ['branch', 'leaf']);
    assert.equal(events[1].where, child);
    assert.equal(events[1].reason, 'remove');
    assert.equal(node.parentBag, null);
    child.setItem('silent', 2);
    events.length = 0;
    child.pop('silent', false);
    assert.equal(events.length, 0);
});

test('fireItem on a missing path emits one insertion with its real value', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag();
    const events = [];
    bag.subscribe('source', {any: e => events.push(e)});
    bag.fireItem('command', 42);
    assert.deepEqual(events.map(e => [e.evt, e.value]), [['ins', 42]]);
    assert.equal(bag.getItem('command'), null);
});

test('callback defaults, overrides and receiver are preserved', () => {
    const {gnr} = load();
    let resolver;
    resolver = new gnr.GnrBagCbResolver({parameters: {a: 1, b: 2}, b: 3,
        method: function(kw) { return [this === resolver, kw.a, kw.b, kw.c]; }});
    assert.deepEqual(resolver.resolve({c: 4}), [true, 1, 3, 4]);
});

test('resolver status follows explicit reassignment and successful resolution', () => {
    const {gnr} = load();
    const node = new gnr.GnrBag().setItem('value', null);
    const resolver = new gnr.GnrBagCbResolver({method: () => 42}, false, 60);
    node.setResolver(resolver);
    assert.equal(node.isLoaded(), false);
    assert.equal(node.getValue('static'), null);
    assert.equal(node.isLoaded(), false);
    assert.equal(node.getValue(), 42);
    assert.equal(node.isLoaded(), true);
});

test('clear removes nodes with individual reverse-order notifications only when requested', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({a: 1, b: 2});
    const events = [];
    bag.subscribe('source', {del: e => events.push(e.node.label)});
    bag.clear(true);
    assert.deepEqual(events, ['b', 'a']);
    bag.setItem('c', 3);
    bag.clear();
    assert.deepEqual(events, ['b', 'a']);
});

test('fromXmlDoc reads cookie XML and typed RPC branches using framework classes', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({retained: 'yes'});
    bag.fromXmlDoc('<GenRoBag><context><value>ok</value></context><count _T="L">12</count><flag _T="B">true</flag><empty _T="BAG"/></GenRoBag>');
    assert.equal(bag.getItem('retained'), 'yes');
    assert.equal(bag.getItem('context.value'), 'ok');
    assert.equal(bag.getItem('count'), 12);
    assert.equal(bag.getItem('flag'), true);
    assert.ok(bag.getItem('empty') instanceof gnr.GnrBag);
    assert.ok(bag.getNode('context.value') instanceof gnr.GnrBagNode);
    const element = (tagName, attr, childNodes = [], textContent = '') => ({
        nodeType: 1, tagName, childNodes, textContent,
        attributes: Object.entries(attr).map(([name, value]) => ({name, value}))
    });
    const root = element('GenRoBag', {}, [element('result', {__cls: 'DOMSOURCE', visible: 'true::B'}, [
        element('panel', {_T: 'BAG'})
    ])]);
    bag.fromXmlDoc({nodeType: 9, documentElement: root}, {DOMSOURCE: gnr.GnrDomSource});
    assert.ok(bag.getItem('result') instanceof gnr.GnrDomSource);
    assert.ok(bag.getNode('result.panel') instanceof gnr.GnrDomSourceNode);
    assert.equal(bag.getNode('result').attr.visible, true);
    assert.equal(bag.getNode('result').attr.__cls, undefined);
    assert.equal(bag.getNode('count').attr._T, undefined);
    const other = new gnr.GnrBag();
    other.fromXmlDoc(root, {DOMSOURCE: gnr.GnrDomSource});
    assert.ok(other.getItem('result.panel') instanceof gnr.GnrDomSource);
});

test('lazySet warns once and delegates writes to native change detection', () => {
    const c = load();
    const warnings = [];
    c.console = {...console, warn: message => warnings.push(message)};
    const bag = new c.gnr.GnrBag();
    const events = [];
    bag.subscribe('probe', {any: event => events.push(event)});
    bag.setItem('item', 1, null, {lazySet: true});
    assert.equal(bag.getItem('item'), 1);
    events.length = 0;
    bag.setItem('item', 1, null, {lazySet: true});
    assert.equal(events.length, 0);
    bag.setItem('item', 2, null, {lazySet: true});
    assert.equal(bag.getItem('item'), 2);
    assert.equal(events.length, 1);
    new c.gnr.GnrBag().setItem('other', 3, null, {lazySet: true});
    assert.equal(warnings.length, 1);
    assert.match(warnings[0], /lazySet is ignored/);
});

test('addItem renames duplicates like Python while preserving DOM classes, positions and events', () => {
    const {gnr} = load();
    const bag = new gnr.GnrDomSource();
    const events = [];
    bag.subscribe('test', {any: event => events.push(event)});
    const first = bag.addItem('panel.row', 'first', {tag:'div'});
    const second = bag.addItem('panel.row', 'second', {tag:'span'});
    assert.ok(first instanceof gnr.GnrDomSourceNode);
    assert.equal(bag.getNode('panel.row'), first);
    assert.equal(second.label, 'row__dup_1');
    assert.equal(second.xmlTag, 'row');
    assert.equal(bag.getNode('panel.#1'), second);
    assert.equal(bag.getItem('panel').length, 2);
    const head = bag.addItem('panel.row', 'head', null, {_position:'<', doTrigger:false});
    assert.equal(head.label, 'row__dup_2');
    assert.equal(bag.getNode('panel.#0'), head);
    assert.equal(bag.getNode('panel.row'), first);
    assert.equal(bag.getItem('panel').pop('row__dup_2', false), 'head');
    assert.equal(bag.getNode('panel.row'), first);
    assert.equal(bag.getItem('panel').pop('row', false), 'first');
    assert.equal(bag.getNode('panel.row'), null);
    assert.equal(bag.getNode('panel.row__dup_1'), second);
    assert.ok(events.some(event => event.evt === 'ins' && event.node === second));
});

test('clearValue is a framework-only node convenience preserving attrs and trigger control', () => {
    const {gnr, GenroBagJS} = load();
    assert.equal(GenroBagJS.BagNode.prototype.clearValue, undefined);
    const bag = new gnr.GnrBag();
    const child = new gnr.GnrBag({leaf: 1});
    const node = bag.setItem('item', child, {caption: 'Item'});
    let events = 0;
    bag.subscribe('probe', {any: () => events++});
    assert.equal(node.clearValue(false), node);
    assert.equal(node.getStaticValue(), null);
    assert.equal(node.attr.caption, 'Item');
    assert.equal(child.parentNode, null);
    assert.equal(events, 0);
    node.setValue(2, false);
    assert.equal(node.clearValue(), node);
    assert.equal(events, 1);
});

test('refresh reloads expired or explicitly forced node resolvers', () => {
    const {gnr, GenroBagJS} = load();
    assert.equal(GenroBagJS.BagNode.prototype.refresh, undefined);
    let calls = 0;
    const resolver = new gnr.GnrBagCbResolver({method: () => ++calls}, false, -1);
    const bag = new gnr.GnrBag();
    const node = bag.setItem('value', null);
    node.setResolver(resolver);
    node.refresh();
    assert.equal(calls, 1);
    node.refresh();
    assert.equal(calls, 1);
    node.refresh(true);
    assert.equal(calls, 2);
    assert.equal(node.getStaticValue(), 2);
});

test('formatting is framework-only and supports labels, nested values and tables', () => {
    const c = load();
    c._F = value => String(value == null ? '' : value);
    const {gnr, GenroBagJS} = c;
    assert.equal(GenroBagJS.Bag.prototype.getFormattedValue, undefined);
    assert.equal(GenroBagJS.BagNode.prototype.getFormattedValue, undefined);
    const bag = new gnr.GnrBag();
    bag.setItem('name', 'Alice', {_valuelabel: 'Customer'});
    bag.setItem('_hidden', 'secret');
    bag.setItem('empty', null);
    assert.equal(bag.getFormattedValue(), 'Customer: Alice');
    assert.equal(bag.getFormattedValue({omitEmpty:false,joiner:' | '}), 'Customer: Alice | Empty: ');
    const outer = new gnr.GnrBag({record:bag});
    assert.equal(outer.getFormattedValue(), 'Record: Customer: Alice');
    assert.match(bag.getFormattedValue({nested:true}), /nestedBagTable/);
    const rows = new gnr.GnrBag({row: new gnr.GnrBag({name:'Alice'})});
    const html = rows.getFormattedValue({cells:'name',headers:'Customer'});
    assert.match(html, /<th>Customer<\/th>/);
    assert.match(html, /<td>Alice<\/td>/);
});

test('deprecated setCallBackItem preserves callback params, receiver and node attributes', () => {
    const c = load(); const warnings = [];
    c.console = {...console, warn: message => warnings.push(message)};
    const bag = new c.gnr.GnrBag();
    const parameters = {base: 2, override: 'default'};
    const kwargs = {gridId: 'grid', override: 'configured'};
    let receiver;
    function callback(kw) { receiver = this; return [kw.base, kw.gridId, kw.override]; }
    assert.equal(bag.setCallBackItem('menu', callback, parameters, kwargs), undefined);
    const node = bag.getNode('menu');
    assert.equal(node.attr.gridId, 'grid');
    assert.equal(node.attr.parameters, parameters);
    assert.equal(node.attr.method, callback);
    assert.deepEqual(Array.from(node.getValue('', {override:'call'})), [2, 'grid', 'call']);
    assert.equal(receiver, node.getResolver());
    assert.deepEqual(kwargs, {gridId:'grid', override:'configured'});
    assert.deepEqual(parameters, {base:2, override:'default'});
    bag.setCallBackItem('other', () => 42);
    assert.equal(bag.getItem('other'), 42);
    assert.equal(warnings.length, 1);
    assert.match(warnings[0], /deprecated/);
});

test('framework lookup, index, object and ancestry helpers preserve node semantics', () => {
    const c = load(); const {gnr} = c;
    c.asText = (value, format) => `${format}:${value}`;
    const bag = new gnr.GnrBag({branch:new gnr.GnrBag({leaf:7}), empty:null});
    bag.setBackRef();
    const branch = bag.getNode('branch'), leaf = bag.getNode('branch.leaf');
    assert.equal(leaf.parentshipLevel(leaf), 0);
    assert.equal(leaf.parentshipLevel(branch), 1);
    assert.equal(branch.parentshipLevel(leaf), -1);
    assert.equal(bag.findNodeById(String(leaf._id)), leaf);
    assert.equal(bag.findNodeById('absent'), undefined);
    assert.deepEqual(Array.from(bag.getIndex(), row => Array.from(row[0]).join('.')), ['branch','branch.leaf','empty']);
    let calls = 0;
    const resolver = new gnr.GnrBagCbResolver({method:()=>++calls});
    bag.setItem('remote',resolver);
    const beforeFormatting = calls;
    assert.equal(bag.asObj().remote, '**');
    assert.equal(calls,beforeFormatting);
    assert.equal(bag.asObj().branch,branch.getValue());
    assert.equal(branch.getValue().asObj({leaf:'number'}).leaf,'number:7');
    bag._modified = true;
    assert.equal(bag.get_modified(),true);
});

test('concat adopts source nodes without copying or emitting insert events', () => {
    const {gnr} = load();
    const target = new gnr.GnrDomSource();
    target.setItem('row','first');
    const source = new gnr.GnrDomSource();
    const node = source.setItem('row',new gnr.GnrDomSource({child:1}));
    let events=0; target.subscribe('test',{any:()=>events++});
    assert.equal(target.concat(source),undefined);
    assert.equal(target.getNode('#1'),node);
    assert.equal(node.getParentBag(),target);
    assert.equal(target.getItem('row'),'first');
    assert.equal(source.getNode('row'),node);
    assert.equal(events,0);
});

test('moveNode preserves identity, order, parents and event reasons', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({a:1,b:2,c:3,d:4});
    const a=bag.getNode('a'); const events=[];
    bag.subscribe('test',{any:event=>events.push([event.evt,event.reason])});
    bag.moveNode(0,2,'movingRows');
    assert.deepEqual(Array.from(bag.keys()),['b','c','a','d']);
    assert.equal(bag.getNode('a'),a);
    assert.equal(a.getParentBag(),bag);
    assert.deepEqual(events,[['del','movingRows'],['ins','movingRows']]);
    events.length=0;
    bag.moveNode([0,1],3,false);
    assert.deepEqual(Array.from(bag.keys()),['a','d','b','c']);
    assert.equal(events.length,0);
    bag.moveNode(0,-1);
    assert.deepEqual(Array.from(bag.keys()),['a','d','b','c']);
});

test('source attr assignment separates construction kwargs from live node attributes', () => {
    const {gnr} = load();
    const bag = new gnr.GnrDomSource();
    const node = bag.setItem('bar', null, {tag:'slotbar',slots:'left,*,right'});
    const construction = node.attr;
    const live = {};
    node.attr = live;
    node.attr.tag = construction.tag;
    delete construction.tag;
    const slots = construction.slots;
    delete construction.slots;
    assert.equal(slots,'left,*,right');
    assert.equal(node.attr,live);
    assert.equal(node.attr.tag,'slotbar');
    assert.equal(construction.tag,undefined);
    node.setAttr({caption:'Bar'});
    assert.equal(node.attr.caption,'Bar');
});

test('direct legacy resolver calls reload without serializing sourceNode context', () => {
    const {gnr} = load();
    const source = new gnr.GnrDomSource();
    source.setBackRef();
    const node = source.setItem('widget', new gnr.GnrDomSource({child:1}));
    let calls = 0, received;
    const resolver = new gnr.GnrBagCbResolver({method: kw => {received=kw._sourceNode; return ++calls;}}, false, -1);
    assert.equal(resolver.resolve({_sourceNode:node, value:1}),1);
    assert.equal(received,node);
    assert.equal(resolver.resolve({_sourceNode:node, value:1}),2);
    assert.equal(resolver.resolve({_sourceNode:node, value:2}),3);
    const other = source.setItem('other',null);
    assert.equal(resolver.resolve({_sourceNode:other,value:2}),4);
});

test('GenroJS expression reads operate on values and attributes without resolver kwargs', () => {
    const c = load();
    c.genro.evaluate = code => require('node:vm').runInContext('(' + code + ')', c);
    const {gnr} = c;
    const bag = new gnr.GnrBag();
    bag.setItem('data',new gnr.GnrBag({a:1,b:2}),{caption:'Hello'});
    assert.equal(bag.getItem('data?=#v.len()'),2);
    assert.equal(bag.getItem('data?caption?=#v.toUpperCase()'),'HELLO');
    assert.equal(bag.getItem('absent?=#v ? 1 : 0'),null);
});

test('real lazyBuildFinalize retains the Bag container and rebuilds child nodes', () => {
    const {gnr} = load();
    const source = new gnr.GnrDomSource();
    const content = new gnr.GnrDomSource();
    content.setItem('child',null,{tag:'div',caption:'Child'});
    const parent = source.setItem('parent',content);
    parent.lazyBuildFinalize({});
    assert.equal(typeof content._nodes.set,'function');
    assert.equal(content.getNode('child').attr.caption,'Child');
    assert.ok(content.getNode('child') instanceof gnr.GnrDomSourceNode);
});

test('GenroJS #id insertion allocates a label before container validation', () => {
    const {gnr,genro}=load(); let counter=0;
    genro.time36Id=()=>`generated_${++counter}`;
    const bag=new gnr.GnrDomSource();
    bag.setItem('#id','one'); bag.setItem('#id','two');
    assert.deepEqual(Array.from(bag.keys()),['generated_1','generated_2']);
});


test('detached source deletions respect the frozen origin and still dispatch after unfreeze', () => {
    const {gnr, genro} = loadClasses(['gnrlang.js', 'genro_bagjs_bundle.js', 'gnrbag_mixin.js', 'gnrdomsource.js', 'genro_src.js']);
    genro.wdg = {getHandler: () => null};
    const source = new gnr.GnrDomSource();
    source.setBackRef();
    const content = source._('div', 'panel', {});
    const parent = content.getParentNode();
    content._('div', 'first', {});
    content._('div', 'second', {});
    const handled = [];
    const handler = Object.assign(Object.create(gnr.GnrSrcHandler.prototype), {
        pendingBuild: [], building: false, _subscribedNodes: {}, _index: {},
        _trigger_del: event => handled.push(event.node.label)
    });
    source.subscribe('delete-test', {del: event => gnr.GnrSrcHandler.prototype.nodeTrigger.call(handler, event)});
    parent.freeze();
    const removed = content.popNode('first');
    assert.equal(removed.getParentBag(), null);
    assert.deepEqual(handled, []);
    parent.unfreeze(true);
    content.popNode('second');
    assert.deepEqual(handled, ['second']);
});

test('framework parent path normalization remains available without the legacy Bag module', () => {
    const {gnr} = load();
    assert.equal(gnr.bagRealPath('form.record.#parent.total'), 'form.total');
    assert.equal(gnr.bagRealPath('form.#parent.#parent.total'), 'total');
    assert.equal(gnr.bagRealPath('form.total'), 'form.total');
});

test('remote resolver consumes callbacks and transport settings before forming load parameters', () => {
    const {gnr} = loadClasses(['gnrlang.js', 'genro_bagjs_bundle.js', 'gnrbag_mixin.js', 'genro_rpc.js']);
    const onResult = () => {};
    const kwargs = {method:'example', _onResult:onResult, sync:true, query:7};
    const resolver = new gnr.GnrRemoteResolver(kwargs, false, 0);
    assert.equal(resolver.onResult, onResult);
    assert.equal(resolver.xhrKwargs.sync, true);
    assert.notEqual(resolver.kwargs, kwargs);
    assert.equal('_onResult' in kwargs, false);
    assert.equal('sync' in kwargs, false);
    assert.equal('_onResult' in resolver.kwargs, false);
    assert.equal('sync' in resolver.kwargs, false);
    assert.equal(resolver.kwargs.query, 7);
});

test('slotbar removes consecutive slot placeholders without skipping retained content', () => {
    const {gnr} = loadClasses(['gnrlang.js', 'genro_bagjs_bundle.js', 'gnrbag_mixin.js', 'genro_components.js']);
    const children = new gnr.GnrBag();
    children.setItem('a', null, {tag:'slot'});
    children.setItem('b', null, {tag:'slot'});
    children.setItem('c', null, {tag:'div'});
    const receiver = {createContent_horizontal: () => 'built'};
    assert.equal(gnr.widgets.SlotBar.prototype.createContent.call(receiver, {}, {orientation:'horizontal'}, children), 'built');
    assert.deepEqual(Array.from(children.keys()), ['c']);
});

test('XML remote resolvers stay lazy and preserve recall parameters and cache policy', () => {
    const {gnr, genro} = load();
    genro.evaluate = JSON.parse;
    const calls = [];
    let loads = 0;
    genro.rpc = {remoteResolver(method, parameters, options) {
        calls.push({method, parameters, options});
        return new gnr.GnrBagCbResolver({method: () => { loads++; return new gnr.GnrBag({item:'Menu'}); }}, false, options.cacheTime);
    }};
    const bag = new gnr.GnrBag();
    bag.fromXmlDoc(`<GenRoBag><root _resolver='{"kwargs":{"cacheTime":60},"args":["menu"]}' cacheTime="120::L"/></GenRoBag>`);
    assert.equal(loads, 0);
    assert.equal(calls[0].method, 'resolverRecall');
    assert.equal(calls[0].options.cacheTime, 120);
    assert.equal(calls[0].parameters.resolverPars.cacheTime, 0);
    assert.deepEqual(calls[0].parameters.resolverPars.args, ['menu']);
    assert.equal(bag.getNode('root').attr._resolver, undefined);
    assert.equal(bag.getItem('root').getItem('item'), 'Menu');
    bag.getItem('root');
    assert.equal(loads, 1);
});

test('XML preloaded relation resolvers reuse their value and retain resolved attributes', () => {
    const {gnr, genro} = load();
    let loads = 0;
    genro.getRelationResolver = (attributes, name, target) => {
        assert.equal(name, 'relation');
        assert.ok(target instanceof gnr.GnrBag);
        return new gnr.GnrBagCbResolver({method: () => { loads++; return new gnr.GnrBag({fresh:1}); }}, false, 60);
    };
    const bag = new gnr.GnrBag();
    bag.fromXmlDoc(`<GenRoBag><root _resolver_name="relation" _resolvedInfo='{"caption":"Loaded"}::JS'><item>cached</item></root></GenRoBag>`);
    assert.equal(bag.getItem('root').getItem('item'), 'cached');
    assert.equal(loads, 0);
    assert.equal(bag.getNode('root').attr.caption, 'Loaded');
    bag.getNode('root').getResolver().reset();
    assert.equal(bag.getItem('root').getItem('fresh'), 1);
    assert.equal(loads, 1);
});


test('menu full paths with root=true omit the datastore wrapper', () => {
    const {gnr} = load();
    const root = new gnr.GnrBag();
    root.setBackRef();
    root.setItem('main', new gnr.GnrBag());
    root.getItem('main').setItem('menu.entry', 'Invoice');
    const node = root.getNode('main.menu.entry');
    assert.equal(node.getFullpath(null, true), 'menu.entry');
    assert.equal(root.getItem('main').getNode(node.getFullpath(null, true)), node);
});


test('bulk framework insertion keeps container storage without numeric aliases', () => {
    const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js']);
    const bag = new c.gnr.GnrBag();
    for (let i = 0; i < 15000; i++) bag.addItem('r_' + i, i);
    assert.equal(bag.getNodes().length, 15000);
    assert.equal(bag.getNode(14999).label, 'r_14999');
    assert.equal(bag.getItem('r_100'), 100);
    assert.equal(Object.keys(bag._nodes).some(key => /^\d+$/.test(key)), false);
    bag.addItem('r_100', 'duplicate');
    assert.equal(bag.getItem('r_100'), 100);
});

test('unqueried store attributes keep the public title without an undefined counter', () => {
    const c = load();
    const bag = new c.gnr.GnrBag();
    bag.setItem('view.store', new c.gnr.GnrBag());
    const totalRowCount = bag.getItem('view.store?totalRowCount');
    const totalrows = bag.getItem('view.store?totalrows');
    let title = 'Customers';
    if (totalRowCount !== null) title += ' (' + totalrows + '/' + totalRowCount + ')';
    else if (totalrows) title += ' (' + totalrows + ')';
    assert.equal(title, 'Customers');
    bag.getNode('view.store').setAttr({totalrows: 0, totalRowCount: 0});
    assert.equal(bag.getItem('view.store?totalRowCount'), 0);
});

test('addItem probes the first free suffix, reuses gaps and warns only on collisions', () => {
    const c = load();
    const warnings = [];
    c.console = {...console, warn: message => warnings.push(message)};
    const bag = new c.gnr.GnrBag();
    const first = bag.addItem('alfa', 10);
    bag.addItem('alfa__dup_2', 'reserved');
    assert.equal(warnings.length, 0);
    const second = bag.addItem('alfa', 20);
    const third = bag.addItem('alfa', 30);
    assert.equal(second.label, 'alfa__dup_1');
    assert.equal(third.label, 'alfa__dup_3');
    assert.equal(second.xmlTag, 'alfa');
    assert.equal(third.xmlTag, 'alfa');
    assert.equal(bag.getNode('alfa'), first);
    assert.equal(bag.getItem('alfa__dup_2'), 'reserved');
    bag.popNode('alfa__dup_1', false);
    const reused = bag.addItem('alfa', 40);
    assert.equal(reused.label, 'alfa__dup_1');
    assert.equal(bag.getItem('alfa__dup_1'), 40);
    assert.equal(warnings.length, 3);
    assert.ok(warnings.every(message => /renamed duplicate alfa.*deprecated/.test(message)));
    for (const node of bag.getNodes()) assert.equal(bag._nodes._dict[node.label], node);
});

test('addItem duplicate policies reject before insertion and preserve the existing node', () => {
    const c = load();
    const warnings = [];
    c.console = {...console, warn: message => warnings.push(message)};
    const bag = new c.gnr.GnrBag();
    const first = bag.addItem('alfa', 10, null, {duplicate_policy: 'error'});
    assert.throws(() => bag.addItem('alfa', 20, null, {duplicate_policy: 'error'}),
        /Bag label already exists/);
    assert.throws(() => bag.addItem('missing.branch', 20, null, {duplicate_policy: 'invalid'}),
        /duplicate_policy/);
    assert.equal(bag.length, 1);
    assert.equal(bag.getNode('alfa'), first);
    assert.equal(first.getValue(), 10);
    assert.equal(warnings.length, 0);
});

test('addItem exposes renamed label, XML tag and attributes to insertion subscribers', () => {
    const c = load();
    c.console = {...console, warn() {}};
    const bag = new c.gnr.GnrBag();
    bag.setBackRef();
    bag.addItem('alfa', 'first');
    const events = [];
    bag.subscribe('check', {ins: event => events.push({label: event.node.label,
        xmlTag: event.node.xmlTag, caption: event.node.attr.caption})});
    const renamed = bag.addItem('alfa', 'second', {caption: 'Second'}, {_position: '<'});
    assert.deepEqual(events, [{label: 'alfa__dup_1', xmlTag: 'alfa', caption: 'Second'}]);
    assert.equal(bag.getNode('#0'), renamed);
    bag.addItem('alfa', 'third', null, {doTrigger: false});
    assert.equal(events.length, 1);
});

test('clear empties storage once, notifies in reverse with live ancestry, then detaches', () => {
    const {gnr} = load();
    const root = new gnr.GnrBag();
    root.setBackRef();
    root.setItem('branch', new gnr.GnrBag({a: 1, b: 2}));
    const bag = root.getItem('branch');
    const nodes = bag.getNodes();
    const events = [];
    root.subscribe('clear', {del: event => {
        assert.equal(event.node.parentBag, bag);
        assert.equal(event.node.parentNode, root.getNode('branch'));
        assert.equal(bag.length, 0);
        events.push([event.node.label, event.ind, event.reason, event.where === bag]);
    }});
    bag.clear(true);
    assert.deepEqual(events, [['b', 1, null, true], ['a', 0, null, true]]);
    assert.ok(nodes.every(node => node.parentBag === null));
});

test('clear is silent by default and clears child backrefs after removing nodes', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag();
    bag.setBackRef();
    bag.setItem('branch', new gnr.GnrBag({leaf: 1}));
    const node = bag.getNode('branch'), child = node.getValue();
    bag.subscribe('clear', {any: () => assert.fail('Silent clear emitted an event')});
    bag.clear();
    assert.equal(bag.length, 0);
    assert.equal(node.parentBag, null);
    assert.equal(child.parentNode, null);
    assert.equal(child.parent, null);
    bag.clear(true); // empty clear is silent as well
});

test('clear releases all removed nodes when a subscriber throws', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({a: 1, b: 2, c: 3});
    bag.setBackRef();
    const nodes = bag.getNodes();
    bag.subscribe('clear', {del: () => { throw new Error('subscriber failed'); }});
    assert.throws(() => bag.clear(true), /subscriber failed/);
    assert.equal(bag.length, 0);
    assert.ok(nodes.every(node => node.parentBag === null));
});

test('clear retains nodes reinserted by subscribers', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({a: 1});
    bag.setBackRef();
    const node = bag.getNode('a');
    bag.subscribe('clear', {del: event => {
        // Restore the existing node, as opposed to setItem which wraps values.
        bag._nodes._list.push(event.node);
        bag._nodes._dict[event.node.label] = event.node;
        event.node.parentBag = bag;
    }});
    bag.clear(true);
    assert.equal(bag.getNode('a'), node);
    assert.equal(node.parentBag, bag);
});

test('clear does not perform per-node searches or removals on a wide Bag', () => {
    const {gnr} = load();
    for (const trigger of [false, true]) {
        const bag = new gnr.GnrBag();
        for (let i = 0; i < 10000; i++) bag.setItem('r' + i, i);
        const nodes = bag.getNodes();
        let events = 0;
        bag.subscribe('clear', {del: () => events++});
        bag._nodes.index = bag._nodes.pop = bag._nodes._list.indexOf =
            () => assert.fail('clear must not search/remove nodes individually');
        bag.clear(trigger);
        assert.equal(events, trigger ? 10000 : 0);
        assert.equal(bag.length, 0);
        assert.ok(nodes.every(node => node.parentBag === null));
    }
});

test('getFullpath delegates label paths without copying sibling lists', () => {
    const {gnr} = load();
    const root = new gnr.GnrBag();
    root.setBackRef();
    root.setItem('branch', new gnr.GnrBag());
    const branch = root.getItem('branch');
    for (let i = 0; i < 10000; i++) branch.setItem('r' + i, i);
    const nodes = branch.getNodes();
    root.getNodes = branch.getNodes = () => assert.fail('Label paths must not copy siblings');
    const relativePath = branch.relativePath;
    let calls = 0;
    branch.relativePath = function(node) { calls++; return relativePath.call(this, node); };
    for (let i = 0; i < nodes.length; i++) {
        assert.equal(nodes[i].getFullpath(null, branch), 'r' + i);
        assert.equal(nodes[i].getFullpath(), 'branch.r' + i);
    }
    assert.equal(calls, 10000);
    assert.equal(nodes[0].getFullpath(null, true), 'r0');
});

test('getFullpath preserves numeric modes and explicit root boundaries', () => {
    const {gnr} = load();
    const root = new gnr.GnrBag();
    root.setBackRef();
    root.setItem('branch', new gnr.GnrBag({a: 1, b: 2}));
    const branch = root.getItem('branch'), node = branch.getNode('b');
    assert.equal(node.getFullpath('#'), '0.1');
    assert.equal(node.getFullpath('##'), '#0.#1');
    assert.equal(node.getFullpath('#', branch), '1');
    assert.equal(node.getFullpath('##', branch), '#1');
    assert.equal(node.getFullpath('##', true), '#1');
    assert.equal(root.getNode(node.getFullpath('##')), node);
});

test('getFullpath disambiguates existing duplicate nodes even at an explicit root', () => {
    const {gnr} = load();
    const root = new gnr.GnrBag();
    root.setBackRef();
    root.setItem('branch', new gnr.GnrBag({x: 1}));
    const branch = root.getItem('branch');
    const second = new gnr.GnrBagNode(branch, 'x', 2);
    branch._nodes._list.push(second);
    assert.equal(second.getFullpath(null, branch), '#1');
    assert.equal(branch.getNode(second.getFullpath(null, branch)), second);
    assert.equal(second.getFullpath(), 'branch.#1');
    assert.equal(root.getNode(second.getFullpath()), second);
    assert.equal(second.getFullpath(null, true), '#1');
});

test('resolver retains class defaults, init changes and the initialized parameter object', () => {
    const {gnr} = load();
    class Resolver extends gnr.GnrBagResolver {
        static classKwargs = {...gnr.GnrBagResolver.classKwargs, limit: 100, table: 'default'};
        init() { this.initializedParameters = this.kwargs; this.kwargs.fromInit = 7; }
        load(kwargs) { return kwargs; }
    }
    const input = {table: 'customer', cacheTime: 99, readOnly: true, asBag: true, retryPolicy: null};
    const resolver = new Resolver(input, false, 30);
    assert.equal(resolver.kwargs, resolver.initializedParameters);
    assert.equal(resolver.kwargs.limit, 100);
    assert.equal(resolver.kwargs.table, 'customer');
    assert.equal(resolver.kwargs.fromInit, 7);
    for (const key of ['cacheTime', 'readOnly', 'asBag', 'retryPolicy']) {
        assert.equal(key in resolver.kwargs, false);
    }
    assert.equal(resolver.cacheTime, 30);
    assert.equal(resolver.readOnly, false);
    assert.equal(resolver.resolve().fromInit, 7);
    assert.equal('fromInit' in input, false);
});

test('resolver preserves inherited enumerable input parameters', () => {
    const {gnr} = load();
    const input = Object.create({inherited: 3});
    input.own = 2;
    const resolver = new gnr.GnrBagResolver(input, false, 0, kwargs => kwargs);
    assert.equal(resolver.resolve().inherited, 3);
    assert.equal(resolver.kwargs.own, 2);
});

for (const mode of ['legacy', 'mixin']) {
    test('remote resolver strips transport settings from the actual RPC payload in ' + mode, () => {
        const files = ['gnrlang.js', ...(mode === 'legacy' ? ['gnrbag.js'] :
            ['genro_bagjs_bundle.js', 'gnrbag_mixin.js']), 'genro_rpc.js'];
        const {gnr, genro} = loadClasses(files);
        const onResult = function(result) {}, onCalling = function(query) {};
        const input = {method: 'example', query: 7, sync: true, httpMethod: 'PUT',
            timeout: 120, preventCache: true, handleAs: 'json',
            _onResult: onResult, _onCalling: onCalling};
        const resolver = new gnr.GnrRemoteResolver(input, false, 0);
        let captured;
        genro.rpc = {_serverCall: (kwargs, xhrKwargs, httpMethod) => {
            captured = {kwargs, xhrKwargs, httpMethod};
            return {addCallback: cb => cb(42)};
        }};
        assert.equal(resolver.load(resolver.kwargs), 42);
        assert.equal(captured.httpMethod, 'PUT');
        assert.equal(captured.xhrKwargs.sync, true);
        assert.equal(captured.xhrKwargs.timeout, 120);
        assert.equal(captured.xhrKwargs.handleAs, 'json');
        assert.equal(captured.xhrKwargs.preventCache, true);
        assert.equal(resolver.onResult, onResult);
        assert.equal(resolver.onCalling, onCalling);
        assert.deepEqual(Object.keys(captured.kwargs).sort(), ['method', 'query']);
        assert.deepEqual(Object.keys(input).sort(), ['method', 'query']);
    });
}

test('remote resolver consumes transport defaults and init changes from the merged parameters', () => {
    const {gnr} = loadClasses(['gnrlang.js', 'genro_bagjs_bundle.js', 'gnrbag_mixin.js', 'genro_rpc.js']);
    class Remote extends gnr.GnrRemoteResolver {
        static classKwargs = {...gnr.GnrBagResolver.classKwargs, timeout: 123, httpMethod: 'PATCH', limit: 10};
        init() { this.kwargs.sync = true; this.kwargs.fromInit = 9; }
    }
    const resolver = new Remote({method: 'example'}, false, 0);
    assert.equal(resolver.xhrKwargs.timeout, 123);
    assert.equal(resolver.httpMethod, 'PATCH');
    assert.equal(resolver.xhrKwargs.sync, true);
    assert.equal(resolver.kwargs.limit, 10);
    assert.equal(resolver.kwargs.fromInit, 9);
    for (const key of ['timeout', 'httpMethod', 'sync']) assert.equal(key in resolver.kwargs, false);
});

test('mixin constructors and insertion preserve native node tags', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag();
    const direct = new gnr.GnrBagNode(bag, 'a', 1, {}, null, 'semantic', 'original');
    assert.equal(direct.nodeTag, 'semantic');
    assert.equal(direct.xmlTag, 'original');
    const inserted = bag.addItem('b', 2, {}, {nodeTag: 'kind', xmlTag: 'source'});
    assert.equal(inserted.nodeTag, 'kind');
    assert.equal(inserted.xmlTag, 'source');
    assert.equal(bag.setItem('c', 3, {}, {nodeTag: 'field'}).nodeTag, 'field');
    const source = new gnr.GnrDomSource();
    const node = source.addItem('pane', null, {tag: 'div'}, {nodeTag: 'semantic-pane', xmlTag: 'panel'});
    assert.ok(node instanceof gnr.GnrDomSourceNode);
    assert.equal(node.nodeTag, 'semantic-pane');
    assert.equal(node.xmlTag, 'panel');
    assert.equal(node.attr.tag, 'div');
});

test('TYTX import and reserialization retain nodeTag at every level', () => {
    const {gnr, GenroBagJS} = load();
    const original = new GenroBagJS.Bag();
    const child = new GenroBagJS.Bag();
    child.setItem('leaf', 7).nodeTag = 'leaf-type';
    original.setItem('branch', child).nodeTag = 'branch-type';
    const imported = new gnr.GnrBag();
    imported.fromTytxDoc(original.toTytx('json'));
    assert.equal(imported.getNode('branch').nodeTag, 'branch-type');
    assert.equal(imported.getNode('branch.leaf').nodeTag, 'leaf-type');
    const restored = GenroBagJS.Bag.fromTytx(imported.toTytx('json'), 'json');
    assert.equal(restored.getNode('branch').nodeTag, 'branch-type');
    assert.equal(restored.getNode('branch.leaf').nodeTag, 'leaf-type');
});

test('XML import preserves the original tag alongside a remapped label', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag();
    bag.fromXmlDoc('<GenRoBag><original _tag="renamed">value</original></GenRoBag>');
    assert.equal(bag.getNode('renamed').xmlTag, 'original');
    assert.equal(bag.toXml(), '<?xml version="1.0" encoding="utf-8"?>\n<GenRoBag><original>value</original></GenRoBag>');
});

test('sort translates legacy modes and delegates once to the standalone algorithm', () => {
    const {gnr, GenroBagJS} = load();
    const bag = new gnr.GnrBag();
    const calls = [];
    const original = GenroBagJS.Bag.prototype.sort;
    GenroBagJS.Bag.prototype.sort = function(key) { calls.push(key); return this; };
    try {
        for (const [legacy, native] of [['a*','a'],['d*','d'],['a','a'],['d','d'],
            ['asc','a'],['desc','d'],['>','A'],['<','D'],['ASC*','A'],['DESC*','D']]) {
            assert.equal(bag.sort('#a.name:' + legacy), bag);
            assert.equal(calls.at(-1), '#a.name:' + native);
        }
        bag.sort(' #a.name : d* , #v : a ');
        assert.equal(calls.at(-1), '#a.name:d,#v:a');
        bag.sort();
        assert.equal(calls.at(-1), '#k:a');
        bag.sort('#v');
        assert.equal(calls.at(-1), '#v:a');
        const key = node => node.value;
        bag.sort(key);
        assert.equal(calls.at(-1), key);
        assert.equal(calls.length, 14);
    } finally { GenroBagJS.Bag.prototype.sort = original; }
});

test('sort handles the textual grid modes and stable multiple criteria', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag();
    bag.setItem('first', 'a', {name: 'a', rank: 1});
    bag.setItem('second', 'B', {name: 'B', rank: 1});
    bag.setItem('third', 'A', {name: 'A', rank: 2});
    bag.sort('#a.name:d*');
    assert.deepEqual(Array.from(bag.keys()), ['second', 'first', 'third']);
    bag.sort('#a.name:a*,#a.rank:d');
    assert.deepEqual(Array.from(bag.keys()), ['third', 'first', 'second']);
    bag.sort('#v:A');
    assert.deepEqual(Array.from(bag.keys()), ['third', 'second', 'first']);
});

test('legacy XML wire matches legacy output and round-trips typed client context', () => {
    const {loadPair} = require('./bag_audit_harness.cjs');
    const pair = loadPair();
    const make = ({gnr}) => {
        const b = new gnr.GnrBag();
        b.setItem('n', 12, {enabled: true, count: 4});
        b.setItem('flag', true);
        b.setItem('ratio', 1.5);
        b.setItem('text', '<hello> & world');
        b.setItem('missing', null);
        b.setItem('child', new gnr.GnrBag({leaf: 'hello'}));
        b.setItem('empty', new gnr.GnrBag());
        return b;
    };
    const legacy = make(pair.legacy), selected = make(pair.selected);
    assert.equal(selected.toXml(), legacy.toXml());
    assert.equal(selected.toXml({encoding: 'UTF-8'}), legacy.toXml({encoding: 'UTF-8'}));
    assert.equal(selected.toXmlBlock(), legacy.toXmlBlock());
    const restored = new pair.selected.gnr.GnrBag();
    restored.fromXmlDoc(selected.toXml());
    assert.equal(restored.getItem('n'), 12);
    assert.equal(restored.getNode('n').attr.enabled, true);
    assert.equal(restored.getNode('n').attr.count, 4);
    assert.equal(restored.getItem('flag'), true);
    assert.equal(restored.getItem('ratio'), 1.5);
    assert.equal(restored.getItem('text'), '<hello> & world');
    assert.equal(restored.getItem('missing'), null);
    assert.equal(restored.getItem('child.leaf'), 'hello');
    assert.ok(restored.getItem('empty') instanceof pair.selected.gnr.GnrBag);
});

test('legacy XML serializes cached resolver values without executing them', () => {
    const {gnr, GenroBagJS} = load();
    const b = new gnr.GnrBag();
    let loads = 0;
    const resolver = new gnr.GnrBagResolver({}, false, 0, () => { loads++; return 'unexpected'; });
    b.setItem('lazy', resolver);
    const node = b.getNode('lazy');
    node.setValue('cached', false);
    b.setItem('nativeChild', new GenroBagJS.Bag({leaf: 3}));
    const xml = b.toXml();
    assert.equal(loads, 0);
    assert.ok(xml.includes('<lazy>cached</lazy>'));
    const restored = new gnr.GnrBag();
    restored.fromXmlDoc(xml);
    assert.equal(restored.getItem('nativeChild.leaf'), 3);
});

for (const operation of ['popNode', 'pop']) {
    for (const action of ['normal', 'throw', 'reinsert', 'transfer']) {
        test(`public ${operation} inherits removal contract: ${action}`, () => {
            const {gnr} = load();
            const bag = new gnr.GnrBag(); bag.setItem('branch.leaf', 1); bag.setBackRef();
            const node = bag.getNode('branch'), child = node.getValue();
            const destination = new gnr.GnrBag(); destination.setBackRef();
            let calls = 0;
            bag.subscribe('watch', {del: () => {
                calls++;
                assert.equal(node.getParentBag(), bag);
                if (action === 'throw') throw Error('subscriber failed');
                if (action === 'reinsert' || action === 'transfer') {
                    const target = action === 'reinsert' ? bag : destination;
                    target._nodes._list.push(node); target._nodes._dict[node.label] = node;
                    node.setParentBag(target);
                }
            }});
            if (action === 'throw') assert.throws(() => bag[operation]('branch'), /subscriber failed/);
            else assert.equal(bag[operation]('branch'), operation === 'popNode' ? node : child);
            assert.equal(calls, 1);
            const target = action === 'reinsert' ? bag : action === 'transfer' ? destination : null;
            assert.equal(node.getParentBag(), target);
            assert.equal(child.parent, target);
            if (!target) {
                let local = 0;
                child.subscribe('local', {upd: () => local++});
                child.setItem('leaf', 2);
                assert.equal(local, 1);
            }
        });
    }
}

test('sort by a Bag row field agrees with legacy without reordering row contents', () => {
    const {loadPair} = require('./bag_audit_harness.cjs');
    const pair = loadPair();
    for (const context of [pair.legacy, pair.selected]) {
        const bag = new context.gnr.GnrBag();
        bag.setItem('r1.z', 0); bag.setItem('r1.price', 20);
        bag.setItem('r2.z', 0); bag.setItem('r2.price', 10);
        const row = bag.getItem('r1');
        bag.sort('price:a');
        assert.deepEqual(Array.from(bag.getNodes(), n => n.label), ['r2', 'r1']);
        assert.equal(bag.getItem('r1'), row);
        assert.deepEqual(Array.from(row.getNodes(), n => n.label), ['z', 'price']);
    }
});

test('null ordering agrees with legacy in both directions', () => {
    const {loadPair} = require('./bag_audit_harness.cjs');
    const pair = loadPair();
    for (const context of [pair.legacy, pair.selected]) {
        for (const mode of ['a', 'd']) {
            const bag = new context.gnr.GnrBag();
            bag.setItem('empty', null); bag.setItem('high', 10); bag.setItem('zero', 0);
            bag.sort(`#v:${mode}`);
            assert.deepEqual(Array.from(bag.getNodes(), n => n.label),
                mode === 'a' ? ['empty', 'zero', 'high'] : ['high', 'zero', 'empty']);
        }
    }
});

test('canonical case modes ignore star in both implementations', () => {
    const {loadPair} = require('./bag_audit_harness.cjs');
    const pair = loadPair();
    const warnings = [], original = console.warn;
    console.warn = message => warnings.push(message);
    try {
        for (const context of [pair.legacy, pair.selected]) {
            for (const [mode, expected] of [['a', ['anna','Zeno']], ['A', ['Zeno','anna']],
                ['d', ['Zeno','anna']], ['D', ['anna','Zeno']], ['a*', ['anna','Zeno']], ['d*', ['Zeno','anna']]]) {
                const bag = new context.gnr.GnrBag();
                bag.setItem('one', 'anna'); bag.setItem('two', 'Zeno');
                const before = warnings.length;
                bag.sort('#v:' + mode);
                assert.deepEqual(Array.from(bag.getNodes(), n => n.getValue()), expected);
                assert.equal(warnings.length - before, 0);
            }
        }
        assert.deepEqual(warnings, []);
    } finally { console.warn = original; }
});

test('both grid sort producers emit canonical modes without stars', () => {
    const fs = require('node:fs'), path = require('node:path');
    const source = fs.readFileSync(path.join(__dirname, '../gnr_d11/js/genro_grid.js'), 'utf8');
    const methods = [...source.matchAll(/patch_sort: function\(\) \{([\s\S]*?)\n    \},/g)].filter(match => match[1].includes('cell.field +'));
    assert.equal(methods.length, 2);
    for (const match of methods) {
        for (const direction of [1, -1]) {
            let output;
            const context = {
                sortInfo: direction, datamode: 'bag',
                layout: {cells: [{field: 'name', dtype: 'T'}]},
                sourceNode: {attr: {}, attrDatapath: () => 'sortedBy'},
                setSortedBy: value => { output = value; }
            };
            const genro = {_data: {setItem: (path, value) => { output = value; }}};
            new Function('genro', match[1]).call(context, genro);
            assert.equal(output, direction > 0 ? 'name:a' : 'name:d');
        }
    }
});

test('node paths require an actual parent Bag reference', () => {
    const {gnr} = load();
    const root = new gnr.GnrBag();
    root.setItem('cliente.nome', 'Mario'); root.setBackRef();
    const node = root.getNode('cliente'), inner = root.getNode('cliente.nome');
    assert.equal(node.getFullpath(), 'cliente');
    assert.equal(node.fullpath, 'cliente');
    assert.equal(inner.getFullpath(), 'cliente.nome');
    assert.equal(inner.fullpath, 'cliente.nome');
    root.popNode('cliente');
    for (const mode of [undefined, '#', '##']) assert.equal(node.getFullpath(mode), null);
    assert.equal(node.fullpath, null);
    assert.equal(inner.getFullpath(), 'nome');
    assert.equal(inner.fullpath, 'nome');
    inner.setParentBag(null);
    assert.equal(inner.getFullpath(), null);
    assert.equal(inner.fullpath, null);
});

test('grid-style strict sum calls use the standalone contract without an adapter', () => {
    const {gnr, GenroBagJS} = load();
    const bag = new gnr.GnrBag();
    assert.equal(bag.sum, GenroBagJS.Bag.prototype.sum);
    bag.setItem('a', null, {amount: 3});
    bag.setItem('b', null, {amount: null});
    bag.setItem('c', null, {amount: 4});
    assert.equal(bag.sum('#a.amount', false), 7);
    assert.equal(bag.sum('#a.amount', true), null);
    assert.equal(bag.sum('#a.amount', true, n => n.label !== 'b'), 7);
});

test('digest temporarily wraps single-field rows with a deprecation warning only in the mixin', () => {
    const {gnr, GenroBagJS} = load();
    const warnings = [], original = console.warn;
    console.warn = message => warnings.push(message);
    try {
        const bag = new gnr.GnrBag(); bag.setItem('a', 1); bag.setItem('b', 2);
        const plain = value => JSON.parse(JSON.stringify(value));
        assert.deepEqual(plain(bag.digest('#v')), [[1], [2]]);
        assert.match(warnings.at(-1), /wrapping is deprecated/);
        assert.deepEqual(plain(bag.digest(['#v'], n => n.label === 'b')), [[2]]);
        assert.deepEqual(plain(bag.query('#v')), [1, 2]);
        const before = warnings.length;
        assert.deepEqual(plain(bag.digest('#k,#v')), [['a', 1], ['b', 2]]);
        assert.deepEqual(plain(bag.digest('#v', null, true)), [[1, 2]]);
        assert.equal(warnings.length, before);
        assert.deepEqual(plain(bag.digest('#v', true)), [[1, 2]]);
        assert.equal(warnings.length, before + 1); // Only the legacy boolean-signature warning.
        const native = new GenroBagJS.Bag(); native.setItem('a', 1);
        assert.deepEqual(plain(native.digest('#v')), [1]);
        const arrays = new gnr.GnrBag(); arrays.setItem('a', [1, 2]);
        assert.deepEqual(plain(arrays.digest('#v')), [[[1, 2]]]);
        assert.deepEqual(plain(new gnr.GnrBag().digest('#v')), []);
    } finally { console.warn = original; }
});


test('attribute search mixin defaults to deep first but delegates explicit order', () => {
    const {gnr, GenroBagJS} = load();
    const bag = new gnr.GnrBag();
    bag.setItem('branch.deep', 1, {match: 'yes'});
    bag.setItem('sibling', 2, {match: 'yes'});
    assert.equal(bag.getNodeByAttr('match').label, 'deep');
    assert.equal(bag.getNodeByAttr('match', 'yes').label, 'deep');
    assert.equal(bag.getNodeByAttr('match', undefined, false, false).label, 'sibling');
    assert.equal(GenroBagJS.Bag.prototype.getNodeByAttr.call(bag, 'match').label, 'sibling');
    bag.popNode('sibling');
    assert.equal(bag.getNodeByAttr('match', undefined, false, false).label, 'deep');
});

test('asDict retains framework recursive, flat, autolist and filtering conventions', () => {
    const {gnr, GenroBagJS} = load();
    const bag = new gnr.GnrBag();
    bag.setItem('section.Value', 3); bag.setItem('section.blank', null);
    bag.setItem('empty', new gnr.GnrBag()); bag.setItem('code', 'f()::JS');
    const plain = value => JSON.parse(JSON.stringify(value));
    assert.deepEqual(plain(bag.asDict(true, true)), {section: {Value: 3}});
    assert.deepEqual(plain(bag.asDict('flat', true)), {Value: 3});
    const list = new gnr.GnrBag();
    list.setItem('r0', 'f()::JS', {_autolist: true}); list.setItem('r1', 0);
    bag.setItem('list', list);
    assert.deepEqual(plain(bag.asDict(true, true)).list, ['f()::JS', 0]);
    assert.deepEqual(plain(GenroBagJS.Bag.prototype.asDict.call(bag, false, false, true, true)), {
        section: {Value: 3}, empty: {}, code: 'f()::JS', list: {r0: 'f()::JS', r1: 0}
    });
});

test('prototype property names remain ordinary labels through the mixin', () => {
    const {gnr} = load();
    for (const label of ['__proto__', 'constructor', 'toString', 'hasOwnProperty']) {
        const bag = new gnr.GnrBag();
        for (let round = 0; round < 2; round++) {
            assert.equal(bag.getNode(label), null);
            bag.setItem(label, 1);
            const node = bag.getNode(label);
            bag.setItem(label, 2);
            assert.equal(bag.getNode(label), node);
            assert.equal(bag.len(), 1);
            assert.equal(Object.getOwnPropertyDescriptor(bag.asDict(), label).value, 2);
            assert.equal(bag.pop(label), 2);
            assert.equal(bag.getNode(label), null);
            bag.setItem(label, 3);
            bag.clear();
            assert.equal(bag.len(), 0);
            assert.equal(bag.getNode(label), null);
        }
    }
});

test('fillFrom replaces atomically through the mixin, including self assignment', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({old: 1});
    bag.fillFrom({fresh: {leaf: 2}});
    assert.equal(bag.getNode('old'), null);
    assert.equal(bag.fillFrom(bag), bag);
    assert.equal(bag.getItem('fresh.leaf'), 2);
    const node = bag.getNode('fresh');
    const source = {first: 3, get broken() { throw new Error('bad source'); }};
    assert.throws(() => bag.fillFrom(source), /bad source/);
    assert.equal(bag.getNode('fresh'), node);
    assert.equal(bag.getNode('first'), null);
});


test('isEqual preserves legacy identity while native equality compares content', () => {
    const {gnr, GenroBagJS} = load();
    const a = new gnr.GnrBag({x: 1});
    const b = new gnr.GnrBag({x: 1});
    assert.equal(a.isEqual(a), true);
    assert.equal(a.isEqual(b), false);
    assert.equal(a.isEqual(null), false);
    assert.equal(a.isEqual(undefined), false);
    assert.equal(a.isEqual({}), false);
    assert.equal(a.equalTo(b), true);
    const parent = new gnr.GnrBag();
    parent.setItem('a', a); parent.setItem('b', b); parent.setBackRef();
    assert.equal(a.isEqual(b), false);
    b._parentnode = a._parentnode;
    assert.equal(a.isEqual(b), true);
});


test('equalTo compares nested framework Bags by content independently of isEqual', () => {
    const {gnr} = load();
    const a = new gnr.GnrBag(); const b = new gnr.GnrBag();
    a.setItem('child.x', 1); b.setItem('child.x', 1);
    assert.equal(a.isEqual(b), false);
    assert.equal(a.equalTo(b), true);
    assert.equal(a.equalTo(null), false);
    b.setItem('child.x', 2);
    assert.equal(a.equalTo(b), false);
});

test('setAttr inherits native autocreation despite reserved legacy getNode argument', () => {
    const {gnr} = load(); const bag = new gnr.GnrBag();
    bag.setAttr('section.customer', {caption: 'Customer'});
    const node = bag.getNode('section.customer');
    assert.ok(node);
    assert.equal(node.getValue(), null);
    assert.equal(node.attr.caption, 'Customer');
    node.setValue(42);
    bag.setAttr('section.customer', {color: 'blue'});
    assert.equal(bag.getNode('section.customer'), node);
    assert.equal(node.getValue(), 42);
    assert.equal(node.attr.caption, 'Customer');
    assert.equal(node.attr.color, 'blue');
});

test('deprecated fillFrom bridges legacy array sources while replace stays Bag-only', () => {
    const {gnr, GenroBagJS} = load();
    const bag = new gnr.GnrBag({old: 1});
    assert.equal(GenroBagJS.Bag.prototype.fillFrom, undefined);
    assert.equal(bag.fillFrom([['name', 'Mario', {role: 'customer'}]]), bag);
    assert.deepEqual(Array.from(bag.keys()), ['name']);
    assert.equal(bag.getNode('name').attr.role, 'customer');
    bag.fillFrom([{name: 'Anna'}, {name: 'Mario'}]);
    assert.deepEqual(Array.from(bag.keys()), ['r_0', 'r_1']);
    assert.equal(bag.getItem('r_0.name'), 'Anna');
    assert.equal(bag.getNode('r_0').attr._autolist, true);
    assert.throws(() => bag.replace({x: 1}), /expects a Bag/);
    bag.fillFrom([]);
    assert.equal(bag.len(), 0);
});

test('retired Bag formulas and validation are not restored by mixins', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag();
    for (const name of ['formula', 'defineFormula', 'defineSymbol']) {
        assert.equal(typeof bag[name], 'undefined');
    }
    assert.equal(typeof gnr.GnrBagFormula, 'undefined');
    const node = bag.setItem('x', 1);
    assert.equal('isValid' in node, false);
    assert.equal('_invalidReasons' in node, false);
});
