# -*- coding: utf-8 -*-
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


def flatCol(c):
    return c.replace('@','_').replace('.','_').replace('$','')
    
class TableHandlerGroupBy(BaseComponent):
    js_requires = 'gnrdatasets,th/th_groupth'

    @extract_kwargs(condition=True,store=True,grid=True,tree=dict(slice_prefix=False), details=True)
    @struct_method
    def th_groupByTableHandler(self,pane,frameCode=None,title=None,table=None,linkedTo=None,
                                struct=None,where=None,viewResource=None,
                                condition=None,condition_kwargs=None,store_kwargs=None,datapath=None,
                                treeRoot=None,configurable=True,
                                dashboardIdentifier=None,static=False,pbl_classes=None,
                                grid_kwargs=None,tree_kwargs=None,groupMode=None,grouper=False,
                                details_kwargs=None,
                                **kwargs):
        inattr = pane.getInheritedAttributes()
        table = table or inattr.get('table')
        if not (dashboardIdentifier or where or condition):
            linkedTo = linkedTo or inattr.get('frameCode')
        
        if linkedTo:
            frameCode = frameCode or '%s_groupedView' %linkedTo 
            if not struct:
                struct = self._th_hook('groupedStruct',mangler=linkedTo,defaultCb=self._thg_defaultstruct)
        if not linkedTo:
            self.subscribeTable(table,True,subscribeMode=True)
        frameCode = frameCode or 'thg_%s' %table.replace('.','_')
        datapath = datapath or '.%s' %frameCode
        rootNodeId = frameCode
        if not struct and viewResource:
            self._th_mixinResource(frameCode,table=table,resourceName=viewResource,defaultClass='View')
            struct = self._th_hook('groupedStruct',mangler=frameCode)
            store_kwargs['applymethod'] = store_kwargs.get('applymethod') or self._th_hook('groupedApplymethod',mangler=frameCode)
        bc = pane.borderContainer(datapath=datapath,_class='group_by_th',_anchor=True,**kwargs)
        stack_kwargs = {}
        if not (grouper or static): #not called as grouper
            grid_kwargs.setdefault('selected__pkeylist','#ANCHOR.details_pkeylist')
            tree_kwargs.setdefault('tree_selected__pkeylist','#ANCHOR.details_pkeylist')
            stack_kwargs.setdefault('grid_selected__pkeylist','#ANCHOR.details_pkeylist')
            region= details_kwargs.get('region') or 'bottom'
            if region in ('top','bottom'):
                height = details_kwargs.get('height') or '250px'
                width = None
            else:
                width = details_kwargs.get('width') or '250px',
                height=None
            if 'closable' in details_kwargs:
                closable = details_kwargs.get('closable')
            else:
                closable = 'close'
            details_pane = bc.contentPane(closable=closable,
                                        region=region,
                                        height = height,
                                        width = width,
                                        splitter=True,
                                        _class='showInnerToolbar')

            details_pane.remote(self._thg_details_rows,table=table,
                                        rootNodeId=rootNodeId,
                                        linkedTo=linkedTo,
                                        viewResource=details_kwargs.get('viewResource'))
        sc = bc.stackContainer(selectedPage='^.output',region='center',
                                nodeId=rootNodeId,_forcedGroupMode=groupMode,_linkedTo =linkedTo,table=table,
                                selfsubscribe_viewMode="""
                                    var viewMode = $1.split('_');
                                    SET .groupMode = viewMode[0];
                                    SET .output = viewMode[1];
                                """,
                                selfsubscribe_saveDashboard="genro.groupth.saveAsDashboard(this,$1);",
                                selfsubscribe_loadDashboard="genro.groupth.loadDashboard(this,$1)",
                                selfsubscribe_deleteCurrentDashboard="genro.groupth.deleteCurrentDashboard(this,$1)",
                                _dashboardRoot=True)  
        gridstack = sc.stackContainer(pageName='grid',title='!!Grid View',selectedPage='^.groupMode')

        #gridstack.dataFormula('.currentTitle','',defaultTitle='!!Group by')
        structcb = struct or self._thg_defaultstruct
        baseViewName = structcb.__doc__
        frame = gridstack.frameGrid(frameCode=frameCode,grid_onDroppedColumn="""
                                    genro.groupth.addColumnCb(this,{data:data, column:column,fieldcellattr:fieldcellattr,treeNode:treeNode});
                                    """,
                                    datamode='attr',
                                struct=structcb,
                                grid_baseViewName = baseViewName,
                                _newGrid=True,pageName='flatview',title='!!Flat',
                                grid_kwargs=grid_kwargs)

        
        frame.dataFormula('.changets.flatview','new Date();',store='^.store',struct='^.grid.struct',
                            _delay=1)
        if dashboardIdentifier:
            frame.dataController("root.publish('loadDashboard',{pkey:dashboardIdentifier});",root=sc,
                                dashboardIdentifier=dashboardIdentifier,_onBuilt=1)
        
        if static:
            slots = '5,vtitle,count,*,searchOn,export,5'
            if pbl_classes is None:
                pbl_classes = True
            if pbl_classes:
                frame.top.slotBar(slots,_class='pbl_roundedGroupLabel',vtitle=title)
                frame.attributes['_class'] = 'pbl_roundedGroup'
            else:
                bar = frame.top.slotToolbar(slots)
                bar.vtitle.div(title,font_size='.9em',color='#666',font_weight='bold')

        else:
            frame.dataFormula('.currentTitle',"basetitle+' '+(loadedDashboard || currentView || '')",
                                    basetitle='!!Group by',
                                    currentView='^.grid.currViewAttrs.description',
                                    loadedDashboard='^.dashboardMeta.description')
            frame.data('.grid.showCounterCol',True)
            frame.dataRemote('.dashboardsMenu',self.thg_dashboardsMenu,cacheTime=5,table=table,
                                rootNodeId=rootNodeId,_fired='^.refreshDashboardsMenu')
            configuratorSlot = 'configuratorPalette' if configurable else '2'
            bar = frame.top.slotToolbar('5,ctitle,stackButtons,10,groupByModeSelector,counterCol,*,searchOn,count,viewsMenu,%s,chartjs,export,dashboardsMenu,5' %configuratorSlot,
                                        dashboardsMenu_linkedTo=linkedTo,
                                        stackButtons_stackNodeId=frameCode)
            bar.ctitle.div(title,color='#444',font_weight='bold')
            bar.counterCol.div().checkbox(value='^.grid.showCounterCol',label='!!Counter column',label_color='#444')
            frame.grid.dataController("""
            if(showCounterCol){
                structrow.setItem('_grp_count',null,{field:'_grp_count',name:'Cnt',width:'5em',group_aggr:'sum',dtype:'L'});
            }else{
                structrow.popNode('_grp_count');
            }
            """,structrow='=.struct.#0.#0',showCounterCol='^.showCounterCol',_if='structrow')
            frame.stackedView = self._thg_stackedView(gridstack,title=title,grid=frame.grid,
                                            frameCode=frameCode,linkedTo=linkedTo,table=table,
                                            stack_kwargs=stack_kwargs)
            frame.treeView = self._thg_treeview(sc,title=title,grid=frame.grid,treeRoot=treeRoot,linkedTo=linkedTo,tree_kwargs=tree_kwargs)
            frame.dataController("""
                grid.collectionStore().loadInvisible = always || genro.dom.isVisible(sc);
            """,output='^.output',groupMode='^.groupMode',always='=.always',
                grid=frame.grid.js_widget,sc=sc,_delay=1)



        gridId = frame.grid.attributes['nodeId']
        frame.dataController("""genro.grid_configurator.loadView(gridId, (currentView || favoriteView));
                                    """,
                                currentView="^.grid.currViewPath",
                                favoriteView='^.grid.favoriteViewPath',
                                gridId=gridId)
        self._thg_structMenuData(frame,table=table,linkedTo=linkedTo,baseViewName=baseViewName)
        if configurable:
            frame.viewConfigurator(table,queryLimit=False,toolbar=False)
        else:
            frame.grid.attributes['gridplugins'] = 'groupth:toggleCounterColumn'
        self._thg_groupByStore(frame,table=table,where=where,condition=condition,linkedTo=linkedTo,
                                condition_kwargs=condition_kwargs,grouper=grouper,**store_kwargs)
        return frame

    
    def _thg_groupByStore(self,frame,table=None,where=None,linkedTo=None,
                            condition=None,condition_kwargs=None,grouper=None,**store_kwargs):
        frame.grid.attributes.setdefault('selfsubscribe_loadingData',
                                            "this.setRelativeData('.loadingData',$1.loading);if(this.attr.loadingHider!==false){this.setHiderLayer($1.loading,{message:'%s'});}" %self._th_waitingElement())
        store_kwargs.update(condition_kwargs)
        store_kwargs['_forcedReload'] = '^.reloadMain'
        frame.grid.selectionStore(table=table,where=where,selectmethod=self._thg_selectgroupby,
                                childname='store',struct='=.grid.struct',
                                groupByStore=True,liveUpdate='PAGE',
                                _linkedTo=linkedTo,
                                _onCalling="""
                                if(!_linkedTo){
                                    return;
                                }
                                var originalAttr = genro.wdgById(_linkedTo+'_grid').collectionStore().storeNode.currentAttributes();
                                var runKwargs = objectUpdate({},originalAttr);
                                var storeKw = objectExtract(runKwargs,_excludeList);
                                if(storeKw._sections){
                                    th_sections_manager.onCalling(storeKw._sections,runKwargs);
                                }
                                objectUpdate(kwargs,runKwargs);
                                if(condition){
                                    kwargs.condition = kwargs.condition? kwargs.condition +' AND '+condition:condition;
                                }
                                """,
                                _excludeList="""columns,sortedBy,currentFilter,customOrderBy,row_count,hardQueryLimit,limit,liveUpdate,method,nodeId,selectionName,
                            selectmethod,sqlContextName,sum_columns,table,timeout,totalRowCount,userSets,_sections,
                            _onCalling,_onResult,applymethod,sum_columns,prevSelectedDict""",
                    condition=condition,**store_kwargs)
        if linkedTo:
            frame.dataController("""
                    var groupbystore = grid.collectionStore();
                    if(!groupbystore){{
                        return;
                    }}
                    if(use_grouper){{
                        PUT #{linkedTo}_grid.grouperPkeyList = null;
                        genro.nodeById('{linkedTo}_grid_store').store.clear();
                    }}else if(!grouper){{
                        SET #ANCHOR.details_pkeylist = null;
                    }}
                    groupbystore.loadData();
                    """.format(linkedTo=linkedTo),
                grid = frame.grid.js_widget,
                use_grouper='=.use_grouper',grouper=grouper,
                datapath=f'#{linkedTo}_frame',
                _runQuery='^.runQueryDo',
                _reloadGrouper='^.reloadGrouper',
                _sections_changed='^.sections_changed',
            linkedTo=linkedTo,_delay=200,
            #**{'subscribe_{linkedTo}_grid_onNewDatastore'.format(linkedTo=linkedTo):True}
            )
            frame.dataController(f"""FIRE #{linkedTo}_frame.reloadGrouper = {{'_changedView':_changedView}};""",
                                _changedView = '^.grid.currViewPath')


    def _thg_defaultstruct(self,struct):
        "!![en]New View"
        r=struct.view().rows()
        r.cell('_grp_count',name='Cnt',width='5em',group_aggr='sum',dtype='L',childname='_grp_count')

    @struct_method
    def thg_slotbar_groupByModeSelector(self,pane,**kwargs):
        inattr = pane.getInheritedAttributes()
        _forcedGroupMode = inattr.get('_forcedGroupMode')
        if _forcedGroupMode:
            pane.dataFormula('#ANCHOR.groupMode','groupMode',groupMode=_forcedGroupMode,_onBuilt=100)
        else:
            pane.multiButton(value='^#ANCHOR.groupMode',values='flatview:[!![en]Flat],stackedview:[!![en]Stacked]')

    
    def _thg_structMenuData(self,frame,table=None,linkedTo=None,baseViewName=None):
        q = Bag()
        if linkedTo:
            pyviews = self._th_hook('groupedStruct',mangler=linkedTo,asDict=True)
            for k,v in list(pyviews.items()):
                prefix,name=k.split('_groupedStruct_')
                q.setItem(name,self._prepareGridStruct(v,table=table),caption=v.__doc__)
            frame.data('.grid.resource_structs',q)
        frame.dataRemote('.grid.structMenuBag',self.th_menuViews,pyviews=q.digest('#k,#a.caption'),currentView="^.grid.currViewPath",
                        table=table,th_root=frame.attributes['frameCode'],objtype='grpview',baseViewName=baseViewName,
                        favoriteViewPath='^.grid.favoriteViewPath',cacheTime=30)



    def _thg_stackedView(self,parentStack,title=None, grid=None,frameCode=None,linkedTo=None,table=None,stack_kwargs=None,**kwargs):
        frame = parentStack.bagGrid(frameCode='%s_stacked' %frameCode,title='!!Stacked',pageName='stackedview',
                                    datapath='.stacked',table=table,
                                    storepath='.store',addrow=False,delrow=False,
                                    datamode='attr',**stack_kwargs)
        bar = frame.top.bar.replaceSlots('#','5,ctitle,stackButtons,10,groupByModeSelector,*,searchOn,export,5,dashboardsMenu',
                                        stackButtons_stackNodeId=frameCode,dashboardsMenu_linkedTo=linkedTo)
        bar.ctitle.div(title,color='#444',font_weight='bold')
        frame.dataController("""
            if(groupMode!='stackedview' && !linkedChart){
                return;    
            }
            var r = genro.groupth.getPivotGrid(flatStore,flatStruct);
            if(!r){
                SET .store = new gnr.GnrBag();
                return;
            }
            SET .grid.struct = r.struct;
            SET .store = r.store;
            SET #ANCHOR.changets.stackedview = changets_flatview;
        """,flatStore='=#ANCHOR.store',
            flatStruct='=#ANCHOR.grid.struct',
            groupMode='^#ANCHOR.groupMode',
            linkedChart='=.grid.linkedChart',
            changets_flatview ='^#ANCHOR.changets.flatview')
        return frame


    def _thg_treeview(self,parentStack,title=None, grid=None,treeRoot=None,linkedTo=None,tree_kwargs=None,**kwargs):
        frame = parentStack.framePane(title='Tree View',pageName='tree')
        bar = frame.top.slotToolbar('5,ctitle,parentStackButtons,10,groupByModeSelector,addTreeRoot,*,searchOn,dashboardsMenu,5',
                                    dashboardsMenu_linkedTo=linkedTo)
        bar.ctitle.div(title,color='#444',font_weight='bold')
        fb = bar.addTreeRoot.div(_class='iconbox tag').tooltipPane().formbuilder(cols=1,border_spacing='2px',color='#666')
        fb.textbox(value='^.treeRootName',lbl='!!Root',width='7em')
        bar.data('.treeRootName',treeRoot)
        bc = frame.center.borderContainer()
        inhattr = frame.getInheritedAttributes()

        treeNodeId = tree_kwargs.setdefault('tree_nodeId','{frameCode}_tree'.format(frameCode=inhattr['frameCode']))
        tree_kwargs['tree_selectedPath'] = '#{treeNodeId}.currentGroupPath'.format(treeNodeId=treeNodeId)
        frame.dataController("""
            if(!genro.dom.isVisible(pane)){
                return;
            }
            var nodeLabel = _node.label;
            var v = _node.getValue();
            var lastTs = v instanceof Date?v:null;
            if(output!='tree' || (lastTs && nodeLabel!=groupMode) ){
                return;
            }
            lastTs = groupMode=='stackedview'?changets_stackedview:changets_flatview;
            var treekw = objectExtract(_kwargs,'tree_*',true);
            if(changets_tree!=lastTs){
                var struct = flatStruct;
                var store = flatStore;
                if(groupMode=='stackedview'){
                    struct = stackedStruct;
                    store = stackedStore;
                }
                if(nodeLabel!='treeRootName'){
                    genro.groupth.buildGroupTree(pane,struct,treekw);
                }
                SET .treestore = genro.groupth.groupTreeData(store,struct,treeRoot,treekw);
                genro.wdgById(treekw.nodeId).setSelectedPath(null,{value:previousSelectedPath});
            }
            """,
            pane=bc.contentPane(region='center'),
            previousSelectedPath='=.currentGroupPath',
            storepath='.treestore',
            flatStruct='=.grid.struct',
            flatStore='=.store',
            stackedStruct = '=.stacked.grid.struct',
            stackedStore ='=.stacked.store',
            changets_tree='=.changets.tree',
            changets_flatview ='^.changets.flatview',
            changets_stackedview = '^.changets.stackedview',
            groupMode='^.groupMode',
            output='^.output',
            treeRoot='^.treeRootName',_delay=1,**tree_kwargs)
        return frame

    @public_method
    def _thg_details_rows(self,pane,table=None,rootNodeId=None,linkedTo=None, viewResource=None):
        view = self.site.virtualPage(table=table,table_resources='th_{}:View'.format(table.split('.')[1]))
        th = pane.plainTableHandler(table=table,datapath='.tree_details',searchOn=True,export=True,
                                        viewResource=viewResource or 'THGViewTreeDetail',
                                        view_structCb=view.th_struct,
                                        count=True,view_store_liveUpdate='PAGE',
                                        nodeId='{rootNodeId}_details'.format(rootNodeId=rootNodeId))

        pane.dataController("""
                            if(pkeylist){
                                var queryvars = {subtable:'*',ignorePartition:true,excludeDraft:false,excludeLogicalDeleted:false};
                                queryvars.condition = '$pkey IN :currpkeylist';
                                queryvars.currpkeylist = pkeylist.split(',');
                                grid.collectionStore().loadData(queryvars);
                            }else{
                                grid.collectionStore().clear();
                            }
                            """,grid=th.view.grid.js_widget,pkeylist='^#ANCHOR.details_pkeylist')


    @public_method
    def _thg_selectgroupby(self,struct=None,groupLimit=None,groupOrderBy=None,
                    keep_pkeys=True,table=None,**kwargs):
        columns_list = list()
        group_list = list()
        having_list = list()
        custom_order_by = list()
        if groupOrderBy:
            for v in list(groupOrderBy.values()):
                field = v['field']
                if not field.startswith('@'):
                    field = f'${field}'
                field = field if not v['group_aggr'] else f"{v['group_aggr']}({field})" 
                custom_order_by.append(f"{field} {'asc' if v['sorting'] else 'desc'}" )
            custom_order_by = ' ,'.join(custom_order_by)
        
        def asName(field,group_aggr):
            return f"{field}_{group_aggr}".replace('.','_')\
                                          .replace('@','_')\
                                          .replace('-','_')\
                                          .replace(' ','_')\
                                          .lower()
        empty_placeholders = {}
        group_list_keys = []
        count_distinct_keys = []
        for v in struct['#0.#0'].digest('#a'):
            if v['field'] =='_grp_count' or v.get('calculated'):
               #having_chunk = []
               #if v.get('min_value') is not None:
               #    parname = f'_grp_count_sum_min_value'
               #    kwargs[parname] = v['min_value']
               #    having_chunk.append(f'count(*)>=:{parname}')
               #if v.get('max_value') is not None:
               #    parname = f'_grp_count_sum_max_value'
               #    kwargs[parname] = v['max_value']
               #    having_chunk.append(f'count(*)>=:{parname}')
               #having_list.append(' AND '.join(having_chunk))
                continue
            col = v.get('queryfield') or v['field']
            if not col.startswith('@'):
                col = f'${col}'
            dtype = v.get('original_dtype') or v.get('dtype')
            group_aggr =  v.get('group_aggr') 
            if dtype in ('N','L','I','F','R') and group_aggr is not False:
                group_aggr =  group_aggr or 'sum'
                col_asname = asName(v['field'],group_aggr)
                grouped_col = f'{group_aggr}({col})'
                col = f'{grouped_col} AS {col_asname}'
                having_chunk = list()
                if v.get('not_zero'):
                    having_chunk.append(f'({grouped_col} != 0)')
                if v.get('min_value') is not None:
                    parname = f'{col_asname}_min_value'
                    kwargs[parname] = v['min_value']
                    having_chunk.append(f'{grouped_col}>=:{parname}')
                if v.get('max_value') is not None:
                    parname = '%s_max_value' %col_asname
                    kwargs[parname] = v['max_value']
                    having_chunk.append(f'{grouped_col}<=:{parname}')
                if len(having_chunk):
                    having_list.append(' AND '.join(having_chunk))
            else:
                col_as = col
                group_empty = v.get('group_empty') or '[NP]'
                if group_aggr:
                    if dtype in ('D','DH','DHZ'):
                        col =  f"to_char({col},'{group_aggr}')"
                        group_list.append(col)
                        col_as = asName(v['field'],group_aggr)
                        colgetter = flatCol(col_as)
                        group_list_keys.append(colgetter)
                        empty_placeholders[colgetter] = group_empty
                        col = f'{col} AS {col_as}'
                    elif group_aggr=='distinct_count' or group_aggr=='distinct':
                        col = self.db.adapter.string_agg(f'CAST({col} AS TEXT)','|')
                        col_as = asName(v['field'],'distinct')
                        if group_aggr == 'distinct_count':
                            count_distinct_keys.append(col_as)
                        col = f'{col} AS {col_as}'
                else:
                    groupcol = col
                    if ' AS ' in col:
                        groupcol,col_as = col.split(' AS ')
                    group_list.append(groupcol)
                    colgetter = flatCol(col_as)
                    caption_field = v.get('caption_field')
                    if caption_field:
                        if not caption_field.startswith('@'):
                            caption_field = f'${caption_field}'
                        group_list.append(caption_field)
                        colgetter = flatCol(caption_field)
                        columns_list.append(caption_field)
                    empty_placeholders[colgetter] = group_empty
                    group_list_keys.append(colgetter)
            columns_list.append(col)
        columns_list.append('count(*) AS _grp_count_sum')
        if not group_list:
            return False
        if keep_pkeys:
            pkeylist_column = self.db.adapter.string_agg(f'CAST(${self.db.table(table).pkey} AS TEXT)',',')
            columns_list.append(f"{pkeylist_column} AS _pkeylist")
        kwargs['columns'] = ','.join(columns_list)
        kwargs['group_by'] = ','.join(group_list)
        kwargs['order_by'] = custom_order_by or kwargs['group_by']
        if having_list:
            kwargs['having'] = ' OR '.join(having_list)
        kwargs['hardQueryLimit'] = False
        if groupLimit:
            kwargs['limit'] = groupLimit
        selection = self.app._default_getSelection(_aggregateRows=False,**kwargs)
        def cb(row):
            resdict = {}
            keylist = []
            for col in group_list_keys:
                keyvalue = row[col] 
                if keyvalue in ('',None):
                    keyvalue = empty_placeholders.get(col)
                    resdict[col] = keyvalue
                keylist.append(str(keyvalue or '_'))
            for col in count_distinct_keys:
                s = set(row[col].split('|')) if row[col] else set()
                resdict[col] = '|'.join(s)
                resdict[f'{col}_count'] = len(s)
            resdict['_thgroup_pkey'] = '|'.join(keylist)
            return resdict
        selection.apply(cb)
        return selection    




    @struct_method
    def thg_slotbar_dashboardsMenu(self,pane,linkedTo=None,**kwargs):
        if not (linkedTo and self.db.package('biz')):
            return pane.div()
        menu = pane.menudiv(tip='!!Advanced tools',
                            iconClass='iconbox menu_gray_svg',
                            storepath='#ANCHOR.dashboardsMenu',**kwargs)
    
    @public_method
    def thg_dashboardsMenu(self,currentDashboard=None,rootNodeId=None,table=None,**kwargs):
        result = Bag()
        result.rowchild(label='!!Save dashboard',
                        action="""this.attributeOwnerNode('_dashboardRoot').publish('saveDashboard');""")
        result.rowchild(label='!!Save dashboard as',
                        action="""this.attributeOwnerNode('_dashboardRoot').publish('saveDashboard',{saveAs:true});""")
        result.rowchild(label='!!Delete current dashboard',
                        action="""this.attributeOwnerNode('_dashboardRoot').publish('deleteCurrentDashboard');""")
        objtype = 'dash_groupby'
        #flags='groupth|%s' %rootNodeId
        userobjects = self.db.table('adm.userobject').userObjectMenu(objtype=objtype,table=table)
        if len(userobjects)>0:
            loadAction = """this.attributeOwnerNode('_dashboardRoot').publish('loadDashboard',{pkey:$1.pkey});"""
            loadmenu = Bag()
            loadmenu.update(userobjects)
            result.setItem('r_%s' %len(result),loadmenu,label='!!Load dashboard',action=loadAction)
        return result

    @struct_method
    def thgp_linkedGroupByAnalyzer(self,view,**kwargs):
        linkedTo=view.attributes.get('frameCode')
        table = view.grid.attributes.get('table')
        frameCode = '%s_gp_analyzer' %linkedTo
        pane = view.grid_envelope.contentPane(region='bottom',height='300px',closable='close',margin='2px',splitter=True,
                                             border_top='1px solid #efefef')
        view.dataController("""
            var analyzerNode = genro.nodeById(analyzerId);
            if(currentSelectedPkeys && currentSelectedPkeys.length){
                analyzerNode.setRelativeData('.analyzer_condition', '$'+pkeyField+' IN :analyzed_pkeys');
                analyzerNode.setRelativeData('.analyzed_pkeys',currentSelectedPkeys);
            }else{
                analyzerNode.setRelativeData('.analyzer_condition',null);
                analyzerNode.setRelativeData('.analyzed_pkeys',null);
            }
        """,pkeyField='=.table?pkey',
            currentSelectedPkeys='^.grid.currentSelectedPkeys',
            analyzerId=frameCode,_delay=500)

        pane.groupByTableHandler(frameCode=frameCode,linkedTo=linkedTo,
                                    table=table,datapath='.analyzerPane',
                                    condition='=.analyzer_condition',
                                    condition_analyzed_pkeys='^.analyzed_pkeys')

