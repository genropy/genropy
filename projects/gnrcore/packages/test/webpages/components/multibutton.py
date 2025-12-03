# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):

    py_requires="gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
        
    def test_0_multibutton_base(self,pane):
        "Multibutton base"
        pane.multibutton(value='^.base',values='pippo:Pippo,paperino:Paperino')
        pane.textbox(value='^.base')
        pane.dataController("genro.bp(true)",v='^.base')

    def test_1_itemsMaxWidth(self,pane):
        "Multibutton itemsMaxWidth"
        pane.textbox(value='^.base',lbl='Curr selected')
        pane.textbox(value='^.values',lbl='Curr values',default='pippo:Pippo,pluto:Pluto,paperino:Paperino,mario:Mario,l:luca,c:Cesare,p:Pancrazio,o:Ortensia,a:Antonella,b:Brigitta')
        pane.div(height='20px')
        pane.div(_class='mobile_bar').multibutton(value='^.base',values='^.values',itemsMaxWidth='300px',content_max_width='40px')
        
    def test_2_multivalue(self, pane):
        "Multivalue: shift+click to select multiple values."
        pane.multibutton(value='^.base',values='pippo:Pippo,paperino:Paperino', multivalue=True)
        pane.textbox(value='^.base')