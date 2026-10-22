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


class FakeElement {
    constructor(tag) {
        this.tagName = tag.toUpperCase();
        this.children = [];
        this.attributes = {};
        this.listeners = {};
        this.style = {};
        this.offsetHeight = 0;
        const classes = new Set();
        this.classList = {
            add: (c) => classes.add(c),
            remove: (c) => classes.delete(c),
            contains: (c) => classes.has(c),
            toggle: (c, on) => (on ? classes.add(c) : classes.delete(c))
        };
        Object.defineProperty(this, 'className', {
            get: () => [...classes].join(' '),
            set: (v) => { classes.clear(); String(v).split(/\s+/).filter(Boolean).forEach((c) => classes.add(c)); }
        });
    }
    get firstChild() { return this.children[0] || null; }
    appendChild(el) { this.children.push(el); return el; }
    insertBefore(el, ref) {
        const i = ref ? this.children.indexOf(ref) : -1;
        if (i < 0) this.children.push(el); else this.children.splice(i, 0, el);
        return el;
    }
    setAttribute(k, v) { this.attributes[k] = String(v); }
    getAttribute(k) { return this.attributes[k]; }
    querySelector() { return null; }
    addEventListener(evt, h) { (this.listeners[evt] ||= []).push(h); }
    removeEventListener(evt, h) { this.listeners[evt] = (this.listeners[evt] || []).filter((x) => x !== h); }
    fire(evt, extra = {}) {
        const e = Object.assign({type: evt, stopped: false, prevented: false,
                                 stopPropagation() { e.stopped = true; },
                                 preventDefault() { e.prevented = true; }}, extra);
        (this.listeners[evt] || []).forEach((h) => h(e));
        return e;
    }
}

function loadCard() {
    const context = {console, File: function() {}, gnr: {}, setTimeout,
                     genro: {wdg: {getHandler: () => null}, safeHtmlContent: (v) => v,
                             dlg: {docTrack: () => {}, openDoc: () => {}}},
                     DOMParser: TextParser,
                     dijit: {getEnclosingWidget: () => null},
                     document: {createElement: (tag) => new FakeElement(tag)}};
    context.dojo = {
        Deferred: function() {},
        eval,
        toJson: JSON.stringify,
        isIE: 0,
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const cardJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_card.js');
    vm.runInContext(readFileSync(cardJs, 'utf8'), context, {filename: 'grouplet_card.js'});
    context._T = (str) => str;
    return context;
}

function bandCard(context, kw = {}) {
    const state = {collapsed: false, checked: false, toggled: 0, expanded: 0, clicks: 0, docs: []};
    const root = new FakeElement('div');
    const card = new context.gnr.GroupletCard(Object.assign({
        rootDom: () => root,
        collapse: {isCollapsed: () => state.collapsed, toggle: () => { state.toggled++; },
                   expand: () => { state.expanded++; }},
        title: (dom) => { dom.innerHTML = 'Alice'; },
        doc: {address: 'grouplet:test:about', fill: (html) => html, placeholders: () => []},
        checkbox: {isChecked: () => state.checked, onClick: () => { state.clicks++; }}
    }, kw));
    const band = new FakeElement('div');
    band.appendChild(new FakeElement('div'));
    card.wireBand(band);
    return {card, band, root, state};
}

// objects of the card's own realm: the framework tells attributes by `instanceof Object`
const inVm = (context, obj) => vm.runInContext('(' + JSON.stringify(obj) + ')', context);

const classes = (band) => band.children.map((el) => el.className);

test('the band lays out chevron, title, doc, the framework spacer, then the checkbox', () => {
    const {band, card} = bandCard(loadCard());
    assert.deepEqual(classes(band), ['grouplet_card_chevron', 'grouplet_card_title', 'grouplet_card_doc',
                                     '', 'grouplet_card_check']);
    assert.equal(card.titleDom.innerHTML, 'Alice');
});

test('tools filters the band: an admitted tool without its host part is dropped too', () => {
    const context = loadCard();
    assert.deepEqual(classes(bandCard(context, {tools: 'title,check'}).band),
                     ['grouplet_card_title', '', 'grouplet_card_check']);
    assert.deepEqual(classes(bandCard(context, {tools: 'collapse,doc', doc: null}).band),
                     ['grouplet_card_chevron', ''], 'doc admitted but missing');
    assert.equal(context.gnr.GroupletCard.parseTools(null), null);
    assert.deepEqual([...context.gnr.GroupletCard.parseTools(' title , menu ')], ['title', 'menu']);
});

test('the chevron toggles by click and keyboard and never reaches the card', () => {
    const {card, state} = bandCard(loadCard());
    const e = card.chevronDom.fire('click');
    assert.equal(e.stopped, true);
    card.chevronDom.fire('keydown', {key: 'Enter'});
    card.chevronDom.fire('keydown', {key: 'a'});
    assert.equal(state.toggled, 2);
    assert.equal(card.chevronDom.getAttribute('aria-expanded'), 'true');
});

test('a folded card opens from its title, an open one ignores it', () => {
    const {card, state} = bandCard(loadCard());
    card.titleDom.fire('click');
    assert.equal(state.expanded, 0);
    state.collapsed = true;
    card.titleDom.fire('click');
    assert.equal(state.expanded, 1);
});

test('applyCollapsed sets the class and the chevron state, without animation when unsupported', () => {
    const {card, root} = bandCard(loadCard());
    card.applyCollapsed(true, true);
    assert.ok(root.classList.contains('grouplet_card--collapsed'));
    assert.equal(card.chevronDom.getAttribute('aria-expanded'), 'false');
    assert.equal(card.chevronDom.getAttribute('title'), '!!Expand');
    card.applyCollapsed(false, true);
    assert.ok(!root.classList.contains('grouplet_card--collapsed'));
});

test('a card draws its folded state when its band is created, with the classes its host asks', () => {
    const context = loadCard();
    const {root} = bandCard(context, {collapse: {isCollapsed: () => true, toggle() {}, expand() {}},
                                      collapsedClasses: ['grouplet_grid_row--collapsed', 'grouplet_card--collapsed']});
    assert.ok(root.classList.contains('grouplet_grid_row--collapsed'));
    assert.ok(root.classList.contains('grouplet_card--collapsed'));
});

test('a folding card animates its height and keeps its content until closed', () => {
    const {card, root} = bandCard(loadCard());
    let anim;
    root.offsetHeight = 120;
    root.animate = (frames, opts) => {
        anim = {frames, opts, cancel() { this.oncancel(); }};
        return anim;
    };
    root.classList.toggle = (c, on) => { root.offsetHeight = on ? 30 : 120; };
    const removed = [];
    root.classList.remove = (c) => removed.push(c);
    const added = [];
    root.classList.add = (c) => added.push(c);
    card.applyCollapsed(true, true);
    assert.deepEqual([...anim.frames].map((f) => f.height), ['120px', '30px']);
    assert.deepEqual(removed, ['grouplet_card--collapsed'], 'content kept in view while folding');
    assert.equal(root.style.overflow, 'hidden');
    anim.onfinish();
    assert.deepEqual(added, ['grouplet_card--collapsed']);
    assert.equal(root.style.overflow, '');
    assert.equal(card._collapseAnim, null);
});

test('the checkbox mirrors the host and reports its clicks', () => {
    const {card, state} = bandCard(loadCard());
    assert.equal(card.checkDom.checked, false);
    card.setChecked(true);
    assert.equal(card.checkDom.checked, true);
    card.checkDom.fire('click');
    assert.equal(state.clicks, 1);
});

test('the doc icon is tracked by its address and opens it with the title, by click or keyboard', () => {
    const context = loadCard();
    const tracked = [];
    const opened = [];
    context.genro.dlg = {docTrack: (dom, address) => tracked.push([dom, address]),
                         openDoc: (dom, address, kw) => opened.push([dom, address, kw])};
    const {band, card} = bandCard(context);
    const icon = band.children[2];
    assert.deepEqual(tracked, [[icon, 'grouplet:test:about']], 'shown when the page learns its doc exists');
    assert.equal(icon.fire('click').stopped, true);
    icon.fire('keydown', {key: ' '});
    icon.fire('keydown', {key: 'a'});
    assert.equal(opened.length, 2);
    const [dom, address, kw] = opened[0];
    assert.equal(dom, icon);
    assert.equal(address, 'grouplet:test:about');
    assert.equal(kw.title, 'Alice');
    assert.equal(kw.fill, card.doc.fill);
    assert.equal(kw.placeholders, card.doc.placeholders);
});

test('docSpec fills the doc on the card data and offers its fields as variables', () => {
    const context = loadCard();
    const Card = context.gnr.GroupletCard;
    const row = new context.gnr.GnrBag();
    row.setItem('city', 'Turin');
    row.setItem('lines', new context.gnr.GnrBag());
    const spec = Card.docSpec('grouplet:test:card_profile', () => row, inVm(context, {courier: 'Fast Parcel'}));
    assert.equal(spec.address, 'grouplet:test:card_profile');
    assert.equal(spec.fill('<p>$city via $courier$none</p>'), '<p>Turin via Fast Parcel</p>');
    assert.deepEqual([...spec.placeholders()], ['city', 'courier'], 'a nested Bag is no variable');
    assert.equal(Card.docSpec(null, () => row), null, 'no address, no doc');
});

test('the band is the drag source, and destroy unwires it', () => {
    const events = [];
    const {card, band} = bandCard(loadCard(), {drag: {start: () => events.push('start'),
                                                      end: () => events.push('end')}});
    assert.equal(band.getAttribute('draggable'), 'true');
    band.fire('dragstart');
    band.fire('dragend');
    card.destroy();
    band.fire('dragstart');
    assert.deepEqual(events, ['start', 'end']);
});

test('mount adds the band and its spacer as framework nodes', () => {
    const context = loadCard();
    const root = new context.gnr.GnrDomSource();
    root._('div', 'tile', {});
    const card = new context.gnr.GroupletCard({});
    const band = card.mount(root.getItem('tile'), '_band');
    assert.equal(root.getNode('tile._band').attr._class, 'grouplet_card_band');
    assert.equal(band.getNode('_spacer').attr._class, 'grouplet_card_spacer');
});

test('buildKebab keeps presets, overrides labels, merges dicts and drops false entries', () => {
    const context = loadCard();
    const root = new context.gnr.GnrDomSource();
    const presets = inVm(context, {copy: {label: 'Copy', action: 'c()'}, 'delete': {label: 'Delete', action: 'd()'}});
    context.gnr.GroupletCard.buildKebab(root, 'kebab',
        inVm(context, {copy: true, 'delete': 'Remove', extra: {label: 'Extra', action: 'x()'}, gone: false, unknown: true}),
        presets, inVm(context, {_class: 'k'}), 'k_icon');
    assert.equal(root.getNode('kebab').attr._class, 'k');
    assert.equal(root.getNode('kebab.glyph').attr._class, 'k_icon');
    const lines = [...root.getItem('kebab').getNodes()[1].getValue().getNodes()].map((n) => [n.attr.label, n.attr.action]);
    assert.deepEqual(lines, [['Copy', 'c()'], ['Remove', 'd()'], ['Extra', 'x()']]);
});

test('templates render on a Bag, with sums, and a blank title falls back to the label', () => {
    const context = loadCard();
    const Card = context.gnr.GroupletCard;
    const row = new context.gnr.GnrBag();
    row.setItem('name', 'Story');
    row.setItem('items.i1.amount', 100.5);
    row.setItem('items.i2.amount', 250);
    const tpl = Card.compileTemplate({template: '$name $total', sums: {total: 'items.amount'}});
    assert.equal(Card.renderTemplate(tpl, row), 'Story 350.5');
    const dom = {};
    Card.renderTitle(dom, tpl, row, () => 'Untitled');
    assert.equal(dom.innerHTML, 'Story 350.5');
    row.setItem('name', '');
    const blank = {};
    Card.renderTitle(blank, tpl, row, () => 'Untitled');
    assert.equal(blank.textContent, 'Untitled', 'its sums alone are no title');
    assert.equal(Card.renderTemplate(null, row), '');
});

test('a field in error inside the card marks the band, once per frame, until destroy', () => {
    const context = loadCard();
    const observers = [];
    context.MutationObserver = class {
        constructor(cb) { this.cb = cb; this.on = true; observers.push(this); }
        observe(root, opts) { this.opts = opts; }
        disconnect() { this.on = false; }
    };
    const frames = [];
    context.requestAnimationFrame = (cb) => frames.push(cb);
    const {card, root} = bandCard(context);
    let invalid = false;
    root.querySelector = (sel) => (sel === context.gnr.GroupletCard.INVALID_SELECTOR && invalid ? {} : null);
    const [obs] = observers;
    assert.deepEqual([...obs.opts.attributeFilter], ['class']);
    invalid = true;
    obs.cb();
    obs.cb();
    assert.equal(frames.length, 1, 'a burst of class changes is checked once');
    frames.shift()();
    assert.ok(root.classList.contains('grouplet_card--invalid'));
    invalid = false;
    obs.cb();
    frames.shift()();
    assert.ok(!root.classList.contains('grouplet_card--invalid'));
    card.destroy();
    assert.equal(obs.on, false);
});

test('a field the row lacks shows blank, so a row with none of its fields shows its label', () => {
    const context = loadCard();
    const Card = context.gnr.GroupletCard;
    const row = new context.gnr.GnrBag();
    row.setItem('name', 'Story');
    assert.equal(Card.renderTemplate(Card.compileTemplate('[$name|$nope]'), row), '[Story|]');
    const dom = {};
    Card.renderTitle(dom, Card.compileTemplate('$code $nope'), row, () => 'Untitled');
    assert.equal(dom.textContent, 'Untitled');
});

test('a doc renders on the card data, with doc_kw for values the data has not', () => {
    const context = loadCard();
    const Card = context.gnr.GroupletCard;
    const row = new context.gnr.GnrBag();
    row.setItem('name', 'Story');
    const doc = Card.compileTemplate('<p>$name, see $manual</p>');
    assert.equal(Card.renderDoc(doc, row, inVm(context, {manual: 'chapter 3'})), '<p>Story, see chapter 3</p>');
    assert.equal(row.getNode('manual'), null, 'the card data is left alone');
    assert.equal(Card.renderDoc(doc, null), '<p>, see </p>');
});

test('useForm: an error status of the card\'s form marks the band even when no field shows it', () => {
    const context = loadCard();
    const {card, root} = bandCard(context);
    const host = Object.create(context.gnr.GroupletCardHost.prototype);
    host.card = card;
    host.setFormStatus('error');
    assert.ok(root.classList.contains('grouplet_card--invalid'));
    host.setFormStatus('changed');
    assert.ok(!root.classList.contains('grouplet_card--invalid'));
});

test('Clear empties the bound values under the card data, or under its own form record', () => {
    const context = loadCard();
    const written = [];
    context.genro.setData = (path, value) => written.push([path, value]);
    const field = (value, abs) => ({attr: {value}, absDatapath: () => abs});
    const nodes = [field('^.city', 'rec.city'), field('^#FORM.other', 'elsewhere.other'),
                   field('=.static', 'rec.static'), {attr: {}}];
    const sourceNode = {absDatapath: () => 'card', getValue: () => ({walk: (cb) => nodes.forEach(cb)})};
    const host = Object.create(context.gnr.GroupletCardHost.prototype);
    Object.assign(host, {sourceNode, kw: {formId: 'c1_form'}});
    context.genro.formById = (id) => (id === 'c1_form'
        ? {formDatapath: '.record', sourceNode: {absDatapath: (p) => (p === '.record' ? 'rec' : null)}} : null);
    host.clearFields();
    assert.deepEqual(written, [['rec.city', null]], 'only a pointer under the form record');
    written.length = 0;
    host.kw = {};
    nodes[0].absDatapath = () => 'card.city';
    host.clearFields();
    assert.deepEqual(written, [['card.city', null]], 'without useForm, under the card data');
});
