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
        safeHtmlContent: (v) => v,
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

function chapters(s, rows) {
    rows.forEach(([key, code, name, amounts]) => {
        const accounts = new s.Bag();
        amounts.forEach((amount, i) => accounts.setItem('a' + i, new s.Bag({code: String(i), amount})));
        s.lines.setItem(key, new s.Bag({code, name, accounts}));
    });
}

test('naturalCompare orders codes as read, blanks last', () => {
    const {context} = createGrid();
    const cmp = context.gnr.GroupletGridController.naturalCompare;
    const sorted = ['10', '2', null, '1.10', '1.2', 'B', 'a', ''].sort(cmp);
    assert.deepEqual(sorted.slice(0, 6), ['1.2', '1.10', '2', '10', 'a', 'B']);
    assert.ok(sorted.slice(6).every((v) => v === null || v === ''));
    assert.equal(cmp(3, 20) < 0, true);
});

test('sortField orders the tab keys without touching the Bag, unless sortStore', () => {
    const s = createGrid();
    chapters(s, [['r_a', '10', 'Crew', []], ['r_b', '2', 'Cast', []], ['r_c', '1', 'Story', []]]);
    const store = new s.context.gnr.GroupletDataStore({store: {getData: () => s.lines}}, {});
    store.setSort({field: 'code'});
    assert.deepEqual([...store.sortedKeys()], ['r_c', 'r_b', 'r_a']);
    assert.equal(store.applySortToStore(), false);
    assert.deepEqual([...s.lines.keys()], ['r_a', 'r_b', 'r_c']);
    store.setSort({field: 'code', store: true});
    assert.equal(store.applySortToStore(), true);
    assert.deepEqual([...s.lines.keys()], ['r_c', 'r_b', 'r_a']);
    store.clearSort();
    assert.deepEqual([...store.sortedKeys()], ['r_c', 'r_b', 'r_a'], 'unsorted is the Bag order');
});

test('titleTemplate shows fields and a live subtree total', () => {
    const s = createGrid();
    chapters(s, [['r_a', '1', 'Story', [100, 250.5]]]);
    const Ctrl = s.context.gnr.GroupletGridController;
    const tpl = Ctrl.compileTemplate({template: '$code $name $total', sums: {total: 'accounts.amount'}});
    assert.equal(s.controller.renderTemplate(tpl, 'r_a'), '1 Story 350.5');
    s.lines.setItem('r_a.accounts.a2', new s.Bag({amount: 9.5}));
    assert.equal(s.controller.renderTemplate(tpl, 'r_a'), '1 Story 360');
    assert.equal(Ctrl.deepSum(s.lines.getItem('r_a'), 'amount'), 360, 'no path: the whole row');
    assert.equal(s.controller.renderTemplate(Ctrl.compileTemplate('$name'), 'r_a'), 'Story');
});

test('a changed sort field re-sorts the strip once, a template row is redrawn', async () => {
    const s = createGrid({controller: {layout: 'tabs'}});
    chapters(s, [['r_a', '3', 'Crew', [1]], ['r_b', '2', 'Cast', [2]]]);
    const store = new s.context.gnr.GroupletDataStore({store: {getData: () => s.lines}}, {});
    store.setSort({field: 'code'});
    const strip = {children: [], appendChild(chip) {
        this.children = this.children.filter((c) => c !== chip).concat(chip);
    }};
    const titles = {};
    const chip = (k) => ({key: k, querySelector: () => ({set innerHTML(v) { titles[k] = v; },
                                                          get textContent() { return titles[k]; }})});
    Object.assign(s.controller, {
        dataStore: store, sortField: 'code', tabstripDom: strip, _dirtyRows: new Set(),
        titleTemplate: s.context.gnr.GroupletGridController.compileTemplate('$code·$name'),
        _tabsByPkey: {r_a: chip('r_a'), r_b: chip('r_b')}
    });
    strip.children = [s.controller._tabsByPkey.r_a, s.controller._tabsByPkey.r_b];
    const storeNode = s.lines.getParentNode();
    s.lines.setItem('r_a.code', '1');
    s.controller._onRowContentChanged(s.lines.getNode('r_a.code'), storeNode);
    s.controller._onRowContentChanged(s.lines.getNode('r_a.name'), storeNode);
    assert.deepEqual(strip.children.map((c) => c.key), ['r_a', 'r_b'], 'deferred');
    await tick();
    assert.equal(titles.r_a, '1·Crew');
    assert.deepEqual(strip.children.map((c) => c.key), ['r_a', 'r_b']);
    s.lines.setItem('r_a.code', '9');
    s.controller._onRowContentChanged(s.lines.getNode('r_a.code'), storeNode);
    await tick();
    assert.deepEqual(strip.children.map((c) => c.key), ['r_b', 'r_a']);
    assert.equal(titles.r_a, '9·Crew');
});
