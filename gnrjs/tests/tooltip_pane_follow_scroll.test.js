const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

class FakeElement {
    constructor(rect, parentNode = null, overflow = 'visible') {
        this.rect = Object.assign({left: 0, top: 0, width: 0, height: 0}, rect);
        this.parentNode = parentNode;
        this.overflow = overflow;
        this.nodeType = 1;
        this.isConnected = true;
        this.style = {};
    }
    getClientRects() { return this.rect.width || this.rect.height ? [this.rect] : []; }
    getBoundingClientRect() {
        const {left, top, width, height} = this.rect;
        return {left, top, width, height, right: left + width, bottom: top + height};
    }
    contains(node) {
        for (let n = node; n; n = n.parentNode) if (n === this) return true;
        return false;
    }
}

function createContext() {
    const listeners = [];
    const published = [];
    const document = {
        addEventListener: (type, handler, capture) => listeners.push({type, handler, capture}),
        removeEventListener: (type, handler, capture) => {
            const i = listeners.findIndex(l => l.type === type && l.handler === handler && l.capture === capture);
            if (i >= 0) listeners.splice(i, 1);
        }
    };
    const window = {pageXOffset: 0, pageYOffset: 0, innerWidth: 1000, innerHeight: 800,
                    getComputedStyle: (node) => ({overflowX: node.overflow, overflowY: node.overflow})};
    const context = {console, File: function() {}, gnr: {}, setTimeout, navigator: {}, window, document,
                     genro: {publish: (topic, kw) => published.push({topic, kw}), wdg: {filterEvent: () => true}}};
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
        connect(obj, name, callback) {
            if (!obj || !callback) return null;
            const original = obj[name];
            obj[name] = function(...args) {
                const result = original && original.apply(this, args);
                callback.apply(this, args);
                return result;
            };
            return {obj, name, original};
        },
        disconnect(handle) { handle.obj[handle.name] = handle.original; },
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
    return {context, listeners, published, window};
}

// a tooltipPane opened on an anchor inside a scrolling container, the wrapper placed below it
function openTooltip({outer = null} = {}) {
    const env = createContext();
    let ddkw;
    const sourceNode = {
        getStringId: () => 'tp_1',
        getParentNode: () => ({getParentNode: () => null, getDomNode: () => ({})}),
        _: (tag, attrs) => {
            ddkw = attrs;
            return {_: () => ({})};
        }
    };
    env.context.gnr.widgets.TooltipPane.prototype.createContent(sourceNode, {}, null);
    const scroller = new FakeElement({left: 0, top: 100, width: 500, height: 300}, outer, 'auto');
    const other = new FakeElement({left: 600, top: 100, width: 200, height: 300});
    const anchor = new FakeElement({left: 50, top: 200, width: 40, height: 20}, new FakeElement({}, scroller));
    const wrapper = new FakeElement({});
    wrapper.style = {left: '50px', top: '220px'};
    const popup = {domNode: {parentNode: wrapper}, onClose() {}, destroy() {}};
    const open = (around) => ddkw.onOpenedPopup.call(sourceNode, {around, popup});
    open(anchor);
    const scroll = (target) => env.listeners.filter(l => l.type === 'scroll' && l.capture)
                                             .forEach(l => l.handler({target}));
    return Object.assign(env, {anchor, wrapper, popup, scroller, other, scroll, open});
}

test('the popup follows its anchor while an ancestor scrolls', () => {
    const {anchor, wrapper, scroller, scroll, published} = openTooltip();
    anchor.rect.top = 140;
    anchor.rect.left = 30;
    scroll(scroller);
    assert.equal(wrapper.style.top, '160px');
    assert.equal(wrapper.style.left, '30px');
    assert.deepEqual(published, []);
});

test('a page scroll leaves the popup where it is: wrapper and anchor move together', () => {
    const {anchor, wrapper, window, scroll} = openTooltip();
    window.pageYOffset = 100;
    anchor.rect.top = 100;
    scroll({});
    assert.equal(wrapper.style.top, '220px');
});

test('a scroll that does not contain the anchor is ignored', () => {
    const {anchor, wrapper, other, scroll, published} = openTooltip();
    anchor.rect.top = 10;
    scroll(other);
    assert.equal(wrapper.style.top, '220px');
    assert.deepEqual(published, []);
});

test('the anchor scrolled out of the container closes the popup', () => {
    const {anchor, scroller, scroll, published} = openTooltip();
    anchor.rect.top = 75;
    scroll(scroller);
    assert.equal(published.length, 1);
    assert.equal(JSON.stringify(published[0].topic), JSON.stringify({topic: 'close', nodeId: 'tp_1'}));
    assert.equal(published[0].kw.evt.target, scroller);
});

test('closing the popup removes the scroll listener', () => {
    const {popup, listeners} = openTooltip();
    assert.equal(listeners.length, 1);
    popup.onClose();
    assert.equal(listeners.length, 0);
});

test('an anchor without layout is not followed', () => {
    const env = createContext();
    const anchor = new FakeElement({});
    env.context.gnr.widgets.TooltipPane.prototype.followAnchor(
        {around: anchor, popup: {domNode: {parentNode: new FakeElement({})}}}, 'tp_1');
    assert.equal(env.listeners.length, 0);
});

test('a detached anchor closes the popup on the next scroll, wherever it happens', () => {
    const {anchor, other, scroll, published} = openTooltip();
    anchor.isConnected = false;
    scroll(other);
    assert.equal(published.length, 1);
});

test('an outer container clipping the scrolling one closes the popup', () => {
    const outer = new FakeElement({left: 0, top: 100, width: 500, height: 150}, null, 'hidden');
    const {anchor, scroller, scroll, published} = openTooltip({outer});
    anchor.rect.top = 260;
    scroll(scroller);
    assert.equal(published.length, 1);
});

test('a close vetoed by onClosing keeps the popup following its anchor', () => {
    const {anchor, wrapper, scroller, scroll, published} = openTooltip();
    anchor.rect.top = 75;
    scroll(scroller);
    assert.equal(published.length, 1);
    assert.equal(wrapper.style.top, '95px');
});

test('reopening on another anchor replaces the tracker instead of adding one', () => {
    const {popup, listeners, open, scroller} = openTooltip();
    open(new FakeElement({left: 50, top: 300, width: 40, height: 20}, scroller));
    assert.equal(listeners.length, 1);
    popup.onClose();
    assert.equal(listeners.length, 0);
});

test('destroying an open popup removes the scroll listener', () => {
    const {popup, listeners} = openTooltip();
    popup.destroy();
    assert.equal(listeners.length, 0);
});
