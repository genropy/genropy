# -*- coding: utf-8 -*-
import logging

from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from gnr.web.gnrmenu import MenuResolver
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

log = logging.getLogger(__name__)

class GnrMenuProxy(GnrBaseProxy):

    @public_method
    def getMenuLineBadge(self,table=None,handler=None,condition=None,**kwargs):
        """Get badge content for menu line.

        Args:
            table: the table to query
            handler: determines the badge computation method:
                - table method name: calls the specified RPC method on the table
                - '#': returns total record count for the table
                - '#:columnName': returns count filtered by boolean column (WHERE $columnName IS TRUE)
            condition: deprecated, use handler with '#' syntax instead
        """
        if condition:
            # deprecated: use menuLineBadge with '#' prefix for count or '#:columnName' for filtered count
            log.warning("getMenuLineBadge 'condition' parameter is deprecated. Use menuLineBadge='#' for count or '#:columnName' for filtered count")
            return self.page.db.table(table).query(where=condition,**kwargs).count()
        if not handler:
            return
        if not handler.startswith('#'):
            return self.getPublicMethod('rpc',  f'_table.{table}.{handler}')(**kwargs)
        # handler starts with '#': use fetch count, optionally with ':columnName' to filter by boolean column
        where = None
        if ':' in handler:
            fieldpath = handler.split(':')[1]
            if fieldpath[0] not in ('$','@'):
                fieldpath = f'${fieldpath}'
            where = f'{fieldpath} IS TRUE'
        return self.page.db.table(table).query(where=where,**kwargs).count()
            

    def getRoot(self,pkg=None,indexPagePkg=None,**kwargs):
        result = Bag()
        result['root'] = MenuResolver(pagepath=self.page.pagepath,
                                        _page=self.page,
                                        pkg=pkg,**kwargs)
        return result
    


    