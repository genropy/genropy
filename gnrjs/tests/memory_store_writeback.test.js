const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            Declared.prototype.constructor = Declared;
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

// location: the Bag the memory form writes into; formData: what the form holds when saving
function saveMemory(kind, location, formData, currPkey) {
    const context = loadContext();
    const Bag = context.gnr.GnrBag;
    const sourceBag = new Bag();
    location(sourceBag, Bag);
    const data = new Bag();
    formData(data, Bag);
    let pkey = currPkey;
    const form = {
        sourceNode: {
            evaluateOnNode: value => Object.assign({}, value),
            getRelativeData: () => sourceBag
        },
        getFormData: () => data,
        getCurrentPkey: () => pkey,
        setCurrentPkey: value => { pkey = value; },
        setOpStatus: () => {},
        reset: () => {},
        load: () => {}
    };
    const store = Object.create(context.gnr.formstores[kind].prototype);
    Object.assign(store, {form, locationpath: '#FORM.record', handlers: {save: {kw: {}}}, saved: () => {}});
    store.save_memory({});
    return sourceBag;
}

test('an Item memory form keeps _sendback on a scalar it writes back unchanged', () => {
    const sourceBag = saveMemory('Item',
        b => b.setItem('__is_draft', true, {dtype: 'B', _sendback: true}),
        d => d.setItem('__is_draft', true, {dtype: 'B'}));
    assert.equal(sourceBag.getNode('__is_draft').attr._sendback, true);
});

test('an Item memory form keeps _sendback on a scalar it writes back changed', () => {
    const sourceBag = saveMemory('Item',
        b => b.setItem('__is_draft', true, {dtype: 'B', _sendback: true}),
        d => d.setItem('__is_draft', false, {dtype: 'B'}));
    const node = sourceBag.getNode('__is_draft');
    assert.equal(node.getValue(), false);
    assert.equal(node.attr._sendback, true);
});

test('an Item memory form keeps the _loadedValue of a field changed in the parent form', () => {
    const sourceBag = saveMemory('Item',
        b => b.setItem('name', 'X', {dtype: 'T', _loadedValue: 'A'}),
        d => d.setItem('name', 'X', {dtype: 'T'}));
    assert.equal(sourceBag.getNode('name').attr._loadedValue, 'A');
});

test('an Item memory form writes back the displayed value of a scalar', () => {
    const sourceBag = saveMemory('Item',
        b => b.setItem('city_id', 'c1', {dtype: 'T'}),
        d => d.setItem('city_id', 'c2', {dtype: 'T', _displayedValue: 'Milano'}));
    assert.equal(sourceBag.getNode('city_id').attr._displayedValue, 'Milano');
});

test('a Collection memory form keeps _sendback and _loadedValue on the scalars it writes back', () => {
    const sourceBag = saveMemory('Collection',
        (b, Bag) => {
            const row = new Bag();
            row.setItem('_pkey', 'r1');
            row.setItem('id', 'r1', {dtype: 'T', _sendback: true});
            row.setItem('name', 'X', {dtype: 'T', _loadedValue: 'A'});
            b.setItem('r1', row);
        },
        d => {
            d.setItem('_pkey', 'r1');
            d.setItem('id', 'r1', {dtype: 'T'});
            d.setItem('name', 'X', {dtype: 'T'});
        },
        'r1');
    assert.equal(sourceBag.getNode('r1.id').attr._sendback, true);
    assert.equal(sourceBag.getNode('r1.name').attr._loadedValue, 'A');
});

test('a memory form keeps the attributes of a Bag it writes back', () => {
    const sourceBag = saveMemory('Item',
        (b, Bag) => b.setItem('_righe_bozza', new Bag(), {_sendback: true}),
        (d, Bag) => d.setItem('_righe_bozza', new Bag()));
    assert.equal(sourceBag.getNode('_righe_bozza').attr._sendback, true);
});

test('an Item memory form drops a displayed value the scalar no longer carries', () => {
    const sourceBag = saveMemory('Item',
        b => b.setItem('city_id', 'c1', {dtype: 'T', _displayedValue: 'Roma', _sendback: true}),
        d => d.setItem('city_id', null, {dtype: 'T'}));
    const node = sourceBag.getNode('city_id');
    assert.equal(node.getValue(), null);
    assert.equal('_displayedValue' in node.attr, false);
    assert.equal(node.attr._sendback, true);
});

test('a Collection memory form writes back the displayed value over the stale one', () => {
    const sourceBag = saveMemory('Collection',
        (b, Bag) => {
            const row = new Bag();
            row.setItem('_pkey', 'r1');
            row.setItem('city_id', 'c1', {dtype: 'T', _displayedValue: 'Roma', _loadedValue: 'c1'});
            b.setItem('r1', row);
        },
        d => {
            d.setItem('_pkey', 'r1');
            d.setItem('city_id', 'c2', {dtype: 'T', _displayedValue: 'Milano'});
        },
        'r1');
    const node = sourceBag.getNode('r1.city_id');
    assert.equal(node.attr._displayedValue, 'Milano');
    assert.equal(node.attr._loadedValue, 'c1');
});
