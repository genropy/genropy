const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createWindow() {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        toJson: JSON.stringify,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
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
    for (const filename of ['gnrlang.js', 'gnrbag.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

// The values are built inside the window: guessDtype recognises arrays with instanceof Array.
const typedJSON = (win, source) => vm.runInContext(`toTypedJSON(${source})`, win);

test('toTypedJSON omits object keys whose value is undefined or a function', () => {
    const win = createWindow();
    const txt = typedJSON(win, '{a: 1, b: undefined, f() {}}');
    assert.equal(txt, '{"a":1}');
    assert.deepEqual(JSON.parse(txt), {a: 1});
});

test('toTypedJSON writes null for undefined or function array items', () => {
    const win = createWindow();
    const txt = typedJSON(win, '[1, undefined, function() {}]');
    assert.equal(txt, '[1,null,null]');
    assert.deepEqual(JSON.parse(txt), [1, null, null]);
});

test('toTypedJSON applies the same rules to nested values', () => {
    const win = createWindow();
    const txt = typedJSON(win, '{a: [1, undefined], b: {c: undefined}}');
    assert.equal(txt, '{"a":[1,null],"b":{}}');
    assert.deepEqual(JSON.parse(txt), {a: [1, null], b: {}});
});

test('toTypedJSON keeps null as null', () => {
    const win = createWindow();
    assert.equal(typedJSON(win, 'null'), 'null');
    const txt = typedJSON(win, '{a: null, b: [null]}');
    assert.equal(txt, '{"a":null,"b":[null]}');
    assert.deepEqual(JSON.parse(txt), {a: null, b: [null]});
});
