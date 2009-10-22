/*
*-*- coding: UTF-8 -*-
*--------------------------------------------------------------------------
* package       : Genro js - see LICENSE for details
* module genro_src : Genro clientside Source Bag handler
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


//######################## genro  #########################

dojo.declare("gnr.GnrSrcHandler",null,{
    
    constructor: function(application){
        this.application=application;
        //this.builder = new gnr.GnrDomBuilder(this);
        this._main=new gnr.GnrDomSource();
        this._main.setBackRef();
        this._main.subscribe('sourceTriggers',{'any':dojo.hitch(this, "nodeTrigger")});
        this._subscribedNodes={};
        this._index={};
        this.pendingBuild=[];
        this.afterBuildCalls=[];
        this.building=false ;
        this.datatags= {'data':null,'dataformula':null,'datascript':null,
                        'datarpc':null,'dataremote':null,'datacontroller':null};
        this.highlightedNode=null;
        
    },
    highlightNode:function(sourceNode){
        if (typeof(sourceNode) == 'string') {
            sourceNode = this._main.getNode(sourceNode);
        };
        if(this.highlightedNode){
            domnode=this.highlightedNode.getDomNode();
            if(domnode){
                genro.dom.removeClass(domnode,'gnrhighlight');
            }
        }
        this.highlightedNode=sourceNode;
        if(sourceNode){
            domnode=this.highlightedNode.getDomNode();
            if(domnode){
                genro.dom.addClass(domnode,'gnrhighlight');
            }
        }
    },
    nodeTrigger:function(kw){
        this.pendingBuild.push(kw);
        if (!this.building){
            this.building=true;
            while(this.pendingBuild.length>0){
                var kw=this.pendingBuild.pop();
                dojo.hitch(this,'_trigger_'+kw.evt)(kw);
            }
            this.building=false;
        }
    },
    _trigger_ins:function(kw){//da rivedere
        var node=kw.node;
        var wherenode=kw.where.getParentNode();
        if(wherenode){
            var where=wherenode.widget || wherenode.domNode;
            if(!where){
                alert('_trigger_ins error????');//|| dojo.byId(genro.domRootName);
            }
        }else{
            var where=dojo.byId(genro.domRootName);
            node.domNode=where;
        }
        var ind=kw.ind;
        this.buildNode(node, where, ind);  
    },
    _trigger_del:function(kw){//da rivedere
        var domNode =  kw.node.getDomNode();
        var widget=kw.node.widget;
        if(widget){
            widget.destroyRecursive();
        }else{
            var widgets = dojo.query('[widgetId]', domNode);
            widgets= widgets.map(dijit.byNode);     // Array
                dojo.forEach(widgets, function(widget){ widget.destroy(); });
            dojo._destroyElement(domNode);
        }
        this.refreshSourceIndexAndSubscribers();
    },
    _trigger_upd:function(kw){//da rivedere
        var destination=kw.node.getParentBuiltObj();
        var domNode =  kw.node.getDomNode();
        var newNode = document.createElement('div');
        var widget=kw.node.widget;
        var ind=-1;
        if(widget){
            if(widget.sizeShare){
                kw.node.attr.sizeShare=widget.sizeShare;
            }
            if(destination.getChildren){
                var children=destination.getChildren();
                ind=children.indexOf(widget);
                destination.removeChild(widget);
                widget.destroyRecursive();
            }else{
                domNode.parentNode.replaceChild(newNode,domNode);
                widget.destroyRecursive();
            }
        }else{
            domNode.parentNode.replaceChild(newNode,domNode);
            var widgets = dojo.query('[widgetId]', domNode);
            widgets= widgets.map(dijit.byNode);     // Array
            dojo.forEach(widgets, function(widget){ widget.destroy(); });
            while (domNode.childNodes.length > 0){
                dojo._destroyElement(domNode.childNodes[0]);
            }
            ind = newNode;
        }
        this.refreshSourceIndexAndSubscribers();
        this.buildNode(kw.node, destination, ind); 

      },
    buildNode: function(sourceNode,where,ind){
        this.afterBuildCalls=[];
        sourceNode._stripData();
        sourceNode.build(where, ind);
        var cb;
        while(this.afterBuildCalls.length>0){
            cb=this.afterBuildCalls.pop();
            cb.call();
        }
    },
    
       

    getSource:function(path){
        if (path){
            return this._main.getItem('main.'+path);
        }
        else{
            return  this._main.getItem('main');
        }
    
        
    },
    getNode:function(obj){
        if(!obj){
            return this._main.getNode('main');
        }
        if (typeof (obj)=='string'){
            if (obj.indexOf('main.') != 0){
                obj = 'main.'+obj;
            }
            return this._main.getNode(obj,false,true);
        }
        if(obj.declaredClass == 'gnr.GnrDomSourceNode'){
            return obj;
        }
        if(obj.sourceNode){
            return obj.sourceNode;
        }
        if(obj.target){
            return obj.target.sourceNode || dijit.getEnclosingWidget(obj.target).sourceNode;
        }
    },
    
    newRoot:function(){
           return new gnr.GnrDomSource();
    },
    setSource:function(path,value,attributes,kw){
        if (!attributes && (value instanceof gnr.GnrDomSource)){
            value=value.getNodes()[0];
        }
        this._main.setItem('main.'+path, value, attributes,kw);
    },
    delSource:function(path){
            this._main.delItem('main.'+path);
       },
          
    startUp:function(source){//nome troppo generico?
        this._main.setItem('main', source);  

    },
    setInRootContainer:function(label,item){
        alert('removed : setInRootContainer in genro_src');
    },
    enclosingSourceNode:function(item){
        if (item.sourceNode){
            return item.sourceNode;
        }
        if (item.widget){
            var widget = item.widget;
        }else{
            var widget = dijit.getEnclosingWidget(item);
        }
        if (widget){
            if (widget.sourceNode){
                return widget.sourceNode
            }else{
                return genro.src.enclosingSourceNode(widget.domNode.parentNode);
            }
        }
    },
    onEventCall:function(e, code, kw){
        var sourceNode = genro.src.enclosingSourceNode(e.target);
        var func = funcCreate(code,'kw,e',sourceNode)
        func(kw,e);
    },
    refreshSourceIndexAndSubscribers:function(){
        var oldSubscribedNodes=this._subscribedNodes;
        this._index={};
        this._subscribedNodes={};
        var refresher=dojo.hitch(this, function(n){
            var id=n.getStringId();
            var oldSubscriber = oldSubscribedNodes[id];
            if (oldSubscriber){
                genro.src._subscribedNodes[id]=oldSubscriber;
                oldSubscribedNodes[id]=null;
            }
            if(n.attr.nodeId){
                genro.src._index[n.attr.nodeId]=n;
            }
        });
        this._main.walk(refresher,'static');
        for(var subscriber in oldSubscribedNodes){
            if(oldSubscribedNodes[subscriber]){
                for (var attr in oldSubscribedNodes[subscriber]){
                    dojo.unsubscribe(oldSubscribedNodes[subscriber][attr]);
                }
                
            }
        }
    }
});