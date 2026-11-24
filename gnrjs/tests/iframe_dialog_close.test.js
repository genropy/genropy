const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// The X of a modal page (genro.dlg.iframeDialog) goes through the root form of the
// page in the iframe: with pending changes it asks Save / Discard / Cancel and closes
// the dialog only when the changes are gone.

// dojo 1.1 Deferred semantics, as in form_rpc_failure.test.js
function isError(value) {
    return value instanceof Error || Object.prototype.toString.call(value) === '[object Error]';
}
function Deferred() {
    this.chain = [];
    this.fired = -1;
    this.results = [null, null];
}
Deferred.prototype.addCallbacks = function(cb, eb) {
    this.chain.push([cb, eb]);
    if (this.fired >= 0) this._fire();
    return this;
};
Deferred.prototype.addCallback = function(cb) { return this.addCallbacks(cb, null); };
Deferred.prototype.addErrback = function(eb) { return this.addCallbacks(null, eb); };
Deferred.prototype.addBoth = function(f) { return this.addCallbacks(f, f); };
Deferred.prototype.callback = function(res) {
    this.fired = isError(res) ? 1 : 0;
    this.results[this.fired] = res;
    this._fire();
};
Deferred.prototype._fire = function() {
    let fired = this.fired;
    let res = this.results[fired];
    while (this.chain.length) {
        const f = this.chain.shift()[fired];
        if (!f) continue;
        try {
            res = f(res);
            fired = isError(res) ? 1 : 0;
        } catch (e) {
            fired = 1;
            res = e;
        }
    }
    this.fired = fired;
    this.results[fired] = res;
};

function createScenario({autoSave = false, store = true, valid = true} = {}) {
    const calls = {rpc: [], pendingDialogs: [], events: [], hides: 0};
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, setInterval, clearInterval};
    context.dojo = {
        Deferred,
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_dlg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = value => value;
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const record = new Bag();
    data.setItem('form.record', record, {_pkey: 'MI'});
    data.setItem('form.controller', new Bag());
    data.setItem('form.pkey', 'MI');
    data.setBackRef();
    const genro = context.genro;
    Object.assign(genro, {
        _data: data,
        lockScreen: () => {},
        nodeById: () => null,
        callAfter: (fn, delay, scope) => fn.call(scope),
        src: {nodeBySourceNodeId: () => null},
        rpc: {
            remoteCall: method => {
                const deferred = new Deferred();
                calls.rpc.push({method, deferred});
                return deferred;
            },
            addDeferredCb: () => {}
        }
    });
    genro.dlg = new context.gnr.GnrDlgHandler();
    genro.dlg.removeFloatingMessage = () => {};
    // the Pending changes dialog: its slotbar action is what a button click runs
    genro.dlg.quickDialog = () => {
        const dialog = {
            center: {_: () => ({})},
            bottom: {_: (tag, kw) => {
                calls.pendingDialogs.push(command => kw.action.call({attr: {command}}));
                return {_: () => ({})};
            }},
            show_action() {},
            close_action() {}
        };
        return dialog;
    };
    const sourceNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    sourceNode.absDatapath = value => value;
    sourceNode.evaluateOnNode = value => value;
    sourceNode.setHiderLayer = () => {};
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode,
        formId: 'F_test',
        formDatapath: 'form.record',
        controllerPath: 'form.controller',
        pkeyPath: 'form.pkey',
        table_name: 'Record',
        gridEditors: {},
        childForms: {},
        _status_list: [],
        formErrors: new Bag(),
        autoSave,
        isValid: () => valid,
        getInvalidFields: () => [],
        isDisabled: () => false,
        disabledStatus: () => null,
        isProtectWrite: () => false,
        isNewRecord: () => false,
        applyDisabledStatus: () => {},
        getVirtualColumns: () => '',
        loaded: () => {},
        publish(topic, kw) {
            calls.events.push(topic);
            if (topic === 'pendingChangesAnswer') this.pendingChangesAnswer(kw);
        }
    });
    if (store) {
        const storeProto = context.gnr.formstores.Base.prototype;
        form.store = Object.assign(Object.create(storeProto), {
            form,
            table: 'test.table',
            handlers: {
                load: {kw: {}, method: storeProto.load_recordCluster},
                save: {kw: {}, method: storeProto.save_recordCluster},
                del: {kw: {}, method: storeProto.del_recordCluster}
            }
        });
    }
    form.resetChanges();
    const dlgNode = {
        widget: {hide: () => { calls.hides += 1; }},
        _iframeNode: {_genro: {_rootForm: form}}
    };
    function edit(field, value) {
        sourceNode.setRelativeData('form.record.' + field, value, null);
    }
    function clickX() {
        genro.dlg.iframeDialogClose(dlgNode);
    }
    function answer(command) {
        calls.pendingDialogs.at(-1)(command);
    }
    function saveSucceeds() {
        const result = new Bag();
        result.setItem('pkey', 'MI', {lastTS: '2026-01-01T00:00:00'});
        calls.rpc.at(-1).deferred.callback(result.getNode('pkey'));
    }
    // a field still focused: as dijit, its value reaches the record only when the focus
    // manager notices the blur, a while after focusNode.blur()
    function focusAndType(field, value) {
        const widget = {
            _focused: true,
            focusNode: {
                blur() {
                    setTimeout(() => {
                        widget._focused = false;
                        edit(field, value);
                    }, 100);
                }
            }
        };
        form.currentFocused = widget;
        return widget;
    }
    record.setItem('name', 'before', {}, {doTrigger: false});
    return {form, calls, dlgNode, edit, clickX, answer, saveSucceeds, focusAndType};
}

const settle = () => new Promise(resolve => setTimeout(resolve, 600));

test('with no pending changes the X closes at once', () => {
    const s = createScenario();
    s.clickX();
    assert.equal(s.calls.hides, 1);
    assert.equal(s.calls.pendingDialogs.length, 0);
});

test('with pending changes the X asks before closing', () => {
    const s = createScenario();
    s.edit('name', 'after');
    s.clickX();
    assert.equal(s.calls.pendingDialogs.length, 1);
    assert.equal(s.calls.hides, 0);
    assert.equal(s.form.changed, true);
});

test('Cancel keeps the dialog open with the changes', () => {
    const s = createScenario();
    s.edit('name', 'after');
    s.clickX();
    s.answer('cancel');
    assert.equal(s.calls.hides, 0);
    assert.equal(s.form.changed, true);
    assert.equal(s.form.getCurrentPkey(), 'MI');
});

test('Discard drops the changes and closes the dialog', () => {
    const s = createScenario();
    s.edit('name', 'after');
    s.clickX();
    s.answer('discard');
    assert.equal(s.form.changed, false);
    assert.equal(s.calls.hides, 1);
    assert.equal(s.calls.rpc.length, 0);
});

test('Save closes the dialog once the record is saved', () => {
    const s = createScenario();
    s.edit('name', 'after');
    s.clickX();
    s.answer('save');
    assert.equal(s.calls.rpc.length, 1);
    assert.equal(s.calls.hides, 0);
    s.saveSucceeds();
    assert.equal(s.form.changed, false);
    assert.equal(s.calls.hides, 1);
});

test('a save that fails keeps the dialog open with the changes', () => {
    const s = createScenario();
    s.edit('name', 'after');
    s.clickX();
    s.answer('save');
    s.calls.rpc.at(-1).deferred.callback({error: 'gnrsilent'});
    assert.equal(s.form.changed, true);
    assert.equal(s.calls.hides, 0);
});

test('Save on an invalid record keeps the dialog open', () => {
    const s = createScenario({valid: false});
    s.edit('name', 'after');
    s.clickX();
    s.answer('save');
    assert.equal(s.calls.rpc.length, 0);
    assert.equal(s.form.changed, true);
    assert.equal(s.calls.hides, 0);
});

test('a cancelled X leaves no subscription that closes the dialog later', () => {
    const s = createScenario();
    s.edit('name', 'after');
    s.clickX();
    s.answer('cancel');
    s.form.load({destPkey: '*dismiss*', discardChanges: true});
    assert.equal(s.form.changed, false);
    assert.equal(s.calls.hides, 0);
});

test('a value typed in a field that still has the focus is asked about, not lost', async () => {
    const s = createScenario();
    s.focusAndType('name', 'typed');
    s.clickX();
    assert.equal(s.calls.hides, 0);
    await settle();
    assert.equal(s.form.changed, true);
    assert.equal(s.calls.pendingDialogs.length, 1);
    assert.equal(s.calls.hides, 0);
    s.answer('discard');
    assert.equal(s.calls.hides, 1);
});

test('an autoSave form closes at once, as before', () => {
    const s = createScenario({autoSave: 2000});
    s.edit('name', 'after');
    s.clickX();
    assert.equal(s.calls.hides, 1);
    assert.equal(s.calls.pendingDialogs.length, 0);
});

test('a page without a root form closes at once, as before', () => {
    const s = createScenario();
    s.dlgNode._iframeNode._genro = {};
    s.clickX();
    assert.equal(s.calls.hides, 1);
});

test('an iframe that is not a genro page closes at once, as before', () => {
    const s = createScenario();
    delete s.dlgNode._iframeNode._genro;
    s.clickX();
    assert.equal(s.calls.hides, 1);
});
