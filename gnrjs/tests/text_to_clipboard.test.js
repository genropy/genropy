const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createPage({clipboard, secure = true, execCommand = () => true}) {
    const messages = [];
    const body = {children: [], appendChild(n) { this.children.push(n); }, removeChild(n) {
        this.children.splice(this.children.indexOf(n), 1);
    }};
    const document = {
        body,
        copied: [],
        createElement: () => ({style: {}, select() { document.selected = this.value; }}),
        execCommand(cmd) {
            const done = execCommand(cmd);
            if (done) document.copied.push(document.selected);
            return done;
        }
    };
    const context = {
        console, gnr: {}, dijit: {}, document,
        window: {isSecureContext: secure},
        navigator: clipboard ? {clipboard} : {}
    };
    context.dojo = {
        version: {major: 1, minor: 1},
        require: () => {},
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = text => text.replace(/^!!/, '');
    const genro = Object.create(context.gnr.GenroClient.prototype);
    genro.nodeById = id => id;
    genro.dlg = {floatingMessage: (node, kw) => messages.push([kw.message, kw.messageType || 'message'])};
    context.genro = genro;
    return {genro, messages, document, body};
}

test('a copy the browser grants shows the caller message', async () => {
    const written = [];
    const page = createPage({clipboard: {writeText: async text => { written.push(text); }}});
    const copied = await page.genro.textToClipboard('a\tb', '1 row copied');
    await new Promise(setImmediate);
    assert.equal(copied, true);
    assert.deepEqual(written, ['a\tb']);
    assert.deepEqual(page.messages, [['1 row copied', 'message']]);
});

test('a copy the browser refuses tells the user and skips the caller message', async () => {
    const refusal = Object.assign(new Error('Write permission denied'), {name: 'NotAllowedError'});
    const page = createPage({clipboard: {writeText: () => Promise.reject(refusal)}});
    let called = false;
    const copied = await page.genro.textToClipboard('a', () => { called = true; });
    await new Promise(setImmediate);
    assert.equal(copied, false);
    assert.equal(called, false);
    assert.deepEqual(page.messages, [['Copy to clipboard failed', 'error']]);
});

test('without navigator.clipboard the text is copied through a hidden textarea', async () => {
    const page = createPage({clipboard: null, secure: false});
    const copied = await page.genro.textToClipboard('plain http', 'Copied');
    await new Promise(setImmediate);
    assert.equal(copied, true);
    assert.deepEqual(page.document.copied, ['plain http']);
    assert.deepEqual(page.body.children, []);
    assert.deepEqual(page.messages, [['Copied', 'message']]);
});

test('an insecure page whose fallback copy fails tells the user', async () => {
    const page = createPage({
        clipboard: {writeText: () => assert.fail('navigator.clipboard is not used outside a secure context')},
        secure: false,
        execCommand: () => { throw new Error('unsupported'); }
    });
    const copied = await page.genro.textToClipboard('x', 'Copied');
    await new Promise(setImmediate);
    assert.equal(copied, false);
    assert.deepEqual(page.body.children, []);
    assert.deepEqual(page.messages, [['Copy to clipboard failed', 'error']]);
});
