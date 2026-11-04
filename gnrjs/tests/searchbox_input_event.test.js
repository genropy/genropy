const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, navigator: {}, window: {}, document: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        toJson: JSON.stringify,
        isIE: 0,
        require() {},
        provide() {},
        // dojo 1.1 on a DOM node: the event name loses its 'on' prefix
        connect: (node, name, handler) => node.addEventListener(name.startsWith('on') ? name.slice(2) : name, handler),
        declare(name, bases, members) {
            const base = Array.isArray(bases) ? bases[0] : bases;
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js', 'genro_components.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    return context;
}

// The search input of a SearchBox, its connect_* handlers wired as _doBuildNode does.
// Every write to .currentValue is what the box's dataController publishes as <nodeId>_changedValue.
function buildSearchInput() {
    const context = createContext();
    const built = [];
    const builder = {_: (tag, attrs) => (built.push({tag, attrs}), builder)};
    const boxNode = Object.assign({}, builder, {
        attr: {},
        setRelativeData() {},
        registerSubscription() {}
    });
    const widget = context.gnr.widgets.SearchBox.prototype;
    widget.createContent(boxNode, widget.contentKwargs(boxNode, {nodeId: 'sb_searchbox'}));
    const filtered = [];
    const activeSearch = [];
    context.genro.dom = {setClass: (node, cls, on) => activeSearch.push(on)};
    const input = new EventTarget();
    input.value = '';
    input.sourceNode = Object.assign(Object.create(context.gnr.GnrDomSourceNode.prototype), {
        attr: {},
        getParentNode: () => ({}),
        setRelativeData: (p, v) => filtered.push([p, v])
    });
    const attrs = built.find(b => b.tag == 'input').attrs;
    for (const k in attrs) {
        if (k.startsWith('connect_')) input.sourceNode.connect(input, k.slice(8), attrs[k]);
    }
    const type = text => {
        input.value = text;
        input.dispatchEvent(new Event('input'));
    };
    const keyup = () => input.dispatchEvent(new Event('keyup'));
    return {type, keyup, filtered, activeSearch};
}

test('text that arrives or goes with no key event filters', () => {
    const {type, filtered, activeSearch} = buildSearchInput();
    type('rossi');
    type('');
    assert.deepEqual(filtered, [['.currentValue', 'rossi'], ['.currentValue', '']]);
    assert.deepEqual(activeSearch, [true, false]);
});

test('a keystroke filters once and a key that changes no text filters nothing', () => {
    const {type, keyup, filtered} = buildSearchInput();
    type('r');
    keyup();
    keyup();
    assert.deepEqual(filtered, [['.currentValue', 'r']]);
});
