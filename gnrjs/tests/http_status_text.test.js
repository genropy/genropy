const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// A browser XHR exposes statusText as a configurable accessor on its own
// prototype, and over HTTP/2 that accessor returns '': this class does both.
function createXhrClass() {
    class FakeXhr {
        constructor(status, statusText) {
            this.status = status;
            this._statusText = statusText;
        }
    }
    Object.defineProperty(FakeXhr.prototype, 'statusText', {
        configurable: true,
        enumerable: true,
        get() { return this._statusText; }
    });
    return FakeXhr;
}

function createPage({fetchResponse} = {}) {
    const context = {console, setTimeout, clearTimeout, URL, Headers, AbortController};
    context.window = context;
    context.XMLHttpRequest = createXhrClass();
    context.DOMParser = class {};
    context.location = {origin: 'https://app.test'};
    context.document = {baseURI: 'https://app.test/page'};
    context.fetch = async () => fetchResponse;
    context.dojo = {
        xhr() {}, rawXhrPost() {}, rawXhrPut() {}, _ioCancelAll() {},
        byId: () => null,
        _ioAddQueryToUrl() {},
        _isDocumentOk: xhr => xhr.status >= 200 && xhr.status < 300,
        _contentHandlers: {text: xhr => xhr.responseText},
        _ioSetArgs(args, canceller, okHandler, errHandler) {
            let settle;
            const done = new Promise(resolve => { settle = resolve; });
            return {
                ioArgs: {args, url: args.url, query: null, handleAs: args.handleAs},
                done,
                callback(dfd) { settle({ok: okHandler(dfd)}); },
                errback(error) { settle({error: errHandler(error)}); }
            };
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'genro_patch.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    return context;
}

test('httpStatusText keeps a server reason phrase and fills a missing one', () => {
    const page = createPage();
    assert.equal(page.httpStatusText(200, ''), 'OK');
    assert.equal(page.httpStatusText(412, ''), 'Precondition Failed');
    assert.equal(page.httpStatusText(500, 'Custom'), 'Custom');
    assert.equal(page.httpStatusText(299, ''), '');
    assert.equal(page.httpStatusText(0, ''), '');
});

test('a native xhr answered over HTTP/2 reads statusText OK', () => {
    const page = createPage();
    page.genropatches.xhrStatusText();
    assert.equal(new page.XMLHttpRequest(200, '').statusText, 'OK');
    assert.equal(new page.XMLHttpRequest(404, '').statusText, 'Not Found');
});

test('a native xhr keeps the reason phrase HTTP/1.1 sent', () => {
    const page = createPage();
    page.genropatches.xhrStatusText();
    assert.equal(new page.XMLHttpRequest(200, 'Fine').statusText, 'Fine');
    assert.equal(new page.XMLHttpRequest(0, '').statusText, '');
});

test('installing the xhr patch twice wraps the accessor once', () => {
    const page = createPage();
    page.genropatches.xhrStatusText();
    const getter = Object.getOwnPropertyDescriptor(page.XMLHttpRequest.prototype, 'statusText').get;
    page.genropatches.xhrStatusText();
    assert.equal(Object.getOwnPropertyDescriptor(page.XMLHttpRequest.prototype, 'statusText').get, getter);
});

test('the fetch transport fills statusText when the response has none', async () => {
    const page = createPage({fetchResponse: {
        status: 200, statusText: '',
        headers: new Headers({'Content-Type': 'text/plain'}),
        text: async () => 'done'
    }});
    page.genropatches.dojoXhr('fetch');
    const dfd = page.dojo.xhr('POST', {url: '/page', handleAs: 'text'}, true);
    assert.deepEqual(await dfd.done, {ok: 'done'});
    assert.equal(dfd.ioArgs.xhr.statusText, 'OK');
});
