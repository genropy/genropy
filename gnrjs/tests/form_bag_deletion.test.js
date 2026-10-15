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

function loadDocument(s, field = 'payload', record = s.record) {
    const details = new s.Bag();
    details.setItem('keep', new s.Bag({description: 'Keep', hidden: 'Preserved'}), {code: 'K'});
    details.setItem('remove', new s.Bag({description: 'Remove'}), {code: 'R'});
    const document = new s.Bag();
    document.setItem('body.details', details);
    record.setItem(field, document, {dtype: 'X'}, {doTrigger: false});
    return details;
}

test('deletion-only changes submit the updated Bag with surviving values and attributes', () => {
    const s = createForm();
    const details = loadDocument(s);
    details.popNode('remove');
    assert.deepEqual(Array.from(details.keys()), ['keep']);
    assert.equal(s.form.hasChanges(), true);
    const changes = s.form.getFormChanges();
    const sent = changes.getItem('record.payload');
    assert.ok(sent, 'Save must include the Bag after a child deletion');
    assert.equal(changes.__isRealChange, true);
    assert.deepEqual(Array.from(sent.getItem('body.details').keys()), ['keep']);
    assert.equal(sent.getItem('body.details.keep.hidden'), 'Preserved');
    assert.equal(sent.getNode('body.details.keep').attr.code, 'K');
    assert.notEqual(sent, s.record.getItem('payload'));
    assert.equal(s.record.getNodeByAttr('_loadedValue'), undefined);
});

test('deleting the last node submits an empty Bag', () => {
    const s = createForm();
    s.initial('payload', new s.Bag({only: 1}), {dtype: 'X'});
    s.record.getItem('payload').popNode('only');
    const sent = s.form.getFormChanges().getItem('record.payload');
    assert.ok(sent, 'An empty Bag must replace the stored value');
    assert.equal(sent.len(), 0);
});

test('a Bag deletion reaches a related record cluster', () => {
    const s = createForm();
    const related = new s.Bag();
    s.initial('@related', related, {_pkey: 'R1', mode: 'O'});
    const details = loadDocument(s, 'payload', related);
    details.popNode('remove');
    const changes = s.form.getFormChanges();
    const sent = changes.getItem('record.@related.payload');
    assert.ok(sent, 'The changed related record must be submitted');
    assert.equal(changes.__isRealChange, true);
    assert.equal(sent.getItem('body.details').len(), 1);
});

test('a deletion does not submit sibling Bags with a shared name prefix', () => {
    const s = createForm();
    loadDocument(s);
    const extra = loadDocument(s, 'payload_extra');
    extra.popNode('remove');
    assert.deepEqual(s.fields(), ['payload_extra']);
});

test('paths containing underscores do not alias nested paths', () => {
    const s = createForm();
    loadDocument(s, 'payload_extra');
    const related = new s.Bag();
    s.initial('payload', related, {_pkey: 'R1', mode: 'O'});
    const details = loadDocument(s, 'extra', related);
    details.popNode('remove');
    assert.deepEqual(s.fields(), ['payload']);
    assert.ok(s.form.getFormChanges().getItem('record.payload.extra'));
});

test('adding then deleting a new child leaves no Bag changes to save', () => {
    const s = createForm();
    const details = loadDocument(s);
    details.setItem('temporary', new s.Bag({description: 'Temporary'}));
    details.popNode('temporary');
    s.assertClean();
});

test('acknowledging a deletion clears the Bag changeset', () => {
    const s = createForm();
    const details = loadDocument(s);
    details.popNode('remove');
    s.form.externalChange('payload', s.record.getItem('payload'));
    s.assertClean();
});

for (const attributes of [{_sendback: false}, {virtual_column: true}]) {
    test(`a deletion respects excluded Bag fields: ${JSON.stringify(attributes)}`, () => {
        const s = createForm();
        const details = loadDocument(s);
        Object.assign(s.record.getNode('payload').attr, attributes);
        details.popNode('remove');
        assert.deepEqual(s.fields(), []);
    });
}
