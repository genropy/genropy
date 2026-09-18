const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createSrc() {
    const context = {console, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
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
    genro.isDeveloper = false;
    genro.wdg = {getHandler: () => null};
    genro._data = new context.gnr.GnrBag();
    genro.src = new context.gnr.GnrSrcHandler({});
    //the batch monitor shape: a pane bound to an absolute datapath, a line
    //under a relative one, a widget subscribed to attributes of that line;
    //inserted silently, as there is no DOM to build into
    const silent = {doTrigger: false};
    const pane = genro.src._main._('div', 'pane', {datapath: 'gnr.batch.b1'}, silent);
    const paneNode = pane.getParentNode();
    const thermo = pane._('div', 'thermo', {datapath: '.thermo'}, silent);
    const thermoNode = thermo.getParentNode();
    const line = thermo._('div', 'l1', {datapath: '.l1'}, silent);
    const lineNode = line.getParentNode();
    const bar = line._('progressBar', 'bar', {progress: '^.?progress', maximum: '^.?maximum'}, silent);
    const barNode = bar.getParentNode();
    barNode._dynattr = {progress: true, maximum: true};
    barNode._setDynAttributes();
    const fired = [];
    barNode.trigger_data = (attr, kw) => fired.push(attr);
    function publish(dpath) {
        genro.src.triggerIndex.publish({evt: 'upd', pathlist: ('main.' + dpath).split('.'), updattr: true});
        const seen = fired.slice();
        fired.length = 0;
        return seen;
    }
    function indexed() {
        let trienode = genro.src.triggerIndex.root;
        for (const key of 'gnr.batch.b1.thermo.l1'.split('.')) {
            trienode = trienode.children[key];
            if (!trienode) return 0;
        }
        return (trienode.subs || []).length;
    }
    return {genro, paneNode, thermoNode, lineNode, barNode, publish, indexed};
}

test('the line widget is indexed under its absolute datapath', () => {
    const {genro, barNode, publish, indexed} = createSrc();
    assert.equal(indexed(), 2);
    assert.ok(genro.src._subscribedNodes[barNode.getStringId()]);
    assert.deepEqual(publish('gnr.batch.b1.thermo.l1').sort(), ['maximum', 'progress']);
});

test('content cleared while the node is frozen leaves the trigger index', () => {
    const {genro, thermoNode, barNode, publish, indexed} = createSrc();
    thermoNode.freeze();
    thermoNode.clearValue();
    assert.equal(barNode.getParentNode(), null);
    assert.equal(indexed(), 0);
    assert.equal(genro.src._subscribedNodes[barNode.getStringId()], undefined);
    assert.deepEqual(publish('gnr.batch.b1.thermo.l1'), []);
    assert.deepEqual(publish('gnr.batch.b1'), []);
});

test('a node popped under a frozen ancestor leaves the trigger index', () => {
    const {genro, thermoNode, lineNode, barNode, publish, indexed} = createSrc();
    thermoNode.freeze();
    lineNode._destroy();
    assert.equal(indexed(), 0);
    assert.equal(genro.src._subscribedNodes[barNode.getStringId()], undefined);
    assert.deepEqual(publish('gnr.batch.b1.thermo.l1'), []);
});

test('a same-bag rebuild under freeze keeps the subscriptions', () => {
    const {thermoNode, publish, indexed} = createSrc();
    thermoNode.freeze();
    thermoNode.rebuild();
    assert.equal(indexed(), 2);
    assert.deepEqual(publish('gnr.batch.b1.thermo.l1').sort(), ['maximum', 'progress']);
});

test('a frozen node with no discarded content is left alone', () => {
    const {paneNode, publish, indexed} = createSrc();
    paneNode.freeze();
    paneNode.setAttr({tip: 'x'});
    assert.equal(indexed(), 2);
    assert.deepEqual(publish('gnr.batch.b1.thermo.l1').sort(), ['maximum', 'progress']);
});

//the teardown the unfreeze rebuild can no longer do: it runs on the new value,
//so the discarded content never sees `_onDeleting` again, and an externalWidget
//hangs off no dijit parent, so no destroyRecursive reaches it either
function spyTeardown(node) {
    const seen = {deleted: false, widgetDestroyed: false};
    const original = node._onDeleting;
    node._onDeleting = function() {
        seen.deleted = true;
        return original.apply(this, arguments);
    };
    node.externalWidget = {destroy: () => {seen.widgetDestroyed = true;}};
    return seen;
}

test('content replaced under freeze is torn down, the frozen node is not', () => {
    const {thermoNode, lineNode, barNode} = createSrc();
    const thermo = spyTeardown(thermoNode);
    const line = spyTeardown(lineNode);
    const bar = spyTeardown(barNode);
    thermoNode.freeze();
    thermoNode.clearValue();
    assert.deepEqual(line, {deleted: true, widgetDestroyed: true});
    assert.deepEqual(bar, {deleted: true, widgetDestroyed: true});
    //the node whose content went is frozen, not dying: it rebuilds on unfreeze
    assert.deepEqual(thermo, {deleted: false, widgetDestroyed: false});
});

test('a node popped under a frozen ancestor is torn down with its content', () => {
    const {thermoNode, lineNode, barNode} = createSrc();
    const thermo = spyTeardown(thermoNode);
    const line = spyTeardown(lineNode);
    const bar = spyTeardown(barNode);
    thermoNode.freeze();
    lineNode._destroy();
    assert.deepEqual(line, {deleted: true, widgetDestroyed: true});
    assert.deepEqual(bar, {deleted: true, widgetDestroyed: true});
    assert.deepEqual(thermo, {deleted: false, widgetDestroyed: false});
});

test('a same-bag rebuild under freeze tears nothing down', () => {
    const {thermoNode, lineNode, barNode} = createSrc();
    const line = spyTeardown(lineNode);
    const bar = spyTeardown(barNode);
    thermoNode.freeze();
    thermoNode.rebuild();
    assert.deepEqual(line, {deleted: false, widgetDestroyed: false});
    assert.deepEqual(bar, {deleted: false, widgetDestroyed: false});
});
