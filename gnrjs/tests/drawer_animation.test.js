const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const frames = new Map();
    let frameId = 0;
    const context = {
        console,
        File: function() {},
        gnr: {},
        genro: {fakeResize() {}},
        setTimeout,
        navigator: {},
        document: {},
        window: {
            matchMedia: () => ({matches: false}),
            requestAnimationFrame(callback) {
                frames.set(++frameId, callback);
                return frameId;
            },
            cancelAnimationFrame(id) {
                frames.delete(id);
            }
        }
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
        hasClass: (node, name) => (node.className || '').split(' ').includes(name),
        addClass(node, name) {
            node.className = [...new Set((node.className || '').split(' ').concat(name))].join(' ').trim();
        },
        removeClass(node, name) {
            node.className = (node.className || '').split(' ').filter(value => value !== name).join(' ');
        },
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
        },
        marginBox(node) {
            return {
                w: parseFloat(node.style.width) || 0,
                h: parseFloat(node.style.height) || 0
            };
        },
        style(node, property, value) {
            if (value !== undefined) node.style[property] = value;
            return node.style[property];
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js',
                            'genro_frm.js', 'genro_widgets.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context,
                        {filename});
    }
    context._T = str => str;
    context.flushFrame = timestamp => {
        const callbacks = [...frames.values()];
        frames.clear();
        callbacks.forEach(callback => callback(timestamp));
    };
    context.pendingFrames = () => frames.size;
    return context;
}

function createDrawer(attributes = {}, region = 'right') {
    const context = createContext();
    const node = {style: {display: '', width: '320px', height: '200px', overflow: 'auto'}};
    const sourceNode = {
        attr: Object.assign({drawer: true}, attributes),
        getAttributeFromDatasource(name) {
            return this.attr[name];
        }
    };
    const prototype = context.gnr.widgets.BorderContainer.prototype;
    const layouts = [];
    const widget = {
        domNode: {className: ''},
        _saved_size: {},
        _drawerAnimations: {},
        _splitters: {},
        _splitterThickness: {},
        _computeSplitterThickness() {},
        _layoutChildren() {
            layouts.push(parseFloat(node.style.width) || 0);
        }
    };
    widget[`_${region}`] = node;
    widget[`_${region}Widget`] = {sourceNode, domNode: node, region, parentBorderContainer: widget};
    sourceNode.widget = widget[`_${region}Widget`];
    sourceNode.getLabelWrapper = () => null;
    for (const name of ['mixin_setRegions', 'mixin_showHideRegion_one',
                        'mixin__showHideRegionImmediate',
                        'mixin__drawerAnimationKw', 'mixin__animateDrawerRegion',
                        'mixin__stopDrawerAnimation', 'mixin_setRegionVisible',
                        'mixin_isRegionVisible']) {
        widget[name.replace('mixin_', '')] = prototype[name];
    }
    return {context, layouts, node, widget};
}

test('drawers animate by default and restore their declared size', () => {
    const {context, layouts, node, widget} = createDrawer();
    assert.equal(widget._drawerAnimationKw('right').duration, 280);

    assert.equal(widget.showHideRegion_one('right', false), false);
    assert.equal(node.style.display, '');
    context.flushFrame(0);
    context.flushFrame(140);
    assert.ok(parseFloat(node.style.width) > 0);
    assert.ok(parseFloat(node.style.width) < 320);
    context.flushFrame(280);
    assert.equal(node.style.display, 'none');
    assert.equal(node.style.width, '320px');

    assert.equal(widget.showHideRegion_one('right', true), true);
    assert.equal(node.style.display, '');
    assert.equal(node.style.width, '0px');
    context.flushFrame(300);
    context.flushFrame(440);
    assert.ok(parseFloat(node.style.width) > 0);
    assert.ok(parseFloat(node.style.width) < 320);
    context.flushFrame(580);
    assert.equal(node.style.display, '');
    assert.equal(node.style.width, '320px');
    assert.ok(layouts.length >= 6);
});

test('drawer animation supports a custom duration and an explicit opt-out', () => {
    const custom = createDrawer({drawer_animate: 420});
    assert.equal(custom.widget._drawerAnimationKw('right').duration, 420);

    const disabled = createDrawer({drawer_animate: false});
    assert.equal(disabled.widget._drawerAnimationKw('right'), null);
    disabled.widget.showHideRegion_one('right', false);
    assert.equal(disabled.node.style.display, 'none');
});

test('top and bottom drawers animate their height', () => {
    const {context, node, widget} = createDrawer({}, 'top');
    widget.showHideRegion_one('top', false);
    context.flushFrame(0);
    context.flushFrame(140);
    assert.ok(parseFloat(node.style.height) > 0);
    assert.ok(parseFloat(node.style.height) < 200);
    context.flushFrame(280);
    assert.equal(node.style.display, 'none');
    assert.equal(node.style.height, '200px');
});

test('changing the size of an open drawer animates the shared layout', () => {
    const {context, node, widget} = createDrawer();
    widget.setRegions({region: 'right', size: '640px', show: true});
    assert.equal(node.style.width, '320px');
    context.flushFrame(0);
    context.flushFrame(140);
    assert.ok(parseFloat(node.style.width) > 320);
    assert.ok(parseFloat(node.style.width) < 640);
    context.flushFrame(280);
    assert.equal(node.style.width, '640px');
    assert.equal(node.style.display, '');
});

test('reapplying the current drawer state and size does not restart the animation', () => {
    const {context, layouts, node, widget} = createDrawer();
    widget.setRegions({region: 'right', size: '320px', show: true});
    assert.equal(context.pendingFrames(), 0);
    assert.equal(layouts.length, 0);
    assert.equal(node.style.width, '320px');

    widget.showHideRegion_one('right', true);
    assert.equal(context.pendingFrames(), 0);
});


test('a manually resized drawer keeps its new width across close and reopen', () => {
    const {context, node, widget} = createDrawer();
    widget._saved_size.right = '320px';
    node.style.width = '475px';
    widget.showHideRegion_one('right', false);
    context.flushFrame(0);
    context.flushFrame(280);
    assert.equal(node.style.width, '475px');
    widget.showHideRegion_one('right', true);
    context.flushFrame(300);
    context.flushFrame(580);
    assert.equal(node.style.width, '475px');
});

test('an immediate command cancels the pending animation and restores styles', () => {
    const {context, node, widget} = createDrawer();
    node.style.willChange = 'opacity';
    widget.showHideRegion_one('right', false);
    context.flushFrame(0);
    context.flushFrame(140);
    widget.showHideRegion_one('right', true, false);
    assert.equal(context.pendingFrames(), 0);
    assert.equal(node.style.width, '320px');
    assert.equal(node.style.overflow, 'auto');
    assert.equal(node.style.willChange, 'opacity');
    context.flushFrame(280);
    assert.equal(node.style.display, '');
});

test('rapid toggles reverse from the current width without losing the open size', () => {
    const {context, node, widget} = createDrawer();
    widget.showHideRegion_one('right', 'toggle');
    context.flushFrame(0);
    context.flushFrame(140);
    const partialWidth = node.style.width;
    widget.showHideRegion_one('right', 'toggle');
    assert.equal(node.style.width, partialWidth);
    assert.equal(context.pendingFrames(), 1);
    context.flushFrame(150);
    context.flushFrame(430);
    assert.equal(node.style.width, '320px');
    assert.equal(node.style.display, '');
});

for (const fallback of ['reduced motion', 'zero duration', 'missing requestAnimationFrame']) {
    test(`resizing an open drawer works with ${fallback}`, () => {
        const {context, node, widget} = createDrawer(fallback === 'zero duration' ? {drawer_duration: 0} : {});
        if (fallback === 'reduced motion') context.window.matchMedia = () => ({matches: true});
        if (fallback === 'missing requestAnimationFrame') delete context.window.requestAnimationFrame;
        widget.setRegions({region: 'right', size: '640px', show: true});
        assert.equal(node.style.width, '640px');
        assert.equal(node.style.display, '');
        assert.equal(context.pendingFrames(), 0);
    });
}

test('size plus toggle closes an open drawer and uses the new width on reopening', () => {
    const {context, node, widget} = createDrawer();
    widget.setRegions({region: 'right', size: '480px', show: 'toggle'});
    context.flushFrame(0);
    context.flushFrame(280);
    assert.equal(node.style.display, 'none');
    assert.equal(node.style.width, '480px');
    widget.showHideRegion_one('right', true, false);
    assert.equal(node.style.width, '480px');
});

test('a repeated target does not prolong an in-flight animation', () => {
    const {context, widget} = createDrawer();
    widget.showHideRegion_one('right', false);
    context.flushFrame(0);
    const state = widget._drawerAnimations.right;
    widget.showHideRegion_one('right', false);
    assert.equal(widget._drawerAnimations.right, state);
    context.flushFrame(280);
    assert.equal(context.pendingFrames(), 0);
});

test('regular regions remain immediate unless animation is explicitly enabled', () => {
    const plain = createDrawer({drawer: false});
    assert.equal(plain.widget._drawerAnimationKw('right'), null);
    plain.widget.showHideRegion_one('right', false);
    assert.equal(plain.node.style.display, 'none');
    const animated = createDrawer({drawer: false, drawer_animate: true}, 'left');
    animated.widget.setRegionVisible('left', false);
    assert.equal(animated.node.style.display, '');
    animated.context.flushFrame(0);
    animated.context.flushFrame(280);
    assert.equal(animated.node.style.display, 'none');
});

test('removing an animated child cancels all callbacks and restores its styles', () => {
    const {context, node, widget} = createDrawer();
    widget._closableRegions = {};
    widget.showHideRegion_one('right', false);
    context.flushFrame(0);
    delete widget._right;
    context.gnr.widgets.BorderContainer.prototype.onRemoveChild(widget, {region: 'right'});
    assert.equal(context.pendingFrames(), 0);
    assert.equal(node.style.width, '320px');
    assert.equal(node.style.overflow, 'auto');
    context.flushFrame(280);
});

for (const hidden of [true, false]) {
    test(`a later setHidden(${hidden}) takes precedence over an in-flight animation`, () => {
        const {context, node, widget} = createDrawer();
        widget.showHideRegion_one('right', !hidden, false);
        widget.showHideRegion_one('right', hidden);
        context.flushFrame(0);
        context.flushFrame(140);
        context.gnr.GnrDomSourceNode.prototype.setHidden.call(widget._rightWidget.sourceNode, hidden);
        assert.equal(context.pendingFrames(), 0);
        context.flushFrame(280);
        assert.equal(node.style.display, hidden ? 'none' : '');
        assert.equal(node.style.width, '320px');
        assert.equal(node.style.overflow, 'auto');
        assert.equal(context.dojo.hasClass(widget.domNode, 'gnrDrawerAnimating'), false);
    });
}

test('an immediate open during closable closing relayouts the restored width', () => {
    const {context, layouts, node, widget} = createDrawer({drawer: false, closable: true, closable_animate: true});
    widget._closableRegions = {right() {assert.fail('the closable is already open');}};
    widget.showHideRegion_one('right', false);
    context.flushFrame(0);
    context.flushFrame(140);
    widget.showHideRegion_one('right', true, false);
    assert.equal(node.style.width, '320px');
    assert.equal(layouts.at(-1), 320);
    assert.equal(context.pendingFrames(), 0);
});

test('scrollbars are suppressed until all simultaneous region animations stop', () => {
    const {context, widget} = createDrawer();
    widget._left = {style: {display: '', width: '200px', overflow: 'auto'}};
    widget._leftWidget = {sourceNode: widget._rightWidget.sourceNode};
    widget.showHideRegion_one('right', false);
    widget.showHideRegion_one('left', false);
    assert.equal(context.dojo.hasClass(widget.domNode, 'gnrDrawerAnimating'), true);
    widget.showHideRegion_one('right', true, false);
    assert.equal(context.dojo.hasClass(widget.domNode, 'gnrDrawerAnimating'), true);
    context.flushFrame(0);
    context.flushFrame(280);
    assert.equal(context.dojo.hasClass(widget.domNode, 'gnrDrawerAnimating'), false);
});

test('removing the animated region restores scrollbar styling', () => {
    const {context, widget} = createDrawer();
    widget._closableRegions = {};
    widget.showHideRegion_one('right', false);
    assert.equal(context.dojo.hasClass(widget.domNode, 'gnrDrawerAnimating'), true);
    context.gnr.widgets.BorderContainer.prototype.onRemoveChild(widget, {region: 'right'});
    assert.equal(context.dojo.hasClass(widget.domNode, 'gnrDrawerAnimating'), false);
});
