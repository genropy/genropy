const  GoogleTypeConverter = {'A':'string','T':'string','C':'string',
                                'B':'boolean','D':'date','DH':'datetime',
                                'N':'number','R':'number','L':'number','I':'number'}

const dataTableFromBag = function(data,columns,datamode){
    if(!datamode){
        datamode = data.getItem('#0')?'bag':'attr';
    }
    if(!columns){
        let firstNode = data.getNode('#0');
        var columns;
        if(datamode=='bag'){
            columns = firstNode.getValue().getNodes().map(n => {
                let dtype = guessDtype(n.getValue())
                return {'type':GoogleTypeConverter[dtype] || 'string','label':n.label,'field':n.label};
            });
        }else{
            columns = [];
            for(let key in firstNode.attr){
                let dtype = guessDtype(firstNode.attr[key]);
                columns.push({'type':GoogleTypeConverter[dtype] || 'string','label':key,'field':key});
            }
        }
    }
    let result = new google.visualization.DataTable();
    for(let c of columns){
        result.addColumn(c.type, c.label);
    }
    result.addRows(data.getNodes().map(n => {
        let r = [];
        let rowSource = datamode=='bag'?n.getValue().asDict():n.attr;
        for(let c of columns){
            r.push(rowSource[c.field]);
        }
        return r;
    }));
    return result;
};

const hierarchicalDataTableFromBag = function(data){
    let result = new google.visualization.DataTable();
    result.addColumn('string', 'Caption');
    result.addColumn('string', 'Parent');
    result.addRows(data.getIndex().map(l=>{
        return [{v:l[0].join('.'),f:l[1].attr.label},l[0].slice(0,-1).join('.')]
    }));
    return result;

};

const dataTableFromGrid = function(grid,given_columns){
    if(typeof(grid)=='string'){
        grid = genro.wdgById(grid);
    }
    let data = grid.storebag();
    let struct = grid.structbag();   
    var columns = [];
    var cells = struct.getItem('view_0.rows_0');
    if(given_columns){
        columns = given_columns.map(c=>{
            let result = {...c};
            let cell = cells.getNodeByAttr('field',c.field).attr;
            if(!result.type){
                result.type = GoogleTypeConverter[cell.dtype] || 'string';
            }
            result.label = result.label || cell.name || result.field;
            return result;
        });
    }else{
        columns = cells.getNodes().map(n => {
            return {'type':GoogleTypeConverter[n.attr.dtype] || 'string','label':n.attr.name || n.attr.field,'field':n.attr.field_getter || n.attr.field};
        });
    }
    return dataTableFromBag(data,columns)
};

dojo.declare("gnr.widgets.GoogleChart", gnr.widgets.baseHtml, {
    constructor: function(application) {
        this._domtag = 'div';
    },
    creating: function(attributes, sourceNode) {
        let chartAttributes = objectExtract(attributes,'chart_*',true);
        objectUpdate(chartAttributes,objectExtract(attributes,'title'))
        attributes.id = attributes.nodeId || 'gchart_'+genro.getCounter();
        let connectedGrid = objectPop(attributes,'grid');
        let columns = attributes.columns;
        sourceNode.attr._workspace = true;
        if(columns && typeof(columns)!='string'){
            let columnsBag = columns;
            if(!(columns instanceof gnr.GnrBag)){
                columnsBag = new gnr.GnrBag();
                columns.forEach((c,idx)=>{
                    columnsBag.addItem('r_'+idx,null,c);
                });
            }
            attributes.columns = '^#WORKSPACE.columns';
            sourceNode.setRelativeData('#WORKSPACE.columns',columnsBag);
            sourceNode.attr.columns = attributes.columns;
        }
        sourceNode._connectedGrid = connectedGrid;
        sourceNode.attr.chartAttributes = chartAttributes;
        attributes.containerId = attributes.id;
        sourceNode.attr.containerId = attributes.containerId;
        this._prepareDynamicAttribute(sourceNode,attributes,'storepath',connectedGrid)
        this._prepareDynamicAttribute(sourceNode,attributes,'structpath',connectedGrid)
        return {chartAttributes:chartAttributes}
    },
    created:function(widget, savedAttrs, sourceNode){
        var that = this;
        var chartAttributes = objectPop(savedAttrs,'chartAttributes');
        if(!genro.googlechart){
            genro.dom.loadJs('https://www.gstatic.com/charts/loader.js',() => {
                google.charts.load('current', {'packages':['corechart']});
                google.charts.setOnLoadCallback(()=>that.initialize(widget,chartAttributes,sourceNode));
            });
        }else{
            this.initialize(widget,chartAttributes,sourceNode);
        }
    },

    initialize:function(widget,chartAttributes,sourceNode){
        sourceNode._chartWrapper = new google.visualization.ChartWrapper({
            chartType: sourceNode.attr.chartType,
            dataTable: this.getDataTable(sourceNode),
            options: this.getOptions(sourceNode),
            containerId: sourceNode.attr.containerId
          });
        sourceNode._chartWrapper.draw();
    },

    _prepareDynamicAttribute:function(sourceNode,attributes,attribute,externalWidgetNode){
        let path = externalWidgetNode? externalWidgetNode.absDatapath(externalWidgetNode.attr[attribute]):sourceNode.absDatapath(attributes[attribute]);
        attributes[attribute] = path;
        sourceNode.attr[attribute] = path;
        sourceNode.registerDynAttr(attribute);
    },

    getOptions:function(sourceNode){
        let result = sourceNode.evaluateOnNode(sourceNode.attr.chartAttributes);
        return result;
    },

    getStruct:function(sourceNode, path){
        let structpath = sourceNode.getAttributeFromDatasource('structpath') || '.struct';
        let structbag = sourceNode.getRelativeData(structpath) || new gnr.GnrBag();
        if(path){
            return structbag.getItem(path);
        }
        return structbag;
    },

    getColumns:function(sourceNode,path){
        let columns = sourceNode.getAttributeFromDatasource('columns');
        if(!columns){
            columns = this.getStruct(sourceNode,"columns");
        }
        if(columns instanceof gnr.GnrBag){
            return columns.getNodes().map((n)=>{
                return {'type':GoogleTypeConverter[n.attr.dtype] || 'string',
                         'label':n.attr.name || n.attr.field,
                         'field':n.attr.field_getter || n.attr.field};
            });
        }
        return columns;
    },

    getDataTable:function(sourceNode){
        let columns = this.getColumns(sourceNode);
        if(sourceNode._connectedGrid){
            return dataTableFromGrid(sourceNode._connectedGrid.widget,columns);
        }
        if(sourceNode.attr.chartType=='OrgChart'){
            return hierarchicalDataTableFromBag(sourceNode.getRelativeData(sourceNode.attr.storepath));
        }
        return dataTableFromBag(sourceNode.getRelativeData(sourceNode.attr.storepath),columns);
    },

    mixin_gnr_getDataTable:function(){
        this.gnr.getDataTable(this.sourceNode);
    },

    mixin_gnr_refresh:function(){
        this.sourceNode._chartWrapper.dataTable = this.gnr_getDataTable();
        this.sourceNode._chartWrapper.draw();
    },

    mixin_gnr_storepath:function(value){
        this.gnr_refresh();
    },

    mixin_gnr_columns:function(value){
        this.gnr_refresh();
    },

    mixin_gnr_structpath:function(value){
        this.gnr_refresh();
    },
});