const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// Each browser window runs its own copy of the sources against its own `genro`
// global, so the root page and its iframe are two sandboxes sharing one clock.
function createWindow(clock, mainGenro) {
    const intervals = new Map();
    let timerId = 0;
    const context = {
        console, gnr: {}, dijit: {}, window: {},
        Date: class extends Date {
            constructor(...args) {
                if (args.length) super(...args); else super(clock.now);
            }
        },
        setInterval: (cb, delay) => { intervals.set(++timerId, delay); return timerId; },
        clearInterval: id => intervals.delete(id),
        setTimeout: () => ++timerId,
        clearTimeout: () => {}
    };
    context.dojo = {
        version: {major: 1, minor: 1},
        require: () => {},
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro.js', 'genro_rpc.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = text => text;
    const locks = [];
    const alerts = [];
    const genro = Object.create(context.gnr.GenroClient.prototype);
    Object.assign(genro, {
        auto_polling: 30,
        user_polling: 3,
        page_id: mainGenro ? 'iframe' : 'root',
        root_page_id: mainGenro ? 'root' : null,
        dom: {addClass: () => {}, removeClass: () => {}},
        dlg: {alert: (msg, title) => alerts.push(title)},
        lockScreen: (locking, reason) => locks.push([locking, reason])
    });
    genro.mainGenroWindow = {genro: mainGenro || genro};
    genro.rpc = new context.gnr.GnrRpcHandler(genro);
    context.genro = genro;
    return {genro, intervals, locks, alerts};
}

function createPage() {
    const clock = {now: Date.parse('2026-10-06T10:00:00')};
    const root = createWindow(clock);
    root.genro.setAutoPolling();
    const iframe = createWindow(clock, root.genro);
    return {clock, root, iframe};
}

test('an outage seen by an iframe is locked, fast polled and restored by the root page', () => {
    const {clock, root, iframe} = createPage();
    iframe.genro.rpc._onServerError();
    clock.now += 6000;
    iframe.genro.rpc._onServerError();

    assert.deepEqual(root.locks, [[true, '_server_unavailable']]);
    assert.equal(root.genro.fast_polling, true);
    assert.deepEqual([...root.intervals.values()], [2000]);
    assert.deepEqual(iframe.locks, []);
    assert.equal(iframe.intervals.size, 0);

    iframe.genro.rpc._onServerSuccess();

    assert.deepEqual(root.locks.at(-1), [false, '_server_unavailable']);
    assert.deepEqual(root.alerts, ['Connection restored']);
    assert.deepEqual([...root.intervals.values()], [30000]);
    assert.deepEqual(iframe.alerts, []);
    assert.equal(iframe.intervals.size, 0);
});

test('errors from the root page and its iframe add up to one outage', () => {
    const {clock, root, iframe} = createPage();
    root.genro.rpc._onServerError();
    clock.now += 6000;
    iframe.genro.rpc._onServerError();
    assert.equal(root.genro.rpc._server_unavailable, true);

    root.genro.rpc._onServerSuccess();
    iframe.genro.rpc._onServerSuccess();
    assert.deepEqual(root.alerts, ['Connection restored']);
    assert.deepEqual(iframe.alerts, []);
});

test('setFastPolling called inside an iframe drives the root page polling', () => {
    const {root, iframe} = createPage();
    iframe.genro.setFastPolling(true);
    assert.equal(root.genro.fast_polling, true);
    assert.deepEqual([...root.intervals.values()], [2000]);

    iframe.genro.setFastPolling(false);
    assert.equal(root.genro.fast_polling, false);
    assert.deepEqual([...root.intervals.values()], [30000]);
    assert.equal(iframe.intervals.size, 0);
});

test('an iframe dropping its fast polling keeps the one the root page asked for', () => {
    const {root, iframe} = createPage();
    root.genro.setFastPolling(true);
    iframe.genro.setFastPolling(true);
    iframe.genro.setFastPolling(false);
    assert.equal(root.genro.fast_polling, true);
    assert.deepEqual([...root.intervals.values()], [2000]);

    root.genro.setFastPolling(false);
    assert.equal(root.genro.fast_polling, false);
    assert.deepEqual([...root.intervals.values()], [30000]);
});

test('an iframe that requests fast polling and is then closed brings the root back to auto polling', () => {
    const {root, iframe} = createPage();
    iframe.genro.notifyPageClosing = () => {};
    iframe.genro.setFastPolling(true);
    assert.equal(root.genro.fast_polling, true);

    iframe.genro.onWindowUnload();
    assert.equal(root.genro.fast_polling, false);
    assert.deepEqual([...root.intervals.values()], [30000]);
});

test('an iframe closed while the root page requests fast polling leaves the root request in place', () => {
    const {root, iframe} = createPage();
    iframe.genro.notifyPageClosing = () => {};
    root.genro.setFastPolling(true);
    iframe.genro.setFastPolling(true);

    iframe.genro.onWindowUnload();
    assert.equal(root.genro.fast_polling, true);
    assert.deepEqual([...root.intervals.values()], [2000]);
});

test('an iframe dropping its fast polling during an outage keeps the outage fast polling', () => {
    const {clock, root, iframe} = createPage();
    iframe.genro.setFastPolling(true);
    root.genro.rpc._onServerError();
    clock.now += 6000;
    root.genro.rpc._onServerError();
    iframe.genro.setFastPolling(false);
    assert.equal(root.genro.fast_polling, true);
    assert.deepEqual([...root.intervals.values()], [2000]);

    root.genro.rpc._onServerSuccess();
    assert.equal(root.genro.fast_polling, false);
    assert.deepEqual([...root.intervals.values()], [30000]);
});
