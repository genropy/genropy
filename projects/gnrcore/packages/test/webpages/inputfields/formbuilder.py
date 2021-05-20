# -*- coding: utf-8 -*-

"""Formbuilder"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_htmltable(self, pane):
        "Formbuilder is basically and HTML table"
        t = pane.table(style='border-collapse:collapse',border='1px solid silver').tbody()
        r = t.tr()
        r.td(width='100%')
        r.td(width='50%').div('Pippo')
        r.td(width='50%').div('Pluto')

        fb = pane.formbuilder(cols=2,border_spacing='3px',border='1px solid silver',colswidth='auto')
        fb.div('Pippo',lbl='Alfa')
        fb.div('Pluto',lbl='Beta')

    def test_1_basic(self, pane):
        "Formbuilder with basic widgets: use of textbox, readOnly and data"
        fb = pane.formbuilder(cols=2, border_spacing='10px', fld_width='100%')
        fb.textbox(value='^.aaa', lbl='Textbox')
        fb.data('.bb','piero')
        fb.textbox(value='^.bb', lbl='readOnly',readOnly=True)
        fb.textbox(value='^.cc', lbl='Bigger textbox', colspan=2)
        
        b = Bag()
        b.setItem('foo',None,id='foo',caption='Foo',test='AAA')
        b.setItem('bar',None,id='bar',caption='Bar',test='BBB')
        b.setItem('spam',None,id='spam',caption='Spam',test='CCC')
        
        fb.data('.xxx',b)
        fb.combobox(value='^.ttt',lbl='Combobox',width='10em',storepath='.xxx',selected_test='.zzz')
        fb.div('^.zzz')

    def test_2_tabindex(self, pane):
        "Use of tabindex to customize behaviour if you press tab. Label positioned on top"
        fb = pane.formbuilder(cols=2, lblpos='T')
        fb.textbox(value='^.val_1',lbl='Val 1',tabindex=1)
        fb.textbox(value='^.val_3',lbl='Val 3',tabindex=3)
        fb.textbox(value='^.val_2',lbl='Val 2',tabindex=2)
        fb.textbox(value='^.val_4',lbl='Val 4',tabindex=4)

    def test_3_tabindex(self, pane):
        "Use of byColumn, move vertically if you press tab. Last field is disabled"
        fb = pane.formbuilder(cols=4,byColumn=True, fld_width='100%')
        fb.textbox(value='^.val_1',lbl='Val 1')
        fb.textbox(value='^.val_3',lbl='Val 3')
        fb.textbox(value='^.val_2',lbl='Val 2')
        fb.textbox(value='^.val_4',lbl='Val 4')
        fb.textbox(value='^.val_5',lbl='Val 5')
        fb.textbox(value='^.val_7',lbl='Val 7')
        fb.textbox(value='^.val_6',lbl='Val 6')
        fb.textbox(value='^.val_8',lbl='Val 8', disabled=True)
