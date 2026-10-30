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
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

const context = loadContext();

function widgetNode(attr, wrapperLabel) {
    const node = Object.create(context.gnr.GnrDomSourceNode.prototype);
    node.label = 'dbSelect_0';
    node.attr = attr;
    let wrapper = null;
    if (wrapperLabel !== undefined) {
        wrapper = Object.create(context.gnr.GnrDomSourceNode.prototype);
        wrapper.attr = {tag: 'labledbox', label: wrapperLabel};
        wrapper.getAttributeFromDatasource = (name) => wrapper.attr[name];
    }
    node.getLabelWrapper = () => wrapper;
    return node;
}

test('a formlet lbl names the widget', () => {
    assert.equal(widgetNode({}, 'Articolo').getElementLabel(), 'Articolo');
});

test('without any label the node name is still the fallback', () => {
    assert.equal(widgetNode({}).getElementLabel(), 'DbSelect_0');
});

test('the placeholder label of an unlabeled button is not a name', () => {
    assert.equal(widgetNode({}, '&nbsp;').getElementLabel(), 'DbSelect_0');
});

test('an explicit label still wins over the formlet lbl', () => {
    assert.equal(widgetNode({error_label: 'Titolo'}, 'Articolo').getElementLabel(), 'Titolo');
    assert.equal(widgetNode({name_long: 'Edizione'}, 'Articolo').getElementLabel(), 'Edizione');
});
