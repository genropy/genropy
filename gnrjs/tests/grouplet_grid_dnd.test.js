const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

class Surface {
    constructor(parent = null) {
        this.parentNode = parent;
        this.children = [];
        this.style = {};
        this.className = '';
        this.clientWidth = 600;
        this.offsetHeight = 40;
        this.listeners = new Map();
        this.attributes = new Map();
        const classes = new Set();
        this.classList = {
            add: (...names) => names.forEach(n => classes.add(n)),
            remove: (...names) => names.forEach(n => classes.delete(n)),
            contains: name => classes.has(name),
            toggle: (name, on) => (on ? classes.add(name) : classes.delete(name))
        };
    }
    get nextSibling() { return this.nextElementSibling; }
    get nextElementSibling() {
        const siblings = this.parentNode ? this.parentNode.children : [];
        const i = siblings.indexOf(this);
        return i < 0 ? null : (siblings[i + 1] || null);
    }
    insertBefore(node, ref) {
        if (node.parentNode) node.remove();
        const i = ref ? this.children.indexOf(ref) : -1;
        if (i < 0) this.children.push(node); else this.children.splice(i, 0, node);
        node.parentNode = this;
        return node;
    }
    remove() {
        if (!this.parentNode) return;
        this.parentNode.children = this.parentNode.children.filter(c => c !== this);
        this.parentNode = null;
    }
    getBoundingClientRect() { return this.rect || {left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0}; }
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
    document.createElement = () => new Surface();
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
    vm.runInContext(readFileSync(path.join(path.dirname(gridJs), 'grouplet_card.js'), 'utf8'), context,
                    {filename: 'grouplet_card.js'});
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
    const slots = (body) => body.children.filter((d) => d.className === 'grouplet_grid_drop_slot').length;
    assert.equal(slots(outer.body), 1, 'the slot opens at the item level');
    assert.equal(slots(inner.body), 0);
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

test('a selected row drags the whole selection, which lands in block and in order', () => {
    const s = setup();
    const g = s.grid('g');
    ['r_a', 'r_b', 'r_c', 'r_d'].forEach(k => s.seed(g, k));
    g.c._multiKeys = ['r_c', 'r_a'];
    const onRow = (key) => {
        const row = new Surface(g.body);
        row.addEventListener('drop', e => g.c.dnd.tileDrop(e, row, key));
        return row;
    };
    onRow('r_d').dispatch('drop', s.start(g, 'r_a'));
    assert.deepEqual([...g.rows.keys()], ['r_b', 'r_d', 'r_a', 'r_c']);
    onRow('r_c').dispatch('drop', s.start(g, 'r_a'));
    assert.deepEqual([...g.rows.keys()], ['r_b', 'r_d', 'r_a', 'r_c'], 'a drop on a dragged row is none');
    onRow('r_d').dispatch('drop', s.start(g, 'r_b'));
    assert.deepEqual([...g.rows.keys()], ['r_d', 'r_b', 'r_a', 'r_c'], 'an unselected row drags alone');
    g.c._multiKeys = ['r_d', 'r_b'];
    g.body.dispatch('drop', s.start(g, 'r_b'));
    assert.deepEqual([...g.rows.keys()], ['r_a', 'r_c', 'r_d', 'r_b'], 'the body takes them to the tail');
    const published = s.published.length;
    g.body.dispatch('drop', s.start(g, 'r_d'));
    assert.equal(s.published.length, published, 'already at the tail');
});

test('a selection moves to another grid in block, within maxRows and minRows', () => {
    const s = setup();
    const src = s.grid('src');
    const dst = s.grid('dst');
    ['r_a', 'r_b', 'r_c'].forEach(k => s.seed(src, k));
    s.seed(dst, 'x');
    src.c._multiKeys = ['r_a', 'r_c'];
    dst.c.maxRows = 2;
    let dt = s.start(src, 'r_c');
    assert.ok(!dst.body.dispatch('dragover', dt).defaultPrevented, 'two rows do not fit');
    dst.body.dispatch('drop', dt);
    assert.equal(dst.rows.len(), 1);
    dst.c.maxRows = null;
    src.c.minRows = 2;
    dt = s.start(src, 'r_c');
    assert.ok(!dst.body.dispatch('dragover', dt).defaultPrevented, 'the source would keep one row');
    src.c.minRows = 0;
    dt = s.start(src, 'r_c');
    assert.equal(dst.body.dispatch('dragover', dt).defaultPrevented, true);
    dst.body.dispatch('drop', dt);
    assert.deepEqual([...dst.rows.keys()], ['x', 'r_a', 'r_c']);
    assert.deepEqual([...src.rows.keys()], ['r_b']);
});

test('the drag image of a card sits in a copy of its grid, a struct row straight in the aux box', () => {
    const s = setup();
    class Box {
        constructor() {
            this.children = [];
            this.parentNode = null;
            this.className = '';
            this.style = {cssText: '', setProperty() {}};
            this.attrs = {};
            this.classList = {remove() {}, add: (...names) => { this.className += ' ' + names.join(' '); }};
        }
        appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
        removeChild(child) { this.children = this.children.filter((c) => c !== child); child.parentNode = null; }
        setAttribute(k, v) { this.attrs[k] = v; }
        cloneNode() { const b = new Box(); b.className = this.className; return b; }
        getBoundingClientRect() { return {left: 0, top: 0}; }
    }
    const aux = new Box();
    s.document.getElementById = (id) => (id === 'auxDragImage' ? aux : null);
    s.document.createElement = () => new Box();
    const {c} = s.grid('cards');
    const container = new Box();
    container.className = 'grouplet_grid_container grouplet_grid grouplet_grid--checkbox';
    container.style.cssText = '--gg-cols: 3;';
    container.style.getPropertyValue = () => '';
    c._containerDom = () => container;
    const images = [];
    const event = {clientX: 5, clientY: 5, dataTransfer: {setDragImage: (img) => images.push(img)}};
    const card = new Box();
    card.className = 'grouplet_grid_row grouplet_card grouplet_card--chrome-top';
    c.dnd._setDragImage(event, card, {count: 1});
    const [frame] = aux.children;
    assert.equal(frame.className, container.className);
    assert.equal(frame.style.cssText, '--gg-cols: 3;', 'the grid tokens set inline come along');
    assert.equal(frame.children[0].className, 'grouplet_grid_body');
    assert.equal(images[0], frame.children[0].children[0], 'the image is the card clone itself');
    assert.equal(frame.style.position, 'fixed', 'above the page while the browser takes it');
    assert.equal(frame.style.zIndex, '2147483647');
    aux.children = [];
    c.dnd._setDragImage(event, card, {count: 1, struct: true});
    assert.ok(aux.children[0].className.includes('grouplet_grid_struct_drag_clone'));
    assert.equal(images[1], aux.children[0]);
    assert.equal(aux.children[0].style.position, 'fixed');
});

test('the slot opens before or after a row: rows by height, cards side by side by width', () => {
    const DnD = setup().context.gnr.GroupletGridDnD;
    const row = {left: 0, top: 100, width: 600, height: 40};
    assert.equal(DnD.dropsBefore(row, 500, 110, 600), true, 'upper half of a full-width row');
    assert.equal(DnD.dropsBefore(row, 10, 130, 600), false);
    const card = {left: 200, top: 0, width: 180, height: 200};
    assert.equal(DnD.dropsBefore(card, 250, 190, 600), true, 'left half of a card');
    assert.equal(DnD.dropsBefore(card, 330, 10, 600), false);
});

test('the nearest row is the one under the pointer, else the closest across a gap', () => {
    const DnD = setup().context.gnr.GroupletGridDnD;
    const rect = (left, top) => ({left, top, right: left + 100, bottom: top + 50, width: 100, height: 50});
    const rows = [{key: 'a', dom: {getBoundingClientRect: () => rect(0, 0)}},
                  {key: 'b', dom: {getBoundingClientRect: () => rect(120, 0)}}];
    assert.equal(DnD.nearestRow(rows, 50, 20).key, 'a');
    assert.equal(DnD.nearestRow(rows, 114, 20).key, 'b', 'in the gap, the closer card');
});

function slotGrid() {
    const s = setup();
    const g = s.grid('cards');
    ['r_a', 'r_b', 'r_c'].forEach((k, i) => {
        s.seed(g, k);
        const dom = g.body.insertBefore(new Surface(), null);
        dom.rect = {left: 0, top: i * 50, right: 600, bottom: i * 50 + 40, width: 600, height: 40};
        dom.addEventListener('dragover', (e) => g.c.dnd.tileDragOver(e, dom));
        dom.addEventListener('drop', (e) => g.c.dnd.tileDrop(e, dom, k));
        g.c.tiles[k] = {domNode: () => dom, flash() {}};
    });
    g.c._isTabsLayout = () => false;
    const values = {};
    const dt = {get types() { return Object.keys(values); },
                setData: (key, value) => { values[key] = value; }, getData: key => values[key] || ''};
    const tile = (k) => g.c.tiles[k].domNode();
    const over = (k, x, y) => {
        const e = tile(k).dispatch('dragover', dt);
        return e;
    };
    return {s, g, dt, tile, over};
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const slotDom = (g) => g.body.children.find((d) => d.className === 'grouplet_grid_drop_slot');
const order = (g) => g.body.children.map((d) => d.className === 'grouplet_grid_drop_slot' ? 'slot'
    : Object.keys(g.c.tiles).find((k) => g.c.tiles[k].domNode() === d));

test('a dragged row lifts out, the slot follows the pointer and the row lands where it opened', async () => {
    const {s, g, dt, tile} = slotGrid();
    g.c.dnd.tileDragStart({dataTransfer: dt, preventDefault() {}, stopPropagation() {}}, tile('r_a'), 'r_a');
    await tick();
    assert.deepEqual(order(g), ['slot', 'r_a', 'r_b', 'r_c'], 'the slot holds the lifted row\'s place');
    assert.ok(tile('r_a').classList.contains('grouplet_grid_row--lifted'));
    const at = (k, y) => {
        const e = {dataTransfer: dt, clientX: 300, clientY: y, preventDefault() { this.prevented = true; },
                   stopPropagation() {}, target: tile(k), currentTarget: tile(k)};
        g.c.dnd.tileDragOver(e, tile(k));
        return e;
    };
    assert.equal(at('r_c', 135).prevented, true);
    assert.deepEqual(order(g), ['r_a', 'r_b', 'r_c', 'slot'], 'lower half of the last row: after it');
    at('r_c', 105);
    assert.deepEqual(order(g), ['r_a', 'r_b', 'slot', 'r_c']);
    slotDom(g).dispatch('drop', dt);
    assert.equal(slotDom(g), undefined);
    assert.ok(!tile('r_a').classList.contains('grouplet_grid_row--lifted'));
    assert.equal(s.published.at(-1).position, '<r_c');
    assert.deepEqual([...g.rows.keys()], ['r_b', 'r_a', 'r_c']);
});

test('dropped at home nothing moves; leaving the grid sends the slot home; a lost drag puts the rows back', async () => {
    const {s, g, dt, tile} = slotGrid();
    const start = () => g.c.dnd.tileDragStart({dataTransfer: dt, preventDefault() {}, stopPropagation() {}},
                                              tile('r_b'), 'r_b');
    start();
    await tick();
    const moves = s.published.length;
    slotDom(g).dispatch('drop', dt);
    assert.equal(s.published.length, moves, 'home: no move');
    assert.deepEqual([...g.rows.keys()], ['r_a', 'r_b', 'r_c']);
    start();
    await tick();
    g.c.dnd.tileDragOver({dataTransfer: dt, clientX: 300, clientY: 130, preventDefault() {}, stopPropagation() {}},
                         tile('r_c'));
    assert.deepEqual(order(g), ['r_a', 'r_b', 'r_c', 'slot']);
    const DnD = s.context.gnr.GroupletGridDnD;
    g.c.dnd.addBtnDragLeave({currentTarget: g.body, relatedTarget: null});
    assert.deepEqual(order(g), ['r_a', 'r_b', 'r_c', 'slot'], 'a dragleave with no relatedTarget is no exit');
    DnD.watchOutside({target: {closest: () => g.body}});
    assert.deepEqual(order(g), ['r_a', 'r_b', 'r_c', 'slot'], 'still over a grid');
    DnD.watchOutside({target: {closest: () => null}});
    assert.deepEqual(order(g), ['r_a', 'slot', 'r_b', 'r_c'], 'over no grid: back where the row came from');
    s.context.gnr.GroupletGridDnD.endDrag();
    await tick();
    assert.equal(slotDom(g), undefined);
    assert.ok(!tile('r_b').classList.contains('grouplet_grid_row--lifted'));
});
