const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// Only the transport is stubbed: _serverCall_execute returns the request it
// would send, so the content built by the real _serverCall is inspected.
function createRpc(data = {}) {
    const context = {console, gnr: {}, genro: {}};
    context.dojo = {
        declare(name, base, members) {
            function Declared(...args) {
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    context.gnr.GnrBag = function () {};
    context.gnr.GnrBagResolver = function () {};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'genro_rpc.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    let counter = 0;
    genro.startArgs = {};
    genro.currentUrl = '/test/page';
    genro.getData = path => data[path];
    genro.getCounter = () => ++counter;
    genro.getServerLastTs = () => null;
    genro.getServerLastRpc = () => null;
    genro.src = {dynamicParameters: kwargs => kwargs};
    const rpc = new context.gnr.GnrRpcHandler({page_id: 'p1'});
    rpc.serializeParameters = kwargs => kwargs;
    rpc._serverCall_execute = (httpMethod, kw) => kw;
    return rpc;
}

test('a context tenant schema travels as temp_tenant_schema on a call', () => {
    const rpc = createRpc({'current.context_tenant_schema': 'foo'});
    const content = rpc._serverCall({method: 'dbCurrentEnv'}, {}).content;
    assert.equal(content.temp_tenant_schema, 'foo');
    assert.equal('env_tenant_schema' in content, false);
});

test('a false context tenant schema asks for the main schema', () => {
    const rpc = createRpc({'current.context_tenant_schema': false});
    assert.equal(rpc._serverCall({method: 'dbCurrentEnv'}, {}).content.temp_tenant_schema, '_main_');
});

test('no context tenant schema sends nothing', () => {
    const rpc = createRpc();
    assert.equal('temp_tenant_schema' in rpc._serverCall({method: 'dbCurrentEnv'}, {}).content, false);
});

test('rpc url args carry the context tenant schema as temp_tenant_schema', () => {
    const rpc = createRpc({'current.context_tenant_schema': 'foo'});
    const args = rpc.getRpcUrlArgs('dbCurrentEnv', {}, null);
    assert.equal(args.temp_tenant_schema, 'foo');
    assert.equal('env_tenant_schema' in args, false);
});
