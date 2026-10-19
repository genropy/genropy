const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadGrid() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout,
                     dijit: {getEnclosingWidget: () => null}};
    context.dojo = {
        Deferred: function() {
            this.callbacks = [];
            this.callback = (value) => { this.result = value; this.callbacks.forEach((cb) => cb(value)); };
            this.errback = (error) => { this.error = error; };
            this.addCallback = (cb) => { this.callbacks.push(cb); return this; };
        },
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const gridJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js');
    vm.runInContext(readFileSync(gridJs, 'utf8'), context, {filename: 'grouplet_grid.js'});
    context._T = str => str;
    return context;
}

function createGrid(kw = {}) {
    const context = loadGrid();
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const lines = new Bag();
    data.setItem('record.lines', lines);
    data.setItem('record.common.producer', 'P01');
    data.setItem('ws', new Bag());
    data.setBackRef();
    let counter = 0;
    const published = [];
    Object.assign(context.genro, {
        _data: data,
        vld: new context.gnr.GnrValidator(context.genro),
        wdg: {getHandler: () => null},
        publish: (topic, payload) => published.push([topic, payload]),
        getData: p => data.getItem(p),
        setData: (p, v) => data.setItem(p, v),
        getDataNode: p => data.getNode(p),
        time36Id: () => 'k' + (++counter),
        evaluate: expr => vm.runInContext('(' + expr + ')', context)
    });
    const controller = Object.create(context.gnr.GroupletGridController.prototype);
    Object.assign(controller, {
        nodeId: 'grid',
        storepath: 'record.lines',
        phantomPath: 'ws.phantom',
        entryPath: 'ws.entry',
        defaultRow: {},
        tiles: {},
        formulas: {},
        _freshRows: {},
        minRows: 0,
        maxRows: null,
        layout: 'cards',
        selectionmenu: {},
        sourceNode: {
            getFormHandler: () => kw.form || null,
            getRelativeData: (p) => data.getItem(p.replace('#FORM.', 'record.')),
            attr: {}
        },
        dataStore: {
            addRow: (key, values) => lines.setItem(key, new Bag(values)),
            rowValue: key => lines.getItem(key),
            removeRow: key => lines.popNode(key),
            getData: () => lines,
            getNodes: () => lines.getNodes(),
            updateRow: (key, dict) => Object.keys(dict).forEach(k => lines.setItem(key + '.' + k, dict[k]))
        },
        _containerDom: () => ({classList: {toggle() {}, remove() {}, add() {}, contains: () => false},
                               querySelectorAll: () => [], contains: () => false})
    }, kw.controller || {});
    return {context, controller, data, lines, published, Bag};
}

const plain = bag => JSON.parse(JSON.stringify(bag.asDict()));
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test('defaultRow: a =path value is read when the row is added', () => {
    const s = createGrid({controller: {defaultRow: {ProducerCode: '=#FORM.common.producer', qty: 1}}});
    s.controller._doAddItem();
    assert.deepEqual(plain(s.lines.getItem('r_k1')), {ProducerCode: 'P01', qty: 1});
    s.data.setItem('record.common.producer', 'P02');
    s.controller._doAddItem(null, {qty: 3});
    assert.deepEqual(plain(s.lines.getItem('r_k2')), {ProducerCode: 'P02', qty: 3});
    assert.equal(s.controller.defaultRow.ProducerCode, '=#FORM.common.producer', 'the spec is kept');
});

test('defaultRow: a blank row compares with the defaults it was given', async () => {
    const s = createGrid({controller: {defaultRow: {ProducerCode: '=#FORM.common.producer'}, phantom: true,
                                       phantomTile: {domNode: () => null}}});
    s.controller._resetPhantom();
    assert.equal(s.data.getItem('ws.phantom.ProducerCode'), 'P01');
    s.data.setItem('record.common.producer', 'P02');
    assert.equal(s.controller._phantomHasValues(), false, 'a later default is no entry');
    s.data.setItem('ws.phantom.item', 'Milk');
    await tick();
    assert.equal(s.lines.getItem('r_k1.ProducerCode'), 'P01');
    assert.equal(s.data.getItem('ws.phantom.ProducerCode'), 'P02', 'the next blank row reads it again');
});

test('defaultRow: a blank entry row shows a default changed since it was cleared', () => {
    const s = createGrid({controller: {defaultRow: {ProducerCode: '=#FORM.common.producer'}, entry: true,
                                       entryTile: {domNode: () => null, tileContent: {walk: () => undefined}}}});
    s.controller._resetEntry();
    s.data.setItem('record.common.producer', 'P02');
    s.controller._refreshEntryDefaults();
    assert.equal(s.data.getItem('ws.entry.ProducerCode'), 'P02');
    s.data.setItem('ws.entry.item', 'Grip');
    s.data.setItem('record.common.producer', 'P03');
    s.controller._refreshEntryDefaults();
    assert.equal(s.data.getItem('ws.entry.ProducerCode'), 'P02', 'a row being typed in keeps it');
});
