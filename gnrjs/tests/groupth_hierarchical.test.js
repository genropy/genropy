const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadContext() {
    const context = {console, gnr: {}, genro: {}, setTimeout};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
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
    for (const filename of ['gnrlang.js', 'gnrbag.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const groupthJs = path.join(__dirname, '../../resources/common/th/th_groupth.js');
    vm.runInContext(readFileSync(groupthJs, 'utf8'), context, {filename: 'th_groupth.js'});
    return context;
}

const context = loadContext();
const Bag = context.gnr.GnrBag;
const groupth = vm.runInContext('genro_plugin_groupth', context);

const TYPE = '@product_type_id.hierarchical_description';
const TYPE_KEY = '_product_type_id_hierarchical_description';
const STATE = '@customer_id.state_name';
const STATE_KEY = '_customer_id_state_name';

function struct(breakCells) {
    const bag = new Bag();
    breakCells.concat([
        {field: 'amount', group_aggr: 'sum', dtype: 'N'},
        {field: 'price', group_aggr: 'avg', dtype: 'N'},
        {field: 'qty', group_aggr: 'min', dtype: 'N'},
        {field: 'qty', group_aggr: 'max', dtype: 'N'},
    ]).forEach((attr, idx) => bag.setItem('view_0.rows_0.cell_' + idx, null, attr));
    return bag;
}

function store(rows) {
    const bag = new Bag();
    rows.forEach((row, idx) => bag.setItem('r_' + idx, null, row));
    return bag;
}

function row(type, count, amount, price, qty, pkeys, extra) {
    return Object.assign({[TYPE_KEY]: type, _grp_count_sum: count, amount_sum: amount, price_avg: price,
                          qty_min: qty[0], qty_max: qty[1], _pkeylist: pkeys}, extra);
}

function labels(bag) {
    return Array.from(bag.getNodes(), n => n.label);
}

function paths(bag, prefix = '') {
    return labels(bag).flatMap(label => {
        const value = bag.getItem(label);
        return value ? [prefix + label, ...paths(value, prefix + label + '.')] : [prefix + label];
    });
}

const hierarchicalType = {field: TYPE, dtype: 'T', hierarchical_field_of: 'description'};

function sampleTree() {
    return groupth.groupTreeData(store([
        row('A', 2, 10, 5, [4, 6], 'p1,p2'),
        row('A/B', 3, 30, 10, [8, 12], 'p3,p4,p5'),
        row('A/B/C', 1, 7, 20, [20, 20], 'p6'),
        row('A/D', 4, 40, 1, [1, 2], 'p7,p8,p9,p10'),
        row('E/F', 1, 3, 2, [3, 3], 'p11'),
    ]), struct([hierarchicalType]));
}

test('a hierarchical Break builds one level per path segment', () => {
    const tree = sampleTree();
    assert.deepEqual(paths(tree), ['A', 'A.B', 'A.B.C', 'A.D', 'E', 'E.F']);
    assert.equal(tree.getAttr('A.B.C', 'description'), 'C');
    assert.equal(tree.getAttr('A.B', 'value'), 'A/B');
    assert.equal(tree.getAttr('E', 'value'), 'E');
});

test('a node total is its own rows plus its children', () => {
    const a = sampleTree().getNode('A').attr;
    assert.equal(a._grp_count_sum, 10);
    assert.equal(a.amount_sum, 87);
    assert.equal(a.price_avg, (5 * 2 + 10 * 3 + 20 * 1 + 1 * 4) / 10);
    assert.equal(a.qty_min, 1);
    assert.equal(a.qty_max, 20);
    const b = sampleTree().getNode('A.B').attr;
    assert.equal(b._grp_count_sum, 4);
    assert.equal(b.price_avg, (10 * 3 + 20 * 1) / 4);
});

test('a node without rows of its own totals its children only', () => {
    const e = sampleTree().getNode('E').attr;
    assert.equal(e._grp_count_sum, 1);
    assert.equal(e.price_avg, 2);
    assert.equal(e._pkeylist, 'p11');
});

test('the pkey list of an intermediate node covers its whole subtree', () => {
    const tree = sampleTree();
    const pkeys = p => tree.getAttr(p, '_pkeylist').split(',').sort();
    assert.deepEqual(pkeys('A'), ['p1', 'p10', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9']);
    assert.deepEqual(pkeys('A.B'), ['p3', 'p4', 'p5', 'p6']);
});

test('the empty value stays a single node', () => {
    const tree = groupth.groupTreeData(store([
        row('A/B', 1, 1, 1, [1, 1], 'p1'),
        row('N/A', 1, 1, 1, [1, 1], 'p2'),
    ]), struct([Object.assign({group_empty: 'N/A'}, hierarchicalType)]));
    assert.deepEqual(labels(tree), ['A', 'N/A']);
    assert.equal(tree.getItem('N/A'), null);
});

test('a single [NP] root with children still collapses', () => {
    const tree = groupth.groupTreeData(store([
        row('[NP]', 1, 1, 1, [1, 1], 'p1', {[STATE_KEY]: 'Tasmania'}),
        row('[NP]', 2, 2, 1, [1, 1], 'p2,p3', {[STATE_KEY]: 'Victoria'}),
    ]), struct([hierarchicalType, {field: STATE, dtype: 'T'}]));
    assert.deepEqual(labels(tree), ['Tasmania', 'Victoria']);
});

test('a single [NP] leaf at the root does not break the tree', () => {
    const tree = groupth.groupTreeData(store([row('[NP]', 1, 1, 1, [1, 1], 'p1')]), struct([hierarchicalType]));
    assert.deepEqual(labels(tree), ['[NP]']);
});

test('a Break that is not hierarchical keeps the slash inside its value', () => {
    const tree = groupth.groupTreeData(store([row('A/B', 1, 1, 1, [1, 1], 'p1')]), struct([{field: TYPE, dtype: 'T'}]));
    assert.deepEqual(labels(tree), ['A/B']);
});

test('averages rolled into an empty accumulator stay weighted', () => {
    const totals = {};
    groupth.updateTotalsAttr(totals, {price_avg: 10, _grp_count_sum: 1});
    groupth.updateTotalsAttr(totals, {price_avg: 1, _grp_count_sum: 9});
    assert.equal(totals.price_avg, (10 + 9) / 10);
    assert.equal(totals._grp_count_sum, 10);
});
