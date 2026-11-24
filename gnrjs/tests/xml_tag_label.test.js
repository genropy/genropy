const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
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
    for (const filename of ['gnrlang.js', 'gnrbag.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

const ENTITIES = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'"};

// node has no XML parser: reject in each _tag what one would reject, then decode it
function tagAttributes(xml) {
    return [...xml.matchAll(/<\w+ _tag="([^"]*)"/g)].map(([, raw]) => {
        assert.doesNotMatch(raw, /</, `raw < in _tag="${raw}"`);
        assert.doesNotMatch(raw, /&(?!(amp|lt|gt|quot|apos|#\d+);)/, `bare & in _tag="${raw}"`);
        return raw.replace(/&(amp|lt|gt|quot|apos|#(\d+));/g,
                           (entity, name, code) => code ? String.fromCharCode(code) : ENTITIES[name]);
    });
}

test('a label with XML special characters round-trips through _tag', () => {
    const {gnr} = loadContext();
    const labels = ['Booklets & Guides', 'a<b', 'say "hi"', "it's", `"both' quotes"`];
    const bag = new gnr.GnrBag();
    labels.forEach((label, i) => bag.setItem(label, i));
    assert.deepEqual(tagAttributes(bag.toXml()), labels);
});
