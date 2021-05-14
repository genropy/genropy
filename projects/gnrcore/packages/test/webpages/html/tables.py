#!/usr/bin/python
# -*- coding: utf-8 -*-

"Grid layouts and tables"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_formbuilder_advanced(self, pane):
        "Formbuilder helps you build HTML tables in an easy way. Use attribute 'pos' to manage content position"
        fb = pane.formbuilder(cols=3,lblpos='T',lbl_text_align='center')
        fb.div('A1',lbl='A', lbl_border_bottom='solid 1px black')
        fb.div('B1',lbl='B', lbl_border_bottom='solid 1px black')
        fb.div('C1',lbl='C', lbl_border_bottom='solid 1px black')
        fb.div('B2',pos='1,1') #Leave empty 1 row and 1 column
        fb.div('C3',pos='2,2') #Leave empty 2 rows and 2 columns

    def test_1_simplegrid(self, pane):
        "Build a simple grid with 'grid' and 'layouts'"
        layout = pane.div(display='grid',height='400px',width='400px',
                        margin='10px', style='grid-template-rows:50px,auto,auto,50px;')
        
        layout.div(border='1px solid silver', background='white')
        layout.div(border='1px solid silver', background='yellow')
        layout.div(border='1px solid silver', background='orange')
        layout.div(border='1px solid silver', background='red')
    
    def test_2_htmltable(self, pane):
        """Html table built manually with table object and cycles"""
        t = pane.table()
        tbody = t.tbody()
        for k in range(6):
            row = tbody.tr()
            for j in range(6):
                row.td('cell: %i' % ((k + 1) * 6 + j), border='1px solid green')