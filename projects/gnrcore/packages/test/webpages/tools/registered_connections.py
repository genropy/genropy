# -*- coding: utf-8 -*-

"""The site registers of live connections and live pages, as trees

The site keeps ONE register, `site.register`, read through views: `connections()`
gives one entry per browser connection, `pages()` one per page open inside them,
and `connection(id)` / `page(id)` return a single entry with its store attached.
Both cases walk it lazily through a BagResolver, so a branch is only loaded when
it is opened.
The first case shows the connections with their pages nested underneath and
writes a value into a connection store; the second shows the flat page register
on its own, which is the view `PageListResolver` gives without a connection
above it.
"""


import datetime
from gnr.core.gnrbag import Bag, BagResolver

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_registered_connections(self, pane):
        """Connections with their pages nested; picking one writes a value into its connection store"""
        bc = pane.borderContainer(height='500px', datapath='.test1')
        left = bc.contentPane(region='left', width='200px', splitter=True)
        left.dataRemote('.curr_connections.connections', 'curr_connections', cacheTime=2)
        left.tree(storepath='.curr_connections', selected_connection_id='^.connection_id')
        center = bc.contentPane(region='center')
        fb = center.formbuilder(cols=1, border_spacing='4px', fld_width='18em')
        fb.div('^.connection_id', lbl='Selected connection')
        fb.textbox(value='^.path', lbl='Path in the connection store')
        fb.textbox(value='^.value', lbl='Value')
        fb.button('Send', fire='.send')
        fb.div('^.result', lbl='Result')
        center.dataRpc('.result', 'send_data_to_connection',
                       v='=.value', p='=.path', _fired='^.send',
                       connection_id='=.connection_id',
                       _onResult='FIRE .reload_store;')
        # The value lands in the selected connection's store, which is buried inside the
        # tree on the left. Under the form is where a reader looks right after Send.
        center.div('Store of the selected connection', font_weight='bold',
                   padding='10px 0 2px 0')
        center.dataRpc('.connection_store', 'connection_store', connection_id='^.connection_id',
                       _onResult='FIRE .rebuild_store;', _fired='^.reload_store')
        center.div(height='250px', overflow='auto',
                   border='1px solid silver').tree(storepath='.connection_store',
                                                   _fired='^.rebuild_store')

    def test_2_registered_pages(self, pane):
        """The page register alone, without the connection level above it"""
        box = pane.div(datapath='.test2', height='500px', overflow='auto')
        box.button('Refresh', fire='.refresh_tree')
        box.dataRemote('.curr_pages.pages', 'curr_pages', cacheTime=2)
        box.tree(storepath='.curr_pages', _fired='^.refresh_tree')

    def rpc_send_data_to_connection(self, v=None, p=None, connection_id=None):
        # No silent fallback to this page's own connection: writing into the wrong
        # store without saying so is worse than refusing.
        if not connection_id:
            return 'Pick a connection in the tree first'
        with self.connectionStore(connection_id=connection_id) as store:
            store.setItem(p, v)
        return 'Written: %s = %s' % (p, v)

    def rpc_connection_store(self, connection_id=None):
        if not connection_id:
            return Bag()
        return self.connectionStore(connection_id=connection_id).getItem(None)

    def rpc_curr_connections(self):
        return ConnectionListResolver()

    def rpc_curr_pages(self):
        return PageListResolver()

class ConnectionListResolver(BagResolver):
    classKwargs = {'cacheTime': 1,
                   'readOnly': False,
                   'connectionId': None}
    classArgs = ['connectionId']

    def load(self):
        if not self.connectionId:
            return self.list_connections()
        else:
            return self.one_connection()

    def one_connection(self):
        connection = self._page.site.register.connection(self.connectionId, include_data=True)
        item = Bag()
        if connection is None:
            # the connection has closed since the list was built: a normal case, not an error
            item['info'] = Bag(dict(connectionId=self.connectionId,
                                    closed='Connection %s has closed' % self.connectionId))
            return item
        data = connection.pop('data', None)
        item['info'] = Bag([('%s:%s' % (k, str(v).replace('.', '_')), v)
                            for k, v in list(connection.items())])
        item['data'] = data
        # The form reads connection_id off the SELECTED node, with no fallback to its
        # ancestors, so every node of the branch must carry it. The walk below cannot
        # enter `pages`, still an unresolved resolver: that node gets it here, and its
        # children get it from the resolver when they load.
        item.setItem('pages', PageListResolver(connectionId=self.connectionId), cacheTime=2,
                     connection_id=self.connectionId)
        item.walk(lambda node: node.setAttr(connection_id=self.connectionId, trigger=False))
        return item

    def list_connections(self):
        connectionsDict = self._page.site.register.connections()
        result = Bag()
        for connection_id, connection in list(connectionsDict.items()):
            delta = int((datetime.datetime.now() - connection['start_ts']).total_seconds())
            user = (connection['user'] or 'Anonymous').replace('.', '_')
            connection_name = connection['connection_name']
            itemlabel = '%s - %s (%i)' % (user, connection_name.replace('.', '_'), delta)
            resolver = ConnectionListResolver(connection_id)
            result.setItem(itemlabel, resolver, cacheTime=1, connection_id=connection_id)
        return result

class PageListResolver(BagResolver):
    classKwargs = {'cacheTime': 1,
                   'readOnly': False,
                   'pageId': None,
                   'connectionId': None}
    classArgs = ['pageId', 'connectionId']

    def load(self):
        if not self.pageId:
            return self.list_pages()
        else:
            return self.one_page()

    def one_page(self):
        page = self._page.site.register.page(self.pageId, include_data=True)
        item = Bag()
        if page is None:
            # the page has closed since the list was built: a normal case, not an error
            item['info'] = Bag(dict(pageId=self.pageId, closed='Page %s has closed' % self.pageId))
        else:
            data = page.pop('data', None)
            item['info'] = Bag([('%s:%s' % (k, str(v).replace('.', '_')), v) for k, v in list(page.items())])
            item['data'] = data
        if self.connectionId:
            item.walk(lambda node: node.setAttr(connection_id=self.connectionId, trigger=False))
        return item

    def list_pages(self):
        pagesDict = self._page.site.register.pages(connection_id=self.connectionId)
        result = Bag()
        for page_id, page in list(pagesDict.items()):
            delta = int((datetime.datetime.now() - page['start_ts']).total_seconds())
            pagename = page['pagename'].replace('.py', '')
            user = (page['user'] or 'Anonymous').replace('.', '_')
            ip = page['user_ip'].replace('.', '_')
            itemlabel = '%s (%s) - %s (%i)' % (user, ip, pagename.replace('.', '_'), delta)
            resolver = PageListResolver(page_id, self.connectionId)
            result.setItem(itemlabel, resolver, cacheTime=1, connection_id=self.connectionId)
        return result
