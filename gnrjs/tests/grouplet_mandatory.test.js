const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createPanel({source = null, withForm = true, innerSource, draft = false} = {}) {
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
    const rootClasses = {};
    context.genro.dom = {setClass: (node, cls, on) => { rootClasses[cls] = on; }};
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const record = new Bag();
    record.setItem('company_name', 'Acme');
    record.setItem('source', source);
    if (draft) record.setItem('__is_draft', true);
    const menu = new Bag();
    const topic = new Bag();
    topic.setItem('company', null, {resource: 'main/company', grouplet_caption: 'Company', locationpath: 'record'});
    topic.setItem('status', null, {resource: 'main/status', grouplet_caption: 'Status', locationpath: 'record',
                                   mandatory: 'source', mandatory_path: 'record'});
    menu.setItem('main', topic, {resource: 'main', caption: 'Prospect record'});
    data.setItem('outer.record', record, {_pkey: 'PK1', _draft: draft});
    data.setItem('outer.controller', new Bag());
    data.setItem('panel.grouplet_menu', menu);
    data.setBackRef();
    context.genro._data = data;
    const sourceNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    sourceNode.absDatapath = value => value[0] === '.' ? 'panel' + value : value;
    sourceNode.getParentNode = () => ({});
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode,
        formDatapath: 'outer.record',
        controllerPath: 'outer.controller',
        pkeyPath: 'outer.pkey',
        gridEditors: {},
        _status_list: [],
        isDisabled: () => false,
        disabledStatus: () => null,
        isProtectWrite: () => false,
        isNewRecord: () => false,
        registeredGridsStatus: () => null,
        publish: () => {},
        applyDisabledStatus: () => {}
    });
    form.resetInvalidFields();
    form.resetChanges();
    if (withForm) sourceNode.form = form;
    let innerFormId = null;
    if (innerSource !== undefined) {
        const innerRecord = new Bag({company_name: 'Acme', source: innerSource});
        const innerForm = {status: 'error', store: {locationpath: 'outer.record'}, getFormData: () => innerRecord};
        context.genro.formById = formId => (formId === 'inner' ? innerForm : null);
        innerFormId = 'inner';
    }
    function checkNow() {
        context.gnr_grouplet.panelCheckMandatory(sourceNode, 'outer', innerFormId);
    }
    async function check() {
        checkNow();
        await new Promise(resolve => setTimeout(resolve, 5));
    }
    const recordNode = data.getNode('outer.record');
    return {form, record, recordNode, topic, menu, data, rootClasses, check, checkNow};
}

test('an incomplete mandatory grouplet is marked, its branch too, and the form is invalid', async () => {
    const s = createPanel();
    await s.check();
    assert.equal(s.topic.getNode('status').attr.mandatory_status, 'missing');
    assert.equal(s.topic.getNode('status').attr._class, 'grouplet_mandatory_missing');
    assert.equal(s.menu.getNode('main').attr.mandatory_status, 'branch');
    assert.equal(s.topic.getNode('company').attr.mandatory_status, undefined);
    assert.equal(s.form.isValid(), false);
    assert.deepEqual(Array.from(s.form.getFormErrors()), ['Incomplete group: Status']);
});

test('filling the mandatory field clears the marks and the form error', async () => {
    const s = createPanel();
    await s.check();
    s.record.setItem('source', 'website');
    await s.check();
    assert.equal(s.topic.getNode('status').attr.mandatory_status, null);
    assert.equal(s.menu.getNode('main').attr.mandatory_status, null);
    assert.equal(s.form.isValid(), true);
});

test('a complete record leaves the menu unmarked and the form valid', async () => {
    const s = createPanel({source: 'website'});
    await s.check();
    assert.equal(s.topic.getNode('status').attr.mandatory_status, undefined);
    assert.equal(s.form.isValid(), true);
});

test('the error comes back on the next check after a form reset', async () => {
    const s = createPanel();
    await s.check();
    s.form.resetInvalidFields();
    assert.equal(s.form.isValid(), true);
    await s.check();
    assert.equal(s.form.isValid(), false);
});

test('without a form only the menu is marked', async () => {
    const s = createPanel({withForm: false});
    await s.check();
    assert.equal(s.topic.getNode('status').attr.mandatory_status, 'missing');
    assert.equal(s.form.isValid(), true);
});

test('the open grouplet counts with its pending edits, not yet in the record', async () => {
    const s = createPanel({source: 'website', innerSource: null});
    await s.check();
    assert.equal(s.topic.getNode('status').attr.mandatory_status, 'missing');
    assert.equal(s.form.isValid(), false);
});

test('on a draft record the grouplet is only signalled and the form stays valid', async () => {
    const s = createPanel({draft: true});
    await s.check();
    assert.equal(s.topic.getNode('status').attr.mandatory_status, 'missing');
    assert.equal(s.data.getItem('panel.mandatory_enforced'), false);
    assert.equal(s.rootClasses.grouplet_mandatory_draft, true);
    assert.equal(s.form.isValid(), true);
});

test('confirming a draft makes the form invalid at once, for the save that follows', async () => {
    const s = createPanel({draft: true});
    await s.check();
    s.record.setItem('__is_draft', false);
    s.checkNow();
    assert.equal(s.data.getItem('panel.mandatory_enforced'), true);
    assert.equal(s.rootClasses.grouplet_mandatory_draft, false);
    assert.equal(s.form.isValid(), false);
});
