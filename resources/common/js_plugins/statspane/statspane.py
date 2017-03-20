# -*- coding: UTF-8 -*-

# chartmanager.py
# Created by Francesco Porcari on 2017-01-01.
# Copyright (c) 2017 Softwell. All rights reserved.
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method,websocket_method,metadata
from gnr.xtnd.gnrpandas import GnrPandas
from gnr.core.gnrbag import Bag
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrstring import slugify

class StatsCommandForms(object):

    def __init__(self,page=None):
        self.page = page

    def commandlist(self):
        return [(m.__name__[4:],m) for m in [getattr(self,c) for c in dir(self) if c.startswith('cmd_')]]

    @classmethod
    def commandmenubags(cls):
        basecommands = Bag()
        dfcommands = Bag()
        for m in [getattr(cls,c) for c in dir(cls) if c.startswith('cmd_')]:
            b = basecommands if getattr(m,'basecmd',None) else dfcommands
            b.setItem('r_%s' %m.order,None,default_kw=dict(command=m.__name__[4:]),caption=m.name)
        basecommands.sort('#k')
        dfcommands.sort('#k')
        return basecommands,dfcommands

    def pt_fieldsStruct(self,struct):
        r = struct.view().rows()
        r.cell('fieldname',name='Field',width='100%')

    def pt_valuesStruct(self,struct):
        r = struct.view().rows()
        r.cell('fieldname',name='Field',width='100%')
        values = ','.join(GnrPandas.AGGFUNCDICT.keys())
        r.cell('aggregators',name='Aggregators',width='15em',edit=dict(tag='checkBoxText',
                                                                        values=values))



    @metadata(order=0,name='!!Dataframe from db',basecmd=True)
    def cmd_dataframeFromDb(self,sc,**kwargs):
        bc = sc.borderContainer(size_h=300,size_w=400,**kwargs)
        fb = bc.contentPane(region='top',datapath='.record').div(margin_right='30px').formbuilder(colswidth='auto',width='100%',fld_width='100%')
        fb.textbox(value='^.dfname',lbl='Dataframe',validate_notnull='^#FORM.record.command?=#v=="dataframeFromDb"',unmodifiable=True)
        fb.textbox(value='^.comment',lbl='!!Comment')
        fb.textbox(value='^.pars.table',lbl='Table',validate_notnull='^#FORM.record.command?=#v=="dataframeFromDb"')
        fb.textbox(value='^.pars.columns',lbl='Columns')
        fb.simpleTextArea(value='^.pars.where',lbl='Where',height='100px')
        #bc.roundedGroupFrame(title='Extra kwargs',region='center').multiValueEditor(value='^#FORM.record.query_kwargs')

    @metadata(order=0,name='!!Edit dataset')
    def cmd_editDataset(self,sc,**kwargs):
        bc = sc.borderContainer(size_h=400,size_w=550,**kwargs)
        fb = bc.contentPane(region='top').formbuilder(datapath='.record',cols=2)
        fb.textbox(value='^.comment',lbl='!!Comment')
        bc.dataController("SET #FORM.record.pars.edited_dataframe = genro.statspane.parentDataFrame(this);",
                            formsubscribe_onLoaded=True,_if='command == "editDataset" && this.form.isNewRecord()',
                            command='=#FORM.record.command')

        def editable_struct(struct):
            r = struct.view().rows()
            r.cell('fieldname',width='10em',name='Column',edit=True,editDisabled="=#ROW.newserie?=!#v")
            r.cell('name',width='12em',edit=True,name='Name')
            r.cell('datatype',width='12em',name='DataType')
            #r.cell('element_count',width='12em',name='Count')
            r.cell('formula',width='12em',name='Formula',edit=True,editDisabled="=#ROW.newserie?=!#v")

        bc.contentPane(region='center').bagGrid(storepath='#FORM.record.pars.edited_dataframe',
                                                datapath='#FORM.dfeditor',
                                                addrow=True,delrow=True,title='Edit Dataframe',
                                                struct=editable_struct,pbl_classes=True,
                                                grid_addRowMode='>',
                                                default_newserie =True,
                                                margin='2px')


    @metadata(order=1,name='!!New Pivot table')
    def cmd_pivotTable(self,sc,**kwargs):
        mainbc = sc.borderContainer(size_h=600,size_w=740,**kwargs)
        mainbc.dataController("SET #FORM.parentDataframe.store = genro.statspane.parentDataFrame(this);",
                                formsubscribe_onLoaded=True,_if="command=='pivotTable'",command='=#FORM.record.command')
        fb = mainbc.contentPane(region='top').div(margin_right='20px').formbuilder(datapath='.record',cols=3,width='100%',colswidth='auto')
        fb.textbox(value='^.comment',lbl='!!Comment',colspan=3,width='100%')
        fb.textbox(value='^.pars.title',lbl='!!Title',colspan=3,width='100%')
        fb.simpleTextArea(value='^.pars.description',lbl='!!Description',colspan=3,width='100%',height='40px')
        fb.checkbox(value='^.pars.out_html',label='!!Out HTML')
        fb.checkbox(value='^.pars.out_xls',label='!!Out XLS')
        fb.textbox(value='^.pars.dest_dataframe',lbl='!!Out dataframe')
        bc = mainbc.borderContainer(design='sidebar',region='center')


        def picker_struct(struct):
            r = struct.view().rows()
            r.cell('fieldname',width='100%')
            r.cell('datatype',width='6em',name='DataType')

        bc.contentPane(region='left',width='200px').bagGrid(storepath='#FORM.parentDataframe.store',
                                                            datapath='#FORM.parentDataframe',
                                                                    grid_draggable_row=True,
                                                                    grid_dragClass='draggedItem',
                                                                    grid_onDrag='dragValues["statcol"]=dragValues.gridrow.rowset;',
                                                                    grid_selected_fieldname='.selectedField',
                                                                    grid_multiSelect=False,
                                                                    addrow=False,delrow=False,title='Dataframe cols',
                                                                    struct=picker_struct,pbl_classes=True,
                                                                    margin='2px')

        tc = bc.tabContainer(region='center',margin='2px',selectedPage='^#FORM.selectedPage')
        parsbc = tc.borderContainer(title='Pivot parameters',pageName='pivotPars')
        parsbc_top = parsbc.borderContainer(region='top',height='50%')
        commonKw = dict(grid_selfDragRows=True,
                        struct=self.pt_fieldsStruct,addrow=False,
                        grid_dropTarget_grid="statcol",pbl_classes='*',margin='2px',
                        grid_onDrop_statcol="""
                            var storebag = this.widget.storebag();
                            data.forEach(function(n){
                                storebag.setItem(n.fieldname,new gnr.GnrBag({fieldname:n.fieldname}));
                            });
 
                        """)
        parsbc_top.contentPane(region='left',width='50%').bagGrid(title='Index',frameCode='pt_index',storepath='#FORM.record.pars.pivot.index',
                                                          datapath='#FORM.indexgrid',**commonKw)
        parsbc_top.contentPane(region='center').bagGrid(title='Columns',frameCode='pt_columns',storepath='#FORM.record.pars.pivot.columns',
                                                          datapath='#FORM.columnsgrid',**commonKw)
        commonKw['struct'] = self.pt_valuesStruct
        commonKw['pbl_classes'] = True
        parsbc.contentPane(region='center').bagGrid(title='Values',frameCode='pt_values',storepath='#FORM.record.pars.pivot.values',
                                                          datapath='#FORM.valuesgrid',**commonKw)

        filterspane = tc.contentPane(title='Dataset filters',pageName='dfFilters')
        filterspane.dataRpc(None,self.page.statspane_availableFieldValues,httpMethod='WSK',
                     fieldname='^#FORM.parentDataframe.grid.selectedField',dfname='=#FORM.record.dfname',
                     code='=#ANCHOR.statcode',
                     _if="fieldname && _pageName=='dfFilters'",
                     _pageName='^#FORM.selectedPage',
                     _onCalling="""
                     if(_stores && _stores.getNode(fieldname)){
                        FIRE #FORM.loadedFilterData;
                        return false;
                     }
                     """,
                     _onResult="""
                        this.setRelativeData('#FORM.availableFilterValuesGrid.stores.'+kwargs.fieldname,result);
                        FIRE #FORM.loadedFilterData;
                     """,_stores='=#FORM.availableFilterValuesGrid.stores')

        def filters_struct(struct):
            r = struct.view().rows()
            r.cell('_selected',userSets=True,name=' ')
            r.cell('fieldvalue',width='100%')

        frame=filterspane.bagGrid(storepath='^#FORM.availableFilterValuesGrid.currentFilterPath',
                    datapath='#FORM.availableFilterValuesGrid',
                    grid_userSets='.currentCheckeds',
                    grid_identifier='fieldvalue',
                        addrow=False,delrow=False,title='Filter on',
                        struct=filters_struct,margin='2px',pbl_classes=True,datamode='attr')
        frame.grid.dataController("""
            if(_triggerpars.kw.reason=='fieldfilterSet'){
                return;
            }
            this.setRelativeData('#FORM.record.pars.filters.'+fieldname,currentCheckeds);
            """,currentCheckeds='^.currentCheckeds._selected',fieldname='=#FORM.parentDataframe.grid.selectedField',
            _if='fieldname')
        frame.grid.dataController("""
            var fieldFilters = this.getRelativeData('#FORM.record.pars.filters.'+fieldname);
            this.setRelativeData('.currentCheckeds._selected',fieldFilters,null,null,'fieldfilterSet');
            """,currentCheckeds='=.currentCheckeds._selected',fieldname='^#FORM.parentDataframe.grid.selectedField',
            _if='fieldname')
        frame.dataController("""
            SET #FORM.availableFilterValuesGrid.currentFilterPath = '#FORM.availableFilterValuesGrid.stores.'+fieldname;
            """,fieldname='^#FORM.parentDataframe.grid.selectedField',pageName='=#FORM.selectedPage',
            _fired='^#FORM.loadedFilterData',
            _if='fieldname && pageName=="dfFilters"')
        frame.top.bar.replaceSlots('#','#,searchOn,5')


class StatsPane(BaseComponent):
    py_requires="""js_plugins/chartjs/chartjs:ChartPane,
                    gnrcomponents/framegrid:FrameGrid,
                    gnrcomponents/formhandler:FormHandler"""
    js_requires='js_plugins/statspane/statspane'
    css_requires='js_plugins/statspane/statspane'


    @public_method
    def pdstats_remoteCommandGrid(self,pane,table=None,code=None,**kwargs):

        tc = pane.tabContainer(margin='2px')
        pane.sharedObject('.stored_data',shared_id=code,autoSave=True,autoLoad=True)
        tc.pandasCommands(code,table=table,title='!!Commands')
        tc.dataframesManager(code,table=table,title='!!Datasets')
        tc.reportSiteParameters(code,table=table,title='!!Publish')
        pane.dataController("""
            var steprow = commands.getItem(step);
            if(error){
                steprow.setItem('status','ERR');
                steprow.setItem('error',error);
                return;
            }
            steprow.setItem('status','OK');
            steprow.setItem('error',null);
            var newdf = result.getItem('newdataframe');
            if(result.getItem('dataframe_info')){
                this.setRelativeData('.dataframes.store.'+result.getItem('dataframe_info'),
                                      new gnr.GnrBag({name:result.getItem('dataframe_info'),comment:comment,
                                                     store:result.getItem('store')}))
            }
            if(newdf){
                this.setRelativeData('.dataframes.store.'+newdf.getItem('dataframe_info'),
                                      new gnr.GnrBag({name:newdf.getItem('dataframe_info'),
                                                        store:newdf.getItem('store'),comment:comment}))
            }if(result.getItem('parent_dataframe')){
                genro.publish(code+'_stepDone',{step:step,result:result,counter:counter,comment:comment,command:command});
            }
            if(last){
                console.log('last step')
                FIRE #ANCHOR.update_report_site;
            }
            """,code=code,commands='=.stored_data.commands',
            **{'subscribe_%s_pandas_step' %code:True})

    def pdcommand_struct(self,struct):
        r = struct.view().rows()
        r.cell('counter',name='C.',width='3em',counter=True,dtype='L')
        r.cell('_tpl',name='Pars',width='100%',rowTemplate='$dfname <span style="color:blue">$command</span><br/>$comment $error')
        r.cell('status',width='2em',name=' ',
                _customGetter="""function(row){
                    return '<div class="stat_step_status_'+row.status+'">&nbsp;</div>';
                }""")
        r.cell('result_id',hidden=True)

    def pddataframe_struct(self,struct):
        r = struct.view().rows()
        r.cell('name',name='!!Name',width='12em')
        r.cell('comment',name='!!Comment',width='15em')


    @struct_method
    def pdstats_reportSiteParameters(self,parent,code=None,storepath=None,table=None,**kwargs):
        pane = parent.contentPane(**kwargs)
        fb = pane.div(margin_right='20px').formbuilder(datapath='.stored_data.publish_info',width='100%',colswidth='auto',fld_width='100%')
        fb.textbox(value='^.title',lbl='!!Title')
        fb.dateTextBox(value='^.publish_date',lbl='!!Date')
        fb.simpleTextArea(value='^.summary',lbl='!!Summary',height='150px')
        fb.checkbox(value='^.published',label='!!Publish')
        fb.button('Apply',action='FIRE #ANCHOR.update_report_site')
        pane.dataRpc(None,self.pdstats_updateReportSiteInfo,publish_info='=.stored_data.publish_info',table=table,
                    _onResult='SET .stored_data.publish_info.site_ready = true;',
                    _onCalling='console.log("rifaccio il publish info")',code=code,httpMethod='WSK',
                    _if='publish_info.getItem("published")',_fired='^.update_report_site')

        pane.dataFormula('#ANCHOR.report_url','p+"?no_cache=t_"+(new Date().getTime())',_onBuilt=True,
            p='/_site/pd_reports/%s/index.html' %code,**{'subscribe_%s_report_site_updated' %code:True})
        pane.dataFormula('#ANCHOR.report_site_active',"(published === true && site_ready === true)",site_ready='^.stored_data.publish_info.site_ready',
                        published='^.stored_data.publish_info.published',_delay=1)


    @struct_method
    def pdstats_dataframesManager(self,parent,code=None,storepath=None,table=None,**kwargs):
        bc = parent.borderContainer(**kwargs)
        frame = bc.bagGrid(frameCode='V_dataframes_%s' %code,title='Dataframes',datapath='.dataframes',
                            storepath=storepath,
                            grid_canSort=False,
                            _class='noheader',
                            addrow=False,delrow=False,struct=self.pddataframe_struct,
                            grid_selectedId='#ANCHOR.dataframes.selectedDataframe',
                            grid_identifier='name',
                            grid_multiSelect=False,
                            region='top',height='200px')
        tc = bc.tabContainer(region='center',margin='2px')

        def infostruct(struct):
            r = struct.view().rows()
            r.cell('fieldname',width='10em',name='Column')
            r.cell('name',width='12em',name='Name')
            r.cell('datatype',width='7em',name='DataType')
            r.cell('element_count',width='3em',name='Count')
            #r.cell('formula',width='12em',name='Formula',edit=True,editDisabled="=#ROW.newserie?=!#v")

        frame.dataFormula('.currentInfoPath',"'#ANCHOR.dataframes.store.'+dfname+'.store'",dfname='^#ANCHOR.dataframes.selectedDataframe',
            _if='dfname',_delay=1,_else='return ".dummypath"')

        tc.contentPane(title='Info').bagGrid(storepath='^#ANCHOR.dataframes.currentInfoPath',
                                            datapath='.dataframes.infogrid',
                                                addrow=False,delrow=False,title='Info',
                                                struct=infostruct,pbl_classes=True,                                                
                                                margin='2px')
        f = tc.contentPane(title='Commands').bagGrid(storepath='#ANCHOR.stored_data.commands',
                                            datapath='.dataframes.commandsgrid',
                                                title='Commands',grid_autoSelect=True,
                                                grid_excludeCol='code',
                                                grid_excludeListCb="""
                                                var result = [];
                                               var selectedDataframe= this.getRelativeData('#ANCHOR.dataframes.selectedDataframe');
                                               if (selectedDataframe){
                                                   var store = this.store.getData().getNodes();
                                                   store.forEach(function(n,idx){
                                                       var v = n.getValue();
                                                       var dfname = v.getItem('dfname');
                                                       if(dfname!=selectedDataframe){
                                                           result.push(v.getItem('code'))
                                                       }
                                                   },'static');
                                               }
                                               return result;
                                                """,
                                                struct=self.pdcommand_struct,pbl_classes='*',   
                                                addrow=False,delrow=True,   
                                                grid_selectedId='#ANCHOR.dfcommands.grid.selectedCommand',                                          
                                                margin='2px',grid_identifier='code',
                                                grid_multiSelect=False)
        bc.dataController("""
            g.filterToRebuild(true);
            g.updateRowCount('*');
            var that = this;
            setTimeout(function(){
                if(g.collectionStore().len(true)){
                     g.selection.select(0);
                }else{
                    that.setRelativeData('#ANCHOR.dfcommands.grid.selectedCommand',null);
                }
            },1)
            """,g=f.grid.js_widget,selectedDataframe='^#ANCHOR.dataframes.selectedDataframe')


    @struct_method
    def pdstats_pandasCommands(self,parent,code=None,table=None,**kwargs):
        storepath = '#ANCHOR.stored_data.commands'
        pane = parent.contentPane(**kwargs)
        frame = pane.bagGrid(frameCode='V_commands_%s' %code,title='Stats commands',datapath='.dfcommands',
                            storepath=storepath,
                            grid_canSort=False,
                            _class='noheader',
                            addrow=False,delrow=True,struct=self.pdcommand_struct,
                            grid_selectedId='^.selectedCommand',
                            grid_identifier='code',
                            grid_multiSelect=False)
        frame.grid.dataController("""
            var viewerNode = this.getRelativeData('#ANCHOR.viewer.rows.'+selectedCommand);
            SET #ANCHOR.selectedStep = viewerNode?selectedCommand:'emptyStep';
            """,selectedCommand='^.selectedCommand',_if='selectedCommand',_else='SET #ANCHOR.selectedStep = "emptyStep"')
        frame.grid.dataController("""
            SET .selectedCommand = selectedStep;
            """,selectedStep='^#ANCHOR.selectedStep',_if='selectedStep && selectedStep!="emptyStep"')
        frame.dataController("""if(_reason=='child' && _triggerpars.kw.evt=='del'){
                var parent_lv = _node.parentshipLevel(commands);
                if(parent_lv==1){
                    genro.publish(code+'_stepRemoved',{step:_node.getValue().getItem('code')});
                }
            }""", commands='^%s' %storepath,code=code)


        bar = frame.top.bar.replaceSlots('delrow','delrow,addrow,5',
                                    addrow_defaults='.menucommands')
        footer = frame.bottom.slotToolbar('5,*,clear_res,5,run,10')
        footer.clear_res.slotButton('Clear',action="""if(commands){commands.values().forEach(function(v){v.setItem('status','NO')})}""",
            commands='=%s' %storepath)
        footer.run.slotButton('Run',action='FIRE .runCommands;')

        footer.dataRpc(None,self.statspane_runCommands,_allcommands='=%s' %storepath,code=code,
                        _fired='^.runCommands',httpMethod='WSK',
                        _onCalling="""
                            if(!_allcommands || _allcommands.len()===0){
                                return false;
                            }
                            var filteredCommands = new gnr.GnrBag();
                            var first = _allcommands.getNodeByValue('status','TC');
                            if(!first){
                                first = _allcommands.getNodeByValue('status','NO');
                            }
                            if(!first){
                                return false;
                            }
                            _allcommands.getNodes().slice(_allcommands.index(first.label)).forEach(function(n){
                                filteredCommands.setItem(n.label,n._value);
                            });
                            kwargs.commands = filteredCommands;
                        """,_lockScreen=True)
        basecommands,dfcommands = StatsCommandForms.commandmenubags()
        frame.data('.basecommands',basecommands)
        frame.data('.dfcommands',dfcommands)

        frame.dataController("""var dataframesPath = this.absDatapath('#ANCHOR.dataframes.store');
                                var cb = function(){
                                    return genro.statspane.commandMenu(genro.getData(dataframesPath),basecommands,dfcommands,{table:table});
                                };
                                SET .menucommands = new gnr.GnrBagCbResolver({method:cb});
                                """,
                        _onBuilt=True,basecommands='=.basecommands',dfcommands='=.dfcommands',
                        table=table)

        #[(caption,dict(command=command)) for order,command,caption in StatsCommandForms.commandlist()]

        form = frame.grid.linkedForm(frameCode='F_commands_%s' %code,
                                 datapath='.dfcommands.form',loadEvent='onRowDblClick',
                                 dialog_height='300px',dialog_width='400px',
                                 dialog_title='Command',handlerType='dialog',
                                 dialog_nodeId='command_dialog_%s' %code,
                                 childname='form',attachTo=pane,store='memory',default_data_type='T',
                                 store_pkeyField='code',dialog_noModal=False,store_newPkeyCb="return 'c_'+new Date().getTime()")
        form.dataController("""grid.updateCounterColumn();
            if(doRunCommand){
                FIRE #ANCHOR.dfcommands.runCommands;
            }
            """,formsubscribe_onDismissed=True,
            grid=frame.grid.js_widget,doRunCommand='=#FORM.controller.temp.doRunCommand')

        sc = form.center.stackContainer(selectedPage='^.record.command',
                                    selfsubscribe_selected="""
                                        if($1.selected){
                                            var sizer = objectExtract(this.widget.gnrPageDict[p_0.page].sourceNode.attr,'size_*',true);
                                            var dialogNode= genro.nodeById('command_dialog_%s') //.resize();
                                            var form = this.form;
                                            dialogNode.widget.resize(sizer);
                                            dialogNode.widget.adjustDialogSize();
                                            setTimeout(function(){
                                                form.sourceNode.widget.resize({w:sizer.w});
                                            },1);
                                        }
                                    """ %code)
        bar = form.bottom.slotBar('*,cancel,savebtn,saveAndRun',margin_bottom='2px',_class='slotbar_dialog_footer')
        fh = StatsCommandForms(self)
        for commandname,commandhandler in fh.commandlist():
            commandhandler(sc,pageName=commandname)
        bar.cancel.button('!!Cancel',action='this.form.abort();')
        bar.savebtn.button('!!Save',iconClass='fh_semaphore',action="""
                                SET #FORM.record.status = 'TC';
                                this.form.publish("save",{destPkey:"*dismiss*"})""")
        bar.saveAndRun.button('!!Save and run',
                        iconClass='fh_semaphore',action="""SET #FORM.record.status = 'TC';
                                        this.form.publish("save",{destPkey:"*dismiss*"});
                                        SET #FORM.controller.temp.doRunCommand = true;
                                        """)

    def getGnrPandas(self,pandasdata,code=None):
        gp = pandasdata.get(code)
        if not gp:
            csspath = self.site.getStaticPath('rsrc:common','js_plugins','statspane','report.css')
            with open(csspath,'r') as f:
                css = f.read()

            gp = GnrPandas(language=self.language,stats_code=code,
                            report_folderpath=self.site.getStaticPath('site:pd_reports',code),
                            report_folderurl=self.site.getStaticUrl('site:pd_reports',code),
                             report_cssbase=css)
            pandasdata[code] = gp
        return gp

    @websocket_method
    def statspane_runCommands(self,commands=None,code=None):
        topic = '%s_pandas_step'%code
        with self.sharedData('pandasdata') as pandasdata:
            gp = self.getGnrPandas(pandasdata,code) 
            for i,n in enumerate(commands):
                error = None
                v = n.value
                try:
                    result = getattr(self,'statspane_run_%(command)s' %v)(gnrpandas=gp,dfname=v['dfname'],counter=v['counter'],
                                                                        comment=v['comment'],**v['pars'].asDict(ascii=True))

                except Exception as e:
                    result = None
                    error = str(e)
                    raise

                self.clientPublish(topic,result=result,
                                        step=n.label,counter=v['counter'],
                                        comment=v['comment'],
                                        command=v['command'],error=error,
                                        last=(i+1==len(commands)))
                if error:
                    return                

    @websocket_method
    def statspane_availableFieldValues(self,code=None,dfname=None,fieldname=None):
        result = Bag()
        with self.sharedData('pandasdata') as pandasdata: 
            gp = self.getGnrPandas(pandasdata,code) 
        gnrdf = gp.dataframes[dfname]
        df = gnrdf.dataframe
        for i,v in enumerate(df[fieldname].unique()):
            if v is not None:
                result.setItem('r_%s' %i,None,fieldvalue=v)
        return result

    def statspane_run_dataframeFromDb(self,gnrpandas=None,dfname=None,table=None,where=None,condition=None,columns=None,
                           selectionKwargs=None,comment=None,**kwargs):
        if selectionKwargs:
            kwargs.update(selectionKwargs)
        if isinstance(where,Bag):
            where,kwargs = self.db.table(table).sqlWhereFromBag(where, kwargs)
        if condition:
            where = ' ( %s ) AND ( %s ) ' % (where, condition) if where else condition
        gnrpandas.dataframeFromDb(dfname=dfname,db=self.db,tablename=table,where=where,condition=condition,
                                columns=columns,comment=comment,**kwargs)
        return Bag(store=gnrpandas[dfname].getInfo(),dataframe_info=dfname)

    @websocket_method
    def pdstats_updateReportSiteInfo(self,code=None,publish_info=None,table=None,**kwargs):
        with self.sharedData('pandasdata') as pandasdata: 
            gp = self.getGnrPandas(pandasdata,code)
            gp.updatePublishInfo(**publish_info.asDict(ascii=True))
            self.clientPublish('%s_report_site_updated' %code,code=code)


    def statspane_run_pivotTable(self,gnrpandas=None,dfname=None,name=None,pivot=None,filters=None,
                                dest_dataframe=None,comment=None,out_html=None,out_xls=None,title=None,counter=None,**kwargs):
        
        if out_html:
            title = title or 'Pivot table %s' %counter
            out_html = Bag(code=slugify('step_%s_%s' %(title,counter)),title=title,
                            comment=comment or '')
        if out_xls:
            title = title or comment or 'Pivot table'
            out_xls = Bag(code=slugify('step_%s_%s' %(title,counter)),title=title)
        pt,store =  gnrpandas[dfname].pivotTableGrid(index=pivot['index'],values=pivot['values'],
                                                columns=pivot['columns'],filters=filters,out_html=out_html,
                                                out_xls=out_xls)
        result = Bag(store=store,parent_dataframe=dfname)

        if dest_dataframe:
            info = gnrpandas.registerDataFrame(dfname=dest_dataframe,dataframe=pt,comment=comment)
            result['newdataframe'] = Bag(store=info,dataframe_info=dest_dataframe)
        return result

    def statspane_run_editDataset(self,gnrpandas=None,dfname=None,edited_dataframe=None,comment=None,**kwargs):
        gnrdf = gnrpandas[dfname]
        if comment:
            gnrdf.comment = comment
        result = gnrdf.applyChanges(edited_dataframe)
        return Bag(store=result,dataframe_info=dfname)

