const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, navigator: {}, window: {}, document: {}};
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js', 'genro_components.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    context.genro.wdg = {getHandler: () => null};
    //the class of a built button lives on its DOM node
    context.genro.dom = {
        isElementOverflowing: () => false,
        setClass: (node, cls, set) => node.domNode.classList[set ? 'add' : 'remove'](cls)
    };
    return context;
}

//the buttons as makeButtons leaves them: the first one selected when created
function createMultiButton(builtCodes = []) {
    const context = createContext();
    const buttons = new context.gnr.GnrDomSource();
    for (const code of ['ios', 'android', 'web']) {
        buttons._('lightbutton', code, {
            multibutton_code: code,
            _class: code == 'ios' ? ' multibutton multibutton_selected' : ' multibutton'
        });
        const btn = buttons.getNode(code);
        if (builtCodes.includes(code)) {
            btn.domNode = {classList: new Set(btn.attr._class.split(' ').filter(Boolean))};
            btn.domNode.classList.remove = btn.domNode.classList.delete;
        }
    }
    const gnrwdg = Object.create(context.gnr.widgets.MultiButton.prototype);
    Object.assign(gnrwdg, {sticky: true, identifier: 'code', multibuttonSource: buttons});
    const selected = () => [...buttons.getNodes()].filter(n => n.domNode ? n.domNode.classList.has('multibutton_selected')
                                                                     : n.attr._class.split(' ').includes('multibutton_selected'))
                                             .map(n => n.attr.multibutton_code);
    return {gnrwdg, buttons, selected};
}

test('buttons still queued for build follow a new value', () => {
    const {gnrwdg, buttons, selected} = createMultiButton();
    gnrwdg.gnrwdg_setValue('android');
    assert.deepEqual(selected(), ['android']);
    assert.deepEqual([...buttons.getNodes()].map(n => n.attr._class), ['multibutton', 'multibutton multibutton_selected', 'multibutton']);
});

test('a multivalue selects every queued button it names', () => {
    const {gnrwdg, selected} = createMultiButton();
    gnrwdg.gnrwdg_setValue('android,web');
    assert.deepEqual(selected(), ['android', 'web']);
});

test('built buttons keep taking the class on their DOM node', () => {
    const {gnrwdg, buttons, selected} = createMultiButton(['ios', 'android']);
    gnrwdg.gnrwdg_setValue('web');
    assert.deepEqual(selected(), ['web']);
    //a built button's attributes are not where its class is read from
    assert.equal(buttons.getNodes()[0].attr._class, ' multibutton multibutton_selected');
});
