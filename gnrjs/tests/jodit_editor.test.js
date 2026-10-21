const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadHandler(globals) {
    // _T leaves a string untranslated while the connection is down: no server call from a test.
    const genro = {locale: () => 'it-IT', getFromStorage: () => ({}), _pageLocals: {},
                   dev: {isConnectionLost: () => true}};
    const context = {console, gnr: {widgets: {}}, genro,
                     dijit: {getEnclosingWidget: () => null}, ...globals};
    context.dojo = {
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        connect(target, event, callback) {
            const wrapped = target[event];
            target[event] = function(...args) {
                const result = wrapped && wrapped.apply(this, args);
                callback.apply(this, args);
                return result;
            };
            return [target, event, wrapped];
        },
        disconnect([target, event, wrapped]) { target[event] = wrapped; },
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
        setRelativeData: (path, v) => { store[path] = v; writes.push([path, v]); },
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

function initializeEditor(value, parentWidget, attr) {
    const listeners = {};
    const editor = {
        value,
        container: {},
        e: {
            on(target, events, callback) {
                if (typeof target === 'string') [events, callback] = [target, events];
                for (const name of events.split(' ')) (listeners[name] ||= []).push(callback);
                return this;
            },
            fire: (name) => (listeners[name] || []).forEach((callback) => callback())
        },
        fire: (name) => (listeners[name] || []).forEach((callback) => callback()),
        waitForReady: () => new Promise(() => {})
    };
    const handler = loadHandler({
        document: {createElement: () => ({})},
        Jodit: {make: () => editor},
        dijit: {getEnclosingWidget: () => parentWidget || null}
    });
    const sourceNode = makeSourceNode(value, attr);
    const widget = {classList: {add() {}}, appendChild() {}};
    handler.initialize(widget, create(handler, {}), sourceNode);
    return {editor, sourceNode};
}

test('a field dropped from a tree is stored on change', () => {
    const {editor, sourceNode} = initializeEditor('<p>Total: </p>');
    editor.fire('drop');
    editor.value = '<p>Total: $total</p>';
    editor.fire('change');
    assert.deepEqual(sourceNode.writes, [['value', '<p>Total: $total</p>']]);
});

test('a field dropped from a tree is stored on blur', () => {
    const {editor, sourceNode} = initializeEditor('');
    editor.fire('drop');
    editor.value = '<p>$protocol</p>';
    editor.fire('blur');
    assert.deepEqual(sourceNode.writes, [['value', '<p>$protocol</p>']]);
});

test('only a Genropy drag of plain text is a field drop, and never into a read-only editor', () => {
    const handler = loadHandler();
    const editor = {getReadOnly: () => false};
    const drag = (...types) => ({types});
    assert.equal(handler.isFieldDrag(editor, drag('text/plain', 'dragsourceinfo', 'treenode')), true);
    assert.equal(handler.isFieldDrag(editor, drag('text/plain')), false);
    assert.equal(handler.isFieldDrag(editor, drag('text/plain', 'dragsourceinfo', 'text/html')), false);
    assert.equal(handler.isFieldDrag(editor, drag('Files', 'text/plain', 'dragsourceinfo')), false);
    assert.equal(handler.isFieldDrag({getReadOnly: () => true}, drag('text/plain', 'dragsourceinfo')), false);
});

test('a dropped field is spaced from the words it would touch', () => {
    const handler = loadHandler();
    const at = (data, offset) => ({startContainer: {nodeType: 3, data}, startOffset: offset});
    const inElement = (childNodes, offset) => ({startContainer: {nodeType: 1, childNodes}, startOffset: offset});
    assert.equal(handler.dropText(at('Total:', 6), '$total'), ' $total');
    assert.equal(handler.dropText(at('Total: ', 7), '$total'), '$total');
    assert.equal(handler.dropText(at('ab', 1), '$x'), ' $x ');
    assert.equal(handler.dropText(inElement([], 0), '$x'), '$x');
    // at the end of a block, after the text node of a field dropped before
    assert.equal(handler.dropText(inElement([{nodeType: 3, data: '$protocol'}], 1), '$total'), ' $total');
    assert.equal(handler.dropText(inElement([{nodeType: 1, hasAttribute: () => false}], 1), '$total'), '$total');
    const field = {nodeType: 3, data: '$protocol', previousSibling: null};
    const invisible = {nodeType: 3, data: '\uFEFF', previousSibling: field};
    const selectionMarker = {nodeType: 1, hasAttribute: (name) => name === 'data-jodit-selection_marker',
                             previousSibling: invisible};
    assert.equal(handler.dropText(inElement([field, invisible], 2), '$total'), ' $total');
    assert.equal(handler.dropText(inElement([field, invisible, selectionMarker], 3), '$total'), ' $total');
});

test('a field dropped below the content goes after a closing table, list or image, inside a closing paragraph', () => {
    const handler = loadHandler();
    const dropBelow = (nodeName) => {
        const last = {nodeType: 1, nodeName, lastChild: null, getBoundingClientRect: () => ({bottom: 10})};
        const range = {
            setStartAfter(node) { this.after = node; },
            setStartBefore(node) { this.before = node; },
            selectNodeContents(node) { this.inside = node; },
            collapse() {}
        };
        const editor = {ed: {createRange: () => range}, editor: {lastElementChild: last, contains: () => true}};
        return [handler.dropRange(editor, 0, 50), last];
    };
    for (const nodeName of ['TABLE', 'UL', 'IMG']) {
        const [range, last] = dropBelow(nodeName);
        assert.equal(range.after, last, nodeName);
        assert.equal(range.inside, undefined, nodeName);
    }
    const [range, last] = dropBelow('P');
    assert.equal(range.inside, last);
    assert.equal(range.after, undefined);
});

test('a resize of the enclosing pane resizes the editor, until it is destroyed', () => {
    const pane = {resize() {}};
    const {editor} = initializeEditor('', pane);
    let resized = 0;
    editor.e.on('resize', () => { resized += 1; });
    pane.resize();
    assert.equal(resized, 1);
    editor.gnr = {writeValue() {}};
    editor.destruct = () => {};
    editor.destroy();
    pane.resize();
    assert.equal(resized, 1);
});

test('source view uses CodeMirror, or the plain textarea for any other sourceEditor', () => {
    assert.equal(typeof initializeWith('codemirror'), 'function');
    assert.equal(initializeWith('area'), 'area');
    assert.equal(initializeWith('ace'), 'area');
});

test('the plain text is written only on blur, and only after a user edit', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<p>a</p>', {textpath: '.text'});
    const editor = makeEditor(handler, sourceNode, '<p>a</p>');
    editor.text = 'a';
    handler.writeValue(editor, true);
    assert.deepEqual(sourceNode.writes, []);
    editor._gnrUserEdit = true;
    editor.value = '<p>ab</p>';
    editor.text = 'ab';
    handler.onEditorChange(editor);
    assert.deepEqual(sourceNode.writes, [['value', '<p>ab</p>']]);
    handler.writeValue(editor, true);
    assert.deepEqual(sourceNode.writes, [['value', '<p>ab</p>'], ['.text', 'ab']]);
});

test('an emptied editor stores no plain text either', () => {
    const handler = loadHandler();
    const sourceNode = makeSourceNode('<p>a</p>', {textpath: '.text'});
    const editor = makeEditor(handler, sourceNode, '');
    editor._gnrUserEdit = true;
    editor.text = '';
    handler.writeValue(editor, true);
    assert.deepEqual(sourceNode.writes, [['value', null], ['.text', null]]);
});

test('leaving the editor stores the plain text, typing in it does not', () => {
    const {editor, sourceNode} = initializeEditor('<p>a</p>', null, {textpath: '.text'});
    editor.fire('keydown');
    editor.value = '<p>ab</p>';
    editor.text = 'ab';
    editor.fire('change');
    assert.deepEqual(sourceNode.writes, [['value', '<p>ab</p>']]);
    editor.fire('blur');
    assert.deepEqual(sourceNode.writes, [['value', '<p>ab</p>'], ['.text', 'ab']]);
});

test('maxLength blocks input at the limit and takes the place of the Jodit counters', () => {
    const handler = loadHandler();
    const options = create(handler, {maxLength: 200}).options;
    assert.equal(options.limitChars, 200);
    // without countTextSpaces the plugin counts the words joined: it would block
    // at a different number than the statusbar shows
    assert.equal(options.countTextSpaces, true);
    assert.deepEqual([options.statusbar, options.showCharsCounter, options.showWordsCounter],
                     [true, false, false]);
    const unlimited = create(handler, {}).options;
    assert.equal('limitChars' in unlimited, false);
    assert.deepEqual([unlimited.statusbar, 'showCharsCounter' in unlimited], [false, false]);
});

function countCharacters(limit, text) {
    const handler = loadHandler({document: {createElement: () => ({style: {}})}});
    const listeners = {};
    const editor = {
        text, o: {limitChars: limit},
        statusbar: {append(node, atEnd) { editor.counter = node; editor.counterAtEnd = atEnd; }},
        e: {on(events, callback) { for (const name of events.split(' ')) (listeners[name] ||= []).push(callback); }},
        fire: (name) => (listeners[name] || []).forEach((callback) => callback())
    };
    handler.setupCharCounter(editor);
    return editor;
}

test('the statusbar counts the characters left and warns as the budget runs out', () => {
    const editor = countCharacters(100, 'a'.repeat(40));
    assert.equal(editor.counterAtEnd, true);
    assert.deepEqual([editor.counter.textContent, editor.counter.style.color], ['Remaining: 60', '']);
    editor.text = 'a'.repeat(95);
    editor.fire('keyup');
    assert.deepEqual([editor.counter.textContent, editor.counter.style.color], ['Remaining: 5', 'orange']);
    // only a value loaded over the limit goes negative: typing stops at it
    editor.text = 'a'.repeat(120);
    editor.fire('change');
    assert.deepEqual([editor.counter.textContent, editor.counter.style.color], ['Remaining: -20', 'red']);
});

test('the counter counts what the limit plugin counts: spaces in, block newlines out', () => {
    const handler = loadHandler();
    // editor.text is innerText: two paragraphs of nine characters joined by a newline
    assert.equal(handler.textLength({text: 'one two x\nfour five'}), 18);
    assert.equal(handler.textLength({text: 'a\uFEFFb'}), 2);
    assert.equal(handler.textLength({}), 0);
    assert.equal(countCharacters(30, 'one two x\nfour five').counter.textContent, 'Remaining: 12');
});

test('no counter without a character limit', () => {
    assert.equal(countCharacters(0, '').counter, undefined);
});

test('placeholders add a $ button inserting the name at the caret', () => {
    const options = create(loadHandler(), {placeholders: 'name, surname'}).options;
    // extraButtons is appended on its own: naming it here too renders it a second time
    assert.deepEqual([...options.buttons], [...loadHandler().toolbars.standard]);
    const [button] = options.extraButtons;
    assert.equal(button.text, '$');
    assert.deepEqual({...button.list}, {$name: '$name', $surname: '$surname'});
    let inserted;
    button.exec({s: {insertHTML: (html) => { inserted = html; }}}, null, {control: {args: ['$surname']}});
    assert.equal(inserted, '$surname');
});

test('placeholders accept a list as well as a comma string', () => {
    const [button] = create(loadHandler(), {placeholders: ['name', 'surname']}).options.extraButtons;
    assert.deepEqual({...button.list}, {$name: '$name', $surname: '$surname'});
});

test('placeholders have nowhere to go without a toolbar', () => {
    const options = create(loadHandler(), {placeholders: 'name', toolbar: false}).options;
    assert.equal('extraButtons' in options, false);
    assert.deepEqual([...options.buttons], []);
});

test('imageData embeds images as data URIs without discarding a configured uploader', () => {
    const handler = loadHandler();
    assert.equal(create(handler, {}).options.uploader, undefined);
    assert.deepEqual({...create(handler, {imageData: true}).options.uploader},
                     {insertImageAsBase64URI: true});
    const configured = create(handler, {imageData: true, config_uploader: {url: '/upload'}}).options;
    assert.deepEqual({...configured.uploader}, {insertImageAsBase64URI: true, url: '/upload'});
    const refused = create(handler, {imageData: true,
                                     config_uploader: {insertImageAsBase64URI: false}}).options;
    assert.equal(refused.uploader.insertImageAsBase64URI, false);
});

test('codeBlock adds a labelled button, never one falling back to its control name', () => {
    const [button] = create(loadHandler(), {codeBlock: true}).options.extraButtons;
    assert.equal(button.name, 'codeBlock');
    // with no icon Jodit renders control.text, or the bare control name when text is missing
    assert.equal(button.text, '{ }');
    assert.ok(button.tooltip);
});

test('codeBlock inserts an empty pre/code block and leaves the caret inside it', () => {
    const handler = loadHandler();
    const nodes = [];
    const editor = {
        createInside: {element: (tag, children) => {
            const node = {tag, children: children || []};
            nodes.push(node);
            return node;
        }},
        s: {insertNode: (node) => { editor.inserted = node; },
            setCursorIn: (node) => { editor.caretIn = node; }}
    };
    handler.insertCodeBlock(editor);
    assert.deepEqual(nodes.map((node) => node.tag), ['code', 'pre']);
    assert.equal(editor.inserted.tag, 'pre');
    assert.deepEqual([...editor.inserted.children], [editor.caretIn]);
    assert.equal(editor.caretIn.tag, 'code');
    assert.deepEqual(editor.caretIn.children, []);
});

test('codeBlock and placeholders are two buttons, neither of them in the toolbar list', () => {
    const handler = loadHandler();
    const options = create(handler, {codeBlock: true, placeholders: 'name'}).options;
    assert.deepEqual([...options.extraButtons].map((button) => button.name), ['placeholders', 'codeBlock']);
    assert.deepEqual([...options.buttons], [...handler.toolbars.standard]);
    const none = create(handler, {codeBlock: true, placeholders: 'name', toolbar: false}).options;
    assert.equal('extraButtons' in none, false);
});

test('no extraButtons key when nothing asks for one', () => {
    assert.equal('extraButtons' in create(loadHandler(), {}).options, false);
});
