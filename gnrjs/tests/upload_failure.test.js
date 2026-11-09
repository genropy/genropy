const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

class FakeXhr {
    constructor() {
        this.listeners = {};
        this.upload = {addEventListener() {}};
        this.status = 0;
        this.statusText = '';
        this.responseXML = null;
        FakeXhr.last = this;
    }
    addEventListener(name, cb) { (this.listeners[name] ||= []).push(cb); }
    open() {}
    send() {}
    fire(name) { (this.listeners[name] || []).forEach(cb => cb.call(this, {type: name})); }
    respond(status, statusText) {
        this.status = status;
        this.statusText = statusText;
        this.onload({type: 'load'});
    }
}

function createPage() {
    const context = {console, File: function() {}, FormData: class { append() {} }, XMLHttpRequest: FakeXhr,
                     gnr: {}, genro: {}};
    context.dojo = {
        declare(name, base, members) {
            function Declared() {}
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'genro_rpc.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    const toasts = [];
    const rpcErrors = [];
    Object.assign(context.genro, {
        page_id: 'p1',
        currentUrl: '/page',
        nodeById: () => null,
        src: {dynamicParameters: params => params},
        toast: {show: opts => toasts.push(opts)},
        dev: {handleRpcError: error => rpcErrors.push(error)}
    });
    const rpc = new context.gnr.GnrRpcHandler();
    rpc.serializeParameters = params => params;
    context.genro.rpc = rpc;
    return {context, rpc, toasts, rpcErrors};
}

function upload(page, kw = {}) {
    const calls = {result: 0, errors: []};
    page.rpc.uploadMultipart_oneFile({name: 'invoice.pdf'}, {}, Object.assign({
        onResult() { calls.result += 1; },
        onError(evt) { calls.errors.push({evt, sender: this}); }
    }, kw));
    return {xhr: FakeXhr.last, calls};
}

for (const [status, reason] of [[413, 'the file is too large for the server'],
                                [502, 'the server is busy or not responding, try again'],
                                [504, 'the server is busy or not responding, try again'],
                                [429, 'the server is busy or not responding, try again']]) {
    test(`an upload answered ${status} by the ingress is reported, not handed to onResult`, () => {
        const page = createPage();
        const {xhr, calls} = upload(page);
        xhr.respond(status, '');
        assert.equal(calls.result, 0);
        assert.equal(calls.errors.length, 1);
        assert.equal(calls.errors[0].sender, xhr);
        assert.equal(calls.errors[0].evt.status, status);
        assert.equal(page.toasts.length, 1);
        assert.equal(page.toasts[0].level, 'error');
        assert.equal(page.toasts[0].duration, 0);
        assert.equal(page.toasts[0].message, `invoice.pdf: ${reason}`);
    });
}

test('another http error names its status', () => {
    const page = createPage();
    const {xhr} = upload(page);
    xhr.respond(500, '');
    assert.equal(page.toasts[0].message, 'invoice.pdf: server error 500 Internal Server Error');
});

test('a connection lost is reported once even when error and timeout both fire', () => {
    const page = createPage();
    const {xhr, calls} = upload(page);
    xhr.fire('error');
    xhr.fire('timeout');
    assert.equal(calls.result, 0);
    assert.equal(calls.errors.length, 1);
    assert.equal(page.toasts.length, 1);
    assert.equal(page.toasts[0].message, 'invoice.pdf: the connection was lost');
});

test('a failure is reported even when the caller passes no onError', () => {
    const page = createPage();
    page.rpc.uploadMultipart_oneFile({name: 'invoice.pdf'}, {}, {onResult() { throw new Error('not a success'); }});
    FakeXhr.last.respond(413, '');
    assert.equal(page.toasts.length, 1);
});

test('a 200 with a plain text body is still a success', () => {
    const page = createPage();
    const {xhr, calls} = upload(page);
    xhr.respond(200, '');
    assert.equal(calls.result, 1);
    assert.equal(calls.errors.length, 0);
    assert.equal(page.toasts.length, 0);
});

test('an application error in the envelope goes to handleRpcError and onError, with the sender as this', () => {
    const page = createPage();
    const {xhr, calls} = upload(page);
    xhr.responseXML = {};
    page.context.gnr.GnrBag = class {
        fromXmlDoc() {}
        getItem(key) { return key === 'error' ? 'gnrexception' : null; }
        getNode() { return {}; }
    };
    xhr.respond(200, 'OK');
    assert.deepEqual(page.rpcErrors, ['gnrexception']);
    assert.equal(calls.result, 0);
    assert.equal(calls.errors.length, 1);
    assert.equal(calls.errors[0].sender, xhr);
    assert.equal(page.toasts.length, 0);
});
