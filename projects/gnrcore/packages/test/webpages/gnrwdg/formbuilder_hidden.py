# -*- coding: utf-8 -*-

"""Hiding formbuilder fields: hidden, hiddenGroup and row_hidden

`hidden` bound to a path hides a field together with its label while the
value is true. `hiddenGroup` gives several fields one name, so hiding one
of them hides the whole group. `row_hidden` hides the formbuilder row the
field sits in. Labels on top of the fields (`mobileFormBuilder`) are hidden
along with their field.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_hidden(self, pane):
        """Hidden alfa / beta hide their field and label; Hidden gamma hides the Row hidden checkbox, which hides the R1 row"""
        fb = pane.formbuilder(cols=2, spacing=10)
        fb.data('.hidden_alfa', True)
        fb.checkbox(value='^.hidden_alfa', label='Hidden alfa')
        fb.checkbox(value='^.hidden_beta', label='Hidden beta')
        fb.textbox(value='^.zzzz', lbl='zzz', colspan=2)

        fb.textbox(value='^.alfa', lbl='Alfa', hidden='^.hidden_alfa')
        fb.checkboxText(value='^.beta', lbl='Beta', hidden='^.hidden_beta', values='pippo,pluto,paperino,/,pancrazio')
        fb.textbox(value='^.yyy', lbl='yyy', colspan=2)
        fb.checkbox(value='^.hidden_gamma', label='Hidden gamma')
        fb.checkbox(value='^.row_hidden', label='Row hidden', hidden='^.hidden_gamma')
        fb.textbox(value='^.uuu', lbl='UUU')

        fb.textbox(value='^.r1', lbl='R1', row_hidden='^.row_hidden')
        fb.textbox(value='^.r2', lbl='R2')

    def test_1_hidden_group(self, pane):
        """Hidden alfa hides Alfa and, through hiddenGroup='alfa', yyy and R1 with it"""
        fb = pane.formbuilder(cols=2, spacing=10)
        fb.data('.hidden_alfa', True)
        fb.checkbox(value='^.hidden_alfa', label='Hidden alfa')
        fb.checkbox(value='^.hidden_beta', label='Hidden beta')
        fb.textbox(value='^.zzzz', lbl='zzz', colspan=2)

        fb.textbox(value='^.alfa', lbl='Alfa', hidden='^.hidden_alfa', hiddenGroup='alfa')
        fb.textbox(value='^.beta', lbl='Beta')
        fb.textbox(value='^.yyy', lbl='yyy', colspan=2, hiddenGroup='alfa')
        fb.checkbox(value='^.hidden_gamma', label='Hidden gamma')
        fb.checkbox(value='^.row_hidden', label='Row hidden')
        fb.textbox(value='^.uuu', lbl='UUU')

        fb.textbox(value='^.r1', lbl='R1', hiddenGroup='alfa')
        fb.textbox(value='^.r2', lbl='R2')

    def test_2_nofb(self, pane):
        """hidden outside a formbuilder, as a formula: type SHOW to see the button and hide the checkbox"""
        pane.textbox('^.status', lbl='Status')
        pane.br()
        pane.button('Test', action='SET .clicked = new Date().toLocaleTimeString();',
                    hidden='^.status?=#v!="SHOW"')
        pane.checkbox(value='^.zio', hidden='^.status?=#v=="SHOW"', label='Not SHOW')
        pane.div('^.clicked')

    def test_3_cbtext(self, pane):
        """A popup checkboxText hidden by a checkbox; Values shows its value"""
        fb = pane.formbuilder(cols=2, spacing=10)
        fb.data('.hidden_beta', True)
        fb.checkbox(value='^.hidden_beta', label='Hidden beta')
        fb.br()
        fb.checkboxText(value='^.beta', lbl='Beta', hidden='^.hidden_beta',
                        values='/2,pippo,pluto,paperino,pancrazio',
                        popup=True)
        fb.textbox(value='^.beta', lbl='Values')

    def test_4_hidden_lblpos_top(self, pane):
        "hidden hides the label as well when labels are on top of the fields"
        fb = pane.mobileFormBuilder(cols=2)
        fb.data('.hidden_alfa', True)
        fb.checkbox(value='^.hidden_alfa', label='Hidden alfa')
        fb.checkbox(value='^.hidden_beta', label='Hidden beta')
        fb.textbox(value='^.alfa', lbl='Alfa', hidden='^.hidden_alfa')
        fb.textbox(value='^.beta', lbl='Beta', hidden='^.hidden_beta')
        fb.textbox(value='^.gamma', lbl='Gamma')
        fb.textbox(value='^.delta', lbl='Delta')

    def test_5_hidden_group_lblpos_top(self, pane):
        "hiddenGroup hides labels too when they are on top of the fields"
        fb = pane.mobileFormBuilder(cols=2)
        fb.data('.hidden_alfa', True)
        fb.checkbox(value='^.hidden_alfa', label='Hidden alfa')
        fb.checkbox(value='^.other', label='Other')
        fb.textbox(value='^.alfa', lbl='Alfa', hidden='^.hidden_alfa', hiddenGroup='alfa')
        fb.textbox(value='^.beta', lbl='Beta')
        fb.textbox(value='^.gamma', lbl='Gamma', hiddenGroup='alfa')
        fb.textbox(value='^.delta', lbl='Delta')
