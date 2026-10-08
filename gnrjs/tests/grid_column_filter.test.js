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
    const cell = Object.assign({original_field: attrs.field, original_name: attrs.field}, attrs);
    context.gnr.widgets.DojoGrid.prototype.setColumnFilterFields(cell);
    return cell;
}

// a NewIncludedView over an attributes store with three filterable columns
function createGrid({virtual = false, condition = null} = {}) {
    const context = createContext();
    const {gnr} = context;
    const data = new gnr.GnrBag();
    const rows = new gnr.GnrBag();
    INVOICES.forEach((row, i) => rows.setItem(`r_${i}`, null, Object.assign({_pkey: `I${i}`}, row)));
    data.setItem('grid.store', rows);
    const storeNode = {
        getRelativeData: p => data.getItem(p),
        setRelativeData: (p, v) => data.setItem(p, v),
        getAttributeFromDatasource: name => (name === 'condition' ? condition : null)
    };
    const storeClass = virtual ? gnr.stores.VirtualSelection : gnr.stores.AttributesBagRows;
    const store = Object.assign(Object.create(storeClass.prototype), {storeNode, storepath: 'grid.store', identifier: '_pkey'});
    const grid = {};
    const proto = gnr.widgets.NewIncludedView.prototype;
    for (const k in proto) {
        if (k.startsWith('mixin_')) grid[k.slice(6)] = proto[k];
    }
    Object.assign(grid, {
        _collectionStore: store,
        collectionStore: () => store,
        datamode: 'attr',
        sourceNode: {attr: {}, evaluateOnNode: attr => attr},
        cellmap: {
            _customer_id_name: filterCell(context, {field: '_customer_id_name', original_field: '@customer_id.name',
                                                    field_getter: '_customer_id_name', filterField: 'customer_id'}),
            status: filterCell(context, {field: 'status', field_getter: 'status', filterField: true}),
            agent: filterCell(context, {field: 'agent', field_getter: 'agent', filterField: '@customer_id.agent_id'})
        }
    });
    store._linkedGrids = [grid];
    const filter = (field, values) => { grid.cellmap[field].filterValues = values; };
    const visible = () => {
        store.createFiltered(grid, null, null, null);
        return store._filtered ? Array.from(store._filtered, i => `I${i}`) : INVOICES.map((r, i) => `I${i}`);
    };
    const counts = field => {
        let result;
        grid.columnFilterValues(grid.cellmap[field], items => { result = items; });
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

test('filter fields: row key, query field and caption', () => {
    const context = createContext();
    const related = filterCell(context, {field: '_customer_id_name', original_field: '@customer_id.name', filterField: 'customer_id'});
    assert.equal(related.filterField_key, 'customer_id');
    assert.equal(related.filterField_query, '$customer_id');
    assert.equal(related.filterField_caption, '@customer_id.name');
    const own = filterCell(context, {field: 'status', filterField: true});
    assert.equal(own.filterField_key, 'status');
    assert.equal(own.filterField_query, '$status');
    assert.equal(own.filterField_caption, null);
    const fkey = filterCell(context, {field: 'customer_id', caption_field: '@customer_id.name', filterField: true});
    assert.equal(fkey.filterField_key, 'customer_id');
    assert.equal(fkey.filterField_caption, '@customer_id.name');
    const path = filterCell(context, {field: 'agent', filterField: '@customer_id.agent_id'});
    assert.equal(path.filterField_key, '_customer_id_agent_id');
    assert.equal(path.filterField_query, '@customer_id.agent_id');
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
    assert.equal(g.grid.hasClientColumnFilters(), true);
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
    let items;
    g.grid.columnFilterValues(g.grid.cellmap._customer_id_name, result => { items = result; });
    assert.deepEqual(Array.from(items, i => [i.value, i.caption, i.count]),
                     [['C1', 'Rossi', 2], ['C2', 'Verdi', 2], ['C3', 'Rossi', 1]]);
});

test('server condition uses parameters and IS NULL for the empty value', () => {
    const g = createGrid({virtual: true});
    g.filter('status', ['Paid', 'Sent']);
    g.filter('agent', ['A1', null]);
    const params = {};
    assert.equal(g.grid.columnFilterCondition(null, params),
                 '( $status IN :colfilter_status ) AND ( @customer_id.agent_id IN :colfilter_customer_id_agent_id OR @customer_id.agent_id IS NULL )');
    assert.deepEqual(JSON.parse(JSON.stringify(params)), {colfilter_status: ['Paid', 'Sent'], colfilter_customer_id_agent_id: ['A1']});
    assert.equal(g.grid.columnFilterCb(), null);
    assert.equal(g.grid.hasClientColumnFilters(), false);
});

test('a virtual store ANDs the column filters to its condition', () => {
    const g = createGrid({virtual: true, condition: '$year = :year'});
    assert.deepEqual({...g.store.columnFilterRunKwargs({a: 1})}, {a: 1});
    g.filter('status', ['Paid']);
    const kw = g.store.columnFilterRunKwargs({a: 1});
    assert.equal(kw.condition, '( $year = :year ) AND ( $status IN :colfilter_status )');
    assert.deepEqual(Array.from(kw.colfilter_status), ['Paid']);
    assert.equal(kw.a, 1);
    assert.equal(g.store.columnFilterRunKwargs({condition: null}).condition, '( $status IN :colfilter_status )');
});
