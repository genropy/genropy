// Copyright 2026 Softwell S.r.l. - SPDX-License-Identifier: LGPL-2.1-or-later
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

class TestEventTarget extends EventTarget {
    emit(type, detail) {
        const event = new Event(type);
        event.detail = detail;
        this.dispatchEvent(event);
    }
}

const published = [];
const frameSourceNode = {
    publish(topic) { published.push(['parent', topic]); },
};
const parentGenro = {
    page_id: 'parent-page',
    mainGenroWindow: {genro: {page_id: 'root-page'}},
};
const windowTarget = new TestEventTarget();
const documentTarget = new TestEventTarget();
documentTarget.documentElement = {dataset: {}};
windowTarget.parent = {genro: parentGenro};
windowTarget.location = {origin: 'http://example.test'};
windowTarget.frameElement = {sourceNode: frameSourceNode};

const context = vm.createContext({
    window: windowTarget,
    document: documentTarget,
    Object,
});
const source = readFileSync(new URL('../../../projects/test_invoice/gramlot_tools/minigenro.js', import.meta.url), 'utf8');
vm.runInContext(source, context);

const application = {
    renders: 0,
    messages: [],
    render() { this.renders += 1; },
    publish(topic, payload) { this.messages.push([topic, payload]); },
    dispose() { this.disposed = true; },
};
documentTarget.emit('gramlot:application-ready', {application});
assert.equal(windowTarget.gramlot, application);
assert.notEqual(windowTarget.genro, application);
const miniGenro = windowTarget.genro;
assert.equal(windowTarget._windowMessageReady, true);

documentTarget.emit('gramlot:content-ready', {application});
assert.equal(miniGenro._pageStarted, true);
assert.equal(miniGenro.parentGenro, parentGenro);
assert.equal(miniGenro.parent_page_id, 'parent-page');
assert.equal(frameSourceNode._genro, miniGenro);
assert.deepEqual(published, [['parent', 'pageStarted']]);

const message = new Event('message');
message.source = windowTarget.parent;
message.origin = windowTarget.location.origin;
message.data = {topic: 'changedStartArgs', customer_id: 42};
windowTarget.dispatchEvent(message);
assert.equal(application.messages.length, 1);
assert.equal(application.messages[0][0], 'changedStartArgs');
assert.equal(application.messages[0][1].customer_id, 42);

miniGenro.resizeAll();
miniGenro.publish({topic: 'onSelectedFrame'}, {});
assert.equal(application.renders, 1);
assert.equal(application.messages.at(-1)[0], 'onSelectedFrame');
assert.equal(Object.keys(application.messages.at(-1)[1]).length, 0);

const count = application.messages.length;
message.origin = 'https://untrusted.test';
windowTarget.dispatchEvent(message);
assert.equal(application.messages.length, count);
assert.equal(miniGenro.hasPendingChanges(), false);
assert.equal(miniGenro.checkBeforeUnload(), undefined);
assert.equal(application.parentGenro, undefined);
application.dispose();
assert.equal(windowTarget.genro, undefined);
assert.equal(application.disposed, true);
assert.equal(frameSourceNode._genro, undefined);
assert.equal(windowTarget.gramlot, undefined);
assert.equal(windowTarget._windowMessageReady, false);
