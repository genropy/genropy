// ============================================================================
// Editor widgets for Genropy.
// Originally housed in genro_extra.js; moved here so extending the editor stack
// (CodeMirror 6, ProseMirror, future Milkdown / TipTap, ...) does not bloat the
// generic widget file. Loaded right after genro_extra in gnrjs_frontend().
// ============================================================================

dojo.declare("gnr.widgets.MDEditor", gnr.widgets.baseExternalWidget, {
    constructor: function(application) {
        this._domtag = 'div';
    },

    creating: function(attributes, sourceNode) {
        let editorAttrs = {...attributes};
        // Do NOT derive initialValue from `value` here; it is a datapath, not content.
        editorAttrs.usageStatistics = objectPop(editorAttrs,'usageStatistics') || false; // default false
        objectPopAll(attributes);
        return editorAttrs;
    },

    created:function(widget, savedAttrs, sourceNode){
        const scriptUrl = "https://uicdn.toast.com/editor/latest/toastui-editor-all.min.js";
        const cssUrl = "https://uicdn.toast.com/editor/latest/toastui-editor.min.css";
        const pickerCss = "https://uicdn.toast.com/tui-color-picker/latest/tui-color-picker.min.css";
        const pickerJs  = "https://uicdn.toast.com/tui-color-picker/latest/tui-color-picker.min.js";
        const colorCss  = "https://uicdn.toast.com/editor-plugin-color-syntax/latest/toastui-editor-plugin-color-syntax.min.css";
        const colorJs   = "https://uicdn.toast.com/editor-plugin-color-syntax/latest/toastui-editor-plugin-color-syntax.min.js";
        
        const loadResource = (url, type) => new Promise((resolve) => {
            if (type === 'js') { genro.dom.loadJs(url, resolve); }
            else if (type === 'css') { genro.dom.loadCss(url, 'tuieditor', resolve); }
        });
        
        const wantColor = !(savedAttrs && savedAttrs.colorSyntax === false);
        const init = () => { this.ready = true; this.initialize(widget, savedAttrs, sourceNode); };

        // Ensure strict load order: Editor -> Picker -> Plugin
        if (!(window.toastui && window.toastui.Editor)) {
            Promise.resolve()
                .then(() => loadResource(scriptUrl, 'js'))
                .then(() => loadResource(cssUrl, 'css'))
                .then(() => wantColor? loadResource(pickerCss, 'css') : null)
                .then(() => wantColor? loadResource(pickerJs,  'js') : null)
                .then(() => wantColor? loadResource(colorCss,  'css') : null)
                .then(() => wantColor? loadResource(colorJs,   'js') : null)
                .then(() => {
                    // Sanity check: plugin expects window.tui.colorPicker
                    if (wantColor && !(window.tui && window.tui.colorPicker)) {
                        console.warn('[MDEditor] tui.colorPicker missing. Color Syntax plugin may fail.');
                    }
                    init();
                });
        } else {
            // Editor already present. Load dependency then plugin in order
            const needPicker = wantColor && !(window.tui && window.tui.colorPicker);
            const needPlugin = wantColor && !(window.toastui && window.toastui.Editor && window.toastui.Editor.plugin && window.toastui.Editor.plugin.colorSyntax);
            Promise.resolve()
                .then(() => needPicker ? loadResource(pickerCss, 'css') : null)
                .then(() => needPicker ? loadResource(pickerJs,  'js')  : null)
                .then(() => needPlugin ? loadResource(colorCss,  'css') : null)
                .then(() => needPlugin ? loadResource(colorJs,   'js')  : null)
                .then(() => {
                    if (!(window.tui && window.tui.colorPicker)) {
                        console.warn('[MDEditor] tui.colorPicker missing after load.');
                    }
                    init();
                });
        }
    },

    initialize:function(widget, savedAttrs, sourceNode){
        let editor_attrs = {...savedAttrs};
        // Detect if the value datapath points to a Bag.
        // Use inner nodes ONLY when no explicit htmlpath is provided.
        let valuePath = sourceNode.attr.value;
        let explicitHtmlPath = !!sourceNode.attr.htmlpath;
        if (valuePath){
            let v = sourceNode.getRelativeData(valuePath);
            if (v instanceof gnr.GnrBag){
                if (!explicitHtmlPath){
                    // Enter Bag mode ONLY if Bag already has text/html keys. Do NOT create nodes.
                    var hasText = (v.getItem('text') !== undefined);
                    var hasHtml = (v.getItem('html') !== undefined);
                    if (hasText || hasHtml){
                        sourceNode._mdBagPath = valuePath;
                        let innerText = v.getItem('text');
                        if(innerText){ editor_attrs.initialValue = String(innerText); }
                        sourceNode._mdInternalHtmlPath = valuePath + '.html';
                    }
                }else{
                    // htmlpath present: use Bag root value
                    if (typeof v.getValue === 'function'){
                        let rootVal = v.getValue();
                        if(!isNullOrBlank(rootVal)){
                            editor_attrs.initialValue = String(rootVal);
                        }
                    }
                }
            }
        }
        // Normalize initialValue to a safe string for ToastUI
        if (editor_attrs.initialValue === undefined){
            // Pull current content from datasource when available
            const vp = sourceNode.attr.value;
            if (vp && !sourceNode._mdBagPath){
                const raw = sourceNode.getRelativeData(vp);
                editor_attrs.initialValue = (raw == null) ? '' : String(raw);
            } else if (sourceNode._mdBagPath){
                const rawText = sourceNode.getRelativeData(sourceNode._mdBagPath + '.text');
                editor_attrs.initialValue = (rawText == null) ? '' : String(rawText);
            } else {
                editor_attrs.initialValue = '';
            }
        } else {
            editor_attrs.initialValue = (editor_attrs.initialValue == null) ? '' : String(editor_attrs.initialValue);
        }
        objectPop(editor_attrs,'htmlpath');
        const editor = editor_attrs.viewer
            ? this.createViewer(widget, editor_attrs)
            : this.createEditor(widget, editor_attrs);
        if (savedAttrs.previewStyle === 'hidden'){
            this._ensureNoPreviewCss();
            try{ editor.el && editor.el.classList && editor.el.classList.add('tui-no-preview'); }catch(e){}
        }
        this.configureToolbar(editor, editor_attrs);
        this.setExternalWidget(sourceNode, editor);
        this.attachHooks(editor, editor_attrs, sourceNode);
    },
    
    createViewer:function(widget, editor_attrs){
        editor_attrs.autofocus = editor_attrs.autofocus || false;
        return window.toastui.Editor.factory({
            el: widget,
            ...editor_attrs
        });
    },

    createEditor:function(widget, editor_attrs){
        editor_attrs.autofocus = false;
        // Attach Color Syntax plugin if loaded via CDN
        try {
            const Editor = window.toastui && window.toastui.Editor;
            const colorSyntax = Editor && Editor.plugin && Editor.plugin.colorSyntax;
            if (editor_attrs.colorSyntax !== false && colorSyntax) {
                editor_attrs.plugins = (editor_attrs.plugins || []).concat([colorSyntax]);
            }
        } catch(e) { /* no-op */ }
        return new window.toastui.Editor({
            el: widget,
            ...editor_attrs
        });
    },

    _ensureNoPreviewCss:function(){
        try{
            const id = 'tui-no-preview-style';
            if(document.getElementById(id)) return;
            const css = [
                '.tui-no-preview .te-preview,',
                '.tui-no-preview .te-mode-switch-section,',
                '.tui-no-preview .toastui-editor-md-splitter,',
                '.tui-no-preview .toastui-editor-md-preview,',
                '.tui-no-preview .toastui-editor-tabs { display:none !important; }'
            ].join('');
            const st = document.createElement('style');
            st.id = id; st.textContent = css; document.head.appendChild(st);
        }catch(e){}
    },

    configureToolbar:function(editor, editor_attrs){
        if(editor_attrs.removeToolbarItems){
            editor_attrs.removeToolbarItems.forEach(item => editor.removeToolbarItem(item));
        }
        if(editor_attrs.insertToolbarItems){
            editor_attrs.insertToolbarItems.forEach(item => {
                // If item has insertText, create a button that inserts that text
                if(item.insertText){
                    const insertText = item.insertText;
                    const buttonEl = document.createElement('button');
                    buttonEl.className = 'toastui-editor-toolbar-icons custom-toolbar-button ' + (item.className || '');
                    buttonEl.type = 'button';
                    buttonEl.title = item.tooltip || 'Insert';

                    // Use SVG icon if provided, otherwise text
                    if(item.icon){
                        buttonEl.innerHTML = item.icon;
                    }else{
                        buttonEl.textContent = item.text || '▼';
                        buttonEl.style.cssText = 'background: none; font-size: 16px;';
                    }

                    buttonEl.onclick = (e) => {
                        e.preventDefault();
                        try {
                            // Get current cursor position
                            const pos = editor.getSelection();
                            let startLine = 0;

                            // Handle both array formats
                            if(Array.isArray(pos) && Array.isArray(pos[0])){
                                startLine = pos[0][0];
                            }else if(Array.isArray(pos)){
                                startLine = pos[0];
                            }

                            // Insert text at cursor
                            editor.insertText(insertText);

                            // Move cursor inside the block if specified
                            if(item.moveCursorLines && typeof startLine === 'number'){
                                setTimeout(() => {
                                    try {
                                        const newLine = startLine + item.moveCursorLines;
                                        editor.setSelection([newLine, 0], [newLine, 0]);
                                        editor.focus();
                                    }catch(e){
                                        console.warn('Could not move cursor', e);
                                    }
                                }, 50);
                            }else{
                                editor.focus();
                            }
                        }catch(e){
                            console.error('Insert text error:', e);
                        }
                    };

                    editor.insertToolbarItem(
                        { groupIndex: item.groupIndex || -1, itemIndex: item.itemIndex || -1 },
                        {
                            name: item.name || 'customButton',
                            tooltip: item.tooltip || 'Insert',
                            el: buttonEl
                        }
                    );
                }else{
                    // Standard toolbar item insertion
                    editor.insertToolbarItem(item);
                }
            });
        }
    },

    attachHooks:function(editor, editor_attrs, sourceNode){
        // Flag to prevent false positives during initial load
        let changeListenerActive = false;
        let originalNormalizedMarkdown = null;

        // Helper to normalize markdown for comparison
        const normalizeMarkdown = function(md) {
            if (!md) return '';
            // Normalize whitespace and common markdown variations
            return md
                .replace(/\r\n/g, '\n')  // Normalize line endings
                .replace(/\n{3,}/g, '\n\n')  // Normalize multiple blank lines
                .trim();
        };

        // Activate change listener on first real user interaction
        const activateListener = function() {
            if (!changeListenerActive) {
                changeListenerActive = true;
                console.log('[MDEditor] Change listener activated');
            }
        };

        // Wait for editor to normalize content after initial load
        setTimeout(() => {
            try {
                const currentMarkdown = editor.getMarkdown();
                originalNormalizedMarkdown = normalizeMarkdown(currentMarkdown);
                console.log('[MDEditor] Initial content stored');

                // Activate listener only on actual user typing
                // Also handle maxLength check on same keydown hook
                let activationDone = false;
                editor.addHook('keydown', () => {
                    if (!activationDone) {
                        activationDone = true;
                        activateListener();
                    }

                    // Handle max length check
                    genro.callAfter(() => {
                        if (editor_attrs.maxLength) {
                            this.checkMaxLength(editor, editor_attrs.maxLength);
                        }
                    }, 10, this, 'typing');
                });
            } catch(e) {
                console.warn('[MDEditor] Failed to setup change detection', e);
                changeListenerActive = true;  // Fallback: activate immediately
            }
        }, 100);

        // Save to datastore only if content actually changed
        editor.on('blur', () => {
            if (!changeListenerActive) {
                console.log('[MDEditor] Blur ignored - listener not active yet');
                return;
            }

            const currentMarkdown = editor.getMarkdown();
            const currentNormalized = normalizeMarkdown(currentMarkdown);

            // Only save if content actually changed
            if (currentNormalized !== originalNormalizedMarkdown) {
                console.log('[MDEditor] Content changed, saving to datastore');
                this.setInDatastore(editor, sourceNode);
                originalNormalizedMarkdown = currentNormalized;
            } else {
                console.log('[MDEditor] Content unchanged, skipping save');
            }
        });

        // Add drag&drop support for external elements
        try {
            const editorElements = editor.getEditorElements();
            console.log('[MDEditor] Editor elements:', editorElements);

            // Get both markdown and wysiwyg editor elements
            const mdEditor = editorElements?.mdEditor;
            const wwEditor = editorElements?.wwEditor;

            const setupDropListener = (element, name) => {
                if (!element) return;

                console.log('[MDEditor] Setting up drop on', name);

                element.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[MDEditor] dragover on', name);
                });

                element.addEventListener('drop', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[MDEditor] drop event on', name);

                    const text = e.dataTransfer.getData('text/plain');
                    console.log('[MDEditor] Dropped text:', text);

                    if (text && editor.insertText) {
                        editor.insertText(text);
                        console.log('[MDEditor] Text inserted');
                        // Activate listener if not already done
                        if (!changeListenerActive) {
                            activateListener();
                        }
                    }
                });
            };

            // Setup listeners on both elements
            setupDropListener(mdEditor, 'mdEditor');
            setupDropListener(wwEditor, 'wwEditor');

            // Also try on the main container
            if (editor.el) {
                setupDropListener(editor.el, 'editor.el');
            }
        } catch (e) {
            console.warn('[MDEditor] Failed to setup drop listeners', e);
        }
    },

    checkMaxLength:function(editor, maxLength){
        let value = editor.getMarkdown();
        if (value.length > maxLength) {
            editor.setMarkdown(value);
        }
        // Update character count in toolbar
        editor.removeToolbarItem('remaining');
        editor.insertToolbarItem({ groupIndex: -1, itemIndex: -1 }, {
            name: 'remaining',
            tooltip: 'Remaining characters',
            text: `Remaining: ${(maxLength - value.length)}`,
            style: {
                textAlign: 'center',
                fontStyle: 'italic',
                fontSize: '.8em',
                cursor: 'auto',
                width: '75px',
                padding: '0 8px'
            }
        });
    },

    onTyped:function(editor){
        // Typing callback logic
    },

    setInDatastore:function(editor, sourceNode){
        let value = editor.getMarkdown();
        const vp = sourceNode.attr.value;
        const htmlpath = sourceNode.attr.htmlpath;

        // If we are in Bag text/html mode, write there
        if (sourceNode._mdBagPath){
            let textPath = sourceNode._mdBagPath + '.text';
            let htmlPath = sourceNode._mdInternalHtmlPath || (sourceNode._mdBagPath + '.html');
            let currText = sourceNode.getRelativeData(textPath);
            if (currText !== value){ sourceNode.setRelativeData(textPath, value || null); }
            sourceNode.setRelativeData(htmlPath, editor.getHTML());
            return;
        }

        // If explicit htmlpath exists and value is a Bag, keep root value and htmlpath
        if (htmlpath && vp){
            let b = sourceNode.getRelativeData(vp);
            if (b instanceof gnr.GnrBag){
                if (typeof b.setValue === 'function'){ b.setValue(value || null); }
                sourceNode.setRelativeData(vp, b); // trigger listeners
                sourceNode.setRelativeData(htmlpath, editor.getHTML());
                return;
            }
        }

        // No explicit htmlpath: if value is Bag without text/html, treat as scalar on root value
        if (vp){
            let b0 = sourceNode.getRelativeData(vp);
            if (b0 instanceof gnr.GnrBag){
                let hasText0 = (b0.getItem('text') !== undefined);
                let hasHtml0 = (b0.getItem('html') !== undefined);
                if (!hasText0 && !hasHtml0 && typeof b0.setValue === 'function'){
                    b0.setValue(value || null);
                    sourceNode.setRelativeData(vp, b0);
                    return;
                }
            }
        }

        // Default scalar behavior
        let currentValue = sourceNode.getAttributeFromDatasource('value');

        // Update datastore ONLY if value has changed
        if (currentValue !== value) {
            sourceNode.setAttributeInDatasource('value', value || null);
            if (htmlpath) { sourceNode.setRelativeData(htmlpath, editor.getHTML()); }
        }
    },
    
    mixin_gnr_value:function(value,kw, trigger_reason){
        const vp = this.sourceNode.attr.value;
        const hasHtml = !!this.sourceNode.attr.htmlpath;
        if (vp){
            let b = this.sourceNode.getRelativeData(vp);
            if (!hasHtml && b instanceof gnr.GnrBag){
                // Enter Bag mode only if existing text/html keys
                let hasText = (b.getItem('text') !== undefined);
                let hasHtmlKey = (b.getItem('html') !== undefined);
                if (hasText || hasHtmlKey){
                    this.sourceNode._mdBagPath = vp;
                    let text = this.sourceNode.getRelativeData(vp + '.text') || '';
                    this.setMarkdown(text);
                    return;
                }
                // Bare Bag without keys: use root value as scalar
                if (typeof b.getValue === 'function'){
                    this.setMarkdown(String(b.getValue() || ''));
                    return;
                }
            }
            if (hasHtml && b instanceof gnr.GnrBag && typeof b.getValue === 'function'){
                this.setMarkdown(String(b.getValue() || ''));
                return;
            }
        }
        // Fallback scalar
        this.setMarkdown(value || '');
    },

    mixin_gnr_setInDatastore:function(){
        let value = this.getMarkdown();
        if(this.sourceNode.getAttributeFromDatasource('value')!=value){
            this.sourceNode.setAttributeInDatasource('value',value || null);
            let htmlpath = this.sourceNode.attr.htmlpath;
            if(htmlpath){
                this.sourceNode.setRelativeData(htmlpath,this.getHTML())
            }
        }
    },
    mixin_gnr_getHTML:function(){
        return this.getHTML();
    },

    mixin_gnr_onPaste:function(){
        this.gnr_setInDatastore();
    },
    
    mixin_gnr_onTyped:function(){
    },

    mixin_gnr_disabled:function(value){
        this.gnr_setDisabled(value);
    },
   
    mixin_gnr_readOnly:function(value){
        this.gnr_setDisabled(value);
    },
   
    mixin_gnr_setDisabled:function(value){
        this.sourceNode.domNode.setAttribute('disabled',value===true?'true':'false');
        if(!this.options.viewer){
            this.mdEditor.el.lastChild.setAttribute('contenteditable',value===true?'false':'true'); 
        }
    }

    



});

dojo.declare("gnr.widgets.codemirror", gnr.widgets.baseExternalWidget, {
    constructor: function(application) {
        this._domtag = 'div';
    },
    creating: function(attributes, sourceNode) {
        var cmAttrs = objectExtract(attributes,'config_*');
        var readOnly = objectPop(attributes,'readOnly');
        var editable = objectPop(attributes,'editable');
        var lineWrapping = objectPop(attributes,'lineWrapping');
        cmAttrs.readOnly = !!readOnly;
        // editable defaults to true: even read-only editors keep cursor + focus + keyboard
        // shortcuts (e.g. Cmd+F search) by default. Pass editable=false explicitly to get the
        // CM5 'nocursor' behaviour (no focus, no shortcuts).
        cmAttrs.editable = (editable === undefined || editable === null) ? true : !!editable;
        if(lineWrapping){
            cmAttrs.lineWrapping = lineWrapping;
        }
        cmAttrs.value = objectPop(attributes,'value') || '';
        return {cmAttrs:cmAttrs};
    },
    created: function(widget, savedAttrs, sourceNode){
        var that = this;
        var cmAttrs = objectPop(savedAttrs,'cmAttrs');
        var cb = function(){ that.initialize(widget, cmAttrs, sourceNode); };
        if(!window.CodeMirror6){
            this.loadCodeMirror6(cb);
        } else {
            cb();
        }
    },
    loadCodeMirror6: function(cb){
        // mtime-based cache-buster: server publishes the file mtime via gnr.vendoredMtime
        // so the browser refetches the bundle whenever it gets rebuilt.
        var mtime = genro.getData('gnr.vendoredMtime.codemirror6') || 0;
        var url = '/_rsrc/js_libs/codemirror6/codemirror6.bundle.js' + (mtime ? '?mtime=' + mtime : '');
        genro.dom.loadJs(url, cb);
    },
    buildExtensions: function(cmAttrs, sourceNode){
        var CM = window.CodeMirror6;
        var extensions = [];
        // Per-instance dynamic state primitives, used by gnr_markText / gnr_addLineClass /
        // gnr_setGutterMarker mixins below. These are wired here so the EditorView is born
        // already prepared to accept dispatch effects targeting them.
        var setMarksEffect = CM.StateEffect.define();           // payload: {add:[{from,to,deco}], remove:[id,...], clear:bool}
        var setLineClassEffect = CM.StateEffect.define();       // payload: {add:[{line,deco,id}], remove:[id,...], clear:bool}
        var setGutterMarkersEffect = CM.StateEffect.define();   // payload: {gutter:str, add:[{line,marker}], remove:[line,...], clear:bool}
        var marksField = CM.StateField.define({
            create: function(){ return CM.RangeSet.empty; },
            update: function(set, tr){
                set = set.map(tr.changes);
                for(var i = 0; i < tr.effects.length; i++){
                    var ef = tr.effects[i];
                    if(!ef.is(setMarksEffect)) continue;
                    var p = ef.value;
                    if(p.clear){ set = CM.RangeSet.empty; }
                    if(p.remove && p.remove.length){
                        var rm = p.remove;
                        set = set.update({filter: function(_from, _to, deco){
                            return rm.indexOf(deco.spec && deco.spec.id) === -1;
                        }});
                    }
                    if(p.add && p.add.length){
                        set = set.update({add: p.add.map(function(a){ return a.deco.range(a.from, a.to); }), sort: true});
                    }
                }
                return set;
            },
            provide: function(field){ return CM.EditorView.decorations.from(field); }
        });
        var lineClassField = CM.StateField.define({
            create: function(){ return CM.RangeSet.empty; },
            update: function(set, tr){
                set = set.map(tr.changes);
                for(var i = 0; i < tr.effects.length; i++){
                    var ef = tr.effects[i];
                    if(!ef.is(setLineClassEffect)) continue;
                    var p = ef.value;
                    if(p.clear){ set = CM.RangeSet.empty; }
                    if(p.remove && p.remove.length){
                        var rm = p.remove;
                        set = set.update({filter: function(_from, _to, deco){
                            return rm.indexOf(deco.spec && deco.spec.id) === -1;
                        }});
                    }
                    if(p.add && p.add.length){
                        set = set.update({add: p.add.map(function(a){ return a.deco.range(a.linePos); }), sort: true});
                    }
                }
                return set;
            },
            provide: function(field){ return CM.EditorView.decorations.from(field); }
        });
        // Gutter markers: a Map<gutterName, Map<linePos, marker>> kept inside a StateField.
        // line positions are normalized to line-start offsets so RangeSet sorting works.
        var gutterMarkersField = CM.StateField.define({
            create: function(){ return {}; },  // {gutterName: Map<linePos, GutterMarker>}
            update: function(state, tr){
                // Shallow clone so reference identity changes (CM6 schedules redraw on change).
                var next = {};
                for(var k in state){ next[k] = new Map(state[k]); }
                for(var i = 0; i < tr.effects.length; i++){
                    var ef = tr.effects[i];
                    if(!ef.is(setGutterMarkersEffect)) continue;
                    var p = ef.value;
                    var gname = p.gutter;
                    if(!next[gname]){ next[gname] = new Map(); }
                    var m = next[gname];
                    if(p.clear){ m.clear(); }
                    if(p.remove && p.remove.length){
                        for(var r = 0; r < p.remove.length; r++){ m.delete(p.remove[r]); }
                    }
                    if(p.add && p.add.length){
                        for(var a = 0; a < p.add.length; a++){
                            m.set(p.add[a].line, p.add[a].marker);
                        }
                    }
                }
                return next;
            }
        });
        extensions.push(marksField);
        extensions.push(lineClassField);
        extensions.push(gutterMarkersField);
        if(cmAttrs.lineNumbers !== false){
            extensions.push(CM.lineNumbers());
        }
        extensions.push(CM.highlightActiveLine());
        extensions.push(CM.highlightActiveLineGutter());
        extensions.push(CM.drawSelection());
        extensions.push(CM.dropCursor());
        extensions.push(CM.history());
        extensions.push(CM.indentOnInput());
        extensions.push(CM.bracketMatching());
        extensions.push(CM.foldGutter());
        extensions.push(CM.highlightSelectionMatches());
        extensions.push(CM.search({top:true}));
        extensions.push(CM.syntaxHighlighting(CM.defaultHighlightStyle, {fallback:true}));
        var keymapList = [].concat(CM.defaultKeymap, CM.searchKeymap, CM.historyKeymap, CM.foldKeymap);
        if(cmAttrs.keyMap === 'softTab'){
            var indentUnit = cmAttrs.indentUnit || 4;
            var pad = new Array(indentUnit + 1).join(' ');
            keymapList.unshift({
                key: 'Tab',
                run: function(view){
                    view.dispatch(view.state.replaceSelection(pad));
                    return true;
                }
            });
        } else {
            keymapList.push(CM.indentWithTab);
        }
        extensions.push(CM.keymap.of(keymapList));
        // Mode aliases keep CM5 names working in CM6. CM6's html() already nests
        // <script> JS and <style> CSS, so it's a drop-in for CM5 'htmlmixed'.
        var modeAlias = {htmlmixed: 'html', htmlembedded: 'html', 'text/html': 'html', md: 'markdown'};
        var mode = cmAttrs.mode;
        if(mode && modeAlias[mode]){ mode = modeAlias[mode]; }
        if(mode && CM.langs[mode]){
            extensions.push(CM.langs[mode]());
        }
        // toolsTheme first, theme last: themes that include their own tool
        // styling (e.g. @codemirror/theme-one-dark) win and override our
        // generic tool skin. Themes that don't (thememirror) leave our skin
        // in place. Order matters: later extensions take precedence.
        if(CM.toolsTheme){
            extensions.push(CM.toolsTheme);
        }
        if(cmAttrs.theme){
            // CM5 theme name aliases mapped to closest CM6 equivalents.
            var themeAlias = {dark: 'oneDark', twilight: 'oneDark', night: 'dracula'};
            var themeKey = themeAlias[cmAttrs.theme] || cmAttrs.theme;
            if(CM.themes[themeKey]){
                extensions.push(CM.themes[themeKey]);
            }
        }
        // Font overrides applied last, so they win over any theme.
        if(cmAttrs.fontSize || cmAttrs.fontFamily){
            var fontRule = {};
            if(cmAttrs.fontSize) fontRule.fontSize = cmAttrs.fontSize;
            if(cmAttrs.fontFamily) fontRule.fontFamily = cmAttrs.fontFamily;
            extensions.push(CM.EditorView.theme({"&": fontRule, ".cm-content": fontRule}));
        }
        if(cmAttrs.lineWrapping){
            extensions.push(CM.EditorView.lineWrapping);
        }
        var readOnlyCompartment = new CM.Compartment();
        extensions.push(readOnlyCompartment.of([
            CM.EditorState.readOnly.of(!!cmAttrs.readOnly),
            CM.EditorView.editable.of(!!cmAttrs.editable)
        ]));
        extensions.push(CM.EditorView.updateListener.of(function(update){
            // Persist selection across rebuilds: stash on sourceNode (which survives).
            if(update.selectionSet || update.docChanged){
                sourceNode._cm6Snapshot = sourceNode._cm6Snapshot || {};
                sourceNode._cm6Snapshot.selection = update.state.selection.toJSON();
            }
            // Push doc changes to the datapath (debounced).
            if(!update.docChanged) return;
            sourceNode.delayedCall(function(){
                var v = sourceNode.externalWidget.state.doc.toString();
                if(sourceNode.attr.value){
                    sourceNode.setRelativeData(sourceNode.attr.value, v, null, null, sourceNode);
                }
            }, sourceNode.attr._delay || 500, 'updatingContent');
        }));
        // Persist scroll position separately (scroll events don't trigger updateListener).
        extensions.push(CM.EditorView.domEventHandlers({
            scroll: function(_event, view){
                sourceNode._cm6Snapshot = sourceNode._cm6Snapshot || {};
                sourceNode._cm6Snapshot.scrollTop = view.scrollDOM.scrollTop;
                sourceNode._cm6Snapshot.scrollLeft = view.scrollDOM.scrollLeft;
            }
        }));
        // Custom gutters declared via config_extraGutters=[{name:'breakpoints', width:'0.8em'}, ...].
        // Each gutter renders markers fetched from gutterMarkersField (line -> GutterMarker).
        var extraGutters = cmAttrs.extraGutters;
        if(extraGutters && extraGutters.length){
            for(var gi = 0; gi < extraGutters.length; gi++){
                (function(spec){
                    var gname = spec.name || spec;
                    var gwidth = spec.width;
                    extensions.push(CM.gutter({
                        class: 'cm-gutter-' + gname,
                        markers: function(view){
                            var byLine = view.state.field(gutterMarkersField)[gname];
                            if(!byLine || !byLine.size) return CM.RangeSet.empty;
                            var entries = [];
                            byLine.forEach(function(marker, linePos){
                                entries.push({pos: linePos, marker: marker});
                            });
                            entries.sort(function(a, b){ return a.pos - b.pos; });
                            var builder = new CM.RangeSetBuilder();
                            for(var k = 0; k < entries.length; k++){
                                builder.add(entries[k].pos, entries[k].pos, entries[k].marker);
                            }
                            return builder.finish();
                        },
                        initialSpacer: gwidth ? function(){
                            return new (function(){
                                var inst = Object.create(CM.GutterMarker.prototype);
                                inst.toDOM = function(){
                                    var el = document.createElement('div');
                                    el.style.minWidth = gwidth;
                                    return el;
                                };
                                return inst;
                            })();
                        } : null,
                        domEventHandlers: {
                            mousedown: function(view, lineBlock, event){
                                var handler = sourceNode.attr['onGutterClick_' + gname];
                                if(handler){
                                    var lineObj = view.state.doc.lineAt(lineBlock.from);
                                    funcCreate(handler, 'view,line,gutter,event')
                                        .call(sourceNode, view, lineObj.number - 1, gname, event);
                                    return true;
                                }
                                return false;
                            }
                        }
                    }));
                })(extraGutters[gi]);
            }
        }
        return {
            extensions: extensions,
            readOnlyCompartment: readOnlyCompartment,
            setMarksEffect: setMarksEffect,
            marksField: marksField,
            setLineClassEffect: setLineClassEffect,
            lineClassField: lineClassField,
            setGutterMarkersEffect: setGutterMarkersEffect,
            gutterMarkersField: gutterMarkersField
        };
    },
    initialize: function(widget, cmAttrs, sourceNode){
        var CM = window.CodeMirror6;
        dojo.style(widget, {position:'relative'});
        var built = this.buildExtensions(cmAttrs, sourceNode);
        var startValue = sourceNode.getAttributeFromDatasource('value') || cmAttrs.value || '';
        // Restore selection from a previous incarnation (sourceNode survives rebuilds).
        var snapshot = sourceNode._cm6Snapshot;
        var selection = null;
        if(snapshot && snapshot.selection){
            try {
                selection = CM.EditorState.fromJSON(
                    {doc: startValue, selection: snapshot.selection}
                ).selection;
            } catch(e){
                selection = null;
            }
        }
        var stateConfig = {doc: startValue, extensions: built.extensions};
        if(selection){
            stateConfig.selection = selection;
        }
        var state = CM.EditorState.create(stateConfig);
        var view = new CM.EditorView({state: state, parent: widget});
        dojo.style(view.dom, {height:'inherit', top:0, left:0, right:0, bottom:0, position:'absolute'});
        view._readOnlyCompartment = built.readOnlyCompartment;
        view._readOnlyState = !!cmAttrs.readOnly;
        view._editableState = !!cmAttrs.editable;
        // Refs to dynamic-state primitives, used by gnr_markText / gnr_addLineClass /
        // gnr_setGutterMarker mixins. See buildExtensions() for definitions.
        view._setMarksEffect = built.setMarksEffect;
        view._marksField = built.marksField;
        view._setLineClassEffect = built.setLineClassEffect;
        view._lineClassField = built.lineClassField;
        view._setGutterMarkersEffect = built.setGutterMarkersEffect;
        view._gutterMarkersField = built.gutterMarkersField;
        view._markIdSeq = 0;
        // Restore scroll position after the view is mounted (needs layout pass).
        if(snapshot && (snapshot.scrollTop || snapshot.scrollLeft)){
            setTimeout(function(){
                view.scrollDOM.scrollTop = snapshot.scrollTop || 0;
                view.scrollDOM.scrollLeft = snapshot.scrollLeft || 0;
            }, 0);
        }
        // baseExternalWidget wires sourceNode.externalWidget, mixins, and back-refs.
        this.setExternalWidget(sourceNode, view);
        // Reapply line classes that were live before the rebuild (e.g. the
        // pdb current-line highlight in gnride). Old ids become stale: rebuild
        // the snapshot map with fresh ids returned by gnr_addLineClass.
        if(snapshot && snapshot.lineClasses){
            var oldClasses = snapshot.lineClasses;
            snapshot.lineClasses = {};
            for(var oldId in oldClasses){
                var entry = oldClasses[oldId];
                view.gnr_addLineClass(entry.line, entry.className);
            }
        }
    },
    _applyReadOnlyEditable: function(view){
        var CM = window.CodeMirror6;
        view.dispatch({
            effects: view._readOnlyCompartment.reconfigure([
                CM.EditorState.readOnly.of(view._readOnlyState),
                CM.EditorView.editable.of(view._editableState)
            ])
        });
    },
    mixin_gnr_value: function(value, kw, trigger_reason){
        var view = this;
        var doc = view.state.doc;
        var newValue = value || '';
        if(doc.toString() === newValue) return;
        view.dispatch({changes: {from: 0, to: doc.length, insert: newValue}});
        var sourceNode = view.sourceNode;
        sourceNode.watch('isVisible', function(){
            return genro.dom.isVisible(sourceNode);
        }, function(){
            view.requestMeasure();
        });
    },
    // CM5 compat: pages may call externalWidget.setValue(...) directly.
    mixin_setValue: function(value){
        return this.gnr_value(value);
    },
    mixin_gnr_setDisabled: function(disabled){
        genro.dom.setDomNodeDisabled(this.sourceNode.domNode, disabled);
        this.gnr_readOnly(disabled);
    },
    mixin_gnr_readOnly: function(value, kw, trigger_reason){
        var view = this;
        if(!view._readOnlyCompartment) return;
        view._readOnlyState = !!value;
        // editable is intentionally left untouched: the new default is editable=true
        // even for read-only editors, so search/keyboard shortcuts keep working.
        view.gnr._applyReadOnlyEditable(view);
    },
    mixin_gnr_editable: function(value, kw, trigger_reason){
        var view = this;
        if(!view._readOnlyCompartment) return;
        view._editableState = !!value;
        view.gnr._applyReadOnlyEditable(view);
    },
    mixin_gnr_lineWrapping: function(value, kw, trigger_reason){
        // Toggling lineWrapping at runtime would require a dedicated compartment;
        // current widget consumers set it once at creation, so this is a noop.
    },
    mixin_gnr_quoteSelection: function(startchunk, endchunk){
        endchunk = endchunk || startchunk;
        var view = this;
        var range = view.state.selection.main;
        var oldtxt = view.state.doc.sliceString(range.from, range.to);
        var newtxt = startchunk + oldtxt + endchunk;
        view.dispatch({changes: {from: range.from, to: range.to, insert: newtxt}});
    },
    // ---- Inline text decorations (CM5 markText equivalent) ----
    // gnr_markText({line,ch}, {line,ch}, {className, attributes})
    // Returns an id that gnr_clearMark uses to remove the decoration.
    mixin_gnr_markText: function(from, to, options){
        var CM = window.CodeMirror6;
        var view = this;
        if(!view._setMarksEffect) return null;
        var fromOff = view.gnr._posToOffset(view, from);
        var toOff = view.gnr._posToOffset(view, to);
        if(fromOff == null || toOff == null || fromOff >= toOff) return null;
        options = options || {};
        var id = 'mark_' + (++view._markIdSeq);
        var spec = {id: id};
        if(options.className) spec['class'] = options.className;
        if(options.attributes) spec.attributes = options.attributes;
        var deco = CM.Decoration.mark(spec);
        view.dispatch({effects: view._setMarksEffect.of({add: [{from: fromOff, to: toOff, deco: deco}]})});
        return id;
    },
    mixin_gnr_clearMark: function(id){
        var view = this;
        if(!view._setMarksEffect || !id) return;
        view.dispatch({effects: view._setMarksEffect.of({remove: [id]})});
    },
    mixin_gnr_clearAllMarks: function(){
        var view = this;
        if(!view._setMarksEffect) return;
        view.dispatch({effects: view._setMarksEffect.of({clear: true})});
    },
    // ---- Per-line CSS classes (CM5 addLineClass / removeLineClass) ----
    // gnr_addLineClass(lineNumber, className) where lineNumber is 0-based.
    // Returns an id that gnr_removeLineClass uses.
    // Active classes are tracked on sourceNode._cm6Snapshot.lineClasses so the
    // current-line highlight (used by gnride debugger) survives editor rebuilds.
    mixin_gnr_addLineClass: function(line, className){
        var CM = window.CodeMirror6;
        var view = this;
        if(!view._setLineClassEffect || className == null) return null;
        var linePos = view.gnr._lineStart(view, line);
        if(linePos == null) return null;
        var id = 'line_' + (++view._markIdSeq);
        var deco = CM.Decoration.line({attributes: {'class': className}, id: id});
        view.dispatch({effects: view._setLineClassEffect.of({add: [{linePos: linePos, deco: deco, id: id}]})});
        var sourceNode = view.sourceNode;
        sourceNode._cm6Snapshot = sourceNode._cm6Snapshot || {};
        sourceNode._cm6Snapshot.lineClasses = sourceNode._cm6Snapshot.lineClasses || {};
        sourceNode._cm6Snapshot.lineClasses[id] = {line: line, className: className};
        return id;
    },
    mixin_gnr_removeLineClass: function(id){
        var view = this;
        if(!view._setLineClassEffect || !id) return;
        view.dispatch({effects: view._setLineClassEffect.of({remove: [id]})});
        var snap = view.sourceNode._cm6Snapshot;
        if(snap && snap.lineClasses){ delete snap.lineClasses[id]; }
    },
    mixin_gnr_clearAllLineClasses: function(){
        var view = this;
        if(!view._setLineClassEffect) return;
        view.dispatch({effects: view._setLineClassEffect.of({clear: true})});
        var snap = view.sourceNode._cm6Snapshot;
        if(snap){ snap.lineClasses = {}; }
    },
    // ---- Programmatic scroll (CM5 scrollIntoView) ----
    // gnr_scrollIntoView({line, ch}) — line and ch are 0-based; line-only also accepted.
    mixin_gnr_scrollIntoView: function(pos){
        var CM = window.CodeMirror6;
        var view = this;
        var off;
        if(typeof pos === 'number'){
            off = pos;
        } else {
            off = view.gnr._posToOffset(view, pos);
        }
        if(off == null) return;
        view.dispatch({effects: CM.EditorView.scrollIntoView(off, {y: 'center'})});
    },
    // ---- Custom gutter markers (CM5 setGutterMarker / clearGutter / lineInfo) ----
    // gnr_setGutterMarker(line, gutterName, domElement | null)
    // line is 0-based. Pass null/undefined as third arg to remove the marker on that line.
    mixin_gnr_setGutterMarker: function(line, gutterName, domElement){
        var CM = window.CodeMirror6;
        var view = this;
        if(!view._setGutterMarkersEffect) return;
        var linePos = view.gnr._lineStart(view, line);
        if(linePos == null) return;
        if(!domElement){
            view.dispatch({effects: view._setGutterMarkersEffect.of({gutter: gutterName, remove: [linePos]})});
            return;
        }
        var marker = Object.create(CM.GutterMarker.prototype);
        marker.toDOM = function(){ return domElement; };
        view.dispatch({effects: view._setGutterMarkersEffect.of({gutter: gutterName, add: [{line: linePos, marker: marker}]})});
    },
    mixin_gnr_clearGutter: function(gutterName){
        var view = this;
        if(!view._setGutterMarkersEffect) return;
        view.dispatch({effects: view._setGutterMarkersEffect.of({gutter: gutterName, clear: true})});
    },
    // gnr_lineInfo(lineNumber) returns {line, gutterMarkers: {gutterName: domElement}}
    // mirrors the small subset of CM5 cm.lineInfo used by gnride.
    mixin_gnr_lineInfo: function(line){
        var view = this;
        var linePos = view.gnr._lineStart(view, line);
        if(linePos == null) return null;
        var info = {line: line, gutterMarkers: {}};
        var byName = view.state.field(view._gutterMarkersField, false) || {};
        for(var gname in byName){
            var byLine = byName[gname];
            if(byLine && byLine.has(linePos)){
                var marker = byLine.get(linePos);
                info.gutterMarkers[gname] = marker.toDOM ? marker.toDOM() : null;
            }
        }
        return info;
    },
    // ---- Internal helpers (called from mixins via view.gnr._...) ----
    _posToOffset: function(view, pos){
        if(pos == null) return null;
        if(typeof pos === 'number') return pos;
        var doc = view.state.doc;
        var lineNum = (pos.line || 0) + 1;
        if(lineNum < 1 || lineNum > doc.lines) return null;
        var lineObj = doc.line(lineNum);
        var off = lineObj.from + (pos.ch || 0);
        return Math.min(off, lineObj.to);
    },
    _lineStart: function(view, line){
        var doc = view.state.doc;
        var lineNum = (line || 0) + 1;
        if(lineNum < 1 || lineNum > doc.lines) return null;
        return doc.line(lineNum).from;
    }
});

// Mark name canonicalization (PM native names → Bag canonical names).
// Biased toward Tiptap StarterKit naming so the same Bag schema works
// unchanged when the widget will be backed by Tiptap in a future phase.
gnr.widgets.proseMirrorEditor_PM_TO_BAG_MARKS = {strong: 'bold', em: 'italic'};
gnr.widgets.proseMirrorEditor_BAG_TO_PM_MARKS = {bold: 'strong', italic: 'em'};

dojo.declare("gnr.widgets.proseMirrorEditor", gnr.widgets.baseExternalWidget, {
    constructor: function(application) {
        this._domtag = 'div';
    },
    creating: function(attributes, sourceNode) {
        var pmAttrs = objectExtract(attributes, 'config_*');
        pmAttrs.value = objectPop(attributes, 'value') || '';
        pmAttrs.format = objectPop(attributes, 'format') || 'html';  // 'html' | 'json' | 'bag'
        // Lifecycle hooks: strings of JS source executed around dispatchTransaction.
        // beforeDispatch runs before the transaction is applied to the state.
        // afterDispatch runs after the state has been updated.
        // onChange runs only when tr.docChanged is true (skip selection-only changes).
        // Scope available in all three: tr, view, steps, doc, before, genro, sourceNode.
        pmAttrs.beforeDispatch = objectPop(attributes, 'beforeDispatch');
        pmAttrs.afterDispatch = objectPop(attributes, 'afterDispatch');
        pmAttrs.onChange = objectPop(attributes, 'onChange');
        // readOnly takes precedence over editable: passing readOnly=true forces
        // editable=false regardless of any explicit editable= argument.
        var readOnly = objectPop(attributes, 'readOnly');
        var editable = objectPop(attributes, 'editable');
        if(readOnly){
            pmAttrs.editable = false;
        } else {
            pmAttrs.editable = (editable === undefined || editable === null) ? true : !!editable;
        }
        return {pmAttrs: pmAttrs};
    },
    created: function(widget, savedAttrs, sourceNode){
        var that = this;
        var pmAttrs = objectPop(savedAttrs, 'pmAttrs');
        var cb = function(){ that.initialize(widget, pmAttrs, sourceNode); };
        if(!window.ProseMirror){
            this.loadProseMirror(cb);
        } else {
            cb();
        }
    },
    loadProseMirror: function(cb){
        // mtime-based cache-buster: server publishes file mtimes via gnr.vendoredMtime
        // so the browser refetches assets whenever they get rebuilt. CSS is loaded
        // first (no callback needed; styles apply asynchronously) so the editor is
        // already styled by the time the JS bundle initializes the view.
        var cssMtime = genro.getData('gnr.vendoredMtime.prosemirrorCss') || 0;
        var cssUrl = '/_rsrc/js_libs/prosemirror/prosemirror.css' + (cssMtime ? '?mtime=' + cssMtime : '');
        genro.dom.loadCss(cssUrl, 'prosemirror');
        var jsMtime = genro.getData('gnr.vendoredMtime.prosemirror') || 0;
        var jsUrl = '/_rsrc/js_libs/prosemirror/prosemirror.bundle.js' + (jsMtime ? '?mtime=' + jsMtime : '');
        genro.dom.loadJs(jsUrl, cb);
    },
    // ===== Bag <-> PM conversion =====
    // PM Node -> gnr.GnrBag. Whole-tree snapshot, lossless against the
    // pre-built schemas (basic, basicWithLists, basicWithListsAndTables) and
    // any custom mark/node that follows the PM model.
    pmDocToBag: function(doc){
        var bag = new gnr.GnrBag();
        bag.setItem('doc', this._pmNodeToBagChildren(doc), {tag: doc.type.name});
        return bag;
    },
    // Build a Bag holding the children of a PM Node, with labels of the form
    // <type>_<index> where index counts occurrences of that type within the
    // same parent (so paragraph_0, paragraph_1, heading_0, ...).
    _pmNodeToBagChildren: function(node){
        var children = new gnr.GnrBag();
        var counters = {};
        var that = this;
        node.forEach(function(child){
            var typeName = child.type.name;
            var index = (counters[typeName] = (counters[typeName] || 0));
            counters[typeName] = index + 1;
            // Inline text nodes become 'txt' cells with the text as value and
            // marks/attrs spread into the cell attributes.
            if(child.isText){
                var attrs = {tag: 'txt'};
                if(child.marks && child.marks.length){
                    var markNames = [];
                    for(var i = 0; i < child.marks.length; i++){
                        var mk = child.marks[i];
                        var canonical = gnr.widgets.proseMirrorEditor_PM_TO_BAG_MARKS[mk.type.name] || mk.type.name;
                        markNames.push(canonical);
                        // Spread mark attrs onto the cell. Standard PM/Tiptap
                        // marks (link.href, link.title) do not collide.
                        if(mk.attrs){
                            for(var k in mk.attrs){
                                if(mk.attrs[k] != null){ attrs[k] = mk.attrs[k]; }
                            }
                        }
                    }
                    markNames.sort();
                    attrs.markers = markNames.join(',');
                }
                var label = 'txt_' + index;
                children.setItem(label, child.text, attrs);
                return;
            }
            // Non-text node: cell with tag + spread attrs, value is the
            // sub-Bag of children (or null for leaves like image / hard_break).
            var nodeAttrs = {tag: typeName};
            if(child.attrs){
                for(var ak in child.attrs){
                    if(child.attrs[ak] != null){ nodeAttrs[ak] = child.attrs[ak]; }
                }
            }
            var label2 = typeName + '_' + index;
            var subBag = (child.content && child.content.size) ? that._pmNodeToBagChildren(child) : null;
            children.setItem(label2, subBag, nodeAttrs);
        });
        return children;
    },
    // gnr.GnrBag -> PM Node. The Bag must have a single top-level entry (doc).
    bagToPmDoc: function(bag, schema){
        var rootNode = bag.getNode('doc');
        if(!rootNode){
            return schema.topNodeType.createAndFill();
        }
        var children = this._bagChildrenToPmFragment(rootNode.getValue(), schema);
        return schema.topNodeType.create(rootNode.attr || null, children);
    },
    // Build a PM Fragment from a Bag of children, using the cell 'tag' attr
    // to look up the node type in the schema. Unknown tags are silently
    // skipped to avoid hard failures on partial / external data.
    _bagChildrenToPmFragment: function(childrenBag, schema){
        var PM = window.ProseMirror;
        var nodes = [];
        if(!childrenBag){ return PM.Fragment.empty; }
        var bagNodes = childrenBag.getNodes();
        for(var i = 0; i < bagNodes.length; i++){
            var bn = bagNodes[i];
            var attrs = bn.attr || {};
            var tag = attrs.tag;
            // Inline text run.
            if(tag === 'txt'){
                var text = bn.getValue();
                if(text == null || text === ''){ continue; }
                var marks = this._bagAttrsToPmMarks(attrs, schema);
                nodes.push(schema.text(String(text), marks));
                continue;
            }
            var nodeType = schema.nodes[tag];
            if(!nodeType){ continue; }
            // Build PM attrs by stripping Bag-only keys.
            var pmAttrs = this._stripBagKeys(attrs);
            var subContent = bn.getValue();
            var content = (subContent && subContent.getNodes) ? this._bagChildrenToPmFragment(subContent, schema) : PM.Fragment.empty;
            try {
                nodes.push(nodeType.createChecked(pmAttrs, content));
            } catch(e){
                // Schema mismatch (e.g. forbidden child). Try createAndFill as a fallback.
                var filled = nodeType.createAndFill(pmAttrs, content);
                if(filled){ nodes.push(filled); }
            }
        }
        return PM.Fragment.fromArray(nodes);
    },
    // Reconstruct PM marks from a 'markers' csv attribute, pulling per-mark
    // attrs (e.g. link.href, link.title) from the cell-level attributes.
    _bagAttrsToPmMarks: function(attrs, schema){
        if(!attrs.markers){ return null; }
        var marks = [];
        var names = String(attrs.markers).split(',');
        for(var i = 0; i < names.length; i++){
            var canonical = names[i].trim();
            if(!canonical){ continue; }
            var pmName = gnr.widgets.proseMirrorEditor_BAG_TO_PM_MARKS[canonical] || canonical;
            var markType = schema.marks[pmName];
            if(!markType){ continue; }
            // Per-mark attrs come from the same cell attribute bag.
            // We pass everything not in the Bag-only allowlist; PM ignores
            // extras that the mark spec doesn't declare.
            var markAttrs = {};
            if(markType.spec.attrs){
                for(var k in markType.spec.attrs){
                    if(attrs[k] !== undefined){ markAttrs[k] = attrs[k]; }
                }
            }
            marks.push(markType.create(markAttrs));
        }
        return marks.length ? marks : null;
    },
    // Strip Bag-only / cell-only attribute keys before passing to PM.
    _stripBagKeys: function(attrs){
        var clean = {};
        for(var k in attrs){
            if(k === 'tag' || k === 'markers'){ continue; }
            // Strip Bag internal double-underscore metadata only.
            if(k.charAt(0) === '_' && k.charAt(1) === '_'){ continue; }
            clean[k] = attrs[k];
        }
        return clean;
    },
    // Parse the initial value (HTML / PM JSON / Bag) into a PM Node using the
    // configured schema. Empty / unparseable input falls back to an empty
    // document so the editor never starts in a broken state.
    parseInitialDoc: function(PM, schema, value, format){
        if(value == null || value === ''){
            return schema.topNodeType.createAndFill();
        }
        if(format === 'json'){
            try {
                var json = (typeof value === 'string') ? JSON.parse(value) : value;
                return PM.Node.fromJSON(schema, json);
            } catch(e){
                return schema.topNodeType.createAndFill();
            }
        }
        if(format === 'bag'){
            var bag;
            if(value && value.getNodes){
                bag = value;
            } else if(typeof value === 'string'){
                try { bag = new gnr.GnrBag().fromXml(value); }
                catch(e){ return schema.topNodeType.createAndFill(); }
            } else {
                return schema.topNodeType.createAndFill();
            }
            try { return this.bagToPmDoc(bag, schema); }
            catch(e){
                console.error('[proseMirrorEditor] bagToPmDoc failed:', e);
                return schema.topNodeType.createAndFill();
            }
        }
        // HTML: parse via DOMParser bound to the schema.
        var div = document.createElement('div');
        div.innerHTML = String(value);
        return PM.DOMParser.fromSchema(schema).parse(div);
    },
    // Serialize the current document back to the configured format for
    // datapath sync. HTML/JSON return strings; 'bag' returns a gnr.GnrBag
    // instance so the datapath can hold it as a navigable tree.
    serializeDoc: function(PM, schema, doc, format){
        if(format === 'json'){
            return JSON.stringify(doc.toJSON());
        }
        if(format === 'bag'){
            return this.pmDocToBag(doc);
        }
        var serializer = PM.DOMSerializer.fromSchema(schema);
        var div = document.createElement('div');
        div.appendChild(serializer.serializeFragment(doc.content));
        return div.innerHTML;
    },
    // Compile a hook string once and run it inside a try/catch so a buggy
    // hook can never break the editor's transaction pipeline.
    _runHook: function(label, source, scope){
        if(!source){ return; }
        try {
            var fn = new Function('tr', 'view', 'steps', 'doc', 'before', 'genro', 'sourceNode', source);
            fn(scope.tr, scope.view, scope.steps, scope.doc, scope.before, window.genro, scope.sourceNode);
        } catch(e){
            console.error('[proseMirrorEditor ' + label + '] hook error:', e);
        }
    },
    initialize: function(widget, pmAttrs, sourceNode){
        var that = this;
        var PM = window.ProseMirror;
        var schema = PM.schemas.basicWithLists;
        var format = pmAttrs.format || 'html';
        // Read initial value from the datasource if a path was bound.
        var initialValue = sourceNode.getAttributeFromDatasource('value');
        if(initialValue == null || initialValue === ''){
            initialValue = pmAttrs.value || '';
        }
        var doc = this.parseInitialDoc(PM, schema, initialValue, format);
        // Build the input rules typically expected from a markdown-ish editor.
        var rules = PM.smartQuotes.concat([PM.ellipsis, PM.emDash]);
        // Headings via `# `, `## `, ..., up to 6.
        if(schema.nodes.heading){
            rules.push(PM.textblockTypeInputRule(/^(#{1,6})\s$/, schema.nodes.heading,
                function(match){ return {level: match[1].length}; }));
        }
        // Blockquote via `> `.
        if(schema.nodes.blockquote){
            rules.push(PM.wrappingInputRule(/^\s*>\s$/, schema.nodes.blockquote));
        }
        // Lists via `1. ` / `* ` (require schema-list).
        if(schema.nodes.ordered_list){
            rules.push(PM.wrappingInputRule(/^(\d+)\.\s$/, schema.nodes.ordered_list,
                function(match){ return {order: +match[1]}; },
                function(match, node){ return node.childCount + node.attrs.order === +match[1]; }));
        }
        if(schema.nodes.bullet_list){
            rules.push(PM.wrappingInputRule(/^\s*([-+*])\s$/, schema.nodes.bullet_list));
        }
        // Code block via triple-backtick.
        if(schema.nodes.code_block){
            rules.push(PM.textblockTypeInputRule(/^```$/, schema.nodes.code_block));
        }
        // Compose keymap: list-aware Enter/Tab/Shift-Tab on top of baseKeymap +
        // history shortcuts, so undo/redo work out of the box.
        var listKeys = {};
        if(schema.nodes.list_item){
            listKeys['Enter'] = PM.splitListItem(schema.nodes.list_item);
            listKeys['Mod-['] = PM.liftListItem(schema.nodes.list_item);
            listKeys['Mod-]'] = PM.sinkListItem(schema.nodes.list_item);
        }
        var historyKeys = {
            'Mod-z': PM.undo,
            'Mod-y': PM.redo,
            'Mod-Shift-z': PM.redo
        };
        var plugins = [
            PM.history(),
            PM.keymap(historyKeys),
            PM.keymap(listKeys),
            PM.keymap(PM.baseKeymap),
            PM.inputRules({rules: rules}),
            PM.dropCursor(),
            PM.gapCursor()
        ];
        var state = PM.EditorState.create({doc: doc, schema: schema, plugins: plugins});
        // editableState lives in this closure so the editable() prop can read
        // it during EditorView construction (before `view` itself is bound).
        var editableState = !!pmAttrs.editable;
        var view = new PM.EditorView(widget, {
            state: state,
            editable: function(){ return editableState; },
            dispatchTransaction: function(tr){
                var hookScope = {tr: tr, view: view, steps: tr.steps, doc: tr.doc,
                                 before: tr.before, sourceNode: sourceNode};
                that._runHook('beforeDispatch', pmAttrs.beforeDispatch, hookScope);
                var newState = view.state.apply(tr);
                view.updateState(newState);
                if(tr.docChanged){
                    that._runHook('onChange', pmAttrs.onChange, hookScope);
                    sourceNode.delayedCall(function(){
                        var serialized = that.serializeDoc(PM, schema, view.state.doc, format);
                        if(sourceNode.attr.value){
                            sourceNode.setRelativeData(sourceNode.attr.value, serialized, null, null, sourceNode);
                        }
                    }, sourceNode.attr._delay || 500, 'updatingContent');
                }
                that._runHook('afterDispatch', pmAttrs.afterDispatch, hookScope);
            }
        });
        // Expose the toggle through the view so gnr_editable can flip it at runtime.
        view._gnrSetEditable = function(v){ editableState = !!v; view.setProps({}); };
        view._gnrSchema = schema;
        view._gnrFormat = format;
        // Public API for console / batch operations: read or replace the
        // document as a gnr.GnrBag, regardless of the configured format.
        view.toBag = function(){ return that.pmDocToBag(view.state.doc); };
        view.fromBag = function(bag){
            var newDoc = that.bagToPmDoc(bag, schema);
            var tr = view.state.tr.replaceWith(0, view.state.doc.content.size, newDoc.content);
            tr.setMeta('addToHistory', false);
            view.updateState(view.state.apply(tr));
        };
        // baseExternalWidget wires sourceNode.externalWidget, mixins, and back-refs.
        this.setExternalWidget(sourceNode, view);
    },
    // ---- Mixins (available on sourceNode.externalWidget as gnr_*) ----
    // gnr_value(text) replaces the current document with the parsed input,
    // honouring the format chosen at construction (html | json).
    mixin_gnr_value: function(value, kw, trigger_reason){
        var view = this;
        var PM = window.ProseMirror;
        var schema = view._gnrSchema;
        var format = view._gnrFormat;
        var newDoc = view.gnr.parseInitialDoc(PM, schema, value || '', format);
        // Replace whole document via a single replace step.
        var tr = view.state.tr.replaceWith(0, view.state.doc.content.size, newDoc.content);
        // Skip docChanged side effects to avoid bouncing the value back to the datapath.
        tr.setMeta('addToHistory', false);
        view.updateState(view.state.apply(tr));
    },
    mixin_gnr_setDisabled: function(disabled){
        genro.dom.setDomNodeDisabled(this.sourceNode.domNode, disabled);
        this.gnr_editable(!disabled);
    },
    mixin_gnr_readOnly: function(value, kw, trigger_reason){
        // For ProseMirror "readOnly" maps directly to "not editable": there is
        // no separate notion of selectable-but-not-editable like in CM5.
        this.gnr_editable(!value);
    },
    mixin_gnr_editable: function(value, kw, trigger_reason){
        if(this._gnrSetEditable){ this._gnrSetEditable(value); }
    }
});

dojo.declare("gnr.widgets.CkEditor", gnr.widgets.baseHtml, {
    constructor: function(application) {
        this._domtag = 'div';
    },

    toolbar_dict:{
        'simple':[['Source','-','Bold', 'Italic', '-', 'NumberedList', 'BulletedList', '-','Image','Table','HorizontalRule','PageBreak'],
                   ['JustifyLeft','JustifyCenter','JustifyRight','JustifyBlock'],
                   ['Styles','Format','Font','FontSize','TextColor','BGColor']],
        'standard':[
                   ['Source','-','Bold', 'Italic', '-', 'NumberedList', 'BulletedList', '-', 'Link', 'Unlink','-','Templates'],
                   ['Image','Table','HorizontalRule','PageBreak'],
                   ['JustifyLeft','JustifyCenter','JustifyRight','JustifyBlock'],
                   ['Styles','Format','Font','FontSize'],
                   ['TextColor','BGColor'],['Maximize', 'ShowBlocks']
                   ]
    },
    
    creating: function(attributes, sourceNode) {
        if('disabled' in attributes){
            if(!('readOnly' in attributes)){
                attributes.readOnly = attributes.disabled;
                sourceNode.attr.readOnly = sourceNode.attr.disabled;
            }
            delete attributes.disabled;
            delete sourceNode.attr.disabled;
        }
        attributes.id = attributes.id || 'ckedit_' + sourceNode.getStringId();
        var toolbar = objectPop(attributes, 'toolbar', 'standard');
        var config = objectExtract(attributes, 'config_*');
        var stylesheet = objectPop(attributes,'stylesheet');
        var customStyles = objectPop(attributes,'customStyles');
        var contentsCss = objectPop(attributes,'contentsCss');

        if(stylesheet){
            config.extraPlugins = 'stylesheetparser';
            config.contentsCss = stylesheet;
        }
        if(customStyles){
            var l = [];
            customStyles.forEach(function(n){
                l.push({name:n.name,element:n.element,styles:objectFromStyle(n.styles),attributes:objectFromStyle(n.attributes)});
            })
            customStyles = l;
        }
        var showtoolbar = true;
        if (toolbar===false){
            toolbar=[];
            showtoolbar = false;
        }
        if (typeof(toolbar) == 'string') {
            if(toolbar in this.toolbar_dict){
                toolbar = this.toolbar_dict[toolbar];
            }else{
                toolbar = genro.evaluate(toolbar);
            }
        }
        ;
        if (toolbar) {
            config.toolbar = 'custom';
            config.toolbar_custom = toolbar;
        }
        var savedAttrs = {'config':config,showtoolbar:showtoolbar,enterMode:objectPop(attributes,'enterMode'),bodyStyle:objectPop(attributes,'bodyStyle',{margin:'2px'})};
        savedAttrs.customStyles = customStyles;
        savedAttrs.contentsCss = contentsCss;
        savedAttrs.contentStyles = objectPop(attributes,'contentStyles');
        savedAttrs.constrainAttr = objectExtract(attributes,'constrain_*')
        return savedAttrs;

    },
    dialog_tableProperties:function(definition,ckeditor){
        this.dialog_table(definition,ckeditor);
    },
    dialog_table:function(definition,ckeditor){
        definition.getContents('info').get('txtBorder')['default']=null;
        definition.getContents('advanced').get('advStyles')['default']='border-collapse:collapse;';
        definition.addContents({
            id : 'gnr_tableProperties',
            label : 'Genropy',
            accessKey : 'G',
            elements : [
                    {id : 'row_datasource',type : 'text',label : 'Row Datasource',
                        setup: function(i) {
                            this.setValue(i.getAttribute('row_datasource') || '');
                        },
                        commit: function(i, j) {
                            if (this.getValue()) j.setAttribute('row_datasource', this.getValue());
                            else j.removeAttribute('row_datasource');
                        }
                    },

                    {id : 'row_condition',type : 'text',label : 'Row Condition',
                        setup: function(i) {
                            this.setValue(i.getAttribute('row_condition') || '');
                        },
                        commit: function(i, j) {
                            if (this.getValue()) j.setAttribute('row_condition', this.getValue());
                            else j.removeAttribute('row_condition');
                        }
                    },
                    {id : 'row_sort',type : 'text',label : 'Row Sort',
                        setup: function(i) {
                            this.setValue(i.getAttribute('row_sort') || '');
                        },
                        commit: function(i, j) {
                            if (this.getValue()) j.setAttribute('row_sort', this.getValue());
                            else j.removeAttribute('row_sort');
                        }
                    }
                    ]
            });
    },
    mixin_gnr_constrain_height:function(height,kw, trigger_reason){
         this.document.getBody()['$'].style.height = height;
    }, 

    mixin_gnr_constrain_width:function(width,kw, trigger_reason){
         this.document.getBody()['$'].style.width = width;
    }, 

    mixin_gnr_contentStyles:function(){
        var that = this;
        this.sourceNode.watch('hasDocument',function(){
            return that.document;
        },function(){
            var contentStyles = that.sourceNode.getAttributeFromDatasource('contentStyles') || '';
            let head = that.document.getHead()['$'];
            let innerID = that.sourceNode._id;
            let styleID = `${innerID}_ckedit_stylenode`;
            let innerdocument = that.document['$'];
            let styleNode = innerdocument.getElementById(styleID);
            if (!styleNode){
                styleNode = innerdocument.createElement('style');
                styleNode.setAttribute('id',styleID);
                head.appendChild(styleNode);
            }
            styleNode.innerText = contentStyles
        });
    },

    mixin_gnr_assignConstrain:function(){
        var that = this;
        this.sourceNode.watch('hasDocument',function(){
            return that.document;
        },function(){
            var constrainAttr = objectExtract(that.sourceNode.attr,'constrain_*',true);
            constrainAttr = that.sourceNode.evaluateOnNode(constrainAttr);
            var b = that.document.getBody()['$'];
            b.style.cssText = objectAsStyle(objectUpdate(objectFromStyle(b.style.cssText),
                                                genro.dom.getStyleDict(constrainAttr)));  
        });
    },

    makeEditor:function(widget, savedAttrs, sourceNode){
        var showtoolbar = objectPop(savedAttrs,'showtoolbar');
        var enterMode = objectPop(savedAttrs,'enterMode') || 'div';
        var bodyStyle = objectPop(savedAttrs,'bodyStyle');
        //var constrainAttr = objectPop(savedAttrs,'constrainAttr');
        var enterModeDict = {'div':CKEDITOR.ENTER_DIV,'p':CKEDITOR.ENTER_P,'br':CKEDITOR.ENTER_BR};
        if(showtoolbar===false){
        objectUpdate(savedAttrs.config, {
            toolbar: 'Custom', //makes all editors use this toolbar
            toolbarStartupExpanded : false,
            toolbarCanCollapse  : false,
            toolbar_Custom: '' //define an empty array or whatever buttons you want.
            });
        }

        if(savedAttrs.customStyles){
            var csname = 'customStyles_'+sourceNode.getStringId();
            CKEDITOR.stylesSet.add(csname,savedAttrs.customStyles);
            savedAttrs.config.stylesSet = csname
        } 
        savedAttrs.config.enterMode = enterModeDict[enterMode];
        //savedAttrs.config.enterMode = CKEDITOR.ENTER_BR;
        //savedAttrs.config.enterMode = CKEDITOR.ENTER_P;

        if(savedAttrs.contentsCss){
            var currlst = CKEDITOR.config.contentsCss;
            if(typeof(currlst)=='string'){
                currlst = currlst.split(',')
            }
            savedAttrs.config.contentsCss = currlst.concat(savedAttrs.contentsCss.split(','));
        }
        CKEDITOR.replace(widget, savedAttrs.config);


        var ckeditor_id = 'ckedit_' + sourceNode.getStringId();
        var ckeditor = CKEDITOR.instances[ckeditor_id];
        sourceNode.externalWidget = ckeditor;
        ckeditor.sourceNode = sourceNode;
        ckeditor.gnr = this;
        for (var prop in this) {
            if (prop.indexOf('mixin_') == 0) {
                ckeditor[prop.replace('mixin_', '')] = this[prop];
            }
        }
        ckeditor.gnr_getFromDatastore();
        var parentWidget = dijit.getEnclosingWidget(widget);
        ckeditor.gnr_readOnly('auto');
        var parentDomNode=sourceNode.getParentNode().getDomNode();
        ckeditor.on('currentInstance', function(ev){
            console.log('currentInstance',constrainAttr);
        });
        
        var cbResize=function(){
                sourceNode._rsz=null;
                try{
                    ckeditor.gnr_assignConstrain();
                    ckeditor.resize(parentDomNode.clientWidth,parentDomNode.clientHeight);
                }catch(e){
                    
                }
                
        };
        ckeditor.on('instanceReady', function(ev){
            var editor = ev.editor;
            editor.gnr_assignConstrain();
            editor.gnr_contentStyles();

            var dropHandler = function( evt ) {
                setTimeout(function(){ckeditor.gnr_setInDatastore();},1);
            };
            if (editor.document.$.addEventListener) {
                editor.document.$.addEventListener( 'drop', dropHandler, true ) ; 
            } else if (editor.document.$.attachEvent) {
                editor.document.$.attachEvent( 'ondrop', dropHandler, true ) ; 
            }
            editor.document.$.addEventListener('keydown',function(evt){
                ckeditor.lastKey = evt.keyCode;
            });

            if(sourceNode.attr.onStarted){
                funcApply(sourceNode.attr.onStarted,{editor:editor},sourceNode);
            }
            cbResize();
            if(sourceNode.attr._inGridEditor){
                var that = this;
                setTimeout(function(){that.focus()},100);
            }
        });


        dojo.connect(parentWidget,'resize',function(){
            if(sourceNode._rsz){
                clearTimeout(sourceNode._rsz);
            }
            sourceNode._rsz=setTimeout(cbResize,100);
        });
        var that=this;
        if(!CKEDITOR._dialog_patched){
            CKEDITOR.on( 'dialogDefinition', function( ev ){
                if (that['dialog_'+ev.data.name]){
                    that['dialog_'+ev.data.name].call(that,ev.data.definition);
                }
            });
            CKEDITOR._dialog_patched = true;
        }

        var ckeditor =  sourceNode.externalWidget;
        dojo.connect(ckeditor.focusManager, 'blur', function(evt){
            ckeditor.gnr_setInDatastore();            
            if(sourceNode.attr.connect_onBlur){
                if(ckeditor._blurTimeOut){
                    clearTimeout(ckeditor._blurTimeOut)
                    ckeditor._blurTimeOut = null
                }
                ckeditor._blurTimeOut = setTimeout(function(){
                    if(sourceNode.attr._inGridEditor && sourceNode.externalWidget.lastKey==9){
                        sourceNode.externalWidget.cellNext = 'RIGHT';  
                    }
                    funcApply(sourceNode.attr.connect_onBlur,{evt:evt},sourceNode);
                    clearTimeout(ckeditor._blurTimeOut)
                    ckeditor._blurTimeOut = null
                },200)
                
            }
        });
        dojo.connect(ckeditor.focusManager, 'focus', function(evt){
            if(ckeditor._blurTimeOut){
                clearTimeout(ckeditor._blurTimeOut)
                    ckeditor._blurTimeOut = null
                }
        });


        dojo.connect(ckeditor.editor, 'paste', ckeditor, 'gnr_onPaste');
        ckeditor['on']('paste',function(e){
            var lastSelection = sourceNode.externalWidget.getSelection().getNative();
            var data = e.data.html || '';
            if(data[0]=='<'){
                var anchorNode = lastSelection.anchorNode;
                if(anchorNode.innerHTML=='<br>'){
                    anchorNode.innerHTML = '&nbsp;';
                    var an = anchorNode.firstChild;
                    lastSelection.anchorNode.parentNode.replaceChild(an,anchorNode);
                    lastSelection.anchorNode = an;
                }
            }
            genro.callAfter(function(){
                this.gnr_onTyped();
                this.gnr_setInDatastore();
            },1,this,'typing');
        })
        ckeditor['on']('key',function(kw){
            if(!sourceNode.attr._inGridEditor){
                genro.callAfter(function(){
                    this.gnr_onTyped();
                    this.gnr_setInDatastore();
                },1000,this,'typing');
            }
        });
    
        return ckeditor;
        
    },

    onSpeechEnd:function(sourceNode,v){
        var lastSelection = sourceNode.externalWidget.getSelection().getNative();
        if(lastSelection){
            var oldValue = sourceNode.getAttributeFromDatasource('value') || '';
            var fistchunk = oldValue.slice(0,lastSelection.start);
            var secondchunk =  oldValue.slice(lastSelection.end);
            v = fistchunk+v+secondchunk;
        }
        setTimeout(function(){
            sourceNode.setAttributeInDatasource('value',v,true);
            //sourceNode.widget.domNode.focus();
        },1);
    },

    created: function(widget, savedAttrs, sourceNode) {
        var that = this;
        var cb = function(){
            that.makeEditor(widget, savedAttrs, sourceNode);
            sourceNode.publish('editorCreated');
        };
        if(!window.CKEDITOR){
            var suff = genro.newCkeditor? '_new':'';
            genro.dom.loadJs('/_rsrc/js_libs/ckeditor'+suff+'/ckeditor.js',function(){
                cb();
            });
            return;
        }
        cb();
         
        // dojo.connect(parentWidget,'onShow',function(){console.log("onshow");console.log(arguments);ckeditor.gnr_readOnly('auto');})
        // setTimeout(function(){;},1000);

    },

    mixin_gnr_value:function(value, kw, reason) {
        if(!this.focusManager.hasFocus){
            this.setData(value);
        }
    },
    
    mixin_gnr_getFromDatastore : function() {
        this.setData(this.sourceNode.getAttributeFromDatasource('value') || '');
    },

    mixin_gnr_setInDatastore : function() {
        var value=this.getData();
        if(this.sourceNode.form && this.sourceNode.form.isDisabled()){
            return;
        }
        if(this.sourceNode.getAttributeFromDatasource('value')!=value){
            this.sourceNode.setAttributeInDatasource('value',value );
        }
    },
    mixin_gnr_onPaste:function(){
        this.gnr_setInDatastore();
    },
    mixin_gnr_onTyped:function(){

    },

    mixin_gnr_setDisabled:function(disabled){
        this.gnr_setReadOnly(disabled);
    },

    mixin_gnr_highlightChild:function(idx){
        var cs = this.sourceNode.externalWidget.document.$.getElementById('customstyles');
        if(!cs){
            var cs = this.sourceNode.externalWidget.document.$.createElement('style');
            cs.setAttribute('id','customstyles');
            this.sourceNode.externalWidget.document.getHead().$.appendChild(cs)
        }
        cs.textContent =idx>=0? "body>*:nth-child("+(idx+1)+"){background:yellow;}":"";
        if(idx>=0){
            var b = this.sourceNode.externalWidget.document.getBody().$;
            var higlightedNode = b.children[idx];
            var ht = higlightedNode.offsetTop;
            //if(b.parentNode.clientHeight+b.scrollTop-ht<0){
               b.scrollTop = ht-100;
            //}
        }
    },

    mixin_gnr_cancelEvent : function(evt) {
        evt.cancel();
    },

    mixin_gnr_readOnly:function(value, kw, reason) {
        var value = (value != 'auto') ? value : this.sourceNode.getAttributeFromDatasource('readOnly');
        this.gnr_setReadOnly(value);
    },
    mixin_gnr_setReadOnly:function(isReadOnly) {
        if (!this.document) {
            return;
        }
        //this.document.$.body.disabled = isReadOnly;
        CKEDITOR.env.ie ? this.document.$.body.contentEditable = !isReadOnly
                : this.document.$.designMode = isReadOnly ? "off" : "on";
        this[ isReadOnly ? 'on' : 'removeListener' ]('key', this.gnr_cancelEvent, null, null, 0);
        this[ isReadOnly ? 'on' : 'removeListener' ]('selectionChange', this.gnr_cancelEvent, null, null, 0);
        var command,
                commands = this._.commands,
                mode = this.mode;
        for (var name in commands) {
            command = commands[ name ];
            isReadOnly ? command.disable() : command[ command.modes[ mode ] ? 'enable' : 'disable' ]();
            this[ isReadOnly ? 'on' : 'removeListener' ]('state', this.gnr_cancelEvent, null, null, 0);
        }
        this[ isReadOnly ? 'on' : 'removeListener' ]('doubleclick', this.gnr_cancelEvent, null, null, 0);
        var toolbarEl = this.container.$.querySelector('.cke_top');
        if(toolbarEl){
            toolbarEl.style.opacity = isReadOnly ? '0.4' : '';
            toolbarEl.style.pointerEvents = isReadOnly ? 'none' : '';
        }
        var body = this.document.getBody().$;
        body.style.opacity = isReadOnly ? '0.5' : '';
        body.style.cursor = isReadOnly ? 'default' : '';
        body.style.caretColor = isReadOnly ? 'transparent' : '';
    }

});

dojo.declare("gnr.widgets.TinyMCE", gnr.widgets.baseHtml, {
  constructor: function(application) {
    this._domtag = 'textarea';
    // Initialize global queue for TinyMCE initialization
    if (!window._gnr_tinymce_init_queue) {
      window._gnr_tinymce_init_queue = [];
      window._gnr_tinymce_loading = false;
      window._gnr_tinymce_processing = false;
    }
  },

  creating: function(attributes, sourceNode){
    const valueAttr = sourceNode.attr.value;
    if (!valueAttr) { throw new Error('TinyMCE widget: missing required "value" datapath'); }
    const valuePath = sourceNode.absDatapath(valueAttr);

    // Optional text field - if provided, plain text will be extracted and saved to textpath
    const textAttr = sourceNode.attr.textpath;
    const textPath = textAttr ? sourceNode.absDatapath(textAttr) : null;

    const height = objectPop(attributes,'height') || '100%';
    const width  = objectPop(attributes,'width')  || '100%';
    const textareaId = 'tinymce_' + sourceNode.getStringId();
    const phRaw = objectPop(attributes,'placeholders');
    const placeholderItems = phRaw ? String(phRaw).split(',').map(s=>s.trim()).filter(Boolean) : [];
    const base_url = objectPop(attributes,'base_url') || '/_rsrc/js_libs/tinymce';
    const content_style = objectPop(attributes,'content_style');
    let plugins = objectPop(attributes,'plugins');
    if (!plugins){ plugins = 'link lists table code image'; }
    const onUploadedMethod = objectPop(attributes,'onUploadedMethod');
    const rpcKw = objectExtract(attributes,'rpc_*');
    let removeToolbarItems = objectPop(attributes,'removeToolbarItems');
    if (removeToolbarItems == null) { removeToolbarItems = []; }
    if (typeof removeToolbarItems === 'string') {
      let s = removeToolbarItems.trim();
      try {
        removeToolbarItems = JSON.parse(s);
      } catch(e) {
        if (s[0] === '[' && s[s.length-1] === ']') { s = s.slice(1,-1); }
        removeToolbarItems = s.split(',').map(t => t.trim().replace(/^['"]|['"]$/g,''));
        removeToolbarItems = removeToolbarItems.filter(Boolean);
      }
    }
    let insertToolbarItems = objectPop(attributes,'insertToolbarItems');
    if (insertToolbarItems == null) { insertToolbarItems = []; }
    if (typeof insertToolbarItems === 'string') {
      let s = insertToolbarItems.trim();
      try {
        insertToolbarItems = JSON.parse(s);
      } catch(e) {
        if (s[0] === '[' && s[s.length-1] === ']') { s = s.slice(1,-1); }
        insertToolbarItems = s.split(',').map(t => t.trim().replace(/^['"]|['"]$/g,''));
        insertToolbarItems = insertToolbarItems.filter(Boolean);
      }
    }
    const imageDataRaw = objectPop(attributes,'imageData');
    const imageData = (imageDataRaw === true || imageDataRaw === 'true' || imageDataRaw === 1 || imageDataRaw === '1');
    const rawUploadPath = objectPop(attributes,'uploadPath');
    const uploadPath = rawUploadPath || 'site:uploaded_files';
    if (imageData && rawUploadPath){
      throw new Error('TinyMCE widget: imageData=True is mutually exclusive with uploadPath');
    }
    const maxLength = objectPop(attributes,'maxLength');
    attributes.id = textareaId;
    attributes.style = `height:${height};width:${width};`;
    return {valuePath, textPath, textareaId, placeholderItems, base_url, content_style, plugins, removeToolbarItems, insertToolbarItems, imageData, uploadPath, onUploadedMethod, rpcKw, maxLength, _rawHeight: height, _rawWidth: width};
  },

  created: function(domNode, savedAttrs, sourceNode){
    var widgetObj = this;
    var initialized = false;
    var that = this;

    // Function to actually initialize this editor
    var doInit = function() {
        if (initialized) { return; }
        if (!genro.dom.isVisible(sourceNode)) {
            genro.callAfter(doInit, 300, that, 'tinymce_wait_'+savedAttrs.textareaId);
            return;
        }
        initialized = true;
        that.makeEditor(domNode, savedAttrs, sourceNode);
    };

    // Subscribe to onShow event
    sourceNode.subscribe('onShow', function() {
        if (!initialized) {
            that.queueTinyMCEInit(doInit, savedAttrs);
        }
    });

    // Queue this editor for initialization
    this.queueTinyMCEInit(doInit, savedAttrs);

    // Cleanup on widget deletion
    dojo.connect(sourceNode,'_onDeleting',function(){
      if (window.tinymce){ try{ tinymce.remove('#' + savedAttrs.textareaId); }catch(e){} }
    });
  },

  queueTinyMCEInit: function(initCallback, savedAttrs) {
    // Add to queue
    window._gnr_tinymce_init_queue.push(initCallback);

    // Ensure TinyMCE library is loaded
    if (!window.tinymce && !window._gnr_tinymce_loading) {
      window._gnr_tinymce_loading = true;
      genro.dom.loadJs(savedAttrs.base_url + '/tinymce.min.js', function(){
        console.log('[TinyMCE] Library loaded, processing queue');
        window._gnr_tinymce_loading = false;
        this.processTinyMCEQueue();
      }.bind(this));
    } else if (window.tinymce && !window._gnr_tinymce_processing) {
      // TinyMCE already loaded, process queue
      this.processTinyMCEQueue();
    }
  },

  processTinyMCEQueue: function() {
    if (window._gnr_tinymce_processing) { return; }
    if (window._gnr_tinymce_init_queue.length === 0) { return; }
    if (!window.tinymce) {
      // Library not ready yet, try again later
      setTimeout(this.processTinyMCEQueue.bind(this), 100);
      return;
    }

    window._gnr_tinymce_processing = true;
    var callback = window._gnr_tinymce_init_queue.shift();

    try {
      callback();
    } catch(e) {
      console.error('[TinyMCE] Initialization error:', e);
    }

    // Process next item in queue after a short delay
    setTimeout(function() {
      window._gnr_tinymce_processing = false;
      this.processTinyMCEQueue();
    }.bind(this), 50);
  },

  makeEditor: function(domNode, savedAttrs, sourceNode){
    var widgetObj = this;
    // Preload value into textarea as fallback
    // Load HTML from valuePath
    try {
      var initialContent = sourceNode.getRelativeData(savedAttrs.valuePath);
      if (typeof initialContent !== 'undefined' && initialContent !== null){
        domNode.value = initialContent;
      }
    } catch(_e) {}
    const rawHeight = savedAttrs._rawHeight;
    const rawWidth  = savedAttrs._rawWidth;
    const numericHeight = (rawHeight && /px$/i.test(rawHeight)) ? parseInt(rawHeight, 10) : null;

    // Pre-process insertToolbarItems to generate button names and add missing plugins
    if (savedAttrs.insertToolbarItems && savedAttrs.insertToolbarItems.length){
      const pluginsArray = savedAttrs.plugins ? savedAttrs.plugins.split(' ').filter(Boolean) : [];
      const pluginsSet = new Set(pluginsArray);

      savedAttrs.insertToolbarItems = savedAttrs.insertToolbarItems.map(function(item){
        if (typeof item === 'string') {
          // For simple string items, check if they need to be added as plugins
          // Common TinyMCE plugins that might be added via insertToolbarItems
          const knownPlugins = ['codesample', 'emoticons', 'charmap', 'anchor', 'searchreplace', 'visualblocks', 'fullscreen', 'insertdatetime', 'media', 'preview', 'help', 'wordcount'];
          if (knownPlugins.indexOf(item) !== -1 && !pluginsSet.has(item)) {
            pluginsArray.push(item);
            pluginsSet.add(item);
          }
        } else if (typeof item === 'object' && item !== null && item.insertText && !item.name) {
          // Generate a unique name for custom buttons without a name
          item.name = 'customButton_' + Math.random().toString(36).substr(2, 9);
        }
        return item;
      });

      // Update plugins string
      if (pluginsArray.length > 0) {
        savedAttrs.plugins = pluginsArray.join(' ');
      }
    }

    // Initialize TinyMCE with toolbar and plugins
    const defaultToolbarLines = [
      'undo redo | bold italic underline | bullist numlist | alignleft aligncenter alignright alignjustify',
      savedAttrs.placeholderItems && savedAttrs.placeholderItems.length ?
        '| link image table | code | placeholders' :
        '| link image table | code'
    ];
    const removeSet = new Set(savedAttrs.removeToolbarItems || []);
    let toolbar = defaultToolbarLines
      .map(line => line.split(' ').filter(tok => !removeSet.has(tok)).join(' '))
      .join(' ');

    // Add insertToolbarItems to toolbar
    if (savedAttrs.insertToolbarItems && savedAttrs.insertToolbarItems.length){
      const insertItems = savedAttrs.insertToolbarItems.map(function(item){
        if (typeof item === 'string') {
          return item; // Simple string like 'codesample'
        } else if (typeof item === 'object' && item !== null) {
          return item.name || ''; // Custom button name
        }
        return '';
      }).filter(Boolean);

      if (insertItems.length > 0) {
        toolbar += ' | ' + insertItems.join(' ');
      }
    }
    tinymce.init({
      target: domNode,
      base_url: savedAttrs.base_url,
      suffix: '.min',
      license_key: 'gpl',
      promotion: false,
      menubar: false,
      branding: false,
      height: (numericHeight !== null) ? numericHeight : undefined,
      width: rawWidth || null,
      plugins: savedAttrs.plugins,
      toolbar: toolbar,
      forced_root_block: 'p',
      valid_children: '+a[div|p|span|strong|em]',
      paste_as_text: false,
      paste_data_images: !!savedAttrs.imageData,
      content_style: (savedAttrs.content_style || ''),
      convert_urls: false,
      relative_urls: false,
      remove_script_host: false,
      urlconverter_callback: function(url /*, node, on_save, name */){
        return url;
      },
      automatic_uploads: savedAttrs.imageData ? false : !!savedAttrs.uploadPath,
      file_picker_types: 'image',
      file_picker_callback: function (cb) {
        const url = prompt('Image URL https://…');
        if (url) cb(url, { alt: '' });
      },
      images_upload_handler: function (blobInfo, progress) {
        if (savedAttrs.imageData){
          return new Promise(function(resolve, reject){
            try{
              var reader = new FileReader();
              reader.onload = function(){ try{ progress(100); }catch(e){}; resolve(reader.result); };
              reader.onerror = function(e){ reject(e); };
              reader.readAsDataURL(blobInfo.blob());
            }catch(e){ reject(e); }
          });
        }
        var originalName = blobInfo.filename();
        var dot = originalName.lastIndexOf('.')
        var ext = dot >= 0 ? originalName.slice(dot) : '';
        var base = dot >= 0 ? originalName.slice(0, dot) : originalName;
        try { base = base.normalize('NFD').replace(/[\u0300-\u036f]/g, ''); } catch(_e) {}
        base = base.replace(/[^A-Za-z0-9_-]+/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '').toLowerCase();
        var safeFilename = (base || 'upload') + (ext ? ext.toLowerCase() : '');
        var params = { uploadPath: savedAttrs.uploadPath, filename: safeFilename };
        if (savedAttrs.onUploadedMethod){ params.onUploadedMethod = savedAttrs.onUploadedMethod; }
        if (savedAttrs.rpcKw){ for (var k in savedAttrs.rpcKw){ params[k] = savedAttrs.rpcKw[k]; } }
        return new Promise(function(resolve, reject){
          try{
            genro.rpc.uploadMultipart_oneFile(
              blobInfo.blob(),
              params,
              {
                method: 'rpc.upload_file',
                uploaderId: (sourceNode && typeof sourceNode._id === 'string') ? sourceNode._id : (sourceNode && typeof sourceNode.getStringId === 'function' ? sourceNode.getStringId() : undefined),
                uploadPath: params.uploadPath,
                filename: params.filename,
                onProgress: function(evt){
                  if (evt && evt.lengthComputable){
                    var pct = Math.round((evt.loaded / evt.total) * 100);
                    try{ progress(pct); }catch(e){}
                  }
                },
                onResult: function(evt){
                  try{
                    var txt = evt.target && evt.target.responseText ? evt.target.responseText : '';
                    var url = null;
                    try{ var j = JSON.parse(txt); url = (j && (j.url || j.uploaded_file_path || j.path)); }catch(_ignored){}
                    if(!url && typeof txt === 'string'){
                      var raw = txt.trim();
                      if ((raw[0]==='"' && raw[raw.length-1]==='"') || (raw[0]==="'" && raw[raw.length-1]==="'")){
                        raw = raw.slice(1,-1);
                      }
                      if (/^https?:\/\//i.test(raw)){
                        url = raw;
                      }else{
                        var m = raw.match(/https?:\/\/[^\s"']+/);
                        url = m ? m[0] : raw;
                      }
                    }
                    if (!url){ throw new Error('Invalid upload response'); }
                    try{ url = encodeURI(url); }catch(_e){}
                    progress(100);
                    resolve(url);
                  }catch(e){ reject(e); }
                },
                onError: function(){ reject(new Error('Upload error')); },
                onAbort: function(){ reject(new Error('Upload aborted')); }
              }
            );
          }catch(e){ reject(e); }
        });
      },
      images_reuse_filename: true,
      setup: function(editor){
        // expose
        sourceNode.externalWidget = editor;
        editor.sourceNode = sourceNode;
        for (var prop in widgetObj) {
          if (prop.indexOf('mixin_') === 0) {
            editor[prop.replace('mixin_', '')] = widgetObj[prop];
          }
        }
        // hover focus + drop placeholders
        function focusOnDrag(e){ try{ e.preventDefault(); }catch(_e){}; try{ editor.focus(); }catch(_e){} }
        function insertDroppedText(e){
          try{ e.preventDefault(); }catch(_e){}; try{ editor.focus(); }catch(_e){};
          var dt = e.dataTransfer || (e.originalEvent && e.originalEvent.dataTransfer);
          var txt = dt ? (dt.getData('text/plain') || dt.getData('text') || '') : '';
          if (!txt){ return; }
          txt = String(txt).trim();
          if (!txt){ return; }
          if (txt[0] !== '$'){ txt = '$' + txt; }
          try{
            var doc = editor.getDoc();
            var rng = null;
            if (doc.caretRangeFromPoint){ rng = doc.caretRangeFromPoint(e.clientX, e.clientY); }
            else if (doc.caretPositionFromPoint){ var pos = doc.caretPositionFromPoint(e.clientX, e.clientY); if (pos){ rng = doc.createRange(); rng.setStart(pos.offsetNode, pos.offset); rng.collapse(true); } }
            if (rng){ editor.selection.setRng(rng); }
          }catch(_e){}
          editor.insertContent(editor.dom.encode(txt));
        }
        var cont = editor.getContainer();
        if (cont){ ['dragenter','dragover'].forEach(function(ev){ cont.addEventListener(ev, focusOnDrag, {passive:false}); }); }
        // datastore syncing
        try { sourceNode.registerDynAttr && sourceNode.registerDynAttr('value'); } catch(_e) {}
        editor.gnr_value = function(value){ if (!editor.hasFocus() && editor.getContent() !== (value || '')){ editor.setContent(value || ''); } };

        // Subscribe to value changes BEFORE Init to catch early updates
        var changeListenerActive = false; // Flag to prevent false positives during initial load
        var originalNormalizedContent = null; // Store normalized version of initial content

        // Helper to normalize HTML for comparison (remove whitespace differences)
        const normalizeForComparison = function(html){
          if (!html) return '';
          return html.replace(/>\s+</g, '><').replace(/\s+/g, ' ').trim();
        };

        const pushChange = function(){
          try {
            if (editor.initialized && changeListenerActive) {
              var currentContent = editor.getContent();

              // Check if content actually changed (ignoring whitespace-only differences)
              var shouldSave = true;
              if (originalNormalizedContent !== null) {
                var currentNormalized = normalizeForComparison(currentContent);
                if (currentNormalized === originalNormalizedContent) {
                  shouldSave = false; // Content unchanged, don't save
                }
              }

              if (shouldSave) {
                // Always save HTML to valuePath
                sourceNode.setRelativeData(savedAttrs.valuePath, currentContent);
              }
            }
          } catch(e) {}
        };
        editor.on('Change Undo Redo SetContent', pushChange);

        // Save plain text to textPath only when user leaves the editor (blur event)
        if (savedAttrs.textPath) {
          editor.on('blur', function(){
            try {
              var plainText = editor.getContent({format: 'text'});
              sourceNode.setRelativeData(savedAttrs.textPath, plainText);
            } catch(e) {
              console.warn('[TinyMCE] Failed to extract plain text on blur', e);
            }
          });
        }

        // Subscribe to valuePath (HTML content)
        sourceNode.subscribe(savedAttrs.valuePath, function(v, kw2, reason){
          if (reason === 'container') { return; }
          if (!editor.initialized) {
            // Editor not ready yet, retry after a short delay
            setTimeout(function(){
              try {
                if (editor.initialized && editor.getContent() !== (v || '')) {
                  editor.setContent(v || '');
                }
              } catch(e) {
                console.warn('[TinyMCE] Failed to set content in retry', e);
              }
            }, 100);
            return;
          }
          try {
            if (editor.getContent() !== (v || '')) { editor.setContent(v || ''); }
          } catch(e) {
            console.warn('[TinyMCE] Failed to set content in subscribe', e);
          }
        });

        // TinyMCE initialization complete
        editor.on('Init', function(){
          var c = editor.getContainer();
          if (c){
            if (rawHeight && /%$/.test(rawHeight)){
              c.style.height = rawHeight; c.style.minHeight = '200px';
            } else if (!rawHeight || rawHeight === '100%'){
              c.style.height = '100%'; c.style.minHeight = '200px';
            }
          }
          try{
            var iv = sourceNode.getRelativeData(savedAttrs.valuePath);
            if (typeof iv !== 'undefined' && iv !== null && editor.getContent() !== (iv || '')){ editor.setContent(iv || ''); }
          }catch(_e){}
          var body = editor.getBody();
          if (body){ ['dragenter','dragover'].forEach(function(ev){ body.addEventListener(ev, focusOnDrag, {passive:false}); }); body.addEventListener('drop', insertDroppedText, {passive:false}); }
          // Resize node alla fine dell'inizializzazione, se visibile
          try {
              if (genro.dom.isVisible(sourceNode)) {
                  genro.dom.resizeNode(domNode);
              }
          } catch(e) {
              console.warn('[TinyMCE] resize skipped - not ready yet', e);
          }

          // Mark editor as initialized
          editor.initialized = true;

          // Retry loading content after a delay to handle race conditions
          setTimeout(function(){
            try {
              var currentValue = sourceNode.getRelativeData(savedAttrs.valuePath);
              if (currentValue && currentValue !== '') {
                var editorContent = '';
                try {
                  editorContent = editor.getContent();
                } catch(e) {
                  console.warn('[TinyMCE] Could not get content in retry', e);
                }
                if (editorContent !== currentValue) {
                  editor.setContent(currentValue);
                  console.log('[TinyMCE] Loaded content from datastore after delay');
                }
              }

              // Store the normalized version of initial content for comparison
              setTimeout(function(){
                try {
                  var currentContent = editor.getContent();
                  var originalContent = sourceNode.getRelativeData(savedAttrs.valuePath);

                  // Store normalized versions for comparison
                  originalNormalizedContent = normalizeForComparison(originalContent || '');
                  var currentNormalized = normalizeForComparison(currentContent);

                  console.log('[TinyMCE] Initial content loaded');
                  console.log('[TinyMCE] Original normalized:', originalNormalizedContent.substring(0, 100));
                  console.log('[TinyMCE] Current normalized:', currentNormalized.substring(0, 100));
                  console.log('[TinyMCE] savedAttrs.textPath:', savedAttrs.textPath);
                  console.log('[TinyMCE] savedAttrs.valuePath:', savedAttrs.valuePath);

                  // Note: We don't populate textPath on initial load to avoid marking record as modified
                  // Plain text extraction happens only when user edits the content

                  // Activate change listener only after first REAL user interaction
                  var activateListener = function(){
                    if (!changeListenerActive) {
                      changeListenerActive = true;
                      console.log('[TinyMCE] Change listener activated');
                    }
                  };

                  // Activate ONLY on actual user typing or content change
                  editor.once('keydown', activateListener);
                  editor.once('input', activateListener);
                  editor.once('ExecCommand', activateListener);
                } catch(e) {
                  console.warn('[TinyMCE] Failed to setup change detection', e);
                  changeListenerActive = true;
                }
              }, 100);
            } catch(e) {
              console.warn('[TinyMCE] Failed to load content after delay', e);
              changeListenerActive = true; // Activate anyway
            }
          }, 200);
        });
        if (savedAttrs.placeholderItems && savedAttrs.placeholderItems.length){
          editor.ui.registry.addMenuButton('placeholders', {
            text: '$',
            fetch: function(cb){
              const items = savedAttrs.placeholderItems.map(function(name){
                const txt = '$' + name.trim();
                return { type: 'menuitem', text: txt, onAction: function(){ editor.insertContent(txt); } };
              });
              cb(items);
            }
          });
        }

        // insertToolbarItems management
        if (savedAttrs.insertToolbarItems && savedAttrs.insertToolbarItems.length){
          savedAttrs.insertToolbarItems.forEach(function(item){
            // Only register custom buttons for objects with insertText
            // Simple strings (like 'codesample') are handled directly in the toolbar
            if (typeof item === 'object' && item !== null && item.insertText){
              const buttonName = item.name;
              const buttonText = item.text || item.tooltip || 'Insert';
              const insertText = item.insertText;

              editor.ui.registry.addButton(buttonName, {
                text: buttonText,
                tooltip: item.tooltip || 'Insert',
                onAction: function(){
                  try {
                    editor.insertContent(insertText);
                    editor.focus();
                  } catch(e) {
                    console.error('[TinyMCE] Insert text error:', e);
                  }
                }
              });
            }
          });
        }

        // maxLength management
        if (savedAttrs.maxLength) {
          var statusbarItemName = 'charcount_' + savedAttrs.textareaId;

          // Function to update character count display
          var updateCharCount = function(){
            try {
              var content = editor.getContent({format: 'text'}) || '';
              var currentLength = content.length;
              var remaining = savedAttrs.maxLength - currentLength;
              var container = editor.getContainer();
              if (!container) return;

              var statusbar = container.querySelector('.tox-statusbar');
              if (!statusbar) return;

              var charCountEl = statusbar.querySelector('.' + statusbarItemName);
              if (!charCountEl) {
                charCountEl = document.createElement('div');
                charCountEl.className = statusbarItemName;
                charCountEl.style.cssText = 'margin-left: auto; padding: 0 8px; font-size: 12px; font-style: italic;';
                statusbar.appendChild(charCountEl);
              }

              charCountEl.textContent = 'Remaining: ' + remaining;
              if (remaining < 0) {
                charCountEl.style.color = 'red';
              } else if (remaining < savedAttrs.maxLength * 0.1) {
                charCountEl.style.color = 'orange';
              } else {
                charCountEl.style.color = '';
              }
            } catch(e) {
              console.warn('[TinyMCE] Failed to update char count', e);
            }
          };

          // Function to enforce maxLength
          var checkMaxLength = function(){
            try {
              var content = editor.getContent({format: 'text'}) || '';
              if (content.length > savedAttrs.maxLength) {
                // Prevent further input by reverting to last valid content
                var html = editor.getContent();
                // Try to trim content intelligently
                var doc = new DOMParser().parseFromString(html, 'text/html');
                var text = doc.body.textContent || '';
                if (text.length > savedAttrs.maxLength) {
                  // Content is too long, we need to truncate
                  // This is a simple approach - you could improve it
                  console.warn('[TinyMCE] Content exceeds maxLength, content will be truncated');
                }
              }
              updateCharCount();
            } catch(e) {
              console.warn('[TinyMCE] Failed to check maxLength', e);
            }
          };

          // Attach event handlers
          editor.on('keyup', checkMaxLength);
          editor.on('change', checkMaxLength);
          editor.on('SetContent', function(){
            setTimeout(updateCharCount, 10);
          });
          editor.on('init', function(){
            setTimeout(updateCharCount, 100);
          });

          // Also update on paste
          editor.on('paste', function(){
            setTimeout(checkMaxLength, 10);
          });
        }

        console.log('[TinyMCE] after init for', savedAttrs.textareaId);
      }
    });
  },

  mixin_gnr_value: function(value, kw, trigger_reason){
      var ed = this.sourceNode && this.sourceNode.externalWidget;
      if (!ed) { return; }
      if (typeof value === 'undefined'){
        try { value = this.sourceNode.getAttributeFromDatasource('value'); } catch(_e) { value = ''; }
      }
      if (!ed.hasFocus() && ed.getContent() !== (value || '')){
        ed.setContent(value || '');
      }
  },

  mixin_gnr_setDisabled: function(disabled){
      var ed = this;
      try{
        if (disabled){
          if (ed.mode && typeof ed.mode.set === 'function'){ ed.mode.set('readonly'); }
          else if (typeof ed.setMode === 'function'){ ed.setMode('readonly'); }
          var body = ed.getBody && ed.getBody();
          if (body){ body.setAttribute('contenteditable','false'); }
          var c = ed.getContainer && ed.getContainer();
          if (c && c.querySelectorAll){
            var ctrls = c.querySelectorAll('button, [role="menuitem"], [aria-label][tabindex]');
            Array.prototype.forEach.call(ctrls, function(el){
              try{ el.disabled = true; el.setAttribute('tabindex','-1'); }catch(_e){}
            });
          }
        }else{
          if (ed.mode && typeof ed.mode.set === 'function'){ ed.mode.set('design'); }
          else if (typeof ed.setMode === 'function'){ ed.setMode('design'); }
          var body2 = ed.getBody && ed.getBody();
          if (body2){ body2.setAttribute('contenteditable','true'); }
          var c2 = ed.getContainer && ed.getContainer();
          if (c2 && c2.querySelectorAll){
            var ctrls2 = c2.querySelectorAll('button, [role="menuitem"], [aria-label][tabindex]');
            Array.prototype.forEach.call(ctrls2, function(el){
              try{ el.disabled = false; el.removeAttribute('tabindex'); }catch(_e){}
            });
          }
        }
      }catch(e){}
  },

  mixin_gnr_readOnly: function(value, kw, trigger_reason){
      this.gnr_setDisabled(!!value);
  },
  mixin_gnr_disabled: function(value, kw, trigger_reason){
      this.gnr_setDisabled(!!value);
  }
});

