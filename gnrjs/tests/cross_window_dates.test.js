const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// Each vm context stands for a window with its own Date: the root page and one of its
// iframe pages, which the root feeds through childDataChanges (genro_rpc.js resultHandler).
// The date formatter reads the date through its getters, as dojo.date.locale.format does.
function formatDate(date, options) {
    const pad = number => String(number).padStart(2, '0');
    const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
    const time = `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    if (options.selector === 'date') return day;
    if (options.selector === 'time') return time;
    return `${day} ${time}`;
}

function createWindow() {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        toJson: JSON.stringify,
        date: {locale: {format: formatDate}},
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_rpc.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context.genro._data = new context.gnr.GnrBag();
    context.genro.rpc = new context.gnr.GnrRpcHandler({page_id: 'p1'});
    return context;
}

const isRealDate = value => Object.prototype.toString.call(value) === '[object Date]';
const TYPED_DATES = ['2026-10-30::D', '2026-10-30 13:00:00.123::DH', '2026-10-30T12:00:00.123Z::DHZ',
                     '13:45:10::H'];

test('a db change relayed to an iframe page keeps its timestamp a Date and serialises it', () => {
    const root = createWindow();
    const child = createWindow();
    const changes = new root.gnr.GnrBag();
    changes.setItem('c_0', 'dbevents', {change_path: 'gnr.dbchanges.pkg_table', change_reason: 'dbevent',
                                        change_ts: root.convertFromText('2026-10-30 13:00:00.123::DH'),
                                        change_attr: {from_page_id: 'p2', dbevent_reason: 'visit'}});
    child.genro.rpc.setDatachangesInData(changes);
    const attr = child.genro._data.getNode('gnr.dbchanges.pkg_table').attr;
    assert.ok(isRealDate(attr._change_ts));
    assert.equal(attr._change_ts.getTime(), new Date('2026-10-30 13:00:00.123').getTime());
    const sent = child.genro.rpc.serializeParameters({changeattr: attr}).changeattr;
    const local = {from_page_id: 'p2', dbevent_reason: 'visit',
                   _change_ts: child.convertFromText('2026-10-30 13:00:00.123::DH')};
    assert.equal(sent, child.genro.rpc.serializeParameters({changeattr: local}).changeattr);
    assert.match(sent, /"_change_ts":"2026-10-30 13:00:00::DH"/);
});

test('mapConvertFromText keeps a Date from another window as that Date', () => {
    const root = createWindow();
    const child = createWindow();
    for (const text of TYPED_DATES) {
        const foreign = root.convertFromText(text);
        assert.equal(child.mapConvertFromText({value: foreign}).value, foreign, text);
    }
});

test('a typed Date from another window is a date and serialises like a local one', () => {
    const root = createWindow();
    const child = createWindow();
    for (const text of TYPED_DATES) {
        const foreign = root.convertFromText(text);
        const local = child.convertFromText(text);
        assert.equal(child.isDate(foreign), true, text);
        assert.equal(child.guessDtype(foreign), child.guessDtype(local), text);
        assert.equal(child.asTypedTxt(foreign), child.asTypedTxt(local), text);
        assert.equal(child.toTypedJSON({value: foreign}), child.toTypedJSON({value: local}), text);
    }
});

test('an untyped Date from another window is a date and serialises like a local one', () => {
    const root = createWindow();
    const child = createWindow();
    for (const [source, dtype] of [['new Date(2026, 9, 30)', 'D'], ['new Date(2026, 9, 30, 13, 5, 7)', 'DH']]) {
        const foreign = vm.runInContext(source, root);
        const local = vm.runInContext(source, child);
        assert.equal(child.isDate(foreign), true, source);
        assert.equal(child.guessDtype(foreign), dtype, source);
        assert.equal(child.asTypedTxt(foreign), child.asTypedTxt(local), source);
        assert.equal(child.toTypedJSON({value: foreign}), child.toTypedJSON({value: local}), source);
    }
});

test('a local Date converts and serialises as before', () => {
    const child = createWindow();
    const expected = {'2026-10-30::D': '2026-10-30::D',
                      '2026-10-30 13:00:00.123::DH': '2026-10-30 13:00:00::DH',
                      '2026-10-30T12:00:00.123Z::DHZ': '2026-10-30T12:00:00.123Z::DHZ',
                      '13:45:10::H': '13:45:10::H'};
    for (const [text, typed] of Object.entries(expected)) {
        const local = child.convertFromText(text);
        assert.equal(child.mapConvertFromText({value: local}).value, local, text);
        assert.equal(child.isDate(local), true, text);
        assert.equal(child.asTypedTxt(local), typed, text);
    }
    assert.equal(child.guessDtype(vm.runInContext('new Date(2026, 9, 30)', child)), 'D');
    assert.equal(child.guessDtype(vm.runInContext('new Date(2026, 9, 30, 13, 5, 7)', child)), 'DH');
});

test('values that are not dates convert as before, from this window or another', () => {
    const root = createWindow();
    const child = createWindow();
    const source = "({n: '12::L', s: 'abc', b: 'true::B', nested: {x: '1.5::N'}, empty: ''})";
    for (const realm of [root, child]) {
        const value = vm.runInContext(source, realm);
        const converted = child.mapConvertFromText(value);
        assert.notEqual(converted, value);
        assert.equal(JSON.stringify(converted), '{"n":12,"s":"abc","b":true,"nested":{"x":1.5},"empty":""}');
    }
    assert.equal(JSON.stringify(child.mapConvertFromText(vm.runInContext("['2::L', 'x']", child))), '[2,"x"]');
    for (const value of [{}, [], 'x', 12, true, {getTime: () => 0}]) {
        assert.equal(child.isDate(value), false, JSON.stringify(value));
    }
    assert.equal(child.guessDtype({a: 1}), 'OBJ');
    assert.equal(child.asTypedTxt({a: 1}), '{"a":1}::JS');
});

test('an object carrying a date dtype is handled as before', () => {
    const child = createWindow();
    for (const dtype of ['D', 'DH', 'DHZ']) {
        const typed = vm.runInContext(`({_gnrdtype: '${dtype}'})`, child);
        assert.equal(child.isDate(typed), true, dtype);
        assert.equal(child.guessDtype(typed), dtype);
        const converted = child.mapConvertFromText(typed);
        assert.notEqual(converted, typed, dtype);
        assert.equal(JSON.stringify(converted), `{"_gnrdtype":"${dtype}"}`);
    }
});
