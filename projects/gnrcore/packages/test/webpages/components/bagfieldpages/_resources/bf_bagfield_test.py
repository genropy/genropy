# -*- coding: utf-8 -*-

"""BagFieldForm resources for bagfield_test.py

A bagField whose form is neither passed explicitly nor defined on the page is
resolved here: the component looks for a BagFieldForm subclass named
BagField_<field> and calls its bf_content.
"""

from gnr.web.gnrbaseclasses import BagFieldForm


class BagField_gamma(BagFieldForm):
    """Form of the bagField named gamma"""

    def bf_content(self, pane, **kwargs):
        fb = pane.formbuilder()
        fb.textbox(value='^.gamma_1', lbl='Gamma1')
        fb.textbox(value='^.gamma_2', lbl='Gamma2')


class BagField_delta(BagFieldForm):
    """Form of the bagField named delta"""

    def bf_content(self, pane, **kwargs):
        fb = pane.formbuilder()
        fb.textbox(value='^.delta_1', lbl='Delta1')
        fb.textbox(value='^.delta_2', lbl='Delta2')
