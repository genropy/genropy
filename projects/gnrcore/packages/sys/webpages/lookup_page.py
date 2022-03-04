# -*- coding: utf-8 -*-

# thpage.py
# Created by Francesco Porcari on 2011-05-05.
# Copyright (c) 2011 Softwell. All rights reserved.

from builtins import object
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrstring import boolean
from gnr.core.gnrdict import dictExtract

class GnrCustomWebPage(object):
    py_requires='public:Public,th/th:TableHandler'
    def main(self,root,th_public=None,viewResource=None,modal=None,**kwargs):
        callArgs = self.getCallArgs('th_pkg','th_table')
        public = boolean(th_public) if th_public else True
        root.attributes['datapath'] = 'main'
        pkg = callArgs.get('th_pkg')
        tbl = callArgs.get('th_table')
        if pkg and tbl:
            root.data('.viewResource',viewResource)
            root.dataFormula('.table','tbl',tbl=f'{pkg}.{tbl}',_onStart=1)
        if public:
            root = root.rootContentPane(**kwargs)
        frame = root.framePane(nodeId='lookup_root')
        modal = modal or callArgs.get('lookupModal')
        root.dataController("""if(_subscription_kwargs.table){
                                    SET main.viewResource = _subscription_kwargs.viewResource;
                                    SET main.table = _subscription_kwargs.table;
                               }
                               """,
                            subscribe_changedStartArgs=True)
        frame.center.contentPane(overflow='hidden').remote(self.remoteTh,
                            table='^main.table',branchIdentifier=self._call_kwargs.get('branchIdentifier'),
                            modal=modal,viewResource='=main.viewResource',
                            _onRemote='FIRE main.load_data;')

    def lookupTablesDefaultStruct(self,struct):
        r = struct.view().rows()
        for k,v in list(struct.tblobj.model.columns.items()):
            attr = v.attributes
            if attr.get('counter'):
                r.fieldcell(k,hidden=True,counter=True)
            elif not (attr.get('_sysfield') or attr.get('dtype') == 'X'):
                condition = attr.get('condition')
                if condition:
                    condition_kwargs = dictExtract(attr,'condition_',slice_prefix=False)
                    cell_edit = attr.setdefault('cell_edit',dict())
                    cell_edit['condition'] = condition
                    cell_edit['condition_kwargs'] = condition_kwargs
                r.fieldcell(k,edit=attr['cell_edit'] if 'cell_edit' in attr else True)
        if '__syscode' in struct.tblobj.model.columns and self.application.checkResourcePermission('_DEV_,superadmin', self.userTags):
            r.fieldcell('__syscode',edit=True)

    @public_method
    def remoteTh(self,pane,table=None,modal=None,viewResource=None,branchIdentifier=None,**kwargs):
        pane.data('.mainth',Bag())
        if not table:
            pane.div('!!Select a table from the popup menu',margin_left='5em',margin_top='5px', color='#8a898a',text_align='center',font_size='large')
        else:
            saveButton = not modal
            semaphore = not modal
            tblobj= self.db.table(table)
            tblattr = tblobj.attributes
            pane.dataFormula('gnr.publicTitle','title',title=tblattr.get('name_plural') or tblattr.get('name_long'),_onBuilt=1)
            th = pane.inlineTableHandler(table=table,viewResource= viewResource or 'LookupView',
                                    datapath='.mainth',autoSave=False,saveButton=saveButton,semaphore=semaphore,
                                    nodeId='mainth',configurable='*',
                                    view_structCb=self.lookupTablesDefaultStruct,condition_loaddata='^main.load_data',
                                    grid_selfDragRows=tblobj.attributes.get('counter'))
            bar = th.view.top.bar.replaceSlots('addrow','addrow,export,importer')
            if branchIdentifier:
                bar.replaceSlots('#','2,pageBranchSelector,#')
            if modal:
                bar = th.view.bottom.slotBar('10,revertbtn,*,cancel,savebtn,10',margin_bottom='2px',_class='slotbar_dialog_footer')
                bar.revertbtn.slotButton('!!Revert',action='FIRE main.load_data;',disabled='==status!="changed"',status='^.grid.editor.status')
                bar.cancel.slotButton('!!Cancel',action='genro.nodeById("lookup_root").publish("lookup_cancel");')
                bar.savebtn.slotButton('!!Save',iconClass='editGrid_semaphore',publish='saveChangedRows',command='save',
                               disabled='==status!="changed"',status='^.grid.editor.status',showLabel=True)  
                th.view.grid.attributes.update(selfsubscribe_savedRows='genro.nodeById("lookup_root").publish("lookup_cancel");')
            else:
                bar = th.view.top.bar.replaceSlots('delrow','revertchanges,5,delrow')
                bar.revertchanges.slotButton('!!Revert',iconClass='iconbox revert',action='FIRE main.load_data;',disabled='==status!="changed"',status='^.grid.editor.status')

