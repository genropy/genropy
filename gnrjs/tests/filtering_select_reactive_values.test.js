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

// a filteringSelect whose values= is reactive, built while its value is not
// yet among them
function createSelect({values, value}) {
    const context = createContext();
    const {gnr, genro, dijit, dojo} = context;
    const messages = [];
    const data = new gnr.GnrBag();
    data.setItem('entry.state', value);
    data.setBackRef();
    Object.assign(genro, {_data: data, getData: p => data.getItem(p), getDataNode: p => data.getNode(p),
        publish: (topic, kw) => topic === 'floating_message' && messages.push(kw.message),
        debug() {}, warning() {}, setInStorage() {}, wdg: {getHandler: () => null},
        dom: {setClass() {}, addClass() {}, removeClass() {}}});
    genro.vld = new gnr.GnrValidator(genro);
    const main = new gnr.GnrDomSource();
    genro.src = {_main: main, _index: {}, _started: true, nodeBySourceNodeId: id => main.findNodeById(id)};
    main._('div', 'entry', {datapath: 'entry'})._('filteringSelect', 'state', {tag: 'filteringSelect', value: '^.state', validate_notnull: true});
    main.setBackRef();
    const field = main.getNode('entry.state');
    field.getLabelWrapper = () => null;
    field._updateErrorTooltip = () => {};
    field.setValidations();
    const handler = new gnr.widgets.FilteringSelect();
    const widget = Object.assign(Object.create(dijit.form.FilteringSelect.prototype), {
        gnr: handler, sourceNode: field, textbox: {value: ''}, valueNode: {value: ''}, focusNode: {}, domNode: {className: ''},
        store: handler.storeFromValues(values), searchAttr: 'caption', ignoreCase: true, _onChangeActive: true, value: ''});
    // what dijit postCreate does before genro mixes its patches in
    dijit.form._FormValueWidget.prototype.postCreate.call(widget);
    gnr.GnrWdgHandler.prototype.doMixin(widget, handler, 'filteringSelect', field);
    field.widget = widget;
    handler.connectChangeEvent(widget);
    field.doUpdateAttrBuiltObj('value', {}, 'node');
    const changes = [];
    dojo.connect(widget, 'onChange', value => changes.push(value));
    const updates = [];
    const doUpdate = field.doUpdateAttrBuiltObj;
    field.doUpdateAttrBuiltObj = function(attr, ...rest) {
        updates.push(attr);
        return doUpdate.call(this, attr, ...rest);
    };
    return {widget, field, data, messages, changes, updates};
}

test('a value that arrived before its values is shown once the values include it', () => {
    const s = createSelect({values: 'NSW', value: 'VIC'});
    assert.equal(s.widget.textbox.value, '');
    const messages = s.messages.length;
    s.widget.setValues('VIC,NSW');
    assert.equal(s.widget.textbox.value, 'VIC');
    assert.equal(s.field.hasValidationError(), undefined);
    assert.deepEqual(s.changes, []);
    assert.equal(s.messages.length, messages);
    assert.equal(s.data.getItem('entry.state'), 'VIC');
});

test('a value still missing from the new values is left as it was', () => {
    const s = createSelect({values: 'NSW', value: 'VIC'});
    const error = s.field.hasValidationError();
    const messages = s.messages.length;
    s.widget.setValues('NSW,TAS');
    assert.equal(s.widget.textbox.value, '');
    assert.deepEqual(s.updates, []);
    assert.deepEqual(s.changes, []);
    assert.equal(s.field.hasValidationError(), error);
    assert.equal(s.messages.length, messages);
    assert.equal(s.data.getItem('entry.state'), 'VIC');
});

test('a blank value is not set again when the values change', () => {
    const s = createSelect({values: 'NSW', value: null});
    s.widget.setValues('VIC,NSW');
    assert.equal(s.widget.textbox.value, '');
    assert.deepEqual(s.updates, []);
    assert.deepEqual(s.changes, []);
    assert.equal(s.data.getItem('entry.state'), null);
});
