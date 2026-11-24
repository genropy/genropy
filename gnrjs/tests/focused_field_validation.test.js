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
        connect() {},
        require() {},
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js', 'genro_wdg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    data.setItem('outer.record', new Bag({customer_id: null}), {_pkey: 'LOM'});
    data.setItem('outer.controller', new Bag());
    data.setItem('outer.pkey', 'LOM');
    data.setBackRef();
    context.genro._data = data;
    context.genro.getDataNode = p => data.getNode(p);
    context.genro.getData = p => data.getItem(p);
    context.genro.dom = {setClass() {}};
    context.genro.wdg = {getHandler: () => null};
    const main = new context.gnr.GnrDomSource();
    context.genro.src = {_main: main, _index: {}, _started: true, formsToUpdate: {}, nodeBySourceNodeId: id => main.findNodeById(id)};
    context.genro.vld = new context.gnr.GnrValidator(context.genro);
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
        autoRegisterTags: {},
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
    main.getNode('body').getValue()._('textbox', 'customer', {tag: 'textbox', value: '^.customer_id'});
    main.setBackRef();
    const field = main.getNode('body.customer');
    field.form = form;
    field.getElementLabel = () => 'Customer';
    field.absDatapath = () => 'outer.record.customer_id';
    field.isLostNode = () => false;
    field.setValidations();
    // a dijit validating widget: validate(isFocused) delegates to isValid(isFocused)
    function buildWidget(isValid) {
        const widget = {sourceNode: field, gnr: {}, valid: false, isValid,
                        validate(isFocused) { return this.isValid(isFocused); }};
        context.gnr.widgets.baseHtml.prototype._created(widget, {}, field);
        field.widget = widget;
        return widget;
    }
    const invalidEntry = () => form.getInvalidDojo().getNode(field.getStringId());
    return {context, form, field, buildWidget, invalidEntry};
}

const dijitIsValid = function() { return this.valid; };
// gnr NumberTextBox.patch_isValid: always valid while focused
const numberIsValid = function(isFocused) { return isFocused ? true : this.valid; };

test('a field that turns valid while focused leaves invalidDojo and unblocks the form', () => {
    const s = createForm();
    const widget = s.buildWidget(dijitIsValid);
    widget.validate(false);
    assert.ok(s.invalidEntry());
    assert.equal(s.form.status, 'error');
    widget.valid = true;
    widget.validate(true);
    assert.equal(s.invalidEntry(), null);
    assert.equal(s.form.isValid(), true);
    assert.notEqual(s.form.status, 'error');
});

test('a field that turns invalid while focused is marked invalid only on blur', () => {
    const s = createForm();
    const widget = s.buildWidget(dijitIsValid);
    widget.validate(true);
    assert.equal(s.form.getInvalidDojo().len(), 0);
    widget.validate(false);
    assert.ok(s.invalidEntry());
});

test('a focused number field whose unfocused check fails keeps the form invalid', () => {
    const s = createForm();
    const widget = s.buildWidget(numberIsValid);
    widget.validate(false);
    assert.ok(s.invalidEntry());
    widget.validate(true);
    assert.ok(s.invalidEntry());
    assert.equal(s.form.isValid(), false);
});

test('checking a gnr-validated field while focused keeps its editing state for the blur', () => {
    const s = createForm();
    const widget = s.buildWidget(dijitIsValid);
    s.context.gnr.GnrWdgHandler.prototype.setIsValidMethod(widget);
    widget.validate(true);
    assert.equal(s.field.editing, true);
});
