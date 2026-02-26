# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method

info = dict(caption='Alfa', code='alfa', priority=1)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px', datapath='.alfa')
        fb.button('Build Alfa').dataRpc('.deferred_result', self.buildContent)
        fb.div(value='^.deferred_result', lbl='Result')

    @public_method
    def buildContent(self, **kwargs):
        return self.mainInfo()

    def mainInfo(self):
        return 'deferred alfa'
