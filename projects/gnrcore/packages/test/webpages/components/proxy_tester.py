# -*- coding: utf-8 -*-

"""Page proxies: reach a component's methods through a named proxy

A BaseComponent declaring proxy=True is attached to the page under a name
derived from its class (Proxy_test becomes self.proxy_test), so its methods are
reachable from the page code and, when decorated with @public_method, from the
client too. The component this page requires lives in
webpages/_resources/proxy_tester.py.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,proxy_tester"

    def test_0_data(self, pane):
        """Server side: call a proxy method while building the page

        self.proxy_test is the Proxy_test component; ciao_test() runs during
        the page build and its return value is written straight into the div.
        """
        pane.div(self.proxy_test.ciao_test())

    def test_1_data(self, pane):
        """Client side: call a proxy @public_method over rpc

        The same proxy exposes ciao() as a public method, so it can be the
        target of a dataRpc: the result lands on the test path and the div
        bound to it shows the answer.
        """
        pane.div('^test')
        pane.dataRpc('^test', self.proxy_test.ciao, _onStart=True)
