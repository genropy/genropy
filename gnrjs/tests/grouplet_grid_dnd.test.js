const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

class Surface {
    constructor(parent = null) {
        this.parentNode = parent;
        this.listeners = new Map();
        this.attributes = new Map();
        const classes = new Set();
        this.classList = {
            add: (...names) => names.forEach(n => classes.add(n)),
            remove: (...names) => names.forEach(n => classes.delete(n)),
            contains: name => classes.has(name)
        };
    }
    setAttribute(name, value) { this.attributes.set(name, value); }
    removeAttribute(name) { this.attributes.delete(name); }
    addEventListener(type, callback) {
        if (!this.listeners.has(type)) this.listeners.set(type, new Set());
        this.listeners.get(type).add(callback);
    }
    removeEventListener(type, callback) {
        this.listeners.get(type)?.delete(callback);
    }
    contains(node) {
        return !!node && (node === this || this.contains(node.parentNode));
    }
    dispatch(type, transfer, target = this, relatedTarget = null) {
        const e = {dataTransfer: transfer, target, relatedTarget,
            preventDefault() { this.defaultPrevented = true; },
            stopPropagation() { this.stopped = true; }};
        for (let dom = this; dom && !e.stopped; dom = dom.parentNode) {
            e.currentTarget = dom;
            for (const callback of dom.listeners.get(type) || []) callback(e);
        }
        return e;
    }
}

function setup() {
    const document = new Surface();
    document.body = new Surface();
    document.getElementById = () => null;
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, document};
    context.dojo = {
        Deferred: function() {}, eval, isIE: 0, toJson: JSON.stringify,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, cb) => Array.prototype.forEach.call(items || [], cb),
        some: (items, cb) => Array.prototype.some.call(items || [], cb),
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_dom.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const gridJs = process.env.GNR_GROUPLET_SOURCE || path.join(__dirname,
        '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js');
    vm.runInContext(readFileSync(gridJs, 'utf8'), context, {filename: 'grouplet_grid.js'});
    const controllers = {};
    const published = [];
    let counter = 0;
    Object.assign(context.genro, {
        time36Id: () => 'new_' + (++counter),
        nodeById: id => ({gridController: controllers[id]}),
        publish(topic, payload) {
            published.push(payload);
            Object.values(controllers).find(c => c.actionTopic === topic)._handleAction(payload);
        },
        dom: {
            setDomNodeDisabled: context.gnr.GnrDomHandler.prototype.setDomNodeDisabled,
            setInDataTransfer: (dt, key, value) => dt.setData(key, JSON.stringify(value)),
            getFromDataTransfer: (dt, key) => dt.getData(key) ? JSON.parse(dt.getData(key)) : null
        }
    });
    const Bag = context.gnr.GnrBag;
    function grid(id, {code = 'details', parent = null, ...kw} = {}) {
        const body = new Surface(parent);
        const container = new Surface();
        const rows = new Bag();
        rows.setBackRef();
        const c = Object.create(context.gnr.GroupletGridController.prototype);
        Object.assign(c, {
            nodeId: id, dragCode: code, layout: 'cards', additem: true,
            tiles: {}, _tabsByPkey: {}, _chipDnDHandlers: {}, minRows: 0,
            store: {getData: () => rows}, bodyNode: {getDomNode: () => body},
            sourceNode: {getFormHandler: () => c.form,
                getAttributeFromDatasource: name => c[name]},
            actionTopic: 'action_' + id, updateCounterColumn() {},
            _containerDom: () => container, ...kw
        });
        c.dataStore = new context.gnr.GroupletDataStore(c, {storepath: id});
        c.dnd = new context.gnr.GroupletGridDnD(c);
        controllers[id] = c;
        c._wireBodyDnD?.();
        return {c, body, rows};
    }
    function seed(grid, key = 'r_a') {
        const row = new Bag({title: 'Full row', qty: 2, extra: new Bag({note: 'Keep me'})});
        row.getNode('qty').setAttr({unit: 'days'});
        grid.rows.setItem(key, row, {_pkey: key, marker: 'preserved'});
        return row;
    }
    function start(grid, key = 'r_a') {
        const values = {};
        const dt = {
            get types() { return Object.keys(values); },
            setData: (key, value) => { values[key] = value; },
            getData: key => values[key] || ''
        };
        const dom = new Surface();
        grid.c.dnd.tileDragStart({dataTransfer: dt, preventDefault() {}, stopPropagation() {}}, dom, key);
        return dt;
    }
    return {context, grid, seed, start, published, document};
}

for (const surface of ['body', 'entry', 'phantom', 'plus']) {
    test(`drop on ${surface} moves the entire real Bag once and leaves the draft untouched`, () => {
        const s = setup();
        const src = s.grid('src');
        const dst = s.grid('dst');
        const value = s.seed(src);
        const draft = new s.context.gnr.GnrBag({title: 'Uncommitted draft'});
        dst.c.entryPath = 'draft';
        s.context.genro.getData = () => draft;
        let removed = 0;
        src.rows.subscribe('count', {del: () => removed++});
        let dom = dst.body;
        if (surface === 'entry' || surface === 'phantom') {
            dom = new Surface();
            const Tile = surface === 'entry' ? s.context.gnr.GroupletGridEntryTile
                : s.context.gnr.GroupletGridPhantomTile;
            const tile = new Tile(dst.c);
            dst.c[surface === 'entry' ? 'entryTile' : 'phantomTile'] = tile;
            tile._wrapperKw().onCreated(dom);
        } else if (surface === 'plus') {
            dom = dst.c.addBtnDom = new Surface();
            dst.c._wireAddBtnDnD();
        }
        const dt = s.start(src);
        const over = dom.dispatch('dragover', dt);
        assert.equal(over.defaultPrevented, true);
        assert.equal(dom.classList.contains('canBeDropped'), true);
        dom.dispatch('drop', dt);
        assert.equal(src.rows.len(), 0);
        assert.equal(dst.rows.getItem('r_a'), value);
        assert.equal(value.getItem('extra.note'), 'Keep me');
        assert.equal(value.getNode('qty').attr.unit, 'days');
        assert.equal(dst.rows.getNode('r_a').attr.marker, 'preserved');
        assert.equal(value.getParentNode(), dst.rows.getNode('r_a'));
        assert.equal(removed, 1);
        assert.equal(draft.getItem('title'), 'Uncommitted draft');
        assert.equal(dom.classList.contains('canBeDropped'), false);
        dom.dispatch('drop', dt);
        assert.equal(removed, 1);
        assert.equal(s.published.length, 1);
    });
}

test('body appends after existing rows; row drops still insert after their target', () => {
    const s = setup();
    const src = s.grid('src');
    const dst = s.grid('dst');
    s.seed(src);
    s.seed(dst, 'r_b');
    s.seed(dst, 'r_c');
    dst.body.dispatch('drop', s.start(src));
    assert.deepEqual([...dst.rows.keys()], ['r_b', 'r_c', 'r_a']);
    const row = new Surface(dst.body);
    row.addEventListener('drop', e => dst.c.dnd.tileDrop(e, row, 'r_b'));
    row.dispatch('drop', s.start(dst));
    assert.deepEqual([...dst.rows.keys()], ['r_b', 'r_a', 'r_c']);
    dst.body.dispatch('drop', s.start(dst));
    assert.deepEqual([...dst.rows.keys()], ['r_b', 'r_c', 'r_a']);
});

test('nested receivers accept details but bubble an item drag to its own level', () => {
    const s = setup();
    const details = s.grid('details');
    const items = s.grid('items', {code: 'items'});
    const outer = s.grid('outer', {code: 'items'});
    s.seed(details);
    s.seed(items, 'item_a');
    s.seed(outer, 'item_b');
    const outerRow = new Surface(outer.body);
    outerRow.addEventListener('dragover', e => outer.c.dnd.tileDragOver(e, outerRow));
    outerRow.addEventListener('drop', e => outer.c.dnd.tileDrop(e, outerRow, 'item_b'));
    const inner = s.grid('inner', {parent: outerRow});
    const dt = s.start(details);
    inner.body.dispatch('dragover', dt);
    assert.equal(inner.body.classList.contains('canBeDropped'), true);
    assert.equal(outerRow.classList.contains('canBeDropped'), false);
    inner.body.dispatch('drop', dt);
    assert.equal(inner.rows.len(), 1);
    const itemDt = s.start(items, 'item_a');
    inner.body.dispatch('dragover', itemDt);
    assert.equal(inner.body.classList.contains('canBeDropped'), false);
    assert.equal(outerRow.classList.contains('canBeDropped'), true);
    inner.body.dispatch('drop', itemDt);
    assert.deepEqual([...outer.rows.keys()], ['item_b', 'item_a']);
    assert.equal(inner.rows.len(), 1);
});

test('foreign and default isolated drag codes and external data cannot move rows', () => {
    const s = setup();
    for (const code of ['other', 'grpgrid_isolated']) {
        const src = s.grid('src_' + code, {code});
        s.seed(src);
        const dst = s.grid('dst_' + code);
        const dt = s.start(src);
        const e = dst.body.dispatch('dragover', dt);
        assert.ok(!e.defaultPrevented && !e.stopped);
        dst.body.dispatch('drop', dt);
        assert.equal(dst.rows.len(), 0);
        assert.equal(dst.body.classList.contains('canBeDropped'), false);
    }
    const dst = s.grid('external');
    const dt = {types: ['text/plain'], getData: () => 'unrelated'};
    dst.body.dispatch('dragover', dt);
    dst.body.dispatch('drop', dt);
    assert.equal(dst.rows.len(), 0);
    assert.equal(s.published.length, 0);
});

for (const constraint of ['locked target', 'locked source', 'disabled', 'maxRows', 'minRows', 'additem']) {
    test(`${constraint} blocks feedback and movement even if it changes during the drag`, () => {
        const s = setup();
        const src = s.grid('src');
        const dst = s.grid('dst');
        s.seed(src);
        const dt = s.start(src);
        dst.body.dispatch('dragover', dt);
        assert.equal(dst.body.classList.contains('canBeDropped'), true);
        if (constraint === 'locked target') dst.c.form = {isDisabled: () => true};
        if (constraint === 'locked source') src.c.form = {isDisabled: () => true};
        if (constraint === 'disabled') dst.c.disabled = true;
        if (constraint === 'maxRows') { dst.c.maxRows = 1; s.seed(dst, 'full'); }
        if (constraint === 'minRows') src.c.minRows = 1;
        if (constraint === 'additem') dst.c.additem = false;
        const over = dst.body.dispatch('dragover', dt);
        assert.ok(!over.defaultPrevented);
        assert.equal(dst.body.classList.contains('canBeDropped'), false);
        dst.body.dispatch('drop', dt);
        assert.equal(src.rows.len(), 1);
        assert.ok(!dst.rows.getNode('r_a'));
    });
}

test('a full grid can reorder its own rows and handles a key collision on cross-grid moves', () => {
    const s = setup();
    const src = s.grid('src');
    const dst = s.grid('dst', {maxRows: 2});
    s.seed(src);
    const previous = s.seed(dst);
    dst.body.dispatch('drop', s.start(src));
    assert.equal(dst.rows.getItem('r_a'), previous);
    assert.equal(dst.rows.len(), 2);
    dst.body.dispatch('drop', s.start(dst));
    assert.deepEqual([...dst.rows.keys()], ['new_1', 'r_a']);
});

test('leave, cancel, dragend, drop and teardown clear the actual receiver and document listeners', () => {
    const s = setup();
    const src = s.grid('src');
    const dst = s.grid('dst');
    s.seed(src);
    for (const finish of ['leave', 'cancel', 'dragend', 'drop', 'teardown']) {
        const dt = s.start(src);
        dst.body.dispatch('dragover', dt);
        if (finish === 'leave') dst.body.dispatch('dragleave', dt);
        if (finish === 'cancel') {
            for (const cb of s.document.listeners.get('keydown')) cb({key: 'Escape'});
        }
        if (finish === 'dragend' || finish === 'drop') s.document.dispatch(finish, dt);
        if (finish === 'teardown') dst.c.dnd.destroy();
        assert.equal(dst.body.classList.contains('canBeDropped'), false, finish);
        s.context.gnr.GroupletGridDnD.endDrag();
        for (const callbacks of s.document.listeners.values()) assert.equal(callbacks.size, 0);
    }
    for (const callbacks of dst.body.listeners.values()) assert.equal(callbacks.size, 0);
});

test('entry child transitions keep feedback; switching to tabs removes the body receiver', () => {
    const s = setup();
    const src = s.grid('src');
    const dst = s.grid('dst');
    s.seed(src);
    const entry = new Surface();
    dst.c.dnd.wireAppendTarget(entry);
    const child = new Surface(entry);
    const dt = s.start(src);
    entry.dispatch('dragover', dt, child);
    entry.dispatch('dragleave', dt, entry, child);
    assert.equal(entry.classList.contains('canBeDropped'), true);
    dst.c._teardownLayoutAffordances();
    dst.c.layout = 'tabs';
    dst.c._wireBodyDnD();
    assert.equal(dst.body.classList.contains('grouplet_grid_body--drop'), false);
    assert.ok(!dst.body.dispatch('dragover', dt).defaultPrevented);
    dst.c.layout = 'cards';
    dst.c._wireBodyDnD();
    dst.c._wireBodyDnD();
    assert.equal(dst.body.listeners.get('drop').size, 1);
    assert.equal(dst.body.dispatch('dragover', dt).defaultPrevented, true);
});

test('a body rebuilt during the initial row sync receives drops and releases the old listeners', () => {
    const s = setup();
    const src = s.grid('src');
    const dst = s.grid('dst');
    s.seed(src);
    s.seed(dst, 'existing');
    const rebuilt = new Surface();
    let current = dst.body;
    Object.assign(dst.c.bodyNode, {
        getDomNode: () => current,
        freeze() {},
        unfreeze() { current = rebuilt; }
    });
    dst.c._renderTile = () => {};
    dst.c._fullSync();
    const dt = s.start(src);
    assert.ok(!dst.body.dispatch('dragover', dt).defaultPrevented);
    assert.equal(rebuilt.dispatch('dragover', dt).defaultPrevented, true);
    rebuilt.dispatch('drop', dt);
    assert.deepEqual([...dst.rows.keys()], ['existing', 'r_a']);
    assert.equal(src.rows.len(), 0);
});


test('sourceNode.setDisabled uses the external widget contract and clears a pending receiver', () => {
    const s = setup();
    const src = s.grid('src');
    const dst = s.grid('dst');
    s.seed(src);
    const dt = s.start(src);
    dst.body.dispatch('dragover', dt);
    dst.c.sourceNode.externalWidget = dst.c;
    const setDisabled = s.context.gnr.GnrDomSourceNode.prototype.setDisabled;
    setDisabled.call(dst.c.sourceNode, 'test');
    assert.equal(dst.c._containerDom().disabled, true);
    assert.equal(dst.body.classList.contains('canBeDropped'), false);
    dst.body.dispatch('drop', dt);
    assert.equal(src.rows.len(), 1);
    setDisabled.call(dst.c.sourceNode, false);
    assert.equal(dst.c._containerDom().disabled, false);
    dst.body.dispatch('drop', dt);
    assert.equal(dst.rows.len(), 1);
});
