
dojo.declare("gnr.GnrIde", null, {
    constructor:function(sourceNode){
        this.sourceNode = sourceNode;
        this.debugEnabled = sourceNode.attr.debugEnabled;
        this.gi_buildEditorTab = sourceNode.attr._gi_buildEditorTab;
        this.gi_makeEditorStack = sourceNode.attr._gi_makeEditorStack;

        this.start();
        genro.activeIDE = genro.activeIDE || {};
        genro.activeIDE[this.sourceNode.attr.nodeId] = this;
    },

    start:function(){
        var that = this;
        if(this.debugEnabled){
            genro.wsk.addhandler('do_pdb_out_bag',function(data){that.onPdbAnswer_bag(data);});
            genro.wsk.addhandler('do_pdb_out_line',function(data){that.onPdbAnswer_line(data);});
            genro.wsk.addhandler('do_close_debugger',function(pdb_id){that.closeDebugger(pdb_id);});
        }
        
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
        var debugged_page_id = kw.debugged_page_id;
        mainstack.setRelativeData('.'+ide_page+'.debugged_page_id',debugged_page_id)
        mainstack._('ContentPane',ide_page,{title:ide_name,_anchor:true,
                                    overflow:'hidden',pageName:ide_page,closable:true,
                                    datapath:'.'+ide_page
                        })._('ContentPane',{remote:this.gi_makeEditorStack,remote_frameCode:ide_page,
                                            remote_isDebugger:kw.isDebugger,overflow:'hidden',
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

    onPdbAnswer_line:function(data){
        this.getStackEditor(data.getItem('pdb_id')).setRelativeData('.output_line',data.getItem('line'));
    },
    onPdbAnswer_bag:function(data){
        var status = data.getItem('status');
        var module = status.getItem('module');
        var lineno = status.getItem('lineno');
        var callcounter = data.getItem('callcounter');
        var functionName = status.getItem('functionName');
        var debugged_page_id = data.pop('debugged_page_id')
        var that = this;
        var finalize = function(){
            that.setDebugData(data);
            that.selectLine(lineno);
        }
        this.openModuleToEditorStack({ide_page:data.getItem('pdb_id'),ide_name:data.getItem('methodname'),
                                                module:module,isDebugger:true,debugged_page_id:debugged_page_id},finalize);
     },

    setDebugData:function(data){
        var ideNode = this.getStackEditor();
        ideNode.setRelativeData('.stack',data.getItem('stack'),{caption:'Stack'})
        var result=new gnr.GnrBag();
        result.setItem('locals',data.getItem('current.locals'),{caption:'Locals'})
        var returnValue = data.getItem('current.returnValue');
        var watches = data.getItem('watches');
        if (returnValue!==undefined){
            result.setItem('returnValue',returnValue,{caption:'Return Value'})       
        }
        if (watches){
            result.setItem('watches',watches,{caption:'Watches'})
        }
        ideNode.setRelativeData('.result',result)
        ideNode.setRelativeData('.status',data.getItem('status'));
        
    },
 
    onCreatedEditor:function(sourceNode){
        var that = this;
        sourceNode.watch('externalWidgetReady',function(){
            return sourceNode.externalWidget;
        },function(){
            that.onCreatedEditorDo(sourceNode);
            sourceNode.fireEvent('.editorCompleted')
        })
    },
    onCreatedEditorDo:function(sourceNode){
        var cm = sourceNode.externalWidget;
        // Helper kept on the gnr handler so it is reachable from python-side dataController.
        cm.gnr.gnrMakeMarker = function(conditional){
            var marker = document.createElement('div');
            var _class = conditional ? 'pdb_conditional_breakpoint' : 'pdb_breakpoint';
            genro.dom.addClass(marker, _class);
            marker.innerHTML = "●";
            return marker;
        };
        // gnrSetCurrentLine highlights the line currently being executed under PDB.
        // pdb_currentLine_wrap is the only line class gnride uses, so clearing all
        // before applying the new one is safe and survives editor rebuilds (the
        // previous mark survives via _cm6Snapshot.lineClasses but its id is stale).
        cm.gnrSetCurrentLine = function(line){
            var cm_line = line - 1;
            cm.gnr_clearAllLineClasses();
            cm.currentLine = cm_line;
            // CM6 has a single per-line decoration class slot (no wrap/background/text/gutter
            // distinction like CM5). The legacy classes are merged into pdb_currentLine_wrap.
            cm.gnr_addLineClass(cm_line, 'pdb_currentLine_wrap');
        };
        // gutter click handling has moved to onBreakpointGutterClick, registered from
        // gnride.py via onGutterClick_pdb_breakpoints. No CM5 cm.on('gutterClick') here.
    },
    onBreakpointGutterClick:function(view, line, gutter, evt){
        var sourceNode = view.sourceNode;
        var info = view.gnr_lineInfo(line);
        var evt_type = (info && info.gutterMarkers && info.gutterMarkers[gutter]) ? 'del' : 'ins';
        var code_line = line + 1;
        var modifier = genro.dom.getEventModifiers(evt);
        var module = sourceNode.attr.modulePath;
        var that = this;
        var cb = function(condition){
            var dom = (evt_type === 'del') ? null : view.gnr.gnrMakeMarker(condition);
            view.gnr_setGutterMarker(line, gutter, dom);
            that.setBreakpoint({line: code_line, module: module, condition: condition, evt: evt_type});
        };
        if(modifier === 'Shift'){
            genro.dlg.prompt(_T("Breakpoint condition"), {lbl: _T('Condition'), action: cb});
        } else {
            cb();
        }
    },
    setBreakpoint:function(kw){
        var debugged_page_id = this.getStackEditor().getRelativeData('.debugged_page_id');
        if(debugged_page_id){
            if(kw.evt=='del'){
                this.sendCommand('cl '+kw.module+':'+kw.line);
            }else{
                var cmdstring = 'b '+kw.module+':'+kw.line;
                if(kw.condition){
                    cmdstring+=','+kw.condition;
                }
                this.sendCommand(cmdstring);
            }
            
        }
        genro.publish('setBreakpoint',kw);
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

    selectLine:function(lineno){
        var editorNode = this.getEditorNode();
        var doselect = function(cm){
            cm.gnrSetCurrentLine(lineno);
            cm.gnr_scrollIntoView({line: lineno});
        }
        if(editorNode.externalWidget){
            doselect(editorNode.externalWidget);
        }else{
            editorNode.watch('editorReady',function(){
                return editorNode.externalWidget;
            },function(){
                doselect(editorNode.externalWidget);
            })
        }
    },
    closeDebugger:function(pdb_id){
        var mainstack = this.getIdeStack();
        var instances = this.sourceNode.getRelativeData('.instances');
        if(this.sourceNode.getRelativeData('.ide_page')==pdb_id){
            this.sourceNode.getRelativeData('.ide_page','mainEditor');
        }
        if(instances.getNode(pdb_id)){
            mainstack._value.popNode(pdb_id);
            instances.popNode(pdb_id);
        }
    },

    isDebugging:function(){
        return this.getStackEditor().getRelativeData('.status.functionName') != null;
    },

    clearConsole:function(){
        this.getStackEditor().setRelativeData('.output','')
    },

    sendCommand:function(command,pdb_id){
        genro.wsk.send("pdb_command",{cmd:command,pdb_id:pdb_id || this.getCurrentIdePage()});
    },
    
    do_stepOver:function(){
        this.sendCommand('next')
    },
    do_setBp:function(){
        this.sendCommand('setbp')
    },

    do_stepIn:function(){
        this.sendCommand('step')
    },
    do_stepOut:function(){
        this.sendCommand('return')
    },
    do_continue:function(module){
        this.sendCommand('c')
    },
    do_jump:function(lineno){
        this.sendCommand('jump '+lineno)
    },

    do_level:function(level){
        this.sendCommand('level '+level)
    },

    onSelectStackMenu:function(kw){
        this.do_level(kw.level);
    },

});
