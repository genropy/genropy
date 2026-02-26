# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method

info = dict(caption='Beta', code='beta', priority=2)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.button('Build Beta').dataRpc('.deferred_result', self.buildContent)
        fb.div(value='^.deferred_result', lbl='Result')

    @public_method
    def buildContent(self, **kwargs):
        return self.mainInfo()

    def mainInfo(self):
        return 'deferred beta'
