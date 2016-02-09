var WorkbenchManager = {
    
    addElement:function(sourceNode,evt,dflt){
        dflt = dflt || {};
        var kw = {tag:'div',name:'box_'+genro.getCounter(),
                                       height:'100px',
                                       width:'100px',
                                       background:'red',
                                       border:'1px solid silver',
                                       moveable:true,
                                       position:'absolute',
                                       start_x:evt.x,start_y:evt.y}
        if(dflt.value){
            dflt.value = '^.'+kw.name;
        }
        var b = new gnr.GnrBag(objectUpdate(kw,dflt));
        genro.dlg.prompt('Create',{widget:'multiValueEditor',
                                    dflt:b,
                                    action:function(result){
                                        var path='#elements.'+result.getItem('name')
                                         sourceNode.setRelativeData(path,result.deepCopy());    
                                    }
                        });
        
    },
    createNode:function(pane, pars){
        var kw = pars.asDict();
        var start_x = objectPop(kw,'start_x');
        var start_y = objectPop(kw,'start_y');               
        var tag = objectPop(kw,'tag') || 'div';
        var name = objectPop(kw,'name') || 'box_'+genro.getCounter();
        if(kw.moveable){
            kw.position = 'absolute';
            kw.top = '^#elements.'+name+'.top';
            kw.left = '^#elements.'+name+'.left';
            genro.setData(kw.top ,start_y+'px');
            genro.setData(kw.left ,start_x+'px');
        }else{
            if(kw.position=='absolute' || kw.position=='relative'){
                kw.top  = start_y+'px';
                kw.left  = start_x+'px'
            }
        }
        pane._(tag,name,kw);
    },
    onChanges:function(sourceNode, pane, elements, tkw, reason){
        var that=this;
        var node=tkw.node;
        if (reason=='container'){
          elements.forEach(function(n){
             that.createNode(pane,n.getValue())
            } 
          )
        }
        if (tkw.where != elements) {
            return
        }
        if (tkw.evt=='ins'){
           that.createNode(pane,node.getValue())
        }else if (tkw.evt=='del'){
            pane.popNode(node.label)
        }else{
        }
    }

};