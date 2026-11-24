const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// A dialog taller than the window is capped and its size saved; when the window grows
// back the size is restored. On Android the keyboard shrinks the window while the login
// dialog shows fields after the avatar check: the saved size was smaller than the content.
function createContext(mainDiv) {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.document = {getElementById: id => (id == 'mainWindow' ? mainDiv : null)};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        isIE: 0,
        coords: node => ({h: node.offsetHeight, w: node.offsetWidth}),
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            // genro_widgets.js extends dijit classes this harness does not load
            Declared.prototype = Object.assign(Object.create(base && base.prototype ? base.prototype : Object.prototype), members);
            Declared.prototype.constructor = Declared;
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    context.dijit = {form: {ValidationTextBox: function() {}, CheckBox: function() {}}};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

// a dialog with a 1px border whose content has a natural size: resize() fixes the margin box,
// and the content overflowing a fixed box shows in scrollHeight as in the browser
function createDialog(content) {
    const mainDiv = {clientHeight: 812, clientWidth: 375};
    const context = createContext(mainDiv);
    const proto = context.gnr.widgets.Dialog.prototype;
    const fixed = {};
    const axis = (k, natural) => ({
        get offset() { return fixed[k] ?? natural() + 2; },
        get client() { return this.offset - 2; },
        get scroll() { return Math.max(this.client, natural()); }
    });
    const h = axis('h', () => content.h);
    const w = axis('w', () => content.w);
    const domNode = {
        get offsetHeight() { return h.offset; }, get clientHeight() { return h.client; },
        get scrollHeight() { return h.scroll; }, get offsetWidth() { return w.offset; },
        get clientWidth() { return w.client; }, get scrollWidth() { return w.scroll; }
    };
    const dialog = {
        sourceNode: {attr: {}},
        domNode,
        resize(c) { fixed.h = c.h; fixed.w = c.w; },
        layout() {},
        getContentMarginSize: proto.mixin_getContentMarginSize,
        adjustDialogSize: proto.mixin_adjustDialogSize
    };
    const setWindowHeight = height => {
        mainDiv.clientHeight = height;
        dialog.adjustDialogSize();
    };
    return {dialog, domNode, setWindowHeight};
}

test('a dialog whose content grew while capped is restored to the content size', () => {
    const content = {h: 235, w: 300};
    const {domNode, setWindowHeight} = createDialog(content);
    setWindowHeight(220);
    assert.equal(domNode.offsetHeight, Math.floor(220 * .98));
    content.h = 281;
    setWindowHeight(812);
    assert.equal(domNode.offsetHeight, 283);
    assert.equal(domNode.scrollHeight, domNode.clientHeight);
});

test('a dialog whose content did not change gets back the size it had', () => {
    const {domNode, setWindowHeight} = createDialog({h: 235, w: 300});
    setWindowHeight(220);
    setWindowHeight(812);
    assert.equal(domNode.offsetHeight, 237);
});

test('content grown beyond the window stays capped until the window can hold it', () => {
    const content = {h: 235, w: 300};
    const {dialog, domNode, setWindowHeight} = createDialog(content);
    setWindowHeight(220);
    content.h = 281;
    setWindowHeight(260);
    assert.equal(domNode.offsetHeight, Math.floor(260 * .98));
    assert.equal(dialog._starting_h, 283);
    setWindowHeight(812);
    assert.equal(domNode.offsetHeight, 283);
    assert.equal(dialog._starting_h, undefined);
});
