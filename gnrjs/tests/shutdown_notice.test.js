const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// The shutdown announced to the connected users (#1903): the ping envelope carries
// 'shutdown' (reason, seconds_left) while it is pending; the main window keeps one
// persistent toast with the countdown and, when the entry disappears before its
// deadline, tells the user once that the shutdown was cancelled.
// The real genro_rpc.js, gnrbag.js and genro_dlg.js run here; only the XML parsing of
// the envelope and the toast DOM are stood in for.

function fakeElement() {
    const parts = {'.gnr-toast-title': {textContent: ''}, '.gnr-toast-message': {textContent: ''}};
    return {querySelector: selector => parts[selector], parts};
}

function createWindow({rootPageId = null} = {}) {
    const toasts = [];
    // unref: a countdown left running by a failing test must not keep the run alive
    const context = {console, File: function() {}, gnr: {}, genro: {}, Date, clearInterval,
                     setInterval: (callback, ms) => setInterval(callback, ms).unref()};
    context.dojo = {
        Deferred: function() {},
        eval,
        toJson: JSON.stringify,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        body: () => ({}),
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_rpc.js', 'genro_dlg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = value => value;
    const GnrBag = context.gnr.GnrBag;
    GnrBag.prototype.fromXmlDoc = function(items) {
        for (const [key, value] of Object.entries(items)) this.setItem(key, value);
    };
    const genro = context.genro;
    genro.root_page_id = rootPageId;
    genro.dom = {setClass() {}};
    genro.toast = {
        show(opts) {
            const el = fakeElement();
            const toast = {opts, el, dismissed: false};
            toasts.push(toast);
            el.toast = toast;
            return el;
        },
        dismiss(el) {
            el.toast.dismissed = true;
            if (el.toast.opts.onClose) el.toast.opts.onClose();
        }
    };
    genro.dlg = new context.gnr.GnrDlgHandler({});
    const rpc = new context.gnr.GnrRpcHandler({page_id: 'p1'});
    Object.assign(rpc, {unregister_call() {}, _onServerSuccess() {}, profileTime() {}, loadRequires() {}});
    genro.rpc = rpc;

    function respond(shutdown, {isPing = true} = {}) {
        const items = {result: null};
        if (shutdown) {
            const notice = new GnrBag();
            notice.setItem('reason', shutdown.reason);
            notice.setItem('seconds_left', shutdown.seconds_left);
            items.shutdown = notice;
        }
        rpc.resultHandler(items, {args: {isPing}});
    }
    return {genro, toasts, respond};
}

const banners = toasts => toasts.filter(t => t.opts.level === 'warning');
const cancelNotices = toasts => toasts.filter(t => t.opts.level === 'success');

test('a ping carrying shutdown shows one persistent toast with reason and countdown', () => {
    const {toasts, respond} = createWindow();
    respond({reason: 'Upgrading the application', seconds_left: 125});
    assert.equal(toasts.length, 1);
    const [banner] = toasts;
    assert.equal(banner.opts.level, 'warning');
    assert.equal(banner.opts.duration, 0);
    assert.equal(banner.el.parts['.gnr-toast-message'].textContent, 'Upgrading the application');
    assert.equal(banner.el.parts['.gnr-toast-title'].textContent, 'Shutdown in 2:05');
});

test('the next pings re-sync the countdown on the same toast', () => {
    const {toasts, respond} = createWindow();
    respond({reason: 'Upgrading', seconds_left: 125});
    respond({reason: 'Upgrading', seconds_left: 3725});
    assert.equal(toasts.length, 1);
    assert.equal(toasts[0].el.parts['.gnr-toast-title'].textContent, 'Shutdown in 1:02:05');
});

test('the reason markup is shown as text', () => {
    const {toasts, respond} = createWindow();
    respond({reason: '<b>Upgrade</b>', seconds_left: 60});
    assert.equal(toasts[0].opts.message, undefined);
    assert.equal(toasts[0].el.parts['.gnr-toast-message'].textContent, '<b>Upgrade</b>');
});

test('shutdown gone before its deadline: the toast goes and a cancel notice shows once', () => {
    const {toasts, respond} = createWindow();
    respond({reason: 'Upgrading', seconds_left: 60});
    respond(null);
    respond(null);
    assert.equal(banners(toasts)[0].dismissed, true);
    assert.equal(cancelNotices(toasts).length, 1);
});

test('shutdown gone after its deadline: the toast goes without a cancel notice', () => {
    const {toasts, respond} = createWindow();
    respond({reason: 'Upgrading', seconds_left: 0});
    respond(null);
    assert.equal(banners(toasts)[0].dismissed, true);
    assert.equal(cancelNotices(toasts).length, 0);
});

test('a toast the user closed stays closed until a new reason is announced', () => {
    const {genro, toasts, respond} = createWindow();
    respond({reason: 'Upgrading', seconds_left: 60});
    genro.toast.dismiss(toasts[0].el);
    respond({reason: 'Upgrading', seconds_left: 57});
    assert.equal(banners(toasts).length, 1);
    respond({reason: 'Moving to a new server', seconds_left: 300});
    assert.equal(banners(toasts).length, 2);
    assert.equal(toasts[1].el.parts['.gnr-toast-message'].textContent, 'Moving to a new server');
});

test('responses other than the ping leave the announcement alone', () => {
    const {toasts, respond} = createWindow();
    respond({reason: 'Upgrading', seconds_left: 60});
    respond(null, {isPing: false});
    assert.equal(toasts.length, 1);
    assert.equal(toasts[0].dismissed, false);
});

test('a page in an iframe leaves the announcement to the main window', () => {
    const {toasts, respond} = createWindow({rootPageId: 'root'});
    respond({reason: 'Upgrading', seconds_left: 60});
    assert.equal(toasts.length, 0);
});
