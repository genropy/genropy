# -*- coding: utf-8 -*-


class Grouplet(object):
    def __info__(self):
        return dict(caption='Gamma', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.textbox(value='^.label', lbl='Label')
        fb.numberTextBox(value='^.amount', lbl='Amount')
