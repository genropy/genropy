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
    // genro_widgets.js extends dijit classes this harness does not load;
    // dbSelect gets BaseSelect as a second base, mixed in as dojo.declare does
    dojo.declare = function(name, base, members) {
        const mixins = Array.isArray(base) ? base.slice(1) : [];
        if (Array.isArray(base)) base = base[0];
        function Declared(...args) {
            if (base) base.apply(this, args);
            for (const mixin of mixins) mixin.apply(this, args);
            if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
        }
        Declared.prototype = Object.create(base && base.prototype ? base.prototype : Object.prototype);
        for (const mixin of mixins) {
            for (const key in mixin.prototype) {
                if (key !== 'constructor') Declared.prototype[key] = mixin.prototype[key];
            }
        }
        Object.assign(Declared.prototype, members);
        Declared.prototype.constructor = Declared;
        return dojo.setObject(name, Declared);
    };
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js', 'gnrstores.js', 'genro_wdg.js']) {
        run(sourceDir, filename);
    }
    context._T = str => str;
    return context;
}

const PRODUCTS = [{_pkey: 'P1', caption: 'Pencil'}, {_pkey: 'P2', caption: 'Pen'}, {_pkey: 'P3', caption: 'Eraser'}];

// a select outside any form; a value comes with its caption in the record,
// as a loaded relation does, so setting it needs no lookup. Only a
// callBackSelect answers lookups, through its own resolver: a dbSelect's
// would reach the server
function createSelect({tag = 'dbSelect', value = null, required = true, firstMatchDisabled = false} = {}) {
    const context = createContext();
    const {gnr, genro, dijit, dojo} = context;
    const messages = [];
    const data = new gnr.GnrBag();
    data.setItem('entry.product_id', value);
    if (value) {
        data.setItem('entry.@product_id', null, {caption: 'Pencil'});
    }
    data.setBackRef();
    Object.assign(genro, {_data: data, getData: p => data.getItem(p), getDataNode: p => data.getNode(p),
        publish: (topic, kw) => topic === 'floating_message' && messages.push(kw.message),
        debug() {}, warning() {}, setInStorage() {}, wdg: {getHandler: () => null},
        dom: {setClass() {}, addClass() {}, removeClass() {}}});
    genro.vld = new gnr.GnrValidator(genro);
    const main = new gnr.GnrDomSource();
    genro.src = {_main: main, _index: {}, _started: true, nodeBySourceNodeId: id => main.findNodeById(id)};
    main._('div', 'entry', {datapath: 'entry'})._(tag, 'product', {tag, value: '^.product_id',
        dbtable: 'shop.product', validate_notnull: required, firstMatchDisabled});
    main.setBackRef();
    const field = main.getNode('entry.product');
    field.getLabelWrapper = () => null;
    field._updateErrorTooltip = () => {};
    const handler = new gnr.widgets[{dbSelect: 'dbSelect', callBackSelect: 'CallBackSelect'}[tag]]();
    const store = new gnr.GnrStoreQuery({searchAttr: 'caption', _parentSourceNode: field});
    store._identifier = '_pkey';
    if (tag === 'callBackSelect') {
        const callback = kw => ({data: PRODUCTS.filter(r => r.caption.toLowerCase().startsWith(kw._querystring.toLowerCase()))});
        store.rootDataNode().setResolver(handler.resolver(field, {callback}, {}));
    }
    const widget = Object.assign(Object.create(dijit.form.FilteringSelect.prototype), {
        gnr: handler, sourceNode: field, textbox: {value: ''}, valueNode: {value: ''}, focusNode: {}, domNode: {className: ''},
        store, searchAttr: 'caption', ignoreCase: true, _onChangeActive: true, value});
    // what dijit postCreate does before genro mixes its patches in
    dijit.form._FormValueWidget.prototype.postCreate.call(widget);
    field.setValidations();
    gnr.GnrWdgHandler.prototype.setIsValidMethod(widget);
    gnr.GnrWdgHandler.prototype.doMixin(widget, handler, tag, field);
    handler.connectForUpdate(widget, field);
    field.widget = widget;
    handler.connectChangeEvent(widget);
    const changes = [];
    dojo.connect(widget, 'onChange', v => changes.push(v));
    const setFromData = v => {
        data.setItem('entry.product_id', v);
        field.doUpdateAttrBuiltObj('value', {evt: 'upd', node: data.getNode('entry.product_id')}, 'container');
    };
    // dijit's focus manager drops _focused before calling _onBlur
    const blur = () => {
        widget._focused = false;
        widget._setBlurValue();
    };
    const type = text => {
        widget.textbox.value = text;
        blur();
    };
    const clear = () => type('');
    return {widget, field, data, messages, changes, setFromData, blur, clear, type};
}

test('a dbSelect born empty, tabbed through, reports no change and stays valid', () => {
    const s = createSelect();
    s.blur();
    assert.deepEqual(s.changes, []);
    assert.deepEqual(s.messages, []);
    assert.equal(s.field.hasValidationError(), undefined);
    assert.equal(s.data.getItem('entry.product_id'), null);
});

test('emptied by a record load, tabbed through, it reports no change either', () => {
    const s = createSelect();
    s.setFromData(null);
    s.blur();
    assert.deepEqual(s.changes, []);
    assert.deepEqual(s.messages, []);
    assert.equal(s.field.hasValidationError(), undefined);
    assert.equal(s.data.getItem('entry.product_id'), null);
});

test('the user clearing a set value is one change, validated once as required', () => {
    const s = createSelect({value: 'P1'});
    assert.equal(s.widget.textbox.value, 'Pencil');
    s.clear();
    assert.deepEqual(s.changes, ['']);
    assert.equal(s.field._validations.error, 'notnull');
    assert.equal(s.messages.length, 1);
});

test('a clear on a select that is not required lands null in data', () => {
    const s = createSelect({value: 'P1', required: false});
    s.clear();
    assert.deepEqual(s.changes, ['']);
    assert.deepEqual(s.messages, []);
    assert.equal(s.data.getItem('entry.product_id'), null);
});

test('text typed and not picked that matches the current item is no change', () => {
    const s = createSelect({tag: 'callBackSelect', value: 'P1'});
    s.type('Penc');
    assert.deepEqual(s.changes, []);
    assert.deepEqual(s.messages, []);
    assert.equal(s.field.hasValidationError(), undefined);
    assert.equal(s.widget.textbox.value, 'Pencil');
    assert.equal(s.data.getItem('entry.product_id'), 'P1');
});

test('text typed and not picked that matches another item is one change to it', () => {
    const s = createSelect({tag: 'callBackSelect', value: 'P1'});
    s.type('Era');
    assert.deepEqual(s.changes, ['P3']);
    assert.deepEqual(s.messages, []);
    assert.equal(s.data.getItem('entry.product_id'), 'P3');
});

test('text typed and not picked that matches nothing is one change, validated once', () => {
    const s = createSelect({tag: 'callBackSelect', value: 'P1'});
    s.type('xyz');
    assert.deepEqual(s.changes, [undefined]);
    assert.equal(s.messages.length, 1);
    assert.equal(s.field.hasValidationError(), true);
});

test('with firstMatchDisabled, text typed and not picked clears the value in one change', () => {
    const s = createSelect({tag: 'callBackSelect', value: 'P1', firstMatchDisabled: true});
    s.type('Penc');
    assert.deepEqual(s.changes, ['']);
    assert.equal(s.messages.length, 1);
});
