const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// the browser's DOMParser as far as a title check reads it: the text outside the tags
class TextParser {
    parseFromString(html) {
        let text = '';
        let inTag = false;
        for (const ch of String(html)) {
            if (ch === '<') inTag = true;
            else if (ch === '>') inTag = false;
            else if (!inTag) text += ch;
        }
        return {body: {textContent: text.split('&nbsp;').join('\u00a0')}};
    }
}


function loadGrid() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, DOMParser: TextParser,
                     dijit: {getEnclosingWidget: () => null}};
    context.dojo = {
        Deferred: function() {
            this.callbacks = [];
            this.callback = (value) => { this.result = value; this.callbacks.forEach((cb) => cb(value)); };
            this.errback = (error) => { this.error = error; };
            this.addCallback = (cb) => { this.callbacks.push(cb); return this; };
        },
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        isIE: 0,
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const gridJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js');
    vm.runInContext(readFileSync(path.join(path.dirname(gridJs), 'grouplet_card.js'), 'utf8'), context,
                    {filename: 'grouplet_card.js'});
    vm.runInContext(readFileSync(gridJs, 'utf8'), context, {filename: 'grouplet_grid.js'});
    context._T = str => str;
    return context;
}

function createGrid(kw = {}) {
    const context = loadGrid();
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const lines = new Bag();
    data.setItem('record.lines', lines);
    data.setItem('record.common.producer', 'P01');
    data.setItem('ws', new Bag());
    data.setBackRef();
    let counter = 0;
    const published = [];
    Object.assign(context.genro, {
        _data: data,
        vld: new context.gnr.GnrValidator(context.genro),
        wdg: {getHandler: () => null},
        publish: (topic, payload) => published.push([topic, payload]),
        getData: p => data.getItem(p),
        setData: (p, v) => data.setItem(p, v),
        getDataNode: p => data.getNode(p),
        time36Id: () => 'k' + (++counter),
        safeHtmlContent: (v) => v,
        evaluate: expr => vm.runInContext('(' + expr + ')', context)
    });
    const controller = Object.create(context.gnr.GroupletGridController.prototype);
    Object.assign(controller, {
        nodeId: 'grid',
        storepath: 'record.lines',
        phantomPath: 'ws.phantom',
        entryPath: 'ws.entry',
        defaultRow: {},
        tiles: {},
        formulas: {},
        _freshRows: {},
        minRows: 0,
        maxRows: null,
        layout: 'cards',
        selectionmenu: {},
        sourceNode: {
            getFormHandler: () => kw.form || null,
            getRelativeData: (p) => data.getItem(p.replace('#FORM.', 'record.')),
            attr: {}
        },
        dataStore: {
            addRow: (key, values) => lines.setItem(key, new Bag(values)),
            rowValue: key => lines.getItem(key),
            rowNode: key => lines.getNode(key),
            removeRow: key => lines.popNode(key),
            getData: () => lines,
            getNodes: () => lines.getNodes(),
            updateRow: (key, dict) => Object.keys(dict).forEach(k => lines.setItem(key + '.' + k, dict[k]))
        },
        _containerDom: () => ({classList: {toggle() {}, remove() {}, add() {}, contains: () => false},
                               querySelectorAll: () => [], contains: () => false})
    }, kw.controller || {});
    return {context, controller, data, lines, published, Bag};
}

const plain = bag => JSON.parse(JSON.stringify(bag.asDict()));
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test('defaultRow: a =path value is read when the row is added', () => {
    const s = createGrid({controller: {defaultRow: {ProducerCode: '=#FORM.common.producer', qty: 1}}});
    s.controller._doAddItem();
    assert.deepEqual(plain(s.lines.getItem('r_k1')), {ProducerCode: 'P01', qty: 1});
    s.data.setItem('record.common.producer', 'P02');
    s.controller._doAddItem(null, {qty: 3});
    assert.deepEqual(plain(s.lines.getItem('r_k2')), {ProducerCode: 'P02', qty: 3});
    assert.equal(s.controller.defaultRow.ProducerCode, '=#FORM.common.producer', 'the spec is kept');
});

test('defaultRow: a blank row compares with the defaults it was given', async () => {
    const s = createGrid({controller: {defaultRow: {ProducerCode: '=#FORM.common.producer'}, phantom: true,
                                       phantomTile: {domNode: () => null}}});
    s.controller._resetPhantom();
    assert.equal(s.data.getItem('ws.phantom.ProducerCode'), 'P01');
    s.data.setItem('record.common.producer', 'P02');
    assert.equal(s.controller._phantomHasValues(), false, 'a later default is no entry');
    s.data.setItem('ws.phantom.item', 'Milk');
    await tick();
    assert.equal(s.lines.getItem('r_k1.ProducerCode'), 'P01');
    assert.equal(s.data.getItem('ws.phantom.ProducerCode'), 'P02', 'the next blank row reads it again');
});

test('defaultRow: a blank entry row shows a default changed since it was cleared', () => {
    const s = createGrid({controller: {defaultRow: {ProducerCode: '=#FORM.common.producer'}, entry: true,
                                       entryTile: {domNode: () => null, tileContent: {walk: () => undefined}}}});
    s.controller._resetEntry();
    s.data.setItem('record.common.producer', 'P02');
    s.controller._refreshEntryDefaults();
    assert.equal(s.data.getItem('ws.entry.ProducerCode'), 'P02');
    s.data.setItem('ws.entry.item', 'Grip');
    s.data.setItem('record.common.producer', 'P03');
    s.controller._refreshEntryDefaults();
    assert.equal(s.data.getItem('ws.entry.ProducerCode'), 'P02', 'a row being typed in keeps it');
});

function chapters(s, rows) {
    rows.forEach(([key, code, name, amounts]) => {
        const accounts = new s.Bag();
        amounts.forEach((amount, i) => accounts.setItem('a' + i, new s.Bag({code: String(i), amount})));
        s.lines.setItem(key, new s.Bag({code, name, accounts}));
    });
}

test('defaultRow: a ==expression is worked out at each add, over the rows and the grid', () => {
    const s = createGrid({controller: {defaultRow: {
        code: "==String(rows.len() + 1).padStart(3, '0')",
        name: '',
        owner: '==this.attr.owner + "/" + grid.nodeId'}}});
    s.controller.sourceNode.attr.owner = 'budget';
    s.controller._doAddItem();
    s.controller._doAddItem(null, {name: 'Crew'});
    assert.deepEqual(plain(s.lines.getItem('r_k1')), {code: '001', name: '', owner: 'budget/grid'});
    assert.deepEqual(plain(s.lines.getItem('r_k2')), {code: '002', name: 'Crew', owner: 'budget/grid'});
    s.controller.entry = true;
    s.controller.entryTile = {domNode: () => null, tileContent: {walk: () => undefined}};
    s.controller._resetEntry();
    assert.equal(s.data.getItem('ws.entry.code'), '003', 'the entry row shows the next one too');
    s.controller._announcer = {textContent: ''};
    const tile = {domNode: () => null, flash() {}};
    s.controller.tiles = {r_k1: tile, r_k2: tile};
    s.controller._insertPastedRows([{name: 'Grip'}, {name: 'Sound'}], null);
    assert.deepEqual([...s.lines.getNodes().map((n) => n.getValue().getItem('code'))], ['001', '002', '003', '004'], 'each pasted row the next code');
});

test('defaultRow: a fresh row left empty is measured on the defaults it was given', () => {
    const s = createGrid({controller: {phantom: true, defaultRow: {code: "==String(rows.len() + 1)"}}});
    s.controller._doAddItem();
    s.controller.tiles = {r_k1: {}};
    assert.equal(s.controller.defaultRowValues().code, '2', 'worked out again it is the next code');
    s.controller._dropIfEmpty('r_k1');
    assert.equal(s.lines.len(), 0, 'still a row with no entry');
});

function focusTile(s, {bodyMounted = true} = {}) {
    // a tile with a code badge, a name and a read-only note, as editors
    // and as source nodes bound to their fields
    const focused = [];
    const editor = (name) => ({name, focus: () => focused.push(name), select() {}});
    const editors = {code: editor('code'), name: editor('name'), note: editor('note')};
    const nodes = ['code', 'name', 'note'].map((f) => ({attr: {value: '^.' + f}, widget: {focusNode: editors[f]}}));
    const tile = Object.create(s.context.gnr.GroupletGridTile.prototype);
    Object.assign(tile, {
        controller: s.controller,
        bodyMounted,
        tileContent: {walk: (cb) => nodes.reduce((found, n) => found || cb(n), undefined)},
        domNode: () => ({isConnected: true, querySelectorAll: () => [editors.code, editors.name]}),
        tileNode: {freeze() {}, unfreeze() {}},
        _cancelPendingBody() {},
        _mountChrome() {},
        _mountBody() {}
    });
    return {tile, focused};
}

test('additem_focus: a row added with + puts the caret on that field, else on the first editor', async () => {
    const s = createGrid({controller: {additemKw: {focus: 'name'}}});
    s.controller._reproxyForm = () => {};
    s.controller._doAddItem();
    assert.equal(s.controller._pendingFocusField, 'name');
    let t = focusTile(s);
    s.controller._focusFirstEditor(t.tile, null, 'name');
    await tick();
    assert.deepEqual(t.focused, ['name']);
    t = focusTile(s);
    s.controller._focusFirstEditor(t.tile, null, null);
    await tick();
    assert.deepEqual(t.focused, ['code'], 'without additem_focus the first editor');
    t = focusTile(s);
    s.controller._focusFirstEditor(t.tile, null, 'note');
    await tick();
    assert.deepEqual(t.focused, ['code'], 'a field that takes no typing falls back to the first');
    t = focusTile(s, {bodyMounted: false});
    s.controller._focusFirstEditor(t.tile, null, 'name');
    await tick();
    assert.deepEqual(t.focused, [], 'a lazy tab has no body yet');
    t.tile.mountBody();
    await tick();
    assert.deepEqual(t.focused, ['name'], 'the caret goes there once the body is mounted');
});

test('naturalCompare orders codes as read, blanks last', () => {
    const {context} = createGrid();
    const cmp = context.gnr.GroupletGridController.naturalCompare;
    const sorted = ['10', '2', null, '1.10', '1.2', 'B', 'a', ''].sort(cmp);
    assert.deepEqual(sorted.slice(0, 6), ['1.2', '1.10', '2', '10', 'a', 'B']);
    assert.ok(sorted.slice(6).every((v) => v === null || v === ''));
    assert.equal(cmp(3, 20) < 0, true);
});

test('sortField orders the tab keys without touching the Bag, unless sortStore', () => {
    const s = createGrid();
    chapters(s, [['r_a', '10', 'Crew', []], ['r_b', '2', 'Cast', []], ['r_c', '1', 'Story', []]]);
    const store = new s.context.gnr.GroupletDataStore({store: {getData: () => s.lines}}, {});
    store.setSort({field: 'code'});
    assert.deepEqual([...store.sortedKeys()], ['r_c', 'r_b', 'r_a']);
    assert.equal(store.applySortToStore(), false);
    assert.deepEqual([...s.lines.keys()], ['r_a', 'r_b', 'r_c']);
    store.setSort({field: 'code', store: true});
    assert.equal(store.applySortToStore(), true);
    assert.deepEqual([...s.lines.keys()], ['r_c', 'r_b', 'r_a']);
    store.clearSort();
    assert.deepEqual([...store.sortedKeys()], ['r_c', 'r_b', 'r_a'], 'unsorted is the Bag order');
});

test('titleTemplate shows fields and a live subtree total', () => {
    const s = createGrid();
    chapters(s, [['r_a', '1', 'Story', [100, 250.5]]]);
    const Card = s.context.gnr.GroupletCard;
    const tpl = Card.compileTemplate({template: '$code $name $total', sums: {total: 'accounts.amount'}});
    assert.equal(s.controller.renderTemplate(tpl, 'r_a'), '1 Story 350.5');
    s.lines.setItem('r_a.accounts.a2', new s.Bag({amount: 9.5}));
    assert.equal(s.controller.renderTemplate(tpl, 'r_a'), '1 Story 360');
    assert.equal(Card.deepSum(s.lines.getItem('r_a'), 'amount'), 360, 'no path: the whole row');
    assert.equal(s.controller.renderTemplate(Card.compileTemplate('$name'), 'r_a'), 'Story');
});

test('a row whose own fields are blank shows its label, not its sums alone', () => {
    const s = createGrid();
    chapters(s, [['r_a', '1', 'Story', [100]], ['r_n', '', '', []]]);
    const tpl = s.context.gnr.GroupletCard.compileTemplate(
        {template: '<b>$code</b> $name <i>$total</i>', sums: {total: 'accounts.amount'}});
    const dom = () => ({textContent: '', set innerHTML(v) { this.textContent = v; }});
    const shown = dom();
    s.controller._renderTitle(shown, tpl, 'r_a');
    assert.equal(shown.textContent, '<b>1</b> Story <i>100</i>');
    const blank = dom();
    s.controller._renderTitle(blank, tpl, 'r_n');
    assert.equal(blank.textContent, 'r_n', 'no titleField: the key');
});

test('a changed sort field re-sorts the strip once, a template row is redrawn', async () => {
    const s = createGrid({controller: {layout: 'tabs'}});
    chapters(s, [['r_a', '3', 'Crew', [1]], ['r_b', '2', 'Cast', [2]]]);
    const store = new s.context.gnr.GroupletDataStore({store: {getData: () => s.lines}}, {});
    store.setSort({field: 'code'});
    const strip = {children: [], appendChild(chip) {
        this.children = this.children.filter((c) => c !== chip).concat(chip);
    }};
    const titles = {};
    const chip = (k) => ({key: k, querySelector: () => ({set innerHTML(v) { titles[k] = v; },
                                                          get textContent() { return titles[k]; }})});
    Object.assign(s.controller, {
        dataStore: store, sortField: 'code', tabstripDom: strip, _dirtyRows: new Set(),
        titleTemplate: s.context.gnr.GroupletCard.compileTemplate('$code·$name'),
        _tabsByPkey: {r_a: chip('r_a'), r_b: chip('r_b')}
    });
    strip.children = [s.controller._tabsByPkey.r_a, s.controller._tabsByPkey.r_b];
    const storeNode = s.lines.getParentNode();
    s.lines.setItem('r_a.code', '1');
    s.controller._onRowContentChanged(s.lines.getNode('r_a.code'), storeNode);
    s.controller._onRowContentChanged(s.lines.getNode('r_a.name'), storeNode);
    assert.deepEqual(strip.children.map((c) => c.key), ['r_a', 'r_b'], 'deferred');
    await tick();
    assert.equal(titles.r_a, '1·Crew');
    assert.deepEqual(strip.children.map((c) => c.key), ['r_a', 'r_b']);
    s.lines.setItem('r_a.code', '9');
    s.controller._onRowContentChanged(s.lines.getNode('r_a.code'), storeNode);
    await tick();
    assert.deepEqual(strip.children.map((c) => c.key), ['r_b', 'r_a']);
    assert.equal(titles.r_a, '9·Crew');
});

function groupGrid(context, code, keys) {
    const Bag = context.gnr.GnrBag;
    const rows = new Bag();
    keys.forEach((k) => rows.setItem(k, new Bag({item: k})));
    const deleted = [];
    const grid = Object.create(context.gnr.GroupletGridController.prototype);
    Object.assign(grid, {
        selectionGroup: code, rowCheckbox: true, minRows: 0, tiles: {}, _multiKeys: null,
        selectionmenu: {'delete': true},
        sourceNode: {getFormHandler: () => null},
        dataStore: {getData: () => rows, deleteRowsAsk: (k) => deleted.push(['ask', [...k]])},
        store: {deleteAsk: (all, protect, cb) => { deleted.push(['group', [...all]]); cb(); },
                deleteRows: (k) => deleted.push(['rows', [...k]])},
        _containerDom: () => ({classList: {toggle() {}, remove() {}}, querySelectorAll: () => []})
    });
    keys.forEach((k) => { grid.tiles[k] = {domNode: () => null}; });
    context.gnr.GroupletGridController._groupSet(code).add(grid);
    return {grid, deleted};
}

test('selectionGroup: grids sharing a code expose one selection, deleted with one question', () => {
    const {context} = createGrid();
    const a = groupGrid(context, 'details', ['d1', 'd2']);
    const b = groupGrid(context, 'details', ['d3']);
    const other = groupGrid(context, 'accounts', ['x1']);
    a.grid._onRowCheck('d2', {});
    b.grid._onRowCheck('d3', {});
    other.grid._onRowCheck('x1', {});
    const shape = (sel) => JSON.parse(JSON.stringify(
        sel.map((e) => [e.grid === a.grid ? 'a' : e.grid === b.grid ? 'b' : '?', [...e.rowKeys]])));
    assert.deepEqual(shape(a.grid.groupSelection()), [['a', ['d2']], ['b', ['d3']]]);
    assert.deepEqual(shape(b.grid.groupSelection()), [['a', ['d2']], ['b', ['d3']]]);
    a.grid.sourceNode.attr = {};
    a.grid._runSelectionAction({key: 'bulk', action: 'grid._got = [selection, rowKeys];'});
    const got = a.grid._got;
    assert.deepEqual(shape(got[0]), [['a', ['d2']], ['b', ['d3']]]);
    assert.deepEqual([...got[1]], ['d2'], 'rowKeys stays the grid\'s own');
    b.grid._deleteSelected();
    assert.deepEqual(JSON.parse(JSON.stringify(b.deleted)), [['group', ['d2', 'd3']], ['rows', ['d3']]]);
    assert.deepEqual(JSON.parse(JSON.stringify(a.deleted)), [['rows', ['d2']]], 'each grid deletes its own');
    a.grid.clearSelection(true);
    assert.equal(a.grid._multiKeys, null);
    assert.equal(b.grid._multiKeys, null);
    assert.deepEqual([...other.grid._multiKeys], ['x1'], 'another group is left alone');
});

test('selectionGroup: every grid of the group is marked selecting while one holds a selection', () => {
    const {context} = createGrid();
    const a = groupGrid(context, 'marks', ['d1']);
    const b = groupGrid(context, 'marks', ['d2']);
    const other = groupGrid(context, 'elsewhere', ['x1']);
    const marked = (g) => {
        const classes = new Set();
        const dom = {classList: {toggle: (c, on) => (on ? classes.add(c) : classes.delete(c)), remove() {}},
                     querySelectorAll: () => []};
        g.grid._containerDom = () => dom;
        return () => classes.has('grouplet_grid--selecting');
    };
    const [isA, isB, isOther] = [marked(a), marked(b), marked(other)];
    a.grid._onRowCheck('d1', {});
    assert.deepEqual([isA(), isB(), isOther()], [true, true, false]);
    a.grid._onRowCheck('d1', {});
    assert.deepEqual([isA(), isB()], [false, false]);
});

test('selectionGroup: one grid alone deletes through its own dialog', () => {
    const {context} = createGrid();
    const a = groupGrid(context, 'solo', ['d1', 'd2']);
    a.grid._onRowCheck('d1', {});
    a.grid._deleteSelected();
    assert.deepEqual(JSON.parse(JSON.stringify(a.deleted)), [['ask', ['d1']]]);
});

function fakeTileDom() {
    const classes = new Set();
    const line = {textContent: '', set innerHTML(v) { this.textContent = v; }};
    const toggle = {attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }};
    return {classes, line, toggle,
            classList: {toggle: (c, on) => (on ? classes.add(c) : classes.delete(c)), contains: (c) => classes.has(c)},
            querySelector: (sel) => (sel.includes('summaryline') ? line : toggle)};
}

test('collapsible: closed cards fold to their summary, the state survives a re-render', async () => {
    const s = createGrid({controller: {collapsible: 'closed', _dirtyRows: new Set()}});
    chapters(s, [['r_a', '1', 'Crew', [100, 50]], ['r_b', '2', 'Cast', [10]]]);
    const Ctrl = s.context.gnr.GroupletGridController;
    s.controller.collapsedTemplate = s.context.gnr.GroupletCard.compileTemplate({template: '$code $name $total',
                                                           sums: {total: 'accounts.amount'}});
    s.controller.dataStore.rowNode = (k) => s.lines.getNode(k);
    const doms = {r_a: fakeTileDom(), r_b: fakeTileDom()};
    s.controller.tiles = {r_a: {domNode: () => doms.r_a}, r_b: {domNode: () => doms.r_b}};
    s.controller._applyCollapsed('r_a');
    assert.ok(doms.r_a.classes.has('grouplet_grid_row--collapsed'));
    assert.equal(doms.r_a.line.textContent, '1 Crew 150');
    assert.equal(doms.r_a.toggle.attrs['aria-expanded'], 'false');
    s.controller.toggleCollapsed('r_a');
    assert.ok(!doms.r_a.classes.has('grouplet_grid_row--collapsed'));
    s.controller._applyCollapsed('r_b');
    s.lines.setItem('r_b.accounts.a1', new s.Bag({amount: 5}));
    s.controller._onRowContentChanged(s.lines.getNode('r_b.accounts.a1'), s.lines.getParentNode());
    await tick();
    assert.equal(doms.r_b.line.textContent, '2 Cast 15', 'a folded card keeps its total live');
    const again = Object.assign(Object.create(Ctrl.prototype), {collapsible: 'closed', storepath: 'record.lines'});
    assert.equal(again.isCollapsed('r_a'), false, 'a new controller on the same rows keeps it open');
    assert.equal(again.isCollapsed('r_c'), true);
    const plainGrid = createGrid();
    assert.equal(plainGrid.controller.isCollapsed('r_a'), false, 'not collapsible: never folded');
});

test('a band title follows its row open or folded; a band without title is left alone', async () => {
    const s = createGrid({controller: {collapsible: true, _dirtyRows: new Set()}});
    chapters(s, [['r_a', '1', 'Crew', [100]], ['r_b', '2', 'Cast', [10]]]);
    const refreshed = [];
    s.controller.tiles = {
        r_a: {card: {titleDom: {}, refreshTitle: () => refreshed.push('r_a')}},
        r_b: {card: {titleDom: null, refreshTitle: () => refreshed.push('r_b')}}
    };
    const storeNode = s.lines.getParentNode();
    s.controller._onRowContentChanged(s.lines.getNode('r_a.name'), storeNode);
    s.controller._onRowContentChanged(s.lines.getNode('r_b.name'), storeNode);
    await tick();
    assert.deepEqual(refreshed, ['r_a'], 'r_a is open, its title is still drawn');
});

function pendingForm(context) {
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    const calls = [];
    Object.assign(form, {
        gridEditors: {},
        checkPendingGridEditor: () => null,
        updateStatus: () => calls.push('status'),
        publish: (command, kw) => calls.push(command + ':' + kw.command),
        opStatus: 'saving',
        autoSave: true
    });
    return {form, calls};
}

function fakeEditor(calls, {pending = true, ok = true, focused = false} = {}) {
    const editor = {
        values: pending,
        isDestroyed: () => false,
        isPending: () => editor.values || focused,
        hasPendingChanges: () => editor.values,
        prepareCommit: () => calls.push('blur'),
        commitPending: () => {
            calls.push('commit');
            if (ok) editor.values = false;
            return ok;
        }
    };
    return editor;
}

test('form: a pending entry is a change, and save commits it before saving once', async () => {
    const {context} = createGrid();
    const {form, calls} = pendingForm(context);
    assert.equal(form.registeredGridsStatus(), null);
    const editor = fakeEditor(calls, {focused: true});
    form.registerPendingEditor('grid', editor);
    assert.equal(form.registeredGridsStatus(), 'changed');
    const result = form.save();
    assert.ok(result instanceof context.dojo.Deferred, 'deferred while the entry commits');
    assert.deepEqual(calls, ['blur']);
    await tick();
    assert.deepEqual(calls, ['blur', 'commit', 'status'], 'the focused entry row does not commit again');
    assert.equal(form.registeredGridsStatus(), null);
    form.unregisterPendingEditor('grid');
    assert.equal(form.livePendingEditors().length, 0);
});

test('form: an entry that refuses stops dismiss, nothing pending dismisses at once', async () => {
    const {context} = createGrid();
    const {form, calls} = pendingForm(context);
    form.registerPendingEditor('grid', fakeEditor(calls, {ok: false}));
    const result = form.dismiss();
    await tick();
    assert.equal(result.result, false);
    assert.ok(!calls.includes('navigationEvent:dismiss'));
    form.unregisterPendingEditor('grid');
    form.dismiss();
    assert.ok(calls.includes('navigationEvent:dismiss'));
});

test('entry row: pending values, a changed edit or a draft set aside; commit adds them', () => {
    const s = createGrid({controller: {entry: true, defaultRow: {qty: 1},
                                       entryTile: {domNode: () => null, tileContent: {walk: () => undefined}},
                                       _announcer: {textContent: ''}}});
    const c = s.controller;
    c._resetEntry();
    assert.equal(c.hasPendingEntry(), false, 'defaults are no entry');
    s.data.setItem('ws.entry.item', 'Milk');
    assert.equal(c.hasPendingEntry(), true);
    assert.equal(c.commitPendingEntry(), true);
    assert.deepEqual([...s.lines.keys()], ['r_k1']);
    assert.equal(c.hasPendingEntry(), false);
    c.rowTemplate = '$item';
    c.tiles = {r_k1: {domNode: () => null, flash() {}}};
    s.data.setItem('ws.entry.item', 'Bread');
    c._editRowInEntry('r_k1');
    assert.equal(c.hasPendingEntry(), true, 'the draft set aside is pending');
    s.data.setItem('ws.entry.qty', 4);
    assert.equal(c.commitPendingEntry(), true);
    assert.equal(s.lines.getItem('r_k1.qty'), 4, 'the edit is saved');
    assert.deepEqual([...s.lines.keys()].map((k) => s.lines.getItem(k + '.item')), ['Milk', 'Bread'],
                     'and the draft added');
});

test('entry row: an invalid field stops the entry with its message', () => {
    const s = createGrid({controller: {entry: true, _announcer: {textContent: ''}}});
    const focused = [];
    const field = {widget: {focus: () => focused.push('qty')}, attr: {},
                   hasValidationError: () => true, getValidationError: () => 'min',
                   getElementLabel: () => 'Qty ', _resolveErrorMessage: () => 'Too small'};
    s.controller.entryTile = {domNode: () => null, tileContent: {walk: (cb) => cb(field)}};
    s.controller._resetEntry();
    s.data.setItem('ws.entry.qty', -1);
    assert.equal(s.controller._addEntry(), false);
    assert.equal(s.lines.len(), 0);
    assert.deepEqual(focused, ['qty']);
    assert.deepEqual(JSON.parse(JSON.stringify(s.published.at(-1))),
                     ['floating_message', {message: 'Qty: Too small', sound: '$onerror', messageType: 'error'}]);
});

test('cards without checkboxes: Cmd/Ctrl/Shift-click selects, once, only with a selection menu', () => {
    const {context} = createGrid();
    const a = groupGrid(context, 'clicks', ['d1', 'd2', 'd3']);
    a.grid.rowCheckbox = false;
    assert.equal(a.grid._clickSelects({metaKey: true}), true);
    assert.equal(a.grid._clickSelects({}), false, 'a plain click edits');
    assert.equal(a.grid._clickSelects({ctrlKey: true, _groupletSelected: true}), false,
                 'an inner row already took it');
    a.grid._onRowCheck('d1', {metaKey: true}, true);
    a.grid._onRowCheck('d3', {shiftKey: true}, true);
    assert.deepEqual([...a.grid._multiKeys], ['d1', 'd2', 'd3']);
    assert.equal(a.grid._clickClearsSelection({}), true, 'a plain click leaves the selection');
    a.grid.clearSelection(true);
    assert.equal(a.grid._clickClearsSelection({}), false, 'nothing selected: the click edits');
    a.grid.selectionmenu = {};
    assert.equal(a.grid._clickSelects({metaKey: true}), false);
});
