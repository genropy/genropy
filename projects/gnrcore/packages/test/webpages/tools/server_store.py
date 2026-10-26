# -*- coding: utf-8 -*-

"""The server-side page store, read and written from the page that owns it and from another

Every page registered with the site carries a server-side store, reachable as
`self.pageStore(page_id)`. The three cases walk out from the current page: the
first sets and gets an item in its own store, the second does the same against a
page picked from the menu of live pages, and the third leaves the item API for
`_serverpath`, which keeps a client datapath and a server store path in sync in
both directions without an explicit call. The form, the page menu and the store
tree all come from the `storetester` resource, shared with `server_store_2.py`
and `setclientdata.py`.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,storetester:StoreTester"

    def test_1_current_page(self, pane):
        """Sets and reads an item in the store of this page, through serverStoreSet/serverStoreGet"""
        self.common_form(pane, datapath='test_1')

    def test_2_external_page(self, pane):
        """The same form against another page's store: pick the target from the page menu"""
        center = self.common_pages_container(pane, height='350px', background='whitesmoke',
                                             datapath='test_2')
        self.common_form(center)

    def test_3_server_data(self, pane):
        """_serverpath binds .foo.bar to the server path `xx`; .foo.baz, outside it, is the control"""
        center = self.common_pages_container(pane, height='350px', background='whitesmoke',
                                             datapath='test_3')
        center.data('.foo.bar', _serverpath='xx')
        fb = center.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.foo.bar', lbl='Server store value')
        fb.textbox(value='^.foo.baz', lbl='Value not in server subscribed path')
        fb.button('Ping', action='genro.ping()')
