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


