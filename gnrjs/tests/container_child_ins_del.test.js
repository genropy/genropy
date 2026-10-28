const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createBox(attributes, record) {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
        eval: expr => vm.runInContext(expr, context),
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        subscribe: () => ({}),
        unsubscribe: () => {},
        publish: () => {},
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_src.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    genro.evaluate = expr => vm.runInContext('(' + expr + ')', context);
    const Bag = context.gnr.GnrBag;
    // same string-only, space-separated contract as genro_dom add/removeClass
    const classNames = cls => typeof cls === 'string' ? cls.split(' ').filter(Boolean) : [];
    genro.dom = {
        addClass: (domnode, cls) => classNames(cls).forEach(c => domnode.classList.add(c)),
        removeClass: (domnode, cls) => classNames(cls).forEach(c => domnode.classList.delete(c))
    };
    genro.wdg = {
        getHandler: () => null,
        create(tag, destination, attrs, ind, sourceNode) {
            const domnode = {classList: new Set(), gnr: {}, innerHTML: attrs.innerHTML};
            sourceNode.domNode = domnode;
            return domnode;
        }
    };
    genro._dataroot = new Bag();
    genro._dataroot.setItem('main', new Bag());
    genro._data = genro._dataroot.getItem('main');
    genro._data.setItem('rec', new Bag(record));
    genro._dataroot.setBackRef();
    genro._dataroot.subscribe('dataTriggers', {any: kw => genro.src.triggerIndex.publish(kw)});
    genro.src = new context.gnr.GnrSrcHandler({});
    const silent = {doTrigger: false};
    const pane = genro.src._main._('div', 'pane', {datapath: 'rec'}, silent);
    pane._('div', 'box', Object.assign({tag: 'div'}, attributes), silent);
    const box = pane.getNode('box');
    box.build(null);
    return {
        set: (name, value) => genro._data.setItem('rec.' + name, value),
        del: (name) => genro._data.delItem('rec.' + name),
        html: () => box.domNode.innerHTML
    };
}

const rows = () => ({rows: {r1: {v: 1}, r2: {v: 2}}});

test('a == formula on a container follows the rows inserted and deleted under it', () => {
    const s = createBox({innerHTML: '==rows.len()', rows: '^.rows'}, rows());
    assert.equal(String(s.html()), '2');
    s.set('rows.r3', {v: 3});
    assert.equal(s.html(), 3);
    s.del('rows.r1');
    assert.equal(s.html(), 2);
});

test('a ?= formula on a container follows the rows inserted and deleted under it', () => {
    const s = createBox({innerHTML: '^.rows?=#v.len()'}, rows());
    s.set('rows.r3', {v: 3});
    assert.equal(s.html(), 3);
    s.del('rows.r1');
    assert.equal(s.html(), 2);
});
