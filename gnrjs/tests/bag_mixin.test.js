const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadClasses} = require('./bag_audit_harness.cjs');
const load = () => loadClasses(['gnrlang.js', 'genro_bagjs_bundle.js', 'gnrbag_mixin.js', 'gnrdomsource.js']);

test('mixin uses native inheritance with no reserve adapter or enumerable-method patch', () => {
    const c = load();
    const bag = new c.gnr.GnrBag();
    assert.ok(bag instanceof c.GenroBagJS.Bag);
    for (const name of ['forEach', 'digest', 'sort', 'walk', 'items', 'keys', 'values', 'columns', 'update', 'deepcopy']) {
        assert.equal(bag[name], c.GenroBagJS.Bag.prototype[name], name);
        assert.equal(Object.getOwnPropertyDescriptor(c.GenroBagJS.Bag.prototype, name).enumerable, false);
    }
    assert.equal(c.GenroBagJS.Bag.prototype.asHtmlTable, undefined);
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

test('tuple lookup keeps framework shape and unsupported kwargs do not silently change meaning', () => {
    const {gnr} = load();
    const bag = new gnr.GnrBag({item: 1});
    const found = bag.getNode('item', true);
    assert.equal(found.obj, bag);
    assert.equal(found.node, bag.getNode('item'));
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

test('addItem preserves duplicate labels, order, lookup and deletion on DOM source bags', () => {
    const {gnr} = load();
    const bag = new gnr.GnrDomSource();
    const events = [];
    bag.subscribe('test', {any: event => events.push(event)});
    const first = bag.addItem('panel.row', 'first', {tag:'div'});
    const second = bag.addItem('panel.row', 'second', {tag:'span'});
    assert.ok(first instanceof gnr.GnrDomSourceNode);
    assert.equal(bag.getNode('panel.row'), first);
    assert.equal(bag.getNode('panel.#1'), second);
    assert.equal(bag.getItem('panel').length, 2);
    const head = bag.addItem('panel.row', 'head', null, {_position:'<', doTrigger:false});
    assert.equal(bag.getNode('panel.row'), head);
    assert.equal(bag.getItem('panel').pop('row', false), 'head');
    assert.equal(bag.getNode('panel.row'), first);
    assert.equal(bag.getItem('panel').pop('row', false), 'first');
    assert.equal(bag.getNode('panel.row'), second);
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

test('resolver cache treats sourceNode as context identity without serializing its tree', () => {
    const {gnr} = load();
    const source = new gnr.GnrDomSource();
    source.setBackRef();
    const node = source.setItem('widget', new gnr.GnrDomSource({child:1}));
    let calls = 0, received;
    const resolver = new gnr.GnrBagCbResolver({method: kw => {received=kw._sourceNode; return ++calls;}}, false, -1);
    assert.equal(resolver.resolve({_sourceNode:node, value:1}),1);
    assert.equal(received,node);
    assert.equal(resolver.resolve({_sourceNode:node, value:1}),1);
    assert.equal(resolver.resolve({_sourceNode:node, value:2}),2);
    const other = source.setItem('other',null);
    assert.equal(resolver.resolve({_sourceNode:other,value:2}),3);
});

test('GenroJS expression reads operate on values and attributes without resolver kwargs', () => {
    const c = load();
    c.genro.evaluate = code => require('node:vm').runInContext('(' + code + ')', c);
    const {gnr} = c;
    const bag = new gnr.GnrBag();
    bag.setItem('data',new gnr.GnrBag({a:1,b:2}),{caption:'Hello'});
    assert.equal(bag.getItem('data?=#v.len()'),2);
    assert.equal(bag.getItem('data?caption?=#v.toUpperCase()'),'HELLO');
    assert.equal(bag.getItem('absent?=#v ? 1 : 0'),0);
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
    const discarded = [];
    const handler = {pendingBuild: [], building: false,
        _trigger_del: event => handled.push(event.node.label),
        _onDeletingContent: () => {},
        deleteChildrenExternalWidget: node => discarded.push(node.label),
        cleanupNodeSubscriptions: () => {}};
    source.subscribe('delete-test', {del: event => gnr.GnrSrcHandler.prototype.nodeTrigger.call(handler, event)});
    parent.freeze();
    const removed = content.popNode('first');
    assert.equal(removed.getParentBag(), null);
    //no rebuild while frozen, but the detached content is torn down now: the
    //rebuild on unfreeze runs on the new value and never sees it again
    assert.deepEqual(handled, []);
    assert.deepEqual(discarded, ['first']);
    parent.unfreeze(true);
    content.popNode('second');
    assert.deepEqual(handled, ['second']);
    assert.deepEqual(discarded, ['first']);
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
    assert.equal(resolver.kwargs, kwargs);
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
