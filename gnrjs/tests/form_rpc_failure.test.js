const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// dojo 1.1 Deferred semantics (dojo/_base/Deferred.js _fire): a handler that
// returns a non-Error value moves the chain back to the callback side, so an
// error handler returning undefined turns an http failure into a callback
// with an undefined result.
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
    this.fired = res instanceof Error ? 1 : 0;
    this.results[this.fired] = res;
    this._fire();
};
Deferred.prototype.errback = function(err) {
    this.callback(err instanceof Error ? err : new Error(String(err)));
};
Deferred.prototype._fire = function() {
    let fired = this.fired;
    let res = this.results[fired];
    while (this.chain.length) {
        const f = this.chain.shift()[fired];
        if (!f) continue;
        try {
            res = f(res);
            fired = res instanceof Error ? 1 : 0;
        } catch (e) {
            fired = 1;
            res = e;
        }
    }
    this.fired = fired;
    this.results[fired] = res;
};

function createScenario({onSaved} = {}) {
    const calls = {rpc: [], alerts: [], locks: [], hider: [], events: [], loaded: 0, deleted: 0};
    const context = {console, File: function() {}, gnr: {}, genro: {}};
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
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
    Object.assign(context.genro, {
        _data: data,
        lockScreen: value => calls.locks.push(value),
        nodeById: () => null,
        callAfter: (fn, delay, scope) => fn.call(scope),
        dlg: {
            alert: (message, title, a, b, kw) => {
                calls.alerts.push(message);
                kw.confirmCb();
            },
            removeFloatingMessage: () => {}
        },
        rpc: {
            remoteCall: method => {
                const deferred = new Deferred();
                calls.rpc.push({method, deferred});
                return deferred;
            }
        }
    });
    const sourceNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    sourceNode.absDatapath = value => value;
    sourceNode.evaluateOnNode = value => value;
    sourceNode.setHiderLayer = value => calls.hider.push(value);
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode,
        formId: 'F_test',
        formDatapath: 'form.record',
        controllerPath: 'form.controller',
        pkeyPath: 'form.pkey',
        gridEditors: {},
        childForms: {},
        _status_list: [],
        isValid: () => true,
        isDisabled: () => false,
        disabledStatus: () => null,
        isProtectWrite: () => false,
        isNewRecord: () => false,
        publish: (topic, kw) => calls.events.push({topic, kw}),
        applyDisabledStatus: () => {},
        getVirtualColumns: () => '',
        loaded: () => { calls.loaded += 1; },
        deleted: () => { calls.deleted += 1; }
    });
    const storeProto = context.gnr.formstores.Base.prototype;
    const store = Object.create(storeProto);
    Object.assign(store, {
        form,
        table: 'test.table',
        onSaved,
        handlers: {
            load: {kw: {}, method: storeProto.load_recordCluster},
            save: {kw: {}, method: storeProto.save_recordCluster},
            del: {kw: {}, method: storeProto.del_recordCluster}
        }
    });
    form.store = store;
    form.resetChanges();
    function edit(field, value) {
        sourceNode.setRelativeData('form.record.' + field, value, null);
    }
    function topics() {
        return calls.events.map(e => e.topic);
    }
    function lastRpc() {
        return calls.rpc.at(-1);
    }
    return {form, store, record, Bag, calls, edit, topics, lastRpc};
}

function assertLoadRecovered(s) {
    assert.equal(s.calls.loaded, 0);
    assert.equal(s.calls.alerts.length, 1);
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.form.getCurrentPkey(), null);
    assert.equal(s.form.getControllerData('loading'), false);
    assert.equal(s.calls.hider.at(-1), false);
    assert.ok(s.topics().includes('onLoadFailed'));
    assert.ok(s.topics().includes('onDismissed'));
    s.form.load({destPkey: 'B'});
    assert.equal(s.calls.rpc.length, 2);
    assert.equal(s.form.opStatus, 'loading');
}

test('a load whose rpc fails at http level aborts the form instead of showing a stale record', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    assert.equal(s.lastRpc().method, 'loadRecordCluster');
    assert.equal(s.form.opStatus, 'loading');
    s.lastRpc().deferred.callback(undefined);
    assertLoadRecovered(s);
});

test('a load answered with an envelope error aborts the form', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback({error: 'server_exception'});
    assertLoadRecovered(s);
});

test('a load whose deferred fails does not leave the form locked in loading', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.errback(new Error('boom'));
    assertLoadRecovered(s);
});

function assertSaveRecovered(s) {
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.form.changed, true);
    assert.equal(s.form.getChangesLogger().len(), 1);
    assert.equal(s.form.getCurrentPkey(), 'MI');
    assert.equal(s.calls.locks.at(-1), false);
    assert.equal(s.form.lazySaving, false);
    assert.ok(s.topics().includes('onSaveFailed'));
    assert.ok(!s.topics().includes('onSaved'));
    const message = s.calls.events.find(e => e.topic === 'message');
    assert.equal(message.kw.messageType, 'error');
    s.form.save();
    assert.equal(s.calls.rpc.length, 2);
    assert.equal(s.form.opStatus, 'saving');
}

for (const onSaved of ['lazyReload', 'reload']) {
    test(`a save whose rpc fails at http level keeps the changes (onSaved=${onSaved})`, () => {
        const s = createScenario({onSaved});
        s.record.setItem('name', 'before', {}, {doTrigger: false});
        s.edit('name', 'after');
        s.form.lazySaving = true;
        s.form.save();
        assert.equal(s.lastRpc().method, 'saveRecordCluster');
        assert.equal(s.calls.locks.at(-1), true);
        s.lastRpc().deferred.callback(undefined);
        assertSaveRecovered(s);
    });
}

test('a save whose deferred fails keeps the changes', () => {
    const s = createScenario({onSaved: 'lazyReload'});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    s.lastRpc().deferred.errback(new Error('boom'));
    assertSaveRecovered(s);
});

test('a save answered with an envelope error keeps the changes', () => {
    const s = createScenario({onSaved: 'lazyReload'});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    s.lastRpc().deferred.callback({error: 'gnrexception'});
    assertSaveRecovered(s);
});

test('a silent envelope error resets the state without a message', () => {
    const s = createScenario({onSaved: 'lazyReload'});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    s.lastRpc().deferred.callback({error: 'gnrsilent'});
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.form.changed, true);
    assert.equal(s.calls.locks.at(-1), false);
    assert.ok(s.topics().includes('onSaveFailed'));
    assert.ok(!s.topics().includes('message'));
});

test('a successful save still resets the changes', () => {
    const s = createScenario({onSaved: 'lazyReload'});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    const result = new s.Bag();
    result.setItem('pkey', 'MI', {lastTS: '2026-01-01T00:00:00'});
    s.lastRpc().deferred.callback(result.getNode('pkey'));
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.form.changed, false);
    assert.ok(s.topics().includes('onSaved'));
});

test('a delete whose rpc fails at http level does not report the record as deleted', () => {
    const s = createScenario();
    s.form.do_deleteItem({});
    assert.equal(s.lastRpc().method, 'deleteDbRow');
    assert.equal(s.form.opStatus, 'deleting');
    s.lastRpc().deferred.callback(undefined);
    assert.equal(s.calls.deleted, 0);
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.calls.locks.at(-1), false);
    const message = s.calls.events.find(e => e.topic === 'message');
    assert.equal(message.kw.messageType, 'error');
    s.form.do_deleteItem({});
    assert.equal(s.calls.rpc.length, 2);
    s.lastRpc().deferred.callback(new s.Bag());
    assert.equal(s.calls.deleted, 1);
});
