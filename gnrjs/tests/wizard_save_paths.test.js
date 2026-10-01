const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout};
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
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const groupletJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet.js');
    vm.runInContext(readFileSync(groupletJs, 'utf8'), context, {filename: 'grouplet.js'});
    context._T = str => str;
    return context;
}

function createForm(context, attrs = {}) {
    const watches = [];
    const sourceNode = {
        watch: (name, condition, callback) => watches.push({condition, callback})
    };
    const saved = [];
    const published = [];
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode,
        table_name: 'Invoice',
        gridEditors: {},
        opStatus: null,
        changed: true,
        isValid: () => false,
        isNewRecord: () => false,
        getControllerData: () => null,
        fireControllerData: () => {},
        getCurrentPkey: () => 'PK1',
        publish: (topic, kw) => published.push({topic, kw}),
        do_save: kw => saved.push(kw)
    }, attrs);
    return {form, watches, saved, published};
}

function stubQuickDialog(context) {
    const dialogs = [];
    const node = () => ({_: (tag, name, attrs) => {
        if (typeof name === 'object') [name, attrs] = [undefined, name];
        dialogs.at(-1).children.push({tag, name, attrs});
        return node();
    }});
    context.genro.dlg = {
        quickDialog: () => {
            dialogs.push({children: []});
            return {center: node(), bottom: node(), show_action: () => {}, close_action: () => {}};
        }
    };
    return dialogs;
}

test('the Pending changes dialog offers Save unless the form opts out', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    createForm(context).form.openPendingChangesDlg({});
    createForm(context, {pendingChangesSaveSlot: false}).form.openPendingChangesDlg({});
    const [regular, wizard] = dialogs.map(d => d.children);
    assert.equal(regular.find(c => c.tag === 'slotBar').attrs.slots, 'discard,*,cancel,save');
    assert.ok(regular.some(c => c.name === 'save'));
    assert.equal(wizard.find(c => c.tag === 'slotBar').attrs.slots, 'discard,*,cancel');
    assert.ok(!wizard.some(c => c.name === 'save'));
});

test('Shift on a dismiss does not save a form that opts out of Save', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    const regular = createForm(context, {isValid: () => true});
    regular.form.load_store({destPkey: '*dismiss*', modifiers: 'Shift'});
    assert.equal(regular.saved.length, 1);
    assert.equal(dialogs.length, 0);
    const wizard = createForm(context, {isValid: () => true, pendingChangesSaveSlot: false});
    wizard.form.load_store({destPkey: '*dismiss*', modifiers: 'Shift'});
    assert.equal(wizard.saved.length, 0);
    assert.equal(dialogs.length, 1);
});

test('Back saves an incomplete step also when a grid editor is still open', () => {
    const context = createContext();
    const step = createForm(context, {allowSaveInvalid: true});
    const grid = {gnrediting: true};
    step.form.gridEditors = {rows: {grid}};
    const frameData = {step_index: 1, wizard_steps: new context.gnr.GnrBag()};
    frameData.wizard_steps.setItem('one', null);
    frameData.wizard_steps.setItem('two', null);
    const frameNode = {
        getRelativeData: p => frameData[p.slice(1)],
        setRelativeData: (p, v) => { frameData[p.slice(1)] = v; }
    };
    context.genro.getFrameNode = () => frameNode;
    context.genro.formById = () => step.form;
    context.gnr_grouplet = vm.runInContext('gnr_grouplet', context);
    context.gnr_grouplet.wizardGoTo(null, 0, 'wiz');
    assert.equal(frameData.step_index, 0);
    assert.equal(step.saved.length, 0);
    assert.equal(step.watches.length, 1);
    grid.gnrediting = false;
    assert.ok(step.watches[0].condition());
    step.watches[0].callback();
    assert.equal(step.saved.length, 1);
    assert.ok(!step.published.some(p => p.topic === 'message'));
});
