const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const calls = [];
    const context = {console, File: function() {}, gnr: {}, setTimeout, navigator: {}, window: {}, document: {}};
    context.genro = {
        serverCall: (method, params) => { calls.push({method, params}); return 'tree'; },
        setData() {},
        publish() {}
    };
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js', 'genro_components.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    return {context, calls, handler: context.gnr.widgets.HierarchicalSelect.prototype};
}

// the widget built on a stub node: what reached the inner dbSelect, and a way to open its menu
function buildOnTable(kw, datastore) {
    const env = createContext();
    const built = {};
    const chain = (tag, attrs) => {
        built[tag] = attrs;
        return {_: chain, getParentNode: () => selectNode};
    };
    const selectNode = {
        widget: {domNode: {offsetWidth: 100}},
        evaluateOnNode: (pars) => Object.fromEntries(Object.entries(pars).map(([k, v]) =>
            [k, typeof v === 'string' && v[0] === '^' ? datastore[v.slice(2)] : v]))
    };
    const sourceNode = {getStringId: () => 'hs_1', _: chain};
    env.handler.createContent(sourceNode, Object.assign({value: '^.pkey'}, kw), null);
    const menuNode = {};
    const open = () => built.menu.connect_onOpeningPopup.call(menuNode, {popup: {domNode: {style: {}}}});
    return Object.assign(env, {built, open});
}

test('a grouped tree asks for the selected columns only, never for the whole row', () => {
    const {calls, open} = buildOnTable({table: 'adm.user', hierarchical: '$group_code',
                                        selected_group_code: '.group_code'}, {});
    open();
    assert.equal(calls[0].params.columns, '$group_code');
});

test('a grouped tree with no selected column asks for no extra column', () => {
    const {calls, open} = buildOnTable({table: 'adm.user', hierarchical: '$group_code'}, {});
    open();
    assert.equal(calls[0].params.columns, undefined);
});

test('the tree reads the store of the inner dbSelect and reloads when it changes', () => {
    const datastore = {store: 'store_a'};
    const {calls, built, open} = buildOnTable({table: 'adm.user', hierarchical: '$group_code',
                                               _storename: '^.store'}, datastore);
    assert.equal(built.dbSelect._storename, '^.store');
    open();
    open();
    datastore.store = 'store_b';
    open();
    assert.deepEqual(calls.map(c => c.params.dbstore), ['store_a', 'store_b']);
});

test('an explicit false store reaches the tree as the root store', () => {
    const {calls, built, open} = buildOnTable({table: 'adm.user', hierarchical: '$group_code',
                                               _storename: false}, {});
    assert.equal(built.dbSelect._storename, false);
    open();
    assert.equal(calls[0].params.dbstore, false);
});

test('values whose names differ only by a dot or an underscore stay apart', () => {
    const {context, handler} = createContext();
    const values = new context.gnr.GnrBag();
    values.setItem('a', null, {code: 'Q.Z', color: 'A.B'});
    values.setItem('b', null, {code: 'Q_Z', color: 'A_B'});
    values.setItem('c', null, {code: 'Q-Z', color: 'A.B'});
    const tree = handler.valuesTree({values, levels: ['color'], identifier: 'code', labelAttribute: 'code'});
    const groups = {};
    tree.getItem('root').forEach(n => {
        const leaves = groups[n.attr.hierarchical_value] = [];
        n.getValue('static').forEach(c => { leaves.push(c.attr.pkey); }, 'static');
    }, 'static');
    assert.deepEqual(groups, {'A.B': ['Q.Z', 'Q-Z'], 'A_B': ['Q_Z']});
});
