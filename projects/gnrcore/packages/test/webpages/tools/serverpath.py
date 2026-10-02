# -*- coding: utf-8 -*-

"""Binding a client datapath to the page's server store: `_serverpath`

A datum declared with `_serverpath` is kept in sync with a path of the page's
server-side store in BOTH directions: what the client writes arrives in the
store without an explicit call, and what an RPC writes into the store comes
back down to the client without the page asking for it. The cases walk the
binding out from the simplest form: a plain data node, the same on a nested
server path, an answer written DEEPER than the bound path, a whole Bag of
which only one node changes, and finally `attr_serverpath`, which puts the
binding on the widget instead of on a data node of its own. The page polls
(`auto_polling`/`user_polling`) because that is how a value pushed from the
server reaches a client that is not asking for it.
"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    auto_polling = 10
    user_polling = 3

    def test_0_serverpath(self, pane):
        """The client writes: the textbox value reaches `mytest0.mirror` in the page store

        The button reads that path back through an RPC, which is the only way to
        see the upward half of the binding from the page itself.
        """
        fb = pane.formbuilder(cols=1, border_spacing='3px', datapath='test0')
        fb.data('.willbesetonserver', '', _serverpath='mytest0.mirror')
        fb.datetextbox(value='^.willbesetonserver', lbl='Set on server')
        fb.button('Get value from server', fire='.get')
        fb.div('^.fromserver', lbl='Value in the store')
        fb.dataRpc('.fromserver', 'get_value_on_server', _fired='^.get')

    def rpc_get_value_on_server(self):
        store = self.pageStore()
        return store.getItem('mytest0.mirror')

    def test_1_serverpath(self, pane):
        """The server writes: the RPC sets `mytest1.mirror` and the bound datum mirrors it back down"""
        fb = pane.formbuilder(cols=1, border_spacing='3px', datapath='test1')
        fb.data('.mysync', '', _serverpath='mytest1.mirror')
        fb.textbox(value='^.mydata', lbl='Data')
        fb.div('^.mysync', lbl='Answer')
        fb.dataRpc('dummy', 'setval', value='^.mydata',
                   serverpath='mytest1.mirror')

    def test_2_serverpath(self, pane):
        """The same, on a nested server path: `mytest2.mirror.ppp` instead of a root item"""
        fb = pane.formbuilder(cols=1, border_spacing='3px', datapath='test2')
        fb.data('.mysync', '', _serverpath='mytest2.mirror.ppp')
        fb.textbox(value='^.mydata', lbl='Data')
        fb.div('^.mysync', lbl='Answer')
        fb.dataRpc('dummy', 'setval', value='^.mydata',
                   serverpath='mytest2.mirror.ppp')

    def test_3_serverpath(self, pane):
        """The answer lands DEEPER than the bound path: `.mysync` binds the root, `.mysync.answer.1.2.3` receives"""
        fb = pane.formbuilder(cols=1, border_spacing='3px', datapath='test3')
        fb.data('.mysync', '', _serverpath='mytest3.mirror')
        fb.textbox(value='^.mydata', lbl='Data')
        fb.div('^.mysync.answer.1.2.3', lbl='Answer')
        fb.dataRpc('dummy', 'setval', value='^.mydata',
                   serverpath='mytest3.mirror.answer.1.2.3')

    def test_4_innerpath(self, pane):
        """A whole Bag is bound: the RPC writes one node of it and only that node changes"""
        b = Bag()
        b['foo.bar'] = 'test'
        pane.data('.mypath4', b, _serverpath='myserverpath4')
        fb = pane.formbuilder(cols=2)
        fb.textbox(value='^.tosend', lbl='Value to send')
        fb.div('^.mypath4.foo.bar', lbl='Result')
        fb.dataRpc('dummy', 'setval', serverpath='myserverpath4.foo.bar',
                   value='^.tosend')

    def test_5_serverpath_widget(self, pane):
        """`attr_serverpath` binds from the widget itself, with no separate data node"""
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.mario', attr_serverpath='mario_path', lbl='With serverpath')

    def rpc_setval(self, serverpath=None, value=None):
        with self.pageStore() as store:
            store.setItem(serverpath, value)
