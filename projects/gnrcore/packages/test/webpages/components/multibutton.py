# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):

    py_requires="gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    
    def windowTitle(self):
        return 'Multibutton test'
        
    def test_0_multibutton_base(self,pane):
        pane.multibutton(value='^.base',values='pippo:Pippo,paperino:Paperino')
        pane.textbox(value='^.base')
        pane.dataController("genro.bp(true)",v='^.base')

    def test_1_itemsMaxWidth(self,pane):
        pane.textbox(value='^.base',lbl='Curr selected')
        pane.textbox(value='^.values',lbl='Curr values',default='pippo:Pippo,pluto:Pluto,paperino:Paperino,mario:Mario,l:luca,c:Cesare,p:Pancrazio,o:Ortensia,a:Antonella,b:Brigitta')
        pane.div(height='20px')
        pane.div(_class='mobile_bar').multibutton(value='^.base',values='^.values',itemsMaxWidth='300px',content_max_width='40px')