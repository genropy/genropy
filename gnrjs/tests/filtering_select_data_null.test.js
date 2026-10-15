const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '../..');
const dojoDir = path.join(root, 'dojo_libs/dojo_11/dojo');
const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');

// the real dojo declare and dijit form widgets: the echo lives in dijit's
// _callbackSetLabel and _handleOnChange, so they must not be faked
function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout};
    vm.createContext(context);
    const run = (dir, filename) => vm.runInContext(readFileSync(path.join(dir, filename), 'utf8'), context, {filename});
    run(path.join(dojoDir, 'dojo/_base/_loader'), 'bootstrap.js');
    const dojo = context.dojo;
    Object.assign(dojo, {_hasResource: {}, provide: name => dojo.getObject(name, true), require() {},
                         requireLocalization() {}, deprecated() {}, isIE: 0, Deferred: function() {}});
    for (const filename of ['lang.js', 'array.js', 'declare.js', 'connect.js']) run(path.join(dojoDir, 'dojo/_base'), filename);
    run(path.join(dojoDir, 'dojo/data/util'), 'filter.js');
    Object.assign(context.dijit, {form: {}, setWaiState() {}, removeWaiState() {}});
    dojo.declare('dijit._Widget', null, {attributeMap: {}});
    dojo.declare('dijit._Templated', null, {});
    for (const filename of ['_FormWidget.js', 'TextBox.js', 'ValidationTextBox.js', 'ComboBox.js', 'FilteringSelect.js']) {
        run(path.join(dojoDir, 'dijit/form'), filename);
    }
    // genro_widgets.js extends dijit classes this harness does not load
    dojo.declare = function(name, base, members) {
        if (Array.isArray(base)) base = base[0];
        function Declared(...args) {
            if (base) base.apply(this, args);
            if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
        }
        Declared.prototype = Object.assign(Object.create(base && base.prototype ? base.prototype : Object.prototype), members);
        Declared.prototype.constructor = Declared;
        return dojo.setObject(name, Declared);
    };
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js', 'gnrstores.js', 'genro_wdg.js']) {
        run(sourceDir, filename);
    }
    context._T = str => str;
    return context;
}

// a values= filteringSelect with validate_notnull outside any form, as a
// groupletGrid entry row cell (parentForm:false) is
function createSelect({focused = false} = {}) {
    const context = createContext();
    const {gnr, genro, dijit, dojo} = context;
    const messages = [];
    const data = new gnr.GnrBag();
    data.setItem('entry.vat', '22');
    data.setBackRef();
    Object.assign(genro, {_data: data, getData: p => data.getItem(p), getDataNode: p => data.getNode(p),
        publish: (topic, kw) => topic === 'floating_message' && messages.push(kw.message),
        debug() {}, warning() {}, setInStorage() {}, wdg: {getHandler: () => null},
        dom: {setClass() {}, addClass() {}, removeClass() {}}});
    genro.vld = new gnr.GnrValidator(genro);
    const main = new gnr.GnrDomSource();
    genro.src = {_main: main, _index: {}, _started: true, nodeBySourceNodeId: id => main.findNodeById(id)};
    main._('div', 'entry', {datapath: 'entry'})._('filteringSelect', 'vat', {tag: 'filteringSelect', value: '^.vat', validate_notnull: true});
    main.setBackRef();
    const field = main.getNode('entry.vat');
    field.getLabelWrapper = () => null;
    field._updateErrorTooltip = () => {};
    field.setValidations();
    const handler = new gnr.widgets.FilteringSelect();
    const widget = Object.assign(Object.create(dijit.form.FilteringSelect.prototype), {
        gnr: handler, sourceNode: field, textbox: {value: ''}, valueNode: {value: ''}, focusNode: {}, domNode: {className: ''},
        store: handler.storeFromValues('22:22%,10:10%'), searchAttr: 'caption', ignoreCase: true, _onChangeActive: true, value: '22'});
    // what dijit postCreate does before genro mixes its patches in
    dijit.form._FormValueWidget.prototype.postCreate.call(widget);
    gnr.GnrWdgHandler.prototype.doMixin(widget, handler, 'filteringSelect', field);
    field.widget = widget;
    handler.connectChangeEvent(widget);
    const changes = [];
    dojo.connect(widget, 'onChange', value => changes.push(value));
    widget._focused = focused;
    const setFromData = value => {
        data.setItem('entry.vat', value);
        field.doUpdateAttrBuiltObj('value', {evt: 'upd', node: data.getNode('entry.vat')}, 'container');
    };
    const blur = () => {
        widget._focused = false;
        widget._setBlurValue();
    };
    const pick = id => {
        widget._focused = true;
        widget._doSelect({item: widget.store.rootData().getNodes().find(n => n.attr.id === id)});
    };
    return {widget, field, data, messages, changes, setFromData, blur, pick};
}

test('a filteringSelect emptied from data reports no change and stays valid', () => {
    const s = createSelect();
    s.setFromData(null);
    assert.equal(s.widget.textbox.value, '');
    assert.deepEqual(s.changes, []);
    assert.deepEqual(s.messages, []);
    assert.equal(s.field.hasValidationError(), undefined);
    assert.equal(s.data.getItem('entry.vat'), null);
});

test('emptied from data while focused, it reports nothing on blur either', () => {
    const s = createSelect({focused: true});
    s.setFromData(null);
    s.blur();
    assert.deepEqual(s.changes, []);
    assert.deepEqual(s.messages, []);
    assert.equal(s.field.hasValidationError(), undefined);
});

test('the user clearing a set value is still a change, validated as required', () => {
    const s = createSelect({focused: true});
    s.widget.textbox.value = '';
    s.blur();
    assert.deepEqual(s.changes, [undefined]);
    assert.equal(s.field._validations.error, 'notnull');
    assert.equal(s.messages.length, 1);
});

test('after a clear from data, a value the user picks then clears is validated', () => {
    const s = createSelect();
    s.setFromData(null);
    s.pick('10');
    assert.equal(s.data.getItem('entry.vat'), '10');
    s.widget.textbox.value = '';
    s.blur();
    assert.deepEqual(s.changes, ['10', undefined]);
    assert.equal(s.field._validations.error, 'notnull');
    assert.equal(s.messages.length, 1);
});
