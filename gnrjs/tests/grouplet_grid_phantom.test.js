const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createGrid({defaultRow = {qty: 1, bought: false}, disabled = false, maxRows = null, rows = 0} = {}) {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, dijit: {getEnclosingWidget: () => null}};
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const gridJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js');
    vm.runInContext(readFileSync(gridJs, 'utf8'), context, {filename: 'grouplet_grid.js'});
    context._T = str => str;
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const lines = new Bag();
    data.setItem('record.lines', lines);
    data.setItem('ws', new Bag());
    data.setBackRef();
    let counter = 0;
    Object.assign(context.genro, {
        getData: p => data.getItem(p),
        setData: (p, v) => data.setItem(p, v),
        time36Id: () => 'k' + (++counter),
        evaluate: expr => vm.runInContext('(' + expr + ')', context)
    });
    const controller = Object.create(context.gnr.GroupletGridController.prototype);
    const tiles = {};
    for (let i = 0; i < rows; i++) tiles['r_' + i] = {};
    Object.assign(controller, {
        phantom: true,
        phantomPath: 'ws.phantom',
        nodeId: 'grid',
        defaultRow,
        maxRows,
        tiles,
        phantomTile: {domNode: () => null},
        formulas: {},
        _freshRows: {},
        sourceNode: {getFormHandler: () => ({isDisabled: () => disabled})},
        minRows: 0,
        dataStore: {
            addRow: (key, values) => lines.setItem(key, new Bag(values)),
            rowValue: key => lines.getItem(key),
            removeRow: key => lines.popNode(key),
            updateRow: (key, dict) => Object.keys(dict).forEach(k => lines.setItem(key + '.' + k, dict[k]))
        },
        layout: 'cards',
        _containerDom: () => ({classList: {toggle() {}, remove() {}}})
    });
    controller._resetPhantom();
    const phantom = () => data.getItem('ws.phantom');
    return {controller, lines, phantom, data, genro: context.genro};
}

const plain = bag => JSON.parse(JSON.stringify(bag.asDict()));
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test('the blank row holds only the defaults and stores nothing', async () => {
    const s = createGrid();
    assert.deepEqual(plain(s.phantom()), {qty: 1, bought: false});
    assert.equal(s.controller._phantomHasValues(), false);
    await tick();
    assert.equal(s.lines.len(), 0);
});

test('the first value entered turns the blank row into a stored row', async () => {
    const s = createGrid();
    s.phantom().setItem('item', 'Milk');
    assert.equal(s.lines.len(), 0);
    await tick();
    assert.equal(s.lines.len(), 1);
    assert.deepEqual(plain(s.lines.getItem('r_k1')), {qty: 1, bought: false, item: 'Milk'});
    assert.deepEqual(plain(s.phantom()), {qty: 1, bought: false, item: null});
    s.phantom().setItem('item', 'Bread');
    await tick();
    assert.equal(s.lines.len(), 2);
    assert.equal(s.lines.getItem('r_k2.item'), 'Bread');
});

test('an emptied cell is not an entry, a changed default is', async () => {
    const s = createGrid({defaultRow: {qty: 1, bought: true}});
    s.phantom().setItem('qty', null);
    s.phantom().setItem('note', '');
    await tick();
    assert.equal(s.lines.len(), 0);
    s.phantom().setItem('bought', false);
    await tick();
    assert.equal(s.lines.len(), 1);
    assert.equal(s.lines.getItem('r_k1.bought'), false);
});

test('a locked form or a full grid discards the entry', async () => {
    for (const kw of [{disabled: true}, {maxRows: 2, rows: 2}]) {
        const s = createGrid(kw);
        s.phantom().setItem('item', 'Milk');
        await tick();
        assert.equal(s.lines.len(), 0);
        assert.equal(s.phantom().getItem('item'), null);
    }
});

test('a row emptied back to its defaults is dropped, a filled one is kept', () => {
    const s = createGrid();
    s.controller.structAdapter = {cells: [
        {field: 'item', edit: true}, {field: 'qty', edit: true}, {field: 'line_total'}]};
    s.lines.setItem('r_a', new s.lines.constructor({item: 'Milk', qty: 1, line_total: 0}));
    s.lines.setItem('r_b', new s.lines.constructor({item: '', qty: 1, line_total: 3}));
    s.controller.tiles = {r_a: {}, r_b: {}};
    s.controller._freshRows = {r_a: true, r_b: true};
    s.controller._dropIfEmpty('r_a');
    s.controller._dropIfEmpty('r_b');
    assert.deepEqual([...s.lines.keys()], ['r_a']);
});

test('minRows and a locked form keep an empty row', () => {
    for (const kw of [{minRows: 1}, {disabled: true}]) {
        const s = createGrid({disabled: kw.disabled});
        s.controller.minRows = kw.minRows || 0;
        s.lines.setItem('r_a', new s.lines.constructor({item: null, qty: 1}));
        s.controller.tiles = {r_a: {}};
        s.controller._freshRows = {r_a: true};
        s.controller._dropIfEmpty('r_a');
        assert.equal(s.lines.len(), 1);
    }
});

test('a row the phantom created can be dropped, a loaded one cannot', async () => {
    const s = createGrid();
    s.lines.setItem('r_loaded', new s.lines.constructor({item: null, qty: 1}));
    s.phantom().setItem('item', 'Milk');
    await tick();
    s.lines.setItem('r_k1.item', null);
    s.controller.tiles = {r_loaded: {}, r_k1: {}};
    s.controller._dropIfEmpty('r_loaded');
    s.controller._dropIfEmpty('r_k1');
    assert.deepEqual([...s.lines.keys()], ['r_loaded']);
});

test('card mode: a nested field is an entry, a formula field is not', async () => {
    const s = createGrid({defaultRow: {}});
    s.controller.formulas = {total: 'qty*price'};
    s.phantom().setItem('total', 12);
    await tick();
    assert.equal(s.lines.len(), 0);
    s.phantom().setItem('extra_data.license_type', 'trial');
    await tick();
    assert.equal(s.lines.len(), 1);
    assert.equal(s.lines.getItem('r_k1.extra_data.license_type'), 'trial');
    assert.equal(s.phantom().getItem('extra_data'), null);
});

function entryGrid({missing = null, disabled = false} = {}) {
    const s = createGrid({disabled});
    const focused = [];
    Object.assign(s.controller, {
        entry: true,
        entryPath: 'ws.entry',
        entryTile: {
            domNode: () => null,
            tileContent: {walk: () => (missing ? {widget: {focus: () => focused.push(missing)}} : undefined)}
        },
        _announcer: {textContent: ''}
    });
    s.controller._resetEntry();
    return {...s, focused, entry: () => s.data.getItem('ws.entry')};
}

test('the entry row adds its values at the tail and clears, keeping the marked fields', () => {
    const s = entryGrid();
    s.entry().setItem('item', 'Milk');
    s.entry().setItem('category', 'food', {_keep: true});
    s.entry().setItem('extra.phone', '333', {_keep: true});
    s.controller._addEntry();
    assert.equal(s.lines.len(), 1);
    assert.equal(s.lines.getItem('r_k1.item'), 'Milk');
    assert.equal(s.lines.getItem('r_k1.category'), 'food');
    assert.equal(s.entry().getItem('item'), null);
    assert.equal(s.entry().getItem('qty'), 1);
    assert.equal(s.entry().getItem('category'), 'food');
    assert.equal(s.entry().getItem('extra.phone'), '333', 'a nested kept field survives');
    assert.equal(s.entry().getNode('category').attr._keep, true, 'and stays marked');
    s.controller._addEntry();
    assert.equal(s.lines.len(), 1, 'kept values alone are not a row');
    s.entry().setItem('item', 'Bread');
    s.controller._addEntry();
    assert.deepEqual([...s.lines.keys()], ['r_k1', 'r_k2']);
});

test('a struct entry row keeps the columns pinned in its header, keepable=* always', () => {
    const s = entryGrid();
    s.controller.structAdapter = {cells: [
        {field: 'shop', edit: true, keepable: true},
        {field: 'cur', edit: true, keepable: '*'},
        {field: 'item', edit: true}]};
    s.controller._containerDom = () => ({querySelectorAll: () => []});
    s.controller._resetEntry();
    s.controller._toggleKeep('shop');
    s.entry().setItem('shop', 'Lidl');
    s.entry().setItem('cur', 'EUR');
    s.entry().setItem('item', 'Milk');
    s.controller._addEntry();
    assert.equal(s.lines.getItem('r_k1.shop'), 'Lidl');
    assert.deepEqual(['shop', 'cur', 'item'].map((f) => s.entry().getItem(f)), ['Lidl', 'EUR', null]);
    s.controller._toggleKeep('shop');
    s.entry().setItem('item', 'Bread');
    s.controller._addEntry();
    assert.equal(s.lines.getItem('r_k2.shop'), 'Lidl');
    assert.deepEqual(['shop', 'cur', 'item'].map((f) => s.entry().getItem(f)), [null, 'EUR', null]);
});

test('a missing required field or a locked form stops the entry', () => {
    const req = entryGrid({missing: 'item'});
    req.entry().setItem('qty', 3);
    req.controller._addEntry();
    assert.equal(req.lines.len(), 0);
    assert.deepEqual(req.focused, ['item']);
    const locked = entryGrid({disabled: true});
    locked.entry().setItem('item', 'Milk');
    locked.controller._addEntry();
    assert.equal(locked.lines.len(), 0);
    assert.equal(locked.entry().getItem('item'), 'Milk');
});

test('template mode: a clicked row is edited in the entry row and saved in place', () => {
    const s = entryGrid();
    s.controller.rowTemplate = '$item';
    s.lines.setItem('r_a', new s.lines.constructor({item: 'Milk', qty: 2}));
    s.controller.tiles = {r_a: {domNode: () => null, flash() {}}};
    s.entry().setItem('item', 'Draft');
    s.controller._editRowInEntry('r_a');
    assert.equal(s.controller._editingKey, 'r_a');
    assert.equal(s.entry().getItem('item'), 'Milk');
    s.entry().setItem('qty', 5);
    assert.equal(s.controller._addEntry(), true);
    assert.equal(s.lines.len(), 1, 'no new row');
    assert.equal(s.lines.getItem('r_a.qty'), 5);
    assert.equal(s.controller._editingKey, null);
    assert.equal(s.entry().getItem('item'), 'Draft', 'the draft comes back');
});

test('template mode: Esc gives the edit up and restores the draft', () => {
    const s = entryGrid();
    s.controller.rowTemplate = '$item';
    s.lines.setItem('r_a', new s.lines.constructor({item: 'Milk', qty: 2}));
    s.controller.tiles = {r_a: {domNode: () => null}};
    s.controller._editRowInEntry('r_a');
    s.entry().setItem('qty', 9);
    s.controller._onEntryKeydown({key: 'Escape', target: {}, preventDefault() {}});
    assert.equal(s.lines.getItem('r_a.qty'), 2);
    assert.equal(s.controller._editingKey, null);
    assert.equal(s.entry().getItem('item'), null);
});

function selectableGrid() {
    const s = entryGrid();
    const deleted = [];
    s.controller.rowTemplate = '$item';
    s.controller.tiles = {};
    ['r_a', 'r_b', 'r_c', 'r_d'].forEach((k) => {
        s.lines.setItem(k, new s.lines.constructor({item: k}));
        s.controller.tiles[k] = {domNode: () => null};
    });
    Object.assign(s.controller.dataStore, {
        getData: () => s.lines,
        deleteRowsAsk: (keys) => deleted.push(keys)
    });
    return {...s, deleted};
}

test('template mode: Cmd/Shift+click select several rows, which leave the entry row', () => {
    const s = selectableGrid();
    const c = s.controller;
    c._onTemplateRowClick('r_a', {});
    assert.equal(c._editingKey, 'r_a');
    c._onTemplateRowClick('r_c', {metaKey: true});
    assert.deepEqual([...c._multiKeys], ['r_a', 'r_c']);
    assert.equal(c._editingKey, null, 'several rows are not edited');
    c._onTemplateRowClick('r_d', {shiftKey: true});
    assert.deepEqual([...c._multiKeys], ['r_c', 'r_d'], 'range from the last clicked row');
    c._onTemplateRowClick('r_d', {metaKey: true});
    assert.equal(c._multiKeys, null);
    assert.equal(c._editingKey, 'r_c', 'one row left is edited again');
    c._onMultiKeydown({key: 'Escape', target: {closest: () => null}, preventDefault() {}});
    assert.equal(c._editingKey, null);
});

test('rowCheckbox: a check selects from the first row, Shift extends, the box for all toggles all', () => {
    const s = selectableGrid();
    const c = s.controller;
    c.rowCheckbox = true;
    c._containerDom = () => ({classList: {toggle() {}, remove() {}}, querySelectorAll: () => []});
    c._onRowCheck('r_b', {});
    assert.deepEqual([...c._multiKeys], ['r_b'], 'one checked row is a selection, not an edit');
    assert.ok(!c._editingKey);
    c._onRowCheck('r_d', {shiftKey: true});
    assert.deepEqual([...c._multiKeys], ['r_b', 'r_c', 'r_d']);
    c._onCheckAll();
    assert.equal(c._multiKeys.length, 4);
    c._onCheckAll();
    assert.equal(c._multiKeys, null);
    c._onRowCheck('r_a', {});
    c._onTemplateRowClick('r_c', {});
    assert.equal(c._multiKeys, null, 'a click on a row clears the checks');
    assert.equal(c._editingKey, 'r_c');
});

test('selectionmenu: delete is a preset, the other entries run with the selected keys', () => {
    const s = selectableGrid();
    const c = s.controller;
    c.sourceNode.attr = {};
    c.selectionmenu = {'delete': true, mark: {label: 'Mark', action: 'grid.marked = rowKeys;'}, off: false};
    const specs = c._selectionSpecs();
    assert.deepEqual([...specs].map((spec) => [spec.key, spec.label]), [['delete', '!!Delete'], ['mark', 'Mark']]);
    c._onTemplateRowClick('r_a', {});
    c._onTemplateRowClick('r_b', {shiftKey: true});
    c._runSelectionAction(specs[1]);
    assert.deepEqual([...c.marked], ['r_a', 'r_b']);
    c._runSelectionAction(specs[0]);
    assert.deepEqual(s.deleted.map((keys) => [...keys]), [['r_a', 'r_b']]);
});

test('template mode: the delete takes the selected rows, within minRows', () => {
    const s = selectableGrid();
    const c = s.controller;
    const warnings = [];
    s.genro.dlg = {floatingMessage: (node, kw) => warnings.push(kw.message)};
    c._onTemplateRowClick('r_b', {});
    c._deleteSelected();
    c._onTemplateRowClick('r_c', {shiftKey: true});
    c._deleteSelected();
    assert.deepEqual(s.deleted.map((keys) => [...keys]), [['r_b'], ['r_b', 'r_c']]);
    c.minRows = 3;
    c._deleteSelected();
    assert.equal(s.deleted.length, 2, 'it would leave fewer than minRows');
    assert.equal(warnings.length, 1);
});

test('pasted text is split on tabs, else semicolons, else commas, with quotes', () => {
    const {controller} = createGrid();
    const parse = t => JSON.parse(JSON.stringify(controller.constructor.parseDelimited(t)));
    assert.deepEqual(parse('Milk\t2\t1,40\r\nBread\t1\t2,20\r\n'),
                     [['Milk', '2', '1,40'], ['Bread', '1', '2,20']]);
    assert.deepEqual(parse('"Rossi; Mario";3\nVerdi;"say ""hi"""'),
                     [['Rossi; Mario', '3'], ['Verdi', 'say "hi"']]);
    assert.deepEqual(parse('a,b\nc,d'), [['a', 'b'], ['c', 'd']]);
});

test('pasted rows map from the target column, skip a header, read booleans', () => {
    const {controller} = createGrid();
    const field = (path, tag) => ({path, labels: [path], node: {attr: {tag}, widget: null}});
    const fields = [field('bought', 'checkbox'), field('item', 'textbox'), field('note', 'textbox')];
    const rows = controller._rowsFromText('bought\titem\tnote\nx\tMilk\t\n0\tBread\tfresh\n\t\t\n',
                                          fields, 0);
    assert.deepEqual(JSON.parse(JSON.stringify(rows)), [
        {bought: true, item: 'Milk', note: null},
        {bought: false, item: 'Bread', note: 'fresh'}]);
    const fromItem = controller._rowsFromText('Eggs\tbrown', fields, 1);
    assert.deepEqual(JSON.parse(JSON.stringify(fromItem)), [{item: 'Eggs', note: 'brown'}]);
});

test('pasting adds one row per line at the tail, over the defaults', () => {
    const s = createGrid();
    s.controller.tiles = {};
    s.controller.phantomTile = {domNode: () => null};
    s.controller._announcer = {textContent: ''};
    s.controller._blankRowFields = () => [
        {path: 'item', labels: ['item'], node: {attr: {tag: 'textbox'}, widget: {domNode: null}}}];
    s.controller._pasteRows('Milk\nBread', s.controller.phantomTile, null);
    assert.equal(s.lines.len(), 2);
    assert.equal(s.lines.getItem('r_k1.item'), 'Milk');
    assert.equal(s.lines.getItem('r_k2.qty'), 1);
    assert.deepEqual(Object.keys(s.controller._freshRows), ['r_k1', 'r_k2']);
});
