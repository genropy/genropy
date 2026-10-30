const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// A refused /_wsx/openchannel must not leave the page on an open socket with
// a rejected channelReady: create() returns early while channelReady is set,
// so every later call would fail until the socket happened to close.

const SOURCE = path.join(__dirname, '..', 'gnr_d11', 'js', 'gnrwebsocket_kajenn.js');

class FakeWebSocket {
    constructor(url) {
        this.url = url;
        this.readyState = 0;
        this.sent = [];
        this.closed = false;
        FakeWebSocket.instances.push(this);
    }
    send(text) {
        this.sent.push(JSON.parse(text.slice('WSX://'.length)));
    }
    close() {
        // the browser fires onclose asynchronously; the handler does not rely on
        // the order, so firing it here keeps the test deterministic
        this.closed = true;
        this.readyState = 3;
        this.onclose();
    }
    open() {
        this.readyState = 1;
        this.onopen();
    }
    answer(status, data) {
        const pending = this.sent[this.sent.length - 1];
        const envelope = {id: pending.id, status: status, data: '"' + data + '"'};
        this.onmessage({data: 'WSX://' + JSON.stringify(envelope)});
    }
}

function loadHandler() {
    FakeWebSocket.instances = [];
    const timeouts = [];
    let declared = null;
    const sandbox = {
        window: {location: {protocol: 'http:', host: 'localhost'}},
        WebSocket: FakeWebSocket,
        dojo: {declare: function(_name, _base, proto) { declared = proto; }},
        objectUpdate: function(target, source) { return Object.assign(target, source); },
        objectPop: function(obj, key) { const value = obj[key]; delete obj[key]; return value; },
        setTimeout: function(fn) { timeouts.push(fn); return timeouts.length; },
        clearTimeout: function() {},
        setInterval: function() { return 1; },
        clearInterval: function() {},
        console: {error: function() {}, debug: function() {}, log: function() {}},
        genro: {publish: function() {}},
        Promise: Promise,
        Error: Error,
        JSON: JSON,
        Object: Object
    };
    vm.runInNewContext(readFileSync(SOURCE, 'utf8'), sandbox, {filename: SOURCE});
    function Handler() {
        declared.constructor.apply(this, arguments);
    }
    Handler.prototype = declared;
    const handler = new Handler({page_id: 'page_1'}, '/websocket', {});
    return {handler, timeouts};
}

const settle = () => new Promise(resolve => setImmediate(resolve));

test('a refused channel closes the socket and resets channelReady', async () => {
    const {handler} = loadHandler();
    handler.create();
    const socket = FakeWebSocket.instances[0];
    socket.open();
    assert.equal(socket.sent[0].path, '/_wsx/openchannel');

    socket.answer(403, 'page of another connection');
    await settle();

    assert.equal(socket.closed, true);
    assert.equal(handler.channelReady, null);
});

test('after a refusal the reconnection opens the channel again', async () => {
    const {handler, timeouts} = loadHandler();
    handler.create();
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].answer(403, 'page of another connection');
    await settle();

    assert.equal(timeouts.length > 0, true);
    timeouts[timeouts.length - 1]();
    assert.equal(FakeWebSocket.instances.length, 2);

    const second = FakeWebSocket.instances[1];
    second.open();
    assert.equal(second.sent[0].path, '/_wsx/openchannel');
    second.answer(200, 'ok');
    await assert.doesNotReject(handler.channelReady);
});

test('an accepted channel leaves the socket open', async () => {
    const {handler} = loadHandler();
    handler.create();
    const socket = FakeWebSocket.instances[0];
    socket.open();
    socket.answer(200, 'ok');
    await handler.channelReady;

    assert.equal(socket.closed, false);
    assert.notEqual(handler.channelReady, null);
});
