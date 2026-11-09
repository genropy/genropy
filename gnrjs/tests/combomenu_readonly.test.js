const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// The dateTimeTextBox popup is a comboMenu attached to the textbox: the menu opens from
// its own mouse handler, so dijit's readOnly gate in _DateTimeTextBox._open never runs.
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
    const data = new context.gnr.GnrBag();
    data.setBackRef();
    context.genro._data = data;
    context.genro.getDataNode = (p, autocreate) => data.getNode(p, false, autocreate);
    context.genro.getData = p => data.getItem(p);
    const main = new context.gnr.GnrDomSource();
    context.genro.src = {_main: main, _index: {}, _started: true, formsToUpdate: {}};
    context.genro.wdg = {getHandler: () => null, filterEvent: () => true};
    context.genro.dom = {isDisabled: () => false, getEventModifiers: () => ''};
    return {context, main};
}

// a menu with modifiers:'*' attached to a field, as ComboMenu and MenuDiv build it
function createMenu(fieldWidget) {
    const {context, main} = createContext();
    main._(fieldWidget ? 'textbox' : 'div', 'field', {tag: fieldWidget ? 'textbox' : 'div', value: '^record.ts'});
    const fieldNode = main.getNode('field');
    fieldNode.widget = fieldWidget;
    main._('menu', 'menu', {tag: 'menu', modifiers: '*', attachTo: fieldNode});
    const menuNode = main.getNode('menu');
    const opened = [];
    const menu = {sourceNode: menuNode, modifiers: '*', getChildren: () => [],
                  _contextMouse_replaced: () => opened.push('contextMouse'),
                  _openMyself_replaced: () => opened.push('openMyself')};
    menuNode.widget = menu;
    const click = () => context.gnr.widgets.Menu.prototype.versionpatch_11__contextMouse.call(
        menu, {target: {sourceNode: fieldNode}, button: 0});
    return {menu, opened, click};
}

test('a comboMenu on a readOnly field does not open', () => {
    const s = createMenu({readOnly: true, disabled: false});
    s.click();
    assert.deepEqual(s.opened, []);
});

test('a comboMenu on a disabled field does not open', () => {
    const s = createMenu({readOnly: false, disabled: true});
    s.click();
    assert.deepEqual(s.opened, []);
});

test('a comboMenu on an editable field opens', () => {
    const s = createMenu({readOnly: false, disabled: false});
    s.click();
    assert.deepEqual(s.opened, ['contextMouse', 'openMyself']);
});

test('readOnly is read at click time', () => {
    const field = {readOnly: false, disabled: false};
    const s = createMenu(field);
    field.readOnly = true;
    s.click();
    assert.deepEqual(s.opened, []);
    field.readOnly = false;
    s.click();
    assert.deepEqual(s.opened, ['contextMouse', 'openMyself']);
});

test('a menu attached to a div with no widget still opens', () => {
    const s = createMenu(undefined);
    s.click();
    assert.deepEqual(s.opened, ['contextMouse', 'openMyself']);
});
