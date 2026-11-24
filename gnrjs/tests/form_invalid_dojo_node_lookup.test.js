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
        isIE: 0,
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_src.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str.replace(/^!!/, '');
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const record = new Bag({sigla: null});
    data.setItem('outer.record', record, {_pkey: 'LOM'});
    data.setItem('outer.controller', new Bag());
    data.setBackRef();
    context.genro._data = data;
    context.genro.getDataNode = p => data.getNode(p);
    const src = Object.create(context.gnr.GnrSrcHandler.prototype);
    src._main = new context.gnr.GnrDomSource();
    context.genro.src = src;
    context.genro.wdg = {getHandler: () => null};
    const formNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    formNode.absDatapath = value => value[0] === '.' ? 'outer' + value : value;
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode: formNode,
        formDatapath: 'outer.record',
        controllerPath: 'outer.controller',
        pkeyPath: 'outer.pkey',
        gridEditors: {},
        _register: {},
        _status_list: [],
        allowSaveInvalid: false,
        isDisabled: () => false,
        disabledStatus: () => null,
        isProtectWrite: () => false,
        isNewRecord: () => false,
        registeredGridsStatus: () => null,
        publish: () => {},
        applyDisabledStatus: () => {}
    });
    form.resetInvalidFields();
    form.resetChanges();
    src._main._('div', 'body', {tag: 'div'});
    const body = src._main.getNode('body').getValue();
    body._('dbselect', 'sigla', {tag: 'dbselect', value: '^.record.sigla'});
    const field = body.getNode('sigla');
    Object.assign(field, {
        form,
        absDatapath: () => 'outer.record.sigla',
        getElementLabel: () => 'Sigla',
        isLostNode: () => false
    });
    return {context, src, form, field, body, Bag};
}

test('nodeBySourceNodeId resolves a node by its string id as well as by its numeric id', () => {
    const s = createForm();
    assert.ok(s.src.nodeBySourceNodeId(s.field._id) === s.field, 'numeric id');
    assert.ok(s.src.nodeBySourceNodeId(s.field.getStringId()) === s.field, 'string id');
    assert.equal(s.src.nodeBySourceNodeId('n_x'), undefined);
    assert.equal(s.src.nodeBySourceNodeId('outer_record_sigla'), undefined);
    assert.equal(s.src.nodeBySourceNodeId('record_n_' + s.field._id), undefined);
});

test('checkInvalidFields keeps the invalidDojo entry of a live widget still invalid', () => {
    const s = createForm();
    s.form.dojoValidation({sourceNode: s.field}, false);
    assert.deepEqual(Array.from(s.form.getInvalidDojo().keys()), [s.field.getStringId()]);
    s.form.checkInvalidFields();
    assert.deepEqual(Array.from(s.form.getInvalidDojo().keys()), [s.field.getStringId()]);
    assert.equal(s.form.isValid(), false);
});

test('checkInvalidFields purges the invalidDojo entry of a node no longer in the source', () => {
    const s = createForm();
    s.form.dojoValidation({sourceNode: s.field}, false);
    s.body.popNode('sigla');
    s.form.checkInvalidFields();
    assert.equal(s.form.getInvalidDojo().len(), 0);
    assert.equal(s.form.isValid(), true);
});

test('the invalid message of a dojo-invalid field shows its own error', () => {
    const s = createForm();
    s.field._validations = {error: 'Unknown province'};
    s.form.dojoValidation({sourceNode: s.field}, false);
    assert.equal(s.form._buildInvalidMessage(), '<b>Sigla</b>: Unknown province');
});

test('the status panel of a dojo-invalid field shows its own error', () => {
    const s = createForm();
    s.field._validations = {error: 'Unknown province'};
    s.form.dojoValidation({sourceNode: s.field}, false);
    s.form.status = 'error';
    s.form.getFormErrors = () => [];
    assert.match(s.form.getSemaphoreStatus(), /<span class="fh_status_error">Unknown province<\/span>/);
});
