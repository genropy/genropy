# -*- coding: utf-8 -*-

from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from gnr.web.gnrmenu import MenuResolver
from gnr.core.gnrbag import Bag


class GnrMenuProxy(GnrBaseProxy):
    def getRoot(self,pkg=None,**kwargs):
        result = Bag()
        result['root'] = MenuResolver(path=getattr(self.page,'menu_path',None), 
                                        pagepath=self.page.pagepath,
                                        _page=self.page,pkg=pkg,**kwargs)
        return result
    


    