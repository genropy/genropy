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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const gridJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js');
    vm.runInContext(readFileSync(path.join(path.dirname(gridJs), 'grouplet_card.js'), 'utf8'), context,
                    {filename: 'grouplet_card.js'});
    vm.runInContext(readFileSync(gridJs, 'utf8'), context, {filename: 'grouplet_grid.js'});
    context._T = str => str;
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const lines = new Bag();
    data.setItem('record.lines', lines);
    data.setItem('ws', new Bag());
    data.setBackRef();
    let counter = 0;
    const published = [];
    Object.assign(context.genro, {
        _data: data,
        vld: new context.gnr.GnrValidator(context.genro),
        wdg: {getHandler: () => null},
        publish: (topic, kw) => published.push([topic, kw]),
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
            rowNode: key => lines.getNode(key),
            removeRow: key => lines.popNode(key),
            updateRow: (key, dict) => Object.keys(dict).forEach(k => lines.setItem(key + '.' + k, dict[k]))
        },
        layout: 'cards',
        _containerDom: () => ({classList: {toggle() {}, remove() {}}})
    });
    controller._resetPhantom();
    const phantom = () => data.getItem('ws.phantom');
    return {controller, lines, phantom, data, published, context, genro: context.genro};
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
    let field;
    if (missing) {
        const row = new s.context.gnr.GnrDomSource();
        row._('div', 'entry', {datapath: 'ws.entry'});
        row.getItem('entry')._('textbox', missing, {tag: 'textbox', value: '^.' + missing, validate_notnull: true});
        field = row.getNode('entry.' + missing);
        field.setValidations();
        field.widget = {focus: () => focused.push(missing)};
        field.updateValidationClasses = () => {};
        field.isLostNode = () => false;
    }
    Object.assign(s.controller, {
        entry: true,
        entryPath: 'ws.entry',
        entryTile: {
            domNode: () => null,
            tileContent: {walk: (cb) => (field ? cb(field) : undefined)}
        },
        _announcer: {textContent: ''}
    });
    s.controller._resetEntry();
    return {...s, focused, field, entry: () => s.data.getItem('ws.entry')};
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

test('the entry row works out its formulas as it is typed in', () => {
    const s = entryGrid();
    s.genro.getDataNode = (p) => s.data.getNode(p);
    s.controller._changeMgr = {
        formulaColumns: {total: 'qty*price', n: '#'},
        evaluateFormula: (field, node) => node.getValue().getItem('qty') * node.getValue().getItem('price')
    };
    s.entry().setItem('price', 2.5);
    assert.equal(s.entry().getItem('total'), 2.5);
    assert.ok(!s.entry().getNode('n'), 'a counter needs a row');
    s.entry().setItem('qty', 4);
    assert.equal(s.entry().getItem('total'), 10);
    s.entry().setItem('item', 'Milk');
    s.controller._addEntry();
    assert.equal(s.lines.getItem('r_k1.total'), 10);
    assert.equal(s.entry().getItem('total'), null, 'the cleared row is not worked out');
});

test('a missing required field or a locked form stops the entry', async () => {
    const req = entryGrid({missing: 'item'});
    await tick();
    assert.equal(req.field.getValidationError(), 'notnull', 'a blank required field is flagged at once');
    req.entry().setItem('qty', 3);
    req.controller._addEntry();
    assert.equal(req.lines.len(), 0);
    assert.deepEqual(req.focused, ['item']);
    assert.ok(req.field.hasValidationError(), 'the field shows it is missing');
    assert.deepEqual(JSON.parse(JSON.stringify(req.published)), [['floating_message',
        {message: 'Item: !!Required field', sound: '$onerror', messageType: 'error'}]]);
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
        rowNode: key => s.lines.getNode(key),
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
    s.controller._rowFields = () => [
        {path: 'item', labels: ['item'], node: {attr: {tag: 'textbox'}, widget: {domNode: null}}}];
    s.controller._pasteRows('Milk\nBread', s.controller.phantomTile, null);
    assert.equal(s.lines.len(), 2);
    assert.equal(s.lines.getItem('r_k1.item'), 'Milk');
    assert.equal(s.lines.getItem('r_k2.qty'), 1);
    assert.deepEqual(Object.keys(s.controller._freshRows), ['r_k1', 'r_k2']);
});

test('the blank row hint goes on a required free-text field, else a free-text one, else the first', () => {
    const {context} = createGrid();
    context.gnr.GroupletGridTile.prototype._mountBody = () => {};
    const hinted = (cells) => {
        const content = new context.gnr.GnrDomSource();
        cells.forEach(([label, attr]) => content._(attr.tag, label, {value: '^.' + label, ...attr}));
        context.gnr.GroupletGridPhantomTile.prototype._mountBody.call(
            {tileContent: content, stripValidations: true, controller: {additemKw: {}}});
        return cells.map(([label]) => label).filter((label) => content.getNode(label).attr.placeholder);
    };
    assert.deepEqual(hinted([
        ['description', {tag: 'textbox'}],
        ['amount', {tag: 'numberTextBox'}],
        ['vat', {tag: 'filteringSelect', validate_notnull: true}]]), ['description']);
    assert.deepEqual(hinted([
        ['shop', {tag: 'textbox'}],
        ['item', {tag: 'textbox', validate_notnull: true}]]), ['item']);
    assert.deepEqual(hinted([
        ['customer', {tag: 'dbSelect'}],
        ['vat', {tag: 'filteringSelect', validate_notnull: true}]]), ['customer']);
});

test('Tab skips a kept struct column, and reaches it again once unpinned', () => {
    const s = entryGrid();
    s.controller.structAdapter = {cells: [
        {field: 'shop', edit: true, keepable: true},
        {field: 'item', edit: true}]};
    s.controller._containerDom = () => ({querySelectorAll: () => []});
    const content = new s.context.gnr.GnrDomSource();
    const focusNodes = {};
    ['shop', 'item'].forEach((field) => {
        content._('textbox', field, {tag: 'textbox', value: '^.' + field});
        const classes = new Set();
        focusNodes[field] = {tabIndex: 0, classes,
                             classList: {toggle: (c, on) => (on ? classes.add(c) : classes.delete(c))}};
        content.getNode(field).widget = {tabIndex: 0, focusNode: focusNodes[field]};
    });
    s.controller.entryTile.tileContent = content;
    s.controller._toggleKeep('shop');
    assert.equal(focusNodes.shop.tabIndex, -1);
    assert.ok(focusNodes.shop.classes.has('grouplet_grid_kept'));
    assert.equal(focusNodes.item.tabIndex, 0);
    s.controller._toggleKeep('shop');
    assert.equal(focusNodes.shop.tabIndex, 0);
});

function clipboardGrid() {
    // rows with a boolean, a text, a number and a date, the blank row's
    // fields as real source nodes; numbers in an Italian-like locale
    const s = createGrid({defaultRow: {}});
    const {context, lines} = s;
    const Bag = lines.constructor;
    const copied = [];
    context.dojo.number = {
        format: v => String(v).replace('.', ','),
        parse: t => (/^-?[\d.]*(,\d+)?$/.test(t) ? parseFloat(t.replace(/\./g, '').replace(',', '.')) : NaN)
    };
    context.dojo.date = {locale: {parse: () => null}};
    s.genro.textToClipboard = (text, message) => copied.push([text, message]);
    const when = vm.runInContext('new Date(2026, 9, 21)', context);
    lines.setItem('r_a', new Bag({bought: true, item: 'Milk', qty: 1.5, when}));
    lines.setItem('r_b', new Bag({bought: false, item: 'say "hi"', qty: 2, when: null}));
    const c = s.controller;
    const fieldTile = (datapath, pkey) => {
        const root = new context.gnr.GnrDomSource();
        root._('div', 'row', {datapath});
        root.setBackRef();
        const row = root.getItem('row');
        const doms = {};
        [['bought', {tag: 'checkbox', lbl: 'Bought'}, null],
         ['item', {lbl: 'Item'}, null],
         ['qty', {lbl: 'Qty'}, 'dijit.form.NumberTextBox'],
         ['when', {}, 'dijit.form.DateTextBox']].forEach(([field, attr, cls]) => {
            row._(attr.tag || 'textbox', field, Object.assign({tag: 'textbox', value: '^.' + field}, attr));
            doms[field] = {field};
            row.getNode(field).widget = {declaredClass: cls, constraints: {},
                                         domNode: {contains: t => t === doms[field]}};
        });
        return {pkey, tileContent: row, doms, domNode: () => null, flash() {}};
    };
    Object.assign(c, {
        storepath: 'record.lines',
        tiles: {r_a: fieldTile('record.lines.r_a', 'r_a'), r_b: fieldTile('record.lines.r_b', 'r_b')},
        phantomTile: fieldTile('ws.phantom'),
        _announcer: {textContent: ''},
        selectionmenu: {copy: true, 'delete': true}
    });
    c._containerDom = () => ({classList: {toggle() {}, remove() {}}, querySelectorAll: () => []});
    c.dataStore.getData = () => lines;
    c.dataStore.rowNode = key => lines.getNode(key);
    c.dataStore.addRow = (key, values, position) => lines.setItem(key, new Bag(values), null,
                                                                   position ? {_position: position} : undefined);
    return {...s, c, copied, fieldTile};
}

test('copied rows are a header and one tab-separated line each, in store order', () => {
    const s = clipboardGrid();
    assert.equal(s.c._rowsAsText([{grid: s.c, rowKeys: ['r_b', 'r_a']}]),
                 'Bought\tItem\tQty\twhen\n'
                 + '1\tMilk\t1,5\t2026-10-21\n'
                 + '0\t"say ""hi"""\t2\t\n');
    assert.equal(s.c._rowsAsText([{grid: s.c, rowKeys: []}]), null, 'nothing selected, nothing copied');
});

test('a struct grid copies every column, a computed one too', () => {
    const s = clipboardGrid();
    s.c.structAdapter = {cells: [{field: 'bought', name: ' '}, {field: 'item', name: 'Item'},
                                 {field: 'qty', name: 'Qty'}, {field: 'total', name: 'Total'}]};
    s.lines.setItem('r_a.total', 3);
    assert.equal(s.c._rowsAsText([{grid: s.c, rowKeys: ['r_a']}]), 'bought\tItem\tQty\tTotal\n1\tMilk\t1,5\t3\n');
});

test('copied rows paste back by their header, wherever the paste lands', () => {
    const s = clipboardGrid();
    const text = s.c._rowsAsText([{grid: s.c, rowKeys: ['r_a', 'r_b']}]);
    s.c._pasteRows(text, s.c.phantomTile, s.c.phantomTile.doms.qty);
    assert.deepEqual([...s.lines.keys()], ['r_a', 'r_b', 'r_k1', 'r_k2']);
    assert.equal(s.lines.getItem('r_k1.bought'), true);
    assert.equal(s.lines.getItem('r_k1.item'), 'Milk');
    assert.equal(s.lines.getItem('r_k1.qty'), 1.5);
    assert.equal(s.lines.getItem('r_k1.when').getTime(), new Date(2026, 9, 21).getTime());
    assert.equal(s.lines.getItem('r_k2.bought'), false);
    assert.equal(s.lines.getItem('r_k2.item'), 'say "hi"');
    assert.equal(s.lines.getItem('r_k2.when'), null);
});

test('a header column no field takes is skipped, the others go by name', () => {
    const s = clipboardGrid();
    s.c.structAdapter = {cells: [{field: 'item', name: 'Item'}, {field: 'total', name: 'Total'},
                                 {field: 'qty', name: 'Qty'}]};
    s.c._pasteRows('Total\tQty\tItem\n9\t4\tEggs\n', s.c.phantomTile, null);
    assert.deepEqual(JSON.parse(JSON.stringify(s.lines.getItem('r_k1').asDict())), {item: 'Eggs', qty: 4});
});

test('pasted into a row\'s field the first row replaces it, the others follow it in order', () => {
    const s = clipboardGrid();
    s.c.dataStore.updateRow = (key, dict) => Object.keys(dict).forEach(k => s.lines.setItem(key + '.' + k, dict[k]));
    s.c._pasteRows('Eggs\t3\nFlour\t1', s.c.tiles.r_a, s.c.tiles.r_a.doms.item);
    assert.deepEqual([...s.lines.keys()], ['r_a', 'r_k1', 'r_b']);
    assert.equal(s.lines.getItem('r_a.item'), 'Eggs', 'a full row is replaced too');
    assert.equal(s.lines.getItem('r_a.qty'), 3);
    assert.equal(s.lines.getItem('r_a.bought'), true, 'a column not pasted keeps its value');
    assert.equal(s.lines.getItem('r_k1.item'), 'Flour');
});

test('a row paste splits only a block, and leaves one an inner grid already took', () => {
    const s = clipboardGrid();
    s.c.dataStore.updateRow = (key, dict) => Object.keys(dict).forEach(k => s.lines.setItem(key + '.' + k, dict[k]));
    const paste = (text, defaultPrevented = false) => {
        const e = {defaultPrevented, target: null, clipboardData: {getData: () => text},
                   preventDefault() { e.defaultPrevented = true; }};
        s.c._onRowsPaste(e, s.c.tiles.r_a);
        return e.defaultPrevented;
    };
    assert.equal(paste('just a value'), false);
    assert.equal(paste('Eggs\nFlour', true), true);
    assert.equal(s.lines.len(), 2, 'nothing added');
    assert.equal(paste('Eggs\nFlour'), true);
    assert.equal(s.lines.len(), 3, 'one replaced, one added');
});

test('the row kebab copies its row, or the whole selection the row is in', () => {
    const s = clipboardGrid();
    s.c._handleAction({action: 'copy', rowKey: 'r_b'});
    assert.equal(s.copied.length, 1);
    assert.equal(s.copied[0][0].split('\n')[1], '0\t"say ""hi"""\t2\t');
    assert.equal(s.copied[0][1], '!!1 row copied');
    s.c._setMulti(['r_a', 'r_b']);
    s.c._handleAction({action: 'copy', rowKey: 'r_b'});
    assert.equal(s.copied[1][0].trim().split('\n').length, 3);
    assert.equal(s.copied[1][1], '!!2 rows copied');
});

test('the selection bar copies the selection from its menu', () => {
    const s = clipboardGrid();
    s.c._setMulti(['r_a', 'r_b']);
    const copy = s.c._selectionSpecs().find(spec => spec.key === 'copy');
    assert.equal(copy.label, '!!Copy');
    s.c._runSelectionAction(copy);
    assert.equal(s.copied.length, 1);
    assert.equal(s.copied[0][0].trim().split('\n').length, 3);
    assert.equal(s.copied[0][1], '!!2 rows copied');
});

test('selectionmenu: Export Excel and Print are presets, in the menu between Copy and Delete', () => {
    const s = clipboardGrid();
    s.c.selectionmenu = {copy: true, exportXls: true, print: 'Print list', 'delete': true};
    assert.deepEqual([...s.c._selectionSpecs()].map(spec => [spec.key, spec.label, spec.iconClass]),
                     [['copy', '!!Copy', 'iconbox copy duplicate_record'],
                      ['exportXls', '!!Export Excel', 'iconbox export'],
                      ['print', 'Print list', 'iconbox print'],
                      ['delete', '!!Delete', undefined]]);
});

function exportCalls(s) {
    const calls = [];
    const downloads = [];
    s.genro.serverCall = (method, params, cb) => {
        calls.push([method, params]);
        cb('/_storage/page/xls/grid_export.xlsx');
    };
    s.genro.download = url => downloads.push(url);
    return {calls, downloads};
}

test('Export Excel sends the selected rows with the copied columns to the grid export', () => {
    const s = clipboardGrid();
    const {calls, downloads} = exportCalls(s);
    s.c._setMulti(['r_b']);
    s.c._runSelectionAction({key: 'exportXls'});
    assert.equal(calls.length, 1);
    const [method, params] = calls[0];
    assert.equal(method, 'app.includedViewAction');
    assert.equal(params.action, 'export');
    assert.equal(params.export_mode, 'xls');
    assert.equal(params.datamode, 'attr');
    assert.equal(params.downloadAs, 'grid_export');
    assert.deepEqual([...params.struct.getItem('view_0.rows_0').getNodes()].map(n => ({...n.attr})),
                     [{field: 'c_0', name: 'Bought', dtype: 'B'}, {field: 'c_1', name: 'Item'},
                      {field: 'c_2', name: 'Qty', dtype: 'L'}, {field: 'c_3', name: 'when'}],
                     'a column with no declared type takes it from the exported values');
    assert.deepEqual([...params.data.getNodes()].map(n => ({...n.attr})),
                     [{c_0: false, c_1: 'say "hi"', c_2: 2, c_3: null}]);
    assert.deepEqual(downloads, ['/_storage/page/xls/grid_export.xlsx']);
});

test('Export Excel with no row selected exports them all, in store order', () => {
    const s = clipboardGrid();
    const {calls} = exportCalls(s);
    s.c.exportRows();
    assert.deepEqual([...calls[0][1].data.getNodes()].map(n => n.attr.c_1), ['Milk', 'say "hi"']);
    assert.equal(s.context.gnr.GroupletGridController._dtypeOf([900, 120], '#,##0.00'), 'N',
                 'whole amounts with a format stay decimal');
    assert.deepEqual([...calls[0][1].struct.getItem('view_0.rows_0').getNodes()].map(n => n.attr.dtype),
                     ['B', undefined, 'N', 'D']);
});

test('a struct grid exports every column, a computed one too, with its declared type', () => {
    const s = clipboardGrid();
    const {calls} = exportCalls(s);
    s.c.structAdapter = {cells: [{field: 'item', name: 'Item', dtype: 'T'}, {field: 'qty', name: 'Qty', dtype: 'R'},
                                 {field: 'total', name: 'Total', dtype: 'N', format: '#,###.00'}]};
    s.lines.setItem('r_a.total', 3);
    s.c.exportRows(['r_a']);
    assert.deepEqual([...calls[0][1].struct.getItem('view_0.rows_0').getNodes()].map(n => [n.attr.name, n.attr.dtype]),
                     [['Item', undefined], ['Qty', 'R'], ['Total', 'N']]);
    assert.deepEqual({...calls[0][1].data.getNode('r_0').attr}, {c_0: 'Milk', c_1: 1.5, c_2: 3});
});

function printFrame(s) {
    // a document small enough to build the printed table in
    const element = tag => ({tag, children: [], style: {}, className: '', textContent: '',
                             appendChild(child) { this.children.push(child); return child; },
                             remove() { this.removed = true; }});
    const listeners = {};
    const frameDoc = {title: '', head: element('head'), body: element('body'), createElement: element};
    const frame = element('iframe');
    frame.contentDocument = frameDoc;
    frame.contentWindow = {addEventListener: (name, cb) => { listeners[name] = cb; }};
    s.context.document = {title: 'Shopping', body: element('body'),
                          createElement: tag => (tag === 'iframe' ? frame : element(tag))};
    const printed = [];
    s.genro.dom = {iFramePrint: f => printed.push(f)};
    s.genro.format = (v, f) => (typeof v === 'number' ? v.toFixed(2) : 'date') + (f.format ? ' ' + f.format : '');
    const table = () => {
        const tbl = frameDoc.body.children[0];
        return tbl.children.map(section => section.children.map(
            tr => tr.children.map(cell => [cell.tag, cell.textContent, cell.className].join(':'))));
    };
    return {frame, frameDoc, printed, listeners, table};
}

test('Print puts the selected rows in a table of the copied columns and prints its frame', () => {
    const s = clipboardGrid();
    const p = printFrame(s);
    s.c._setMulti(['r_a']);
    s.c._runSelectionAction({key: 'print'});
    assert.deepEqual(p.printed, [p.frame]);
    assert.equal(p.frame.style.display, 'none');
    assert.equal(p.frameDoc.title, 'Shopping');
    assert.match(p.frameDoc.head.children[0].textContent, /\.num\{text-align:right\}/);
    assert.deepEqual(p.table(), [
        [['th:Bought:', 'th:Item:', 'th:Qty:num', 'th:when:']],
        [['td:✓:', 'td:Milk:', 'td:1.50:num', 'td:date:']]
    ]);
    p.listeners.afterprint();
    assert.ok(p.frame.removed, 'the frame goes once printed');
});

test('Print with no row selected prints them all, with the formats of the struct', () => {
    const s = clipboardGrid();
    const p = printFrame(s);
    s.c.structAdapter = {cells: [{field: 'item', name: 'Item', dtype: 'T'},
                                 {field: 'qty', name: 'Qty', dtype: 'N', format: '#,###.00'}]};
    s.c.printRows();
    assert.deepEqual(p.table()[1], [['td:Milk:', 'td:1.50 #,###.00:num'], ['td:say "hi":', 'td:2.00 #,###.00:num']]);
});

test('Cmd/Ctrl+C copies the selected rows of the grid last selected in, never over selected text', () => {
    const s = clipboardGrid();
    const c = s.c;
    const messages = [];
    s.genro.dlg = {floatingMessage: (node, kw) => messages.push(kw.message)};
    s.genro.nodeById = () => null;
    const inGrid = new Set();
    c._containerDom = () => ({classList: {toggle() {}, remove() {}}, querySelectorAll: () => [],
                              contains: el => inGrid.has(el)});
    const copy = (target) => {
        const data = {};
        const e = {target, defaultPrevented: false, clipboardData: {setData: (t, v) => { data[t] = v; }},
                   preventDefault() { e.defaultPrevented = true; }};
        c._onCopy(e);
        return e.defaultPrevented ? data['text/plain'] : null;
    };
    s.context.document = {activeElement: null};
    const field = (start, end) => {
        const f = {selectionStart: start, selectionEnd: end};
        f.closest = () => f;
        inGrid.add(f);
        s.context.document.activeElement = f;
        return f;
    };
    const box = {closest: () => null};
    assert.equal(copy(box), null, 'nothing selected, nothing copied');
    c._setMulti(['r_b']);
    assert.equal(copy(box).split('\n')[1], '0\t"say ""hi"""\t2\t');
    assert.equal(messages[0], '!!1 row copied');
    assert.equal(copy(null).split('\n').length, 3, 'nothing focused: the selection is copied');
    assert.equal(copy(field(0, 4)), null, 'text selected in a field is copied as text');
    assert.ok(copy(field(2, 2)), 'a field with no text selected copies the rows');
    const auto = field(0, 4);
    auto._ggAutoSelected = true;
    assert.ok(copy(auto), 'text the grid selected itself does not stop the row copy');
    const outside = {selectionStart: 2, selectionEnd: 2};
    outside.closest = () => outside;
    s.context.document.activeElement = outside;
    assert.equal(copy(outside), null, 'a field of another grid is not ours');
    const left = field(0, 4);
    s.context.document.activeElement = null;
    assert.ok(copy(left), 'a field without the focus is only where the page selection lingers');
    const caret = field(1, 1);
    s.c.phantomTile = {domNode: () => ({contains: el => el === caret})};
    assert.equal(copy(caret), null, 'never from the blank row');
    s.c.phantomTile = {domNode: () => null};
    s.context.gnr.GroupletGridController._lastSelected = {nodeId: 'other'};
    assert.equal(copy(box), null, 'another grid selected since answers instead');
});

test('a field laid out by a formlet is named by its label wrapper', () => {
    const s = clipboardGrid();
    const root = new s.context.gnr.GnrDomSource();
    root._('div', 'row', {datapath: 'record.lines.r_a'});
    root.setBackRef();
    root.getItem('row')._('labledbox', 'box', {_labelWrapperId: 'w1', label: 'Product'});
    root.getItem('row.box')._('textbox', 'item', {tag: 'textbox', value: '^.item', _labelWrapper: 'w1'});
    root.getNode('row.box.item').widget = {domNode: null};
    const fields = s.c._rowFields({pkey: 'r_a', tileContent: root.getItem('row')});
    assert.deepEqual([...fields].map(f => [f.path, f.label]), [['item', 'Product']]);
    assert.ok(fields[0].labels.includes('product'));
});

test('the band\'s kebab: the editmenu entries, then Copy, then Delete only when rows can be deleted', () => {
    const s = clipboardGrid();
    const tile = Object.create(s.context.gnr.GroupletGridTile.prototype);
    const spec = (editmenuSpec, hasDelete) => {
        Object.assign(tile, {editmenuSpec, hasDelete});
        return JSON.parse(JSON.stringify(tile._bandMenuSpec()));
    };
    assert.deepEqual(spec(null, true), {copy: true, 'delete': true});
    assert.deepEqual(spec(null, false), {copy: true}, 'delitem=False drops Delete');
    assert.deepEqual(Object.keys(spec({addPrev: true, 'delete': true, addNext: true}, true)),
                     ['addPrev', 'addNext', 'copy', 'delete']);
    assert.deepEqual(spec({'delete': true}, false), {copy: true}, 'an editmenu delete is no delitem');
    assert.deepEqual(spec({copy: false, 'delete': 'Remove'}, true), {copy: false, 'delete': 'Remove'});
});

test('the corner kebab keeps its label, classes and node id; the band one takes the card classes', () => {
    const s = clipboardGrid();
    const c = s.c;
    Object.assign(c, {actionTopic: 'grid_action', controllerPath: 'ws.ctrl',
                      editmenuKw: vm.runInContext('({_class: "custom"})', s.context)});
    const kebab = (card) => {
        const tile = Object.create(s.context.gnr.GroupletGridTile.prototype);
        const content = new s.context.gnr.GnrDomSource();
        Object.assign(tile, {controller: c, pkey: 'r_a', tileContent: content, hasDelete: true,
                             editmenuSpec: vm.runInContext('({addNext: true})', s.context), card: null});
        if (card) tile.card = {bandContent: content};
        tile._mountKebab();
        const node = content.getNode('_grtile_kebab_r_a');
        return [node.attr._class, node.attr.nodeId, node.getValue().getNode('glyph').attr._class];
    };
    assert.deepEqual(kebab(false), ['grouplet_grid_row_kebab custom', '__grpgridtilemenu__grid__r_a',
                                    'grouplet_grid_kebab_icon']);
    assert.deepEqual(kebab(true), ['grouplet_card_kebab custom', '__grpgridtilemenu__grid__r_a',
                                   'grouplet_card_kebab_icon']);
});

function chromeClasses(s, {struct, hasDelete, hasCopy, editmenu}) {
    const c = s.c;
    Object.assign(c, {actionTopic: 'grid_action', controllerPath: 'ws.ctrl', structAdapter: struct ? {} : null,
                      delitemKw: {}, copyitemKw: {}, editmenuKw: {}});
    const tile = Object.create(s.context.gnr.GroupletGridTile.prototype);
    const content = new s.context.gnr.GnrDomSource();
    Object.assign(tile, {controller: c, pkey: 'r_a', tileContent: content, card: null, hasDelete, hasCopy,
                         editmenuSpec: editmenu ? vm.runInContext('({addNext: true})', s.context) : null});
    tile._mountChrome();
    const classes = {};
    content.getNodes().forEach((n) => { classes[n.label.replace(/^_grtile_|_r_a$/g, '')] = n.attr._class; });
    return {classes, content};
}

test('struct rows set the kebab, the trash and the copy side by side from the right edge', () => {
    const s = clipboardGrid();
    assert.deepEqual(chromeClasses(s, {struct: true, hasDelete: true, hasCopy: true, editmenu: true}).classes, {
        del: 'grouplet_grid_row_delete grouplet_grid_tool_slot_1',
        copy: 'grouplet_grid_row_copy grouplet_grid_tool_slot_2',
        kebab: 'grouplet_grid_row_kebab'
    });
    assert.deepEqual(chromeClasses(s, {struct: true, hasDelete: true, hasCopy: false, editmenu: true}).classes, {
        del: 'grouplet_grid_row_delete grouplet_grid_tool_slot_1',
        kebab: 'grouplet_grid_row_kebab'
    }, 'the trash no longer sits over the kebab');
    assert.deepEqual(chromeClasses(s, {struct: true, hasDelete: false, hasCopy: true, editmenu: false}).classes, {
        copy: 'grouplet_grid_row_copy'
    });
});

test('a card keeps its kebab apart: the copy sits left of the trash in the corner', () => {
    const s = clipboardGrid();
    assert.deepEqual(chromeClasses(s, {struct: false, hasDelete: true, hasCopy: true, editmenu: true}).classes, {
        del: 'grouplet_grid_row_delete',
        copy: 'grouplet_grid_row_copy grouplet_grid_tool_slot_1',
        kebab: 'grouplet_grid_row_kebab'
    });
});

test('the copy button publishes the row copy, as the kebab entry does', () => {
    const s = clipboardGrid();
    const {content} = chromeClasses(s, {struct: true, hasDelete: false, hasCopy: true, editmenu: false});
    const copy = content.getNode('_grtile_copy_r_a').attr;
    assert.equal(copy.connect_onclick, "genro.publish('grid_action',{action:'copy',rowKey:'r_a'});");
});

test('a dynamic delitem is read on the row as its menu opens, and refuses the delete', () => {
    const s = clipboardGrid();
    const c = s.c;
    c.controllerPath = 'ws.ctrl';
    c.minRows = 0;
    c.dataStore.rowValue = (k) => s.lines.getItem(k);
    s.lines.setItem('r_a.invoiced', true);
    s.lines.setItem('r_b.invoiced', false);
    Object.keys(c.tiles).forEach((k) => {
        c.tiles[k].delitem = '==!invoiced';
        c.tiles[k].tileNode = {currentFromDatasource: () => null};
    });
    const locked = (k) => {
        c._refreshRowMenu(k);
        return s.data.getItem('ws.ctrl.row_menu.delete_locked');
    };
    assert.equal(locked('r_a'), true);
    assert.equal(locked('r_b'), false);
    s.lines.setItem('r_a.invoiced', false);
    assert.equal(locked('r_a'), false, 'read again at the next opening');
    s.lines.setItem('r_a.invoiced', true);
    const asked = [];
    const warned = [];
    c.dataStore.deleteRowAsk = (k) => asked.push(k);
    s.genro.dlg = {floatingMessage: (node, kw) => warned.push(kw.message)};
    c._handleAction({action: 'delete', rowKey: 'r_a'});
    c._handleAction({action: 'delete', rowKey: 'r_b'});
    assert.deepEqual(asked, ['r_b']);
    assert.deepEqual(warned, ['!!This row cannot be deleted']);
    c._setMulti(['r_a', 'r_b']);
    assert.equal(c._selectionDeleteLocked(), true, 'a selection holding r_a cannot be deleted');
    c.tiles.r_a.delitem = true;
    assert.equal(c._selectionDeleteLocked(), false, 'a static delitem never refuses');
});

test('a row\'s card profile: its resource\'s card, then the caller\'s, the title of last resort the resource template', () => {
    const s = clipboardGrid();
    const c = s.c;
    const inVm = (obj) => vm.runInContext('(' + JSON.stringify(obj) + ')', s.context);
    s.genro.safeHtmlContent = (v) => v;
    Object.assign(c, {_cardProfiles: {}, collapsedTemplate: null,
                      card: inVm({tools: 'title,menu'}),
                      templateCards: inVm({offer: {tools: 'title,doc', delitem: false, doc: 'grouplet:test:offer',
                                                   template: '$item!'}})});
    const offer = c._cardProfile('offer');
    assert.equal(offer.tools, 'title,menu', 'the caller wins');
    assert.equal(offer.delitem, false);
    const row = new s.lines.constructor({item: 'Milk'});
    assert.equal(s.context.gnr.GroupletCard.renderTemplate(offer.title, row), 'Milk!');
    assert.equal(offer.doc, 'grouplet:test:offer', 'the row\'s doc address');
    assert.equal(c._cardProfile('offer'), offer, 'computed once per resource');
    const plain = c._cardProfile('__default__');
    assert.equal(plain.title, null);
    assert.equal(plain.doc, undefined);
    assert.ok(!('delitem' in plain), 'the grid\'s delitem then applies');
});

test('cards use the band unless chromeSide is off; line rows, tabs and blank rows never do', () => {
    const s = clipboardGrid();
    const c = s.c;
    const tile = Object.create(s.context.gnr.GroupletGridTile.prototype);
    tile.controller = c;
    c._isTabsLayout = () => c.layout !== 'cards';
    c.chromeSide = 'top';
    assert.equal(tile._usesBand(), true);
    c.chromeSide = null;
    assert.equal(tile._usesBand(), false);
    c.chromeSide = 'left';
    c.layout = 'tabs';
    assert.equal(tile._usesBand(), false);
    c.layout = 'cards';
    c.structAdapter = {cells: []};
    assert.equal(tile._usesBand(), false);
    c.structAdapter = null;
    c.rowTemplate = '$item';
    assert.equal(tile._usesBand(), false);
    c.rowTemplate = null;
    const blank = Object.create(s.context.gnr.GroupletGridPhantomTile.prototype);
    blank.controller = c;
    assert.equal(blank._usesBand(), false);
});

test('the row kebab says and does what it acts on: its row, or the whole selection the row is in', () => {
    const s = clipboardGrid();
    const c = s.c;
    c.controllerPath = 'ws.ctrl';
    const menu = () => JSON.parse(JSON.stringify(s.data.getItem('ws.ctrl.row_menu').asDict()));
    c.minRows = 0;
    c._refreshRowMenu('r_a');
    assert.deepEqual(menu(), {copy_label: '!!Copy', delete_label: '!!Delete row', delete_locked: false});
    c.minRows = 2;
    c._refreshRowMenu('r_a');
    assert.equal(menu().delete_locked, true, 'two rows, minRows=2');
    c.minRows = 0;
    c._setMulti(['r_a', 'r_b']);
    c._refreshRowMenu('r_b');
    assert.deepEqual(menu(), {copy_label: '!!Copy $count rows'.replace('$count', 2),
                              delete_label: '!!Delete $count rows'.replace('$count', 2), delete_locked: false});
    c.minRows = 1;
    c._refreshRowMenu('r_b');
    assert.equal(menu().delete_locked, true, 'the selection would leave fewer than minRows');
    const asked = [];
    c.dataStore.deleteRowsAsk = keys => asked.push([...keys]);
    c.minRows = 0;
    c._handleAction({action: 'delete', rowKey: 'r_a'});
    assert.deepEqual(asked, [['r_a', 'r_b']], 'the kebab of a selected row deletes the selection');
    c.sourceNode.getFormHandler = () => ({isDisabled: () => true});
    assert.equal(c._deleteLocked(), true);
    assert.equal(c._selectionDeleteLocked(), true);
});

test('a selection ticks the checkboxes in the chrome band too', () => {
    const s = clipboardGrid();
    const c = s.c;
    c.rowCheckbox = true;
    const boxes = {};
    Object.keys(c.tiles).forEach((k) => {
        boxes[k] = {checked: false};
        c.tiles[k].domNode = () => ({classList: {toggle() {}}, querySelector: () => null});
        c.tiles[k].card = {setChecked: (v) => { boxes[k].checked = v; }};
    });
    c._rowCount = () => Object.keys(c.tiles).length;
    c._setMulti(['r_b']);
    assert.deepEqual(Object.keys(boxes).map(k => boxes[k].checked), [false, true]);
});

test('Cmd/Ctrl+C copies a card selected by a plain click, which is not ticked', () => {
    const s = clipboardGrid();
    const c = s.c;
    s.genro.dlg = {floatingMessage() {}};
    s.genro.nodeById = () => null;
    c.layout = 'cards';
    c._isTabsLayout = () => false;
    c.tiles.r_a.domNode = () => ({classList: {add() {}, remove() {}}});
    c.selectTile('r_a');
    assert.ok(!c._multiKeys, 'one card is no multiple selection');
    const data = {};
    const e = {target: null, defaultPrevented: false, clipboardData: {setData: (t, v) => { data[t] = v; }},
               preventDefault() { e.defaultPrevented = true; }};
    c._onCopy(e);
    assert.equal(e.defaultPrevented, true);
    assert.equal(data['text/plain'].split('\n')[1], '1\tMilk\t1,5\t2026-10-21');

});

test('row clicks select as in a file list: Cmd toggles, Shift takes the range in place, Cmd+Shift adds it', () => {
    const s = clipboardGrid();
    const c = s.c;
    c._isTabsLayout = () => false;
    ['r_c', 'r_d'].forEach((k) => {
        s.lines.setItem(k, new s.lines.constructor({item: k}));
        c.tiles[k] = s.fieldTile('record.lines.' + k, k);
    });
    Object.keys(c.tiles).forEach((k) => {
        c.tiles[k].domNode = () => ({classList: {add() {}, remove() {}, toggle() {}}, querySelector: () => null});
    });
    c.selectTile('r_a');
    c._onRowClickSelect('r_c', {metaKey: true});
    assert.deepEqual([...c._multiKeys], ['r_a', 'r_c'], 'Cmd adds to the row selected by a plain click');
    c._onRowClickSelect('r_d', {shiftKey: true});
    assert.deepEqual([...c._multiKeys], ['r_c', 'r_d'], 'Shift: the range from the anchor, in place');
    c._onRowClickSelect('r_a', {shiftKey: true});
    assert.deepEqual([...c._multiKeys], ['r_a', 'r_b', 'r_c'], 'the anchor stays where Cmd left it');
    c._onRowClickSelect('r_d', {metaKey: true});
    c._onRowClickSelect('r_b', {metaKey: true});
    assert.deepEqual([...c._multiKeys], ['r_a', 'r_c', 'r_d']);
    c._onRowClickSelect('r_a', {metaKey: true, shiftKey: true});
    assert.deepEqual([...c._multiKeys].sort(), ['r_a', 'r_b', 'r_c', 'r_d'], 'Cmd+Shift adds the range');
    c.rowCheckbox = true;
    assert.equal(c._clickClearsSelection({}), true, 'a plain click clears the ticks too');
});

test('pasted or added rows become the selection: one is the current row, several are ticked', () => {
    const s = clipboardGrid();
    const c = s.c;
    c._isTabsLayout = () => false;
    c._multiKeys = ['r_a'];
    c._pasteRows('Eggs\nFlour', c.phantomTile, null);
    assert.deepEqual([...c._multiKeys], ['r_k1', 'r_k2']);
    c._pasteRows('Milk\t2', c.phantomTile, null);
    assert.ok(!c._multiKeys, 'no ticks left');
    assert.equal(c.selectedPkey, 'r_k3');
    c._setMulti(['r_a', 'r_b']);
    c._doAddItem();
    assert.ok(!c._multiKeys);
    assert.equal(c.selectedPkey, 'r_k4');
});
test('Cmd/Ctrl+V with a row selected and no field focused adds the rows at the tail', () => {
    const s = clipboardGrid();
    const c = s.c;
    c._rowFields = () => [
        {path: 'item', labels: ['item'], node: {attr: {tag: 'textbox'}, widget: {domNode: null}}}];
    s.context.document = {activeElement: {closest: () => null}};
    const paste = (text) => {
        const e = {defaultPrevented: false, clipboardData: {getData: () => text},
                   preventDefault() { e.defaultPrevented = true; }};
        c._onDocumentPaste(e);
        return e.defaultPrevented;
    };
    assert.equal(paste('Eggs\nFlour'), false, 'no grid selected in yet');
    s.context.gnr.GroupletGridController._lastSelected = c;
    assert.equal(paste('Eggs\nFlour'), false, 'nothing selected');
    c.selectedPkey = 'r_a';
    assert.equal(paste('just a value'), false);
    assert.equal(paste('Eggs\nFlour'), true);
    assert.deepEqual([...s.lines.keys()], ['r_a', 'r_b', 'r_k1', 'r_k2']);
    assert.equal(s.lines.getItem('r_a.item'), 'Milk', 'the selected row is untouched');
    const field = {closest: () => field};
    s.context.document.activeElement = field;
    assert.equal(paste('Eggs\nFlour'), false, 'a focused field pastes into its row');
});

test('template mode: pasted in the entry row editing a row, the first row replaces it', () => {
    const s = selectableGrid();
    const c = s.controller;
    c._rowFields = () => [
        {path: 'item', labels: ['item'], node: {attr: {tag: 'textbox'}, widget: {domNode: null}}}];
    c.dataStore.addRow = (key, values, position) => s.lines.setItem(key, new s.lines.constructor(values), null,
                                                                     position ? {_position: position} : undefined);
    c._onTemplateRowClick('r_b', {});
    assert.equal(c._editingKey, 'r_b');
    c._pasteRows('Eggs\nFlour', c.entryTile, null);
    assert.equal(c._editingKey, null, 'the edit is closed');
    assert.equal(s.lines.getItem('r_b.item'), 'Eggs');
    assert.deepEqual([...s.lines.keys()], ['r_a', 'r_b', 'r_k1', 'r_c', 'r_d']);
    assert.equal(s.lines.getItem('r_k1.item'), 'Flour');
});
