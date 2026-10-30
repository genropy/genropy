const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, setInterval, clearInterval,
                     navigator: {}, window: {}, document: {}};
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

// A NewIncludedView over a real store; the store bag 'del' triggers reach the grid as its ^storepath does.
// db: a Selection store (th grids, liveUpdate); bag: a ValuesBagRows store edited by a GridEditor (bagGrid).
function createGrid({kind = 'db', codes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], selected = 'C',
                     attr = {}, autoSelect, autoInsert, excluded} = {}) {
    const {gnr, genro} = createContext();
    const serverCalls = [];
    Object.assign(genro, {
        compareDict: {'==': (a, b) => a == b},
        dom: {addClass() {}, removeClass() {}, setClass() {}},
        userInfoCb: [],
        serverCall: (method, kw) => serverCalls.push({method, kw}),
        lockScreen() {},
        callAfter() {},
        getFrameNode() {}
    });
    const makeRows = list => {
        const rows = new gnr.GnrBag();
        list.forEach((code, i) => {
            if (kind == 'db') {
                rows.setItem(`r_${i}`, null, {_pkey: code});
            } else {
                const value = new gnr.GnrBag();
                value.setItem('name', code);
                rows.setItem(`r_${i}`, value, code ? {_pkey: code} : {});
            }
        });
        return rows;
    };
    const data = new gnr.GnrBag();
    const rows = makeRows(codes);
    data.setItem('grid.store', rows);
    data.setBackRef();
    const storeNode = {
        attr: {nodeId: 'g_store', table: 'test.item'},
        getAttributeFromDatasource() {},
        getRelativeData: p => data.getItem(p),
        setRelativeData: (p, v) => data.setItem(p, v)
    };
    const storeClass = kind == 'db' ? gnr.stores.Selection : gnr.stores.ValuesBagRows;
    const store = Object.assign(Object.create(storeClass.prototype),
        {storeNode, storepath: 'grid.store', identifier: '_pkey', _filtered: null, askToDelete: false});
    const selection = {index: -1};
    const grid = {};
    const proto = gnr.widgets.NewIncludedView.prototype;
    for (const k in proto) {
        if (k.startsWith('mixin_')) grid[k.slice(6)] = proto[k];
    }
    const sourceNode = Object.assign(Object.create(gnr.GnrDomSourceNode.prototype),
        {attr: {nodeId: 'g', storepath: 'grid.store', masterColumn: 'name', ...attr}});
    sourceNode.publish = () => {};
    sourceNode.setRelativeData = () => {};
    Object.assign(grid, {
        gnr: proto,
        _collectionStore: store,
        _identifier: '_pkey',
        datamode: kind == 'db' ? 'attr' : 'bag',
        cellmap: {},
        domNode: {focus() {}},
        scroller: {firstVisibleRow: 0},
        autoSelect,
        autoInsert,
        selection: {
            get selectedIndex() { return selection.index; },
            select(idx) { selection.index = idx; },
            addToSelection(idx) { selection.index = idx; },
            unselectAll() { selection.index = -1; },
            getSelected: () => (selection.index >= 0 ? [selection.index] : [])
        },
        sourceNode,
        updateRowCount() {
            if (this.invalidFilter()) this.createFiltered();
            this.rowCount = store.len(true);
        }
    });
    if (excluded) {
        Object.assign(grid, {excludeListCb: () => excluded, excludeCol: '_pkey', filteringMode: 'exclude'});
        grid.createFiltered();
    }
    if (kind == 'bag') {
        grid.gridEditor = Object.assign(Object.create(gnr.GridEditor.prototype),
            {grid, status: {}, deletedRows: new gnr.GnrBag(), _status_list: []});
    }
    store._linkedGrids = [grid];
    rows.subscribe('grid', {del: kw => grid.setStorepath(null, kw)});
    grid.updateRowCount();
    if (selected !== null) {
        grid.selection.select(grid.indexByRowAttr('_pkey', selected));
    }
    const tick = () => new Promise(resolve => setTimeout(resolve, 10));
    return {
        grid, store, rows, serverCalls, tick, makeRows,
        selected: () => (selection.index >= 0 ? grid.rowIdByIndex(selection.index) : null),
        // a db event: the rows of delKeys are deleted, the rows of leftKeys no longer match the query
        dbEvent: async ({delKeys = [], leftKeys = []}) => {
            store.checkExternalChange(delKeys, leftKeys, {}, {});
            await new Promise(resolve => setTimeout(resolve, 10));
        }
    };
}

test('the selected row leaving the query leaves no row selected', async () => {
    const g = createGrid();
    await g.dbEvent({leftKeys: ['C']});
    assert.equal(g.store.len(), 7);
    assert.equal(g.selected(), null);
});

test('the selected row deleted by another page leaves no row selected', async () => {
    const g = createGrid();
    await g.dbEvent({delKeys: ['C']});
    assert.equal(g.store.len(), 7);
    assert.equal(g.selected(), null);
});

test('with autoSelect the row taking the place of the vanished selected row gets selected', async () => {
    const g = createGrid({autoSelect: true});
    await g.dbEvent({leftKeys: ['C']});
    assert.equal(g.selected(), 'D');
});

test('a grid linked to a form selects no neighbour', async () => {
    const g = createGrid({attr: {_linkedFormId: 'f'}});
    await g.dbEvent({leftKeys: ['C']});
    assert.equal(g.selected(), null);
});

for (const autoSelect of [undefined, true]) {
    const label = autoSelect ? ' (autoSelect)' : '';
    test(`a row above the selected one leaving keeps the same row selected${label}`, async () => {
        const g = createGrid({autoSelect});
        await g.dbEvent({leftKeys: ['A']});
        assert.equal(g.selected(), 'C');
        assert.equal(g.grid.selection.selectedIndex, 1);
    });

    test(`two rows above the selected one leaving together keep the same row selected${label}`, async () => {
        const g = createGrid({autoSelect});
        await g.dbEvent({leftKeys: ['A', 'B']});
        assert.equal(g.selected(), 'C');
        assert.equal(g.grid.selection.selectedIndex, 0);
    });

    test(`a row below the selected one leaving keeps the same row selected${label}`, async () => {
        const g = createGrid({autoSelect});
        await g.dbEvent({leftKeys: ['E']});
        assert.equal(g.selected(), 'C');
        assert.equal(g.grid.selection.selectedIndex, 2);
    });
}

// B and E filtered out: the grid shows A C D F G H
test('in a filtered grid a visible row above the selected one leaving keeps the same row selected', async () => {
    const g = createGrid({excluded: ['B', 'E']});
    assert.equal(g.grid.selection.selectedIndex, 1);
    await g.dbEvent({leftKeys: ['A']});
    assert.equal(g.selected(), 'C');
    assert.equal(g.grid.selection.selectedIndex, 0);
});

test('in a filtered grid a hidden row above the selected one leaving keeps the same row selected', async () => {
    const g = createGrid({excluded: ['B', 'E']});
    await g.dbEvent({leftKeys: ['B']});
    assert.equal(g.selected(), 'C');
    assert.equal(g.grid.selection.selectedIndex, 1);
});

for (const [autoSelect, expected] of [[undefined, null], [true, 'D']]) {
    test(`in a filtered grid the selected row leaving selects ${expected || 'nothing'}${autoSelect ? ' (autoSelect)' : ''}`, async () => {
        const g = createGrid({excluded: ['B', 'E'], autoSelect});
        await g.dbEvent({leftKeys: ['C']});
        assert.equal(g.selected(), expected);
    });
}

function reload(g, codes) {
    g.grid.selectionKeeper('save');
    g.store.onLoaded(g.makeRows(codes));
    g.grid.updateRowCount();
    g.grid.restoreSelectedRows();
}

test('a reload still holding the selected row selects it by identity', () => {
    const g = createGrid();
    reload(g, ['C', 'D', 'E']);
    assert.equal(g.selected(), 'C');
    assert.equal(g.grid.selection.selectedIndex, 0);
});

for (const [autoSelect, expected] of [[undefined, null], [true, 'E']]) {
    test(`a reload without the selected row selects ${expected || 'nothing'}${autoSelect ? ' (autoSelect)' : ''}`, () => {
        const g = createGrid({autoSelect});
        reload(g, ['A', 'B', 'E', 'F']);
        assert.equal(g.selected(), expected);
    });
}

test('deleting the selected row from a db grid lands on the next row', async () => {
    const g = createGrid();
    g.grid.deleteSelectedRows();
    assert.equal(g.serverCalls[0].method, 'app.deleteDbRows');
    assert.deepEqual([...g.serverCalls[0].kw.pkeys], ['C']);
    await g.dbEvent({delKeys: ['C']});
    assert.equal(g.selected(), 'D');
});

test('deleting the selected row of a db grid with many rows lands on the next row after the reload', () => {
    const g = createGrid();
    g.grid.deleteSelectedRows();
    reload(g, ['A', 'B', 'D', 'E']);
    assert.equal(g.selected(), 'D');
});

test('deleting the selected row from a bagGrid lands on the next row', async () => {
    const g = createGrid({kind: 'bag'});
    g.grid.deleteSelectedRows();
    await g.tick();
    assert.equal(g.store.len(), 7);
    assert.equal(g.selected(), 'D');
    assert.equal(g.grid.gridEditor.deletedRows.len(), 1);
});

test('deleting the last row from a bagGrid lands on the new last row', async () => {
    const g = createGrid({kind: 'bag', selected: 'H'});
    g.grid.deleteSelectedRows();
    await g.tick();
    assert.equal(g.selected(), 'G');
});

test('a programmatic delete of a row above the selected one keeps the selection', async () => {
    const g = createGrid({kind: 'bag'});
    g.grid.gridEditor.deleteSelectedRows(['A']);
    await g.tick();
    assert.equal(g.store.len(), 7);
    assert.equal(g.selected(), 'C');
});

test('pruning the empty autoInsert row on blur keeps the selection', async () => {
    const g = createGrid({kind: 'bag', codes: ['A', 'B', 'C', 'D', ''], selected: 'B', autoInsert: true});
    g.grid.changedFocus(false);
    await g.tick();
    assert.equal(g.store.len(), 4);
    assert.equal(g.selected(), 'B');
});

test('pruning the selected empty autoInsert row on blur selects the row before it', async () => {
    const g = createGrid({kind: 'bag', codes: ['A', 'B', 'C', 'D', ''], selected: null, autoInsert: true});
    g.grid.selection.select(4);
    g.grid.changedFocus(false);
    await g.tick();
    assert.equal(g.store.len(), 4);
    assert.equal(g.selected(), 'D');
});
