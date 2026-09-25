const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createRemote() {
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
    genro.dom = {pendingHeaders: {}};
    genro.fakeResize = () => {};
    genro.evaluate = (expr) => vm.runInContext('(' + expr + ')', context);
    context._T = (str) => str;
    const fetches = [];
    genro.rpc = {remoteCall(method, kwargs, mode, httpMethod, preventCache, cb) {
        fetches.push({resource: kwargs.resource, land: () => cb({resource: kwargs.resource})});
    }};
    genro._data.setItem('gnr.step.resource', 'first');
    const pane = genro.src._main._('div', 'pane', {}, {doTrigger: false});
    const node = pane._('contentPane', 'remote', {remote: 'remoteBuilder',
                                                 remote_resource: '^gnr.step.resource',
                                                 remote__waitingMessage: true},
                        {doTrigger: false}).getParentNode();
    const mounted = [];
    node.setHiderLayer = () => {};
    node.mergeRemoteContent = (result) => mounted.push(result.resource);
    return {context, genro, node, fetches, mounted};
}

//a sync rpc on the way to the fetch (the first _T of the page) lets dojo
//deliver an async response already in: the form load that moves the step
//lands inside the update still preparing the old one
function reenterOnce(context, genro, node) {
    const original = context._T;
    context._T = function(str) {
        context._T = original;
        genro._data.setItem('gnr.step.resource', 'second');
        node.updateRemoteContent(node);
        return str;
    };
}

function landAll(fetches) {
    for (let i = 0; i < fetches.length; i++) {
        fetches[i].land();
    }
}

test('an update re-entering before the fetch waits for the running one', () => {
    const {context, genro, node, fetches} = createRemote();
    reenterOnce(context, genro, node);
    node.updateRemoteContent();
    assert.deepEqual(fetches.map(f => f.resource), ['first']);
});

test('the step it re-entered for is the one left mounted', () => {
    const {context, genro, node, fetches, mounted} = createRemote();
    reenterOnce(context, genro, node);
    node.updateRemoteContent();
    landAll(fetches);
    assert.equal(mounted.at(-1), 'second');
});

test('a trigger during the flight re-fetches with fresh attributes', () => {
    const {genro, node, fetches, mounted} = createRemote();
    node.updateRemoteContent();
    genro._data.setItem('gnr.step.resource', 'second');
    node.updateRemoteContent(node);
    assert.equal(fetches.length, 1);
    landAll(fetches);
    assert.deepEqual(fetches.map(f => f.resource), ['first', 'second']);
    assert.equal(mounted.at(-1), 'second');
});

test('a condition that turns false releases the node', () => {
    const {genro, node, fetches, mounted} = createRemote();
    node.attr.remote__if = 'resource';
    genro._data.setItem('gnr.step.resource', null);
    node.updateRemoteContent(node);
    genro._data.setItem('gnr.step.resource', 'second');
    node.updateRemoteContent(node);
    assert.deepEqual(fetches.map(f => f.resource), ['second']);
    landAll(fetches);
    assert.deepEqual(mounted, ['second']);
});
