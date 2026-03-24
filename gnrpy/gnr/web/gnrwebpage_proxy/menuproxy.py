# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from gnr.web.gnrmenu import MenuResolver


class GnrMenuProxy(GnrBaseProxy):

    def getRoot(self, pkg=None, indexPagePkg=None, **kwargs):
        result = Bag()
        result['root'] = MenuResolver(pagepath=self.page.pagepath,
                                        _page=self.page,
                                        pkg=pkg, **kwargs)
        return result
