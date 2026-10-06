const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// Every rpc fails. 'expired': as on a page whose session is gone, a failed rpc
// returns {error} to a sync caller and queues handleRpcError, as
// genro_rpc.js resultHandler does with setTimeout. 'http400': the sync xhr
// calls handleRpcHttpError on the same stack, as genro_rpc.js errorHandler does.
const SERVER_CALL_CAP = 50;

function createPage(failure = 'expired') {
    const context = {console, gnr: {}, genro: {}};
    context.dojo = {
        declare(name, base, members) {
            function Declared(...args) {
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(Object.prototype), members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'genro_dev.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    const queue = [];
    const calls = {server: 0, ask: 0, message: 0, alert: 0};
    genro.mainGenroWindow = {genro};
    genro._pageLocals = {};
    genro.locale = () => 'it-IT';
    genro.getFromStorage = () => null;
    genro.setInStorage = () => {};
    genro.serverCall = () => {
        calls.server++;
        if (calls.server > SERVER_CALL_CAP) {
            throw new Error('server call cap reached');
        }
        if (failure === 'http400') {
            genro.dev.handleRpcHttpError({}, {xhr: {status: 400}});
            return undefined;
        }
        queue.push(() => genro.dev.handleRpcError('expired'));
        return {error: 'expired'};
    };
    genro.dlg = {
        message: () => { calls.message++; },
        alert: (msg, title) => {
            calls.alert++;
            context._T(title);
            context._T(msg);
        },
        ask: (title, msg) => {
            calls.ask++;
            context._T(msg);
            context._T(title);
        }
    };
    genro.dev = new context.gnr.GnrDevHandler();
    function drain(limit) {
        let steps = 0;
        while (queue.length && steps < limit) {
            queue.shift()();
            steps++;
        }
        return queue.length;
    }
    return {context, genro, calls, drain};
}

test('a failed translation falls back to the source string, once per page', () => {
    const {context, calls} = createPage();
    assert.equal(context._T('Expired session'), 'Expired session');
    assert.equal(context._T('Expired session'), 'Expired session');
    assert.equal(calls.server, 1);
});

test('the expired session dialog opens once', () => {
    const {genro, calls} = createPage();
    genro.dev.handleRpcError('expired');
    genro.dev.handleRpcError('expired');
    assert.equal(calls.ask, 1);
    assert.equal(calls.message, 1);
});

test('an expired rpc does not feed itself through the dialog translations', () => {
    const {genro, calls, drain} = createPage();
    genro.dev.handleRpcError('expired');
    assert.equal(drain(1000), 0);
    assert.equal(calls.ask, 1);
    assert.equal(calls.server, 0);
});

test('a sync http error does not recurse through the dialog translations', () => {
    const {context, calls} = createPage('http400');
    assert.equal(context._T('Some label'), 'Some label');
    assert.equal(calls.server, 1);
    assert.equal(calls.alert, 1);
});

test('a lost connection stops polling and asks the server for no translation', () => {
    const {context, genro, calls} = createPage('http400');
    genro.polling_enabled = true;
    genro.dev.handleRpcHttpError({}, {xhr: {status: 400}});
    genro.dev.handleRpcHttpError({}, {xhr: {status: 400}});
    assert.equal(calls.alert, 1);
    assert.equal(genro.polling_enabled, false);
    assert.equal(context._T('Another label'), 'Another label');
    assert.equal(calls.server, 0);
});

test('a window still stops polling when another window already marked the connection lost', () => {
    const {genro, calls} = createPage('http400');
    genro.mainGenroWindow = {genro: {_connectionLost: true}};
    genro.polling_enabled = true;
    genro.dev.handleRpcHttpError({}, {xhr: {status: 400}});
    assert.equal(genro.polling_enabled, false);
    assert.equal(calls.alert, 0);
});
