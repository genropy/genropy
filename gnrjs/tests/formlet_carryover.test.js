const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// carryover on a formlet field: the labledBox around the field compares the
// field's value with the value it was filled with (a path, or with
// carryover=true the value the record was loaded with), marks the state worth
// marking with its carryover_class and offers a restore button.

function createContext() {
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    genro.startArgs = {};
    genro.wdg = {getHandler: () => null};
    let counter = 0;
    genro.time36Id = () => `id${counter++}`;
    genro.mainGenroWindow = {genro};
    genro._pageLocals = {};
    genro.locale = () => 'en-US';
    genro.getFromStorage = () => null;
    genro.setInStorage = () => {};
    genro.serverCall = (method, kw) => ({translation: kw.txt.replace(/^!!/, '')});
    genro.dev = {isConnectionLost: () => false};
    genro.dom = {setClass: (element, name, on) => (on ? element.classes.add(name) : element.classes.delete(name))};
    return context;
}

const context = createContext();
const own = vm.runInContext('(attr) => Object.assign({}, attr)', context);
const date = vm.runInContext('(y, m, d) => new Date(y, m, d)', context);
const handler = context.gnr.widgets.labledbox.prototype;

function serverFormlet(gridAttr, fields) {
    const root = new context.gnr.GnrDomSource();
    root.setBackRef();
    const grid = root._('gridbox', 'fb', own({_class: 'gnrgridbox formlet', columns: 2, ...gridAttr}));
    for (const [tag, attr] of fields) grid._(tag, own(attr));
    const nodes = root.getNode('fb').getValue('static').getNodes();
    for (const node of nodes) node.buildLblWrapper();
    return [...nodes];
}

function element(tag) {
    const el = {tag, value: '', classes: new Set(), attributes: {}};
    el.setAttribute = (name, value) => { el.attributes[name] = value; };
    el.removeAttribute = (name) => { delete el.attributes[name]; };
    el.closest = (selector) => (selector === '.dijitComboBox' && el.combo ? {} : null);
    return el;
}

// a labledBox wrapper and its field, as the widget sees them once built
function wrapper({carryover, loaded = false, value, tag = 'textbox', attr = {}, field = {}, form = null, combo = false}) {
    const input = element('input');
    input.combo = combo;
    const content = element('div');
    content.querySelector = () => input;
    const fieldAttr = {tag, value: '^.city', ...field};
    const fieldNode = {
        attr: fieldAttr, form, data: value,
        getAttributeFromDatasource: (name) => (name === 'value' ? fieldNode.data : fieldAttr[name]),
        attrDatapath: () => 'record.city'
    };
    const restore = element('div');
    const sourceNode = {
        attr: {carryover_field: '^.city', carryover: loaded ? true : '^.carried.city', ...attr},
        domNode: element('div'),
        _carryoverContent: {getNodes: () => [fieldNode], getParentNode: () => ({domNode: content})},
        _carryoverRestore: {domNode: restore},
        isLostNode: () => false,
        attributeOwnerNode: () => null,
        getAttributeFromDatasource: (name) => (name === 'carryover' ? carryover : sourceNode.attr[name])
    };
    return {sourceNode, fieldNode, input, restore};
}

function status(kw) {
    return handler.carryoverStatus(wrapper(kw).sourceNode);
}

test('the carryover attributes move to the wrapper, which watches the field value', () => {
    const [city, name] = serverFormlet({}, [
        ['textbox', {lbl: 'City', value: '^.city', carryover: '^.carried.city', carryover_caption: 'From the person'}],
        ['textbox', {lbl: 'Name', value: '^.name'}]
    ]);
    assert.equal(city.attr.tag, 'labledbox');
    assert.equal(city.attr.carryover, '^.carried.city');
    assert.equal(city.attr.carryover_caption, 'From the person');
    assert.equal(city.attr.carryover_field, '^.city');
    assert.equal(city._contentNode.attr.carryover, undefined);
    assert.equal(name.attr.carryover_field, undefined);
});

test('item_carryover reaches every field, carryover=False opts one out', () => {
    // formlet() promotes a static item_carryover to the gridbox
    const [city, name] = serverFormlet({carryover: true}, [
        ['textbox', {lbl: 'City', value: '^.city'}],
        ['textbox', {lbl: 'Name', value: '^.name', carryover: false}]
    ]);
    assert.equal(city.attr.carryover_field, '^.city');
    assert.equal(name.attr.carryover, false);
    assert.equal(name.attr.carryover_field, undefined);
});

test('a field with a datapath of its own does not resolve its value like the wrapper', () => {
    const [city] = serverFormlet({}, [['textbox', {lbl: 'City', value: '^.city', datapath: '.other',
                                                  carryover: '^.carried.city'}]]);
    assert.equal(city.attr.carryover_field, undefined);
});

test('carried, overridden, cleared and nothing to carry', () => {
    assert.equal(status({carryover: 'Bologna', value: 'Bologna'}).state, 'carried');
    const changed = status({carryover: 'Bologna', value: 'Modena'});
    assert.equal(changed.state, 'overridden');
    assert.equal(changed.prior, 'Bologna');
    assert.equal(changed.cleared, false);
    assert.equal(status({carryover: 'Bologna', value: null}).cleared, true);
    assert.equal(status({carryover: '', value: 'Modena'}).state, null);
    assert.equal(status({carryover: null, value: null}).state, null);
});

test('values compare by type: numbers with their text, dates by day', () => {
    assert.equal(status({carryover: 1, value: '1'}).state, 'carried');
    assert.equal(status({carryover: date(2026, 2, 12), value: date(2026, 2, 12)}).state, 'carried');
    assert.equal(status({carryover: date(2026, 2, 12), value: date(2026, 2, 13)}).state, 'overridden');
});

test('a checkbox takes empty and false as the same value, and is never cleared', () => {
    assert.equal(status({carryover: false, value: null, tag: 'checkbox'}).state, 'carried');
    const unticked = status({carryover: true, value: null, tag: 'checkbox'});
    assert.equal(unticked.state, 'overridden');
    assert.equal(unticked.cleared, false);
});

test('carryover=true compares with the value the record was loaded with', () => {
    const genro = context.genro;
    genro.getDataNode = () => ({attr: {_loadedValue: 'Merola'}});
    const changed = status({loaded: true, value: 'Merolla'});
    assert.equal(changed.state, 'overridden');
    assert.equal(changed.prior, 'Merola');
    genro.getDataNode = () => ({attr: {}});
    const same = status({loaded: true, value: 'Merola'});
    assert.equal(same.state, 'same');
    assert.equal(same.prior, 'Merola');
    assert.equal(status({loaded: true, value: 'x', form: {isNewRecord: () => true}}).state, null);
});

test('the class of the state worth marking', () => {
    const cls = (loaded, carryoverClass) => handler.carryoverClass(
        wrapper({carryover: 'Bologna', loaded, value: null,
                 attr: carryoverClass === undefined ? {} : {carryover_class: carryoverClass}}).sourceNode);
    assert.equal(cls(false), 'carryover_inherited');
    assert.equal(cls(true), null);
    assert.equal(cls(true, 'carryover_changed'), 'carryover_changed');
    assert.equal(cls(false, false), null);
    assert.equal(cls(false, 'my_carried'), 'my_carried');
});

test('a carried value is marked, a changed one shows the restore tooltip', () => {
    const carried = wrapper({carryover: 'N', value: 'N', attr: {carryover_caption: 'From the person'},
                             field: {values: 'N:no,S:yes'}});
    handler.updateCarryover(carried.sourceNode);
    assert.deepEqual([...carried.sourceNode.domNode.classes].sort(), ['carryover_inherited', 'labledBox_carried']);
    assert.equal(carried.input.attributes['aria-description'], 'From the person');
    const changed = wrapper({carryover: 'N', value: 'S', field: {values: 'N:no,S:yes'}});
    handler.updateCarryover(changed.sourceNode);
    assert.deepEqual([...changed.sourceNode.domNode.classes], ['labledBox_overridden']);
    assert.equal(changed.restore.attributes.title, 'Changed · before: no · restore');
});

test('with carryover=true the class marks the changed field', () => {
    context.genro.getDataNode = () => ({attr: {_loadedValue: 'Merola'}});
    const changed = wrapper({loaded: true, value: 'Merolla', attr: {carryover_class: 'carryover_changed'}});
    handler.updateCarryover(changed.sourceNode);
    assert.deepEqual([...changed.sourceNode.domNode.classes].sort(), ['carryover_changed', 'labledBox_overridden']);
});

test('typing in a carried field shows the restore button at once, not in a select', () => {
    const field = wrapper({carryover: 'Bologna', value: 'Bologna'});
    field.input.value = 'Bologna';
    handler.updateCarryover(field.sourceNode);
    field.input.value = 'Bolog';
    handler.carryoverTyping(field.sourceNode, {target: field.input});
    assert.ok(field.sourceNode.domNode.classes.has('labledBox_overridden'));
    assert.ok(!field.sourceNode.domNode.classes.has('carryover_inherited'));
    field.input.value = 'Bologna';
    handler.carryoverTyping(field.sourceNode, {target: field.input});
    assert.ok(field.sourceNode.domNode.classes.has('labledBox_carried'));

    const select = wrapper({carryover: 'N', value: 'N', combo: true});
    select.input.value = 'no';
    handler.updateCarryover(select.sourceNode);
    select.input.value = 'y';
    handler.carryoverTyping(select.sourceNode, {target: select.input});
    assert.ok(select.sourceNode.domNode.classes.has('labledBox_carried'));
});

test('restore sets the carried value back, or the text typed but not yet set', () => {
    const sets = [];
    context.genro.setData = (dataPath, value) => sets.push([dataPath, value]);
    const changed = wrapper({carryover: 'Bologna', value: 'Modena'});
    handler.updateCarryover(changed.sourceNode);
    handler.restoreCarryover(changed.sourceNode);
    assert.deepEqual(sets, [['record.city', 'Bologna']]);

    const typed = wrapper({carryover: 'Bologna', value: 'Bologna'});
    typed.input.value = 'Bologna';
    handler.updateCarryover(typed.sourceNode);
    typed.input.value = 'Bolo';
    handler.restoreCarryover(typed.sourceNode);
    assert.equal(typed.input.value, 'Bologna');
    assert.equal(sets.length, 1);

    const locked = wrapper({carryover: 'Bologna', value: 'Modena', form: {isDisabled: () => true}});
    handler.updateCarryover(locked.sourceNode);
    handler.restoreCarryover(locked.sourceNode);
    assert.equal(sets.length, 1);
});
