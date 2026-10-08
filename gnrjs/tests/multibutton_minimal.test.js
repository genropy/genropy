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
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        isIE: 0,
        require() {},
        provide() {},
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js', 'genro_widgets.js', 'genro_components.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    return context;
}

//the attributes createContent gives the container div
function buildContainer(kw) {
    const context = createContext();
    const built = [];
    const sourceNode = {
        attr: {},
        gnrwdg: {makeButtons() {}},
        registerDynAttr() {},
        getRelativeData: () => null,
        setRelativeData() {},
        _: (tag, name, attrs) => {
            built.push({tag, name, attrs});
            return {getParentNode: () => null};
        }
    };
    const subTagItems = {item: new context.gnr.GnrBag(), store: new context.gnr.GnrBag()};
    context.gnr.widgets.MultiButton.prototype.createContent(sourceNode, Object.assign({value: '^.mode'}, kw), null, subTagItems);
    return built.find(b => b.name == 'multibutton').attrs;
}

test('minimal adds its class to the container', () => {
    const attrs = buildContainer({minimal: true});
    assert.equal(attrs._class, 'multibutton_container multibutton_minimal');
    assert.equal('minimal' in attrs, false);
});

test('without minimal the container keeps its own class only', () => {
    assert.equal(buildContainer({})._class, 'multibutton_container');
});
