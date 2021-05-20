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

    def test_3_complextable(self, pane):
        "Design a complex table"
        tbl = pane.table(width='500px')
        h = tbl.thead()
        h.th()
        h.th('2016',width='10em',text_align='center')
        h.th('2015',width='10em',text_align='center')
        h.th('',width='2em')
        tb = tbl.tbody()
        r = tb.tr()
        r.td('Attivo')
        r.td('50.500',text_align='right')
        r.td('80.200',text_align='right')
        r.td().lightbutton(_class='iconbox tinyOpenBranch')
        r = tb.tr()
        r.td('Credito verso soci',text_indent='20px')
        r.td('30.500',text_align='right')
        r.td('0',text_align='right')
        r.td().lightbutton(_class='iconbox tinyOpenBranch')

        r = tb.tr()
        r.td('Mario rossi',text_indent='50px')
        r.td('10.500',text_align='right')
        r.td('0',text_align='right')

        r = tb.tr()
        r.td('Luigi bianchi',text_indent='50px')
        r.td('20.000',text_align='right')
        r.td('0',text_align='right')

        r = tb.tr()
        r.td('Credito verso banche',text_indent='20px')
        r.td('10.000',text_align='right')
        r.td('0',text_align='right')
        r.td().lightbutton(_class='iconbox tinyOpenBranch')

        r = tb.tr()
        r.td('Creval',text_indent='50px')
        r.td('5.500',text_align='right')
        r.td('0',text_align='right')

        r = tb.tr()
        r.td('Banco Popolare',text_indent='50px')
        r.td('4.500',text_align='right')
        r.td('0',text_align='right')


    def test_4_complextable(self, pane):
        "Same as before, but with different styles defined inside pane"
        tbl = pane.table(width='500px',_class='ittc-Soci_chiuso')
        pane.style("""
            .ittc-Attivo_chiuso .ittc-Attivo{
                display:none;
            }
            .ittc-Soci_chiuso .ittc-Soci{
                display:none;
            }
            .ittc-Banche_chiuso .ittc-Banche{
                display:none;
            }
            """)
        h = tbl.thead()
        h.th()
        h.th('2016',width='10em',text_align='center')
        h.th('2015',width='10em',text_align='center')
        h.th('',width='2em')
        tb = tbl.tbody()
        r = tb.tr()
        r.td('Attivo')
        r.td('50.500',text_align='right')
        r.td('80.200',text_align='right')
        r.td().lightbutton(_class='iconbox tinyOpenBranch')
        r = tb.tr(_class='ittc-Attivo')
        r.td('Credito verso soci',text_indent='20px')
        r.td('30.500',text_align='right')
        r.td('0',text_align='right')
        r.td().lightbutton(_class='iconbox tinyOpenBranch')

        r = tb.tr(_class='ittc-Attivo ittc-Soci')
        r.td('Mario rossi',text_indent='50px')
        r.td('10.500',text_align='right')
        r.td('0',text_align='right')

        r = tb.tr(_class='ittc-Attivo ittc-Soci')
        r.td('Luigi bianchi',text_indent='50px')
        r.td('20.000',text_align='right')
        r.td('0',text_align='right')

        r = tb.tr(_class='ittc-Attivo')
        r.td('Credito verso banche',text_indent='20px')
        r.td('10.000',text_align='right')
        r.td('0',text_align='right')
        r.td().lightbutton(_class='iconbox tinyOpenBranch')

        r = tb.tr(_class='ittc-Attivo itcc-Banche')
        r.td('Creval',text_indent='50px')
        r.td('5.500',text_align='right')
        r.td('0',text_align='right')

        r = tb.tr(_class='ittc-Attivo itcc-Banche')
        r.td('Banco Popolare',text_indent='50px')
        r.td('4.500',text_align='right')
        r.td('0',text_align='right')
