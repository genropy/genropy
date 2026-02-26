# -*- coding: utf-8 -*-

info = dict(caption='Contact Info', code='contact_info', priority=1)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.full_name', lbl='Full Name', colspan=2, width='100%')
        fb.textbox(value='^.email', lbl='Email')
        fb.textbox(value='^.phone', lbl='Phone')
