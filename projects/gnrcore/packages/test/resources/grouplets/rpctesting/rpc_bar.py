# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method


class Grouplet(object):
    def __info__(self):
        return dict(caption='RPC Bar', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.button('Bar').dataRpc('.rpc_result', self.testRpc)
        fb.div(value='^.rpc_result', lbl='Result')

    @public_method
    def testRpc(self, **kwargs):
        from datetime import datetime
        return 'bar %s' % datetime.now().isoformat()
