# -*- coding: utf-8 -*-

# untitled.py
# Created by Francesco Porcari on 2012-04-03.
# Copyright (c) 2012 Softwell. All rights reserved.

from builtins import str
from gnr.web.gnrwebpage import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrdict import dictExtract
from gnr.web.gnrwebpage import GnrMissingResourceException

class THPicker(BaseComponent):
    js_requires='th/th_picker'

    @struct_method
    def pk_palettePicker(self,pane,grid=None,table=None,relation_field=None,paletteCode=None,
                         viewResource=None,searchOn=True,multiSelect=True,structure_field=None,
                         title=None,autoInsert=None,dockButton=None,nodup=None,picker_kwargs=None,
                         height=None,width=None,checkbox=False,defaults=None,condition=None,**kwargs):
        dockButton = dockButton or dict(parentForm=True,iconClass='iconbox picker app')
        picker_kwargs = picker_kwargs or dict()
        checkbox = checkbox or picker_kwargs.get('checkbox',False)
        one = picker_kwargs.get('one',False)
        picker_kwargs.setdefault('uniqueRow',True)
        nodup = nodup or picker_kwargs.get('nodup')
        condition= condition or picker_kwargs.pop('condition',None)
        many = relation_field or picker_kwargs.get('relation_field',None)
        table = table or picker_kwargs.get('table',None)
        height = height or picker_kwargs.get('height')
        width = width or picker_kwargs.get('width')
        defaults = defaults or picker_kwargs.get('defaults',False)
        dropDefaults = dictExtract(kwargs,'default_',pop=True,slice_prefix=False)
        if autoInsert is None:
            autoInsert = picker_kwargs.get('autoInsert',True)
        title = title or picker_kwargs.get('title')
        viewResource = viewResource or picker_kwargs.get('viewResource')
        if viewResource is True:
            viewResource = 'ViewPicker'
        searchOn = searchOn or picker_kwargs.get('searchOn')
        maintable = None
        if grid is not None:
            maintable = grid.getInheritedAttributes()['table']
            if not table:
                tblobj = self.db.table(maintable).column(many).relatedTable().dbtable
                table = tblobj.fullname  
            else:
                tblobj = self.db.table(table) 
        elif table:
            tblobj = self.db.table(table)
        
        paletteCode = paletteCode or picker_kwargs.get('paletteCode')
        if not paletteCode:
            paletteCode = f"{table.replace('.','_')}_{id(pane)}_picker" 
        title = title or tblobj.name_long
        treepicker = tblobj.attributes.get('hierarchical') and not viewResource
        condition_kwargs = dictExtract(picker_kwargs,'condition_',pop=True,slice_prefix=not treepicker)
        if treepicker:
            palette = pane.palettePane(paletteCode=paletteCode,dockButton=dockButton,title=title,
                            width=width or '400px',height=height or '600px')
            frame = palette.framePane(frameCode=paletteCode)
            frame.top.slotToolbar('*,searchOn,5')
            tree_kwargs = dictExtract(picker_kwargs,'tree_',pop=True)
            tree_kwargs.update(condition_kwargs)
            frame.center.contentPane(overflow='auto').div(margin='10px').hTableTree(table=table,draggableFolders=picker_kwargs.pop('draggableFolders',None),
                            dragTags=paletteCode,caption_field=picker_kwargs.get('caption_field'),
                            moveTreeNode=False,
                            onDrag="""function(dragValues, dragInfo, treeItem) {
                                                if (treeItem.attr.child_count && treeItem.attr.child_count > 0 && !dragInfo.sourceNode.attr.draggableFolders) {
                                                    return false;
                                                }
                                                dragValues['text/plain'] = treeItem.attr.caption;
                                                dragValues['%s'] = treeItem.attr;
                                            }""" %paletteCode,
                            condition=condition,checkbox=checkbox,**tree_kwargs)
        else:
            palette = pane.paletteGridPicker(grid=grid,table=table,relation_field=many,
                                            paletteCode=paletteCode,viewResource=viewResource,
                                            searchOn=searchOn,multiSelect=multiSelect,title=title,
                                            dockButton=dockButton,height=height,
                                            width=width,condition=condition,condition_kwargs=condition_kwargs,
                                            checkbox=checkbox,structure_field = structure_field or picker_kwargs.get('structure_field'),
                                            uniqueRow=picker_kwargs.get('uniqueRow',True),
                                            top_height=picker_kwargs.get('top_height'),structure_kwargs = dictExtract(picker_kwargs,'structure_'),**kwargs)

        if grid is not None:
            grid.attributes.update(dropTargetCb_picker='return this.form?!this.form.isDisabled():true')
            grid.dragAndDrop(paletteCode)
            if autoInsert:
                method = getattr(tblobj,'insertPicker',self._th_insertPicker)
                formNode = pane.parentNode.attributeOwnerNode('formId')
                if not one and formNode and grid.attributes.get('table'):
                    formtblobj = self.db.table(formNode.attr.get('table'))
                    oneJoiner = formtblobj.model.getJoiner(maintable)
                    one = oneJoiner.get('many_relation').split('.')[-1]
                controller = "THPicker.onDropElement(this,data,mainpkey,rpcmethod,treepicker,tbl,one,many,grid,defaults,nodup,objectExtract(_kwargs,'default_*',false,false))" if autoInsert is True else autoInsert
                grid.dataController(controller,data='^.dropped_%s' %paletteCode,
                    droppedInfo='=.droppedInfo_%s' %paletteCode,
                    mainpkey='=#FORM.pkey' if formNode else None,nodup=nodup,
                        rpcmethod=method,treepicker=treepicker,tbl=maintable,
                        one=one,many=many,grid=grid.js_widget,defaults=defaults,
                        **dropDefaults)  
        return palette


    @struct_method
    def pk_paletteGridPicker(self,pane,grid=None,table=None,relation_field=None,paletteCode=None,
                                viewResource=None,searchOn=True,multiSelect=True,
                                title=None,dockButton=True,
                                height=None,width=None,condition=None,condition_kwargs=None,
                                structure_field=None,uniqueRow=True,top_height=None,
                                checkbox=None,structure_kwargs=None,
                                **kwargs):
        many = relation_field 
        if viewResource is True:
            viewResource = 'ViewPicker'
        maintable = None
        if grid:
            maintable = grid.getInheritedAttributes()['table']
            if not table:
                tblobj = self.db.table(maintable).column(many).relatedTable().dbtable
                table = tblobj.fullname  
            else:
                tblobj = self.db.table(table) 
        elif table:
            tblobj = self.db.table(table)
        paletteCode = paletteCode or '%s_picker' %table.replace('.','_')
        title = title or tblobj.name_long
        default_width = '400px'
        default_height = '600px'
        viewResource = viewResource or 'PickerView'
        groupable= False
        try:
            resource = self._th_getResClass(table=table,resourceName=viewResource)
            if resource and hasattr(resource,'th_groupedStruct'):
                groupable = dict(width='350px', closable='open')
            default_width = '800px'
            default_height = '500px'
        except GnrMissingResourceException:
            pass

        palette = pane.palettePane(paletteCode=paletteCode,dockButton=dockButton,
                                        title=title,width=width or default_width,height=height or default_height)

        def struct(struct):
            r = struct.view().rows()
            r.fieldcell(tblobj.attributes['caption_field'], name=tblobj.name_long, width='100%')


        bc = palette.borderContainer(_anchor=True)
        center = bc.contentPane(region='center')
        paletteth = center.plainTableHandler(table=table,viewResource=viewResource,
                                                grid_onDrag='dragValues["%s"]=dragValues.gridrow.rowset;' %paletteCode,
                                                grid_multiSelect=multiSelect,
                                                view_structCb=struct,
                                                groupable=groupable,
                                                title=title,searchOn=searchOn,configurable=False,
                                                childname='picker_tablehandler',nodeId='%s_th' %paletteCode)
        if structure_field:
            top = bc.contentPane(region='top',height=top_height or '50%',splitter=True,datapath='.structuretree')
            structure_tblobj = tblobj.column(structure_field).relatedTable().dbtable
            structure_tbl = tblobj.column(structure_field).relatedTable().fullname
            if not structure_tblobj.attributes.get('hierarchical'):
                self.plainPickerStructure(top, paletteth=paletteth, structure_field=structure_field, structure_tbl=structure_tbl,
                                                structure_kwargs=structure_kwargs, **kwargs)
            else:
                self.hierarchicalPickerStructure(top, paletteth=paletteth, structure_field=structure_field, 
                                                maintable=maintable, structure_tbl=structure_tbl, paletteCode=paletteCode, 
                                                checkbox=checkbox, structure_kwargs=structure_kwargs, **kwargs)
        if checkbox or self.isMobile:
            paletteth.view.grid.attributes.update(onCreating="""function(attributes,handler){
                    handler.addNewSetColumn(this,{field:'pickerset'});
                }""")
            bar = paletteth.view.bottom.slotBar('*,moveButton,2',margin_bottom='2px',_class='slotbar_dialog_footer')
            bar.moveButton.slotButton('!!Pick checked',
                                        action="""
                                            if(!pickerset){
                                                return;
                                            }
                                            var rows = [];
                                            pickerset.split(',').forEach(function(pkey){
                                                rows.push(sourcegrid.rowBagNodeByIdentifier(pkey).attr);
                                            });
                                            if(destgrid){
                                                destgrid.fireEvent('.dropped_'+paletteCode,rows);
                                            } 
                                            PUT .grid.sets.pickerset = null;
                                        """,sourcegrid=paletteth.view.grid.js_widget,
                                        pickerset='=.grid.sets.pickerset',
                                        destgrid=grid,paletteCode=paletteCode)

        if condition:
            paletteth.view.store.attributes.update(condition=condition,**condition_kwargs)
        if not condition_kwargs:
            paletteth.view.store.attributes.update(_onStart=True)
        if grid and uniqueRow:
            paletteth.view.grid.attributes.update(filteringGrid=grid.js_sourceNode(),filteringColumn='_pkey:%s' %many)
        return palette
        
        
    def plainPickerStructure(self, top, paletteth=None, structure_field=None, structure_tbl=None, 
                                            structure_kwargs=None, **kwargs):
        th = top.plainTableHandler(table=structure_tbl, configurable=False, view_store__onStart=True,
                                            **structure_kwargs, **kwargs)
        th.view.dataController("""SET #ANCHOR.structuretree.selectedStructureField = selectedId;""", 
                                            selectedId='^.grid.selectedId', _delay=1)
        paletteth.view.store.attributes.update(where=f"${structure_field}=:sel", 
                                                sel='^#ANCHOR.structuretree.selectedStructureField')
        
    def hierarchicalPickerStructure(self, top, paletteth=None, structure_field=None, maintable=None, structure_tbl=None, 
                                            paletteCode=None, checkbox=None, structure_kwargs=None, **kwargs):
        defaultPickerStructure = False
        if maintable:
            defaultPickerStructure =  structure_field if structure_field in self.db.table(maintable).columns else False
        pickerStructure = structure_kwargs.pop('pickerStructure',defaultPickerStructure)
        structureTreeKwargs = dict(draggable=False,moveTreeNode=False)
        if pickerStructure:
            structureTreeKwargs['draggable'] = True 
            structureTreeKwargs['draggableFolders'] = structure_kwargs.pop('draggableFolders',True)
            structureTreeKwargs['onDrag']="""function(dragValues, dragInfo, treeItem) {
                                            if (treeItem.attr.child_count && treeItem.attr.child_count > 0 && !dragInfo.sourceNode.attr.draggableFolders) {
                                                return false;
                                            }
                                            dragValues['text/plain'] = treeItem.attr.caption;
                                            var kw_drag = objectUpdate({},treeItem.attr);
                                            kw_drag.structure_many = '%s';
                                            dragValues['%s'] = kw_drag;
                                        }""" %(pickerStructure,paletteCode)
            structureTreeKwargs['checkbox'] = checkbox
        structureTree = top.tree(storepath='.store',_class='fieldsTree', hideValues=True,
                        selectedLabelClass='selectedTreeNode',
                        labelAttribute='caption',
                        selected_pkey='.tree.pkey',
                        selected_hierarchical_pkey='.tree.hierarchical_pkey',                          
                        selectedPath='.tree.path',  
                        identifier='treeIdentifier',margin='6px',
                        **structureTreeKwargs,
                        **kwargs
                    ).htableViewStore(table=structure_tbl,**structure_kwargs)
        if structure_field.startswith('@'):
            sf = structure_field.split('.')
            hpkey_ref = '%s.@%s.hierarchical_pkey' %(sf[0],sf[-1]) 
            fkey_ref = structure_field
        else:
            hpkey_ref = '@%s.hierarchical_pkey' %structure_field 
            fkey_ref = '$%s' %structure_field
        paletteth.view.store.attributes.update(where = """
                                                        ( (:selected_pkey IS NOT NULL) AND (%s ILIKE (:hierarchical_pkey || '%s') OR :hierarchical_pkey IS NULL)  
                                                            OR ( (%s IS NULL) AND (:selected_pkey IS NULL) ) )
                                                    """ %(hpkey_ref,'%%',fkey_ref),
                                  hierarchical_pkey='^#ANCHOR.structuretree.tree.hierarchical_pkey',
                                  selected_pkey='^#ANCHOR.structuretree.tree.pkey',_delay=500)

    @struct_method
    def th_slotbar_thpicker(self,pane,relation_field=None,picker_kwargs=None,title=None,**kwargs):
        view = pane.parent.parent.parent    
        relation_field = relation_field or picker_kwargs.pop('relation_field',None)
        if relation_field and ',' in relation_field:
            pg = pane.paletteGroup(groupCode='pickers_%s' %view.getInheritedAttributes().get('nodeId'),title=title or '!!Picker',
                            dockButton=dict(parentForm=True,iconClass='iconbox app picker'))
            for rf in relation_field.split(','):
                pg.palettePicker(view.grid,relation_field=rf,picker_kwargs=picker_kwargs,**kwargs)
            return pg
        else:
            return pane.palettePicker(view.grid,relation_field=relation_field,picker_kwargs=picker_kwargs,title=title,**kwargs)

    @public_method
    def _th_insertPicker(self,dragPkeys=None,dropPkey=None,tbl=None,one=None,many=None,dragDefaults=None,**kwargs):
        tblobj = self.db.table(tbl)
        pkeyfield = tblobj.pkey
        dropDefaults = dictExtract(kwargs,'default_')
        commit = False
        for fkey in dragPkeys:
            commit = True
            if not many:
                many = '_dup_'
            d = {one:dropPkey,many:fkey,**dropDefaults}
            if many==pkeyfield:
                with tblobj.recordToUpdate(fkey) as rec:
                    rec[one] = dropPkey
            else:
                if many=='_dup_':
                    pkeyToDup = d.pop(many)
                    if dragDefaults:
                        d.update(dragDefaults[fkey])
                    tblobj.duplicateRecord(pkeyToDup,**d)
                else:
                    r = tblobj.newrecord(**d)
                    if dragDefaults:
                        r.update(dragDefaults[fkey])
                    tblobj.insert(r)
        if commit:
            self.db.commit()

    @struct_method
    def th_slotbar_addrowmenu(self,pane,parameters=None,**kwargs):
        view = pane.parent.parent.parent    
        grid = view.grid  
        many = parameters['relation_field']
        condition = parameters.get('condition')
        condition_kwargs = dictExtract(parameters,'condition_')
        unique = parameters.get('unique',False)
        cacheTime = parameters.get('cacheTime',-1)
        loadWithDefault = parameters.get('loadWithDefault')
        one = False
        maintable = pane.getInheritedAttributes()['table']
        relation_tblobj = self.db.table(maintable).column(many).relatedTable().dbtable

        formNode = view.parentNode.attributeOwnerNode('formId')
        if formNode:
            formtblobj = self.db.table(formNode.attr.get('table'))
            oneJoiner = formtblobj.model.getJoiner(maintable)
            if oneJoiner:
                one = oneJoiner.get('many_relation').split('.')[-1] 

        hiddenItemCb = None
        if unique:
            hiddenItemCb="""var excludelist = genro.wdgById('%s').getColumnValues('%s')
                              return (dojo.indexOf(excludelist,item.pkey)>=0)
                              """ %(grid.attributes.get('nodeId'),many)

        if(hasattr(relation_tblobj,'hierarchicalHandler')):
            pane.dataRemote('.picker_menu',relation_tblobj.getHierarchicalData,
                        formpkey='=#FORM.pkey',cacheTime=cacheTime,condition=condition,
                        condition_kwargs=condition_kwargs)
            menupath = '.picker_menu.root'
        else:
            pane.dataRemote('.picker_menu',self.th_addmenu_menucontent,dbtable=relation_tblobj.fullname,many=many,one=one,
                        formpkey='=#FORM.pkey',cacheTime=cacheTime,condition=condition,condition_kwargs=condition_kwargs)
            menupath = '.picker_menu'
        pane.menudiv(storepath=menupath,iconClass='add_row',tip='!!Add',
                        action='FIRE .grid.addrowmenu_%s = $1.pkey' %many,
                        hiddenItemCb=hiddenItemCb,parentForm=True)
        method = getattr(relation_tblobj,'insertMenu',self._th_insertPicker)
        grid.dataController("""
                    var kw = {dropPkey:mainpkey,tbl:tbl,one:one,many:many};
                    kw.dragPkeys = [fkey];
                    kw['_sourceNode'] = this;
                    if(grid.gridEditor && grid.gridEditor.editorPars && !(grid.gridEditor.autoSave && mainpkey)){
                        var rows = [];
                        dojo.forEach(kw.dragPkeys,function(fkey){
                            var r = {};
                            r[many] = fkey;
                            rows.push(r);
                        });
                        grid.gridEditor.addNewRows(rows);
                    }else if(mainpkey){
                        if(loadWithDefault){
                            var default_kw = {};
                            default_kw[many] = fkey;
                            grid.sourceNode.publish('editrow',{pkey:'*newrecord*',default_kw:default_kw});
                        }else{
                            genro.serverCall(rpcmethod,kw,function(){},null,'POST');
                        }
                    }
                """,fkey='^.addrowmenu_%s' %many ,mainpkey='=#FORM.pkey',
                        rpcmethod=method,tbl=maintable,
                        one=one,many=many,grid=grid.js_widget,
                        loadWithDefault=loadWithDefault or False)  

    @public_method
    def th_addmenu_menucontent(self,dbtable=None,condition=None,condition_kwargs=None,**kwargs):
        result = Bag()
        tblobj = self.db.table(dbtable)
        caption_field = tblobj.attributes['caption_field']
        condition_kwargs = dict([(str(k),v) for k,v in list(condition_kwargs.items())]) #fix unicode
        fetch = tblobj.query(columns='*,$%s' %(caption_field),where=condition,**condition_kwargs).fetch()
        for i,r in enumerate(fetch):
            result.setItem('r_%i' %i,None,caption=r[caption_field],pkey=r['pkey'])
        return result

    