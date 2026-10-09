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
        toJson: JSON.stringify,
        isIE: 0,
        mixin: Object.assign,
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'gnrstores.js', 'genro_widgets.js', 'genro_components.js', 'genro_grid.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    return context;
}

const context = createContext();
const Bag = context.gnr.GnrBag;

const cellmap = {
    provincia: {field: 'provincia', original_field: 'provincia', field_getter: 'sigla'},
    qty: {field: 'qty', original_field: 'qty', field_getter: 'qty'}
};

const rows = [
    {provincia: 'MI', sigla: 'Milano', qty: 4},
    {provincia: 'CO', sigla: 'Como', qty: 4},
    {provincia: 'MI', sigla: 'Milano', qty: 7}
];

function bagRows(values) {
    const data = new Bag();
    values.forEach((row, i) => data.setItem('r_' + i, new Bag(row)));
    return data;
}

function attrRows(values) {
    const data = new Bag();
    values.forEach((row, i) => data.setItem('r_' + i, null, Object.assign({_pkey: 'r_' + i}, row)));
    return data;
}

//the grid methods the function relies on, taken from the real widget class
function grid(widgetClass, datamode, data, storeClass) {
    const proto = context.gnr.widgets[widgetClass].prototype;
    const result = {datamode, cellmap, storebag: () => data,
                    rowFromBagNode: proto.mixin_rowFromBagNode,
                    distinctColumnValues: proto.mixin_distinctColumnValues};
    if (storeClass) {
        const store = Object.create(context.gnr.stores[storeClass].prototype);
        store.identifier = '_pkey';
        result.collectionStore = () => store;
    }
    return result;
}

test('datamode bag reads the row values', () => {
    assert.equal(grid('NewIncludedView', 'bag', bagRows(rows), 'ValuesBagRows').distinctColumnValues('provincia'),
                 'MI:Milano,CO:Como');
    assert.equal(grid('IncludedView', 'bag', bagRows(rows)).distinctColumnValues('qty'), '4,7');
});

test('datamode bag on rows carried by attributes reads the attributes', () => {
    assert.equal(grid('IncludedView', 'bag', attrRows(rows)).distinctColumnValues('provincia'), 'MI:Milano,CO:Como');
});

test('datamode attr keeps reading the row attributes', () => {
    assert.equal(grid('IncludedView', 'attr', attrRows(rows)).distinctColumnValues('provincia'), 'MI:Milano,CO:Como');
    assert.equal(grid('NewIncludedView', 'attr', attrRows(rows), 'Selection').distinctColumnValues('provincia'),
                 'MI:Milano,CO:Como');
});

test('a column missing from the grid and an empty store give no values', () => {
    assert.equal(grid('IncludedView', 'bag', bagRows(rows)).distinctColumnValues('missing'), '');
    assert.equal(grid('IncludedView', 'bag', new Bag()).distinctColumnValues('provincia'), '');
});

test('a caption with a comma is joined so that the values parser keeps it whole', () => {
    const values = grid('NewIncludedView', 'attr', attrRows([{provincia: 'MB', sigla: 'Monza, Brianza'},
                                                             {provincia: 'CO', sigla: 'Como'}]), 'Selection')
        .distinctColumnValues('provincia');
    const store = context.gnr.widgets.BaseCombo.prototype.storeFromValues(values);
    const parsed = Array.from(store.mainbag.getItem('root').getNodes(), n => [n.attr.id, n.attr.caption]);
    assert.deepEqual(parsed, [['MB', 'Monza, Brianza'], ['CO', 'Como']]);
});
