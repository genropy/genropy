# -*- coding: utf-8 -*-

"""Child page of polling_iframe: it never polls on its own"""

from datetime import datetime

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_call(self, pane):
        """Each press sends one rpc: two failed ones, five seconds apart, make an outage"""
        pane.button('Server call', action='FIRE .call')
        pane.dataRpc('.result', self.serverTime, _fired='^.call')
        pane.div('^.result')

    @public_method
    def serverTime(self):
        return datetime.now().strftime('%H:%M:%S')
