const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createForm() {
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
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const record = new Bag();
    data.setItem('form.record', record, {_pkey: 'MI'});
    data.setItem('form.controller', new Bag());
    data.setItem('form.pkey', 'MI');
    data.setBackRef();
    context.genro._data = data;
    const sourceNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    sourceNode.absDatapath = value => value;
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode,
        formDatapath: 'form.record',
        controllerPath: 'form.controller',
        pkeyPath: 'form.pkey',
        gridEditors: {},
        _status_list: [],
        isValid: () => true,
        isDisabled: () => false,
        disabledStatus: () => null,
        isProtectWrite: () => false,
        isNewRecord: () => false,
        publish: () => {},
        applyDisabledStatus: () => {}
    });
    form.resetChanges();
    function initial(field, value, attributes = {}) {
        record.setItem(field, value, attributes, {doTrigger: false});
    }
    function edit(field, value) {
        sourceNode.setRelativeData('form.record.' + field, value, null);
    }
    function fields() {
        return Array.from(form.getFormChanges().getItem('record').keys());
    }
    function assertClean() {
        assert.equal(form.hasChanges(), false);
        assert.equal(form.status, 'ok');
        assert.equal(form.getChangesLogger().len(), 0);
        assert.equal(record.getNodeByAttr('_loadedValue') == null, true);
        assert.deepEqual(fields(), []);
    }
    return {form, record, data, Bag, initial, edit, fields, assertClean};
}

for (const virtual of [false, true]) {
    for (const [name, before, after] of [
        ['equal', false, false],
        ['changed', true, false],
        ['to null', 10, null],
        ['from null', null, 10],
        ['to zero', 10, 0],
        ['to blank', 'text', '']
    ]) {
        test(`silent ${virtual ? 'virtual' : 'physical'} push: ${name}`, () => {
            const s = createForm();
            const attributes = {dtype: 'B', caption: 'Flag'};
            if (virtual) attributes.virtual_column = true;
            s.initial('flag', before, attributes);
            s.form.externalChange('flag', after);
            s.form.externalChange('flag', after);
            assert.equal(s.record.getItem('flag'), after);
            assert.deepEqual({...s.record.getNode('flag').attr}, attributes);
            s.assertClean();
        });
    }
}

for (const value of [false, null, 0, '']) {
    test(`silent push creates a clean node for ${JSON.stringify(value)}`, () => {
        const s = createForm();
        s.form.externalChange('flag', value);
        assert.ok(s.record.getNode('flag'));
        assert.equal(s.record.getItem('flag'), value);
        s.assertClean();
    });
}

for (const serverValue of [11, 12]) {
    test(`silent push acknowledges an edited field with value ${serverValue}`, () => {
        const s = createForm();
        s.initial('amount', 10, {dtype: 'L'});
        s.edit('amount', 11);
        assert.equal(s.form.hasChanges(), true);
        s.form.externalChange('amount', serverValue);
        s.assertClean();
        s.edit('amount', 13);
        assert.equal(s.record.getNode('amount').attr._loadedValue, serverValue);
        assert.deepEqual(s.fields(), ['amount']);
        s.edit('amount', serverValue);
        s.assertClean();
    });
}

test('a silent push preserves unrelated local edits', () => {
    const s = createForm();
    s.initial('name', 'before');
    s.edit('name', 'after');
    s.form.externalChange('flag', false);
    assert.equal(s.form.hasChanges(), true);
    assert.equal(s.record.getNode('name').attr._loadedValue, 'before');
    assert.deepEqual(s.fields(), ['name']);
});

test('bindings receive one changed-value notification and no duplicate on an equal push', () => {
    const s = createForm();
    s.initial('flag', true, {virtual_column: true});
    const values = [];
    s.data.subscribe('binding', {any: kw => {
        if (kw.node.label === 'flag') values.push(kw.node.getValue());
    }});
    s.form.externalChange('flag', false);
    s.form.externalChange('flag', false);
    assert.deepEqual(values, [false]);
    s.assertClean();
});

test('a reactive write to another field is still a local edit', () => {
    const s = createForm();
    s.initial('derived', 1);
    s.data.subscribe('controller', {any: kw => {
        if (kw.node.label === 'amount') s.edit('derived', 2);
    }});
    s.form.externalChange('amount', 12);
    assert.equal(s.record.getNode('derived').attr._loadedValue, 1);
    assert.deepEqual(s.fields(), ['derived']);
});

test('a reactive write to the pushed field uses the server value as its baseline', () => {
    const s = createForm();
    s.initial('amount', 10);
    s.data.subscribe('controller', {any: kw => {
        if (kw.node.label === 'amount' && kw.node.getValue() === 12) s.edit('amount', 13);
    }});
    s.form.externalChange('amount', 12);
    assert.equal(s.record.getItem('amount'), 13);
    assert.equal(s.record.getNode('amount').attr._loadedValue, 12);
    assert.deepEqual(s.fields(), ['amount']);
});

test('non-silent pushes keep normal change tracking and preserve attributes', () => {
    const s = createForm();
    s.initial('amount', 10, {dtype: 'L'});
    s.form.externalChange('amount', 12, true);
    assert.equal(s.form.hasChanges(), true);
    assert.equal(s.record.getNode('amount').attr.dtype, 'L');
    assert.equal(s.record.getNode('amount').attr._loadedValue, 10);
    assert.deepEqual(s.fields(), ['amount']);
});

test('a non-silent insertion is still tracked', () => {
    const s = createForm();
    s.form.externalChange('amount', 12, true);
    assert.equal(s.form.hasChanges(), true);
    assert.deepEqual(s.fields(), ['amount']);
});

for (const change of ['none', 'update', 'insert', 'delete']) {
    test(`a silent Bag replacement clears its ${change} changes`, () => {
        const s = createForm();
        s.initial('payload', new s.Bag({a: 1, b: 2}), {dtype: 'X'});
        if (change === 'update') s.edit('payload.a', 3);
        if (change === 'insert') s.edit('payload.c', 3);
        if (change === 'delete') s.record.popNode('payload.a');
        s.form.externalChange('payload', new s.Bag({a: 4}));
        assert.equal(s.record.getItem('payload.a'), 4);
        assert.equal(s.record.getNode('payload').attr.dtype, 'X');
        s.assertClean();
    });
}

test('a Bag replacement preserves a sibling whose name shares its prefix', () => {
    const s = createForm();
    s.initial('payload', new s.Bag({a: 1}), {dtype: 'X'});
    s.initial('payload_extra', 1);
    s.edit('payload_extra', 2);
    s.edit('payload.a', 3);
    s.form.externalChange('payload', new s.Bag({a: 4}));
    assert.deepEqual(s.fields(), ['payload_extra']);
    assert.equal(s.form.getChangesLogger().len(), 1);
    assert.equal(s.record.getNode('payload_extra').attr._loadedValue, 1);
});

test('an equal Bag snapshot acknowledges child changes', () => {
    const s = createForm();
    s.initial('payload', new s.Bag({a: 1}), {dtype: 'X'});
    s.edit('payload.a', 2);
    s.form.externalChange('payload', s.record.getItem('payload'));
    s.assertClean();
});

test('a silent push acknowledges a previously deleted field', () => {
    const s = createForm();
    s.initial('amount', 10);
    s.record.popNode('amount');
    s.form.externalChange('amount', 12);
    s.assertClean();
});
