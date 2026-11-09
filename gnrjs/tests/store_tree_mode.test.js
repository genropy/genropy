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
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        indexOf: (items, item) => Array.prototype.indexOf.call(items || [], item),
        toJson: JSON.stringify,
        isIE: 0,
        require() {},
        provide() {},
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js', 'genro_components.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

const ROWS = [['t', 'Tools', 10], ['h', 'Tools/Hammers', 4], ['c', 'Tools/Hammers/Claw', 1],
              ['s', 'Tools/Saws', 6], ['p', 'Paint', 3], ['x', 'Garden/Hoses/Long', 7]];

//flat rows as a selection brings them, the hierarchy in their path column
function createStore({rows = ROWS, separator = '/', storeClass = 'AttributesBagRows'} = {}) {
    const context = createContext();
    const Bag = context.gnr.GnrBag;
    const root = new Bag();
    for (const [pkey, rowPath, population] of rows) {
        const attr = {_pkey: pkey, path: rowPath, population};
        if (storeClass == 'ValuesBagRows') {
            root.setItem(pkey, new Bag(attr));
        } else {
            root.setItem(pkey, null, attr);
        }
    }
    root.setBackRef();
    const store = Object.create(context.gnr.stores[storeClass].prototype);
    Object.assign(store, {identifier: '_pkey', storeNode: {getRelativeData: () => root}, _filtered: null,
                          _linkedGrids: []});
    store.setTreeMode({field: 'path', hierarchical: separator});
    return {store, root, context};
}

const keys = store => [...store.getItems()].map(n => store.keyGetter(n));
const keyIndex = (store, key) => store.getIdxFromPkey(key);
const row = (store, key) => store.rowByIndex(keyIndex(store, key));

//a grid as toggleNode drives it: index selection, and the selectedId it publishes
function attachGrid(store) {
    const grid = {
        selected: [],
        published: [],
        selection: {
            getSelected: () => grid.selected.slice(),
            getFirstSelected: () => grid.selected.length ? grid.selected[0] : -1,
            beginUpdate() {},
            endUpdate() {},
            unselectAll() { grid.selected = []; },
            addToSelection(idx) { grid.selected.push(idx); }
        },
        updateRowCount() {},
        _gnrUpdateSelect(idx) { grid.published.push(idx); }
    };
    store._linkedGrids = [grid];
    return grid;
}

test('a collapsed tree lists the first segment of the paths', () => {
    const {store} = createStore();
    assert.deepEqual(keys(store), ['t', 'p', '_tree_Garden']);
    const tools = row(store, 't');
    assert.equal(tools._tree_level, 0);
    assert.equal(tools._tree_label, 'Tools');
    assert.equal(tools._tree_branch, true);
    assert.equal(tools._tree_expanded, false);
    assert.equal(row(store, 'p')._tree_branch, false);
});

test('expanding shows the children depth-first, labelled by their last segment', () => {
    const {store} = createStore();
    store.toggleNode(0);
    store.toggleNode(keyIndex(store, 'h'));
    assert.deepEqual(keys(store), ['t', 'h', 'c', 's', 'p', '_tree_Garden']);
    const claw = row(store, 'c');
    assert.equal(claw._tree_level, 2);
    assert.equal(claw._tree_label, 'Claw');
    assert.equal(claw.path, 'Tools/Hammers/Claw');
});

test('ancestors missing from the rows become virtual rows', () => {
    const {store} = createStore();
    const garden = row(store, '_tree_Garden');
    assert.equal(garden._tree_virtual, true);
    assert.equal(garden._tree_label, 'Garden');
    assert.equal(garden.path, 'Garden');
    assert.equal(garden.population, undefined);
    store.toggleNode(keyIndex(store, '_tree_Garden'));
    store.toggleNode(keyIndex(store, '_tree_Garden/Hoses'));
    assert.deepEqual(keys(store), ['t', 'p', '_tree_Garden', '_tree_Garden/Hoses', 'x']);
    assert.equal(row(store, 'x')._tree_virtual, false);
    assert.equal(row(store, 'x')._tree_level, 2);
});

test('any character separates the levels', () => {
    const {store} = createStore({separator: '.', rows: [['a', '1', 1], ['b', '1.1', 2], ['c', '1.1.2', 3], ['d', '2', 4]]});
    store.toggleNode(0);
    store.toggleNode(keyIndex(store, 'b'));
    assert.deepEqual(keys(store), ['a', 'b', 'c', 'd']);
    assert.equal(row(store, 'c')._tree_label, '2');
});

test('a row without a path is a root', () => {
    const {store} = createStore({rows: [['a', 'A', 1], ['n', null, 2]]});
    assert.deepEqual(keys(store), ['a', 'n']);
    assert.equal(row(store, 'n')._tree_level, 0);
});

test('rows sharing a path are siblings, the first one holds the children', () => {
    const {store} = createStore({rows: [['a', 'A', 1], ['a2', 'A', 2], ['b', 'A/B', 3]]});
    assert.deepEqual(keys(store), ['a', 'a2']);
    assert.equal(row(store, 'a')._tree_branch, true);
    assert.equal(row(store, 'a2')._tree_branch, false);
    store.toggleNode(0);
    assert.deepEqual(keys(store), ['a', 'a2', 'b']);
});

test('a collapsed parent hides its subtree and reopens it as it was', () => {
    const {store} = createStore();
    store.toggleNode(0);
    store.toggleNode(keyIndex(store, 'h'));
    store.toggleNode(0);
    assert.deepEqual(keys(store), ['t', 'p', '_tree_Garden']);
    store.toggleNode(0);
    assert.deepEqual(keys(store), ['t', 'h', 'c', 's', 'p', '_tree_Garden']);
});

test('sort orders the siblings of every level', () => {
    const {store} = createStore();
    store.toggleNode(0);
    store.sort('population:d');
    assert.deepEqual(keys(store), ['t', 's', 'h', '_tree_Garden', 'p']);
});

test('a branch sorts by its own row, not by its children', () => {
    const {store} = createStore({rows: [['t', 'Tools', 1], ['h', 'Tools/Hammers', 100], ['p', 'Paint', 3]]});
    store.sort('population:d');
    assert.deepEqual(keys(store), ['p', 't']);
});

test('a numeric path segment zero is a path, not an empty value', () => {
    const {store} = createStore({separator: '.', rows: [['z', 0, 1], ['a', 1, 2]]});
    assert.equal(row(store, 'z')._tree_label, '0');
});

test('the filtered data follows the visible rows of the tree', () => {
    const {store} = createStore();
    store.toggleNode(0);
    store._filtered = [1, 2];
    assert.deepEqual([...store.getData(true).getNodes()].map(n => n.attr._pkey), ['h', 's']);
});

test('the open nodes survive a reload of the rows', () => {
    const {store, root, context} = createStore();
    store.toggleNode(0);
    const reloaded = new context.gnr.GnrBag();
    for (const n of root.getNodes()) {
        reloaded.setItem(n.label, null, Object.assign({}, n.attr));
    }
    store.storeNode = {getRelativeData: () => reloaded};
    assert.deepEqual(keys(store), ['t', 'h', 's', 'p', '_tree_Garden']);
});

test('a filter indexes the visible rows', () => {
    const {store} = createStore();
    store.toggleNode(0);
    store._filtered = [1, 2];
    assert.equal(store.len(true), 2);
    assert.equal(store.getKeyFromIdx(1, true), 's');
    assert.equal(store.getIdxFromPkey('s'), 1);
    assert.equal(store.getIdxFromPkey('s', false), 2);
});

test('expanding marks the filter to rebuild', () => {
    const {store} = createStore();
    store._filtered = [0];
    store._filterToRebuild = false;
    store.toggleNode(0);
    assert.equal(store.invalidFilter(), true);
});

test('collapsing a node moves the selection from its subtree onto it', () => {
    const {store} = createStore();
    const grid = attachGrid(store);
    store.toggleNode(0);
    store.toggleNode(keyIndex(store, 'h'));
    grid.selected = [keyIndex(store, 'c'), keyIndex(store, 'p')];
    store.toggleNode(0);
    assert.deepEqual(grid.selected.map(idx => store.getKeyFromIdx(idx)), ['t', 'p']);
    assert.equal(grid.published.length, 1);
});

test('expanding keeps the selection on its rows and publishes nothing', () => {
    const {store} = createStore();
    const grid = attachGrid(store);
    grid.selected = [keyIndex(store, 'p')];
    store.toggleNode(0);
    assert.deepEqual(grid.selected.map(idx => store.getKeyFromIdx(idx)), ['p']);
    assert.deepEqual(grid.published, []);
});

test('collapsing a virtual node drops the selection inside it', () => {
    const {store} = createStore();
    const grid = attachGrid(store);
    store.toggleNode(keyIndex(store, '_tree_Garden'));
    store.toggleNode(keyIndex(store, '_tree_Garden/Hoses'));
    grid.selected = [keyIndex(store, 'x')];
    store.toggleNode(keyIndex(store, '_tree_Garden'));
    assert.deepEqual(grid.selected, []);
    assert.equal(grid.published.length, 1);
});

test('virtual rows are told apart from the real ones', () => {
    const {store} = createStore();
    assert.equal(store.isVirtualRow(keyIndex(store, '_tree_Garden')), true);
    assert.equal(store.isVirtualRow(keyIndex(store, 't')), false);
});

test('rows kept in the node values build the same tree', () => {
    const {store} = createStore({storeClass: 'ValuesBagRows'});
    store.toggleNode(0);
    assert.deepEqual(keys(store), ['t', 'h', 's', 'p', '_tree_Garden']);
    assert.equal(row(store, 'h')._tree_label, 'Hammers');
});

test('without a hierarchical column the store is flat again', () => {
    const {store} = createStore();
    assert.equal(store.setTreeMode(null), true);
    assert.equal(store.isTreeStore, undefined);
    assert.equal(store.len(), 6);
    assert.equal(store.setTreeMode(null), false);
});

test('a virtual selection refuses the hierarchical column', () => {
    const context = createContext();
    const store = Object.create(context.gnr.stores.VirtualSelection.prototype);
    const warn = console.warn;
    console.warn = () => {};
    try {
        assert.equal(store.setTreeMode({field: 'path', hierarchical: '/'}), false);
    } finally {
        console.warn = warn;
    }
    assert.equal(store.isTreeStore, undefined);
});
