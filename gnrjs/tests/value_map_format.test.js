const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const context = {console, TextEncoder, TextDecoder, Uint8Array, atob, btoa, gnr: {}, genro: {}};
    context.dojo = {
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

const DOLLAR_PATTERNS = ['A$&B', "A$`B", "A$'B", 'A$1B', 'A$$B'];

test('a value carrying a $ pattern rides through a wildcard label unchanged', () => {
    const {valueMapFormat} = createContext();
    for (const value of DOLLAR_PATTERNS) {
        assert.equal(valueMapFormat('A:Approvato,*:Altro [%s]', value), 'Altro [' + value + ']');
    }
});

test('a value carrying a $ pattern rides through the mask unchanged', () => {
    const {gnrformatter} = createContext();
    for (const value of DOLLAR_PATTERNS) {
        assert.equal(gnrformatter.asText(value, {dtype: 'T', format: 'A:Approvato,*:Altro [%s]',
                                                 mask: '[%s]'}),
                     '[Altro [' + value + ']]');
    }
});

test('a label carrying a $ pattern is not expanded either', () => {
    const {valueMapFormat} = createContext();
    assert.equal(valueMapFormat('A:Costo $$ alto,*:Altro', 'A'), 'Costo $$ alto');
});

test('the mapped and unmapped renderings are unchanged', () => {
    const {valueMapFormat, gnrformatter} = createContext();
    assert.equal(valueMapFormat('A:Approvato,R:Respinto', 'A'), 'Approvato');
    assert.equal(valueMapFormat('A:Approvato,R:Respinto', 'M'), 'M');
    assert.equal(valueMapFormat('A:Approvato,R:Respinto,*:Altro [%s]', 'M'), 'Altro [M]');
    assert.equal(valueMapFormat('HH:mm', '12'), '12');
    assert.equal(valueMapFormat('#,###', '12'), null);
    assert.equal(gnrformatter.asText('A', {dtype: 'T', format: 'A:Approvato', mask: '[%s]'}),
                 '[Approvato]');
});
