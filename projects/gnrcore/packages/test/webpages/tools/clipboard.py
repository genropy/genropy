# -*- coding: utf-8 -*-

"Clipboard"
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_pasteFromClipboard(self,pane):
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.button('Load clipboard',action="this.pasteFromClipboard('.clip')")
        fb.div('^.clip')

    def test_1_pasteFromClipboard_xlsx(self,pane):
        pane.button('Load clipboard',action="this.pasteFromClipboard('.clip','xlsx');")
        
        pane.quickGrid('^.clip',height='100px')



