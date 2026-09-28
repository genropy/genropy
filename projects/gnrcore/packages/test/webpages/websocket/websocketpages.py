# -*- coding: utf-8 -*-

"""Connected pages with their connection and user, polled over the websocket

Like `testcomunication.py` but reading the register through
`self.asyncServer`, and returning the page id, the connection id and the user
of every entry rather than just its key. The call is fired with _timing=.5 so
the grid keeps refreshing while other pages open and close.
"""

from gnr.core.gnrdecorator import websocket_method
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    def main(self,root,**kwargs):
        bc = root.borderContainer(datapath='main')
        top = bc.contentPane(region='top', height='50px')
        fb = top.formBuilder(cols=4)
        fb.button(label='getPages',fire='.getPages')
        top.dataRpc('.pages', self.getPages, _fired='^.getPages',httpMethod='WSK',_timing=.5)

        bc.contentPane(region='center').quickgrid(value='^.pages')

        
        
        
    @websocket_method
    def getPages(self,**kwargs):
        pages= self.asyncServer.pages
        b=Bag()
        for k,page in list(pages.items()):
            kw = dict([(key,getattr(page,key,None)) for key in ('page_id','connection_id','user')])
            b[k] = Bag(kw)
        return b
