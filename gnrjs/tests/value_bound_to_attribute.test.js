const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// The dateTimeTextBox popup binds a timeTextBox to 'value?_time' and a dateTextBox to
// 'value?_date'. Their dtype must stay on the attribute they write: on the node of a DH
// field a dtype 'H' makes the save send the timestamp as a time.
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
    context.genro.setInStorage = () => {};
    const main = new context.gnr.GnrDomSource();
    context.genro.src = {_main: main, _index: {}, _started: true, formsToUpdate: {}};
    context.genro.wdg = {getHandler: () => null};
    const VmDate = vm.runInContext('Date', context);
    return {context, data, main, date: (...args) => new VmDate(...args)};
}

function writeFromWidget(tag, valuePath, value, valueAttr) {
    const s = createContext();
    s.main._(tag, 'field', {tag, value: valuePath});
    const sourceNode = s.main.getNode('field');
    sourceNode.publish = () => {};
    const handler = new s.context.gnr.widgets[tag]();
    handler.setValueInData(sourceNode, value(s), valueAttr);
    return s;
}

test('a time written on the attribute of a DH field leaves the field dtype alone', () => {
    const s = writeFromWidget('TimeTextBox', '^record.ets?_time', s => s.date(1970, 0, 1, 22, 45), {dtype: 'H'});
    const node = s.data.getNode('record.ets');
    assert.equal(node.attr._time.getHours(), 22);
    assert.equal('dtype' in node.attr, false);
});

test('a date written on the attribute of a DH field leaves the field dtype alone', () => {
    const s = createContext();
    s.data.setItem('record.ets', s.date(2026, 10, 5, 12, 0), {dtype: 'DH'});
    s.main._('DateTextBox', 'field', {tag: 'DateTextBox', value: '^record.ets?_date'});
    const sourceNode = s.main.getNode('field');
    sourceNode.publish = () => {};
    new s.context.gnr.widgets.DateTextBox().setValueInData(sourceNode, s.date(2026, 10, 6), {dtype: 'D'});
    const node = s.data.getNode('record.ets');
    assert.equal(node.attr.dtype, 'DH');
    assert.equal(node.attr._date.getDate(), 6);
});

test('a widget bound to a value still writes its attributes on the node', () => {
    const s = writeFromWidget('TimeTextBox', '^record.start', s => s.date(1970, 0, 1, 9, 30), {dtype: 'H'});
    assert.equal(s.data.getNode('record.start').attr.dtype, 'H');
});
