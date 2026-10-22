const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// The docs of a page (genro_dlg.js): the icons of doc addresses learn in one
// request which docs exist and which the user may edit, the popup shows a doc,
// a documenter writes it in the editor and saves it to sys/ep_doc.

class FakeIcon {
    constructor() {
        this.attributes = {};
        const classes = new Set();
        this.classList = {add: (c) => classes.add(c), contains: (c) => classes.has(c),
                          toggle: (c, on) => (on ? classes.add(c) : classes.delete(c))};
    }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    getAttribute(name) { return this.attributes[name]; }
}

function createPage() {
    const icons = [];
    const docListeners = {};
    const context = {console, gnr: {}, setTimeout, Promise, URLSearchParams, Set,
                     document: {addEventListener: (evt, h) => { docListeners[evt] = h; },
                                removeEventListener: (evt, h) => {
                                    if (docListeners[evt] === h) delete docListeners[evt];
                                },
                                querySelectorAll: () => icons.filter((i) => i.getAttribute('data-doc-address'))}};
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_dlg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = (str) => str;
    const data = {'gnr.language': 'it'};
    const requests = [];
    const responses = [];
    context.fetch = (url, opts) => {
        const params = opts && opts.body ? Object.fromEntries(opts.body) : null;
        requests.push({url, method: (opts && opts.method) || 'GET', params});
        const [status, body] = responses.shift() || [404, null];
        return Promise.resolve({ok: status === 200, status, json: () => Promise.resolve(body)});
    };
    const published = [];
    const genro = context.genro = {
        page_id: 'PAGE1',
        getData: (p) => data[p],
        setData: (p, v) => { data[p] = v; },
        publish: (topic, kw) => published.push([topic, kw]),
        addParamsToUrl: (url, params) => url + '?' + Object.keys(params)
            .filter((k) => params[k] !== undefined && params[k] !== null && params[k] !== '')
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
    const dialogs = [];
    genro.dlg.quickDialog = (title, kw) => {
        const built = [];
        const area = (name) => ({_: (tag, label, attrs) => {
            built.push([name, tag, typeof label === 'string' ? attrs : label]);
            return area(name);
        }});
        const dlg = {title, kw, built, center: area('center'), bottom: area('bottom'), closed: false,
                     show_action() {}, close_action() { this.closed = true; }};
        dialogs.push(dlg);
        return dlg;
    };
    const newIcon = () => {
        const icon = new FakeIcon();
        icons.push(icon);
        return icon;
    };
    return {context, genro, data, requests, responses, popups, dialogs, published, docListeners, newIcon};
}

const flush = () => new Promise((resolve) => setImmediate(resolve));
const shown = (icon) => icon.classList.contains('doc_icon--shown');
const empty = (icon) => icon.classList.contains('doc_icon--empty');

test('the icons of a page ask sys/ep_doc in one request which docs exist and which may be edited', async () => {
    const page = createPage();
    const [a, b, c, a2] = [page.newIcon(), page.newIcon(), page.newIcon(), page.newIcon()];
    page.responses.push([200, {docs: {'field:adm.user:username': {language: 'it', mtime: 1}},
                               editable: ['field:adm.user:email']}]);
    page.genro.dlg.docTrack(a, 'field:adm.user:username');
    page.genro.dlg.docTrack(b, 'field:adm.user:email');
    page.genro.dlg.docTrack(c, 'field:sys.service:name');
    page.genro.dlg.docTrack(a2, 'field:adm.user:username');
    assert.ok(a.classList.contains('doc_icon') && !shown(a), 'hidden until the answer');
    await flush();
    await flush();
    assert.equal(page.requests.length, 1, 'one request for the page');
    const {method, params} = page.requests[0];
    assert.equal(method, 'POST');
    assert.deepEqual({...params}, {_index: '1', language: 'it', _calling_page_id: 'PAGE1',
                                   addresses: 'field:adm.user:username,field:adm.user:email,field:sys.service:name'});
    assert.ok(shown(a) && shown(a2) && !empty(a), 'an existing doc is shown to everybody');
    assert.ok(!shown(b) && !shown(c), 'an empty doc is hidden');
    page.data['gnr.docModeVisible'] = true;
    page.genro.dlg.docApplyStates();
    assert.ok(shown(b) && empty(b), 'documentation mode shows the empty doc a documenter may write, red');
    assert.ok(!shown(c), 'but not one of a package the user does not document');
    const late = page.newIcon();
    page.genro.dlg.docTrack(late, 'field:adm.user:username');
    assert.ok(shown(late) && page.requests.length === 1, 'a known address asks nothing');
});

test('the popup shows the doc with a link to its page and, to a documenter, Edit', () => {
    const page = createPage();
    const icon = {};
    let edited = 0;
    page.genro.dlg.docPopup(icon, {title: 'Username', html: '<p>Login</p>', address: 'field:adm.user:username',
                                   onEdit: () => edited++});
    const {kw, built} = page.popups[0];
    assert.equal(kw.nodeId, 'doc_popup', 'one popup for the page');
    assert.equal(kw.domNode, icon);
    assert.deepEqual(built.map(([tag, attrs]) => [tag, attrs._class]),
                     [['div', 'doc_popup_box'], ['div', 'doc_popup_title'], ['div', 'doc_popup_body'],
                      ['div', 'doc_popup_links'], ['a', 'doc_popup_open'], ['a', 'doc_popup_edit']]);
    assert.equal(built[4][1].href, '/sys/ep_doc?address=field%3Aadm.user%3Ausername&language=it&_calling_page_id=PAGE1');
    built[5][1].connect_onclick({preventDefault() {}});
    assert.equal(edited, 1);
    assert.deepEqual(page.published.map(([topic]) => topic), ['doc_popup_opener_close'], 'the popup closes first');
    page.docListeners.keydown({key: 'Escape'});
    assert.equal(page.docListeners.keydown, undefined, 'Esc closes it and stops listening');
    page.genro.dlg.docPopup(icon, {title: 'Missing'});
    assert.equal(page.popups[1].built[2][1].innerHTML, '!!No documentation available');
    assert.equal(page.popups[1].built.length, 4, 'no link and no Edit');
});

test('openDoc: a doc fills its template; an empty one opens the editor to a documenter, says so to others', async () => {
    const page = createPage();
    page.responses.push([200, {exists: true, editable: false, title: 'Shipping', html: '<p>$city</p>',
                               markdown: '$city', language: 'it', mtime: 5}]);
    await page.genro.dlg.openDoc({}, 'grouplet:test:card_profile', {fill: (html) => html.replace('$city', 'Turin')});
    assert.equal(page.popups[0].built[2][1].innerHTML, '<p>Turin</p>');
    assert.equal(page.popups[0].built.filter(([tag]) => tag === 'a').length, 1, 'no Edit without the tag');
    page.responses.push([200, {exists: false, editable: true, title: 'email', html: '', markdown: '',
                               language: 'it', mtime: null}]);
    await page.genro.dlg.openDoc({}, 'field:adm.user:email', {title: 'Email'});
    assert.equal(page.dialogs.length, 1, 'straight to the editor');
    assert.equal(page.dialogs[0].title, '!!Documentation · Email (it)');
    page.responses.push([404, null]);
    await page.genro.dlg.openDoc({}, 'field:sys.service:name', {title: 'Name'});
    assert.equal(page.popups[1].built[2][1].innerHTML, '!!No documentation available');
});

test('the editor saves the Markdown with relative images, then the doc shows for everybody', async () => {
    const page = createPage();
    const source = {exists: true, editable: true, title: 'Shipping', language: 'it', mtime: 7,
                    markdown: 'Zones ![map](assets/a.png)'};
    const icon = page.newIcon();
    page.genro.dlg._docStates = {'grouplet:test:card_profile': {exists: false, editable: true}};
    page.genro.dlg._docSources = {'grouplet:test:card_profile': Promise.resolve(source)};
    icon.setAttribute('data-doc-address', 'grouplet:test:card_profile');
    const dlg = page.genro.dlg.docEdit('grouplet:test:card_profile', {placeholders: () => ['city']}, source);
    const assets = '/sys/ep_doc?address=grouplet%3Atest%3Acard_profile&language=it&_calling_page_id=PAGE1&asset=';
    assert.equal(page.data['gnr.docEditor.markdown'], `Zones ![map](${assets}a.png)`, 'the editor shows the images');
    const editor = dlg.built.find(([, tag]) => tag === 'MDEditor')[2];
    assert.equal(editor.value, '^gnr.docEditor.markdown');
    assert.equal(editor.initialEditType, 'wysiwyg');
    assert.equal(dlg.built.find(([, tag, attrs]) => tag === 'div' && attrs._class === 'doc_editor_placeholders')[2]
        .innerHTML, '!!Variables: $city');
    page.data['gnr.docEditor.markdown'] = `Zones ![map](${assets}a.png) for $city`;
    page.responses.push([200, {mtime: 9}]);
    dlg.built.find(([, , attrs]) => attrs && attrs.label === '!!Save')[2].action();
    await flush();
    await flush();
    const {params} = page.requests.at(-1);
    assert.equal(params._save, '1');
    assert.equal(params.markdown, 'Zones ![map](assets/a.png) for $city', 'saved with relative images');
    assert.equal(params.base_mtime, '7');
    assert.equal(params.title, 'Shipping');
    assert.ok(dlg.closed);
    assert.ok(shown(icon) && !empty(icon), 'every icon of the address shows it now');
    assert.ok(!('grouplet:test:card_profile' in page.genro.dlg._docSources), 'read again on the next open');
});

test('a doc saved meanwhile by somebody else asks before overwriting', async () => {
    const page = createPage();
    const source = {exists: true, editable: true, title: 'T', language: 'it', mtime: 7, markdown: 'old'};
    page.genro.dlg._docStates = {};
    page.genro.dlg._docSources = {};
    const asked = [];
    page.genro.dlg.ask = (title, msg, buttons, actions) => asked.push(actions);
    const dlg = page.genro.dlg.docEdit('field:adm.user:email', {}, source);
    page.responses.push([409, {conflict: true, mtime: 8}]);
    dlg.built.find(([, , attrs]) => attrs && attrs.label === '!!Save')[2].action();
    await flush();
    assert.equal(asked.length, 1);
    assert.ok(!dlg.closed);
    page.responses.push([200, {mtime: 10}]);
    asked[0].overwrite();
    await flush();
    await flush();
    assert.equal(page.requests.at(-1).params.force, '1');
    assert.ok(dlg.closed);
});

test('a translation starts from another language and is saved as a new file', async () => {
    const page = createPage();
    const source = {exists: true, editable: true, title: 'T', language: 'en', mtime: 7, markdown: 'English'};
    page.genro.dlg._docStates = {};
    page.genro.dlg._docSources = {};
    const dlg = page.genro.dlg.docEdit('field:adm.user:email', {}, source);
    assert.equal(page.data['gnr.docEditor.markdown'], 'English');
    page.responses.push([200, {mtime: 1}]);
    dlg.built.find(([, , attrs]) => attrs && attrs.label === '!!Save')[2].action();
    await flush();
    assert.equal(page.requests.at(-1).params.language, 'it');
    assert.equal(page.requests.at(-1).params.base_mtime, undefined, 'no base: the Italian file is new');
});

test('an image pasted in the editor is stored next to the doc', async () => {
    const page = createPage();
    page.context.FileReader = class {
        readAsDataURL() { this.result = 'data:image/png;base64,AAAA'; this.onload(); }
    };
    page.responses.push([200, {link: 'assets/f00.png'}]);
    const link = await page.genro.dlg.docUploadImage('field:adm.user:email', {});
    assert.equal(link, 'assets/f00.png');
    assert.deepEqual({...page.requests[0].params}, {_asset: '1', address: 'field:adm.user:email',
                                                     dataUrl: 'data:image/png;base64,AAAA',
                                                     language: 'it', _calling_page_id: 'PAGE1'});
});
