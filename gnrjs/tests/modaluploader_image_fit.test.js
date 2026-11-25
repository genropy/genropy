const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// An image in a document iframe is shown through a srcdoc page holding an img. The browser
// does not scale an image loaded straight into an iframe, so a portrait image was cropped in
// the modalUploader preview; the srcdoc page fitted the width only and let it overflow downwards.
function createContext() {
    const context = {console, File: function() {}, gnr: {}, setTimeout, navigator: {}, window: {},
                     dijit: {_Widget: function() {}, layout: {}, form: {}}};
    // parseURL reads the parts of a URL through an anchor element
    context.document = {
        createElement: () => {
            let url;
            return {
                set href(value) { url = new URL(value, 'http://localhost'); },
                get protocol() { return url.protocol; }, get hostname() { return url.hostname; },
                get port() { return url.port; }, get search() { return url.search; },
                get origin() { return url.origin; }, get pathname() { return url.pathname; },
                get hash() { return url.hash; }, get href() { return url.href; }
            };
        }
    };
    context.dojo = {
        Deferred: function() {},
        eval,
        isIE: 0,
        version: {major: 1, minor: 1},
        require() {},
        provide() {},
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        indexOf: (items, value) => Array.prototype.indexOf.call(items || [], value),
        toJson: JSON.stringify,
        declare(name, bases, members) {
            const base = Array.isArray(bases) ? bases[0] : bases;
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js', 'genro_components.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context._T = str => str;
    const pdfViewer = [];
    context.genro = {
        page_id: 'page',
        dom: {
            addClass() {},
            removeClass() {},
            detectPdfViewer: src => { pdfViewer.push(src); return src; }
        },
        addParamsToUrl: (url, params) => url + '?' + new URLSearchParams(params)
    };
    return {context, pdfViewer};
}

// the iframe of a document preview: setSrc_do writes its src or its srcdoc
function loadInDocumentIframe(url) {
    const {context, pdfViewer} = createContext();
    const handler = Object.create(context.gnr.widgets.iframe.prototype);
    handler.initContentHtml = () => false;
    const attributes = {};
    const domnode = {
        sourceNode: {attr: {documentClasses: true}, savedAttrs: {}, evaluateOnNode: kw => kw},
        setAttribute(name, value) { attributes[name] = value; },
        removeAttribute(name) { delete attributes[name]; }
    };
    handler.setSrc_do(domnode, url);
    return {attributes, pdfViewer};
}

// the inline style of the first tag with this name, as {property: value}
function tagStyle(markup, tagName) {
    const tag = markup.match(new RegExp(`<${tagName}\\b[^>]*>`));
    assert.ok(tag, `no <${tagName}> in the srcdoc`);
    const style = (tag[0].match(/style="([^"]*)"/) || [, ''])[1];
    return Object.fromEntries(style.split(';').filter(Boolean)
        .map(rule => rule.split(':').map(part => part.trim())));
}

test('an image preview fits the whole image in the frame, in both directions', () => {
    const {attributes} = loadInDocumentIframe('/site/portrait.png');
    const srcdoc = attributes.srcdoc;
    assert.ok(srcdoc, 'an image is shown through a srcdoc page');
    // the page fills the frame, so a percentage on the image refers to the frame height
    assert.equal(tagStyle(srcdoc, 'html').height, '100%');
    assert.equal(tagStyle(srcdoc, 'body').height, '100%');
    const img = tagStyle(srcdoc, 'img');
    assert.equal(img['max-width'], '100%');
    assert.equal(img['max-height'], '100%');
    assert.equal(img['object-fit'], 'contain', 'the image keeps its proportions');
});

test('a pdf preview still loads the document itself', () => {
    const {attributes, pdfViewer} = loadInDocumentIframe('/site/document.pdf');
    assert.equal(attributes.srcdoc, undefined);
    assert.equal(pdfViewer.length, 1, 'the pdf goes through the pdf viewer detection');
});

// a source node that records what is built under it
function recordingNode(tag, attrs) {
    const node = {
        tag, attrs, children: [],
        _(childTag, name, childAttrs) {
            const child = recordingNode(childTag, typeof name === 'object' ? name : childAttrs || {});
            node.children.push(child);
            return child;
        },
        getParentNode: () => node,
        currentFromDatasource: () => null,
        setRelativeData() {}
    };
    return node;
}

test('the modalUploader preview is a document iframe, so an image fits its box', () => {
    const {context} = createContext();
    const widget = Object.create(context.gnr.widgets.ModalUploader.prototype);
    const sourceNode = recordingNode('root', {});
    widget.createContent(sourceNode, {value: '^.document', dest_stn: 'site:document.pdf', label: 'Document'});
    const wrapper = sourceNode.children[0];
    const preview = wrapper.children.find(child => child.tag == 'iframe');
    assert.equal(preview.attrs._class, 'modalUploader_preview');
    assert.equal(preview.attrs.documentClasses, true);
});

// The srcdoc page is a window of its own, without the genro of the page that holds the iframe:
// clicking the zoom-in image threw "genro is not defined" and opened nothing.
test('clicking an image preview opens it in a browser tab through the parent page', () => {
    const {attributes} = loadInDocumentIframe('/site/portrait.png');
    const imgTag = attributes.srcdoc.match(/<img\b[^>]*>/)[0];
    const onclick = (imgTag.match(/onclick="([^"]*)"/) || [])[1];
    assert.ok(onclick, 'the image has a click handler');
    const opened = [];
    const srcdocWindow = vm.createContext({parent: {genro: {openBrowserTab: (...args) => opened.push(args)}}});
    srcdocWindow.window = srcdocWindow;
    const handler = vm.runInContext(`(function(){${onclick}})`, srcdocWindow);
    handler.call({src: 'http://localhost/site/portrait.png'});
    assert.deepEqual(opened, [['http://localhost/site/portrait.png']]);
});
