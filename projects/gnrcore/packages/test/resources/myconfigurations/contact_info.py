# -*- coding: utf-8 -*-


class Grouplet(object):
    def __info__(self):
        return dict(caption='Contact Info', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.full_name', lbl='Full Name', colspan=2, width='100%')
        fb.textbox(value='^.email', lbl='Email')
        fb.textbox(value='^.phone', lbl='Phone')
