const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const PAYLOAD = '<img src=x onerror=window.__xss=1>';

function createContext() {
    const context = {console: {log() {}, warn() {}, error() {}}, gnr: {}, File: function() {},
                     setTimeout, clearTimeout};
    context.dojo = {
        require() {}, provide() {}, Deferred: function() {}, connect() {}, subscribe() {},
        mixin: Object.assign, isString: s => typeof s === 'string',
        declare(name, base, members) {
            const bases = [].concat(base || []);
            function Declared(...args) {
                for (const b of bases) b.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(bases.length ? bases[0].prototype : Object.prototype),
                                               ...bases.slice(1).map(b => b.prototype), members);
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context.genro = {
        safeHtmlContent: str => context.stripJsFromHtml(str),
        format: v => v,
        getData: () => undefined
    };
    return context;
}

// The title controller as th_form.py ships it: the client macro SET is left out, publish is captured.
function titleController(context) {
    const source = readFileSync(path.join(__dirname, '../../resources/common/th/th_form.py'), 'utf8');
    const body = source.match(/form\.dataController\("""([\s\S]*?onChangedTitle[\s\S]*?)"""/)[1]
                       .replace(/^\s*SET .*$/m, '');
    const run = vm.runInContext(`(function(newrecord, caption, record, titleTemplate, newTitleTemplate){${body}})`,
                                context);
    return kw => {
        const published = [];
        const form = {publish: (topic, payload) => published.push([topic, payload])};
        run.call({form}, kw.newrecord, kw.caption, kw.record, kw.titleTemplate, kw.newTitleTemplate);
        assert.equal(published.length, 1);
        assert.equal(published[0][0], 'onChangedTitle');
        return published[0][1].title;
    };
}

test('a record caption reaches the title as text', () => {
    const context = createContext();
    const title = titleController(context)({caption: PAYLOAD});
    assert.equal(title, '&lt;img src=x onerror=window.__xss=1&gt;');
    assert.ok(!title.includes('<'));
});

test('a new record caption reaches the title as text', () => {
    const context = createContext();
    const title = titleController(context)({newrecord: true, caption: `New ${PAYLOAD}`});
    assert.ok(!title.includes('<'));
});

test('ampersands and quotes in a caption stay readable once rendered', () => {
    const context = createContext();
    assert.equal(titleController(context)({caption: 'Rossi & "Figli"'}), 'Rossi &amp; &quot;Figli&quot;');
});

test('a missing caption gives an empty title', () => {
    const context = createContext();
    assert.equal(titleController(context)({caption: undefined}), '');
    assert.equal(titleController(context)({newrecord: true, caption: null}), '');
});

test('a titleTemplate keeps its markup and its field values lose active JS', () => {
    const context = createContext();
    const record = new context.gnr.GnrBag({description: PAYLOAD, code: 'A1'});
    const title = titleController(context)({record, caption: 'ignored',
                                            titleTemplate: '<b>$code</b> $description'});
    assert.ok(title.startsWith('<b>A1</b> '), title);
    assert.ok(!/onerror/i.test(title), title);
});
