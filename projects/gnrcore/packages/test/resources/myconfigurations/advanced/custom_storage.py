# -*- coding: utf-8 -*-


class Grouplet(object):
    def __info__(self):
        return dict(caption='Custom Storage', priority=3,
                    locationpath='custom_data')

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.textbox(value='^.label', lbl='Label')
        fb.textbox(value='^.value', lbl='Value')
