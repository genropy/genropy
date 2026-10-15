const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout};
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
    const gridJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js');
    vm.runInContext(readFileSync(gridJs, 'utf8'), context, {filename: 'grouplet_grid.js'});
    context._T = str => str;
    context.genro.evaluate = expr => vm.runInContext('(' + expr + ')', context);
    vm.runInContext('Math.round10 = v => Math.round(v * 1e10) / 1e10;', context);
    return context;
}

const context = loadContext();
const Bag = context.gnr.GnrBag;

function controller(totals, rows) {
    const ctrl = Object.create(context.gnr.GroupletGridController.prototype);
    ctrl.totals = totals;
    ctrl.controllerPath = 'ctrl';
    const data = {};
    ctrl.sourceNode = {
        setRelativeData: (p, v) => { data[p] = v; },
        getRelativeData: (p) => data[p],
    };
    const bag = rows === null ? null : new Bag();
    for (let i = 0; i < (rows || 0); i++) bag.setItem('r_' + i, new Bag({quantita: 1}));
    ctrl.storebag = () => bag;
    return {ctrl, data, bag};
}

test('a count entry holds the number of rows', () => {
    const s = controller([{key: 'righe', count: true}], 3);
    s.ctrl._updateCountTotals();
    assert.equal(s.data['ctrl.totalize.righe'], 3);
    s.bag.popNode('r_0');
    s.ctrl._updateCountTotals();
    assert.equal(s.data['ctrl.totalize.righe'], 2);
});

test('a record with no rows Bag counts zero', () => {
    const s = controller([{key: 'righe', count: true}], null);
    s.ctrl._updateCountTotals();
    assert.equal(s.data['ctrl.totalize.righe'], 0);
});

test('a formula can read the count', () => {
    const s = controller([{key: 'righe', count: true},
                          {key: 'doppio', formula: 'righe*2'}], 4);
    s.ctrl._updateCountTotals();
    assert.equal(s.data['ctrl.totalize.doppio'], 8);
});

test('a grid without count entries writes nothing', () => {
    const s = controller([{key: 'totale', field: 'totale'}], 2);
    s.ctrl._updateCountTotals();
    assert.deepEqual(Object.keys(s.data), []);
});

test('each entry cell carries its own attributes', () => {
    const s = controller([
        {key: 'righe', count: true, label: 'Righe', attrs: {}},
        {key: 'totale', field: 'totale', label: 'Totale', highlight: true,
         attrs: {hidden: '==c!="V"', c: '^.causale', _class: 'mine'}},
    ], 1);
    const cells = [];
    const node = {
        _(tag, attrs) {
            if (attrs._class && attrs._class.startsWith('grouplet_grid__total') && !attrs._class.includes('_label')
                    && !attrs._class.includes('_value') && attrs._class !== 'grouplet_grid__totals') {
                cells.push(attrs);
            }
            return node;
        }
    };
    context.genro.src = {newRoot: () => node};
    s.ctrl._resolveStructSlots = () => ({bottom: {}});
    s.ctrl._mountSlotContent = () => {};
    s.ctrl._containerDom = () => ({classList: {add() {}}});
    s.ctrl._mountTotals();
    assert.equal(cells.length, 2);
    assert.equal(cells[0]._class, 'grouplet_grid__total');
    assert.equal(cells[0].hidden, undefined);
    assert.equal(cells[1]._class, 'grouplet_grid__total grouplet_grid__total--highlight mine');
    assert.equal(cells[1].hidden, '==c!="V"');
    assert.equal(cells[1].c, '^.causale');
});
