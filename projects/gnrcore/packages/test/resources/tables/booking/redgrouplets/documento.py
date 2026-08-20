# -*- coding: utf-8 -*-

"""Second step of the red wizard probe: a plain field, so the wizard has a
stepper and a Next."""

from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Documento', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.div(margin='10px').formlet(cols=1, table='test.booking')
        fb.field('guest_name')
