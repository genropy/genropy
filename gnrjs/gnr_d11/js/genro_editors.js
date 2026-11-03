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
        const scriptUrl = "https://uicdn.toast.com/editor/3.2.2/toastui-editor-all.min.js";
        const cssUrl = "https://uicdn.toast.com/editor/3.2.2/toastui-editor.min.css";
        const pickerCss = "https://uicdn.toast.com/tui-color-picker/v2.2.8/tui-color-picker.min.css";
        const pickerJs  = "https://uicdn.toast.com/tui-color-picker/v2.2.8/tui-color-picker.min.js";
        const colorCss  = "https://uicdn.toast.com/editor-plugin-color-syntax/3.0.3/toastui-editor-plugin-color-syntax.min.css";
        const colorJs   = "https://uicdn.toast.com/editor-plugin-color-syntax/3.0.3/toastui-editor-plugin-color-syntax.min.js";
        
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
        if(window.CodeMirror6){
            cb();
            return;
        }
        // Dedupe concurrent loads: several editors created in the same tick all see
        // !window.CodeMirror6 and would each append a <script> via loadJs (which does
        // not dedupe). The bundle would then run twice, instantiating a second
        // @codemirror/state and breaking instanceof checks across editors ("multiple
        // instances of @codemirror/state are loaded"). Queue callbacks behind a single
        // in-flight load instead. The handler is a singleton (gnr.wdg caches it), so
        // this state is shared across every codemirror editor on the page.
        this._cm6PendingCbs = this._cm6PendingCbs || [];
        this._cm6PendingCbs.push(cb);
        if(this._cm6Loading){
            return;
        }
        this._cm6Loading = true;
        var that = this;
        // mtime-based cache-buster: server publishes the file mtime via gnr.vendoredMtime
        // so the browser refetches the bundle whenever it gets rebuilt.
        var mtime = genro.getData('gnr.vendoredMtime.codemirror6') || 0;
        var url = '/_rsrc/js_libs/codemirror6/codemirror6.bundle.js' + (mtime ? '?mtime=' + mtime : '');
        genro.dom.loadJs(url, function(){
            that._cm6Loading = false;
            var cbs = that._cm6PendingCbs;
            that._cm6PendingCbs = [];
            for(var i = 0; i < cbs.length; i++){ cbs[i](); }
        });
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
        var lineWrappingCompartment = new CM.Compartment();
        extensions.push(lineWrappingCompartment.of(cmAttrs.lineWrapping ? CM.EditorView.lineWrapping : []));
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
            lineWrappingCompartment: lineWrappingCompartment,
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
                console.warn('codemirror6: failed to restore selection snapshot', e);
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
        view._lineWrappingCompartment = built.lineWrappingCompartment;
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
        // Cheap length check first so unchanged large docs don't materialize the full rope.
        if(doc.length === newValue.length && doc.toString() === newValue) return;
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
        var CM = window.CodeMirror6;
        var view = this;
        if(!view._lineWrappingCompartment) return;
        view.dispatch({
            effects: view._lineWrappingCompartment.reconfigure(value ? CM.EditorView.lineWrapping : [])
        });
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
        // value: leave the binding (^.path) intact on sourceNode.attr so that
        // mixin_gnr_value can react to datapath changes. Resolve the current
        // value via getAttributeFromDatasource which follows the binding when
        // present and returns the literal value otherwise.
        pmAttrs.value = sourceNode.getAttributeFromDatasource('value');
        if(pmAttrs.value == null){ pmAttrs.value = ''; }
        pmAttrs.format = objectPop(attributes, 'format') || 'html';  // 'html' | 'json' | 'bag'
        // Lifecycle hooks: strings of JS source executed around dispatchTransaction.
        // beforeDispatch runs before the transaction is applied to the state.
        // afterDispatch runs after the state has been updated.
        // onChange runs only when tr.docChanged is true (skip selection-only changes).
        // Scope available in all three: tr, view, steps, doc, before, genro, sourceNode.
        pmAttrs.beforeDispatch = objectPop(attributes, 'beforeDispatch');
        pmAttrs.afterDispatch = objectPop(attributes, 'afterDispatch');
        pmAttrs.onChange = objectPop(attributes, 'onChange');
        // schema selection: 'basic' | 'basicWithLists' (default) | 'basicWithListsAndTables'
        pmAttrs.schema = objectPop(attributes, 'schema') || 'basicWithLists';
        // setup preset: 'minimal' | 'example' (default) | 'full'
        // - minimal: baseKeymap + history + cursors. No input rules, no menubar.
        // - example: input rules (markdown-ish) + list keymap + history.
        // - full: example + menubar (toolbar) + table editing/resizing if schema
        //   includes tables + trailing-node.
        pmAttrs.setup = objectPop(attributes, 'setup') || 'example';
        // menubar override: True/False forces presence regardless of setup.
        // null/undefined = derived from setup ('full' -> true, others -> false).
        pmAttrs.menubar = objectPop(attributes, 'menubar');
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
    // Resolve the schema name to the actual Schema instance from the bundle.
    // Unknown names fall back to basicWithLists so the editor still boots.
    _resolveSchema: function(PM, name){
        var s = PM.schemas[name];
        if(!s){
            console.warn('[proseMirrorEditor] unknown schema "' + name + '", falling back to basicWithLists');
            s = PM.schemas.basicWithLists;
        }
        return s;
    },
    // Build the plugin list for the requested setup preset. 'minimal' returns
    // just baseKeymap+history+cursors. 'example' adds markdown-ish input rules
    // and list keymap. 'full' is example + menubar + tables + trailing node.
    _buildPlugins: function(PM, schema, setup, menubarOverride){
        var plugins = [];
        if(setup === 'minimal'){
            plugins.push(PM.history());
            plugins.push(PM.keymap({'Mod-z': PM.undo, 'Mod-y': PM.redo, 'Mod-Shift-z': PM.redo}));
            plugins.push(PM.keymap(PM.baseKeymap));
            plugins.push(PM.dropCursor());
            plugins.push(PM.gapCursor());
            return plugins;
        }
        // example + full share the markdown-ish input rules and list keymap.
        var rules = PM.smartQuotes.concat([PM.ellipsis, PM.emDash]);
        if(schema.nodes.heading){
            rules.push(PM.textblockTypeInputRule(/^(#{1,6})\s$/, schema.nodes.heading,
                function(match){ return {level: match[1].length}; }));
        }
        if(schema.nodes.blockquote){
            rules.push(PM.wrappingInputRule(/^\s*>\s$/, schema.nodes.blockquote));
        }
        if(schema.nodes.ordered_list){
            rules.push(PM.wrappingInputRule(/^(\d+)\.\s$/, schema.nodes.ordered_list,
                function(match){ return {order: +match[1]}; },
                function(match, node){ return node.childCount + node.attrs.order === +match[1]; }));
        }
        if(schema.nodes.bullet_list){
            rules.push(PM.wrappingInputRule(/^\s*([-+*])\s$/, schema.nodes.bullet_list));
        }
        if(schema.nodes.code_block){
            rules.push(PM.textblockTypeInputRule(/^```$/, schema.nodes.code_block));
        }
        var listKeys = {};
        if(schema.nodes.list_item){
            listKeys['Enter'] = PM.splitListItem(schema.nodes.list_item);
            listKeys['Mod-['] = PM.liftListItem(schema.nodes.list_item);
            listKeys['Mod-]'] = PM.sinkListItem(schema.nodes.list_item);
        }
        var markKeys = {};
        if(schema.marks.strong){ markKeys['Mod-b'] = PM.toggleMark(schema.marks.strong); }
        if(schema.marks.em){ markKeys['Mod-i'] = PM.toggleMark(schema.marks.em); }
        if(schema.marks.code){ markKeys['Mod-`'] = PM.toggleMark(schema.marks.code); }
        var historyKeys = {'Mod-z': PM.undo, 'Mod-y': PM.redo, 'Mod-Shift-z': PM.redo};
        plugins.push(PM.history());
        plugins.push(PM.keymap(historyKeys));
        plugins.push(PM.keymap(listKeys));
        plugins.push(PM.keymap(markKeys));
        plugins.push(PM.keymap(PM.baseKeymap));
        plugins.push(PM.inputRules({rules: rules}));
        plugins.push(PM.dropCursor());
        plugins.push(PM.gapCursor());
        // 'full' adds menubar / tables / trailing-node on top of 'example'.
        var menubarEnabled = (menubarOverride == null) ? (setup === 'full') : !!menubarOverride;
        if(setup === 'full' || menubarEnabled){
            // Menubar: prosemirror-example-setup.buildMenuItems builds a menu
            // tailored to the given schema (basic / lists / tables).
            try {
                var menu = PM.buildMenuItems(schema);
                var fullMenu = menu.fullMenu;
                // If the schema has tables, splice in a "Table" dropdown right
                // after the formatting groups (matches the position used in the
                // prosemirror-tables demo).
                if(schema.nodes.table && PM.tables){
                    var tableMenu = this._buildTableMenu(PM, schema);
                    if(tableMenu && tableMenu.length){
                        fullMenu = fullMenu.slice();
                        fullMenu.splice(2, 0, [new PM.menu.Dropdown(tableMenu, {label: 'Table'})]);
                    }
                }
                plugins.push(PM.menu.menuBar({floating: true, content: fullMenu}));
            } catch(e){
                console.warn('[proseMirrorEditor] menubar build failed:', e);
            }
        }
        // Tables: column resizing + table editing keymap if schema has tables.
        if(schema.nodes.table && PM.tables){
            try {
                plugins.push(PM.tables.columnResizing());
                plugins.push(PM.tables.tableEditing());
                // Tab / Shift-Tab to move between cells.
                plugins.push(PM.keymap({
                    'Tab': PM.tables.goToNextCell(1),
                    'Shift-Tab': PM.tables.goToNextCell(-1)
                }));
            } catch(e){
                console.warn('[proseMirrorEditor] tables plugins failed:', e);
            }
        }
        // Trailing node: keep an empty paragraph at the end so users can click
        // below the last block. Only meaningful in 'full' setup.
        if(setup === 'full' && PM.trailingNode){
            try { plugins.push(PM.trailingNode()); } catch(e){}
        }
        return plugins;
    },
    // Build the "Table" dropdown menu. The "Insert table 3x3" command is
    // custom (prosemirror-tables exposes the per-cell commands but no helper
    // to create a fresh table); the rest are direct from PM.tables.
    _buildTableMenu: function(PM, schema){
        var T = PM.tables;
        var Mi = PM.menu.MenuItem;
        function item(label, cmd){
            return new Mi({label: label, select: cmd, run: cmd});
        }
        var insertTable = function(state, dispatch){
            var rows = 3, cols = 3;
            var cellType = schema.nodes.table_cell;
            var headerType = schema.nodes.table_header;
            var rowType = schema.nodes.table_row;
            var tableType = schema.nodes.table;
            if(!cellType || !rowType || !tableType){ return false; }
            var headerRow = null;
            if(headerType){
                var headerCells = [];
                for(var i = 0; i < cols; i++){
                    headerCells.push(headerType.createAndFill());
                }
                headerRow = rowType.create(null, headerCells);
            }
            var bodyRows = [];
            for(var r = 0; r < (headerRow ? rows - 1 : rows); r++){
                var bodyCells = [];
                for(var c = 0; c < cols; c++){
                    bodyCells.push(cellType.createAndFill());
                }
                bodyRows.push(rowType.create(null, bodyCells));
            }
            var allRows = headerRow ? [headerRow].concat(bodyRows) : bodyRows;
            var table = tableType.create(null, allRows);
            if(dispatch){
                var tr = state.tr.replaceSelectionWith(table).scrollIntoView();
                dispatch(tr);
            }
            return true;
        };
        var items = [
            item('Insert table (3×3)', insertTable),
            item('Insert column before', T.addColumnBefore),
            item('Insert column after', T.addColumnAfter),
            item('Delete column', T.deleteColumn),
            item('Insert row before', T.addRowBefore),
            item('Insert row after', T.addRowAfter),
            item('Delete row', T.deleteRow),
            item('Delete table', T.deleteTable),
            item('Merge cells', T.mergeCells),
            item('Split cell', T.splitCell),
            item('Toggle header column', T.toggleHeaderColumn),
            item('Toggle header row', T.toggleHeaderRow),
            item('Toggle header cells', T.toggleHeaderCell)
        ];
        if(T.setCellAttr){
            items.push(item('Highlight cell (green)', T.setCellAttr('background', '#dfd')));
            items.push(item('Clear cell highlight', T.setCellAttr('background', null)));
        }
        return items;
    },
    initialize: function(widget, pmAttrs, sourceNode){
        // Tag the host so prosemirror.css can clip overflow at the user-supplied
        // height and let the .ProseMirror surface scroll inside.
        widget.classList.add('gnr-prosemirror-host');
        var that = this;
        var PM = window.ProseMirror;
        var schemaName = pmAttrs.schema || 'basicWithLists';
        var schema = this._resolveSchema(PM, schemaName);
        var format = pmAttrs.format || 'html';
        var setup = pmAttrs.setup || 'example';
        // pmAttrs.value is already resolved by `creating` (or by `rebuild` for
        // subsequent mounts) so we don't re-read from the datasource here.
        var initialValue = (pmAttrs.value == null) ? '' : pmAttrs.value;
        var doc = this.parseInitialDoc(PM, schema, initialValue, format);
        var plugins = this._buildPlugins(PM, schema, setup, pmAttrs.menubar);
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
        view._gnrSchemaName = schemaName;
        view._gnrFormat = format;
        view._gnrSetup = setup;
        view._gnrPmAttrs = pmAttrs;
        view._gnrWidget = widget;
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
    // Tear down the current EditorView and rebuild it with merged pmAttrs.
    // Used by gnr_rebuild and the schema/setup change mixins. Preserves the
    // current document content (serialized in the previous format) so that
    // switching setup or menubar does not blank out the user's work.
    rebuild: function(sourceNode, overrides){
        var view = sourceNode.externalWidget;
        if(!view){ return; }
        var prevPmAttrs = view._gnrPmAttrs || {};
        var widget = view._gnrWidget;
        // Snapshot the current value in the prev format and feed it back as
        // initial value of the rebuild. If the format itself changed, we
        // serialize in the OLD format and the new init parser will receive a
        // value it does not understand: in that case start empty.
        var PM = window.ProseMirror;
        var prevSchema = view._gnrSchema;
        var prevFormat = view._gnrFormat;
        var snapshot;
        try { snapshot = this.serializeDoc(PM, prevSchema, view.state.doc, prevFormat); }
        catch(e){ snapshot = ''; }
        var newPmAttrs = objectUpdate({}, prevPmAttrs);
        objectUpdate(newPmAttrs, overrides || {});
        // If the format changed, the snapshot is in the wrong language: drop it.
        if(overrides && overrides.format && overrides.format !== prevFormat){
            newPmAttrs.value = '';
        } else {
            newPmAttrs.value = snapshot;
        }
        view.destroy();
        // The widget div is the same DOM node; clear any leftover children.
        while(widget.firstChild){ widget.removeChild(widget.firstChild); }
        this.initialize(widget, newPmAttrs, sourceNode);
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
    },
    // gnr_setSchema('basicWithListsAndTables') / gnr_setSetup('full') /
    // gnr_setMenubar(true) trigger a full view rebuild with the override
    // merged on top of the previous pmAttrs. Document content is preserved
    // when the format does not change.
    mixin_gnr_setSchema: function(value, kw, trigger_reason){
        var view = this;
        view.gnr.rebuild(view.sourceNode, {schema: value});
    },
    mixin_gnr_setSetup: function(value, kw, trigger_reason){
        var view = this;
        view.gnr.rebuild(view.sourceNode, {setup: value});
    },
    mixin_gnr_setMenubar: function(value, kw, trigger_reason){
        var view = this;
        view.gnr.rebuild(view.sourceNode, {menubar: !!value});
    },
    mixin_gnr_setFormat: function(value, kw, trigger_reason){
        var view = this;
        view.gnr.rebuild(view.sourceNode, {format: value});
    },
    // Generic rebuild: pass any subset of {schema, setup, menubar, format,
    // beforeDispatch, afterDispatch, onChange} as kw.
    mixin_gnr_rebuild: function(value, kw, trigger_reason){
        var view = this;
        view.gnr.rebuild(view.sourceNode, kw || value || {});
    }
});

dojo.declare("gnr.widgets.joditEditor", gnr.widgets.baseExternalWidget, {
    toolbars: {
        minimal: ['bold', 'italic', 'underline', '|', 'ul', 'ol', '|', 'link', '|', 'source'],
        simple: ['bold', 'italic', 'underline', '|', 'ul', 'ol', '|', 'paragraph', '|',
                 'left', 'center', 'right', '|', 'link', 'image', 'table', '|', 'eraser', '|', 'source'],
        standard: ['bold', 'italic', 'underline', 'strikethrough', '|', 'ul', 'ol', 'outdent', 'indent', '|',
                   'paragraph', 'font', 'fontsize', 'brush', '|', 'left', 'center', 'right', 'justify', '|',
                   'link', 'image', 'table', 'hr', 'symbols', '|', 'eraser', 'copyformat', '|',
                   'undo', 'redo', '|', 'find', 'source', 'fullsize']
    },
    // Jodit's defaults rewrite stored markup on the first save (iframes dropped
    // or sandboxed, b/i renamed, &nbsp; replaced, empty spacers removed or
    // filled with <br>): keep it as written.
    cleanHTML: {denyTags: 'script', replaceOldTags: false, replaceNBSP: false,
                removeEmptyElements: false, fillEmptyParagraph: false,
                sandboxIframesInContent: false, collapseEmptyValueToEmptyString: true},
    modeNames: ['wysiwyg', 'source', 'split'],

    constructor: function(application) {
        this._domtag = 'div';
    },
    creating: function(attributes, sourceNode) {
        objectPop(attributes, 'value');
        // read back from sourceNode.attr when the text is written, as mode and _delay are
        objectPop(attributes, 'textpath');
        var toolbar = objectPop(attributes, 'toolbar');
        var placeholder = objectPop(attributes, 'placeholder');
        var placeholders = this.splitList(objectPop(attributes, 'placeholders'));
        var codeBlock = objectPop(attributes, 'codeBlock');
        var maxLength = Number(objectPop(attributes, 'maxLength')) || 0;
        var imageData = objectPop(attributes, 'imageData');
        var options = {
            toolbar: toolbar !== false,
            buttons: this.resolveToolbar(toolbar),
            toolbarAdaptive: false,
            iframe: objectPop(attributes, 'iframe') !== false,
            iframeCSSLinks: this.splitList(objectPop(attributes, 'contentsCss')),
            enter: (objectPop(attributes, 'enter') || 'p').toUpperCase(),
            placeholder: placeholder || '',
            showPlaceholder: !!placeholder,
            statusbar: !!objectPop(attributes, 'statusbar'),
            hidePoweredByJodit: true,
            readonly: !!objectPop(attributes, 'readOnly'),
            disabled: !!objectPop(attributes, 'disabled'),
            language: (genro.locale() || 'en').slice(0, 2).toLowerCase(),
            height: attributes.height ? '100%' : 'auto',
            minHeight: 0,
            allowResizeY: false,
            askBeforePasteHTML: false,
            askBeforePasteFromWord: false,
            beautifyHTML: false,
            cleanHTML: objectUpdate({}, this.cleanHTML)
        };
        if(maxLength){
            // Jodit's own counters are on by default and would sit next to the
            // remaining budget repeating it: the budget alone is shown. Without
            // countTextSpaces the limit plugin counts the words joined, so it
            // would block at a different number than the one on display.
            objectUpdate(options, {limitChars: maxLength, countTextSpaces: true, statusbar: true,
                                   showCharsCounter: false, showWordsCounter: false});
        }
        // with toolbar=False there is no bar to put them in: the buttons are dropped
        var extraButtons = options.toolbar ? this.resolveExtraButtons(placeholders, codeBlock) : [];
        if(extraButtons.length){
            options.extraButtons = extraButtons;
        }
        objectUpdate(options, objectExtract(attributes, 'config_*'));
        if(imageData){
            // merged after config_*, so an uploader passed by the caller survives and wins
            options.uploader = objectUpdate({insertImageAsBase64URI: true}, options.uploader);
        }
        return {joditAttrs: {options: options,
                             mode: objectPop(attributes, 'mode') || 'wysiwyg',
                             sourceEditor: objectPop(attributes, 'sourceEditor') || 'codemirror',
                             contentStyles: objectPop(attributes, 'contentStyles'),
                             bodyStyle: objectPop(attributes, 'bodyStyle')}};
    },
    created: function(widget, savedAttrs, sourceNode) {
        var that = this;
        var joditAttrs = objectPop(savedAttrs, 'joditAttrs');
        this.loadJodit(function(){ that.initialize(widget, joditAttrs, sourceNode); });
    },
    loadJodit: function(cb) {
        if(window.Jodit){
            cb();
            return;
        }
        var cssMtime = genro.getData('gnr.vendoredMtime.joditCss') || 0;
        genro.dom.loadCss('/_rsrc/js_libs/jodit/jodit.min.css' + (cssMtime ? '?mtime=' + cssMtime : ''), 'jodit');
        var jsMtime = genro.getData('gnr.vendoredMtime.jodit') || 0;
        genro.dom.loadJs('/_rsrc/js_libs/jodit/jodit.min.js' + (jsMtime ? '?mtime=' + jsMtime : ''), cb);
    },
    resolveToolbar: function(toolbar) {
        if(toolbar === false){
            return [];
        }
        if(!toolbar || this.toolbars[toolbar]){
            return this.toolbars[toolbar || 'standard'].slice();
        }
        return this.splitList(toolbar);
    },
    splitList: function(value) {
        if(!value){
            return [];
        }
        if(typeof(value) == 'string'){
            value = value.split(',');
        }
        return value.map(function(item){ return item.trim(); }).filter(Boolean);
    },
    // extraButtons is appended to the toolbar on its own: naming a control in the
    // buttons list too renders it twice, the second time as its bare name.
    resolveExtraButtons: function(placeholders, codeBlock) {
        var buttons = [];
        if(placeholders.length){
            buttons.push(this.placeholdersButton(placeholders));
        }
        if(codeBlock){
            buttons.push(this.codeBlockButton());
        }
        return buttons;
    },
    placeholdersButton: function(names) {
        var list = {};
        names.forEach(function(name){
            list['$' + name] = '$' + name;
        });
        return {name: 'placeholders', text: '$', tooltip: _T('Insert field'), list: list,
                exec: function(jodit, current, opts){
                    jodit.s.insertHTML(opts.control.args[0]);
                }};
    },
    // No vendored Jodit icon fits a code block, and the only near one, source, is the
    // glyph of the Source button already in the toolbar: a text label instead.
    codeBlockButton: function() {
        var that = this;
        return {name: 'codeBlock', text: '{ }', tooltip: _T('Code block'),
                exec: function(jodit){ that.insertCodeBlock(jodit); }};
    },
    // The caret cannot sit in a truly empty element: setCursorIn leaves there the
    // invisible space Jodit uses for it, which textLength and the drop code skip.
    insertCodeBlock: function(editor) {
        var code = editor.createInside.element('code');
        editor.s.insertNode(editor.createInside.element('pre', [code]));
        editor.s.setCursorIn(code);
    },
    modeCode: function(name) {
        var code = this.modeNames.indexOf(name) + 1;
        if(!code){
            throw new Error('joditEditor: unknown mode "' + name + '", expected ' + this.modeNames.join('|'));
        }
        return code;
    },
    modeName: function(code) {
        return this.modeNames[code - 1];
    },
    initialize: function(widget, joditAttrs, sourceNode) {
        var that = this;
        widget.classList.add('gnr-jodit-host');
        var textarea = document.createElement('textarea');
        textarea.value = sourceNode.getAttributeFromDatasource('value') || '';
        widget.appendChild(textarea);
        var options = objectUpdate({defaultMode: this.modeCode(joditAttrs.mode)}, joditAttrs.options);
        if(joditAttrs.sourceEditor == 'codemirror'){
            options.sourceEditor = function(jodit){ return that.makeCodemirrorSource(jodit); };
        }else{
            options.sourceEditor = 'area';
        }
        var editor = Jodit.make(textarea, options);
        editor._gnrReadOnly = options.readonly;
        this.setExternalWidget(sourceNode, editor);
        var markUserEdit = function(){ editor._gnrUserEdit = true; };
        editor.e.on('keydown mousedown paste drop', markUserEdit)
                .on(editor.container, 'mousedown keydown touchstart', markUserEdit)
                .on('change', function(){ that.onEditorChange(editor); })
                .on('blur', function(){ that.writeValue(editor, true); })
                .on('afterSetMode', function(){ that.onModeChange(editor); });
        // Jodit sizes its workplace on window resize only: built in a hidden page it stays 150px high
        var parentWidget = dijit.getEnclosingWidget(widget);
        if(parentWidget){
            editor._gnrParentResize = dojo.connect(parentWidget, 'resize', function(){ editor.e.fire('resize'); });
        }
        editor.waitForReady().then(function(){
            editor.gnr_contentStyles(joditAttrs.contentStyles);
            editor.gnr_bodyStyle(joditAttrs.bodyStyle);
            that.setupFieldDrop(editor);
            that.releaseChangeLimit(editor);
            that.setupCharCounter(editor);
        });
    },
    onSpeechEnd: function(sourceNode, text) {
        var editor = sourceNode.externalWidget;
        editor._gnrUserEdit = true;
        editor.s.insertNode(editor.createInside.text(text));
        this.writeValue(editor);
    },
    // A Genropy drag (a template variable from a tree) stops its dragstart, so neither
    // Jodit nor the browser place it reliably: it is shown and inserted here.
    isFieldDrag: function(editor, dataTransfer) {
        if(editor.getReadOnly()){
            return false;
        }
        var types = Array.prototype.slice.call((dataTransfer && dataTransfer.types) || []);
        return types.indexOf('dragsourceinfo') >= 0 && types.indexOf('text/plain') >= 0
            && types.indexOf('text/html') < 0 && types.indexOf('Files') < 0;
    },
    dropRange: function(editor, x, y) {
        var doc = editor.ed;
        var body = editor.editor;
        var range = null;
        if(doc.caretRangeFromPoint){
            range = doc.caretRangeFromPoint(x, y);
        } else if(doc.caretPositionFromPoint){
            var position = doc.caretPositionFromPoint(x, y);
            if(position){
                range = doc.createRange();
                range.setStart(position.offsetNode, position.offset);
            }
        }
        var last = body.lastElementChild || body.lastChild;
        var below = !last || (last.getBoundingClientRect && y > last.getBoundingClientRect().bottom);
        if(!range || below || range.startContainer === body || !body.contains(range.startContainer)){
            var block = last && last.nodeType === 1 ? last : body;
            range = doc.createRange();
            if(block !== body && !/^(P|DIV|H[1-6]|PRE|BLOCKQUOTE)$/.test(block.nodeName)){
                // a table, a list or an image closing the content: the field goes after it, not inside
                range.setStartAfter(block);
                range.collapse(true);
            } else if(block.lastChild && block.lastChild.nodeName === 'BR'){
                range.setStartBefore(block.lastChild);
                range.collapse(true);
            } else {
                range.selectNodeContents(block);
                range.collapse(false);
            }
        }
        return range;
    },
    // Jodit surrounds the caret with \uFEFF text nodes, and with marker spans while the editor is not focused
    isCursorMarker: function(node) {
        if(node.nodeType === 3){
            return !node.data.replace(/\uFEFF/g, '');
        }
        return node.nodeType === 1 && node.hasAttribute('data-jodit-selection_marker');
    },
    // the visible character next to the drop point, on the given side
    charAround: function(range, side) {
        var node = range.startContainer;
        var offset = range.startOffset;
        var step = function(n){ return side < 0 ? n.previousSibling : n.nextSibling; };
        if(node.nodeType === 3){
            var text = (side < 0 ? node.data.slice(0, offset) : node.data.slice(offset)).replace(/\uFEFF/g, '');
            if(text){
                return side < 0 ? text.charAt(text.length - 1) : text.charAt(0);
            }
            node = step(node);
        } else {
            node = node.childNodes[side < 0 ? offset - 1 : offset];
        }
        while(node && this.isCursorMarker(node)){
            node = step(node);
        }
        if(node && node.nodeType === 3){
            return side < 0 ? node.data.charAt(node.data.length - 1) : node.data.charAt(0);
        }
        return '';
    },
    dropText: function(range, text) {
        if(/\S/.test(this.charAround(range, -1))){
            text = ' ' + text;
        }
        if(/\S/.test(this.charAround(range, 1))){
            text = text + ' ';
        }
        return text;
    },
    showDropCaret: function(editor, range) {
        var doc = editor.ed;
        var caret = editor._gnrDropCaret;
        if(!caret){
            caret = doc.createElement('div');
            caret.className = 'gnr-jodit-dropcaret';
            caret.style.cssText = 'position:absolute;width:2px;background:#1a73e8;pointer-events:none;z-index:10;';
            // outside the body, so it never becomes part of the value
            doc.documentElement.appendChild(caret);
            editor._gnrDropCaret = caret;
        }
        var rect = range.getBoundingClientRect();
        if(!rect.height){
            var block = range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentNode;
            var blockRect = block.getBoundingClientRect();
            rect = {left: blockRect.left, top: blockRect.top, height: blockRect.height || 16};
        }
        var win = doc.defaultView;
        caret.style.left = (rect.left + win.scrollX) + 'px';
        caret.style.top = (rect.top + win.scrollY) + 'px';
        caret.style.height = rect.height + 'px';
    },
    dropHighlightNode: function(editor) {
        return editor.o.iframe ? editor.ed.documentElement : editor.editor;
    },
    clearFieldDrop: function(editor) {
        var highlight = this.dropHighlightNode(editor).style;
        highlight.boxShadow = '';
        highlight.background = '';
        if(editor._gnrDropCaret){
            editor._gnrDropCaret.remove();
            delete editor._gnrDropCaret;
        }
    },
    setupFieldDrop: function(editor) {
        var that = this;
        // with the iframe the empty area under the content belongs to <html>, not to the body
        var target = editor.o.iframe ? editor.ed : editor.editor;
        editor.e.on(target, 'dragover', function(evt){
            if(!that.isFieldDrag(editor, evt.dataTransfer)){
                return;
            }
            evt.preventDefault();
            var highlight = that.dropHighlightNode(editor).style;
            highlight.boxShadow = 'inset 0 0 0 2px #1a73e8';
            highlight.background = 'rgba(26, 115, 232, .05)';
            that.showDropCaret(editor, that.dropRange(editor, evt.clientX, evt.clientY));
        }).on(target, 'dragleave', function(evt){
            if(!evt.relatedTarget || !target.contains(evt.relatedTarget)){
                that.clearFieldDrop(editor);
            }
        }).on(target, 'drop', function(evt){
            if(!that.isFieldDrag(editor, evt.dataTransfer)){
                return;
            }
            evt.preventDefault();
            evt.stopPropagation();
            that.clearFieldDrop(editor);
            var range = that.dropRange(editor, evt.clientX, evt.clientY);
            var text = that.dropText(range, evt.dataTransfer.getData('text/plain'));
            var field = editor.createInside.text(text);
            editor._gnrUserEdit = true;
            editor.s.selectRange(range);
            editor.s.insertNode(field);
            // the <br> Jodit keeps in an empty block would push the field onto a second line
            if(field.nextSibling && field.nextSibling.nodeName === 'BR' && !field.nextSibling.nextSibling){
                field.nextSibling.remove();
            }
            that.writeValue(editor);
            return false;
        });
    },
    // What the limit plugin counts with countTextSpaces: editor.text is innerText,
    // which adds a newline between blocks that the plugin strips before comparing.
    textLength: function(editor) {
        return (editor.text || '').replace(/[\uFEFF\r\n]/g, '').length;
    },
    // The limit plugin reverts the whole value on its change hook, and that hook fires on
    // a programmatic assignment too: a value loaded over the limit would be refused, and
    // an over-limit record would be frozen, the revert undoing a deletion as well. Only
    // that listener goes: the key guard still blocks typing at the limit (its COMMAND_KEYS
    // exemption is what lets an over-limit record be deleted back under it) and
    // afterPaste.limit still refuses a paste that does not fit.
    releaseChangeLimit: function(editor) {
        if(editor.o.limitChars){
            editor.e.off('change.limit');
        }
    },
    // limitChars blocks typing at the limit without saying how much is left:
    // the budget takes the place of the Jodit counters switched off with it.
    setupCharCounter: function(editor) {
        var limit = editor.o.limitChars;
        if(!limit || !editor.statusbar){
            return;
        }
        var that = this;
        var counter = document.createElement('span');
        counter.className = 'gnr-jodit-charcounter';
        var label = _T('Remaining') + ': ';
        var update = function(){
            var left = limit - that.textLength(editor);
            counter.textContent = label + left;
            // typing cannot go past the limit: only a value loaded over it goes negative
            counter.style.color = left < 0 ? 'red' : (left < limit * 0.1 ? 'orange' : '');
        };
        editor.statusbar.append(counter, true);
        editor.e.on('change keyup', update);
        update();
    },
    setContentStyle: function(editor, id, css) {
        if(!editor.o.iframe || !editor.ed){
            return;
        }
        var styleNode = editor.ed.getElementById(id);
        if(!styleNode){
            styleNode = editor.ed.createElement('style');
            styleNode.id = id;
            editor.ed.head.appendChild(styleNode);
        }
        styleNode.textContent = css || '';
    },
    onEditorChange: function(editor) {
        if(editor._gnrSilent || !editor._gnrUserEdit){
            return;
        }
        var that = this;
        var sourceNode = editor.sourceNode;
        sourceNode.delayedCall(function(){ that.writeValue(editor); },
                               sourceNode.attr._delay || 500, 'updatingContent');
    },
    writeValue: function(editor, onBlur) {
        if(editor.isInDestruct){
            return;
        }
        if(editor._gnrSource){
            editor._gnrSource.flush();
        }
        if(!editor._gnrUserEdit){
            return;
        }
        var sourceNode = editor.sourceNode;
        var value = editor.value || null;
        if(value !== (sourceNode.getAttributeFromDatasource('value') || null)){
            sourceNode.setAttributeInDatasource('value', value);
        }
        // the plain text follows the markup only when the user leaves the editor,
        // so loading a record never marks it as modified
        if(onBlur && sourceNode.attr.textpath){
            sourceNode.setRelativeData(sourceNode.attr.textpath, editor.text || null);
        }
    },
    onModeChange: function(editor) {
        var sourceNode = editor.sourceNode;
        if(sourceNode.isPointerPath(sourceNode.attr.mode)){
            sourceNode.setAttributeInDatasource('mode', this.modeName(editor.getMode()));
        }
    },
    // Jodit hands the factory only the editor: the host is the plugin's
    // .jodit-source container, already in the workplace when this runs.
    makeCodemirrorSource: function(jodit) {
        var host = document.createElement('div');
        host.className = 'gnr-jodit-codemirror';
        jodit.workplace.querySelector('.jodit-source').appendChild(host);
        var readyCallbacks = [];
        var source = {
            isReady: false,
            view: null,
            _dirty: false,
            _pushing: false,
            _settingValue: false,
            init: function(){
                genro.wdg.getHandler('codemirror').loadCodeMirror6(function(){
                    if(jodit.isInDestruct){
                        return;
                    }
                    source.view = source.createView(window.CodeMirror6);
                    source.isReady = true;
                    readyCallbacks.splice(0).forEach(function(cb){ cb(); });
                });
            },
            createView: function(CM){
                source._readOnly = new CM.Compartment();
                var pushLater = jodit.async.debounce(function(){ source.flush(); }, jodit.defaultTimeout);
                var extensions = [
                    CM.lineNumbers(), CM.highlightActiveLine(), CM.drawSelection(), CM.history(),
                    CM.indentOnInput(), CM.bracketMatching(), CM.foldGutter(), CM.highlightSelectionMatches(),
                    CM.search({top: true}), CM.langs.html(), CM.EditorView.lineWrapping,
                    CM.syntaxHighlighting(CM.defaultHighlightStyle, {fallback: true}),
                    CM.keymap.of([].concat(CM.defaultKeymap, CM.searchKeymap, CM.historyKeymap,
                                           CM.foldKeymap, [CM.indentWithTab])),
                    CM.toolsTheme,
                    source._readOnly.of(CM.EditorState.readOnly.of(!!jodit.o.readonly)),
                    CM.EditorView.updateListener.of(function(update){
                        if(update.docChanged && !source._settingValue){
                            source._dirty = true;
                            pushLater();
                        }
                    }),
                    CM.EditorView.domEventHandlers({
                        focus: function(evt){ jodit.e.fire('focus', evt); },
                        blur: function(evt){ jodit.e.fire('blur', evt); }
                    })
                ];
                return new CM.EditorView({parent: host, state: CM.EditorState.create({doc: '', extensions: extensions})});
            },
            flush: function(){
                if(!source._dirty || jodit.isInDestruct){
                    return;
                }
                source._dirty = false;
                source._pushing = true;
                try {
                    jodit.value = source.getValue();
                } finally {
                    source._pushing = false;
                }
            },
            getValue: function(){
                return source.view ? source.view.state.doc.toString() : '';
            },
            setValue: function(raw){
                if(source._pushing || !source.view || raw === source.getValue()){
                    return;
                }
                var head = Math.min(source.view.state.selection.main.head, raw.length);
                source._settingValue = true;
                try {
                    source.view.dispatch({changes: {from: 0, to: source.view.state.doc.length, insert: raw},
                                          selection: {anchor: head}});
                } finally {
                    source._settingValue = false;
                }
            },
            insertRaw: function(raw){
                source.view.dispatch(source.view.state.replaceSelection(raw));
            },
            getSelectionStart: function(){
                return source.view ? source.view.state.selection.main.from : 0;
            },
            getSelectionEnd: function(){
                return source.view ? source.view.state.selection.main.to : 0;
            },
            setSelectionRange: function(start, end){
                var length = source.view.state.doc.length;
                var clamp = function(pos){ return Math.max(0, Math.min(pos, length)); };
                source.view.dispatch({selection: {anchor: clamp(start), head: clamp(end == null ? start : end)},
                                      scrollIntoView: true});
            },
            setPlaceHolder: function(){},
            get isFocused(){
                return !!(source.view && source.view.hasFocus);
            },
            focus: function(){
                if(source.view){ source.view.focus(); }
            },
            blur: function(){
                if(source.view){ source.view.contentDOM.blur(); }
            },
            setReadOnly: function(isReadOnly){
                if(source.view){
                    source.view.dispatch({effects: source._readOnly.reconfigure(
                        window.CodeMirror6.EditorState.readOnly.of(!!isReadOnly))});
                }
            },
            selectAll: function(){
                source.view.dispatch({selection: {anchor: 0, head: source.view.state.doc.length}});
            },
            replaceUndoManager: function(){},
            onReadyAlways: function(cb){
                if(source.isReady){
                    cb();
                } else {
                    readyCallbacks.push(cb);
                }
            },
            destruct: function(){
                if(source.view){ source.view.destroy(); }
                host.remove();
                if(jodit._gnrSource === source){ delete jodit._gnrSource; }
            }
        };
        jodit._gnrSource = source;
        return source;
    },

    mixin_gnr_value: function(value, kw, trigger_reason) {
        value = value || '';
        if(value === this.value){
            return;
        }
        this._gnrSilent = true;
        try {
            this.value = value;
        } finally {
            this._gnrSilent = false;
        }
        this._gnrUserEdit = false;
    },
    mixin_gnr_readOnly: function(value, kw, trigger_reason) {
        this._gnrReadOnly = !!value;
        this.setReadOnly(this._gnrReadOnly || this.getDisabled());
    },
    mixin_gnr_setDisabled: function(disabled) {
        this.setDisabled(!!disabled);
        // Jodit re-enables without leaving read-only: its setReadOnly(false)
        // is a no-op until the cached state is flipped back to true.
        if(!disabled && this.getReadOnly() && !this._gnrReadOnly){
            this.setReadOnly(true);
            this.setReadOnly(false);
        }
    },
    mixin_gnr_mode: function(value, kw, trigger_reason) {
        var code = this.gnr.modeCode(value || 'wysiwyg');
        if(code !== this.getMode()){
            this.setMode(code);
        }
    },
    mixin_gnr_contentStyles: function(value, kw, trigger_reason) {
        this.gnr.setContentStyle(this, 'gnr_contentStyles', value);
    },
    // Appended after contentStyles, so the body box wins over the content CSS.
    mixin_gnr_bodyStyle: function(value, kw, trigger_reason) {
        this.gnr.setContentStyle(this, 'gnr_bodyStyle', value ? 'body{' + value + '}' : '');
    },
    mixin_destroy: function() {
        this.gnr.writeValue(this);
        if(this._gnrParentResize){
            dojo.disconnect(this._gnrParentResize);
        }
        this.destruct();
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
        genro.dev.deprecation('ckEditor', 'joditEditor');
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
