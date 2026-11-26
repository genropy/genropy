const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// The real handler; the site answers from `server` and GenroApp from `invoke`.
function createHandler({server, invoke}) {
    const calls = [];
    const context = {console: {log() {}}, gnr: {}};
    context.window = {location: {origin: 'https://app.test'}, top: {}};
    if (invoke) {
        context.window.__TAURI__ = {core: {invoke: async (command, args) => {
            calls.push([command, args]);
            return invoke(command, args);
        }}};
    }
    context.genro = {serverCall: (method, kwargs, callback) => {
        calls.push([method, kwargs]);
        callback(server[method](kwargs));
    }};
    context.dojo = {declare(name, base, members) {
        function Declared(...args) { members.constructor.apply(this, args); }
        Object.assign(Declared.prototype, members);
        context.gnr[name.split('.').at(-1)] = Declared;
    }};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    vm.runInContext(readFileSync(path.join(sourceDir, 'genro_genroapp.js'), 'utf8'), context,
                    {filename: 'genro_genroapp.js'});
    return {handler: new context.gnr.GnrGenroAppHandler(context.genro), calls};
}

const CHALLENGE = '_table.adm.user_device.confirmChallenge';
const SIGNED = '_table.adm.user_device.confirmSigned';
const signature = {key_id: 'k1', user: 'mario', signature: 'c2ln', connector_id: 'c1'};

test('a confirmation asks the challenge, GenroApp and the verification', async () => {
    const {handler, calls} = createHandler({
        server: {[CHALLENGE]: () => 'q0-_Zz9', [SIGNED]: () => true},
        invoke: () => signature
    });
    assert.equal(await handler.confirm('Approve payment 1234'), true);
    // the arguments are objects of the vm context: compared as JSON
    assert.deepEqual(JSON.parse(JSON.stringify(calls)), [
        [CHALLENGE, {text: 'Approve payment 1234'}],
        ['device_confirm', {origin: 'https://app.test', challenge: 'q0-_Zz9', text: 'Approve payment 1234'}],
        [SIGNED, {key_id: 'k1', signature: 'c2ln', connector_id: 'c1'}]
    ]);
});

test('a browser confirms nothing and asks nothing', async () => {
    const {handler, calls} = createHandler({server: {}});
    assert.equal(await handler.confirm('Approve payment 1234'), false);
    assert.deepEqual(calls, []);
});

test('a refused text stops before GenroApp', async () => {
    const {handler, calls} = createHandler({server: {[CHALLENGE]: () => null}, invoke: () => signature});
    assert.equal(await handler.confirm(' Approve'), false);
    assert.equal(calls.length, 1);
});

test('a cancelled identity check is not sent to the site', async () => {
    const {handler, calls} = createHandler({
        server: {[CHALLENGE]: () => 'q0-_Zz9'},
        invoke: () => { throw new Error('cancelled'); }
    });
    assert.equal(await handler.confirm('Approve payment 1234'), false);
    assert.equal(calls.length, 2);
});

test('a signature the site refuses does not confirm', async () => {
    const {handler} = createHandler({
        server: {[CHALLENGE]: () => 'q0-_Zz9', [SIGNED]: () => false},
        invoke: () => signature
    });
    assert.equal(await handler.confirm('Approve payment 1234'), false);
});
