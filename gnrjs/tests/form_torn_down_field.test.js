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
            // genro_widgets.js extends dijit classes this harness does not load
            Declared.prototype = Object.assign(Object.create(base && base.prototype ? base.prototype : Object.prototype), members);
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
    context.dijit = {form: {ValidationTextBox: function() {}}};
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const record = new Bag();
    record.setItem('nome', 'Lombardia');
    const rows = new Bag();
    rows.setItem('r_1', new Bag({sigla: 'MI', nome: 'Milano'}));
    record.setItem('rows', rows);
    data.setItem('outer.record', record, {_pkey: 'LOM'});
    data.setItem('outer.controller', new Bag());
    data.setBackRef();
    context.genro._data = data;
    context.genro.getDataNode = p => data.getNode(p);
    context.genro.getData = p => data.getItem(p);
    // the live source tree, what nodeBySourceNodeId resolves against
    const main = new context.gnr.GnrDomSource();
    context.genro.src = {_main: main, _index: {}, _started: true, formsToUpdate: {}, nodeBySourceNodeId: id => main.findNodeById(id)};
    context.genro.vld = new context.gnr.GnrValidator(context.genro);
    context.genro.wdg = {
        getHandler: () => null,
        // what genro_wdg does for a textbox with validate_*: a ValidationTextBox and the validate mixin
        create(tag, destination, attributes, ind, sourceNode) {
            const widget = Object.assign(Object.create(context.dijit.form.ValidationTextBox.prototype),
                                         {gnr: {connectChangeEvent() {}}, validate() {}});
            sourceNode.widget = widget;
            sourceNode.setValidations();
            sourceNode.validationsOnChange = context.gnr.widgets.baseDojo.prototype.validatemixin_validationsOnChange;
            return widget;
        }
    };
    const formNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    formNode.absDatapath = value => value[0] === '.' ? 'outer' + value : value;
    formNode.getParentNode = () => ({});
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode: formNode,
        formDatapath: 'outer.record',
        controllerPath: 'outer.controller',
        pkeyPath: 'outer.pkey',
        gridEditors: {},
        _register: {},
        autoRegisterTags: {textbox: true},
        checkLastSavedTags: {},
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
    main._('div', 'body', {tag: 'div'});
    const body = main.getNode('body').getValue();
    // a row widget as a groupletGrid or an includedView grafts it: wrapper + one textbox
    function graftRow() {
        body._('div', 'row_r_1', {tag: 'div', datapath: '.r_1'});
        body.getNode('row_r_1').getValue()._('textbox', 'sigla', {tag: 'textbox', value: '^.sigla', validate_notnull: true});
        const node = body.getNode('row_r_1').getValue().getNode('sigla');
        node.form = form;
        node.updateValidationClasses = () => {};
        node.getElementLabel = () => 'Sigla';
        node.absDatapath = () => 'outer.record.rows.r_1.sigla';
        node.isLostNode = () => false;
        form.registerChild(node);
        return node;
    }
    const field = graftRow();
    field.setValidations();
    function tearDownRow() {
        // what the row's teardown does: popNode of the sourceNode runs _onDeleting → unregisterChild
        body.popNode('row_r_1');
        field._onDeleting();
    }
    function rebuildRow() {
        const node = graftRow();
        node._doBuildNode('textbox', {value: record.getItem('rows.r_1.sigla')}, null);
        return node;
    }
    return {Bag, form, field, record, rows, tearDownRow, rebuildRow};
}

test('a field invalid on its own validations no longer blocks the form once torn down', () => {
    const s = createForm();
    s.field.setValidationError({error: 'Required', warnings: [], required: true});
    s.form.updateInvalidField(s.field, 'outer.record.rows.r_1.sigla');
    assert.equal(s.form.isValid(), false);
    s.tearDownRow();
    assert.equal(s.form.getInvalidFields().len(), 0);
    assert.equal(s.form.isValid(), true);
});

test('a field invalid for dojo no longer blocks the form once torn down', () => {
    const s = createForm();
    s.form.dojoValidation({sourceNode: s.field}, false);
    assert.equal(s.form.isValid(), false);
    s.tearDownRow();
    assert.equal(s.form.getInvalidDojo().len(), 0);
    assert.equal(s.form.isValid(), true);
});

test('a widget rebuilt over a value still invalid makes the form invalid again', () => {
    const s = createForm();
    s.record.setItem('rows.r_1.sigla', null);
    s.field.setValidationError({error: 'Required', warnings: [], required: true});
    s.form.updateInvalidField(s.field, 'outer.record.rows.r_1.sigla');
    s.tearDownRow();
    assert.equal(s.form.isValid(), true);
    const rebuilt = s.rebuildRow();
    assert.equal(s.form.isValid(), false);
    assert.deepEqual(Object.keys(s.form.getInvalidFields().getItem('#0')), [rebuilt.getStringId()]);
});

test('tearing down one of two invalid widgets on the same path keeps the other', () => {
    const s = createForm();
    const twin = Object.create(s.field);
    twin._id = s.field._id + 100000;
    twin.getStringId = () => 'n_' + twin._id;
    twin.setValidations();
    twin.setValidationError({error: 'Required', warnings: [], required: true});
    s.field.setValidationError({error: 'Required', warnings: [], required: true});
    s.form.updateInvalidField(s.field, 'outer.record.rows.r_1.sigla');
    s.form.updateInvalidField(twin, 'outer.record.rows.r_1.sigla');
    s.form.unregisterChild(s.field);
    assert.equal(s.form.getInvalidFields().len(), 1);
    assert.deepEqual(Object.keys(s.form.getInvalidFields().getItem('#0')), [twin.getStringId()]);
    assert.equal(s.form.isValid(), false);
});

test('popping a new row takes its change entries away, popping a loaded one logs its real path', () => {
    const s = createForm();
    s.rows.setItem('r_2', new s.Bag({sigla: null, nome: 'Nuova'}));
    s.rows.getItem('r_2').setItem('sigla', 'BG');
    assert.deepEqual(Array.from(s.form.getChangesLogger().keys()), ['record_rows_r_2', 'record_rows_r_2_sigla']);
    s.rows.popNode('r_2');
    assert.deepEqual(Array.from(s.form.getChangesLogger().keys()), []);
    assert.equal(s.form.changed, false);
    s.rows.popNode('r_1');
    assert.deepEqual(Array.from(s.form.getChangesLogger().keys()), ['record_rows_r_1']);
    assert.equal(s.form.changed, true);
});
