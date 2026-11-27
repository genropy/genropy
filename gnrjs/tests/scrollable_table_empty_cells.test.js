const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// dbSelect appends a null_row with no auxiliary values, and nullable auxiliary fields
// leave cells empty: the typed formatter must not see the blank placeholder.
function setup() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout: () => {}};
    context.dojo = {
        Deferred: function() {}, eval, isIE: 0, toJson: JSON.stringify,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, cb) => Array.prototype.forEach.call(items || [], cb),
        some: (items, cb) => Array.prototype.some.call(items || [], cb),
        number: {format: (value, opt) => `N:${value}:${opt.pattern}`},
        date: {locale: {format(value) {
            if (!(value instanceof Date)) throw new TypeError('not a Date');
            return 'D:' + value.toISOString().slice(0, 10);
        }}},
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
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
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_dom.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

function render(rows) {
    const context = setup();
    const bag = new context.gnr.GnrBag();
    rows.forEach((attr, i) => bag.setItem('r_' + i, null, attr));
    const domnode = {innerHTML: ''};
    const handler = {getDomNode: node => node};
    context.gnr.GnrDomHandler.prototype.scrollableTable.call(handler, domnode, bag, {
        columns: ['amount', 'flag', 'day'], headers: ['Amount', 'Flag', 'Day'], tblclass: 'multiColumnSelect',
        colinfo: [{dtype: 'N', format: '#,##0.00'}, {dtype: 'B'}, {dtype: 'D'}]
    });
    return [...domnode.innerHTML.matchAll(/<tr id="[^"]*"[^>]*>(.*?)<\/tr>/g)]
        .map(m => [...m[1].matchAll(/<td style="([^"]*)">(.*?)<\/td>/g)].map(c => ({style: c[1], text: c[2]})));
}

test('the empty option renders blank cells for every dtype', () => {
    const [cells] = render([{}]);
    assert.deepEqual(cells.map(c => c.text), ['&nbsp;', '&nbsp;', '&nbsp;']);
});

test('a populated row is formatted and its numeric cell right-aligned', () => {
    const [, cells] = render([{}, {amount: 14.4, flag: true, day: new Date('2026-11-27T00:00:00Z')}]);
    assert.deepEqual(cells.map(c => c.text), ['N:14.4:#,##0.00', 'true', 'D:2026-11-27']);
    assert.match(cells[0].style, /text-align:right;/);
    assert.doesNotMatch(cells[1].style, /text-align:right;/);
});

test('false and zero are formatted, not blanked', () => {
    const [cells] = render([{amount: 0, flag: false}]);
    assert.deepEqual(cells.map(c => c.text), ['N:0:#,##0.00', 'false', '&nbsp;']);
});
