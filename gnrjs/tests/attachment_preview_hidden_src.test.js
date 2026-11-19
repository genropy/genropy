const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// attachmentPreviewViewer stacks an iframe, an img and a video. A hidden img still
// fetches its src: when a PDF reached it too, the request without Origin went to the
// same signed S3 url as the CORS fetch of PDF.js and poisoned the browser cache (#1921).
// Only the element of the selected page may receive the url.
const ATTACHMANAGER_PY = path.join(__dirname, '../../resources/common/gnrcomponents/attachmanager/attachmanager.py');

function readComponent() {
    const source = readFileSync(ATTACHMANAGER_PY, 'utf8');
    const viewer = source.slice(source.indexOf('def at_attachmentPreviewViewer'));
    const controller = viewer.match(/parent\.dataController\("""([\s\S]*?)"""/);
    assert.ok(controller, 'attachmentPreviewViewer routes the src in a dataController');
    const extensions = name => {
        const match = source.match(new RegExp(`^${name} = \\(([^)]*)\\)`, 'm'));
        assert.ok(match, `${name} is declared in attachmanager.py`);
        return match[1].split(',').map(ext => ext.trim().replace(/'/g, ''));
    };
    return {
        body: controller[1],
        IMAGES_EXT: extensions('IMAGES_EXT'),
        VIDEOS_EXT: extensions('VIDEOS_EXT'),
        UNPLAYABLE_VIDEOS_EXT: extensions('UNPLAYABLE_VIDEOS_EXT')
    };
}

function createContext() {
    const context = {console, gnr: {}, genro: {}, window: {}, navigator: {}};
    // parseURL reads the parts of the url from an anchor element
    context.document = {
        createElement: () => {
            const anchor = {};
            Object.defineProperty(anchor, 'href', {
                set(value) {
                    const url = new URL(value, 'https://app.example.com/page');
                    for (const part of ['protocol', 'hostname', 'port', 'search', 'origin', 'pathname', 'hash']) {
                        this[part] = url[part];
                    }
                    this._href = url.href;
                },
                get() { return this._href; }
            });
            return anchor;
        }
    };
    context.dojo = {hitch: (object, method) => method.bind(object)};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    vm.runInContext(readFileSync(path.join(sourceDir, 'gnrlang.js'), 'utf8'), context, {filename: 'gnrlang.js'});
    context.genro.evaluate = expr => vm.runInContext('(' + expr + ')', context);
    return context;
}

function route(src, state = {}) {
    const component = readComponent();
    const context = createContext();
    const sourceNode = {setRelativeData: (pathname, value) => { state[pathname] = value; }};
    const sc = {switchPage: page => { state.page = page; }};
    const controller = context.funcCreate(component.body,
                                          'src,sc,IMAGES_EXT,VIDEOS_EXT,UNPLAYABLE_VIDEOS_EXT', sourceNode);
    controller(src, sc, component.IMAGES_EXT, component.VIDEOS_EXT, component.UNPLAYABLE_VIDEOS_EXT);
    return state;
}

function sources(state) {
    return {
        document: state['.$preview_src.document'],
        image: state['.$preview_src.image'],
        video: state['.$preview_src.video']
    };
}

test('a PDF reaches only the document page: the hidden img gets no url', () => {
    const src = '/_storage/site/attachments/legacy/report.pdf';
    const state = route(src);
    assert.equal(state.page, 'document');
    assert.deepEqual(sources(state), {document: src, image: '', video: ''});
});

test('an image reaches only the img, a video only the video', () => {
    const image = route('/_storage/site/attachments/photo.JPG');
    assert.equal(image.page, 'image');
    assert.deepEqual(sources(image), {document: '', image: '/_storage/site/attachments/photo.JPG', video: ''});

    const video = route('/_storage/site/attachments/clip.mp4');
    assert.equal(video.page, 'video');
    assert.deepEqual(sources(video), {document: '', image: '', video: '/_storage/site/attachments/clip.mp4'});
});

test('the source_ext parameter decides over the file name', () => {
    const src = '/_storage/site/attachments/preview?source_ext=png';
    const state = route(src);
    assert.equal(state.page, 'image');
    assert.deepEqual(sources(state), {document: '', image: src, video: ''});
});

test('an unplayable video is offered for download, no element loads it', () => {
    const state = route('/_storage/site/attachments/clip.avi');
    assert.equal(state.page, 'unsupported');
    assert.deepEqual(sources(state), {document: '', image: '', video: ''});
});

test('switching from an image to a PDF clears the img', () => {
    const state = route('/_storage/site/attachments/photo.png');
    route('/_storage/site/attachments/report.pdf', state);
    assert.equal(state.page, 'document');
    assert.equal(state['.$preview_src.image'], '');
});

test('an empty src clears every element and keeps the current page', () => {
    const state = route('/_storage/site/attachments/photo.png');
    route(null, state);
    assert.equal(state.page, 'image');
    assert.equal(state['.$ext'], '');
    assert.deepEqual(sources(state), {document: '', image: '', video: ''});
});
