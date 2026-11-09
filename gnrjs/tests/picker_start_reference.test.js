const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

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
    context.genro.wdg = {getHandler: () => null};
    // dates must come from the page realm, as the widget checks them with instanceof Date
    const VmDate = vm.runInContext('Date', context);
    return {context, data, main, date: (...args) => new VmDate(...args)};
}

// what dijit _DateTimeTextBox._open does: build the picker once, on the value or today
function dijitOpen() {
    if (!this._picker) {
        const picker = {value: null, setValue(v) { this.value = v; }};
        this._picker = picker;
        picker.setValue(this.getValue() || new Date());
    }
}

function createField(tag, attr, fieldValue) {
    const s = createContext();
    s.NOVEMBER = s.date(2026, 10, 20);
    s.DECEMBER = s.date(2026, 11, 3);
    s.main._(tag, 'field', Object.assign({tag}, attr));
    const sourceNode = s.main.getNode('field');
    const handler = new s.context.gnr.widgets[tag]();
    const widget = {gnr: handler, sourceNode, _open_replaced: dijitOpen,
                    getValue: () => fieldValue(s), _open: handler.patch__open};
    return Object.assign(s, {widget, handler});
}

test('an empty date field opens on its start_date', () => {
    const s = createField('DateTextBox', {value: '^date_to', start_date: '=date_from'}, () => null);
    s.data.setItem('date_from', s.NOVEMBER);
    s.widget._open();
    assert.equal(s.widget._picker.value, s.NOVEMBER);
});

test('a start_date changed after the first opening is picked up by the next one', () => {
    const s = createField('DateTextBox', {value: '^date_to', start_date: '=date_from'}, () => null);
    s.data.setItem('date_from', s.NOVEMBER);
    s.widget._open();
    s.data.setItem('date_from', s.DECEMBER);
    s.widget._open();
    assert.equal(s.widget._picker.value, s.DECEMBER);
});

test('a date field with a value opens on its value, not on start_date', () => {
    const s = createField('DateTextBox', {value: '^date_to', start_date: '=date_from'}, s => s.DECEMBER);
    s.data.setItem('date_from', s.NOVEMBER);
    s.widget._open();
    assert.equal(s.widget._picker.value, s.DECEMBER);
});

test('without a start_date value the date field still opens on today', () => {
    const s = createField('DateTextBox', {value: '^date_to', start_date: '=date_from'}, () => null);
    s.widget._open();
    assert.equal(s.widget._picker.value.toDateString(), new Date().toDateString());
});

test('an empty time field opens on its start_time', () => {
    const s = createField('TimeTextBox', {value: '^time_to', start_time: '=time_from'}, () => null);
    const nine = s.date(1970, 0, 1, 9, 30);
    s.data.setItem('time_from', nine);
    s.widget._open();
    assert.equal(s.widget._picker.value, nine);
});

test('a time field ignores start_date', () => {
    const s = createField('TimeTextBox', {value: '^time_to', start_date: '=date_from'}, () => null);
    s.data.setItem('date_from', s.NOVEMBER);
    s.widget._open();
    assert.notEqual(s.widget._picker.value, s.NOVEMBER);
});

test('the reference attribute is not handed to the dijit widget', () => {
    const {context, date} = createContext();
    const dateAttributes = {start_date: date(2026, 10, 20)};
    new context.gnr.widgets.DateTextBox().creating(dateAttributes, {attr: {}});
    assert.equal('start_date' in dateAttributes, false);
    const timeAttributes = {start_time: date(1970, 0, 1, 9, 30), constraints: {}};
    new context.gnr.widgets.TimeTextBox().creating(timeAttributes, {attr: {}});
    assert.equal('start_time' in timeAttributes, false);
});
