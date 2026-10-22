const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// genro.dlg.docPopup is the one popup of a page for the docs of grouplet
// cards and of field helpers; genro.dlg.docSource reads a doc address from
// sys/ep_doc once per page.

function createPage() {
    const docListeners = {};
    const context = {console, gnr: {}, setTimeout, Promise,
                     document: {addEventListener: (evt, h) => { docListeners[evt] = h; },
                                removeEventListener: (evt, h) => {
                                    if (docListeners[evt] === h) delete docListeners[evt];
                                }}};
    context.dojo = {
        Deferred: function() {},
        eval,
        toJson: JSON.stringify,
        isIE: 0,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_dlg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = (str) => str;
    const data = {'gnr.language': 'en', 'gnr.pagename': 'orders'};
    const published = [];
    const fetched = [];
    const responses = {};
    context.fetch = (url, opts) => {
        fetched.push([url, opts]);
        const address = decodeURIComponent(/address=([^&]*)/.exec(url)[1]);
        const answer = responses[address];
        if (answer instanceof Error) return Promise.reject(answer);
        return Promise.resolve({ok: !!answer, json: () => Promise.resolve(answer)});
    };
    const genro = context.genro = {
        page_id: 'PAGE1',
        isDeveloper: false,
        getData: (p) => data[p],
        publish: (topic) => published.push(topic),
        addParamsToUrl: (url, params) => url + '?' + Object.keys(params)
            .filter((k) => params[k] !== undefined && params[k] !== null)
            .map((k) => k + '=' + encodeURIComponent(params[k])).join('&')
    };
    genro.dlg = new context.gnr.GnrDlgHandler();
    const popups = [];
    genro.dlg.quickTooltipPane = (kw, cb) => {
        const built = [];
        const node = {_: (tag, attrs) => { built.push([tag, attrs]); return node; }};
        cb(node);
        popups.push({kw, built});
    };
    return {context, genro, data, popups, published, fetched, responses, docListeners};
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test('one popup for the page: title, body, a link for an address, Esc closes it', () => {
    const {genro, popups, published, docListeners} = createPage();
    const icon = {};
    genro.dlg.docPopup(icon, {title: 'Shipping', html: '<p>About</p>', address: 'grouplet:test:card_profile'});
    genro.dlg.docPopup(icon, {title: 'Again'});
    const [{kw, built}, second] = popups;
    assert.equal(kw.nodeId, 'doc_popup');
    assert.equal(kw.domNode, icon);
    assert.deepEqual(built.map(([tag, attrs]) => [tag, attrs._class]),
                     [['div', 'doc_popup_box'], ['div', 'doc_popup_title'], ['div', 'doc_popup_body'],
                      ['a', 'doc_popup_open']]);
    assert.equal(built[2][1].innerHTML, '<p>About</p>');
    assert.equal(built[3][1].href,
                 '/sys/ep_doc?address=grouplet%3Atest%3Acard_profile&language=en&_calling_page_id=PAGE1');
    assert.equal(built[3][1].target, '_blank');
    assert.equal(second.built[2][1].innerHTML, '!!No documentation available', 'no doc says so');
    genro.dlg.docPopup(icon, {address: 'grouplet:test:missing'});
    assert.deepEqual(popups[2].built.map(([tag]) => tag), ['div', 'div'], 'and offers no link to it');
    docListeners.keydown({key: 'a'});
    docListeners.keydown({key: 'Escape'});
    assert.deepEqual(published, ['doc_popup_opener_close']);
    assert.equal(docListeners.keydown, undefined, 'and stops listening');
});

test('a text is escaped, blank lines make paragraphs; a page of its own goes in an iframe', () => {
    const {genro, popups} = createPage();
    genro.dlg.docPopup({}, {text: ' a <b>bold</b> & x\nline 2\n\nsecond '});
    assert.equal(popups[0].built[1][1].innerHTML,
                 '<p>a &lt;b&gt;bold&lt;/b&gt; &amp; x<br>line 2</p><p>second</p>');
    genro.dlg.docPopup({}, {title: 'Install', page: true, address: 'docu::guide/install'});
    const frame = popups[1].built[2];
    assert.equal(frame[0], 'iframe');
    assert.deepEqual({...frame[1]}, {_class: 'doc_popup_frame', src: '/sys/ep_doc',
                                     src_address: 'docu::guide/install', src_language: 'en'});
});

test('docSource asks sys/ep_doc once per address for this page, null when it is not served', async () => {
    const {genro, fetched, responses} = createPage();
    responses['grouplet:test:card_profile'] = {title: 'Shipping', html: '<p>$city</p>'};
    responses['help:x.y:z'] = new Error('network');
    const got = [];
    const ask = (address) => genro.dlg.docSource(address, (s) => got.push([address, s && s.title]));
    ['grouplet:test:card_profile', 'grouplet:test:card_profile', 'grouplet:test:missing', 'help:x.y:z'].forEach(ask);
    await flush();
    assert.equal(fetched.length, 3, 'the same address is fetched once');
    assert.equal(fetched[0][0], '/sys/ep_doc?address=grouplet%3Atest%3Acard_profile&language=en'
                                + '&_calling_page_id=PAGE1&_fragment=1');
    assert.equal(fetched[0][1].credentials, 'same-origin');
    assert.deepEqual(got.sort(), [['grouplet:test:card_profile', 'Shipping'], ['grouplet:test:card_profile', 'Shipping'],
                                  ['grouplet:test:missing', null], ['help:x.y:z', null]]);
});

test('openDoc fills the template it is served and keeps the address for the link', async () => {
    const {genro, popups, responses} = createPage();
    responses['grouplet:test:card_profile'] = {title: 'Shipping', html: '<p>$city</p>'};
    genro.dlg.openDoc({}, 'grouplet:test:card_profile', {fill: (tpl) => tpl.replace('$city', 'Turin')});
    await flush();
    const built = popups[0].built;
    assert.equal(built[1][1].innerHTML, 'Shipping');
    assert.equal(built[2][1].innerHTML, '<p>Turin</p>');
    assert.equal(built[3][0], 'a');
});

function helperNode(context, helperValue) {
    const node = Object.create(context.gnr.GnrDomSourceNode.prototype);
    node.attr = {helpcode: 'delivery'};
    node.getInheritedAttributes = () => ({});
    node.getRelativeData = (p) => (p === 'gnr.helpers.orders.delivery?en' ? helperValue : null);
    node._labelNode = {domNode: {innerHTML: 'Delivery'}};
    return node;
}

test('helperbutton: a user sees the help in the doc popup, a developer with tools visible edits it', () => {
    const {context, genro, data, popups} = createPage();
    const node = helperNode(context, 'Leave it\n\nat the door');
    const button = {domNode: {}};
    node.onHelperClick(button);
    assert.equal(popups.length, 1);
    assert.equal(popups[0].kw.domNode, button.domNode);
    assert.deepEqual(popups[0].built.slice(1).map(([, attrs]) => attrs.innerHTML),
                     ['Delivery', '<p>Leave it</p><p>at the door</p>']);
    const prompts = [];
    genro.dlg.prompt = (title, kw) => prompts.push(kw.dflt);
    genro.isDeveloper = true;
    data['gnr.developerToolsVisible'] = true;
    node.onHelperClick(button);
    assert.deepEqual(prompts, ['Leave it\n\nat the door'], 'the in-place editor, as before');
    assert.equal(popups.length, 1);
});
