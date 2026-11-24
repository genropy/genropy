const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test, mock} = require('node:test');
const vm = require('node:vm');

// genro.dlg.prompt: closing the last prompt clears gnr.promptDlg once the dialog
// is destroyed. A prompt opened in that window, typically from an asynchronous
// callback of the first one, must keep its data.

function load() {
    const context = {console, File: function() {}, setTimeout: (...args) => setTimeout(...args)};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
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
    context.gnr = {};
    context.genro = {locale: () => 'en-US'};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_dlg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    // the labels of the buttons need no translation here
    context._T = text => text;
    const genro = context.genro;
    genro._data = new context.gnr.GnrBag();
    genro.getData = datapath => genro._data.getItem(datapath);
    genro.getDataNode = datapath => genro._data.getNode(datapath);
    genro.setData = (datapath, value, attr) => genro._data.setItem(datapath, value, attr);
    genro.startArgs = {};
    genro.dev = {formbuilder: () => ({addField() {}})};
    genro.dlg = new context.gnr.GnrDlgHandler();
    const bars = [];
    genro.dlg.quickDialog = () => {
        const node = {widget: {}};
        return {
            bottom: {_: (tag, kw) => { bars.push(kw); return {_() {}}; }},
            center: {_: () => ({_() {}}), walk() {}, getParentNode: () => node},
            getParentNode: () => node,
            show_action() {},
            close_action() {}
        };
    };
    return {context, genro, bars};
}

function prompt(s, code, action) {
    s.genro.dlg.prompt('Prompt', {
        widget: [{value: '^.code', lbl: 'Code'}],
        dflt: new s.context.gnr.GnrBag({code}),
        action: action || (() => {})
    });
    return s.bars.at(-1).action;
}

test('a prompt opened while the previous one is closing keeps its data', () => {
    mock.timers.enable({apis: ['setTimeout']});
    try {
        const s = load();
        const confirmFirst = prompt(s, 'first');
        confirmFirst('confirm');
        // the second prompt opens before the first one is destroyed
        prompt(s, 'second');
        const datapath = 'gnr.promptDlg.prompt_1.promptvalue.code';
        assert.equal(s.genro.getData(datapath), 'second');
        mock.timers.tick(s.genro.dlg._quickDialogDestroyTimeout + 1);
        assert.equal(s.genro.getData(datapath), 'second');
    } finally {
        mock.timers.reset();
    }
});

test('the data of the prompts goes once the last one is closed', () => {
    mock.timers.enable({apis: ['setTimeout']});
    try {
        const s = load();
        prompt(s, 'only')('confirm');
        mock.timers.tick(s.genro.dlg._quickDialogDestroyTimeout + 1);
        assert.equal(s.genro.getData('gnr.promptDlg'), null);
    } finally {
        mock.timers.reset();
    }
});
