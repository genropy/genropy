const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadHandler(globals) {
    const context = {console, gnr: {widgets: {}}, genro: {locale: () => 'it-IT'}, ...globals};
    context.dojo = {
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        declare(name, base, members) {
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
    for (const filename of ['gnrlang.js', 'gnrbag.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    // Same contract as gnr.widgets.baseExternalWidget in genro_widgets.js.
    context.gnr.widgets.baseHtml = function() {};
    context.dojo.declare('gnr.widgets.baseExternalWidget', context.gnr.widgets.baseHtml, {
        setExternalWidget(sourceNode, externalWidget) {
            sourceNode.externalWidget = externalWidget;
            externalWidget.gnr = this;
            for (const prop in this) {
                if (prop.indexOf('mixin_') == 0) {
                    externalWidget[prop.replace('mixin_', '')] = this[prop];
                }
            }
            externalWidget.sourceNode = sourceNode;
        }
    });
    vm.runInContext(readFileSync(path.join(sourceDir, 'genro_editors.js'), 'utf8'), context, {filename: 'genro_editors.js'});
    return new context.gnr.widgets.joditEditor();
}

function makeSourceNode(value, attr) {
    const store = {value};
    const writes = [];
    return {
        store, writes,
        attr: Object.assign({value: '^.html'}, attr),
        getAttributeFromDatasource: (name) => store[name],
        setAttributeInDatasource: (name, v) => { store[name] = v; writes.push([name, v]); },
        delayedCall: (fn) => fn(),
        isPointerPath: (p) => typeof p === 'string' && p[0] === '^'
    };
}

// Reproduces Jodit 4.15.13 setReadOnly/setDisabled, cache included.
function makeEditor(handler, sourceNode, value) {
    const editor = {
        value: value || '',
        o: {readonly: false, disabled: false},
        __wasReadOnly: false,
        getReadOnly() { return this.o.readonly; },
        getDisabled() { return this.o.disabled; },
        setReadOnly(isReadOnly) {
            if (this.__wasReadOnly === isReadOnly) return;
            this.__wasReadOnly = isReadOnly;
            this.o.readonly = isReadOnly;
        },
        setDisabled(isDisabled) {
            this.o.disabled = isDisabled;
            const readOnly = this.__wasReadOnly;
            this.setReadOnly(isDisabled || readOnly);
            this.__wasReadOnly = readOnly;
        }
    };
    handler.setExternalWidget(sourceNode, editor);
    return editor;
}

function create(handler, attributes) {
    return handler.creating(attributes, makeSourceNode('')).joditAttrs;
}

test('creating keeps stored markup as written and leaves layout attributes to the host', () => {
    const handler = loadHandler();
    const attributes = {value: '^.html', height: '300px', border: '1px solid silver'};
    const {options, mode, sourceEditor} = handler.creating(attributes, makeSourceNode('')).joditAttrs;
    assert.deepEqual({...attributes}, {height: '300px', border: '1px solid silver'});
    assert.deepEqual([...options.buttons], [...handler.toolbars.standard]);
    assert.deepEqual({...options.cleanHTML}, {
        denyTags: 'script', replaceOldTags: false, replaceNBSP: false, removeEmptyElements: false,
        fillEmptyParagraph: false, sandboxIframesInContent: false, collapseEmptyValueToEmptyString: true
    });
    assert.equal(options.beautifyHTML, false);
    assert.equal(options.iframe, true);
    assert.equal(options.enter, 'P');
    assert.equal(options.height, '100%');
    assert.equal(options.language, 'it');
    assert.equal(mode, 'wysiwyg');
    assert.equal(sourceEditor, 'codemirror');
});

test('an editor without height grows with its content', () => {
    assert.equal(create(loadHandler(), {}).options.height, 'auto');
});

test('toolbar accepts a preset, a list, a comma string or false', () => {
    const handler = loadHandler();
    assert.deepEqual([...create(handler, {toolbar: 'minimal'}).options.buttons], [...handler.toolbars.minimal]);
    assert.deepEqual([...create(handler, {toolbar: 'bold, italic,|,source'}).options.buttons],
                     ['bold', 'italic', '|', 'source']);
    assert.deepEqual([...create(handler, {toolbar: ['ul', 'ol']}).options.buttons], ['ul', 'ol']);
    const none = create(handler, {toolbar: false}).options;
    assert.equal(none.toolbar, false);
    assert.deepEqual([...none.buttons], []);
});

test('presets are copied, never shared with the editor', () => {
    const handler = loadHandler();
    create(handler, {}).options.buttons.push('about');
    assert.equal(handler.toolbars.standard.includes('about'), false);
});

test('config_* options override the defaults', () => {
    const options = create(loadHandler(), {config_beautifyHTML: true, config_iframe: false,
                                           contentsCss: '/a.css, /b.css'}).options;
    assert.equal(options.beautifyHTML, true);
    assert.equal(options.iframe, false);
    assert.deepEqual([...options.iframeCSSLinks], ['/a.css', '/b.css']);
});

test('mode names map to the Jodit mode codes', () => {
    const handler = loadHandler();
    assert.deepEqual(['wysiwyg', 'source', 'split'].map((m) => handler.modeCode(m)), [1, 2, 3]);
    assert.equal(handler.modeName(3), 'split');
    assert.throws(() => handler.modeCode('html'), /unknown mode "html"/);
});

test('loading a value never writes it back, even when the editor normalizes it', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<b>old</b>');
    const editor = makeEditor(handler, sourceNode, '<b>old</b>');
    editor.gnr_value('<b>new</b>');
    assert.equal(editor.value, '<b>new</b>');
    editor.value = '<strong>new</strong>';
    handler.onEditorChange(editor);
    handler.writeValue(editor);
    assert.deepEqual(sourceNode.writes, []);
});

test('a user edit is written once, and an unchanged value is not rewritten', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<p>a</p>');
    const editor = makeEditor(handler, sourceNode, '<p>a</p>');
    editor._gnrUserEdit = true;
    editor.value = '<p>ab</p>';
    handler.onEditorChange(editor);
    handler.writeValue(editor);
    assert.deepEqual(sourceNode.writes, [['value', '<p>ab</p>']]);
});

test('an emptied editor stores null', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<p>a</p>');
    const editor = makeEditor(handler, sourceNode, '<p>a</p>');
    editor._gnrUserEdit = true;
    editor.value = '';
    handler.writeValue(editor);
    assert.deepEqual(sourceNode.writes, [['value', null]]);
});

test('an external value discards the pending user edit flag', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<p>a</p>');
    const editor = makeEditor(handler, sourceNode, '<p>a</p>');
    editor._gnrUserEdit = true;
    editor.gnr_value('<p>from the store</p>');
    handler.onEditorChange(editor);
    assert.deepEqual(sourceNode.writes, []);
});

test('pending source view edits are flushed before writing', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<p>a</p>');
    const editor = makeEditor(handler, sourceNode, '<p>a</p>');
    editor._gnrUserEdit = true;
    editor._gnrSource = {flush: () => { editor.value = '<p>typed in the source view</p>'; }};
    handler.writeValue(editor);
    assert.deepEqual(sourceNode.writes, [['value', '<p>typed in the source view</p>']]);
});

test('switching view writes the mode back only to a datapath', () => {
    const handler = loadHandler();
    const bound = makeSourceNode('', {mode: '^.mode'});
    const boundEditor = makeEditor(handler, bound);
    boundEditor.getMode = () => 3;
    handler.onModeChange(boundEditor);
    assert.deepEqual(bound.writes, [['mode', 'split']]);
    const literal = makeSourceNode('', {mode: 'source'});
    const literalEditor = makeEditor(handler, literal);
    literalEditor.getMode = () => 1;
    handler.onModeChange(literalEditor);
    assert.deepEqual(literal.writes, []);
});

test('re-enabling a disabled editor makes it editable again', () => {
    const handler = loadHandler();
    const editor = makeEditor(handler, makeSourceNode(''));
    editor.gnr_setDisabled(true);
    editor.gnr_setDisabled(false);
    assert.deepEqual([editor.getReadOnly(), editor.getDisabled()], [false, false]);
});

test('readOnly survives a disable/enable cycle and cannot unlock a disabled editor', () => {
    const handler = loadHandler();
    const editor = makeEditor(handler, makeSourceNode(''));
    editor.gnr_readOnly(true);
    editor.gnr_setDisabled(true);
    editor.gnr_setDisabled(false);
    assert.equal(editor.getReadOnly(), true);
    editor.gnr_setDisabled(true);
    editor.gnr_readOnly(false);
    assert.equal(editor.getReadOnly(), true);
    editor.gnr_setDisabled(false);
    assert.equal(editor.getReadOnly(), false);
});

function makeIframeDocument() {
    const nodes = {};
    const head = [];
    return {
        head: {appendChild: (node) => { head.push(node); nodes[node.id] = node; }},
        createElement: () => ({id: null, textContent: ''}),
        getElementById: (id) => nodes[id] || null,
        styles: () => head.map((node) => [node.id, node.textContent])
    };
}

test('bodyStyle is appended after contentStyles as a body rule', () => {
    const handler = loadHandler();
    assert.equal(create(handler, {bodyStyle: 'width:170mm'}).bodyStyle, 'width:170mm');
    const editor = makeEditor(handler, makeSourceNode(''));
    editor.o.iframe = true;
    editor.ed = makeIframeDocument();
    editor.gnr_contentStyles('.note{color:red}');
    editor.gnr_bodyStyle('width:170mm;height:250mm');
    editor.gnr_contentStyles('.note{color:blue}');
    assert.deepEqual(editor.ed.styles(), [['gnr_contentStyles', '.note{color:blue}'],
                                          ['gnr_bodyStyle', 'body{width:170mm;height:250mm}']]);
    editor.gnr_bodyStyle(null);
    assert.deepEqual(editor.ed.styles()[1], ['gnr_bodyStyle', '']);
});

test('content styles are ignored without the iframe', () => {
    const handler = loadHandler();
    const editor = makeEditor(handler, makeSourceNode(''));
    editor.o.iframe = false;
    editor.ed = makeIframeDocument();
    editor.gnr_contentStyles('.note{color:red}');
    assert.deepEqual(editor.ed.styles(), []);
});

test('dictated text is inserted as text at the caret and stored', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<p>a</p>');
    const editor = makeEditor(handler, sourceNode, '<p>a</p>');
    editor.createInside = {text: (text) => ({text})};
    editor.s = {insertNode: (node) => { editor.value = '<p>a' + node.text + '</p>'; }};
    handler.onSpeechEnd(sourceNode, ' <b>dictated</b>');
    assert.deepEqual(sourceNode.writes, [['value', '<p>a <b>dictated</b></p>']]);
});

function initializeWith(sourceEditor) {
    let made;
    const editor = {
        container: {},
        e: {on() { return this; }},
        waitForReady: () => new Promise(() => {})
    };
    const handler = loadHandler({
        document: {createElement: () => ({})},
        Jodit: {make: (textarea, options) => { made = options; return editor; }}
    });
    const joditAttrs = create(handler, {sourceEditor});
    const widget = {classList: {add() {}}, appendChild() {}};
    handler.initialize(widget, joditAttrs, makeSourceNode(''));
    return made.sourceEditor;
}

test('source view uses CodeMirror, or the plain textarea for any other sourceEditor', () => {
    assert.equal(typeof initializeWith('codemirror'), 'function');
    assert.equal(initializeWith('area'), 'area');
    assert.equal(initializeWith('ace'), 'area');
});
