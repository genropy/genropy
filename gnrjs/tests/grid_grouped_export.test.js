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

// the grouped rows as the browser holds them after a client side sort:
// rowidx is the index of each row in the selection frozen on the server
const GROUPED = [
    {rowidx: 2, _customer_id_state: 'QLD', total_sum: 900, _pkeylist: 'i7,i8,i9'},
    {rowidx: 0, _customer_id_state: 'NSW', total_sum: 700, _pkeylist: 'i1,i2,i3'},
    {rowidx: 3, _customer_id_state: 'VIC', total_sum: 500, _pkeylist: 'i10,i11'},
    {rowidx: 1, _customer_id_state: 'SA', total_sum: 100, _pkeylist: 'i4,i5,i6'}
];

// a grouped view grid over a groupByStore Selection store, loaded through the
// store's own onLoaded with the attributes getSelection answers with
function createGroupedGrid({resultAttr = {selectionName: 'grouped', totalrows: GROUPED.length}, selected = []} = {}) {
    const context = createContext();
    const {gnr, genro} = context;
    const data = new gnr.GnrBag();
    const storeNode = {
        attr: {groupByStore: true},
        getRelativeData: p => data.getItem(p),
        setRelativeData: (p, v) => (v instanceof gnr.GnrBagNode ? data.setItem(p, v.getValue(), v.attr) : data.setItem(p, v))
    };
    const store = Object.assign(Object.create(gnr.stores.Selection.prototype),
                                {storeNode, storepath: 'grid.store', identifier: '_pkey', storeType: 'Selection'});
    const rows = new gnr.GnrBag();
    GROUPED.forEach((row, i) => rows.setItem(`r_${i}`, null, Object.assign({_pkey: `r_${i}`}, row)));
    const result = new gnr.GnrBag();
    result.setItem('result', rows, resultAttr);
    store.onLoaded(result.getNode('result'));
    const calls = [];
    genro.lockScreen = () => {};
    genro.rpc = {remoteCall: (method, kwargs) => calls.push({method, kwargs})};
    const grid = {};
    const proto = gnr.widgets.NewIncludedView.prototype;
    for (const k in proto) {
        if (k.startsWith('mixin_')) grid[k.slice(6)] = proto[k];
    }
    Object.assign(grid, {
        _collectionStore: store,
        collectionStore: () => store,
        datamode: 'attr',
        sourceNode: {attr: {table: 'invc.invoice'}, getStringId: () => 'grouped_grid'},
        getExportStruct: () => 'struct',
        getSelectedRowidx: () => selected,
        getSelectedNodes: () => selected.map(i => store.currentItems()[i])
    });
    const exportKwargs = (allRows = false) => {
        grid.serverAction({command: 'export', opt: {export_mode: 'xls', rawData: true, allRows}});
        return calls.at(-1).kwargs;
    };
    return {grid, store, exportKwargs};
}

test('the grouped store keeps the selectionName getSelection answers with', () => {
    assert.equal(createGroupedGrid().store.selectionName, 'grouped');
    assert.equal(createGroupedGrid({resultAttr: {totalrows: GROUPED.length}}).store.selectionName, undefined);
});

test('exporting all the grouped rows sends the selection name, not the rows', () => {
    const {store, exportKwargs} = createGroupedGrid();
    store.sortedBy = 'total_sum:d';
    const kwargs = exportKwargs(true);
    assert.equal(kwargs.selectionName, 'grouped');
    assert.deepEqual(Array.from(kwargs.selectedRowidx), []);
    assert.equal(kwargs.sortBy, 'total_sum:d');
    assert.equal('data' in kwargs, false);
    assert.equal('limit' in kwargs, false);
});

test('the selected grouped rows are sent by their rowidx on the server', () => {
    const kwargs = createGroupedGrid({selected: [0, 2]}).exportKwargs();
    assert.equal(kwargs.selectionName, 'grouped');
    assert.deepEqual(Array.from(kwargs.selectedRowidx), [2, 3]);
    assert.equal('data' in kwargs, false);
});

test('a filtered grouped view exports its visible rows by rowidx', () => {
    const {store, exportKwargs} = createGroupedGrid();
    store._filtered = [1, 3];
    const kwargs = exportKwargs(true);
    assert.deepEqual(Array.from(kwargs.selectedRowidx), [0, 1]);
    assert.equal('data' in kwargs, false);
});

test('a grouped view filtered to no rows still exports nothing', () => {
    const {store, exportKwargs} = createGroupedGrid();
    store._filtered = [];
    const kwargs = exportKwargs(true);
    assert.equal('selectionName' in kwargs, false);
    assert.equal(kwargs.data.len(), 0);
});

test('a grouped store without a frozen selection keeps uploading its rows', () => {
    const kwargs = createGroupedGrid({resultAttr: {totalrows: GROUPED.length}}).exportKwargs(true);
    assert.equal('selectionName' in kwargs, false);
    assert.deepEqual(Array.from(kwargs.data.getNodes(), n => n.attr.rowidx), [2, 0, 3, 1]);
});
