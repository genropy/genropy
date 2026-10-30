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

// an editable bag grid over rows A, B, C whose filter hides B: grid row 1 is C
function createGrid({filtered = [0, 2], selected = [1]} = {}) {
    const context = createContext();
    const {gnr, genro} = context;
    const data = new gnr.GnrBag();
    const rows = new gnr.GnrBag();
    ['A', 'B', 'C'].forEach((code, i) => {
        const row = new gnr.GnrBag();
        row.setItem('_pkey', code);
        row.setItem('qty', i);
        rows.setItem(`r_${i}`, row, {_pkey: code});
    });
    data.setItem('grid.store', rows);
    data.setBackRef();
    const serverCalls = [];
    Object.assign(genro, {
        serverCall: (method, kw) => serverCalls.push({method, kw}),
        lockScreen() {},
        assert(condition, message) { if (!condition) throw new Error(message); },
        getFrameNode() {},
        dom: {setClass() {}},
        dlg: {prompt: (title, kw) => { genro.promptkw = kw; }}
    });
    const storeNode = {
        getRelativeData: p => data.getItem(p),
        setRelativeData: (p, v) => data.setItem(p, v)
    };
    const store = Object.assign(Object.create(gnr.stores.ValuesBagRows.prototype),
        {storeNode, storepath: 'grid.store', identifier: '_pkey', _filtered: filtered});
    const grid = {};
    const proto = gnr.widgets.NewIncludedView.prototype;
    for (const k in proto) {
        if (k.startsWith('mixin_')) grid[k.slice(6)] = proto[k];
    }
    const columnInfo = new gnr.GnrBag();
    columnInfo.setItem('qty', null);
    Object.assign(grid, {
        _collectionStore: store,
        _virtual: false,
        _identifier: '_pkey',
        datamode: 'bag',
        cellmap: {qty: {field: 'qty', original_field: 'qty', edit: true, dtype: 'L'}},
        selection: {getSelected: () => selected.slice()},
        sourceNode: {attr: {storepath: 'grid.store', nodeId: 'g'}, setRelativeData() {}, publish() {}},
        getColumnInfo: () => columnInfo
    });
    const editor = Object.assign(Object.create(gnr.GridEditor.prototype), {
        grid,
        status: {},
        deletedRows: new gnr.GnrBag(),
        editorPars: {},
        remoteRowController: 'rowCtrl',
        columns: {qty: {attr: {field: 'qty', original_name: 'Qty', batch_assign: true, remoteRowController: true}}}
    });
    grid.gridEditor = editor;
    const assign = values => {
        editor.batchAssign();
        const result = new gnr.GnrBag();
        for (const [k, v] of Object.entries(values)) result.setItem(k, v);
        genro.promptkw.action(result);
    };
    return {rows, serverCalls, assign};
}

test('with a filter active the remote row controller gets the selected row', () => {
    const g = createGrid();
    g.assign({qty: 9});
    assert.equal(g.rows.getItem('r_2.qty'), 9);
    assert.equal(g.rows.getItem('r_1.qty'), 1);
    assert.equal(g.serverCalls.length, 1);
    const sent = g.serverCalls[0].kw.rows;
    assert.deepEqual([...sent.keys()], ['r_2']);
    assert.equal(sent.getItem('r_2.qty'), 9);
});

test('without a filter grid and store indexes match', () => {
    const g = createGrid({filtered: null, selected: [0, 2]});
    g.assign({qty: 7});
    assert.deepEqual([...g.serverCalls[0].kw.rows.keys()], ['r_0', 'r_2']);
    assert.equal(g.rows.getItem('r_0.qty'), 7);
    assert.equal(g.rows.getItem('r_1.qty'), 1);
    assert.equal(g.rows.getItem('r_2.qty'), 7);
});
