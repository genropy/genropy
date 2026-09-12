const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// A lightButton stops mousedown propagation, so dijit's document-level
// _onTouchNode has to be called by the button itself. That call is the only
// thing that blurs the widget being left SYNCHRONOUSLY, and a dijit textbox
// writes its value to the data bag from _onBlur: without it a click right
// after typing acts on the value the field had before the edit, because the
// native blur only reaches the widget through a 100ms timer.
//
// The real dijit focus manager is loaded here, not a stand-in: what is under
// test is the interplay between the button and that manager.

function createScope() {
    const context = {console, setTimeout, clearTimeout};
    context.window = context;
    const declared = {};
    context.dojo = {
        _hasResource: {},
        provide() {},
        mixin: (target, source) => Object.assign(target, source),
        connect: () => ({}),
        publish: () => {},
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        addOnLoad() {},
        isIE: 0,
        doc: {},
        global: context,
        body: () => context._body,
        byId: () => null,
        declare(name, base, members) {
            const bases = (Array.isArray(base) ? base : [base]).filter(Boolean);
            function Declared() {}
            let proto = Object.prototype;
            for (const one of bases) proto = Object.assign(Object.create(proto), one.prototype);
            Declared.prototype = Object.assign(Object.create(proto), members || {});
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            declared[name] = Declared;
            return Declared;
        }
    };
    context.dijit = {byId: (id) => context._widgets[id]};
    context.gnr = {widgets: {}};
    context.genro = {};
    context._widgets = {};
    context._body = {tagName: 'BODY'};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    const dijitFocus = path.join(__dirname,
        '../../dojo_libs/dojo_11/dojo_src/dijit/_base/focus.js');
    vm.runInContext(readFileSync(dijitFocus, 'utf8'), context, {filename: 'focus.js'});
    for (const filename of ['gnrlang.js', 'genro_widgets.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return {context, declared};
}

// A widget the focus manager can blur, registered in its active stack the way
// a focused textbox would be.
function focusedWidget(scope, id, ancestorOf) {
    const widget = {id, blurred: 0, _onBlur() { this.blurred++; }};
    scope.context._widgets[id] = widget;
    scope.context.dijit._setStack([id]);
    if (ancestorOf) ancestorOf.widgetId = id;
    return widget;
}

// The button's DOM node, and the ancestor chain _onTouchNode walks up.
function buttonNode(scope, {inside} = {}) {
    const node = {
        tagName: 'DIV',
        listeners: {},
        getAttribute(name) { return this[name] || null; },
        addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
    };
    node.parentNode = inside
        ? {tagName: 'DIV', getAttribute(name) { return this[name] || null; },
           widgetId: inside, parentNode: scope.context._body}
        : scope.context._body;
    return node;
}

function mousedown(node) {
    const event = {target: node, stopped: 0, stopPropagation() { this.stopped++; }};
    node.listeners.mousedown.forEach((fn) => fn(event));
    return event;
}

function buildButton(scope, options) {
    const LightButton = scope.declared['gnr.widgets.LightButton'];
    const node = buttonNode(scope, options);
    LightButton.prototype.created(node, {}, {_dynattr: {}});
    return node;
}

test('a mousedown on a lightButton blurs the widget being left', () => {
    const scope = createScope();
    const textbox = focusedWidget(scope, 'txt_1');
    mousedown(buildButton(scope));
    assert.equal(textbox.blurred, 1,
        'the edited field must commit its value before the click handler runs');
});

test('a lightButton still stops the mousedown from propagating', () => {
    const scope = createScope();
    focusedWidget(scope, 'txt_1');
    assert.equal(mousedown(buildButton(scope)).stopped, 1);
});

test('a lightButton does not blur the widget that contains it', () => {
    const scope = createScope();
    const node = buildButton(scope, {inside: 'palette_1'});
    const palette = focusedWidget(scope, 'palette_1', node.parentNode);
    mousedown(node);
    assert.equal(palette.blurred, 0,
        'an ancestor widget stays active: only the widgets left behind are blurred');
});
