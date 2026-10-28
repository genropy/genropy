const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// funcApply (gnrlang.js) calls a widget action: a `function(a, b)` gets its
// arguments from the parameters, any other function (an arrow, a method) is
// called too, instead of failing on its missing `function(...)` signature.

function load() {
    const context = {console};
    context.dojo = {declare() {}, hitch: (o, m) => m, forEach: (items, cb) => Array.prototype.forEach.call(items || [], cb)};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    vm.runInContext(readFileSync(path.join(sourceDir, 'gnrlang.js'), 'utf8'), context, {filename: 'gnrlang.js'});
    return context;
}

test('a function(...) action still gets its arguments', () => {
    const {funcApply} = load();
    const seen = [];
    funcApply(function(a, b) { seen.push([a, b]); }, {a: 1, b: 2});
    assert.deepEqual(seen, [[1, 2]]);
});

test('an arrow function action is called too', () => {
    const {funcApply} = load();
    const scope = {};
    let calls = 0;
    funcApply(() => { calls++; }, {a: 1}, scope);
    funcApply(async () => { calls++; }, {}, scope);
    const obj = {action() { calls++; }};
    funcApply(obj.action, {}, scope);
    assert.equal(calls, 3);
});
