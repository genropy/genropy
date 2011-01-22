//GNRWDG WIDGET DEFINITION BASE
dojo.declare("gnr.widgets.gnrwdg", null, {
    constructor: function(application) {
        this._domtag = 'div';
    },
    _beforeCreation: function(sourceNode) {
        sourceNode.gnrwdg = {'gnr':this,'sourceNode':sourceNode};
        var attributes = objectUpdate({}, sourceNode.attr);
        objectExtract(sourceNode.attr, 'nodeId');
        var contentKwargs = this.contentKwargs(sourceNode, attributes);
        if (!this.createContent) {
            return false;
        }
        sourceNode.freeze();
        var children = sourceNode.getValue();
        sourceNode.clearValue();
        var content = this.createContent(sourceNode, contentKwargs,children);
        content.concat(children);
        sourceNode._stripData();
        sourceNode.unfreeze(true);
        return false;
    },
    onStructChild:function(attributes) {
        if (!attributes.datapath) {
            var defaultDatapath = this.defaultDatapath(attributes);
            if (defaultDatapath) {
                attributes.datapath = defaultDatapath;
            }
        }

    },
    contentKwargs: function(sourceNode, attributes) {
        return attributes;
    },
    defaultDatapath:function(attributes) {
        return null;
    }
});

dojo.declare("gnr.widgets.Palette", gnr.widgets.gnrwdg, {
    contentKwargs: function(sourceNode, attributes) {
        var left = objectPop(attributes, 'left');
        var right = objectPop(attributes, 'right');
        var top = objectPop(attributes, 'top');
        var bottom = objectPop(attributes, 'bottom');
        if ((left === null) && (right === null) && (top === null) && (bottom === null)) {
            this._last_floating = this._last_floating || {top:0,right:0};
            this._last_floating['top'] += 10;
            this._last_floating['right'] += 10;
            top = this._last_floating['top'] + 'px';
            right = this._last_floating['right'] + 'px';
        }
        var dockTo = objectPop(attributes, 'dockTo');
        var floating_kwargs = objectUpdate(attributes, {dockable:true,closable:false,visibility:'hidden'});
        var showOnStart = false;
        if (dockTo === false) {
            floating_kwargs.closable = true;
            floating_kwargs.dockable = false;
            showOnStart = true;
        } else if (dockTo && dockTo.indexOf(':open') >= 0) {
            dockTo = dockTo.split(':')[0];
            objectPop(floating_kwargs, 'visibility');
            showOnStart = true;
        }
        if (showOnStart) {
            floating_kwargs.onCreated = function(widget) {
                setTimeout(function() {
                    widget.show();
                    widget.bringToTop();
                }, 1);
            };
        }
        if (!dockTo && dockTo !== false) {
            dockTo = 'default_dock';
        }
        if (dockTo) {
            floating_kwargs.dockTo = dockTo;
        }
        return objectUpdate({height:'400px',width:'300px',
            top:top,right:right,left:left,bottom:bottom,
            resizable:true}, floating_kwargs);
    },
    createContent:function(sourceNode, kw) {
        if (kw.dockTo == '*') {
            var dockId = sourceNode._id + '_dock';
            sourceNode._('dock', {id:dockId});
            kw.dockTo = dockId;
        }
        if (kw.nodeId) {
            kw.connect_show = function() {
                genro.publish(kw.nodeId + '_showing');
            };
            kw.connect_hide = function() {
                genro.publish(kw.nodeId + '_hiding');
            };
        }
        return sourceNode._('floatingPane', kw);
    }
});


dojo.declare("gnr.widgets.PalettePane", gnr.widgets.gnrwdg, {
    contentKwargs: function(sourceNode, attributes) {
        var inattr = sourceNode.getInheritedAttributes();
        var groupCode = inattr.groupCode;
        attributes.nodeId = attributes.nodeId || 'palette_' + attributes.paletteCode;
        attributes._class = attributes._class || "basePalette";
        if (groupCode) {
            attributes.groupCode = groupCode;
            attributes.pageName = attributes.paletteCode;
        }
        return attributes;
    },

    defaultDatapath:function(attributes) {
        return  'gnr.palettes.' + attributes.paletteCode;
    },
    createContent:function(sourceNode, kw) {
        var paletteCode = objectPop(kw, 'paletteCode');
        var groupCode = objectPop(kw, 'groupCode');
        if (groupCode) {
            var pane = sourceNode._('ContentPane', objectExtract(kw, 'title,pageName'))._('ContentPane', objectUpdate({'detachable':true}, kw));
            var controller_kw = {'script':"SET gnr.palettes._groups.pagename." + groupCode + " = paletteCode;",
                'paletteCode':paletteCode}
            controller_kw['subscribe_show_palette_' + paletteCode] = true;
            pane._('dataController', controller_kw);
            return pane;
        } else {
            var palette_kwargs = objectExtract(kw, 'title,dockTo,top,left,right,bottom,maxable,height,width');
            palette_kwargs['nodeId'] = paletteCode + '_floating';
            palette_kwargs['title'] = palette_kwargs['title'] || 'Palette ' + paletteCode;
            objectUpdate(palette_kwargs, objectExtract(kw, 'palette_*'));
            palette_kwargs.selfsubscribe_showing = function() {
                genro.publish('palette_' + paletteCode + '_showing');
            }
            var floating = sourceNode._('palette', palette_kwargs);
            return floating._('ContentPane', kw);
        }
    }
});



dojo.declare("gnr.widgets.FramePane", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw,children) {
        var node;
        var bc = sourceNode._('BorderContainer', kw);
        dojo.forEach(['top','bottom','left','right'],function(side){
             node = children.popNode('#side='+side);
             if(node){
                 bc._('ContentPane',{'region':side}).setItem(node.label,node._value,
                                                                objectUpdate({'parentKw':kw},node.attr));
             }
        });
        var centerNode = children.popNode('#side=center');
        var center;
        if(centerNode){
            centerNode.attr['region'] = objectPop(centerNode.attr,'side');
            bc.setItem(centerNode.label,centerNode._value,centerNode.attr);
            center = centerNode._value;
        }else{
            center = bc._('ContentPane',{'region':'center'});
        }
        return center;
    }
});

dojo.declare("gnr.widgets.PaneGrid", gnr.widgets.gnrwdg, {    
    createContent:function(sourceNode, kw,children) {
        var paneCode = objectPop(kw, 'paneCode');
        var gridId = objectPop(kw, 'gridId') || paneCode+'_grid';
        var storepath = objectPop(kw, 'storepath');
        var structpath = objectPop(kw, 'structpath');
        storepath = storepath? sourceNode.absDatapath(storepath):'.store';
        structpath = structpath? sourceNode.absDatapath(structpath):'.struct';
        var gridKwargs = {'nodeId':gridId,'datapath':'.grid','table':objectPop(kw,'table'),
                           'margin':'6px','configurable':true,
                           'storepath': storepath,
                           'structpath': structpath,
                           'draggable_row':true,
                           'relativeWorkspace':true};             
        gridKwargs.grid_onDrag = function(dragValues, dragInfo) {
            if (dragInfo.dragmode == 'row') {
                dragValues[paneCode] = dragValues.gridrow.rowsets;
            }
        };
        objectUpdate(gridKwargs, objectExtract(kw, 'grid_*'));
        kw['wdgNodeId'] = gridId;
        var pane = sourceNode._('FramePane', kw);
        if(kw.searchOn){
            pane._('SlotToolbar',{'side':'top',slots:'*,searchOn',wdgNodeId:gridId,searchOn:objectPop(kw,'searchOn')});
        }
        var grid = pane._('includedview', gridKwargs);
        return pane;
    }
});

dojo.declare("gnr.widgets.PaletteGrid", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw,children) {
        var paletteCode = objectPop(kw,'paletteCode');
        var paletteKw = objectExtract(kw, 'title,dockTo,top,left,right,bottom,maxable,height,width');
        paletteKw['paletteCode'] = paletteCode;
        kw['paneCode'] = paletteCode;
        var gridId = kw.gridId || paletteCode+'_grid';
        kw['gridId'] = gridId;
        paletteKw.selfsubscribe_showing = function() {
            var grid = genro.wdgById(gridId);
            if (grid.storebag().len() == 0) {
                grid.reload();
            }
        }
        return sourceNode._('PalettePane', paletteKw)._('PaneGrid',kw);
    }
});

dojo.declare("gnr.widgets.PaneTree", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw) {
        var paneCode = kw.paneCode;
        var editable = objectPop(kw, 'editable');
        var treeId = objectPop(kw, 'treeId') || paneCode + '_tree';
        var storepath = objectPop(kw, 'storepath') || '.store';
        var tree_kwargs = {_class:'fieldsTree', hideValues:true,
            margin:'6px', draggable:true,nodeId:treeId,
            storepath:storepath,labelAttribute:'caption'};
        tree_kwargs.onDrag = function(dragValues, dragInfo, treeItem) {
            if (treeItem.attr.child_count && treeItem.attr.child_count > 0) {
                return false;
            }
            dragValues['text/plain'] = treeItem.attr.caption;
            dragValues[paneCode] = treeItem.attr;
        };
        objectUpdate(tree_kwargs, objectExtract(kw, 'tree_*'));
        var searchOn = objectPop(kw, 'searchOn');

        var pane = sourceNode._('FramePane', kw);
        if (searchOn) {
            pane._('SlotToolbar',{'side':'top',slots:'*,searchOn',wdgNodeId:treeId,searchOn:true});
        }
        if (editable) {
            var bc = pane._('BorderContainer',{'side':'center'});
            var bottom = bc._('ContentPane', {'region':'bottom',height:'30%',
                splitter:true});
            bottom._('BagNodeEditor', {nodeId:treeId + '_editbagbox',datapath:'.bagNodeEditor',bagpath:pane.getParentNode().absDatapath(storepath)});
            pane = bc._('ContentPane',{'region':'center'});
        }
        pane._('tree', tree_kwargs);
        return pane;
    }
});

dojo.declare("gnr.widgets.PaletteTree", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw,children) {
        var paletteCode = objectPop(kw,'paletteCode');
        var paletteKw = objectExtract(kw, 'title,dockTo,top,left,right,bottom,maxable,height,width');
        paletteKw['paletteCode'] = paletteCode;
        kw['paneCode'] = paletteCode;
        return sourceNode._('PalettePane', paletteKw)._('PaneTree',kw);
    }
});

dojo.declare("gnr.widgets.PaletteBagNodeEditor", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw) {
        var nodeId = objectPop(kw, 'nodeId');
        var pane = sourceNode._('PalettePane', kw);
        pane._('BagNodeEditor', {nodeId:nodeId,datapath:'.bagNodeEditor',bagpath:kw.bagpath});
        return pane;
    }
});

dojo.declare("gnr.widgets.BagNodeEditor", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw) {
        var gnrwdg = sourceNode.gnrwdg;
        var nodeId = objectPop(kw, 'nodeId');
        var readOnly = objectPop(kw, 'readOnly', false);
        var valuePath = objectPop(kw, 'valuePath');
        var showBreadcrumb = objectPop(kw, 'showBreadcrumb', true);
        var bc = sourceNode._('BorderContainer', {'nodeId':nodeId,detachable:true,_class:'bagNodeEditor'});
        if (showBreadcrumb) {
            var top = bc._('ContentPane', {'region':'top',background_color:'navy',color:'white'});
            top._('span', {'innerHTML':'Path : '});
            top._('span', {'innerHTML':'^.currentEditPath'});
        }
        var box = bc._('ContentPane', {'region':'center',_class:'formgrid'});
        var gridId = nodeId + '_grid';
        var topic = nodeId + '_editnode';
        var bagpath = objectPop(kw, 'bagpath');
        this.prepareStruct();
        gnrwdg.bagpath = bagpath;
        gnrwdg.valuePath = valuePath;
        gnrwdg.readOnly = readOnly;
        dojo.subscribe(topic, this, function(item) {
            gnrwdg.gnr.setCurrentNode(gnrwdg, item)
        });
        var grid = box._('includedview', {'storepath':'.data','structpath':'gnr._dev.bagNodeEditorStruct',
            'datamode':'bag','relativeWorkspace':true,'nodeId':gridId,
            autoWidth:false,'editorEnabled':true});
        if (!readOnly) {
            var gridEditor = grid._('gridEditor');
            var cellattr = {'gridcell':'attr_value','autoWdg':true};
            cellattr.validate_onAccept = function(value, result, validations, rowIndex, userChange) {
                var dataNode = this.grid.storebag().getParentNode().attr.dataNode;
                var attr_name = this.getRelativeData('.attr_name');
                if (attr_name == '*value') {
                    dataNode.setValue(value);
                } else {
                    var newattr = !('attr_name' in dataNode.attr);
                    dataNode.setAttribute(attr_name, value);
                    if (!value) {
                        objectPop(dataNode.attr, attr_name);
                    }
                    if (newattr || !value)
                        setTimeout(function() {
                            genro.publish(topic, dataNode);
                        }, 300);
                }
            };
            gridEditor._('textbox', {gridcell:'attr_name'});
            gridEditor._('textbox', cellattr);
        }
        return box;
    },
    setCurrentNode:function(gnrwdg, item) {
        var bagpath = gnrwdg.bagpath;
        var sourceNode = gnrwdg.sourceNode;
        if (typeof(item) == 'string') {
            item = sourceNode.getRelativeData(bagpath).getNode(item);
        }
        var itempath = item.getFullpath(null, sourceNode.getRelativeData(bagpath));
        sourceNode.setRelativeData('.currentEditPath', itempath);
        gnrwdg.currentEditPath = itempath;
        var newstore = new gnr.GnrBag();
        for (var k in item.attr) {
            var row = new gnr.GnrBag();
            row.setItem('attr_name', k, {_editable:false});
            row.setItem('attr_value', item.attr[k]);
            newstore.setItem('#id', row);
        }
        var itemvalue = item.getValue('static');

        if (gnrwdg.valuePath) {
            sourceNode.setRelativeData(gnrwdg.valuePath, itemvalue);
        } else {
            var editable = true;
            row = new gnr.GnrBag();
            row.setItem('attr_name', '*value', {_editable:false});
            if (itemvalue instanceof gnr.GnrBag) {
                var editable = false;
                itemvalue = '*bag*';
            }
            row.setItem('attr_value', itemvalue, {_editable:editable});
            newstore.setItem('#id', row);
        }

        newstore.sort('attr_name');
        //newstore.forEach(function(n){if(n.label.indexOf('~~')==0){n.label=n.label.slice(2);}});
        if (!gnrwdg.readOnly) {
            newstore.setItem('#id', new gnr.GnrBag({'attr_name':null,'attr_value':null}));
        }
        sourceNode.setRelativeData('.data', newstore, {'dataNode':item});
    },
    prepareStruct:function() {
        if (genro.getData('gnr._dev.bagNodeEditorStruct')) {
            return;
        }
        var rowstruct = new gnr.GnrBag();
        rowstruct.setItem('cell_0', null, {field:'attr_name',name:'Name',width:'30%',
            cellStyles:'background:gray;color:white;border-bottom:1px solid white;'});
        rowstruct.setItem('cell_1', null, {field:'attr_value',name:'Value',width:'70%',
            cellStyles:'border-bottom:1px solid lightgray;'});
        genro.setData('gnr._dev.bagNodeEditorStruct.view_0.row_0', rowstruct);
    }
});

dojo.declare("gnr.widgets.SearchBox", gnr.widgets.gnrwdg, {
    contentKwargs: function(sourceNode, attributes) {
        //var topic = attributes.nodeId+'_keyUp';
        var delay = 'delay' in attributes ? objectPop(attributes, 'delay') : 100;
        attributes.onKeyUp = function(e) {
            var sourceNode = e.target.sourceNode;
            if (sourceNode._onKeyUpCb) {
                clearTimeout(sourceNode._onKeyUpCb);
            }
            var v = e.target.value;
            sourceNode._onKeyUpCb = setTimeout(function() {
                sourceNode.setRelativeData('.currentValue', v);
            }, delay);
        };
        return attributes;
    },
    defaultDatapath:function(attributes) {
        return '.searchbox';
    },
    createContent:function(sourceNode, kw) {
        var searchOn = objectPop(kw, 'searchOn');
        var searchDtypes;
        if (searchOn[0] == '*') {
            searchDtypes = searchOn.slice(1);
            searchOn = true;
        }
        var nodeId = objectPop(kw, 'nodeId');
        var menubag;
        var databag = new gnr.GnrBag();
        var defaultLabel = objectPop(kw, 'searchLabel') || 'Search';
        databag.setItem('menu_dtypes', searchDtypes);
        databag.setItem('caption', defaultLabel);
        this._prepareSearchBoxMenu(searchOn, databag);
        sourceNode.setRelativeData(null, databag);
        var searchbox = sourceNode._('div', {nodeId:nodeId});
        sourceNode._('dataController', {'script':'genro.publish(searchBoxId+"_changedValue",currentValue,field)',
            'searchBoxId':nodeId,currentValue:'^.currentValue',field:'^.field'});
        var searchlbl = searchbox._('div', {'float':'left', margin_top:'2px'});
        searchlbl._('span', {'innerHTML':'^.caption',_class:'buttonIcon'});
        searchlbl._('menu', {'modifiers':'*',_class:'smallmenu',storepath:'.menubag',
            selected_col:'.field',selected_caption:'.caption'});

        searchbox._('input', {'value':'^.value',_class:'searchInput',
            connect_onkeyup:kw.onKeyUp,
            width:kw.width});
        dojo.subscribe(nodeId + '_updmenu', this, function(searchOn) {
            menubag = this._prepareSearchBoxMenu(searchOn, databag);
        });
        return searchbox;
    },
    _prepareSearchBoxMenu: function(searchOn, databag) {
        var menubag = new gnr.GnrBag();
        var i = 0;
        if (searchOn === true) {
            databag.setItem('menu_auto', menubag);
        }
        else {
            dojo.forEach(searchOn.split(','), function(col) {
                col = dojo.trim(col);
                var caption = col;
                if (col.indexOf(':') >= 0) {
                    col = col.split(':');
                    caption = col[0];
                    col = col[1];
                }
                col = col.replace(/[.@]/g, '_');
                menubag.setItem('r_' + i, null, {col:col,caption:caption,child:''});
                i++;
            });
        }
        databag.setItem('field', menubag.getItem('#0?col'));
        var defaultLabel = menubag.getItem('#0?caption');
        if (defaultLabel) {
            databag.setItem('caption', defaultLabel);
        }
        databag.setItem('menubag', menubag);
        databag.setItem('value', '');
    }

});


dojo.declare("gnr.widgets.PaletteGroup", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw) {
        var groupCode = objectPop(kw, 'groupCode');
        var palette_kwargs = objectExtract(kw, 'title,dockTo,top,left,right,bottom');
        palette_kwargs['nodeId'] = palette_kwargs['nodeId'] || groupCode + '_floating';
        palette_kwargs.selfsubscribe_showing = function() {
            genro.publish('palette_' + this.getRelativeData('gnr.palettes._groups.pagename.' + groupCode) + '_showing'); //gnr.palettes?gruppopiero=palettemario
        }
        palette_kwargs['title'] = palette_kwargs['title'] || 'Palette ' + groupCode;
        var floating = sourceNode._('palette', palette_kwargs);
        var tab_kwargs = objectUpdate(kw, {selectedPage:'^gnr.palettes._groups.pagename.' + groupCode,groupCode:groupCode,_class:'smallTabs'});
        var tc = floating._('tabContainer', tab_kwargs);
        return tc;
    }
});


dojo.declare("gnr.widgets.SlotToolbar", gnr.widgets.gnrwdg, {
    createContent:function(sourceNode, kw,children) {
        kw.orientation = (kw.orientation || 'H').toUpperCase();
        var table = sourceNode._('toolbar',{'_class':'sltb_toolbar sltb_'+kw.orientation})._('table',{'_class':'sltb_table'})._('tbody');
        return this['createContent_'+kw.orientation](table,kw,children);
    },

    createContent_H:function(table,kw,children){
        kw['_class'] = (kw['_class'] || '')+' sltb_row';
        var slots = objectPop(kw,'slots');
        var toolbarCode = objectPop(kw,'toolbarCode');
        var r = table._('tr',kw);
        var attr,cell,slotNode,slotValue;
        var children = children || new gnr.GnrBag();
        var that = this;
        dojo.forEach(splitStrip(slots),function(slot){
            if(slot=='*'){
                r._('td',{'_class':'sltb_elastic_spacer'});
                return;
            }
            if(slot=='|'){
                r._('td',{'_class':'sltb_slot_td'})._('div',{'_class':'sltb_spacer'});
                return;
            }
            cell = r._('td',{_slotname:slot,'_class':'sltb_slot_td'});
            slotNode = children.popNode(slot);
            if (slotNode){
                slotValue = slotNode.getValue();
                if(slotValue instanceof gnr.GnrBag){
                    slotValue.forEach(function(n){
                        cell.setItem(n.label,n._value,n.attr);
                    })
                }
            }
            else if(that['slot_'+slot]){
                that['slot_'+slot](cell,kw)
            }            
        });
        
        return r;
    },
    createContent_V:function(table,kw){
        return table;
    },
    
    slot_searchOn:function(pane,kw){
        var div = pane._('div',{'width':'205px'});
        div._('SearchBox', {searchOn:kw.searchOn,nodeId:kw.wdgNodeId+'_searchbox',datapath:'.searchbox'});
    }

    
});


dojo.declare("gnr.widgets.FormStore", gnr.widgets.gnrwdg, {
    _beforeCreation: function(sourceNode) {
        var kw = objectUpdate({}, sourceNode.attr);
        var storeType = objectPop(kw, 'storeType')
        objectPop(kw, 'tag');
        sourceNode.form.setStore(storeType, kw);
        return false;
    }
});


