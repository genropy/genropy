# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method

info = dict(caption='RPC Bar', code='rpc_bar', priority=2)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px',datapath='.bar')
        fb.button('Bar').dataRpc('.rpc_result', self.testRpc)
        fb.div(value='^.rpc_result', lbl='Result')

    @public_method
    def testRpc(self, **kwargs):
        from datetime import datetime
        return 'bar %s' % datetime.now().isoformat()
