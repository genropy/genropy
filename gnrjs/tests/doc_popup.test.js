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
    const editors = {};
    const genro = context.genro = {
        page_id: 'PAGE1',
        nodeById: (id) => editors[id] || null,
        getData: (p) => data[p],
        setData: (p, v) => { data[p] = v; },
        publish: (topic, kw) => published.push([topic, kw]),
        addParamsToUrl: (url, params) => url + '?' + Object.keys(params)
            .filter((k) => params[k] !== undefined && params[k] !== null && params[k] !== '')
            .map((k) => k + '=' + encodeURIComponent(params[k])).join('&')
    };
    genro.dlg = new context.gnr.GnrDlgHandler();
    // the page source as the help panel uses it: one named node, cleared and refilled
    const panels = [];
    let panelNode = null;
    const sourceNode = (built) => ({_: (tag, attrs) => { built.push([tag, attrs]); return sourceNode(built); }});
    genro.src = {getNode: (name) => {
        if (!name) return {_: () => { panelNode = panelNode || {}; }};
        if (!panelNode) return null;
        return Object.assign(panelNode, {
            freeze() {}, unfreeze() {},
            clearValue() { const built = []; panels.push(built); Object.assign(panelNode, sourceNode(built)); return panelNode; }
        });
    }};
    // the popup at an icon: one built content per opening
    const tooltips = [];
    genro.dlg.quickTooltipPane = (kw, contentCb) => {
        const built = [];
        contentCb(sourceNode(built));
        tooltips.push({kw, built});
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
    return {context, genro, data, requests, responses, panels, tooltips, dialogs, published, docListeners, newIcon,
            editors};
}

const flush = () => new Promise((resolve) => setImmediate(resolve));
// the index request leaves on a setTimeout(0): wait past it and its promises
const settle = () => new Promise((resolve) => setTimeout(resolve, 5));
const shown = (icon) => icon.classList.contains('doc_icon--shown');
const empty = (icon) => icon.classList.contains('doc_icon--empty');
const classes = (built) => built.map(([tag, attrs]) => [tag, attrs._class]);
const byClass = (built, cls) => (built.find(([, attrs]) => attrs._class === cls) || [])[1];
const escape = (target) => {
    const evt = {key: 'Escape', target, stopPropagation() { evt.stopped = true; },
                 preventDefault() { evt.prevented = true; }};
    return evt;
};

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
    await settle();
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

test('a manual section shows the icon to everybody, red only where nothing documents the address', async () => {
    const page = createPage();
    const [manual, none] = [page.newIcon(), page.newIcon()];
    page.responses.push([200, {docs: {}, editable: ['field:adm.user:email', 'field:adm.user:phone'],
                               manual: ['field:adm.user:email']}]);
    page.genro.dlg.docTrack(manual, 'field:adm.user:email');
    page.genro.dlg.docTrack(none, 'field:adm.user:phone');
    await settle();
    assert.ok(shown(manual) && !empty(manual), 'the manual documents it');
    assert.ok(!shown(none));
    page.data['gnr.docModeVisible'] = true;
    page.genro.dlg.docApplyStates();
    assert.ok(shown(none) && empty(none) && !empty(manual));
});

test('the help panel shows the manual section, a link to the manual and the customer note', () => {
    const page = createPage();
    let edited = 0;
    page.genro.dlg.docEdit = () => edited++;
    page.genro.dlg.helpPanel('field:adm.user:email', {fill: (html) => html.replace('$x', 'X')}, {
        exists: true, editable: true, title: 'email', html: '<p>Note $x</p>',
        manual: {title: 'The email', html: '<p>From the manual</p>', url: 'https://docs.example.org/op.html#a'}});
    const built = page.panels[0];
    assert.deepEqual(classes(built), [
        ['div', 'doc_help_panel'], ['div', 'doc_help_panel_resize'], ['div', 'doc_help_panel_head'],
        ['div', 'doc_help_panel_title'], ['div', 'doc_help_panel_tool'], ['div', 'doc_help_panel_close'],
        ['div', 'doc_help_panel_body'], ['div', 'doc_help_manual'],
        ['a', 'doc_help_link'], ['div', 'doc_help_note'], ['div', 'doc_help_note_title'],
        ['div', 'doc_help_note_body'], ['a', 'doc_help_edit']]);
    assert.equal(byClass(built, 'doc_help_panel_title').innerHTML, 'The email', 'the manual\'s title');
    assert.equal(byClass(built, 'doc_help_manual').innerHTML, '<p>From the manual</p>');
    assert.equal(byClass(built, 'doc_help_link').href, 'https://docs.example.org/op.html#a');
    assert.equal(byClass(built, 'doc_help_link').target, '_blank', 'a plain click elsewhere: a new tab');
    assert.equal(byClass(built, 'doc_help_note_body').innerHTML, '<p>Note X</p>', 'the note filled');
    assert.equal(byClass(built, 'doc_help_edit').innerHTML, '!!Edit the note');
    byClass(built, 'doc_help_edit').connect_onclick({preventDefault() {}});
    assert.equal(edited, 1);
    page.panels.length = 0;
    page.genro.dlg.closeHelpPanel();
    page.genro.dlg.helpPanel('field:adm.user:email', {}, {exists: false, editable: false,
                                                           manual: {title: 'T', html: '', url: 'https://d.org/a.html#x'}});
    const inDialog = escape({closest: (selector) => (selector === '.dijitDialog' ? {} : null)});
    page.docListeners.keydown(inDialog);
    assert.equal(page.panels.length, 2, 'Esc in a dialog above the page is the dialog\'s');
    assert.ok(!inDialog.stopped);
    const onPage = escape({closest: () => null});
    page.docListeners.keydown(onPage);
    assert.equal(page.panels.length, 3, 'Esc clears the panel');
    assert.equal(page.panels[2].length, 0);
    assert.ok(onPage.stopped && onPage.prevented, 'and nothing below closes with it');
    assert.equal(page.docListeners.keydown, undefined, 'and stops listening');
});

test('the help panel follows only an http(s) or site link to the manual', () => {
    const page = createPage();
    for (const url of ['javascript:alert(1)', 'data:text/html,x', '//evil.example.org/', 'file:///etc/passwd']) {
        page.genro.dlg.helpPanel('field:adm.user:email', {}, {exists: false, editable: false,
                                                               manual: {title: 'T', html: '<p>M</p>', url}});
        assert.equal(byClass(page.panels.at(-1), 'doc_help_link'), undefined, url);
        assert.equal(byClass(page.panels.at(-1), 'doc_help_manual').innerHTML, '<p>M</p>');
    }
    page.genro.dlg.helpPanel('field:adm.user:email', {}, {exists: false, editable: false,
                                                           manual: {title: 'T', html: '', url: '/_storage/site/m/a.html#x'}});
    assert.equal(byClass(page.panels.at(-1), 'doc_help_link').href, '/_storage/site/m/a.html#x');
});

test('the help panel without manual: the note alone, or a way to add one, or nothing to show', () => {
    const page = createPage();
    page.genro.dlg.helpPanel('field:adm.user:email', {title: 'Email'}, {exists: true, editable: false,
                                                                        title: 'email', html: '<p>Note</p>'});
    assert.deepEqual(classes(page.panels[0]).slice(7).map(([, c]) => c), ['doc_help_note', 'doc_help_note_body'],
                     'no manual, no "Notes" title, no Edit');
    page.genro.dlg.helpPanel('field:adm.user:phone', {}, {exists: false, editable: true, title: 'phone'});
    assert.deepEqual(classes(page.panels[1]).slice(7).map(([, c]) => c), ['doc_help_empty', 'doc_help_edit']);
    assert.equal(byClass(page.panels[1], 'doc_help_edit').innerHTML, '!!Add a note');
    byClass(page.panels[1], 'doc_help_panel_close').connect_onclick();
    assert.equal(page.panels[2].length, 0, 'the close button clears it');
});

test('openDoc: the panel with the note filled; an address with nothing opens the editor to a documenter', async () => {
    const page = createPage();
    page.responses.push([200, {exists: true, editable: false, title: 'Shipping', html: '<p>$city</p>',
                               markdown: '$city', language: 'it', mtime: 5, manual: null}]);
    await page.genro.dlg.openDoc({}, 'grouplet:test:card_profile', {fill: (html) => html.replace('$city', 'Turin')});
    assert.equal(byClass(page.panels[0], 'doc_help_note_body').innerHTML, '<p>Turin</p>');
    page.responses.push([200, {exists: false, editable: true, title: 'email', html: '', markdown: '',
                               language: 'it', mtime: null, manual: null}]);
    await page.genro.dlg.openDoc({}, 'field:adm.user:email', {title: 'Email'});
    assert.equal(page.dialogs.length, 1, 'straight to the editor');
    assert.equal(page.dialogs[0].title, '!!Documentation · Email (it)');
    page.responses.push([200, {exists: false, editable: true, title: 'email', html: '', markdown: '',
                               language: 'it', mtime: null, manual: {title: 'T', html: '<p>M</p>', url: 'u'}}]);
    await page.genro.dlg.openDoc({}, 'field:adm.user:phone', {});
    assert.equal(page.dialogs.length, 1, 'a manual section opens the panel, the note is added from there');
    assert.equal(byClass(page.panels[1], 'doc_help_manual').innerHTML, '<p>M</p>');
    page.responses.push([404, null]);
    await page.genro.dlg.openDoc({}, 'field:sys.service:name', {title: 'Name'});
    assert.equal(byClass(page.panels[2], 'doc_help_empty').innerHTML, '!!No documentation available');
});

test('Open in the manual shows the manual page in the widened panel, never leaving the page', () => {
    const page = createPage();
    const url = '/_storage/site/manual/users.html#help-field-adm-user-email';
    const source = {exists: false, editable: false, manual: {title: 'Email', html: '<p>M</p>', url}};
    page.genro.dlg.helpPanel('field:adm.user:email', {}, source);
    let prevented = false;
    byClass(page.panels[0], 'doc_help_link').connect_onclick({preventDefault() { prevented = true; }});
    assert.ok(prevented, 'the link is not followed');
    const built = page.panels[1];
    assert.equal(byClass(built, 'doc_help_panel doc_help_panel--wide').width, null, 'widened');
    const frame = byClass(built, 'doc_help_panel_frame');
    assert.equal(frame.src, url, 'at the section');
    assert.equal(frame.externalSite, true, 'no page id appended to its url');
    assert.ok(!/allow-same-origin|allow-top-navigation/.test(frame.sandbox), 'it can neither reach nor replace the page');
    assert.equal(byClass(built, 'doc_help_panel_body'), undefined, 'the frame in place of the help');
    const [, [, newWindow]] = built.filter(([, attrs]) => attrs._class === 'doc_help_panel_tool');
    assert.deepEqual([newWindow.href, newWindow.target, newWindow.rel], [url, '_blank', 'noopener']);
    built.find(([, attrs]) => attrs.title === '!!Back to the help')[1].connect_onclick();
    assert.equal(byClass(page.panels[2], 'doc_help_manual').innerHTML, '<p>M</p>', 'back to the section');
    assert.equal(byClass(page.panels[2], 'doc_help_panel_frame'), undefined);
});

test('the help panel widens and narrows; a dragged width is used by the next panel', () => {
    const page = createPage();
    page.genro.dlg.helpPanel('field:adm.user:email', {}, {exists: true, html: '<p>N</p>'});
    assert.equal(byClass(page.panels[0], 'doc_help_panel').width, null, 'the default width of the css');
    page.panels[0].find(([, attrs]) => attrs.title === '!!Widen')[1].connect_onclick();
    assert.ok(byClass(page.panels[1], 'doc_help_panel doc_help_panel--wide'));
    page.panels[1].find(([, attrs]) => attrs.title === '!!Narrow')[1].connect_onclick();
    assert.ok(byClass(page.panels[2], 'doc_help_panel'));
    const style = {}, classList = new Set(['doc_help_panel']);
    const panelDom = {style, classList: {add: (c) => classList.add(c), remove: (c) => classList.delete(c)}};
    const listeners = {};
    const handle = {parentNode: panelDom, setPointerCapture() {},
                    addEventListener: (evt, h) => { listeners[evt] = h; },
                    removeEventListener: (evt) => { delete listeners[evt]; }};
    page.context.window = {innerWidth: 1000};
    const stored = [];
    page.genro.setInStorage = (type, key, value) => stored.push([type, key, value]);
    byClass(page.panels[2], 'doc_help_panel_resize').connect_onpointerdown(
        {currentTarget: handle, pointerId: 1, preventDefault() {}});
    listeners.pointermove({clientX: 400});
    assert.equal(style.width, '600px', 'from the pointer to the right edge');
    listeners.pointermove({clientX: 950});
    assert.equal(style.width, '320px', 'never narrower than 320px');
    listeners.pointermove({clientX: 10});
    assert.equal(style.width, '900px', 'never wider than 90% of the window');
    listeners.pointerup();
    assert.deepEqual(stored, [['local', 'docHelpPanelWidth', 900]], 'kept in the browser');
    assert.equal(listeners.pointermove, undefined);
    page.genro.dlg.helpPanel('field:adm.user:phone', {}, {exists: true, html: '<p>N</p>'});
    assert.equal(byClass(page.panels.at(-1), 'doc_help_panel').width, '900px');
});

test('openDoc with tooltip: the help in a popup at the icon, the panel untouched', async () => {
    const page = createPage();
    const icon = {};
    page.responses.push([200, {exists: true, editable: true, title: 'email', html: '<p>Note</p>', markdown: 'Note',
                               language: 'it', mtime: 5,
                               manual: {title: 'The email', html: '<p>M</p>', url: 'https://docs.example.org/a.html#x'}}]);
    await page.genro.dlg.openDoc(icon, 'field:adm.user:email', {title: 'Email', tooltip: true});
    assert.equal(page.panels.length, 0, 'no help panel');
    assert.equal(page.tooltips.length, 1);
    const {kw, built} = page.tooltips[0];
    assert.equal(kw.domNode, icon, 'anchored to the icon clicked');
    assert.equal(kw.nodeId, 'doc_help_tooltip', 'one popup for the page');
    assert.deepEqual(classes(built), [
        ['div', 'doc_help_tooltip_box'], ['div', 'doc_help_tooltip_title'], ['div', 'doc_help_tooltip_body'],
        ['div', 'doc_help_manual'], ['a', 'doc_help_link'], ['div', 'doc_help_note'], ['div', 'doc_help_note_title'],
        ['div', 'doc_help_note_body'], ['a', 'doc_help_edit']], 'what the help panel shows');
    assert.equal(byClass(built, 'doc_help_tooltip_title').innerHTML, 'Email', "the caller's title");
    byClass(built, 'doc_help_edit').connect_onclick({preventDefault() {}});
    assert.deepEqual(page.published.at(-1), ['doc_help_tooltip_opener_close', undefined], 'Edit closes the popup');
    assert.equal(page.dialogs.length, 1, 'and opens the editor');
    assert.equal(page.docListeners.keydown, undefined, 'Esc is no longer heard for it');
});

test('the help popup closes on Esc; an address with nothing still opens the editor to a documenter', async () => {
    const page = createPage();
    page.responses.push([200, {exists: false, editable: false, title: 'card', html: '', markdown: '',
                               language: 'it', mtime: null, manual: {title: 'Card', html: '<p>M</p>', url: ''}}]);
    await page.genro.dlg.openDoc({}, 'grouplet:test:card_profile', {tooltip: true});
    assert.equal(byClass(page.tooltips[0].built, 'doc_help_tooltip_title').innerHTML, 'Card', "the manual's title");
    page.docListeners.keydown({key: 'Enter'});
    assert.equal(page.published.length, 0, 'another key leaves it open');
    page.docListeners.keydown({key: 'Escape'});
    assert.deepEqual(page.published.at(-1), ['doc_help_tooltip_opener_close', undefined]);
    assert.equal(page.docListeners.keydown, undefined);
    page.responses.push([200, {exists: false, editable: true, title: 'phone', html: '', markdown: '',
                               language: 'it', mtime: null, manual: null}]);
    await page.genro.dlg.openDoc({}, 'field:adm.user:phone', {title: 'Phone', tooltip: true});
    assert.equal(page.tooltips.length, 1, 'no popup');
    assert.equal(page.dialogs.length, 1, 'straight to the editor');
});

test("the doc's own title is text: its markup is escaped, the caller's title is the caller's", async () => {
    const page = createPage();
    const title = '<img src=x onerror="alert(1)">';
    page.responses.push([200, {exists: true, editable: true, title, html: '<p>Body</p>',
                               markdown: 'Body', language: 'it', mtime: 5}]);
    await page.genro.dlg.openDoc({}, 'field:adm.user:email');
    const shownTitle = byClass(page.panels[0], 'doc_help_panel_title').innerHTML;
    assert.equal(shownTitle, '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
    byClass(page.panels[0], 'doc_help_edit').connect_onclick({preventDefault() {}});
    assert.equal(page.dialogs[0].title, '!!Documentation · ' + shownTitle + ' (it)', 'the editor too');
    page.responses.push([200, {exists: true, editable: false, title, html: '<p>Body</p>',
                               markdown: 'Body', language: 'it', mtime: 5}]);
    await page.genro.dlg.openDoc({}, 'field:adm.user:username', {title: '<b>User</b>'});
    assert.equal(byClass(page.panels[1], 'doc_help_panel_title').innerHTML, '<b>User</b>',
                 'a label keeps its markup');
    page.genro.dlg.helpPanel('field:adm.user:phone', {}, {exists: false, editable: false, title: 'phone',
                                                          manual: {title: 'T <img src=x onerror=alert(1)>',
                                                                   html: '', url: 'https://docs.example.org/a.html'}});
    assert.equal(byClass(page.panels[2], 'doc_help_panel_title').innerHTML, 'T &lt;img src=x onerror=alert(1)&gt;',
                 "the manual's title is text too");
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

test('Save reads the editor itself: its datapath is written only on blur', async () => {
    const page = createPage();
    const source = {exists: false, editable: true, title: 'Email', language: 'it', mtime: null, markdown: ''};
    page.genro.dlg._docStates = {};
    page.genro.dlg._docSources = {};
    const dlg = page.genro.dlg.docEdit('field:adm.user:email', {}, source);
    assert.equal(dlg.built.find(([, tag]) => tag === 'MDEditor')[2].nodeId, 'doc_editor_md');
    page.editors.doc_editor_md = {externalWidget: {getMarkdown: () => 'Typed, not blurred'}};
    page.responses.push([200, {mtime: 1}]);
    dlg.built.find(([, , attrs]) => attrs && attrs.label === '!!Save')[2].action();
    await flush();
    assert.equal(page.requests.at(-1).params.markdown, 'Typed, not blurred');
});
