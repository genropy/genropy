# -*- coding: utf-8 -*-

from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from gnr.web.gnrmenu import MenuResolver
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrMenuProxy(GnrBaseProxy):

    @public_method
    def getMenuLineBadge(self,table=None,handler=None,condition=None,conditionColumn=None,**kwargs):
        if handler:
            return self.getPublicMethod('rpc',  f'_table.{table}.{handler}')(**kwargs)
        if conditionColumn:
            condition = f'${conditionColumn} IS TRUE'
        if condition:
            return self.page.db.table(table).query(where=condition,**kwargs).count()

    def getRoot(self,pkg=None,indexPagePkg=None,**kwargs):
        result = Bag()
        result['root'] = MenuResolver(pagepath=self.page.pagepath,
                                        _page=self.page,
                                        pkg=pkg,**kwargs)
        return result
    


    