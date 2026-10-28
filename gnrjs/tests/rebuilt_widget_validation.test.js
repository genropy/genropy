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
    context.dijit = {form: {ValidationTextBox: function() {}, CheckBox: function() {}}};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    data.setItem('outer.record', new Bag({flag: null}), {_pkey: 'LOM'});
    data.setItem('outer.controller', new Bag());
    data.setBackRef();
    context.genro._data = data;
    context.genro.getDataNode = p => data.getNode(p);
    context.genro.getData = p => data.getItem(p);
    const main = new context.gnr.GnrDomSource();
    context.genro.src = {_main: main, _index: {}, _started: true, formsToUpdate: {}, nodeBySourceNodeId: id => main.findNodeById(id)};
    context.genro.vld = new context.gnr.GnrValidator(context.genro);
    context.genro.wdg = {
        getHandler: () => null,
        // what genro_wdg does for a dojo widget with validate_*: the widget and the validate mixin
        create(tag, destination, attributes, ind, sourceNode) {
            const widget = Object.assign(Object.create(context.dijit.form.CheckBox.prototype),
                                         {gnr: {connectChangeEvent() {}}});
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
        autoRegisterTags: {checkbox: true},
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
    main._('checkbox', 'flag', {tag: 'checkbox', value: '^.flag', validate_notnull: true});
    const field = main.getNode('flag');
    field.form = form;
    field.updateValidationClasses = () => {};
    field.getElementLabel = () => 'Flag';
    field.absDatapath = () => 'outer.record.flag';
    field.isLostNode = () => false;
    form.registerChild(field);
    return {form, field};
}

test('a checkbox rebuilt over an empty required value makes the form invalid', () => {
    const s = createForm();
    assert.equal(s.form.isValid(), true);
    s.field._doBuildNode('checkbox', {value: null}, null);
    assert.equal(s.form.isValid(), false);
    assert.deepEqual(Object.keys(s.form.getInvalidFields().getItem('#0')), [s.field.getStringId()]);
});
