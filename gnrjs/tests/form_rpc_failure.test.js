const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// dojo 1.1 Deferred semantics (dojo/_base/Deferred.js _fire): a handler that
// returns a non-Error value moves the chain back to the callback side, so an
// error handler returning undefined turns an http failure into a callback
// with an undefined result.
// dojo tests it with `instanceof Error`; here the sources run in a vm sandbox
// with its own Error constructor, so the same-realm check has to be widened.
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
Deferred.prototype.errback = function(err) {
    this.callback(isError(err) ? err : new Error(String(err)));
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

const storeMethods = {
    recordCluster: {load: 'load_recordCluster', save: 'save_recordCluster', del: 'del_recordCluster'},
    rpc: {load: 'load_record', save: 'save_record', del: 'del_recordCluster'},
    document: {load: 'load_document', save: 'save_document', del: 'del_document'}
};

function createScenario({onSaved, store: storeType = 'recordCluster', handlerCallbacks = false} = {}) {
    const calls = {rpc: [], alerts: [], locks: [], hider: [], events: [], loaded: 0, deleted: 0,
                   handlerCallbacks: [], errbacks: []};
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
            },
            // same registration genro.rpc.addDeferredCb does for a non errback entry
            addDeferredCb: (deferred, func) => {
                deferred.addCallback(result => {
                    calls.handlerCallbacks.push({func, result});
                    return result;
                });
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
    const callbacks = handlerCallbacks ? [{getValue: () => 'handler_callback', attr: {}}] : null;
    const methods = storeMethods[storeType];
    Object.assign(store, {
        form,
        table: 'test.table',
        onSaved,
        handlers: {
            load: {kw: {}, method: storeProto[methods.load], callbacks},
            save: {kw: {}, method: storeProto[methods.save], callbacks},
            del: {kw: {}, method: storeProto[methods.del], callbacks}
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
    return {form, store, record, Bag, calls, edit, topics, lastRpc, genro: context.genro};
}

function countTopic(s, topic) {
    return s.topics().filter(t => t === topic).length;
}

// alerts defaults to 0: on a failure the platform reports itself the form only recovers
function assertLoadRecovered(s, {alerts = 0} = {}) {
    assert.equal(s.calls.loaded, 0);
    assert.equal(s.calls.alerts.length, alerts);
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.form.getCurrentPkey(), null);
    assert.equal(s.form.getControllerData('loading'), false);
    assert.equal(s.calls.hider.at(-1), false);
    assert.equal(countTopic(s, 'onLoadFailed'), 1);
    assert.ok(s.topics().includes('onDismissed'));
    s.form.load({destPkey: 'B'});
    assert.equal(s.calls.rpc.length, 2);
    assert.equal(s.form.opStatus, 'loading');
}

test('a load whose rpc fails at http level is announced, then aborts the form instead of showing a stale record', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    assert.equal(s.lastRpc().method, 'loadRecordCluster');
    assert.equal(s.form.opStatus, 'loading');
    s.lastRpc().deferred.callback(undefined);
    assertLoadRecovered(s, {alerts: 1});
});

test('a load answered with an envelope error aborts the form', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback({error: 'server_exception'});
    assertLoadRecovered(s);
});

test('a load whose deferred fails is announced and does not leave the form locked in loading', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.errback(new Error('boom'));
    assertLoadRecovered(s, {alerts: 1});
});

test('a load answered with an error nobody else reports is the one the form announces', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assertLoadRecovered(s, {alerts: 1});
});

test('a silent load failure restores the state without dismissing the form', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback({error: 'gnrsilent'});
    assert.equal(s.calls.alerts.length, 0);
    assert.equal(s.calls.loaded, 0);
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.form.getControllerData('loading'), false);
    assert.equal(s.calls.hider.at(-1), false);
    assert.equal(countTopic(s, 'onLoadFailed'), 1);
    assert.ok(!s.topics().includes('onDismissed'));
    assert.equal(s.form.getCurrentPkey(), 'A');
    assert.equal(s.calls.rpc.length, 1);
});

function createDbstoreScenario() {
    const s = createScenario();
    s.form.dbstoreField = 'dbstore';
    s.form.sourceNode.attr = {};
    return s;
}

test('a silent load failure on a dbstore form stays silent and keeps the form open', () => {
    const s = createDbstoreScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback({error: 'gnrsilent'});
    assert.equal(s.calls.alerts.length, 0);
    assert.equal(s.calls.loaded, 0);
    const failed = s.calls.events.find(e => e.topic === 'onLoadFailed');
    assert.equal(failed.kw.error.error, 'gnrsilent');
    assert.ok(!s.topics().includes('onDismissed'));
    assert.equal(s.form.getCurrentPkey(), 'A');
});

test('a load whose rpc fails at http level on a dbstore form is announced, then aborts the form', () => {
    const s = createDbstoreScenario();
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback(undefined);
    const failed = s.calls.events.find(e => e.topic === 'onLoadFailed');
    assert.deepEqual({...failed.kw.error}, {error: 'rpc_error'});
    assertLoadRecovered(s, {alerts: 1});
});

function assertSaveRecovered(s, {messages = 0} = {}) {
    assert.equal(s.form.opStatus == null, true);
    assert.equal(s.form.changed, true);
    assert.equal(s.form.getChangesLogger().len(), 1);
    assert.equal(s.form.getCurrentPkey(), 'MI');
    assert.equal(s.calls.locks.at(-1), false);
    assert.equal(s.form.lazySaving, false);
    assert.equal(countTopic(s, 'onSaveFailed'), 1);
    assert.ok(!s.topics().includes('onSaved'));
    assert.equal(countTopic(s, 'message'), messages);
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

test('a save answered with an error nobody else reports is the one the form announces', () => {
    const s = createScenario({onSaved: 'lazyReload'});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assertSaveRecovered(s, {messages: 1});
    const message = s.calls.events.find(e => e.topic === 'message');
    assert.equal(message.kw.messageType, 'error');
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
    assert.equal(countTopic(s, 'onDeleteFailed'), 1);
    assert.equal(countTopic(s, 'message'), 0);
    s.form.do_deleteItem({});
    assert.equal(s.calls.rpc.length, 2);
    s.lastRpc().deferred.callback(new s.Bag());
    assert.equal(s.calls.deleted, 1);
});

test('a delete answered with an error nobody else reports is the one the form announces', () => {
    const s = createScenario();
    s.form.do_deleteItem({});
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assert.equal(s.calls.deleted, 0);
    assert.equal(countTopic(s, 'onDeleteFailed'), 1);
    const message = s.calls.events.find(e => e.topic === 'message');
    assert.equal(message.kw.messageType, 'error');
});

test('a failed load leaves the chain on the error side', () => {
    const s = createScenario();
    s.form.load({destPkey: 'A'});
    const deferred = s.lastRpc().deferred;
    deferred.addErrback(failure => { s.calls.errbacks.push(failure); return failure; });
    deferred.callback({error: 'my_application_error'});
    assert.equal(deferred.fired, 1);
    assert.equal(s.calls.errbacks.length, 1);
    assert.equal(s.calls.errbacks[0].rpcFailure.error, 'my_application_error');
});

test('a failed load does not run the store handler callbacks', () => {
    const s = createScenario({handlerCallbacks: true});
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assert.equal(s.calls.handlerCallbacks.length, 0);
});

test('a successful load runs the store handler callbacks', () => {
    const s = createScenario({handlerCallbacks: true});
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback(new s.Bag());
    assert.equal(s.calls.handlerCallbacks.length, 1);
});

test('a failed delete does not run the store handler callbacks', () => {
    const s = createScenario({handlerCallbacks: true});
    s.form.do_deleteItem({});
    s.lastRpc().deferred.callback(undefined);
    assert.equal(s.calls.handlerCallbacks.length, 0);
});

test('a failed save does not run the store handler callbacks', () => {
    const s = createScenario({onSaved: 'lazyReload', handlerCallbacks: true});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    s.lastRpc().deferred.callback(undefined);
    assert.equal(s.calls.handlerCallbacks.length, 0);
});

test('a failed load does not run onReload', () => {
    const s = createScenario();
    const reloads = [];
    s.form.load({destPkey: 'A', onReload: result => reloads.push(result)});
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assert.equal(reloads.length, 0);
});

test('a successful load runs onReload', () => {
    const s = createScenario();
    const reloads = [];
    s.form.load({destPkey: 'A', onReload: result => reloads.push(result)});
    s.lastRpc().deferred.callback(new s.Bag());
    assert.equal(reloads.length, 1);
});

test('a failed delete does not run onDeleted', () => {
    const s = createScenario();
    const deletions = [];
    s.form.do_deleteItem({onDeleted: result => deletions.push(result)});
    s.lastRpc().deferred.callback(undefined);
    assert.equal(deletions.length, 0);
});

test('a successful delete runs onDeleted', () => {
    const s = createScenario();
    const deletions = [];
    s.form.do_deleteItem({onDeleted: result => deletions.push(result)});
    s.lastRpc().deferred.callback(new s.Bag());
    assert.equal(deletions.length, 1);
});

test('a save whose rpcmethod returns null is a committed save that keeps the current pkey', () => {
    const s = createScenario({store: 'rpc'});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    assert.equal(s.lastRpc().method, 'app.saveRecord');
    s.lastRpc().deferred.callback(null);
    assert.equal(s.lastRpc().deferred.fired, 0);
    assert.equal(s.form.getCurrentPkey(), 'MI');
    assert.equal(s.form.changed, false);
    assert.ok(s.topics().includes('onSaved'));
    assert.ok(!s.topics().includes('onSaveFailed'));
});

test('a recordCluster save answered with null is a committed save that keeps the current pkey', () => {
    const s = createScenario({onSaved: 'reload'});
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    assert.equal(s.lastRpc().method, 'saveRecordCluster');
    s.lastRpc().deferred.callback(null);
    const saved = s.calls.events.find(e => e.topic === 'onSaved');
    assert.equal(saved.kw.pkey, 'MI');
    assert.equal(s.form.getCurrentPkey(), 'MI');
    assert.equal(s.lastRpc().method, 'loadRecordCluster');
});

test('a load whose rpcmethod returns null is not a failure', () => {
    const s = createScenario({store: 'rpc'});
    s.form.load({destPkey: 'A'});
    assert.equal(s.lastRpc().method, 'app.getRecord');
    s.lastRpc().deferred.callback(null);
    assert.equal(s.lastRpc().deferred.fired, 0);
    assert.equal(s.calls.loaded, 1);
    assert.ok(!s.topics().includes('onLoadFailed'));
});

test('a failed document load is settled instead of crashing on the missing content', () => {
    const s = createScenario({store: 'document'});
    s.form.load({destPkey: 'A'});
    assert.equal(s.lastRpc().method, 'getSiteDocument');
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assert.equal(s.calls.loaded, 0);
    const failed = s.calls.events.find(e => e.topic === 'onLoadFailed');
    assert.equal(failed.kw.error.error, 'my_application_error');
    assertLoadRecovered(s, {alerts: 1});
});

test('a document load answered with null loads an empty content', () => {
    const s = createScenario({store: 'document'});
    s.form.load({destPkey: 'A'});
    s.lastRpc().deferred.callback(null);
    assert.equal(s.lastRpc().deferred.fired, 0);
    assert.equal(s.calls.loaded, 1);
    assert.ok(!s.topics().includes('onLoadFailed'));
});

// an application store method is free not to guard its own result: the settle
// registered by the form is then the only thing that can flip the chain
test('a failed load through an unguarded store method is still settled as a failure', () => {
    const s = createScenario();
    s.store.handlers.load.method = kw => s.genro.rpc.remoteCall('app.rawLoad', kw);
    const reloads = [];
    s.form.load({destPkey: 'A', onReload: result => reloads.push(result)});
    assert.equal(s.lastRpc().method, 'app.rawLoad');
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assert.equal(reloads.length, 0);
    assert.equal(s.lastRpc().deferred.fired, 1);
    assert.equal(countTopic(s, 'onLoadFailed'), 1);
});

test('a failed delete through an unguarded store method is still settled as a failure', () => {
    const s = createScenario();
    s.store.handlers.del.method = (pkey, kw) => s.genro.rpc.remoteCall('app.rawDelete', kw);
    const deletions = [];
    s.form.do_deleteItem({onDeleted: result => deletions.push(result)});
    assert.equal(s.lastRpc().method, 'app.rawDelete');
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assert.equal(deletions.length, 0);
    assert.equal(s.lastRpc().deferred.fired, 1);
    assert.equal(countTopic(s, 'onDeleteFailed'), 1);
});

test('a failed save through an unguarded store method is still settled as a failure', () => {
    const s = createScenario({onSaved: 'lazyReload'});
    s.store.handlers.save.method = kw => s.genro.rpc.remoteCall('app.rawSave', kw);
    s.record.setItem('name', 'before', {}, {doTrigger: false});
    s.edit('name', 'after');
    s.form.save();
    assert.equal(s.lastRpc().method, 'app.rawSave');
    s.lastRpc().deferred.callback({error: 'my_application_error'});
    assert.equal(s.lastRpc().deferred.fired, 1);
    assert.equal(countTopic(s, 'onSaveFailed'), 1);
    assert.equal(s.form.changed, true);
});
