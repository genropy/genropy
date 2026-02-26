# -*- coding: utf-8 -*-

info = dict(caption='Gamma', code='gamma', priority=1)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.textbox(value='^.label', lbl='Label')
        fb.numberTextBox(value='^.amount', lbl='Amount')
