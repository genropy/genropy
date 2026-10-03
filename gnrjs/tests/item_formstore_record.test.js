const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createStage({outerPkey = 'PK1'} = {}) {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout: () => {}};
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
    context.genro.evaluate = expr => vm.runInContext('(' + expr + ')', context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const record = new Bag();
    record.setItem('name', 'Rome', {dtype: 'T'});
    record.setItem('description', 'Main venue', {dtype: 'T'});
    record.setItem('seats', 120, {dtype: 'L'});
    record.setItem('extra', new Bag({room: 'A', setup: new Bag({chairs: 20})}), {dtype: 'X'});
    record.setItem('__moved_related', null, {dtype: 'X'});
    data.setItem('outer.record', record, {_pkey: outerPkey, caption: 'Rome'});
    data.setItem('outer.controller', new Bag());
    data.setItem('outer.pkey', outerPkey);
    data.setItem('inner.controller', new Bag());
    data.setBackRef();
    context.genro._data = data;
    context.genro.callAfter = (callback, delay, scope) => callback.call(scope);
    context.genro.dlg = {removeFloatingMessage() {}};
    const sourceNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    sourceNode.absDatapath = value => value;
    function createForm(root, extra) {
        const form = Object.create(context.gnr.GnrFrmHandler.prototype);
        return Object.assign(form, {
            sourceNode,
            formId: root,
            formDatapath: root + '.record',
            controllerPath: root + '.controller',
            pkeyPath: root + '.pkey',
            gridEditors: {},
            _status_list: [],
            isValid: () => true,
            isDisabled: () => false,
            disabledStatus: () => null,
            isProtectWrite: () => false,
            publish: () => {},
            setHider: () => {},
            applyDisabledStatus: () => {}
        }, extra);
    }
    const outer = createForm('outer', {isNewRecord: () => false});
    outer.resetChanges();
    const inner = createForm('inner', {
        autoSave: 500,
        loaded(result) {
            this.setFormData(result);
            this.reset();
        }
    });
    const store = new context.gnr.formstores.Item({handler: 'memory', locationpath: 'outer.record'},
                                                  {save: {}, load: {}, del: {}});
    store.init(inner);
    inner.store = store;
    inner.load();
    function editInner(field, value) {
        sourceNode.setRelativeData('inner.record.' + field, value, null);
    }
    function outerFields() {
        const changes = outer.getFormChanges().getItem('record');
        return changes ? Array.from(changes.keys()) : [];
    }
    function reloadProbe() {
        let asked = 0;
        Object.assign(inner, {
            autoSave: false,
            opStatus: null,
            setOpStatus(status) { this.opStatus = status || null; },
            openPendingChangesDlg() { asked++; }
        });
        return () => asked;
    }
    return {Bag, record, outer, inner, store, editInner, outerFields, reloadProbe};
}

test('saving an untouched record leaves the destination form clean', () => {
    const s = createStage();
    s.store.save_memory({});
    assert.equal(s.outer.getChangesLogger().len(), 0);
    assert.equal(s.record.getNodeByAttr('_loadedValue'), undefined);
    assert.deepEqual(s.outerFields(), []);
    assert.equal(s.record.getNode('name').attr.dtype, 'T');
    assert.equal(s.record.getNode('seats').attr.dtype, 'L');
});

test('only the edited field reaches the destination, keeping its attributes', () => {
    const s = createStage();
    s.editInner('description', 'Side venue');
    s.store.save_memory({});
    assert.equal(s.record.getItem('description'), 'Side venue');
    assert.deepEqual(s.outerFields(), ['description']);
    assert.equal(s.record.getNode('description').attr.dtype, 'T');
    assert.equal(s.record.getNode('description').attr._loadedValue, 'Main venue');
});

test('a later save keeps the change tracking of fields edited before', () => {
    const s = createStage();
    s.editInner('description', 'Side venue');
    s.store.save_memory({});
    s.editInner('seats', 80);
    s.store.save_memory({});
    assert.deepEqual(s.outerFields().sort(), ['description', 'seats']);
    assert.equal(s.record.getNode('description').attr._loadedValue, 'Main venue');
});

test('editing a field back to its loaded value leaves the destination clean', () => {
    const s = createStage();
    s.editInner('name', 'Milan');
    s.store.save_memory({});
    s.editInner('name', 'Rome');
    s.store.save_memory({});
    assert.equal(s.outer.getChangesLogger().len(), 0);
    assert.deepEqual(s.outerFields(), []);
});

test('a change inside a Bag column is written back', () => {
    const s = createStage();
    s.editInner('extra.setup.chairs', 30);
    s.store.save_memory({});
    assert.equal(s.record.getItem('extra.setup.chairs'), 30);
    assert.equal(s.record.getItem('extra.room'), 'A');
    assert.deepEqual(s.outerFields(), ['extra']);
});

test('a changed scalar takes the new label and keeps its dtype', () => {
    const s = createStage();
    s.record.getNode('name').attr._displayedValue = 'Roma';
    s.inner.load();
    s.inner.getFormData().setItem('name', 'Milan', {_displayedValue: 'Milano'}, {_updattr: true});
    s.store.save_memory({});
    const node = s.record.getNode('name');
    assert.equal(node.getValue(), 'Milan');
    assert.equal(node.attr._displayedValue, 'Milano');
    assert.equal(node.attr.dtype, 'T');
    assert.equal(node.attr._loadedValue, 'Rome');
});

test('a changed Bag column keeps its destination attributes', () => {
    const s = createStage();
    s.record.getNode('extra').attr._sendback = true;
    s.editInner('extra.room', 'B');
    s.store.save_memory({});
    const node = s.record.getNode('extra');
    assert.equal(node.getValue().getItem('room'), 'B');
    assert.equal(node.attr._sendback, true);
    assert.equal(node.attr.dtype, 'X');
});

test('the loaded pkey is the pkey of the destination record', () => {
    const s = createStage();
    assert.equal(s.inner.getCurrentPkey(), 'PK1');
    s.inner.reload();
    assert.equal(s.inner.getCurrentPkey(), 'PK1');
    assert.equal(s.inner.getFormData().getItem('name'), 'Rome');
});

test('a plain load on a changed form over a real record reloads it without asking', () => {
    const s = createStage();
    const asked = s.reloadProbe();
    s.editInner('description', 'set by the build');
    assert.equal(s.inner.changed, true);
    s.inner.load();
    assert.equal(asked(), 0);
    assert.equal(s.inner.getFormData().getItem('description'), 'Main venue');
    assert.equal(s.inner.getCurrentPkey(), 'PK1');
});

test('a plain load on a dismissed form reloads it without asking', () => {
    const s = createStage();
    const asked = s.reloadProbe();
    s.inner.doload_store({destPkey: '*dismiss*'});
    assert.equal(s.inner.getCurrentPkey(), null);
    s.editInner('description', 'set by the build');
    s.inner.load();
    assert.equal(asked(), 0);
    assert.equal(s.inner.getFormData().getItem('description'), 'Main venue');
    assert.equal(s.inner.getCurrentPkey(), 'PK1');
});

test('a new destination record keeps the placeholder pkey and its data', () => {
    const s = createStage({outerPkey: '*newrecord*'});
    assert.equal(s.inner.getCurrentPkey(), '*loaditem*');
    s.inner.reload();
    assert.equal(s.inner.getFormData().getItem('name'), 'Rome');
});

test('hasSameValues compares labels and values, not attributes', () => {
    const {Bag} = createStage();
    const a = new Bag({x: 1, y: new Bag({z: 'k'})});
    const b = new Bag();
    b.setItem('x', 1, {dtype: 'L'});
    b.setItem('y', new Bag({z: 'k'}), {dtype: 'X'});
    assert.equal(a.hasSameValues(b), true);
    b.setItem('y.z', 'j');
    assert.equal(a.hasSameValues(b), false);
    assert.equal(a.hasSameValues(new Bag({y: new Bag({z: 'k'}), x: 1})), false);
    assert.equal(a.hasSameValues(null), false);
});

test('invalid fields marked on the item form stay on its own record', () => {
    const s = createStage();
    s.editInner('description', '');
    const innerRecord = s.inner.getFormData();
    s.inner.setRecordInvalidFields(innerRecord.getNode('description'), true, {error: 'Required'});
    assert.ok(s.inner.getDataNodeAttributes()._invalidFields.description);
    s.store.save_memory({});
    assert.equal(s.record.getItem('description'), '');
    const outerRecordNode = s.record.getParentNode();
    assert.equal(outerRecordNode.attr._invalidFields, undefined);
    assert.equal(s.record.getNodeByAttr('_invalidFields'), undefined);
    assert.equal(s.inner.getDataNodeAttributes()._invalidFields, undefined);
});
