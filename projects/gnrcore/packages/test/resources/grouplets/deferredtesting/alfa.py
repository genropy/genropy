# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method


class Grouplet(object):
    def __info__(self):
        return dict(caption='Alfa', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.button('Build Alfa').dataRpc('.deferred_result', self.buildContent)
        fb.div(value='^.deferred_result', lbl='Result')

    @public_method
    def buildContent(self, **kwargs):
        return self.mainInfo()

    def mainInfo(self):
        return 'deferred alfa'
