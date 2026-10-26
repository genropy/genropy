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
    function rows(owner, ...keys) {
        const result = new Bag();
        keys.forEach(key => result.setItem(key, new Bag({A: null, B: 'typed'})));
        owner.setItem('sheet.List', result, null, {doTrigger: false});
        return result;
    }
    form.resetChanges();
    return {form, record, Bag, rows};
}

test('deleting a row forgets the invalid fields recorded under it', () => {
    const s = createForm();
    const list = s.rows(s.record, 'r_0', 'r_1', 'r_10');
    const invalid = s.record.getParentNode().attr._invalidFields = {
        'sheet.List.r_0.A': {}, 'sheet.List.r_1.A': {}, 'sheet.List.r_1.B': {}, 'sheet.List.r_10.A': {}};
    list.popNode('r_1');
    assert.deepEqual(Object.keys(invalid), ['sheet.List.r_0.A', 'sheet.List.r_10.A']);
});

test('a row of a related record forgets the invalid fields kept by that record', () => {
    const s = createForm();
    const related = new s.Bag();
    s.record.setItem('@related', related, {_pkey: 'R1', mode: 'O'}, {doTrigger: false});
    const list = s.rows(related, 'r_0', 'r_1');
    const invalid = s.record.getNode('@related').attr._invalidFields = {'sheet.List.r_0.A': {}, 'sheet.List.r_1.A': {}};
    list.popNode('r_1');
    assert.deepEqual(Object.keys(invalid), ['sheet.List.r_0.A']);
});

test('the invalid fields shown again after a save never recreate a removed row', () => {
    const s = createForm();
    s.rows(s.record, 'r_0');
    const invalid = {'sheet.List.r_0.A': {}, 'sheet.List.r_1.A': {}};
    s.form._triggerInvalidFields(invalid, s.record);
    assert.deepEqual(Array.from(s.record.getItem('sheet.List').keys()), ['r_0']);
    assert.deepEqual(Object.keys(invalid), ['sheet.List.r_0.A']);
});
