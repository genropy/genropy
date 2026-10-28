dojo.declare("gnr.widgets.GoogleLoader", null, {
    geocoder:{module_name:'maps',other_params: "sensor=false",version:'3.26',language:navigator.language
    },
              
    constructor: function(application) {
        this.pending_commands=[];
        this.ready = true;
        var that=this;
        if (!window.google){
            this.ready = false;
            genro.dom.loadJs("https://www.google.com/jsapi",
                          function(){
                              that.ready=true;
                              dojo.forEach(that.pending_commands, function(cb){
                                  cb.call(that);
                              });
                              that.pending_commands=[];
                          });
        }
    },
    
    runCommand:function(module,cb){
        var that=this;
        if (!this.ready){
            this.pending_commands.push(function(){
                that.runCommand(module,cb);
            });
            return;
        }
        var handler=google[module.module_name];
        if(handler && handler._loaded){
            cb.call(this);
        }
        else if('pending_calls' in module){
            module.pending_calls.push(cb);
        }
        else {
            var kw=objectUpdate({},module);
            var pending_calls=[cb];
            module.pending_calls=pending_calls;
            var module_name=objectPop(kw,'module_name');
            var version=objectPop(kw,'version');
            kw.callback=function(){
                handler=google[module_name];
                handler._loaded=true;
                 dojo.forEach(pending_calls, function(cb){
                     cb.call(that);
                 });
            };
            google.load(module_name,version,kw);
        }
    },
    setGeocoder:function(widget,cb){
        var obj=widget;
        if(this._mapkey){
            this.geocoder.other_params+=('&key='+this._mapkey);
        }
        this.runCommand(this.geocoder,function(){
            obj.geocoder = new google.maps.Geocoder();
            if (cb){
                cb();
            }
        });
    }

});
dojo.declare("gnr.widgets.fullcalendar", gnr.widgets.baseHtml, {
    constructor: function(application) {
        this._domtag = 'div';
    },
    getAddOnDict:function(key){
        return {}[key];
    },
    creating: function(attributes, sourceNode) {
        var boxAttrs = objectExtract(attributes,'box_*');
        var calAttrs = objectUpdate({},attributes);
        var storepath = objectPop(calAttrs,storepath);
        
        objectPopAll(attributes);
        objectUpdate(attributes,boxAttrs);
        //var readOnly = objectPop(attributes,'readOnly');

        return {calAttrs:calAttrs,storepath:storepath};
    },

    created:function(widget, savedAttrs, sourceNode){
        var that = this;
        if(sourceNode.attr.storepath){
            sourceNode.attr.storepath = sourceNode.absDatapath(sourceNode.attr.storepath);
            sourceNode.registerDynAttr('storepath');
        }
        var cb = function(){
            setTimeout(function(){
                that.initialize(widget,savedAttrs.calAttrs);
            });
        }
        if(!window.FullCalendar){
            this.loadFullCalendar(cb);
        }else{
            cb();
        }
    },

    loadFullCalendar:function(cb){
        var urlist = ['/_rsrc/js_libs/fullcalendar/premium/main.min.css'];
        genro.dom.addHeaders(urlist,function(){
            genro.dom.loadJs('/_rsrc/js_libs/fullcalendar/premium/main.js',cb);
        });
    },

    initialize:function(domroot,calAttrs){
        //dojo.style(domroot,{position:'relative'})
        calAttrs.schedulerLicenseKey = genro._('gnr.api_keys.fullcalendar?schedulerLicenseKey');
        var that = this;
        calAttrs.eventSources = [function(info,successCallback,failureCallback){
            return that.readEventStore(domroot.sourceNode,info,successCallback,failureCallback);
        }]
        var calendar = new FullCalendar.Calendar(domroot,calAttrs);
        //dojo.style(domroot.firstChild,{height:'inherit',top:0,left:0,right:0,bottom:0,position:'absolute'})

        calendar.render();
        calendar.sourceNode = domroot.sourceNode;
        calendar.gnr = this;
        calendar.sourceNode.externalWidget = calendar;
        for (var prop in this) {
            if (prop.indexOf('mixin_') == 0) {
                calendar[prop.replace('mixin_', '')] = this[prop];
            }
        }

        // Watch for visibility changes and update size when visible
        var sourceNode = calendar.sourceNode;
        sourceNode.watch('isVisible',function(){
            return genro.dom.isVisible(sourceNode);
        },function(){
            calendar.updateSize();
        });

        // Initial updateSize after a short delay to handle initial render issues
        setTimeout(function(){
            calendar.updateSize();
        }, 100);
    },

    mixin_gnr_storepath:function(value,kw, trigger_reason){        
        var calendar = this;
        this.sourceNode.delayedCall(function(){
            console.log('update')
            calendar.refetchEvents();
        }, 500,'updatingContent')    
    },
    
    readEventStore:function(sourceNode,info,successCallback,failureCallback){
        var store = sourceNode.getRelativeData(sourceNode.attr.storepath);
        var events= []
        if(!store){
            return
        }
        store.getNodes().forEach(function(n){
            let row = objectUpdate({},n.attr);
            let v = n.getValue();
            if(v){
                objectUpdate(row,v.asDict());
            }
            if(row.start && row.end){
                events.push(row);
            }
        });
        console.log('successCallback',events);
        successCallback(events);
        
    }
});

dojo.declare("gnr.widgets.qrscanner", gnr.widgets.baseHtml, {
    constructor: function(application) {
        this._domtag = 'video';
    },
    creating: function(attributes, sourceNode) {
        /* onDecodeError	Handler to be invoked on decoding errors. The default is QrScanner._onDecodeError.
            preferredCamera	Preference for the camera to be used. The preference can be either a device id as returned by listCameras or a facing mode specified as 'environment' or 'user'. The default is 'environment'. Note that there is no guarantee that the preference can actually be fulfilled.
            maxScansPerSecond	This option can be used to throttle the scans for less battery consumption. The default is 25. If supported by the browser, the scan rate is never higher than the camera's frame rate to avoid unnecessary duplicate scans on the same frame.
            calculateScanRegion	A method that determines a region to which scanning should be restricted as a performance improvement. This region can optionally also be scaled down before performing the scan as an additional performance improvement. The region is specified as x, y, width and height; the dimensions for the downscaled region as downScaledWidth and downScaledHeight. Note that the aspect ratio between width and height and downScaledWidth and downScaledHeight should remain the same. By default, the scan region is restricted to a centered square of two thirds of the video width or height, whichever is smaller, and scaled down to a 400x400 square.
            highlightScanRegion	Set this option to true for rendering an outline around the scan region on the video stream. This uses an absolutely positioned div that covers the scan region. This div can either be supplied as option overlay, see below, or automatically created and then accessed via qrScanner.$overlay. It can be freely styled via CSS, e.g. by setting an outline, border, background color, etc. See the demo for examples.
            highlightCodeOutline	Set this option to true for rendering an outline around detected QR codes. This uses an absolutely positioned div on which an SVG for rendering the outline will be placed. This div can either be supplied as option overlay, see below, or be accessed via qrScanner.$overlay. The SVG can be freely styled via CSS, e.g. by setting the fill color, stroke color, stroke width, etc. See the demo for examples. For more special needs, you can also use the cornerPoints directly, see below, for rendering an outline or the points yourself.
            overlay	A custom div that can be supplied for use for highlightScanRegion and highlightCodeOutline. The div should be a sibling of videoElem in the DOM. If this option is supplied, the default styles for highlightCodeOutline are not applied as the expectation is that the element already has some custom style applied to it.
            returnDetailedScanResult Enforce reporting detailed scan results, see below.
            */

        let scannerAttributes = objectExtract(attributes,'onDecodeError,preferredCamera,maxScansPerSecond,calculateScanRegion,highlightScanRegion,highlightCodeOutline,returnDetailedScanResult');
        scannerAttributes.highlightCodeOutline = scannerAttributes.highlightCodeOutline!==false;
        scannerAttributes.highlightScanRegion = scannerAttributes.highlightScanRegion!==false;
        return {scannerAttributes:scannerAttributes}

    },
    created:function(widget, savedAttrs, sourceNode){
        var that = this;
        var scannerAttributes = objectPop(savedAttrs,'scannerAttributes');

        if(!genro.QrScanner){
            import('/_rsrc/js_libs/qr-scanner/qr-scanner.min.js').then((module) => {
                genro.QrScanner = module.default;
                that.initialize(widget,scannerAttributes,sourceNode);
            });
        }else{
            this.initialize(widget,scannerAttributes,sourceNode);
        }
    },

    initialize:function(widget,scannerAttributes,sourceNode){
        widget._scanner = new genro.QrScanner(
            widget,
            result => {
                        sourceNode.setRelativeData(sourceNode.attr.value,result?result.data:null);
                        if(result.data){
                            genro.playSound('ping');
                        }
                      },
            scannerAttributes
        );
        if(sourceNode.attr.autoStart!==false){
            widget._scanner.start();
        }
    },
    mixin_gnr_start:function(){
        this._scanner.start();
    },
    mixin_gnr_stop:function(){
        this._scanner.stop();
    },

    mixin_gnr_toggle:function(){
        if(this._scanner._active){
            this._scanner.stop();
        }else{
            this._scanner.start();
        }
    },
    
    mixin_gnr_value:function(){
        //console.log('aaa')
    }
});


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

    normalizeMarkdown:function(md){
        if (!md) return '';
        // Normalize whitespace and common markdown variations
        return md
            .replace(/\r\n/g, '\n')  // Normalize line endings
            .replace(/\n{3,}/g, '\n\n')  // Normalize multiple blank lines
            .trim();
    },

    attachHooks:function(editor, editor_attrs, sourceNode){
        // Flag to prevent false positives during initial load
        let changeListenerActive = false;

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
                sourceNode._mdOriginalMarkdown = this.normalizeMarkdown(editor.getMarkdown());
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

            const currentNormalized = this.normalizeMarkdown(editor.getMarkdown());

            // Only save if content actually changed
            if (currentNormalized !== sourceNode._mdOriginalMarkdown) {
                console.log('[MDEditor] Content changed, saving to datastore');
                this.setInDatastore(editor, sourceNode);
                sourceNode._mdOriginalMarkdown = currentNormalized;
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
                    this.gnr_loadMarkdown(text);
                    return;
                }
                // Bare Bag without keys: use root value as scalar
                if (typeof b.getValue === 'function'){
                    this.gnr_loadMarkdown(String(b.getValue() || ''));
                    return;
                }
            }
            if (hasHtml && b instanceof gnr.GnrBag && typeof b.getValue === 'function'){
                this.gnr_loadMarkdown(String(b.getValue() || ''));
                return;
            }
        }
        // Fallback scalar
        this.gnr_loadMarkdown(value || '');
    },

    mixin_gnr_loadMarkdown:function(markdown){
        this.setMarkdown(markdown, false);
        if(!this.options.viewer){
            this.sourceNode._mdOriginalMarkdown = this.gnr.normalizeMarkdown(this.getMarkdown());
        }
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

dojo.declare("gnr.widgets.chartjs", gnr.widgets.baseHtml, {
    constructor: function(application) {
        this._domtag = 'canvas';
    },


    creating: function(attributes, sourceNode) {
        sourceNode.registerDynAttr('storepath');
        var savedAttrs = objectExtract(attributes,'chartType,filter,datasets,captionField,options,data,scalesBag,onClick');
        return savedAttrs;
    },
    

    created:function(domNode, savedAttrs, sourceNode){
        //var chartjs_root = document.createElement('canvas');
        //domNode.appendChild(chartjs_root);
        var data = savedAttrs.data;
        var dataset = savedAttrs.dataset;
        var filter = savedAttrs.filter;
        var captionField = savedAttrs.captionField;
        var options = savedAttrs.options || {maintainAspectRatio:false};
        if(savedAttrs.onClick){
            options.onClick = funcCreate(savedAttrs.onClick,'event,elements',sourceNode);
        }
        var chartType = savedAttrs.chartType;
        var scalesBag = savedAttrs.scalesBag;
        var scalesOpt;
        var that = this;
        dojo.connect(sourceNode,'_onDeleting',function(){
            //Chart.helpers.removeResizeListener(sourceNode.domNode);
            //sourceNode.externalWidget.destroy();
        });
        if(scalesBag){
            if(scalesBag){
                scalesOpt = scalesBag.asDict(true,true);
                objectPop(scalesOpt,'radiant'); //to implement
                if(objectNotEmpty(scalesOpt)){
                    options.scales = scalesOpt;
                }else{
                    scalesOpt = false;
                }
                
            }
        }
        sourceNode.freeze();
        var cb = function(){
            sourceNode.unfreeze(true);
            var chartjs = new Chart(domNode,{'type':chartType,options:options});
            sourceNode.externalWidget = chartjs;
            chartjs.sourceNode = sourceNode;
            chartjs.gnr = that;
            for (var prop in that) {
                if (prop.indexOf('mixin_') === 0) {
                    chartjs[prop.replace('mixin_', '')] = that[prop];
                }
            }
            sourceNode.publish('chartReady');
            if(sourceNode.attr.optionsBag){
                var optionsBag = sourceNode.getAttributeFromDatasource('optionsBag');
                if(optionsBag && optionsBag.getNodeByAttr('_userChanges')){
                    optionsBag.walk(function(n){
                        if(n.attr._userChanges){
                            n.setValue(n._value);
                        }
                    });
                }else{
                    sourceNode.setAttributeInDatasource('optionsBag',new gnr.GnrBag(chartjs.options));
                }
                if(!scalesOpt){
                    sourceNode.setAttributeInDatasource('scalesBag',new gnr.GnrBag(chartjs.options.scales));
                }
            }
            chartjs.gnr_updateChart();
        };
        if(!window.Chart){
            //var url = '/_rsrc/js_libs/Chart.min.js'; 
            var url ='/_rsrc/js_libs/Chart.js';
            genro.dom.loadJs(url,function(){
                genro.setData('gnr.chartjs.defaults',new gnr.GnrBag(Chart.defaults));
                cb();
            });
        }else{
            setTimeout(cb,1);
        }
    },
    autoColors:function(dataset){
        var colorParNames = ['backgroundColor:0.7','borderColor:1',
                            'pointBackgroundColor:1','pointBorderColor:1'];
        var result = {};
        colorParNames.forEach(function(n){
            n = n.split(':'); 
            if(dataset[n[0]]=='*'){
                dataset[n[0]] = [];
                result[n[0]] = n[1];
            }
        });
        return result;
    },

    makeDataset:function(kw){
        var field = objectPop(kw,'field');

        var dataset = objectUpdate({data:[]},kw.pars);
        var autoColorsDict = this.autoColors(dataset);
        objectPop(dataset,'enabled');
        var idx = 0;
        var k;
        var caption;
        var isBagMode = kw.datamode=='bag';
        kw.rows.walk(function(n){
            if('pageIdx' in n.attr){return;}
            var row = isBagMode?n.getValue('static').asDict() : n.attr;
            var pkey = row._pkey || n.label;
            if(kw.filterCb(pkey,row)){
                var chart_row_pars = objectExtract(row,'chart_*');
                caption = row[kw.captionField] || (dataset.label || field)+' '+idx;
                if('labels' in kw){
                    kw.labels.push(caption);
                }
                dataset.data.push(row[field]);
                var autocol = chroma(stringToColour(caption));
                for(k in autoColorsDict){
                    dataset[k].push(chroma(autocol).alpha(autoColorsDict[k]).css());
                }
                for(k in chart_row_pars){
                    if(isNullOrBlank(dataset[k])){
                        dataset[k] = [];
                    }
                    if(dataset[k] instanceof Array){
                        dataset[k].push(chart_row_pars[k]);
                    }
                    
                }
                idx++;
            }
            return '__continue__';
        },'static',null,isBagMode);
        return dataset;
    },

    mixin_gnr_updateChart:function(){
        if(this.sourceNode.isFreezed()){
            return;
        }
        var that = this;
        this.sourceNode.delayedCall(function(){
            var data = that.sourceNode.getAttributeFromDatasource('data'); 
            if(!data){
                var rows = that.sourceNode.getRelativeData(that.sourceNode.attr.storepath); 
                var filter = that.sourceNode.getAttributeFromDatasource('filter'); 
                var datasets = that.sourceNode.getAttributeFromDatasource('datasets'); 
                var captionField = that.sourceNode.getAttributeFromDatasource('captionField');
                var filterCb;
                if(typeof(filter)=='string'){
                    filter = filter.split(',');
                }
                if(typeof(filter)!='function'){
                    filterCb = filter?function(pkey,row){return filter.length===0 ||filter.indexOf(pkey)>=0;}:function(){return true;};
                }else{
                    filterCb = filter;
                }
                var attrs,dslabel,dsfield;
                var datamode = that.sourceNode.attr.datamode || 'attr';
                data = {labels:[],datasets:[]};
                var dskw = {'rows':rows,'datamode':datamode,
                            'filterCb':filterCb,'labels':data.labels,
                            'captionField':captionField};
                if(datasets){
                    datasets._nodes.forEach(function(n){
                        var v = n.getValue();
                        if(!(v.getNode('enabled')) || v.getItem('enabled')){
                            dskw.pars = v.getItem('parameters').asDict(true,true);
                            dskw.pars.type = v.getItem('chartType');
                            dskw.field = v.getItem('field');
                            data.datasets.push(that.gnr.makeDataset(dskw));
                            objectPop(dskw,'labels');
                        }
                    });
                }
            }         
            objectUpdate(that.data,data);
            that.update();
            that.resize();
        },1,'updateChart');
        
    },
    
    mixin_gnr_storepath:function(value,kw, trigger_reason){  
        this.gnr_updateChart();
    },
    
    mixin_gnr_chartType:function(value,kw, trigger_reason){  
        //this.config.type = this.sourceNode.getAttributeFromDatasource('chartType');
        //this.gnr_updateChart();
        if(this.sourceNode.isFreezed()){
            return;
        }
        this.sourceNode.rebuild();
        
    },

    mixin_gnr_datasets:function(value,kw, trigger_reason){ 
        if(kw.node.label == 'xAxisID' || kw.node.label=='yAxisID'){
            var axes = kw.node.label=='xAxisID'?'xAxes':'yAxes';
            var axeslist = this.options.scales[axes];
            if(!axeslist.some(function(n){return n.id==value;})){
                this.sourceNode.publish('addAxis',{axes:axes,id:kw.value});
                return;
            }
        }
        this.gnr_updateChart();
    },

    mixin_gnr_filter:function(value,kw, trigger_reason){  
        this.gnr_updateChart();
    },

    mixin_gnr_captionField:function(value,kw, trigger_reason){  
        this.gnr_updateChart();
    },
    mixin_gnr_scalesBag:function(value,kw, trigger_reason){ 
        var scalesBag = this.sourceNode.getAttributeFromDatasource('scalesBag');
        if(kw.node._id == scalesBag.getParentNode()._id){
            return;
        }
        this.gnr_updateOptionsObject(kw.node,this.options.scales,scalesBag);
    },
    mixin_gnr_optionsBag:function(value,kw, trigger_reason){ 
        var optionsBag = this.sourceNode.getAttributeFromDatasource('optionsBag');
        if(kw.node._id == optionsBag.getParentNode()._id){
            return;
        }
        this.gnr_updateOptionsObject(kw.node,this.options,optionsBag);
    },

    mixin_gnr_updateOptionsObject:function(triggerNode,curr,optionsBagChunk){
        var optpath = triggerNode.getFullpath(null,optionsBagChunk);
        var currOptionBag = optionsBagChunk;
        var node,val;
        var optlist = ((typeof optpath === 'string') ? optpath : String(optpath || '')).split('.');
        var lastLabel = optlist.pop();
        var k;
        optlist.forEach(function(chunk){
            node = currOptionBag.getNode(chunk);
            if(node.attr._autolist){
                k = currOptionBag.index(chunk);
                if(isNullOrBlank(curr[k])){
                    curr[k] = {};
                }
                curr = curr[k];
            }else{
                if(!(chunk in curr)){
                    curr[chunk] = {};
                }
                curr = curr[chunk];
            }
            currOptionBag = node.getValue();
        });
        var lastValue = currOptionBag.getItem(lastLabel);
        lastValue = lastValue instanceof gnr.GnrBag?lastValue.asDict(true,true):lastValue;
        if(curr instanceof Array){
            var lastIdx = currOptionBag.index(lastLabel);
            if(curr.length>lastIdx){
                curr[lastIdx] = lastValue;
            }else{
                curr.push(lastValue);
            }
        }
        if(curr[lastLabel]!=lastValue){
            triggerNode.attr._userChanges = true;
            curr[lastLabel] = lastValue;
        }
        if(this.sourceNode.isFreezed()){
            return;
        }
        this.update();
        this.resize();
    }
});

dojo.declare("gnr.widgets.dygraph", gnr.widgets.baseHtml, {
    constructor: function(application) {
        this._domtag = 'div';
    },

    creating: function(attributes, sourceNode) {
        var savedAttrs = objectExtract(attributes,'data,options,columns');
        return savedAttrs;
    },

    created:function(domNode, savedAttrs, sourceNode){
        var dygraph_root = document.createElement('div');
        domNode.appendChild(dygraph_root);
        var data = savedAttrs.data;
        var options = savedAttrs.options;
        if(options instanceof gnr.GnrBag){
            options =  options.asDict(true);
        }
        if(sourceNode.attr.title){
            options.title = options.title || sourceNode.attr.title; 
        }
        if(sourceNode.attr.detachable){
            options.title = options.title || 'Untiled Graph';
        }
        if(data instanceof gnr.GnrBag){
            sourceNode.labelKeys = sourceNode.labelKeys || savedAttrs.columns.split(','); //during rebuilding
            data = this.getDataFromBag(sourceNode,data);
        }
        var that = this;

        var cb = function(){
            sourceNode._current_height = domNode.clientHeight;
            sourceNode._current_width = domNode.clientWidth;
            options.height = sourceNode._current_height;
            options.width = sourceNode._current_width;
            var dygraph = new Dygraph(dygraph_root,data,options);
            sourceNode.externalWidget = dygraph;
            dygraph.sourceNode = sourceNode;
            dygraph.gnr = that;
            for (var prop in that) {
                if (prop.indexOf('mixin_') === 0) {
                    dygraph[prop.replace('mixin_', '')] = that[prop];
                }
            }
            genro.dom.setAutoSizer(sourceNode,domNode,function(w,h){
                 dygraph.resize(w,h);
            });
        };
        if(!window.Dygraph){
            genro.dom.loadJs('/_rsrc/js_libs/dygraph-combined.js',cb);
        }else{
            setTimeout(cb,1);
        }
    },

    getDataFromBag:function(sourceNode,data){
        var result = [];
        var labelKeys = sourceNode.labelKeys;
        var datagetter = function(n,l){
            return n.attr[l];
        };
        if(data.getItem('#0')){
            datagetter = function(n,l){
                return n._value.getItem(l);
            };
        }
        data.forEach(function(n){
            var row = [];
            labelKeys.forEach(function(l){
                row.push(datagetter(n,l));
            });
            result.push(row);
        });
        return result;
    },

    mixin_gnr_columns:function(value,kw, trigger_reason){  
        this.sourceNode.labelKeys = (typeof value === 'string') ? value.split(',') : (Array.isArray(value) ? value : [String(value||'')]);
        this.sourceNode.rebuild();
    },
    
    mixin_gnr_data:function(value,kw, trigger_reason){  
        var data = this.sourceNode.getAttributeFromDatasource('data');      
        if(data instanceof gnr.GnrBag){
            data = this.gnr.getDataFromBag(this.sourceNode,data);
        }
        this.updateOptions({ 'file': data });
    },

    mixin_gnr_options:function(options,kw, trigger_reason){   
        options = this.sourceNode.getAttributeFromDatasource('options');      
        if(options instanceof gnr.GnrBag){
            options = options.asDict(true);
        }    
        this.updateOptions(options);
    }
});


