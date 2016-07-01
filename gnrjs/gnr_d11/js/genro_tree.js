/*
 *--------------------------------------------------------------------------
 * package       : Genro js - see LICENSE for details
 * module genro_widget : Genro ajax widgets module
 * Copyright (c) : 2004 - 2007 Softwell sas - Milano
 * Written by    : Giovanni Porcari, Francesco Cavazzana
 *                 Saverio Porcari, Francesco Porcari
 *--------------------------------------------------------------------------
 *This library is free software; you can redistribute it and/or
 *modify it under the terms of the GNU Lesser General Public
 *License as published by the Free Software Foundation; either
 *version 2.1 of the License, or (at your option) any later version.

 *This library is distributed in the hope that it will be useful,
 *but WITHOUT ANY WARRANTY; without even the implied warranty of
 *MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 *Lesser General Public License for more details.

 *You should have received a copy of the GNU Lesser General Public
 *License along with this library; if not, write to the Free Software
 *Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

//######################## genro tree #########################

dojo.declare("gnr.widgets.Tree", gnr.widgets.baseDojo, {
    constructor: function() {
        this._domtag = 'div';
        this._dojotag = 'Tree';
    },

    onBuilding:function(sourceNode){
        var popup = objectPop(sourceNode.attr,'popup');
        if(!popup){
            return;
        }
        var popup_kw = {tag:'menu',modifiers:'*',_class:'menupane',
                        connect_ondblclick:function(bagNode,treeNode){
                            this.widget.onCancel();
                        }};
        var treeattr = objectUpdate({},sourceNode.attr);
        popup_kw.datapath = objectPop(treeattr,'datapath');
        popup_kw.connect_onOpen = function(evt){
            var box = this.getValue().getItem('m_item.m_scrollbox.m_spacer');
            if(!box.getNode('treemenu')){
                box._('tree','treemenu',
                        objectUpdate({openOnClick:true,
                            hideValues:true,autoCollapse:true, //excludeRoot:true,
                            labelAttribute:'caption',selectedLabelClass:'selectedFieldTreeNode',
                            parentMenu:this,_class:"branchtree noIcon"},treeattr));
            }
            box.getNode('treemenu').widget.originalContextTarget = this.widget.originalContextTarget;
        };
        var box_kw = objectExtract(popup_kw,'max_height,min_width');
        objectUpdate(popup_kw,objectExtract(sourceNode.attr,'popup_*'));
        sourceNode.attr = popup_kw;
        box_kw.max_height= box_kw.max_height || '300px';
        box_kw.min_width= box_kw.min_width || '220px';
        box_kw.overflow='auto';
        box_kw.connect_onclick = function(e){e.stopPropagation();e.preventDefault();};
        sourceNode._('menuItem','m_item',{},{doTrigger:false})._('div','m_scrollbox',box_kw,{doTrigger:false})._('div','m_spacer',{padding_top:'4px', padding_bottom:'4px'},{doTrigger:false});
    },


    creating: function(attributes, sourceNode) {
        dojo.require("dijit.Tree");
        // var nodeAttributes = objectExtract(attributes,'node_*');
        var storepath = sourceNode.absDatapath(objectPop(attributes, 'storepath'));
        var labelAttribute = objectPop(attributes, 'labelAttribute');
        var labelCb = objectPop(attributes, 'labelCb');
        var hideValues = objectPop(attributes, 'hideValues');
        var _identifier = objectPop(attributes, 'identifier') || '#id';
        var hasChildrenCb = objectPop(attributes, 'hasChildrenCb');
        if (hasChildrenCb){
            hasChildrenCb = funcCreate(hasChildrenCb);
        }

        if (labelCb) {
            labelCb = funcCreate(labelCb);
        }
        var store = new gnr.GnrStoreBag({datapath:storepath,_identifier:_identifier,
            hideValues:hideValues,
            labelAttribute:labelAttribute,
            labelCb:labelCb,
            hasChildrenCb:hasChildrenCb,
            sourceNode:sourceNode
            });
        var model = new dijit.tree.ForestStoreModel({store: store,childrenAttrs: ["#v"]});
        attributes.model = model;
        attributes.showRoot = false;
        attributes.persist = attributes.persist || false;
        if (attributes['getLabel']) {
            var labelGetter = funcCreate(attributes['getLabel'], 'node');
            attributes.getLabel = function(node) {
                if (node.attr) {
                    return labelGetter(node);
                }
            };
        }
        if (!attributes['getLabelClass']) {
            attributes['getLabelClass'] = function(node, opened) {
                var labelClass;
                if (opened) {
                    return node.attr.labelClassOpened || node.attr.labelClass;
                } else {
                    return node.attr.labelClassClosed || node.attr.labelClass;
                }
            };
        }
        var labelClassGetter = funcCreate(attributes['getLabelClass'], 'node,opened');

        var selectedLabelClass = attributes['selectedLabelClass'];
        attributes.getLabelClass = function(node, opened) {
            if (node.attr) {
                var labelClass = labelClassGetter.call(this, node, opened) || '';
                if (selectedLabelClass) {
                    return (this.currentSelectedNode && this.currentSelectedNode.item == node) ? labelClass + ' ' + selectedLabelClass : labelClass;
                } else {
                    return labelClass;
                }
            }
        };
        if (attributes['getIconClass']) {
            var iconGetter = funcCreate(attributes['getIconClass'], 'node,opened');
            attributes.getIconClass = function(node, opened) {
                if (node.attr) {
                    return iconGetter(node, opened);
                }
            };
        }
        attributes.onChecked=attributes.onChecked || ('checkedPaths' in attributes) || ('checked' in attributes) || objectNotEmpty(objectExtract(sourceNode.attr,'checked_*',true))
        if (attributes.onChecked) {
            attributes.getIconClass = function(node, opened) {
                if (!(node instanceof gnr.GnrBagNode)) {
                    return;
                }
                if (node.attr) {
                    var checked = 'checked' in node.attr? node.attr.checked : node.getInheritedAttributes()['checked'];
                    if(checked=='disabled:on'){
                        return 'checkboxOn dimmed';
                    }else if(checked=='disabled:off'){
                        return 'checkboxOff dimmed';
                    }

                    if (!('checked' in node.attr)) {
                        node.attr.checked = this.tree.checkBoxCalcStatus(node);
                    } 
                    
                    return (node.attr.checked == -1) ? "checkboxOnOff" : node.attr.checked ? "checkboxOn" : "checkboxOff";
                }
            };
            if(attributes.checkedPaths){
                sourceNode.registerDynAttr('checkedPaths');
            }

        }
        if (attributes.selectedPath) {
            sourceNode.registerDynAttr('selectedPath');
        }
        var tooltipAttrs = objectExtract(attributes, 'tooltip_*');
        var savedAttrs = objectExtract(attributes, 'inspect,autoCollapse,onChecked,editable');
        if (objectNotEmpty(tooltipAttrs)) {
            savedAttrs['tooltipAttrs'] = tooltipAttrs;
        }
        // attributes.gnrNodeAttributes=nodeAttributes;
        attributes.sourceNode = sourceNode;
        return savedAttrs;

    },
    
    created: function(widget, savedAttrs, sourceNode) {
        if (savedAttrs.tooltipAttrs) {

            var funcToCall = funcCreate(savedAttrs.tooltipAttrs.callback, 'sourceNode,treeNode', widget);
            var cb = function(n) {
                var item = dijit.getEnclosingWidget(n).item;
                return funcToCall(item, n);
            };

            genro.wdg.create('tooltip', null, {label:cb,
                validclass:'dijitTreeLabel',
                modifiers:savedAttrs.tooltipAttrs.modifiers
            }).connectOneNode(widget.domNode);
        }
        if (savedAttrs.inspect) {
            var modifiers = (savedAttrs.inspect == true) ? '' : savedAttrs.inspect;
            genro.wdg.create('tooltip', null, {label:function(n) {
                return genro.dev.bagAttributesTable(n);
            },
                validclass:'dijitTreeLabel',
                modifiers:modifiers
            }).connectOneNode(widget.domNode);
        }

        //dojo.connect(widget,'onClick',widget,'_updateSelect');
        var storepath = widget.model.store.datapath;
        if ((storepath == '*D') || (storepath == '*S'))
            widget.sourceNode.registerSubscription('_trigger_data',widget,function(kw){
                this.setStorepath('', kw);
            });
        else {
            sourceNode.registerDynAttr('storepath');
        }
        if (savedAttrs.onChecked) {
            widget.checkBoxTree = true;
            if (savedAttrs.onChecked != true) {
                widget.onChecked = funcCreate(savedAttrs.onChecked, 'node,event');
            }
        }
        if (savedAttrs.autoCollapse) {
            dojo.connect(widget, '_expandNode', function(node) {
                dojo.forEach(node.getParent().getChildren(), function(n) {
                    if (n != node && n.isExpanded) {
                        n.tree._collapseNode(n);
                    }
                });
            });
        }
        var nodeId = sourceNode.attr.nodeId;
        if(savedAttrs.editable){
            var editmodifiers = savedAttrs.editable==true?'Shift':savedAttrs.editable;
            dojo.connect(widget,'onClick',function(item,treeNode){
                if(treeNode.__eventmodifier==editmodifiers){
                    var origin=storepath.startsWith('*S')?'*S':null;
                    genro.dev.openBagNodeEditorPalette(item.getFullpath(null,origin!='*S'?genro._data:null),{name:nodeId || 'inspector_'+sourceNode.getPathId(),origin:origin});
                }
            });
        }
        
        if(nodeId){
            var searchBoxCode = (sourceNode.attr.frameCode || nodeId)+'_searchbox';
            var searchBoxNode = genro.nodeById(searchBoxCode);
            if (searchBoxNode){
                sourceNode.registerSubscription(searchBoxCode+'_changedValue',widget,function(v,field){
                    this.applyFilter(v);
                });
            }
           //var editBagBoxNode = genro.nodeById(nodeId+'_editbagbox');
           //if (editBagBoxNode){
           //    dojo.connect(widget,'_updateSelect',function(item,node){
           //        if(!(item instanceof gnr.GnrBagNode)){
           //            if(item===null){
           //                return;
           //            }
           //            item = node.getParent().item;
           //        }
           //        editBagBoxNode.gnrwdg.setCurrentNode(item);
           //    });
           //}
        }
    },


    
    
    fillDragInfo:function(dragInfo) {
        dragInfo.treenode = dragInfo.widget;
        dragInfo.widget = dragInfo.widget.tree;
        dragInfo.treeItem = dragInfo.treenode.item;

    },
    
    fillDropInfo:function(dropInfo) {
        dropInfo.treenode = dropInfo.widget;
        dropInfo.widget = dropInfo.widget.tree;
        dropInfo.treeItem = dropInfo.treenode.item;
        dropInfo.outline = dropInfo.treenode.domNode;

    },
    onDragStart:function(dragInfo) {
        var item = dragInfo.treenode.item;
        var caption = dragInfo.treenode.label;
        var result = {};
        
        result['text/plain'] = dragInfo.treenode.label;
        result['text/xml'] = dragInfo.treenode.label;

        result['nodeattr'] = item.attr;
        result['treenode'] = {'fullpath':item.getFullpath(),'relpath':item.getFullpath(null, dragInfo.treenode.tree.model.store.rootData())};
        return result;
    },
    
    attributes_mixin_checkBoxCalcStatus:function(bagnode) {
        var checked,ck;
        if (bagnode._resolver && bagnode._resolver.expired()) {
            return false;
        } else if (bagnode._value instanceof gnr.GnrBag) {
            bagnode._value.forEach(function(node) {
                var checked = ('checked' in node.attr) ? (node.attr.checked || false) : -1;
                ck = (ck == null) ? checked : (ck != checked) ? -1 : ck;
            }, 'static');
        }
        return ck;
    },

    mixin_collapseAll:function(curr){
        curr = curr || this.rootNode;
        var tree = this;
        dojo.forEach(curr.getChildren(), function(n) {
            if (n.isExpanded) {
                tree.collapseAll(n);
                tree._collapseNode(n);
            }
        });
    },

    mixin_applyFilter:function(search){
        var treeNodes=dojo.query('.dijitTreeNode',this.domNode);
        treeNodes.removeClass('hidden');
        if (!search){return;}
        var searchmode=null;
        if (search.indexOf('#')==0){
            var k=search.indexOf('=');
            if ((k<0 )||(k==(search.length-1))){
                return;
            }
            search=search.split('=');
            searchmode=search[0];
            search=search[1];
        }
        var _this=this;
        cb_match=function(n){
            if (!searchmode){
                var label=_this.getLabel(n);
                return (label.toLowerCase().indexOf(search)>=0);
            }else if(searchmode=='#'){
                console.log('ss');
            }else {
                var label=n.attr[searchmode.slice(1)]+'';
                if (label){
                    return (label.toLowerCase().indexOf(search)>=0);
                }
            }
            
        };
        var root=this.model.store.rootData();
        cb=function(n){
            if (cb_match(n)){
                var fullpath=n.getFullpath(null,root);
                _this.showNodeAtPath(fullpath);
            }
        };
        var mode = this.sourceNode.attr.searchMode;
        root.walk(cb,mode)
        treeNodes.addClass('hidden');
        treeNodes.forEach(function(n){
            var tn = dijit.getEnclosingWidget(n);
            var parent=tn.getParent();
            if((!parent) || cb_match(tn.item)){
                dojo.removeClass(tn.domNode,'hidden');
                while(parent&&dojo.hasClass(parent.domNode,'hidden')){
                    dojo.removeClass(parent.domNode,'hidden');
                    parent=parent.getParent();
                }
                
            };
        });
        
    },

    mixin_updateLabels:function(){
        var n;
        for (var k in this._itemNodeMap){
            n = this._itemNodeMap[k];
            if(n){
                n.setLabelNode(this.getLabel(n.item));
            }
        }
    },

    mixin_storebag:function(){
        return this.sourceNode.getRelativeData(this.sourceNode.attr.storepath);
    },

    mixin_clickOnCheckbox:function(bagnode, e) {
        if(bagnode.attr.checked=='disabled:on' || bagnode.attr.checked=='disabled:off'){
            return;
        }
        var checked = bagnode.attr.checked ? false : true;
        var walkmode = this.sourceNode.attr.eagerCheck ? null : 'static';
        var updBranchCheckedStatus = function(bag) {
            bag.forEach(function(n) {
                if(n.attr.checked == 'disabled:on' || n.attr.checked=='disabled:off'){
                    return
                }
                var v = n.getValue(walkmode);
                if ((v instanceof gnr.GnrBag) && v.len()) {
                    updBranchCheckedStatus(v);
                    var checkedStatus = dojo.every(v.getNodes(), function(cn) {
                        return cn.attr.checked == true;
                    });
                    if (!checkedStatus) {
                        var allUnchecked = dojo.every(v.getNodes(), function(cn) {
                            return cn.attr.checked == false;
                        });
                        checkedStatus = allUnchecked ? false : -1;
                    }
                    n.setAttr({'checked':checkedStatus}, true, true);

                } else if (n._resolver && n._resolver.expired()) {
                    n.setAttr({'checked':false}, true, true);
                } else {
                    n.setAttr({'checked':checked}, true, true);
                }
            });
        };
        if (bagnode.getValue) {
            var value = bagnode.getValue();
            if ((value instanceof gnr.GnrBag) && this.sourceNode.attr.checkChildren!==false) {
                updBranchCheckedStatus(value);
            }
        }
        bagnode.setAttr({'checked':checked}, true, true);
        var parentNode = bagnode.getParentNode();
        var rootNodeId = genro.getDataNode(this.model.store.datapath)._id;
        while (parentNode && (parentNode._id != rootNodeId)) {
            parentNode.setAttr({'checked':this.checkBoxCalcStatus(parentNode)}, true, true);
            var parentNode = parentNode.getParentNode();
        }
        if (this.sourceNode.attr.nodeId) {
            genro.publish(this.sourceNode.attr.nodeId + '_checked', bagnode);
        }
         this.updateCheckedAttr()
    },

    mixin_updateCheckedAttr:function(){
        var checked_attr = objectExtract(this.sourceNode.attr,'checked_*',true)
        var checked_attr_joiners = {};
        var p;
        for (var k in checked_attr){
            p = checked_attr[k];
            if(p.indexOf(':')>=0){
                p = p.split(':');
                checked_attr[k] = p[0]
                checked_attr_joiners[k] = p[1];
            }
        }
        var checkedPaths = this.sourceNode.attr.checkedPaths;
        var checkedPaths_joiner = this.sourceNode.attr.checkedPaths_joiner;
         if(objectNotEmpty(checked_attr) || checkedPaths){
             var propagate = this.sourceNode.attr.checkChildren!==false;
             var walkmode = this.sourceNode.attr.eagerCheck ? null : 'static';
             var store = this.sourceNode.getRelativeData(this.sourceNode.attr.storepath);
             var result = {};
             var cp = [];
             var p;
             for(var k in checked_attr){
                 result[k] = [];
             }

             store.walk(function(n){
                 var v = n.getValue(walkmode);
                 if(propagate && (v instanceof gnr.GnrBag )&& (v.len()>0)){
                     return;
                 }else if(n.attr.checked===true){
                     for(var k in checked_attr){
                         var av = n.attr[k];
                         if(result[k].indexOf(av)<0){
                             result[k].push(av)
                         }
                         if(checkedPaths){
                             p = n.getFullpath('static',store);
                             if(cp.indexOf(p)<0){
                                 cp.push(p);
                             }
                         }
                     }
                 }
             },walkmode);
             for(var k in checked_attr){
                 this.sourceNode.setRelativeData(checked_attr[k],result[k].join(checked_attr_joiners[k] || ','))
             }
             if(checkedPaths){
                 this.sourceNode.setRelativeData(checkedPaths,cp.join(checkedPaths_joiner || ','),null,null,this);
             }
             
         }

    },

    versionpatch_11__onClick:function(e) {
        var nodeWidget = dijit.getEnclosingWidget(e.target);
        if (dojo.hasClass(e.target, 'dijitTreeIcon') && this.tree.checkBoxTree) {
            var bagnode = nodeWidget.item;
            if (bagnode instanceof gnr.GnrBagNode) {
                var onCheck = this.onChecked ? this.onChecked(bagnode, e) : true;
                if (onCheck != false) {
                    this.tree.clickOnCheckbox(bagnode, e);
                }
            }
            dojo.stopEvent(e);
            return;
        }
        var nodeWidget = dijit.getEnclosingWidget(e.target);
       //if (nodeWidget.htmlLabel && (!dojo.hasClass(e.target, 'dijitTreeExpando'))) {
       //    return;
       //}
        if (nodeWidget == nodeWidget.tree.rootNode) {
            return;
        }
        nodeWidget.__eventmodifier = eventToString(e);
        this._onClick_replaced(e);
        if (genro.wdg.filterEvent(e, '*', 'dijitTreeLabel,dijitTreeContent,treeCellContent')) {
            this.setSelected(nodeWidget);
        }
    },
    versionpatch_15__onClick:function(nodeWidget, e) {
        // summary:
        //      Translates click events into commands for the controller to process
        if (dojo.hasClass(e.target, 'dijitTreeIcon') && this.tree.checkBoxTree) {
            var bagnode = nodeWidget.item;
            if (bagnode instanceof gnr.GnrBagNode) {
                var onCheck = this.onChecked ? this.onChecked(bagnode, e) : true;
                if (onCheck != false) {
                    this.tree.clickOnCheckbox(bagnode, e);
                }
            }
            dojo.stopEvent(e);
            return;
        }
        if (nodeWidget.htmlLabel && (!dojo.hasClass(e.target, 'dijitTreeExpando'))) {
            return;
        }
        if (nodeWidget == nodeWidget.tree.rootNode) {
            return;
        }
        nodeWidget.__eventmodifier = eventToString(e);
        this._onClick_replaced(nodeWidget, e);
        if (genro.wdg.filterEvent(e, '*', 'dijitTreeLabel,dijitTreeContent')) {
            this.setSelected(nodeWidget);
        }
    },
    mixin_getItemById: function(id) {
        return this.model.store.rootData().findNodeById(id);
    },
    mixin_saveExpanded:function(){
        var that = this;
        this._savedExpandedStatus = dojo.query('.dijitTreeContentExpanded',that.domNode).map(function(n){
                                            return that.model.store.getIdentity(dijit.getEnclosingWidget(n).item);});
    },
    
    mixin_restoreExpanded:function(){
        if (this._savedExpandedStatus){
            var that = this;
            dojo.forEach(this._savedExpandedStatus,function(n){
                if(n){
                    var tn = that._itemNodeMap[n];
                    if(tn){
                        that._expandNode(tn);
                    }
                }
            });
        }
    },
    mixin_expandAll:function(rootNode){
        var that = this;
        var nodes = dojo.query('.dijitTreeExpando.dijitTreeExpandoClosed',rootNode.domNode);
        nodes.forEach(function(n){
                var n = that.model.store.getIdentity(dijit.getEnclosingWidget(n).item);
                var tn = that._itemNodeMap[n];
                that._expandNode(tn);
        });
    },

    attributes_mixin__saveState: function() {
        return;
        //summary: create and save a cookie with the currently expanded nodes identifiers
        if (!this.persist) {
            return;
        }
        var cookiepars = {};
        if (this.persist == 'site') {
            cookiepars.path = genro.getData('gnr.homeUrl');
        }
        var ary = [];
        for (var id in this._openedItemIds) {
            ary.push(id);
        }
        dojo.cookie(this.cookieName, ary.join(","), cookiepars);
    },
    attributes_mixin_loadState:function(val, kw) {
        //var cookie = dojo.cookie(this.cookieName);
        this._openedItemIds = {};
        /*if (cookie) {
            dojo.forEach(cookie.split(','), function(item) {
                this._openedItemIds[item] = true;
            }, this);
        }*/
    },
    mixin_setStorepath:function(val, kw) {
        //genro.debug('trigger_store:'+kw.evt+' at '+kw.pathlist.join('.'));
        var storeAbsPath = this.sourceNode.absDatapath(this.sourceNode.attr.storepath);
        var eventPath = kw.pathlist.join('.').slice(5);
        if (kw.evt == 'upd') {
            if (kw.updvalue) {
                if (kw.value instanceof gnr.GnrBag) {
                    if(storeAbsPath.indexOf(eventPath)==0){
                        this.sourceNode.rebuild();
                    }else{
                        this._onItemChildrenChange(/*dojo.data.Item*/ kw.node, /*dojo.data.Item[]*/ kw.value.getNodes());
                    }
                } else {
                    this._onItemChange({id:kw.node._id + 'c',label:kw.value});
                }
            } else if (kw.updattr) {
                this._onItemChange(kw.node);
            }
            //this.model.store._triggerUpd(kw);
        } else if (kw.evt == 'ins') {
            if(undefined in this._itemNodeMap && objectSize(this._itemNodeMap)==1){
                this.sourceNode.rebuild();
            }else{
                this.model.store._triggerIns(kw);
            }
            
        } else if (kw.evt == 'del') {
            this._onItemChildrenChange(/*dojo.data.Item*/ kw.where.getParentNode(), /*dojo.data.Item[]*/ kw.where.getNodes());
            //this.model.store._triggerDel(kw);
        }
    },
    
    patch__onItemChildrenChange:function(n,nodes){
        var that = this;
        var identifier;
        dojo.forEach(nodes,function(n){
            identifier = that.model.store.getIdentity(n);
            objectPop(that._itemNodeMap,identifier);
        });
        this._onItemChildrenChange_replaced(n,nodes);
    },

    mixin_setCheckedPaths:function(path,kw){
        if (kw.reason == this || kw.reason=='autocreate') {
            return;
        }
        var store = this.sourceNode.getRelativeData(this.sourceNode.attr.storepath);
        store.walk(function(n){
            n.setAttr({'checked':false}, true, true);
        },'static');
        var paths = this.sourceNode.getRelativeData(this.sourceNode.attr.checkedPaths);
        if(!paths){
            this.updateCheckedAttr();
            return;
        }
        paths = paths.split(this.sourceNode.attr.checkedPaths_joiner || ',');
        var that = this;
        var treeNode;
        paths.forEach(function(path){
            var n = store.getNode(path);
            if(n){
                that.clickOnCheckbox(n);
            }
        });
    },

    mixin_setSelectedPath:function(path, kw) {
        if (kw.reason == this) {
            return;
        }
        var curr = this.model.store.rootData();
        var currNode,treeNode;
        if (!kw.value) {
            this.setSelected(null);
            return;
        }
        var pathList = kw.value.split('.');
        for (var i = 0; i < pathList.length; i++) {
            if(!curr){
                return;
            }
            if(!(curr instanceof gnr.GnrBag)){
                console.warn('TREE setSelectedPath warn curr is not a bag',curr);
                //genro.dev.addError('TREE setSelectedPath warn curr is not a bag','warn',true);
                return;
            }
            currNode = curr.getNode(pathList[i]);
            if(!currNode){
                return;
            }
            var identity = this.model.store.getIdentity(currNode);
            treeNode = this._itemNodeMap[identity];
            if (i < pathList.length - 1) {
                if (!treeNode.isExpanded) {
                    this._expandNode(treeNode);
                }
            }
            curr = currNode.getValue();
        }
        var currTree = this;
        setTimeout(function() {
            currTree.focusNode(treeNode);
            currTree.setSelected(treeNode);
            if(kw.expand){
                currTree._expandNode(treeNode);
            }
        }, 100);
    },
     mixin_showNodeAtPath:function(path) {
         var curr = this.model.store.rootData();
         var pathList = path.split('.');
         for (var i = 0; i < pathList.length; i++) {
            var currNode = curr.getNode(pathList[i]);
            if (!currNode){
                return;
            }
            var identity = this.model.store.getIdentity(currNode);
            var treeNode = this._itemNodeMap[identity];
            curr = currNode.getValue('static');
            if (i < pathList.length - 1) {
                if (!treeNode.isExpanded) {
                    this._expandNode(treeNode);
                }
            }
        }
     },
    mixin_setSelected:function(node) {
        if(node){
            if(node.item.attr._isSelectable===false || (this.sourceNode.attr.openOnClick===true && node.item.attr.child_count)){
                return;
            }
            
        }
        var prevSelectedNode = this.currentSelectedNode;
        this.currentSelectedNode = node;
        if (prevSelectedNode) {
            prevSelectedNode._updateItemClasses(prevSelectedNode.item);
        }
        if (node) {
            node._updateItemClasses(node.item);
            this._updateSelect(node.item, node);
        }
        
    },
    mixin_isSelectedItem:function(item) {
        return this.currentSelectedNode ? this.currentSelectedNode.item == item : false;
    },

    mixin_getContainingtMenu:function(){
        return this.sourceNode.attributeOwnerNode('tag','menu',true);
    },

    mixin__updateSelect: function(item, node) {
        var modifiers = objectPop(node, '__eventmodifier');
        var reason = this;
        var attributes = {};
        var setterNode = this.sourceNode;
        var countainingMenu = this.getContainingtMenu();
        var path;
        if(countainingMenu){
            var targetDomNode = countainingMenu.widget.originalContextTarget;
            if(targetDomNode.sourceNode){
                setterNode = targetDomNode.sourceNode;
            }else{
                var targetWdg = dijit.getEnclosingWidget(targetDomNode);
                setterNode = targetWdg? targetWdg.sourceNode:setterNode;
            }
        }
        if (modifiers) {
            attributes._modifiers = modifiers;
        }
        if (!item) {
            item = new gnr.GnrBagNode();
        }
        else if (!item._id) {
            item = node.getParent().item;
        }
        var root = this.model.store.rootData();
        var itemFullPath = item.getFullpath(null, root);
        if (this.sourceNode.attr.selectedLabel) {
            path = this.sourceNode.attrDatapath('selectedLabel',setterNode);
            setterNode.setRelativeData(path, item.label, attributes, null, reason);
        }
        if (this.sourceNode.attr.selectedItem) {
            path = this.sourceNode.attrDatapath('selectedItem',setterNode);
            setterNode.setRelativeData(path, item, attributes, null, reason);
        }
        if (this.sourceNode.attr.selectedPath) {
            path = this.sourceNode.attrDatapath('selectedPath', setterNode);
            setterNode.setRelativeData(path, itemFullPath, objectUpdate(attributes, item.attr), null, reason);
        }
        var selattr = objectExtract(this.sourceNode.attr, 'selected_*', true);
        for (var sel in selattr) {
            path = this.sourceNode.attrDatapath('selected_' + sel,setterNode);
            setterNode.setRelativeData(path, item.attr[sel], attributes, null, reason);
        }
        if(this.sourceNode.attr.onSelectedFire){
            setterNode.fireEvent(this.sourceNode.attr.onSelectedFire,true);
        }
        this.sourceNode.publish('onSelected',{path:itemFullPath,item:item,node:node});
    }
});
