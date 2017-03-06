# -*- coding: UTF-8 -*-

# chartmanager.py
# Created by Francesco Porcari on 2017-01-01.
# Copyright (c) 2017 Softwell. All rights reserved.
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrasync import SharedObject
from gnr.core.gnrdecorator import public_method,metadata
from gnr.xtnd.gnrpandas import GnrPandas
from gnr.core.gnrbag import Bag
from gnr.web.gnrwebstruct import struct_method



class StatsCommandForms(object):

    def __init__(self,page=None):
        self.page = page

    @classmethod
    def commandlist(cls):
        z = [(m.order,m.__name__[4:],m.name) for m in [getattr(cls,c) for c in dir(cls) if c.startswith('cmd_')]]
        return sorted(z)

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


    @metadata(order=0,name='!!Dataframe from db',basecmd=True)
    def cmd_dataframeFromDb(self,pane):
        bc = pane.borderContainer()
        fb = bc.contentPane(region='top').formbuilder()
        fb.textbox(value='^.dfname',lbl='Dataframe',validate_notnull=True,unmodifiable=True)
        fb.textbox(value='^.pars.table',lbl='Table',validate_notnull=True)
        fb.textbox(value='^.pars.where',lbl='Where')
        fb.textbox(value='^.pars.columns',lbl='Columns')
        #bc.roundedGroupFrame(title='Extra kwargs',region='center').multiValueEditor(value='^#FORM.record.query_kwargs')

    @metadata(order=0,name='!!New Pivot table',)
    def cmd_pivotTable(self,pane):
        pass

class PdCommandsGrid(BaseComponent):
    js_requires='js_plugins/statspane/pandas'
    py_requires="""public:Public,
                   gnrcomponents/framegrid:FrameGrid,
                    gnrcomponents/formhandler:FormHandler"""

    @public_method
    def pdstats_commandForm(self,pane,command=None,**kwargs):
        fh = StatsCommandForms(self)
        getattr(fh,'cmd_%s' %command)(pane)


    def pdcommand_struct(self,struct):
        r = struct.view().rows()
        r.cell('counter',name='C.',width='3em',counter=True,dtype='L')
        r.cell('dfname',name='Dataframe',width='7em')
        r.cell('command',name='Command',width='10em')
        r.cell('_tpl',name='Pars',width='100%',_customGetter="""function(row){
                //objectExtract(row,'counter,command,done,code');
                var v = new gnr.GnrBag(row.pars);
                return v.getFormattedValue()
            }
            """)
        r.cell('done',dtype='B',semaphore=True)

    @struct_method
    def pdstats_pdCommandsGrid(self,pane,code=None,storepath=None,**kwargs):

        frame = pane.bagGrid(frameCode='V_%s' %code,title='Stats commands',datapath='.pdcommands',storepath=storepath,
                            grid_canSort=False,
                            addrow=False,delrow=True,struct=self.pdcommand_struct,**kwargs)
        frame.top.bar.replaceSlots('delrow','delrow,addrow',
                                    addrow_defaults='.menucommands')
        basecommands,dfcommands = StatsCommandForms.commandmenubags()
        frame.data('.basecommands',basecommands)
        frame.data('.dfcommands',dfcommands)
        frame.dataController("""var cb = function(){
                                    var currentCommands = g.storebag();
                                    return pandas_commands_manager.commandMenu(currentCommands,basecommands,dfcommands);
                                };
                                SET .menucommands = new gnr.GnrBagCbResolver({method:cb});
                                """,
                        _onStart=True,basecommands='=.basecommands',dfcommands='=.dfcommands',g=frame.grid.js_widget)

        #[(caption,dict(command=command)) for order,command,caption in StatsCommandForms.commandlist()]

        form = frame.grid.linkedForm(frameCode='F_%s' %code,
                                 datapath='.pdcommands.form',loadEvent='onRowDblClick',
                                 dialog_height='300px',dialog_width='400px',
                                 dialog_title='Command',handlerType='dialog',
                                 childname='form',attachTo=pane,store='memory',default_data_type='T',
                                 store_pkeyField='code',modal=True)
        form.dataController("""grid.updateCounterColumn();
            """,formsubscribe_onDismissed=True,grid=frame.grid.js_widget)

        form.center.contentPane(datapath='.record').contentPane().remote(self.pdstats_commandForm,command='^.command')
        bar = form.bottom.slotBar('*,cancel,savebtn',margin_bottom='2px',_class='slotbar_dialog_footer')
        bar.cancel.button('!!Cancel',action='this.form.abort();')
        bar.savebtn.button('!!Save',iconClass='fh_semaphore',action='this.form.publish("save",{destPkey:"*dismiss*"})')


class StatsPane(BaseComponent):
    py_requires='js_plugins/chartjs/chartjs:ChartPane'
    js_requires='js_plugins/statspane/statspane'
    css_requires='js_plugins/statspane/statspane'


    @public_method
    def pdstats_configuratorTabs(self,pane,table=None,dfname=None,query_pars=None,connectedWidgetId=None,**kwargs):
        query_pars = query_pars or {}
        if query_pars:
            query_pars['where'] = query_pars.pop('_')
        bc = pane.borderContainer()
        top = bc.contentPane(region='top',border_bottom='1px solid silver')
        fb = top.formbuilder(cols=2,border_spacing='3px',_anchor=True)
        fb.button('Load',fire='#WORKSPACE.df.load_dataframe')
        fb.dataRpc('#WORKSPACE.df.info.store',self.dataframeFromDb,
                    _connectedWidgetId=connectedWidgetId,
                    _fired='^#WORKSPACE.df.load_dataframe',
                    tablename=table,dfname=dfname,
                    _onCalling="""
                        genro.statspane.queryParsFromGrid(kwargs);
                    """,
                    _onResult='FIRE #WORKSPACE.df.loadedDataframe',
                    _lockScreen=True,timeout=300000,
                    **query_pars)
        tc = bc.tabContainer(region='center',margin='2px')
        self.dataFrameCoords(tc.borderContainer(title='Dataframe'),table=table,dfname=dfname)
        self.pivotTables(tc.borderContainer(title='Pivot',_class='noheader'),table=table,dfname=dfname)        


    def dataFrameCoords(self,bc,table=None,dfname=None):
        frame = bc.contentPane(region='top',height='50%').bagGrid(frameCode='dataFrameInfo',storepath='.store',title='DF coords',
                                                                datapath='#WORKSPACE.df.info',
                                                                struct=self.dfcoords_struct,
                                                                grid_selfDragRows=True,
                                                                addrow=True,delrow=True)
        bar = frame.bottom.slotBar('*,updateDataframe,5',margin_bottom='2px',_class='slotbar_dialog_footer')
        bar.updateDataframe.slotButton('Update',fire='#WORKSPACE.df.update')
        bc.dataRpc('#WORKSPACE.df.info.store',self.updateDataframe,table='=#WORKSPACE.df.table',limit='=#WORKSPACE.df.limit',
                    dfname='=#WORKSPACE.df.dfname',info='=#WORKSPACE.df.info.store',_fired='^#WORKSPACE.df.update')

    def pivotTablesStruct(self,struct):
        r = struct.view().rows()
        r.cell('_tpl',_customGetter="""
            function(row){
                var b = new gnr.GnrBag(row);
                return b.getFormattedValue();
            }
            """,width='100%')


    def pivotTables(self,bc,table=None,dfname=None):
        view = bc.contentPane(region='bottom',height='40%').bagGrid(title='Stored pivots',frameCode='V_%s_pivotTable' %dfname,storepath='.store',
                                                                    datapath='#WORKSPACE.df.storedPivots',
                                                                    struct=self.pivotTablesStruct,
                                                                    addrow=False,delrow=True)
        self.pivotTableForm(view.grid.linkedForm(frameCode='F_%s_pivotTable' %dfname,
                                 datapath='#WORKSPACE.df.storedPivots.form',loadEvent='onRowDblClick',
                                 handlerType='border',
                                 childname='form',attachTo=bc,
                                 formRoot=bc.contentPane(region='center'),
                                 store='memory',
                                 store_pkeyField='code'),table=table,dfname=dfname)



    def pivotTableForm(self,form,table=None,dfname=None):
        topbar = form.top.slotToolbar('10,ftitle,*')
        bottom = form.bottom.slotBar('5,clearCurrent,savePivot,*,runCurrent,5',margin_bottom='2px',_class='slotbar_dialog_footer')

        topbar.ftitle.div("^#FORM.record.code?=#v?'Pivot:'+#v:'Pivot'",font_size='.9em',color='#666',font_weight='bold')
        form.dataController("this.form.reset();this.form.newrecord();",_fired='^#WORKSPACE.df.loadedDataframe')
        bottom.clearCurrent.slotButton('Clear',action="""
            this.form.reset();
            this.form.newrecord();
            """)
        bottom.runCurrent.slotButton('Run',fire='.run')
        form.dataRpc('#WORKSPACE.pivot.result',self.getPivotTable,data='=#FORM.record',
                    dfname=dfname,table=table,_fired='^.run')
        bottom.savePivot.slotButton('Save',#iconClass="iconbox save",
                                parentForm=True,
                                ask=dict(askIf="!code",title='Save new pivot',askOn='Shift',
                                        fields=[dict(name='code',lbl='Code')]),
                                action="""
                                SET #FORM.record.code = code;
                                this.form.save();
                                """,code='=#FORM.record.code')

        bc = form.center.borderContainer(design='sidebar')

        def picker_struct(struct):
            r = struct.view().rows()
            r.cell('fieldname',width='100%')
        bc.contentPane(region='left',width='140px').bagGrid(storepath='#WORKSPACE.df.info.store',
                                                            datapath='#FORM.available_df_cols',
                                                                    grid_draggable_row=True,
                                                                    grid_dragClass='draggedItem',
                                                                    grid_onDrag='dragValues["statcol"]=dragValues.gridrow.rowset;',
                                                                    addrow=False,delrow=False,title='Dataframe cols',
                                                                    struct=picker_struct)

        commonKw = dict(grid_selfDragRows=True,
                        struct=self.pt_fieldsStruct,addrow=False,
                        grid_dropTarget_grid="statcol",
                        grid_onDrop_statcol="""
                            var storebag = this.widget.storebag();
                            data.forEach(function(n){
                                storebag.setItem(n.fieldname,new gnr.GnrBag({fieldname:n.fieldname}));
                            });

                        """)
        bc.contentPane(region='top',height='33%').bagGrid(title='Index',frameCode='pt_index',storepath='#FORM.record.index',
                                                          datapath='#FORM.indexgrid',**commonKw)
        bc.contentPane(region='bottom',height='33%').bagGrid(title='Values',frameCode='pt_values',storepath='#FORM.record.values',
                                                          datapath='#FORM.valuesgrid',**commonKw)
        bc.contentPane(region='center').bagGrid(title='Columns',frameCode='pt_columns',storepath='#FORM.record.columns',
                                                          datapath='#FORM.columnsgrid',**commonKw)

    def pt_fieldsStruct(self,struct):
        r = struct.view().rows()
        r.cell('fieldname',name='Field',width='100%')

    def dfcoords_struct(self,struct):
        r = struct.view().rows()
        r.cell('fieldname',name='Field',width='10em')
        #r.cell('dataType',name='Dtype',width='5em')
        r.cell('name',name='Label',width='12em',edit=True)
        r.cell('element_count',name='C.',width='4em',dtype='L')

    @public_method
    def dataframeFromDb(self,dfname=None,tablename=None,where=None,condition=None,columns=None,statname=None,selectionKwargs=None,**kwargs):
        statname = statname or dfname
        path = self.site.getStaticPath('page:stats',statname)
        if selectionKwargs:
            kwargs.update(selectionKwargs)
        if isinstance(where,Bag):
            where,kwargs = self.db.table(tablename).sqlWhereFromBag(where, kwargs)
        if condition:
            where = ' ( %s ) AND ( %s ) ' % (where, condition) if where else condition
        gp = GnrPandas()
        #with GnrPandas(path) as gp:
        gp.dataframeFromDb(dfname=dfname,db=self.db,tablename=tablename,where=where,condition=condition,
                                columns=columns,**kwargs)
        gp.save(path)
        return gp[dfname].getInfo()

    @public_method
    def updateDataframe(self,dfname=None,statname=None,info=None,**kwargs):
        statname = statname or dfname
        path = self.site.getStaticPath('page:stats',statname)
        gp = GnrPandas()
        gp.load(path)

        #return gnrdf.getInfo()

    @public_method
    def getPivotTable(self,dfname=None,data=None,statname=None,**kwargs):
        statname = statname or dfname
        path = self.site.getStaticPath('page:stats',statname)
        gp = GnrPandas()
        gp.load(path)
        #with GnrPandas(path) as gp:
        return gp[dfname].pivotTableGrid(index=data['index'].keys() if data['index'] else None,
                                    values=data['values'].keys() if data['values'] else None,
                                    columns=data['columns'].keys() if data['columns'] else None)


class GnrPandasSharedStore(SharedObject):
        
    def onInit(self,**kwargs):
        print 'onInit',self.shared_id
        
    def onSubscribePage(self,page_id):
        print 'onSubscribePage',self.shared_id,page_id
        
    def onUnsubscribePage(self,page_id):
        print 'onUnsubscribePage',self.shared_id,page_id
    
    def onDestroy(self):
        print 'onDestroy',self.shared_id
    

