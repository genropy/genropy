# -*- coding: utf-8 -*-

# Copyright (c) 2011 Softwell. All rights reserved.

"inlineTableHandler"

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def windowTitle(self):
        return 'dialogTableHandler'

    def mystruct(self,struct):
        r = struct.view().rows()
        for k,v in list(struct.tblobj.model.columns.items()):
            attr = v.attributes
            if not (attr.get('_sysfield') or attr.get('dtype') == 'X'):
                r.fieldcell(k,edit=attr['cell_edit'] if 'cell_edit' in attr else True)

    def test_0_thvariabile(self,pane):
        "Simple inlineTableHandler. Try using 'glbl.provincia' in the textbox"
        bc = pane.borderContainer(height='300px')
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^table', lbl='Table', placeholder='glbl.provincia')
        bc.contentPane(region='center').remote(self.remoteTh,table='^table',_if='table')

    @public_method
    def remoteTh(self,pane,table=None):
        pane.inlineTableHandler(table=table,viewResource='pippo',view_structCb=self.mystruct,condition__onBuilt=True)