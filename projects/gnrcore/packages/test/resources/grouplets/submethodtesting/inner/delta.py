# -*- coding: utf-8 -*-

info = dict(caption='Delta', code='delta', priority=2)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.textbox(value='^.description', lbl='Description')
        fb.checkbox(value='^.active', label='Active')
