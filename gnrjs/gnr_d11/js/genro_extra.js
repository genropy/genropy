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
        if(!events.length){
            events = [{title:'Prova',start:new Date()}]
        }
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
        let value = objectPop(editorAttrs,'value');
        if(value){
            editorAttrs.initialValue = value;
        }
        editorAttrs.usageStatistics = objectPop(editorAttrs,'usageStatistics') || false; //usageStatistics is false by default
        objectPopAll(attributes);
        return editorAttrs;
    },

    created:function(widget, savedAttrs, sourceNode){
        const scriptUrl = "https://uicdn.toast.com/editor/latest/toastui-editor-all.min.js";
        const cssUrl = "https://uicdn.toast.com/editor/latest/toastui-editor.min.css";
    
        const loadResource = (url, type) => {
            return new Promise((resolve, reject) => {
                if (type === 'js') {
                    genro.dom.loadJs(url, resolve);
                } else if (type === 'css') {
                    genro.dom.loadCss(url, 'tuieditor', resolve);
                }
            });
        };
    
        if (!(window.toastui && window.toastui.Editor)) {
            Promise.all([
                loadResource(scriptUrl, 'js'),
                loadResource(cssUrl, 'css')
            ]).then(() => {
                this.ready = true;
                this.initialize(widget, savedAttrs, sourceNode);
            });
        } else {
            this.ready = true;
            this.initialize(widget, savedAttrs, sourceNode);
        }
    },

    initialize:function(widget, savedAttrs, sourceNode){
        let editor_attrs = {...savedAttrs};
        objectPop(editor_attrs,'htmlpath');
        const editor = editor_attrs.viewer
            ? this.createViewer(widget, editor_attrs)
            : this.createEditor(widget, editor_attrs);
    
        this.configureToolbar(editor, editor_attrs);
        this.setExternalWidget(sourceNode, editor);
        this.attachHooks(editor, editor_attrs, sourceNode);
    },
    
    createViewer:function(widget, editor_attrs){
        editor_attrs.autofocus = true;
        return window.toastui.Editor.factory({
            el: widget,
            ...editor_attrs
        });
    },
    
    createEditor:function(widget, editor_attrs){
        editor_attrs.autofocus = editor_attrs.autofocus || false;
        return new window.toastui.Editor({
            el: widget,
            ...editor_attrs
        });
    },

    configureToolbar:function(editor, editor_attrs){
        if(editor_attrs.removeToolbarItems){
            editor_attrs.removeToolbarItems.forEach(item => editor.removeToolbarItem(item));
        }
        if(editor_attrs.insertToolbarItems){
            editor_attrs.insertToolbarItems.forEach(item => editor.insertToolbarItem(item));
        }
    },

    attachHooks:function(editor, editor_attrs, sourceNode){
    // Usa il metodo ufficiale di Toast UI Editor per intercettare la perdita del focus
        editor.on('blur', () => {
            //console.log("📌 [DEBUG] Focus perso, salvo nel datastore...");
            this.setInDatastore(editor, sourceNode);
        });

        // Se serve gestire anche quando prende focus
        editor.on('focus', () => {
            //console.log("📌 [DEBUG] Editor ha preso il focus.");
        });

        // Mantieni la gestione della lunghezza massima su keydown se necessario
        editor.addHook('keydown', () => {
            genro.callAfter(() => {
                if (editor_attrs.maxLength) {
                    this.checkMaxLength(editor, editor_attrs.maxLength);
                }
            }, 10, this, 'typing');
        });
    },

    checkMaxLength:function(editor, maxLength){
        let value = editor.getMarkdown();
        if (value.length > maxLength) {
            editor.setMarkdown(value);
        }
        // Aggiorna il conteggio dei caratteri nella toolbar
        editor.removeToolbarItem('remaining');
        editor.insertToolbarItem({ groupIndex: -1, itemIndex: -1 }, {
            name: 'remaining',
            tooltip: 'Remaining characters',
            text: `Remaining: ${(maxLength - value.length)}`,
            style: { textAlign: 'right', fontStyle: 'italic', fontSize: '.8em', cursor: 'auto', width: '75px', textAlign: 'center'}
        });
    },
    
    onTyped:function(editor){
        // Logica di callback per la digitazione
    },
    
    setInDatastore:function(editor, sourceNode){
        let value = editor.getMarkdown();
        let currentValue = sourceNode.getAttributeFromDatasource('value');
    
        // Aggiorna il datastore SOLO se il valore è cambiato
        if (currentValue !== value) {
            sourceNode.setAttributeInDatasource('value', value || null);
            const htmlpath = sourceNode.attr.htmlpath;
            if (htmlpath) {
                sourceNode.setRelativeData(htmlpath, editor.getHTML());
            }
        }
    },
    
    mixin_gnr_value:function(value,kw, trigger_reason){    
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

dojo.declare("gnr.widgets.codemirror", gnr.widgets.baseHtml, {
    constructor: function(application) {
        this._domtag = 'div';
    },
    getAddOnDict:function(key){
        return {
            search:{
                command:'find',
                js:['addon/search/search.js','addon/search/searchcursor.js','addon/dialog/dialog.js'],
                css:['addon/dialog/dialog.css'],
            },lint:{
                command:'lint',
                js:['//ajax.aspnetcdn.com/ajax/jshint/r07/jshint.js','addon/lint/lint.js','addon/lint/javascript-lint.js'],
                css:['addon/lint/lint.css'],
            }
        }[key];
    },
    creating: function(attributes, sourceNode) {
        //if (sourceNode.attr.storepath) {
        //    sourceNode.registerDynAttr('storepath');
        //}
        var cmAttrs = objectExtract(attributes,'config_*');
        var readOnly = objectPop(attributes,'readOnly');
        var lineWrapping = objectPop(attributes,'lineWrapping');

        if(readOnly){
            cmAttrs.readOnly = readOnly;
        }
        if(lineWrapping){
            cmAttrs.lineWrapping = lineWrapping;
        }
        cmAttrs.value = objectPop(attributes,'value') || '';
        return {cmAttrs:cmAttrs}
    },

    created:function(widget, savedAttrs, sourceNode){
        var that = this;
        var cmAttrs = objectPop(savedAttrs,'cmAttrs');
        var mode = cmAttrs.mode;
        var theme = cmAttrs.theme;
        var addon = cmAttrs.addon;
        if(addon){
            addon = addon.split(',');
        }

        var cb = function(){
            that.load_mode(mode,function(){
                if(theme){
                    that.load_theme(theme,function(){that.initialize(widget,cmAttrs,sourceNode)})
                }
                else{
                    that.initialize(widget,cmAttrs,sourceNode);
                }
             });
            if(addon){
                addon.forEach(function(addon){
                    that.load_addon(addon)
                })
            }
        }
        if(!window.CodeMirror){
            this.loadCodeMirror(cb);
        }else{
            cb();
        }
    },

    loadCodeMirror:function(cb){
        var urlist = ['/_rsrc/js_libs/codemirror/lib/codemirror.js',
                    '/_rsrc/js_libs/codemirror/lib/codemirror.css'];
        genro.dom.addHeaders(urlist,function(){
            genro.dom.loadJs('/_rsrc/js_libs/codemirror/addon/mode/overlay.js',cb);
        });
        
    },
    defineKeyMap:function(name,keyMap){
        CodeMirror.keyMap[name] = objectUpdate(keyMap,CodeMirror.keyMap['default']);
    },


    initialize:function(widget,cmAttrs,sourceNode){
        this.defineKeyMap('softTab',{'Tab':function(cm){
                                          var spaces = Array(cm.getOption("indentUnit") + 1).join(" ");
                                          cm.replaceSelection(spaces);
                                      }
                                });
        dojo.style(widget,{position:'relative'})
        var cm = CodeMirror(widget,cmAttrs);
        dojo.style(widget.firstChild,{height:'inherit',top:0,left:0,right:0,bottom:0,position:'absolute'})
        cm.refresh();
        cm.sourceNode = sourceNode;
        cm.gnr = this;
        sourceNode.externalWidget = cm;
        for (var prop in this) {
            if (prop.indexOf('mixin_') == 0) {
                cm[prop.replace('mixin_', '')] = this[prop];
            }
        }
        cm.on('update',function(){
            sourceNode.delayedCall(function(){
                var v = sourceNode.externalWidget.getValue();
                if(sourceNode.attr.value){
                    sourceNode.setRelativeData(sourceNode.attr.value,v,null,null,sourceNode);
                }
            },sourceNode.attr._delay || 500,'updatingContent')
        })
        let startValue = sourceNode.getAttributeFromDatasource('value');
        cm.setValue(startValue || '');
    },


    load_theme:function(theme,cb){
        genro.dom.loadCss('/_rsrc/js_libs/codemirror/theme/'+theme+'.css','codemirror_'+theme,cb);
    },

    load_addon:function(addon,cb){
        var that = this;
        var addondict = this.getAddOnDict(addon);
        if (!CodeMirror.commands[addondict.command]){
            addondict.js.forEach(function(path){
                if(path[0]=='/'){
                    genro.dom.loadJs(path);
                }else{
                    genro.dom.loadJs('/_rsrc/js_libs/codemirror/'+path);
                }
                 
            })
            addondict.css.forEach(function(path){
                 genro.dom.loadCss('/_rsrc/js_libs/codemirror/'+path);
            })
        }
    },

    load_mode:function(mode,cb){
        var that = this;
        if (!(mode in CodeMirror.modes)){
            genro.dom.loadJs('/_rsrc/js_libs/codemirror/mode/'+mode+'/'+mode+'.js',function(){
                if(CodeMirror.modes[mode].dependencies){
                    var i =0;
                    CodeMirror.modes[mode].dependencies.forEach(function(dep){
                        i++;
                        if(CodeMirror.modes[mode].dependencies.length==i){
                            that.load_mode(dep,function(){
                                setTimeout(function(){cb()},10);
                            });
                        }else{
                            that.load_mode(dep);
                        }
                    });
                }
                else if(cb){
                    cb()
                }
            });
        }
        else if(cb){
            cb();
        }
    },

    mixin_gnr_value:function(value,kw, trigger_reason){        
        this.setValue(value || '');
        var that = this;
        var sourceNode = this.sourceNode;

        sourceNode.watch('isVisible',function(){
            return genro.dom.isVisible(sourceNode);
        },function(){
            that.refresh();
        });
    },


    mixin_gnr_setDisabled:function(disabled){
        genro.dom.setDomNodeDisabled(this.sourceNode.domNode,disabled);
        this.gnr_readOnly(disabled);
    },

    mixin_gnr_readOnly:function(value,kw,trigger_reason){
        this.setOption('readOnly',value?'nocursor':false);
    },

    mixin_gnr_lineWrapping:function(value,kw,trigger_reason){
        this.setOption('lineWrapping',value);
    },


    mixin_gnr_quoteSelection:function(startchunk,endchunk){
        endchunk = endchunk || startchunk;
        var oldtxt = this.doc.getSelection();
        var newtxt = startchunk+oldtxt+endchunk;
        this.doc.replaceSelection(newtxt);
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
        var optlist = optpath.split('.');
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
        this.sourceNode.labelKeys = value.split(',');
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
    }

});


dojo.declare("gnr.widgets.TinyMCE", gnr.widgets.baseHtml, {
  constructor: function(application) {
    this._domtag = 'textarea';
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
    const imageDataRaw = objectPop(attributes,'imageData');
    const imageData = (imageDataRaw === true || imageDataRaw === 'true' || imageDataRaw === 1 || imageDataRaw === '1');
    const rawUploadPath = objectPop(attributes,'uploadPath');
    const uploadPath = rawUploadPath || 'site:uploaded_files';
    if (imageData && rawUploadPath){
      throw new Error('TinyMCE widget: imageData=True is mutually exclusive with uploadPath');
    }
    attributes.id = textareaId;
    attributes.style = `height:${height};width:${width};`;
    return {valuePath, textPath, textareaId, placeholderItems, base_url, content_style, plugins, removeToolbarItems, imageData, uploadPath, onUploadedMethod, rpcKw, _rawHeight: height, _rawWidth: width};
  },

  created: function(domNode, savedAttrs, sourceNode){
    var widgetObj = this;
    // Widget created, defer editor initialization until node is visible
    var initialized = false;
    var that = this;
    function initIfVisible() {
        if (initialized) { return; }
        if (genro.dom.isVisible(sourceNode)) {
            initialized = true;
            // Initialize TinyMCE editor once the node is visible
            that.makeEditor(domNode, savedAttrs, sourceNode);
        } else {
            genro.callAfter(initIfVisible, 300, that, 'tinymce_wait_'+savedAttrs.textareaId);
        }
    }
    sourceNode.subscribe('onShow', function() {
        if (!initialized) {
            initialized = true;
            that.makeEditor(domNode, savedAttrs, sourceNode);
        }
    });
    if (!window.tinymce){
      genro.dom.loadJs(savedAttrs.base_url + '/tinymce.min.js', function(){
        initIfVisible();
      });
    } else {
      initIfVisible();
    }
    // Cleanup on widget deletion
    dojo.connect(sourceNode,'_onDeleting',function(){
      if (window.tinymce){ try{ tinymce.remove('#' + savedAttrs.textareaId); }catch(e){} }
    });
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
    // Initialize TinyMCE with toolbar and plugins
    const defaultToolbarLines = [
      'undo redo | bold italic underline | bullist numlist | alignleft aligncenter alignright alignjustify',
      savedAttrs.placeholderItems && savedAttrs.placeholderItems.length ?
        '| link image table | code | placeholders' :
        '| link image table | code'
    ];
    const removeSet = new Set(savedAttrs.removeToolbarItems || []);
    const toolbar = defaultToolbarLines
      .map(line => line.split(' ').filter(tok => !removeSet.has(tok)).join(' '))
      .join(' ');
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
