# -*- coding: utf-8 -*-

"""Lists the pages currently connected, asked over the websocket channel

The getPages button calls a `websocket_method` with httpMethod='WSK': the
method reads `self.ws_site.pages`, the page register of the async server, and
returns it as a Bag the quickgrid displays. It is the simplest check that the
websocket daemon is up and that this page is registered on it.
"""

from gnr.core.gnrdecorator import websocket_method, public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):

    def main(self,root,**kwargs):
        bc = root.borderContainer(height='100%')
        top = bc.contentPane(region='top', height='150px', datapath='ws_top')
        
        top.dataRpc('.pages', self.getPages, _fired='^.getPages',httpMethod='WSK')
        fb = top.formBuilder(cols=4)
        fb.button(label='getPages',fire='.getPages')
        fb.quickgrid(value='^.pages',height='300px',width='400px')
        
        
    @websocket_method
    def getPages(self):
        #wdb.set_trace()
        pages= self.ws_site.pages
        b=Bag()
        for k,page in list(pages.items()):
            b[k]=Bag(dict(pageid=k))
        return b


    @public_method
    def test_rpc(self):
        """HTTP counterpart of getPages, kept to compare the two channels"""
        return 'test ok'
