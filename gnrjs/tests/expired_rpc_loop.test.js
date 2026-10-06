const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// Every rpc answers expired, as on a page whose session is gone. A failed rpc
// returns {error} to a sync caller and queues handleRpcError, as
// genro_rpc.js resultHandler does with setTimeout.
function createPage() {
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
    const calls = {server: 0, ask: 0, message: 0};
    genro._pageLocals = {};
    genro.locale = () => 'it-IT';
    genro.getFromStorage = () => null;
    genro.setInStorage = () => {};
    genro.serverCall = () => {
        calls.server++;
        queue.push(() => genro.dev.handleRpcError('expired'));
        return {error: 'expired'};
    };
    genro.dlg = {
        message: () => { calls.message++; },
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
    assert.equal(calls.server, 2);
});
