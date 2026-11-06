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
function createGrid({virtual = false, selection = false, records = INVOICES} = {}) {
    const context = createContext();
    const {gnr, genro} = context;
    const data = new gnr.GnrBag();
    const rows = new gnr.GnrBag();
    records.forEach((row, i) => rows.setItem(`r_${i}`, null, Object.assign({_pkey: `I${i}`}, row)));
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
        return store._filtered ? Array.from(store._filtered, i => `I${i}`) : records.map((r, i) => `I${i}`);
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

function createTaggedInvoices() {
    const g = createGrid({records: [
        {supplier: 'AKOAN S.A.S.', tags: 'B14 Restaurants,B14 Verificato,SenzaTitoloProgetto'},
        {supplier: 'AKOAN S.A.S.', tags: 'fattura ok'},
        {supplier: 'Other supplier', tags: 'SenzaTitoloProgetto'},
        {supplier: 'Other supplier', tags: 'SenzaTitoloProgetto Extra'},
        {supplier: 'Other supplier', tags: null},
        {supplier: 'Other supplier', tags: ' B14 Verificato, B14 Verificato, ,fattura ok '},
        {supplier: 'Other supplier', tags: ' , '}
    ]});
    for (const field of ['supplier', 'tags']) {
        g.grid.cellmap[field] = filterCell(g.context, {field, field_getter: field, filterField: true});
    }
    return g;
}

test('comma-separated tags have individual choices and row counts under a supplier filter', () => {
    const g = createTaggedInvoices();
    g.grid.cellmap.tags.filterField_aggr = ',';
    g.filter('supplier', ['AKOAN S.A.S.']);
    assert.deepEqual(g.counts('tags'), {
        'B14 Restaurants': 1, 'B14 Verificato': 1, SenzaTitoloProgetto: 1,
        'fattura ok': 1, 'SenzaTitoloProgetto Extra': 0, null: 0
    });
    const choices = g.grid.columnFilterValues(g.grid.cellmap.tags);
    assert.equal(choices.find(item => item.value === 'SenzaTitoloProgetto').caption, 'SenzaTitoloProgetto');
    g.filter('tags', ['SenzaTitoloProgetto']);
    assert.deepEqual(g.visible(), ['I0']);
    assert.equal(g.counts('tags')['fattura ok'], 1);
    g.filter('tags', ['SenzaTitoloProgetto', 'fattura ok']);
    assert.deepEqual(g.visible(), ['I0', 'I1']);
    g.filter('tags', null);
    assert.deepEqual(g.visible(), ['I0', 'I1']);
});

test('tag matching is exact, trims whitespace, counts duplicates once and groups empty lists', () => {
    const g = createTaggedInvoices();
    g.grid.cellmap.tags.filterField_aggr = ',';
    assert.equal(g.counts('tags')['B14 Verificato'], 2);
    g.filter('tags', ['SenzaTitoloProgetto']);
    assert.deepEqual(g.visible(), ['I0', 'I2']);
    g.filter('tags', ['B14 Verificato']);
    assert.deepEqual(g.visible(), ['I0', 'I5']);
    g.filter('tags', [null]);
    assert.deepEqual(g.visible(), ['I4', 'I6']);
    assert.equal(g.counts('tags').null, 2);
});

test('ordinary text containing commas remains a single value by default', () => {
    const g = createTaggedInvoices();
    assert.equal(g.counts('tags')['B14 Restaurants,B14 Verificato,SenzaTitoloProgetto'], 1);
    g.filter('tags', ['SenzaTitoloProgetto']);
    assert.deepEqual(g.visible(), ['I2']);
});

test('the declared separator is used literally for both choices and matching', () => {
    const g = createGrid({records: [
        {tags: 'Restaurants, catering|Verified'},
        {tags: 'Verified| No project |Verified'},
        {tags: 'No project Extra'},
        {tags: ' | '}
    ]});
    g.grid.cellmap.tags = filterCell(g.context, {
        field: 'tags', field_getter: 'tags', filterField: true, filterField_aggr: '|'
    });
    assert.deepEqual(g.counts('tags'), {
        'Restaurants, catering': 1, Verified: 2, 'No project': 1, 'No project Extra': 1, null: 1
    });
    g.filter('tags', ['No project']);
    assert.deepEqual(g.visible(), ['I1']);
    g.filter('tags', ['Restaurants, catering', 'No project']);
    assert.deepEqual(g.visible(), ['I0', 'I1']);
    g.filter('tags', [null]);
    assert.deepEqual(g.visible(), ['I3']);
});

test('filterField_aggr survives cell construction and uses the declared filter field', () => {
    const g = createTaggedInvoices();
    const cell = structCell(g.context, {}, {field: 'display', filterField: 'tags', filterField_aggr: ','});
    g.grid.cellmap.display = cell;
    cell.filterValues = ['SenzaTitoloProgetto'];
    assert.equal(cell.filterField_aggr, ',');
    assert.deepEqual(g.visible(), ['I0', 'I2']);
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
    assert.equal(structCell(context, on, {field: 'status', values: 'A:Open,C:Closed'}).filterField, true);
    for (const attrs of [{template: '$a $b'}, {rowTemplate: '$a'}, {template_columns: 'a,b'}, {calculated: true},
                         {format_isbutton: true}, {format_buttonclass: 'iconbox'}]) {
        assert.equal(structCell(context, on, Object.assign({field: 'status'}, attrs)).filterField, undefined, JSON.stringify(attrs));
    }
    assert.equal(structCell(context, {}, {field: 'status'}).filterField, undefined);
});

test('a values column lists its captions and filters on its keys', () => {
    const g = createGrid({records: [{status: 'A'}, {status: 'C'}, {status: 'A'}, {status: null}]});
    const cell = structCell(g.context, {filterFieldDefault: true}, {field: 'status', values: 'A:Open,C:Closed'});
    g.grid.cellmap = {status: cell};
    assert.equal(g.grid.columnFilterCaption(cell, {status: 'A'}, 'A'), 'Open');
    assert.deepEqual(Array.from(g.grid.columnFilterValues(cell), i => [i.value, i.caption, i.count]),
                     [['A', 'Open', 2], ['C', 'Closed', 1], [null, null, 1]]);
    cell.filterValues = ['C'];
    assert.deepEqual(g.visible(), ['I1']);
    const tags = structCell(g.context, {}, {field: 'tags', values: 'A:Open,C:Closed', filterField: true, filterField_aggr: ','});
    assert.equal(g.grid.columnFilterCaption(tags, {tags: 'A,C'}, 'C'), 'Closed');
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

test('the header click position is measured from the cell, whatever element holds the pointer', () => {
    const context = createContext();
    const headerBuilder = function() {};
    context.dojo_version = '1.1';
    context.dojox = {grid: {Builder: function() {}, headerBuilder}};
    new context.gnr.widgets.DojoGrid();
    const getCellX = headerBuilder.prototype.getCellX;
    const cellNode = {getBoundingClientRect: () => ({left: 690})};
    const icon = {getBoundingClientRect: () => ({left: 694.5})};
    assert.equal(getCellX({clientX: 696, target: icon, cellNode}), 6);
    context.dojo.isMoz = 1;
    assert.equal(getCellX({clientX: 696, target: icon, cellNode}), 6);
    assert.equal(getCellX({clientX: 696, target: icon, cellNode: null}), 0);
});

test('a mousedown on the filter icon cannot start a column drag, elsewhere it goes on', () => {
    const {gnr} = createContext();
    const mousedown = gnr.widgets.DojoGrid.prototype.patch_onHeaderCellMouseDown;
    const forwarded = [];
    const grid = {onHeaderCellMouseDown_replaced: e => forwarded.push(e)};
    const event = onIcon => ({
        prevented: false,
        preventDefault() { this.prevented = true; },
        target: {closest: selector => (onIcon && selector === '.gridColumnFilter' ? {} : null)}
    });
    const onIcon = event(true);
    mousedown.call(grid, onIcon);
    assert.equal(onIcon.prevented, true);
    assert.deepEqual(forwarded, []);
    const onTitle = event(false);
    mousedown.call(grid, onTitle);
    assert.equal(onTitle.prevented, false);
    assert.deepEqual(forwarded, [onTitle]);
});

test('the filter icon is never a resize area, the rest of the header edge still is', () => {
    const context = createContext();
    const headerBuilder = function() {};
    headerBuilder.prototype.overLeftResizeArea = () => true;
    headerBuilder.prototype.overRightResizeArea = () => true;
    context.dojo_version = '1.1';
    context.dojox = {grid: {Builder: function() {}, headerBuilder}};
    new context.gnr.widgets.DojoGrid();
    const builder = new headerBuilder();
    const target = onIcon => ({target: {closest: selector => (onIcon && selector === '.gridColumnFilter' ? {} : null)}});
    assert.equal(builder.overLeftResizeArea(target(true)), false);
    assert.equal(builder.overRightResizeArea(target(true)), false);
    assert.equal(builder.overLeftResizeArea(target(false)), true);
    assert.equal(builder.overRightResizeArea(target(false)), true);
});

test('a column drag that starts on the filter icon is refused, a press on the title clears the mark', () => {
    const {gnr} = createContext();
    const grid = {onHeaderCellMouseDown_replaced: () => {}};
    const mousedown = gnr.widgets.DojoGrid.prototype.patch_onHeaderCellMouseDown;
    const press = onIcon => mousedown.call(grid, {
        preventDefault() {},
        target: {closest: selector => (onIcon && selector === '.gridColumnFilter' ? {} : null)}
    });
    const dragStart = gnr.widgets.DojoGrid.prototype.onDragStart;
    press(true);
    assert.equal(dragStart({dragmode: 'column', widget: grid}), false);
    press(false);
    assert.equal(grid._columnFilterPressed, false);
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

test('a period and checked values add up, and either marks the header active', () => {
    const g = createGrid();
    const date = (y, m, d) => vm.runInContext(`new Date(${y}, ${m}, ${d})`, g.context);
    const cell = filterCell(g.context, {field: 'issued', field_getter: 'issued', filterField: true, dtype: 'D'});
    g.grid.cellmap = {issued: cell};
    Object.assign(g.grid, {structCellNode: () => null, refreshColumnFilterHeaders() {}, applyColumnFilters() {}});
    const march = {from: '2026-03-01', to: '2026-03-31'};
    g.grid.setColumnFilter(cell, null, march);
    assert.ok(g.gnr.widgets.NewIncludedView.prototype.cellHeaderContent({attr: {}}, cell).includes('gridColumnFilterActive'));
    const d5 = date(2026, 2, 5);
    g.grid.setColumnFilter(cell, [d5], march);
    const keep = g.grid.columnFilterCb();
    assert.equal(keep({issued: d5}), true);
    assert.equal(keep({issued: date(2026, 2, 14)}), false);
    assert.equal(g.grid.columnFilterSignature(), `issued=2026-03-01..2026-03-31|${g.gnr.columnFilterKey(d5)}`);
    g.grid.setColumnFilter(cell, [], march);
    assert.deepEqual(Array.from(cell.filterValues), []);
    assert.equal(g.grid.columnFilterCb()({issued: d5}), false);
    g.grid.setColumnFilter(cell, [], null);
    assert.equal(cell.filterValues, null);
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

test('a period narrows the list with its days checked, a click refines it, emptying it keeps the checks', () => {
    const context = createContext();
    const {gnr} = context;
    const date = (y, m, d) => vm.runInContext(`new Date(${y}, ${m}, ${d})`, context);
    const items = [date(2026, 1, 20), date(2026, 2, 5), date(2026, 2, 14), date(2026, 3, 1)]
        .map(value => ({value, key: gnr.columnFilterKey(value), count: 1}));
    const march = {from: '2026-03-01', to: '2026-03-31'};
    const cell = {field: 'issued', filterField: true, filterRange: march};
    const pane = Object.assign(Object.create(gnr.GridColumnFilterPane.prototype), {
        cell, items, rangePath: null,
        grid: {setColumnFilter: (c, values, range) => {
            c.filterRange = range && (range.from || range.to) ? range : null;
            c.filterValues = values && (values.length || c.filterRange) ? values : null;
        }},
        renderList() {}, updateFoot() {}
    });
    const row = (idx, checked) => ({dataset: {idx: `${idx}`}, checked, parentNode: {classList: {toggle() {}}}});
    const keys = () => Array.from(pane.checkedKeys());
    assert.deepEqual(keys(), [items[1].key, items[2].key]);
    pane.toggle(row(2, false));
    assert.deepEqual(cell.filterValues.map(gnr.columnFilterKey), [items[1].key]);
    assert.equal(cell.filterRange, march);
    pane.toggle(row(2, true));
    assert.equal(cell.filterValues, null);
    pane.toggle(row(2, false));
    pane.setRange(null, null);
    assert.equal(cell.filterRange, null);
    assert.deepEqual(cell.filterValues.map(gnr.columnFilterKey), [items[1].key]);
    assert.deepEqual(keys(), [items[1].key]);
});

test('the period fields set the filter only when the period changes', () => {
    const context = createContext();
    const {gnr} = context;
    const date = (y, m, d) => vm.runInContext(`new Date(${y}, ${m}, ${d})`, context);
    const calls = [];
    const cell = {field: 'issued', filterField: true, filterValues: ['x']};
    const pane = Object.assign(Object.create(gnr.GridColumnFilterPane.prototype), {
        cell, grid: {setColumnFilter: (c, values, range) => { calls.push(range); c.filterRange = range; }}, renderList() {}
    });
    pane.setRange(null, null);
    assert.equal(calls.length, 0);
    pane.setRange(date(2026, 4, 1), date(2026, 4, 31));
    assert.deepEqual({...calls[0]}, {from: '2026-05-01', to: '2026-05-31'});
    pane.setRange(date(2026, 4, 1), date(2026, 4, 31));
    assert.equal(calls.length, 1);
});

function fakeDocument(context) {
    const element = tag => ({
        tagName: tag, children: [], dataset: {}, hidden: false, className: '', textContent: '', title: '',
        classList: {add() {}, toggle() {}},
        listeners: {},
        addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
        attributes: {},
        setAttribute(name, value) { this.attributes[name] = value; },
        focus() { context.document.activeElement = this; },
        append(...nodes) { this.children.push(...nodes); },
        appendChild(node) { this.children.push(node); },
        replaceChildren(fragment) { this.children = fragment.children.slice(); }
    });
    Object.assign(context.document, {createElement: element, createDocumentFragment: () => element('#fragment')});
}

// twelve codes C01..C12: group x holds C01..C08, group y holds C09..C12
function createCodes() {
    const records = Array.from({length: 12}, (_, i) => ({
        code: `C${String(i + 1).padStart(2, '0')}`, group: i < 8 ? 'x' : 'y'
    }));
    const g = createGrid({records});
    g.grid.cellmap = {};
    for (const field of ['code', 'group']) {
        g.grid.cellmap[field] = filterCell(g.context, {field, field_getter: field, filterField: true});
    }
    return g;
}

function openPane(g, field, {maxRows} = {}) {
    fakeDocument(g.context);
    Object.assign(g.grid, {structCellNode: () => null, refreshColumnFilterHeaders() {}, applyColumnFilters() {}});
    if (maxRows) g.gnr.GridColumnFilterPane.prototype.maxRows = maxRows;
    const pane = new g.gnr.GridColumnFilterPane(g.grid, g.grid.cellmap[field], g.context.document.createElement('div'));
    const rows = () => pane.listNode.children.filter(n => n.className.startsWith('gcf_row'));
    const shown = () => rows().map(n => n.children[1].textContent);
    const ticked = () => rows().filter(n => n.className.includes('gcf_checked')).map(n => n.children[1].textContent);
    const search = text => { pane.search = text; pane.renderList(); };
    const values = () => (pane.cell.filterValues ? Array.from(pane.cell.filterValues) : null);
    return {pane, shown, ticked, search, values};
}

test('values with no rows under the other filters are hidden unless checked, a toggle shows them', () => {
    const g = createGrid();
    g.filter('_customer_id_name', ['C3']);
    const {pane, shown} = openPane(g, 'status');
    assert.deepEqual(shown(), ['Overdue']);
    assert.equal(pane.emptyNode.hidden, false);
    assert.ok(pane.emptyNode.textContent.includes('(2)'));
    pane.toggleEmpty();
    assert.deepEqual(shown(), ['Overdue', 'Paid', 'Sent']);
    pane.toggleEmpty();
    assert.deepEqual(shown(), ['Overdue']);
    g.filter('status', ['Paid']);
    pane.renderList();
    assert.deepEqual(shown(), ['Overdue', 'Paid']);
    assert.ok(pane.emptyNode.textContent.includes('(1)'));
    g.filter('_customer_id_name', null);
    pane.setItems(g.grid.columnFilterValues(pane.cell));
    assert.equal(pane.emptyNode.hidden, true);
});

test('the search box appears when the listed values pass the threshold', () => {
    const g = createCodes();
    g.filter('group', ['y']);
    const {pane, shown} = openPane(g, 'code');
    assert.equal(shown().length, 4);
    assert.equal(pane.searchBox.hidden, true);
    pane.toggleEmpty();
    assert.equal(shown().length, 12);
    assert.equal(pane.searchBox.hidden, false);
});

test('select all and deselect all act on the searched values only and keep the other checks', () => {
    const g = createCodes();
    g.filter('group', ['x']);
    g.filter('code', ['C11']);
    const {pane, search, values} = openPane(g, 'code');
    assert.equal(pane.deselectNode.hidden, true);
    search('C0');
    assert.equal(pane.selectNode.hidden, false);
    pane.selectAll();
    assert.deepEqual(values(), ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C11']);
    assert.equal(pane.selectNode.hidden, true);
    assert.equal(pane.deselectNode.hidden, false);
    search('C0');
    pane.deselectAll();
    assert.deepEqual(values(), ['C11']);
    search('');
    assert.equal(pane.deselectNode.hidden, true);
});

test('select all reaches the values past maxRows and leaves out the hidden ones with no rows', () => {
    const g = createCodes();
    g.filter('group', ['x']);
    const {pane, shown, values} = openPane(g, 'code', {maxRows: 3});
    assert.equal(shown().length, 3);
    assert.equal(pane.moreNode.hidden, false);
    pane.selectAll();
    assert.deepEqual(values(), ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08']);
    assert.equal(g.gnr.columnFilterActive(pane.cell), true);
});

test('every value checked leaves no filter and the popup keeps them checked', () => {
    const g = createCodes();
    const {pane, values, ticked} = openPane(g, 'code', {maxRows: 3});
    assert.equal(pane.selectNode.hidden, false);
    assert.equal(pane.deselectNode.hidden, true);
    pane.selectAll();
    assert.equal(values(), null);
    assert.equal(g.gnr.columnFilterActive(pane.cell), false);
    assert.equal(ticked().length, 12);
    assert.equal(pane.selectNode.hidden, true);
    assert.equal(pane.deselectNode.hidden, false);
    pane.deselectAll();
    assert.equal(values(), null);
    assert.deepEqual(ticked(), []);
    assert.equal(pane.deselectNode.hidden, true);
});

test('checking the last value one click at a time keeps the checks, unchecking one filters the rest', () => {
    const g = createGrid();
    const {pane, values, ticked} = openPane(g, 'status');
    const row = (idx, checked) => ({dataset: {idx: `${idx}`}, checked, parentNode: {classList: {toggle() {}}}});
    pane.toggle(row(0, true));
    pane.toggle(row(1, true));
    assert.deepEqual(values(), ['Overdue', 'Paid']);
    pane.toggle(row(2, true));
    assert.equal(values(), null);
    assert.equal(g.gnr.columnFilterActive(pane.cell), false);
    pane.renderList();
    assert.deepEqual(ticked(), ['Overdue', 'Paid', 'Sent']);
    pane.toggle(row(1, false));
    assert.deepEqual(values(), ['Overdue', 'Sent']);
    const reopened = openPane(g, 'status');
    pane.grid.setColumnFilter(pane.cell, null);
    reopened.pane.renderList();
    assert.deepEqual(reopened.ticked(), []);
});

test('the popup buttons never take the focus, so the search keeps it and the popup stays open', () => {
    const g = createCodes();
    const {pane} = openPane(g, 'code');
    for (const button of [pane.selectNode, pane.deselectNode, pane.clearNode, pane.emptyNode, pane.searchClearNode]) {
        let prevented = false;
        (button.listeners.mousedown || []).forEach(handler => handler({preventDefault() { prevented = true; }}));
        assert.equal(prevented, true, button.textContent);
    }
});

test('the clear button of the search shows with text, empties it and keeps typing there', () => {
    const g = createCodes();
    const {pane, shown} = openPane(g, 'code');
    const fire = (node, type) => (node.listeners[type] || []).forEach(handler => handler({}));
    assert.equal(pane.searchClearNode.hidden, true);
    assert.equal(pane.searchClearNode.attributes['aria-label'], 'Clear search');
    pane.searchNode.value = 'C1';
    fire(pane.searchNode, 'input');
    assert.equal(pane.searchClearNode.hidden, false);
    assert.equal(shown().length, 3);
    fire(pane.searchClearNode, 'click');
    assert.equal(pane.searchNode.value, '');
    assert.equal(pane.search, '');
    assert.equal(shown().length, 12);
    assert.equal(pane.searchClearNode.hidden, true);
    assert.equal(g.context.document.activeElement, pane.searchNode);
});
