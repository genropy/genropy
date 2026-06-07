
dojo.declare("gnr.GnrIde", null, {
    constructor:function(sourceNode){
        this.sourceNode = sourceNode;
        this.gi_buildEditorTab = sourceNode.attr._gi_buildEditorTab;
        this.gi_makeEditorStack = sourceNode.attr._gi_makeEditorStack;

        this.start();
        genro.activeIDE = genro.activeIDE || {};
        genro.activeIDE[this.sourceNode.attr.nodeId] = this;
    },

    start:function(){
        if(genro.ext.startingModule){
            this.openModuleToEditorStack({module:genro.ext.startingModule});
        }
    },


    selectStackEditor:function(kw,onSelected){
        var scNode = this.getStackEditor(kw.ide_page);
        var ide_page = kw.ide_page || this.getCurrentIdePage();
        if(scNode){
            this.sourceNode.getRelativeData('.ide_page',ide_page)
            onSelected();
        }else{
            this.newIde(kw,onSelected);
            this.sourceNode.getRelativeData('.ide_page',ide_page);
        }
    },

    getStackEditor:function(ide_page){
        ide_page = ide_page || this.getCurrentIdePage();
        return genro.nodeById(ide_page+'_sc');
    },

    getIdeStack:function(){
        return genro.nodeById(this.sourceNode.attr.nodeId +'_stack');
    },

    newIde:function(kw,finalize){
        var mainstack = this.getIdeStack();
        var ide_page = kw.ide_page;
        var ide_name = kw.ide_name || ide_page;
        mainstack._('ContentPane',ide_page,{title:ide_name,_anchor:true,
                                    overflow:'hidden',pageName:ide_page,closable:true,
                                    datapath:'.'+ide_page
                        })._('ContentPane',{remote:this.gi_makeEditorStack,remote_frameCode:ide_page,
                                            overflow:'hidden',
                                            remote__onRemote:finalize});

    },

    openModuleToEditorStack:function(kw,finalize){
        var module = kw.module;
        var ide_page = kw.ide_page || this.getCurrentIdePage();
        var that = this;
        this.selectStackEditor(kw,function(){
            var scNode = that.getStackEditor(kw.ide_page);
            var module = kw.module;
            if(!(module in scNode.widget.gnrPageDict)){
                that.addModuleToEditorStack(ide_page,module,finalize);
                scNode.setRelativeData('.selectedModule',module);
            }else{
                scNode.setRelativeData('.selectedModule',module);
                if(finalize){
                    finalize()
                }
            }
        })  
    },

    addModuleToEditorStack:function(ide_page,module,finalize){
        ide_page = ide_page || this.getCurrentIdePage();
        var scNode = this.getStackEditor(ide_page);
        var label = this.getModuleKey(module);
        var l = module.split('/');
        var title = l[l.length-1];
        scNode._('ContentPane',label,{title:title,datapath:'.editors.page_'+scNode._value.len(),
                                    overflow:'hidden',
                                    pageName:module,closable:true
                                    })._('ContentPane',{remote:this.gi_buildEditorTab,remote_ide_page:ide_page,
                                                        remote_module:module,overflow:'hidden',
                                                        remote__onRemote:finalize})
    },

    getCurrentModule:function(ide_page){
        ide_page = ide_page || this.getCurrentIdePage();
        return this.sourceNode.getRelativeData('.instances.'+ide_page+'.selectedModule');
    },
    getCurrentIdePage:function(){
        return this.sourceNode.getRelativeData('.ide_page');
    },

    getEditorNode:function(module,ide_page){
        ide_page = ide_page || this.getCurrentIdePage();
        module = module || this.getCurrentModule(ide_page);
        return genro.nodeById(ide_page+'_'+this.getModuleKey(module)+'_cm');
    },

    getModuleKey:function(module){
        return module.replace(/[\.|\/]/g,'_');
    },

});
