# -*- coding: UTF-8 -*-

# tablehandler.py
# Created by Francesco Porcari on 2011-02-22.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent

class TableHandler(BaseComponent):
    py_requires = """
                     tablehandler/th_form,
                     tablehandler/th_list_legacy:TableHandlerListLegacy,
                     tablehandler/th_core,
                     tablehandler/th_extra:TagsHandler,
                     tablehandler/th_extra:FiltersHandler,
                     tablehandler/th_extra:HierarchicalViewHandler,
                    foundation/userobject:UserObject,foundation/dialogs"""
    css_requires = 'tablehandler/th_style'

    def main(self, root, **kwargs):
        root.data('selectedPage', 0)
        root.data('gnr.maintable', self.maintable)
        root.dataController("genro.dom.setClass(dojo.body(),'form_edit',selectedPage==1)", selectedPage="^selectedPage")
        self.userObjectDialog()
        self.deleteUserObjectDialog()
        self.parsePageParameters(root, **kwargs)
        self.joinConditions()

        if hasattr(self.tblobj, 'hasRecordTags') and self.tblobj.hasRecordTags():
            self.tags_main(root)
        self.setOnBeforeUnload(root, cb="genro.getData('gnr.forms.formPane.changed')",
                               msg="!!There are unsaved changes, do you want to close the page without saving?")
       
        sc = root.rootStackContainer(center_selected='^selectedPage',
                                    center_class='pbl_mainstack',
                                    center_nodeId='tablehandler_mainstack',
                                    bottom_messageBox_subscribeTo='form_formPane_message')
        sc.listPage(frameCode='mainlist')
        sc.formPage(frameCode='formPane')
        
    def parsePageParameters(self, root, pkey=None, **kwargs):
        if pkey == '*newrecord*':
            self.startWithNewRecord(root)
        elif pkey and self.db.table(self.maintable).existsRecord(pkey):
            self.startWithExistingRecord(root, pkey)

    def startWithNewRecord(self, root):
        root.dataController('FIRE list.newRecord; FIRE status.unlock', _fired='^gnr.onStart', _delay=4000)

    def startWithExistingRecord(self, root, pkey):
        root.data('initialPkey', pkey)

    def joinConditions(self):
        """hook to define all join conditions for retrieve records related to the current edited record
           using method self.setJoinCondition
        """
        pass

    def pluralRecordName(self):
        return self.tblobj.attributes.get('name_plural', 'Records')

    def getSelection_filters(self):
        return self.clientContext['filter.%s' % self.pagename]

    def _infoGridStruct(self):
        struct = self.newGridStruct()
        r = struct.view().rows()
        r.cell('lbl', name='Field', width='10em', headerStyles='display:none;', cellClasses='infoLabels', odd=False)
        r.cell('val', name='Value', width='10em', headerStyles='display:none;', cellClasses='infoValues', odd=False)
        return struct
    