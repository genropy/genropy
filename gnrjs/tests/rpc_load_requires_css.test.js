const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// loadRequires on the real genro_rpc.js: only genro.dom.addHeaders is stubbed,
// it records the headers the page would append (#148).
function createRpc() {
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
    const headers = [];
    context.genro.dom = {addHeaders: (urlist) => headers.push(...urlist)};
    const rpc = new context.gnr.GnrRpcHandler({page_id: 'p1'});
    return {rpc, headers};
}

function envelope(css_requires) {
    return {getItem: key => (key === 'css_requires' ? css_requires : undefined)};
}

test('a css name resolved to several files links every one of them', () => {
    const {rpc, headers} = createRpc();
    rpc.loadRequires(envelope({styles: ['/_rsrc/pkg_a/styles.css', '/_rsrc/pkg_b/styles.css']}));
    assert.deepEqual(headers.map(h => h.href), ['/_rsrc/pkg_a/styles.css', '/_rsrc/pkg_b/styles.css']);
});

test('a css name resolved to a single url still links it', () => {
    const {rpc, headers} = createRpc();
    rpc.loadRequires(envelope({styles: '/_rsrc/pkg_a/styles.css'}));
    assert.deepEqual(headers.map(h => h.href), ['/_rsrc/pkg_a/styles.css']);
});

test('a css name already loaded is not linked again', () => {
    const {rpc, headers} = createRpc();
    rpc.loadRequires(envelope({styles: ['/_rsrc/pkg_a/styles.css']}));
    rpc.loadRequires(envelope({styles: ['/_rsrc/pkg_a/styles.css']}));
    assert.equal(headers.length, 1);
});

test('a css name with no file links nothing', () => {
    const {rpc, headers} = createRpc();
    rpc.loadRequires(envelope({styles: null}));
    assert.equal(headers.length, 0);
});
