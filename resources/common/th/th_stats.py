# -*- coding: UTF-8 -*-
#--------------------------------------------------------------------------
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import public_method,extract_kwargs
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrbag import Bag

try:
    import pandas as pd
    import numpy as np
    from gnr.xtnd.gnrpandas import GnrDbDataframe
except Exception:
    pd = False
    np = False
    GnrDbDataframe = False

class TableHandlerStats(BaseComponent):
    js_requires='th/th_stats'
    @extract_kwargs(condition=dict(slice_prefix=False))
    @struct_method
    def th_tableHandlerStats(self,pane,table=None,
                            relation_field=None,
                            relation_value=None,
                            default_rows=None,
                            default_values=None,
                            default_columns=None,
                            condition=None,
                            condition_kwargs=None,
                            nodeId=None,
                            statIdentifier=None,**kwargs):
        if not pd:
            pane.div('Missing Pandas')
        nodeId = nodeId or 'th_stats_%s' %table.replace('.','_')
        bc = pane.borderContainer(datapath='.%s' %nodeId,_anchor=True,**kwargs)
        inattr = pane.getInheritedAttributes()
        relatedTable = inattr.get('table')
        relatedTableHandlerFrameCode = inattr.get('frameCode') if not relation_value else None
        bc.child('_tableHandlerStatsLayout',region='center',
                            table=table,nodeId=nodeId,
                            relation_field=relation_field,
                            relation_value=relation_value.replace('^','') if relation_value else None,
                            default_rows=default_rows,
                            default_values=default_values,
                            default_columns=default_columns,
                            condition=condition,
                            relatedTable=relatedTable,
                            relatedTableHandlerFrameCode=relatedTableHandlerFrameCode,
                            condition_kwargs=condition_kwargs,
                            userObjectId=statIdentifier,**kwargs)
        
        indipendentQuery = relation_value or condition
        bc.dataController("""
           if(autorun){
               var that = this;
               genro.callAfter(function(){
                   that.fireEvent('.stats.run_pivot_do',true);
               },2000,this,'stast_run');
           }
        """,relation_value=relation_value,
            filters='^.stats.filters',
            stat_rows='^.stats.conf.rows',
            stat_values='^.stats.conf.values',
            stat_columns='^.stats.conf.columns',
            autorun='=.stats.autorun',
            #_delay=2000,
            bcNode=bc)
        if not indipendentQuery:
            bc.dataController("FIRE .stats.run_pivot_do",_runQuery='^.#parent.runQueryDo')
        bc.dataRpc(None,self.ths_getPivotTable,
                    table=table,
                    relatedTable=relatedTable,
                    relation_field=relation_field,
                    relation_value=relation_value.replace('^','=') if relation_value else None,
                    mainfilter = '=.stats.filters.%s' %relation_field if relatedTable and not relation_value else None,
                    condition=condition,
                    filters='=.stats.filters',
                    stat_rows='=.stats.conf.rows',
                    stat_values='=.stats.conf.values',
                    stat_columns='=.stats.conf.columns',
                    relatedTableHandlerFrameCode=relatedTableHandlerFrameCode,
                    _lockScreen=True,
                    _onCalling="""
                        if(!genro.dom.isVisible(_bcNode)){
                            return false;
                        }
                        if(relatedTableHandlerFrameCode){
                            var selectionAttributes = genro.wdgById(relatedTableHandlerFrameCode+'_grid').collectionStore().storeNode.currentAttributes()
                            objectExtract(selectionAttributes,'table,columns,checkPermissions');
                            objectUpdate(kwargs,selectionAttributes);
                        }
                        SET .stats.pivot_html = "";
                        if (!(stat_values && stat_values.len() && stat_rows && stat_rows.len())){
                            return false;
                        }
                    """,
                    _if='',
                    outmode='^.stats.run_pivot_do',
                    _onResult="""
                        result = result || new gnr.GnrBag();
                        SET .stats.pivot_grid = result.popNode('pivot_grid')
                        SET .stats.pivot_html = result.getItem('pivot_html')
                        if(result.getItem('xls_url')){
                            genro.download(result.getItem('xls_url'));
                        }
                    """,_bcNode=bc,**condition_kwargs)

        
    @public_method
    def _ths_configurator(self,pane,table=None,relation_field=None,
                                relation_value=None,condition=None,
                                relatedTableHandlerFrameCode=None,
                                relatedTable=None,source_filters=None,**kwargs):
        tc = pane.tabContainer(region='left',width='250px',margin='2px',drawer=True,splitter=True)
        self._ths_configPivotGrids(tc.borderContainer(title='!!Pivot'))
        self._ths_configFields(tc.borderContainer(title='!!Fields'))

        if relatedTable:
            tblobj = self.db.table(relatedTable)
            caption_field = tblobj.attributes.get('caption_field')
            if caption_field and relatedTable and not relation_value:
                self._ths_mainFilter(tc.contentPane(title='!!Main'),
                                relatedTableHandlerFrameCode=relatedTableHandlerFrameCode,
                                table=relatedTable,relation_field=relation_field) 
        self._ths_filters(tc.contentPane(title='!!Filters'),table=table,source_filters=source_filters)

    @public_method
    def _ths_viewer(self,pane,table=None,relation_field=None,default_columns=None,
                    default_rows=None,default_values=None,relation_value=None,**kwargs):
        
        frame = pane.framePane()
        frame.data('.stats.conf',self.ths_configPivotTreeData(table,relation_field=relation_field,
                                                    default_columns=default_columns,
                                                    default_rows=default_rows,
                                                    default_values=default_values))
        self._ths_fill_filtersData(pane,table)

        sc = frame.center.stackContainer()
        iframe = self._ths_framehtml(sc.contentPane(title='Html'))
        #tc = center.tabContainer()
        grid = sc.contentPane(title='!!Grid').quickGrid('^.stats.pivot_grid')
        #grid.tools('export')
        bar = frame.top.slotToolbar('2,stackButtons,*,autorun,10,printStats,exportStats,5')
        bar.autorun.checkbox(value='^.stats.autorun',label='!!Autorun',
                            validate_onAccept="""
                                if(value){
                                    FIRE .stats.run_pivot;
                                }
                            """,default_value=True if relation_value else False)
        bar.printStats.slotButton('!!Print',action="genro.dom.iFramePrint(_iframe)",iconClass='iconbox print',
                                _iframe=iframe.js_domNode)
        bar.exportStats.slotButton('!!Export',iconClass='iconbox export',fire_xls='.stats.run_pivot_do')


    def _ths_mainFilter(self,pane,table=None,relatedTableHandlerFrameCode=None,relation_field=None):
        tblobj = self.db.table(table)
        caption_field = tblobj.attributes.get('caption_field')
        def struct(struct):
            r = struct.view().rows()
            if relation_field:
                r.cell(relation_field.replace('.','_').replace('@','_'), userSets=True, name=' ')
            r.fieldcell(caption_field,
                        width='100%',
                        name=tblobj.attributes['name_long'])
        pane.dataFormula("#ANCHOR.stats.filters.%s" %relation_field, 'mainfilterPkeys',
                        mainfilterPkeys='^#ANCHOR.stats._checked_mainfilter.%s' %relation_field)
        pane.frameGrid(datapath='.stats.mainfilter',table=table,
                        grid_store='%s_grid' %relatedTableHandlerFrameCode,
                        _newGrid=True,
                        grid_userSets='#ANCHOR.stats._checked_mainfilter',
                        struct=struct)

    def _ths_filters(self,pane,table=None,source_filters=None):
        tblobj = self.db.table(table)
        if not source_filters:
            return
        for n in source_filters:
            v = n.value
            label = n.label
            title = n.attr.get('title') or tblobj.column(label).attributes.get('name_long') or label
            titlepane = pane.titlePane(title=title,margin='2px')
            if isinstance(v,basestring):
                titlepane.checkBoxText(value='^.%s' %label,
                                        values='^#ANCHOR.stats.source_filters.%s' %label,
                                        datapath='.stats.filters',
                                        cols=1)
            if isinstance(v,Bag):
                titlepane.tree(storepath='.stats.source_filters.%s' %label,
                        checked_id='.stats.filters.%s' %label,
                        labelAttribute='caption',hideValues=True,
                        margin='2px')

    def _ths_fill_filtersData(self,pane,table):
        tblobj = self.db.table(table)
        if not hasattr(tblobj,'stats_filters'):
            return
        filtersbag = tblobj.stats_filters()
        pane.data('.stats.source_filters',filtersbag)
        for n in filtersbag:
            v = n.value
            label = n.label
            defaults = n.attr.get('defaults')
            pane.data('.stats.filters.%s' %label,defaults)

    def _ths_framehtml(self,pane,**kwargs):
        iframe = pane.div(_class='scroll-wrapper').htmliframe(height='100%',width='100%',border=0)
        pane.dataController("""var cw = _iframe.contentWindow;
                        var cw_body = cw.document.body;
                        if(genro.isMobile){
                            cw_body.classList.add('touchDevice');
                        }
                        var e = cw.document.createElement("link");
                        e.href = styleurl;
                        e.type = "text/css";
                        e.rel = "stylesheet";
                        //e.media = "screen";
                        cw.document.getElementsByTagName("head")[0].appendChild(e);
                        cw_body.classList.add('bodySize_'+genro.deviceScreenSize);
                        cw_body.classList.add('report_content');
                        cw_body.innerHTML = htmlcontent;
                    """ ,
                    _if='htmlcontent',
                    _else="""_iframe.contentWindow.document.body.innerHTML ="<div class='document'>Vuoto</div>" """,
                    _iframe=iframe.js_domNode,styleurl=self.getResourceUri('js_plugins/statspane/report.css', add_mtime=True),
                    htmlcontent='^.stats.pivot_html')
        return iframe       

    def ths_getDataframe(self,table,filters=None,mainfilter=None,relatedTable=None,
                                relation_field=None,relation_value=None,
                                maintable=None,columns=None,condition=None,condition_kwargs=None,
                                where=None,**kwargs):
        df = GnrDbDataframe('current_df_%s' %table.replace('.','_'),self.db)
        related_pkeys = None
        if mainfilter:
            where = None
        elif isinstance(where,Bag):
            if relatedTable and relation_field:
                relatedTableObj = self.db.table(relatedTable)
                where, kwargs = self.app._decodeWhereBag(relatedTableObj, where, kwargs)
                kwargs['filters_%s' %relation_field] =  [r['pkey'] for r in relatedTableObj.query(where=where, **kwargs).fetch()]
                where = ' $%s IN :filters_%s' %(relation_field,relation_field)
            else:
                where, kwargs = self.app._decodeWhereBag(self.db.table(table), where, kwargs)
        elif relation_value:
            where = ' $%s IN :filters_%s' %(relation_field,relation_field)
            kwargs['filters_%s' %relation_field] = [relation_value]
        where = [where] if where else []
        where_kwargs = kwargs
        if condition:
            where.append(condition)
            where_kwargs.update(condition_kwargs)
        if filters:
            for fkey,filter_pkeys in filters.items():
                if filter_pkeys:
                    where.append(' $%s IN :filters_%s' %(fkey,fkey))
                    where_kwargs['filters_%s' %fkey] = filter_pkeys.split(',')
        df.query(table,where=' AND '.join(where),columns=columns,**where_kwargs)
        return df
        
        
    def ths_configPivotTreeData(self,table,relation_field=None,
                                default_columns=None,
                                default_rows=None,
                                default_values=None):
        df = GnrDbDataframe('current_df_%s' %table.replace('.','_'),self.db)
        
        return df.configPivotTree(self.db.table(table),
                                default_values=default_values,
                                default_rows=default_rows,
                                default_columns=default_columns)

    @public_method
    def ths_getPivotTable(self,df=None,table=None,relation_field=None,relation_value=None,
                        filters=None,mainfilter=None,
                        stat_rows=None,stat_columns=None,
                        stat_values=None,outmode=None,
                        filename=None,condition=None,where=None,
                        **kwargs):
        condition_kwargs= dictExtract(kwargs,'condition_')
        stats_tableobj = self.db.table(table)
        main_tableobj = stats_tableobj.column(relation_field).relatedColumn().table if relation_field else stats_tableobj
        if not df:
            stat_values = stat_values or Bag()
            stat_columns = stat_columns or Bag()
            stat_rows = stat_rows or Bag()
            columns = stat_values.digest('#v.field') + stat_columns.digest('#v.field') + stat_rows.digest('#v.field')
            df = self.ths_getDataframe(table,filters=filters,mainfilter=mainfilter,
                                        relation_field=relation_field,
                                        relation_value=relation_value,
                                        maintable=main_tableobj.fullname,
                                        columns=','.join(set(columns)),
                                        condition=condition,
                                        where=where,
                                        condition_kwargs=condition_kwargs,
                                        **kwargs)
            if not df:
                return        
        pivotdf,bagresult = df.pivotTableGrid(index=stat_rows if stat_rows else None,
                                            values=stat_values if stat_values else None,
                                            columns=stat_columns if stat_columns else None)
        result = Bag()
        result['pivot_html'] = pivotdf.to_html()
        result['pivot_grid'] = bagresult
        if outmode=='xls':
            filename = filename or 'stats_%s' %main_tableobj.name
            path = self.db.application.site.getStaticPath('page:xls_stats','%s.xls' %filename,autocreate=-1)
            writer = pd.ExcelWriter(path)
            pivotdf.to_excel(writer,'Sheet1')
            writer.save()
            result['xls_url'] = self.db.application.site.getStaticUrl('page:xls_stats','%s.xls' %filename)
        return result   

    
    def _ths_branchgrid(self,parent,branch,addrow=False,delrow=True,**kwargs):
        frameCode = 'V_th_conf_%s' %branch

        def struct(struct):
            r = struct.view().rows()
            r.cell('caption',width='100%',name='!!Field')
            #r.cell('stat_type',width='4em')
            if branch=='values':
                r.cell('aggregators',edit=dict(tag='checkboxtext',values='sum,mean,min,max,count',cols=1),
                                        width='15em',name='Aggregate')


        frame = parent.bagGrid(frameCode=frameCode,title=branch.title(),
                                datapath='#ANCHOR.stats.%s' %frameCode,
                                struct=struct,storepath='#ANCHOR.stats.conf.%s' %branch,
                                pbl_classes=True if branch=='values' else '*',
                                grid_rowCustomClassesCb="""function(row){
                                                            return 'ths_'+row.stat_type;
                                                        }
                                                    """,
                                grid_selfDragRows=True,
                                addrow=addrow,delrow=delrow,
                                margin='2px',**kwargs)
        if branch!='fields':
            menupath = '#ANCHOR.stats.controller.%s_menu' %(branch if branch=='values' else 'index')
            frame.top.bar.replaceSlots('delrow','delrow,addrow',
                                addrow_defaults=menupath)
            frame.grid.attributes.update(
                selfsubscribe_addrow="""
                var storebag = this.widget.storebag();
                var newrow = new gnr.GnrBag(p_0.opt);
                newrow.setItem('caption',newrow.pop('label'));
                var fullpath = newrow.pop('fullpath');
                storebag.setItem(fullpath,newrow);
                """
            )

        return frame

    def _ths_configFields(self,bc):
        frame = self._ths_branchgrid(bc,'fields',region='center')
        bc.dataController("""
        var index_menu = new gnr.GnrBag();
        var values_menu = new gnr.GnrBag();
        fields.getNodes().forEach(function(n){
            if(n.getValue().getItem('stat_type')=='numeric'){
                if(!values.getNode(n.label)){
                    values_menu.setItem(n.label,null,n.getValue().asDict());
                }
            }else{
                if(!(rows.getNode(n.label) || columns.getNode(n.label))){
                    index_menu.setItem(n.label,null,n.getValue().asDict());
                }
            }
        });
        SET .stats.controller.index_menu = index_menu;
        SET .stats.controller.values_menu = values_menu;
        """,fields='^.stats.conf.fields',
            rows='^.stats.conf.rows',
            columns='^.stats.conf.columns',
            values='^.stats.conf.values',
            _if='fields',_onBuilt=True,_delay=10)
        form = frame.grid.linkedForm(frameCode='th_conf_fields',
                                 datapath='.form',loadEvent='onRowDblClick',
                                 dialog_height='530px',dialog_width='680px',
                                 dialog_title='^.form.ftitle',handlerType='dialog',
                                 childname='form',attachTo=bc,store='memory',
                                 store_pkeyField='pkey')
       #stfield_type = Bag()

       #stfield_type.setItem('formula',None,caption='New formula')
       #stfield_type.setItem('calc_on_field',None,caption='Calculated from field')

       #frame.top.bar.replaceSlots('delrow','delrow,addrow',addrow_defaults=stfield_type)
        self.ths_fieldsform(form)

    def ths_fieldsform(self,form):

        fb = form.record.formbuilder()
        fb.textbox(value='^.caption',lbl='Caption')

    def _ths_configPivotGrids(self,bc):
        self._ths_branchgrid(bc,'rows',region='top',height='33%')
        self._ths_branchgrid(bc,'values',region='bottom',height='33%')
        self._ths_branchgrid(bc,'columns',region='center')
