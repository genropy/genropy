var th_stats_js = {
    confTreeOnDrop:function(sourceNode,dropInfo,data){
        if(!dropInfo.selfdrop){
                return;
        }
        var put_before = dropInfo.modifiers == 'Shift';
        var b = sourceNode.widget.storebag();
        var destpath = dropInfo.treeItem.getFullpath(null,b);
        if(destpath==data){
            return;
        }
        var destNode = b.getNode(destpath);
        var destBag;
        var kw = {};
        if(destNode.attr.field){
            destBag = destNode.getParentBag();
            kw._position = (put_before?'<':'>')+destNode.label;
        }else{
            destBag = destNode.getValue();
        }
        var dragNode = b.popNode(data);
        destBag.setItem(dragNode.label,dragNode,null,kw);
    }
};

dojo.declare("gnr.widgets._tableHandlerStatsLayout", gnr.widgets.UserObjectLayout, {
    objtype:'pnd_simple',
    newcaption:'New',
    default_configurator_pars:{region:'left',splitter:true,
                                border_right:'1px solid #ccc',width:'230px'},

    contentKwargs: function(sourceNode, attributes) {
        var mainpars = objectExtract(attributes,'relation_field,relation_value,default_rows,relatedTable,relatedTableHandlerFrameCode,default_values,default_columns,condition,condition_kwargs');        
        for(var k in mainpars){
            sourceNode.gnrwdg[k] = mainpars[k];
        }
        if(!('configurator' in attributes)){
            attributes.configurator = this.default_configurator_pars;
            if(attributes.userObjectId){
                attributes.configurator.drawer='close';
            }
        }
        return attributes;
    },


    gnrwdg_viewerFrame:function(frame){
        //override
        var gnrwdg = this;
        var userObjectId = this.startUserObjectIdOrCode;

        var cpkw = {side:'center',overflow:'hidden',remote:'_ths_viewer',
                    remote_table:this.table,
                    remote_relation_field:this.relation_field,
                    remote_default_rows:this.default_rows,
                    remote_default_values:this.default_values,
                    remote_default_columns:this.default_columns,
                    remote_relation_value:this.relation_value,
                    remote_condition:this.condition,
                    remote_userObjectId:userObjectId,
                    remote_py_requires:'th/th_stats:TableHandlerStats',
                    remote__onRemote:function(){
                        if(userObjectId){
                            gnrwdg.loadObject(userObjectId,true);
                        }
                    }};
        //cpkw.remote_query_pars = normalizeKwargs(kw,'condition');
        frame._('ContentPane',cpkw);
    },

    gnrwdg_configuratorFrame:function(frame,kw){

        var cpkw = {side:'center',overflow:'hidden',remote:'_ths_configurator',
                              remote_relatedTable:this.relatedTable,
                              remote_relation_field:this.relation_field,
                              remote_relation_value:this.relation_value,
                              remote_table:this.table,
                              remote_condition:this.condition,
                              remote_relatedTableHandlerFrameCode:this.relatedTableHandlerFrameCode,
                              remote_py_requires:'th/th_stats:TableHandlerStats'};
        //cpkw.remote_query_pars = normalizeKwargs(kw,'condition');
        frame._('ContentPane',cpkw);
    },

    gnrwdg_userObjectData:function(){
        //override
        return this.sourceNode.getRelativeData('.stats.conf').deepCopy();
    },

    gnrwdg_onLoadingObject:function(userObjectId,fistLoad){
        //override
    },

    gnrwdg_onLoadedObject:function(result,userObjectId,fistLoad){
        //override
        if(userObjectId=='__newobj__'){
            var conf = this.sourceNode.getRelativeData('.stats.conf');
            var fields = conf.getItem('fields');
            var n;
            ['rows','columns','values'].forEach(function(k){
                conf.getItem(k).keys().forEach(function(f){
                    n = conf.getItem(k).popNode(f);
                    fields.setItem(f,n._value,n.attr);
                });
            });
        }else{
            this.sourceNode.setRelativeData('.stats.conf',result || new gnr.GnrBag());
        }
        
    }
});