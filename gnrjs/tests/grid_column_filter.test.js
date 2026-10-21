const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, navigator: {}, window: {}, document: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        isIE: 0,
        require() {},
        provide() {},
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        indexOf: (items, value) => Array.prototype.indexOf.call(items || [], value),
        toJson: JSON.stringify,
        declare(name, bases, members) {
            const base = Array.isArray(bases) ? bases[0] : bases;
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js',
                            'genro_components.js', 'genro_grid.js', 'genro_wdg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    return context;
}

const INVOICES = [
    {customer_id: 'C1', _customer_id_name: 'Rossi', status: 'Paid', _customer_id_agent_id: 'A1'},
    {customer_id: 'C1', _customer_id_name: 'Rossi', status: 'Sent', _customer_id_agent_id: 'A1'},
    {customer_id: 'C2', _customer_id_name: 'Verdi', status: 'Paid', _customer_id_agent_id: null},
    {customer_id: 'C3', _customer_id_name: 'Rossi', status: 'Overdue', _customer_id_agent_id: 'A2'},
    {customer_id: 'C2', _customer_id_name: 'Verdi', status: 'Sent', _customer_id_agent_id: ''}
];

function filterCell(context, attrs) {
    const cell = Object.assign({original_name: attrs.field}, attrs);
    cell.filterField_key = context.gnr.widgets.DojoGrid.prototype.columnFilterRowKey(cell);
    return cell;
}

// a NewIncludedView over an attributes store with three filterable columns
function createGrid({virtual = false, selection = false} = {}) {
    const context = createContext();
    const {gnr, genro} = context;
    const data = new gnr.GnrBag();
    const rows = new gnr.GnrBag();
    INVOICES.forEach((row, i) => rows.setItem(`r_${i}`, null, Object.assign({_pkey: `I${i}`}, row)));
    data.setItem('grid.store', rows);
    const storeNode = {
        getRelativeData: p => data.getItem(p),
        setRelativeData: (p, v) => data.setItem(p, v)
    };
    const storeClass = virtual ? gnr.stores.VirtualSelection : selection ? gnr.stores.Selection : gnr.stores.AttributesBagRows;
    const store = Object.assign(Object.create(storeClass.prototype), {storeNode, storepath: 'grid.store', identifier: '_pkey'});
    if (selection) {
        Object.assign(store, {storeType: 'Selection'});
        storeNode.attr = {};
    }
    genro.nodeById = id => (id === 'invoices_store' ? {store} : null);
    const grid = {};
    const proto = gnr.widgets.NewIncludedView.prototype;
    for (const k in proto) {
        if (k.startsWith('mixin_')) grid[k.slice(6)] = proto[k];
    }
    Object.assign(grid, {
        _collectionStore: store,
        collectionStore: () => store,
        datamode: 'attr',
        gnr: gnr.widgets.NewIncludedView.prototype,
        sourceNode: {attr: {store: 'invoices'}, evaluateOnNode: attr => attr},
        cellmap: {
            _customer_id_name: filterCell(context, {field: '_customer_id_name', field_getter: '_customer_id_name',
                                                    filterField: 'customer_id'}),
            status: filterCell(context, {field: 'status', field_getter: 'status', filterField: true}),
            agent: filterCell(context, {field: 'agent', field_getter: 'agent', filterField: '@customer_id.agent_id'})
        }
    });
    const filter = (field, values) => { grid.cellmap[field].filterValues = values; };
    const visible = () => {
        store.createFiltered(grid, null, null, null);
        return store._filtered ? Array.from(store._filtered, i => `I${i}`) : INVOICES.map((r, i) => `I${i}`);
    };
    const counts = field => {
        const result = grid.columnFilterValues(grid.cellmap[field]);
        return Object.fromEntries(Array.from(result, item => [`${item.value}`, item.count]));
    };
    return {context, gnr, grid, store, filter, visible, counts};
}

test('a string filterField reaches the query columns, true adds nothing', () => {
    const {gnr} = createContext();
    const struct = new gnr.GnrBag();
    const rows = new gnr.GnrBag();
    rows.setItem('c0', null, {field: '@customer_id.name', filterField: 'customer_id'});
    rows.setItem('c1', null, {field: 'status', filterField: true});
    rows.setItem('c2', null, {field: 'agent', calculated: true, filterField: '@customer_id.agent_id'});
    struct.setItem('view_0.rows_0', rows);
    assert.deepEqual(gnr.columnsFromStruct(struct).split(','),
                     ['$customer_id', '@customer_id.name', '$status', '@customer_id.agent_id']);
});

test('the row key of the filter field', () => {
    const context = createContext();
    assert.equal(filterCell(context, {field: '_customer_id_name', filterField: 'customer_id'}).filterField_key, 'customer_id');
    assert.equal(filterCell(context, {field: 'status', filterField: true}).filterField_key, 'status');
    assert.equal(filterCell(context, {field: 'customer_id', filterField: '$customer_id'}).filterField_key, 'customer_id');
    assert.equal(filterCell(context, {field: 'agent', filterField: '@customer_id.agent_id'}).filterField_key, '_customer_id_agent_id');
});

test('the header shows the filter icon only where supported, filled when active', () => {
    const {gnr} = createContext();
    const sourceNode = {attr: {}};
    const cell = {original_name: 'Status', filterField: true};
    assert.ok(!gnr.widgets.IncludedView.prototype.cellHeaderContent(sourceNode, cell).includes('gridColumnFilter'));
    const handler = gnr.widgets.NewIncludedView.prototype;
    const idle = handler.cellHeaderContent(sourceNode, cell);
    assert.ok(idle.includes('class="gridColumnFilter"'));
    assert.ok(idle.includes('withColumnFilter'));
    cell.filterValues = ['Paid'];
    assert.ok(handler.cellHeaderContent(sourceNode, cell).includes('gridColumnFilterActive'));
    assert.ok(!handler.cellHeaderContent(sourceNode, {original_name: 'Total'}).includes('gridColumnFilter'));
});

test('checked values combine with OR in a column and with AND across columns', () => {
    const g = createGrid();
    assert.deepEqual(g.visible(), ['I0', 'I1', 'I2', 'I3', 'I4']);
    g.filter('status', ['Paid', 'Sent']);
    assert.deepEqual(g.visible(), ['I0', 'I1', 'I2', 'I4']);
    g.filter('_customer_id_name', ['C2']);
    assert.deepEqual(g.visible(), ['I2', 'I4']);
    assert.equal(g.grid.hasColumnFilters(), true);
});

test('null and empty values are one empty choice', () => {
    const g = createGrid();
    g.filter('agent', [null]);
    assert.deepEqual(g.visible(), ['I2', 'I4']);
});

test('counts follow the other filters and ignore the column own filter', () => {
    const g = createGrid();
    g.filter('status', ['Paid']);
    g.filter('_customer_id_name', ['C1']);
    assert.deepEqual(g.counts('status'), {Paid: 1, Sent: 1, Overdue: 0});
    assert.deepEqual(g.counts('_customer_id_name'), {C1: 1, C2: 1, C3: 0});
});

test('the same caption on two ids stays two values', () => {
    const g = createGrid();
    const items = g.grid.columnFilterValues(g.grid.cellmap._customer_id_name);
    assert.deepEqual(Array.from(items, i => [i.value, i.caption, i.count]),
                     [['C1', 'Rossi', 2], ['C2', 'Verdi', 2], ['C3', 'Rossi', 1]]);
});

test('a virtual store ignores filterField: no icon and no filter', () => {
    const g = createGrid({virtual: true});
    g.filter('status', ['Paid']);
    assert.deepEqual(Array.from(g.grid.columnFilterCells()), []);
    assert.equal(g.grid.columnFilterCb(), null);
    assert.equal(g.grid.hasColumnFilters(), false);
    const header = g.gnr.widgets.NewIncludedView.prototype.cellHeaderContent(g.grid.sourceNode, g.grid.cellmap.status);
    assert.ok(!header.includes('gridColumnFilter'));
});

function structCell(context, gridAttr, cellAttr) {
    const {gnr, genro} = context;
    genro.dom = {getStyleDict: () => ({})};
    genro.evaluate = v => v;
    const struct = new gnr.GnrBag();
    const rows = new gnr.GnrBag();
    rows.setItem('c0', null, cellAttr);
    struct.setItem('view_0.rows_0', rows);
    struct.setBackRef();
    const sourceNode = {attr: gridAttr, currentFromDatasource: v => v,
                        isPointerPath: gnr.GnrDomSourceNode.prototype.isPointerPath};
    return gnr.widgets.NewIncludedView.prototype.structFromBag_cell(sourceNode, struct.getNode('view_0.rows_0.c0'), new gnr.GnrBag());
}

test('filterFieldDefault on the grid turns filterField on for plain data cells only', () => {
    const context = createContext();
    const on = {filterFieldDefault: true};
    assert.equal(structCell(context, on, {field: 'status'}).filterField, true);
    assert.equal(structCell(context, on, {field: '@customer_id.name'}).filterField_key, '_customer_id_name');
    assert.equal(structCell(context, on, {field: 'status', filterField: false}).filterField, false);
    assert.equal(structCell(context, on, {field: 'agent', filterField: 'agent_id'}).filterField, 'agent_id');
    for (const attrs of [{template: '$a $b'}, {rowTemplate: '$a'}, {template_columns: 'a,b'}, {calculated: true},
                         {values: 'A:Open,C:Closed'}, {format_isbutton: true}, {format_buttonclass: 'iconbox'}]) {
        assert.equal(structCell(context, on, Object.assign({field: 'status'}, attrs)).filterField, undefined, JSON.stringify(attrs));
    }
    assert.equal(structCell(context, {}, {field: 'status'}).filterField, undefined);
});

test('a template cell filtered on another field captions the filtered value', () => {
    const g = createGrid();
    const {context, grid} = g;
    const cell = filterCell(context, {field: 'customer_id', field_getter: 'customer_id', filterField: 'status',
                                      _filterCaptionFromValue: true});
    assert.equal(grid.columnFilterCaption(cell, INVOICES[0], INVOICES[0].status), 'Paid');
    assert.equal(grid.columnFilterCaption(grid.cellmap._customer_id_name, INVOICES[0], 'C1'), 'Rossi');
});

test('filter values follow the natural order of the column, empty last', () => {
    const context = createContext();
    const {gnr} = context;
    const date = (y, m, d) => vm.runInContext(`new Date(${y}, ${m}, ${d})`, context);
    const order = (cell, items) => {
        const pane = Object.assign(Object.create(gnr.GridColumnFilterPane.prototype), {cell});
        return items.map(([value, caption]) => ({value, caption: caption === undefined ? value : caption,
                                                 key: gnr.columnFilterKey(value), count: 0}))
                    .sort(pane.compareItems.bind(pane)).map(item => pane.captionText(item));
    };
    assert.deepEqual(order({filterField: true}, [[10, '10,00'], [null], [9, '9,00'], [-5, '-5,00']]),
                     ['-5,00', '9,00', '10,00', '(empty)']);
    assert.deepEqual(order({filterField: true}, [[date(2026, 1, 1), '01/02/2026'], [date(2025, 0, 15), '15/01/2025']]),
                     ['15/01/2025', '01/02/2026']);
    assert.deepEqual(order({filterField: true}, [['zeta'], [''], ['Beta'], ['alfa'], ['PO 10'], ['PO 9']]),
                     ['alfa', 'Beta', 'PO 9', 'PO 10', 'zeta', '(empty)']);
    assert.deepEqual(order({filterField: true, caption_field: '_c'}, [[3, 'Rossi'], [1, 'Verdi'], [2, 'Bianchi']]),
                     ['Bianchi', 'Rossi', 'Verdi']);
});

test('the pkeys of the grid are the rows the filters leave visible', () => {
    const g = createGrid();
    assert.deepEqual(Array.from(g.grid.getAllPkeys()), ['I0', 'I1', 'I2', 'I3', 'I4']);
    g.filter('status', ['Paid']);
    g.visible();
    assert.deepEqual(Array.from(g.grid.getAllPkeys()), ['I0', 'I2']);
    assert.deepEqual(Array.from(g.grid.getAllPkeys('_customer_id_name'), r => `${r.pkey}:${r.caption}`),
                     ['I0:Rossi', 'I2:Verdi']);
});

test('print and batch with no row selected get the visible rows of a static selection', () => {
    const g = createGrid({selection: true});
    Object.assign(g.grid, {getSelectedPkeys: () => [], getSelectedRowidx: () => []});
    g.filter('_customer_id_name', ['C2']);
    g.visible();
    const kw = g.grid.currentSelectionPars();
    assert.deepEqual(Array.from(kw.selectedPkeys), ['I2', 'I4']);
    assert.equal(kw.selectionCount, 2);
});

test('the export of a filtered grid holds the visible rows, none when nothing matches', () => {
    const g = createGrid();
    const exported = () => Array.from(g.grid.currentData('all', true, true).getNodes(), n => n.attr._pkey);
    assert.deepEqual(exported(), ['I0', 'I1', 'I2', 'I3', 'I4']);
    g.filter('status', ['Sent']);
    g.visible();
    assert.deepEqual(exported(), ['I1', 'I4']);
    g.filter('_customer_id_name', ['C3']);
    g.visible();
    assert.deepEqual(exported(), []);
    assert.equal(g.grid.currentData('all', true, false).len(), 5);
});

test('a period on a date column keeps the rows whose day falls in it, bounds included', () => {
    const g = createGrid();
    const date = (y, m, d, h = 0) => vm.runInContext(`new Date(${y}, ${m}, ${d}, ${h})`, g.context);
    const cell = filterCell(g.context, {field: 'issued', field_getter: 'issued', filterField: true, dtype: 'DH'});
    g.grid.cellmap.issued = cell;
    cell.filterRange = {from: '2026-03-01', to: '2026-03-31'};
    const keep = g.grid.columnFilterCb();
    assert.equal(keep({issued: date(2026, 2, 1)}), true);
    assert.equal(keep({issued: date(2026, 2, 31, 23)}), true);
    assert.equal(keep({issued: date(2026, 3, 1)}), false);
    assert.equal(keep({issued: date(2026, 1, 28, 23)}), false);
    assert.equal(keep({issued: null}), false);
    assert.equal(keep({issued: '2026-03-15'}), true);
    cell.filterRange = {from: null, to: '2026-03-31'};
    assert.equal(g.grid.columnFilterCb()({issued: date(2020, 0, 1)}), true);
    assert.equal(g.grid.columnFilterSignature(), 'issued=..2026-03-31');
});

test('a period and checked values exclude each other, and either marks the header active', () => {
    const g = createGrid();
    const cell = g.grid.cellmap.status;
    Object.assign(g.grid, {structCellNode: () => null, refreshColumnFilterHeaders() {}, applyColumnFilters() {}});
    g.grid.setColumnFilter(cell, null, {from: '2026-01-01', to: null});
    assert.deepEqual({...cell.filterRange}, {from: '2026-01-01', to: null});
    assert.ok(g.gnr.widgets.NewIncludedView.prototype.cellHeaderContent({attr: {}}, cell).includes('gridColumnFilterActive'));
    g.grid.setColumnFilter(cell, ['Paid']);
    assert.equal(cell.filterRange, null);
    assert.deepEqual(Array.from(cell.filterValues), ['Paid']);
    g.grid.setColumnFilter(cell, null, {from: null, to: null});
    assert.equal(g.gnr.columnFilterActive(cell), false);
});

test('the order of the filter values turns descending, empty still last', () => {
    const context = createContext();
    const {gnr} = context;
    const date = (y, m, d) => vm.runInContext(`new Date(${y}, ${m}, ${d})`, context);
    const order = (cell, items) => {
        const pane = Object.assign(Object.create(gnr.GridColumnFilterPane.prototype), {cell});
        return items.map(([value, caption]) => ({value, caption: caption === undefined ? value : caption,
                                                 key: gnr.columnFilterKey(value), count: 0}))
                    .sort(pane.compareItems.bind(pane)).map(item => pane.captionText(item));
    };
    assert.deepEqual(order({filterField: true, _filterDescending: true},
                           [[date(2025, 0, 15), '15/01/2025'], [null], [date(2026, 1, 1), '01/02/2026']]),
                     ['01/02/2026', '15/01/2025', '(empty)']);
    assert.deepEqual(order({filterField: true, _filterDescending: true}, [['alfa'], [''], ['PO 9'], ['PO 10']]),
                     ['PO 10', 'PO 9', 'alfa', '(empty)']);
});
