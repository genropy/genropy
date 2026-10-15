# -*- coding: utf-8 -*-

"""Editing another page's whole server store as a Bag, in a tree

Where `server_store.py` sets and gets one item at a time, this page reads the
WHOLE store of a page picked from the menu of live pages, shows it as a tree,
and writes an edited node back through `pageStore(p_id)`. The round trip is the
point: the change lands in the other page's store, not in this one's.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,storetester:StoreTester"

    def test_0_firsttest(self, pane):
        """Pick a page from the menu, edit a node of its store, Apply Changes writes it back"""
        center = self.common_pages_container(pane, height='500px', background='whitesmoke',
                                             datapath='test_0')
        bc = center.borderContainer(height='100%')
        top = bc.contentPane(region='top').slotToolbar('*,confirm')
        top.confirm.button('Apply Changes', fire='.applyOnRemote')
        bc.dataRpc('.remote_page.data', 'getRemotePageData', p_id='^.info.pageId',
                   _onResult='FIRE .rebuild_tree', _fired='^.getRemotePageData')
        # The editor writes through into `.remote_page.data`, so that IS the edited bag:
        # its own `.bagNodeEditor.data` is never written, the grid stages rows in a workspace.
        bc.dataRpc('.dummy', 'applyOnRemote', _fired='^.applyOnRemote', editedData='=.remote_page.data',
                   currpath='=.currpath', p_id='=.info.pageId', _onResult='FIRE .getRemotePageData;')

        # A BagNodeEditor is fed by one topic and nothing else, `<its nodeId>_currentPath`;
        # publishing it on selection is what the dev palette does to pair the two widgets.
        bc.contentPane(region='left', width='200px').tree(storepath='.remote_page', selectedPath='.currpath',
                                                          _fired='^.rebuild_tree', nodeId='remote_page_tree',
                                                          selfsubscribe_onSelected="""
                                                          genro.publish('remote_page_tree_editbagbox_currentPath',
                                                                        $1.item.getFullpath(null, genro._data));
                                                          """)
        bc.contentPane(region='center').BagNodeEditor(nodeId='remote_page_tree_editbagbox',
                                                      datapath='.bagNodeEditor', bagpath='.remote_page')

    def rpc_getRemotePageData(self, p_id=None, **kwargs):
        store = self.pageStore(p_id)
        return store.getItem(None)

    def rpc_applyOnRemote(self, p_id=None, editedData=None, currpath=None, **kwargs):
        # the root node is `data` itself, the whole store: no node picked to write back
        if not currpath or currpath == 'data':
            return
        # the tree's paths are rooted at `.remote_page`, whose `data` IS the store
        if currpath.startswith('data.'):
            currpath = currpath[5:]
        with self.pageStore(p_id) as store:
            store.setItem(currpath, editedData[currpath])
