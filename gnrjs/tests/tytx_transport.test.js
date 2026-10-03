const test = require('node:test');
const assert = require('node:assert/strict');
const {loadClasses} = require('./bag_audit_harness.cjs');

test('TYTX envelope reconstruction preserves typed values and DOM source classes', () => {
    const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js','gnrdomsource.js']);
    c.atob = value => Buffer.from(value, 'base64').toString('binary');
    c.btoa = value => Buffer.from(value, 'binary').toString('base64');
    const source = new c.GenroBagJS.Bag();
    source.setItem('result', new c.GenroBagJS.Bag({text:'literal::T', empty:new c.GenroBagJS.Bag(), flag:false}), {__cls:'domsource', nullable:false});
    const envelope = new c.gnr.GnrBag();
    envelope.fromTytxDoc(source.toTytx('json'), {domsource:c.gnr.GnrDomSource});
    assert.ok(envelope.getItem('result') instanceof c.gnr.GnrDomSource);
    // Recognized TYTX suffixes in literal strings are interpreted by contract.
    assert.equal(envelope.getItem('result.text'), 'literal');
    assert.equal(envelope.getItem('result.flag'), false);
    assert.ok(envelope.getItem('result.empty') instanceof c.gnr.GnrDomSource);
    assert.equal(envelope.getNode('result').attr.nullable, false);
});

test('TYTX relation resolvers preserve cached values and reload only on demand', () => {
    const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js']);
    let loads = 0;
    c.genro.getRelationResolver = () => new c.gnr.GnrBagCbResolver({method: () => {
        loads++; return new c.gnr.GnrBag({fresh:1});
    }}, false, 60);
    const source = new c.GenroBagJS.Bag();
    source.setItem('relation', new c.GenroBagJS.Bag({item:'cached'}), {_resolver_name:'relation', _resolvedInfo:{caption:'Loaded'}});
    const target = new c.gnr.GnrBag();
    target.fromTytxDoc(source.toTytx('json'));
    assert.equal(target.getItem('relation.item'), 'cached');
    assert.equal(target.getNode('relation').attr.caption, 'Loaded');
    assert.equal(loads, 0);
    target.getNode('relation').resolver.reset();
    assert.equal(target.getItem('relation.fresh'), 1);
    assert.equal(loads, 1);
});

test('TYTX Python resolver descriptions become framework remote resolvers', () => {
    const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js']);
    let received;
    c.genro.rpc = {};
    c.genro.rpc.remoteResolver = (method, params, options) => {
        received = {method, params, options};
        return new c.gnr.GnrBagCbResolver({method: () => 'loaded'}, false, options.cacheTime);
    };
    const source = new c.GenroBagJS.Bag();
    source.setItem('remote',
        '::RSLV:{"resolver_module":"pkg.mod","resolver_class":"Items","args":[1],"kwargs":{"cache_time":12}}');
    const encoded = source.toTytx('json');
    const target = new c.gnr.GnrBag();
    target.fromTytxDoc(encoded);
    assert.equal(received.method, 'resolverRecall');
    assert.deepEqual(JSON.parse(JSON.stringify(received.params.resolverPars)), {
        resolvermodule:'pkg.mod', resolverclass:'Items', args:[1], kwargs:{cache_time:12}, cacheTime:0
    });
    assert.equal(received.options.cacheTime, 12);
    assert.equal(target.getItem('remote'), 'loaded');
});

test('TYTX RPC references remain opaque transport tokens', () => {
    const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js']);
    const source = new c.GenroBagJS.Bag({callback:'app.run::RPC', caption:'literal::RPC suffix'});
    const target = new c.gnr.GnrBag();
    target.fromTytxDoc(source.toTytx('json'));
    assert.equal(target.getItem('callback'), 'app.run::RPC');
    assert.equal(target.getItem('caption'), 'literal::RPC suffix');
});

test('remote resolver callback accepts a text TYTX response without an XML document', () => {
    const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js','genro_rpc.js']);
    const response = 'typed-json-response';
    c.genro.rpc = {resultHandler: (body) => { assert.equal(body,response); return 42; }};
    assert.equal(c.gnr.GnrRemoteResolver.prototype.resultHandler.call({updateAttr:false},response,{}),42);
});


test('Python infinite resolver cache preserves menu node identity and full paths', () => {
    const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js']);
    let loads = 0;
    c.genro.rpc = {remoteResolver: (method, params, options) => {
        assert.equal(options.cacheTime, -1);
        return new c.gnr.GnrBagCbResolver({method: () => {
            loads++;
            return new c.gnr.GnrBag({entry: 'Invoice rows'});
        }}, false, options.cacheTime);
    }};
    const source = new c.GenroBagJS.Bag();
    source.setItem('root', '::RSLV:{"resolver_module":"gnr.web.gnrmenu","resolver_class":"MenuResolver","args":[],"kwargs":{"cache_time":false}}');
    const menu = new c.gnr.GnrBag();
    menu.fromTytxDoc(source.toTytx('json'));
    const store = new c.gnr.GnrBag();
    store.setBackRef();
    store.setItem('gnr.appmenu', menu);
    const entry = store.getItem('gnr.appmenu.root').getNode('entry');
    assert.equal(store.getItem('gnr.appmenu.root').getNode('entry'), entry);
    assert.equal(entry.getFullpath(), 'gnr.appmenu.root.entry');
    assert.equal(loads, 1);
});
