# -*- coding: utf-8 -*-
import logging

from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from gnr.web.gnrmenu import MenuResolver
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

log = logging.getLogger(__name__)

class GnrMenuProxy(GnrBaseProxy):

    @public_method
    def getMenuLineBadge(self, table=None, handler=None, condition=None, **kwargs):
        """Get badge content for menu line.

        Args:
            table: the table to query
            handler: determines the badge computation method:
                - 'methodName': calls the specified RPC method on the table
                - '#': returns total record count for the table
                - '#:fieldpath': returns count where field has a "positive" value
                - '#:!fieldpath': returns count where field has a "negative" value
                  fieldpath can be prefixed with $ (column) or @ (relation), defaults to $
            condition: deprecated, use handler with '#' syntax instead

        The filter condition depends on the column dtype:
            - Boolean (B): IS TRUE / IS NOT TRUE
            - Numeric (N,L,I,R): IS NOT NULL AND !=0 / IS NULL OR =0
            - Other (text, date, etc.): IS NOT NULL / IS NULL
        """
        if condition:
            log.warning("getMenuLineBadge 'condition' parameter is deprecated. "
                       "Use menuLineBadge='#' for count or '#:columnName' for filtered count")
            return self.page.db.table(table).query(where=condition, **kwargs).count()
        if not handler:
            return
        # handler is a table method name - call it via RPC
        if not handler.startswith('#'):
            return self.getPublicMethod('rpc', f'_table.{table}.{handler}')(**kwargs)

        # handler starts with '#': use record count
        where = None
        tblobj = self.page.db.table(table)
        if ':' in handler:
            # extract fieldpath after ':'
            fieldpath = handler.split(':')[1]

            # check for negation prefix '!'
            positiveCondition = True
            if fieldpath.startswith('!'):
                fieldpath = fieldpath[1:]
                positiveCondition = False

            # auto-prepend $ if no prefix specified
            if fieldpath[0] not in ('$', '@'):
                fieldpath = f'${fieldpath}'

            # build WHERE clause based on column dtype
            column = tblobj.column(fieldpath)
            if not column:
                log.error(f"Column {fieldpath} not found in table {table}")
                return 0
            dtype = column.attributes.get('dtype')
            if dtype == 'B':
                # boolean: check for TRUE/NOT TRUE
                where = f'{fieldpath} IS TRUE' if positiveCondition else f'{fieldpath} IS NOT TRUE'
            elif dtype in ('N', 'L', 'I', 'R'):
                # numeric: check for non-null and non-zero
                if positiveCondition:
                    where = f'{fieldpath} IS NOT NULL AND {fieldpath}!=0'
                else:
                    where = f'{fieldpath} IS NULL OR {fieldpath}=0'
            else:
                # text, date, etc.: check for non-null
                where = f'{fieldpath} IS NOT NULL' if positiveCondition else f'{fieldpath} IS NULL'

        return tblobj.query(where=where, **kwargs).count()
            

    def getRoot(self,pkg=None,indexPagePkg=None,**kwargs):
        result = Bag()
        result['root'] = MenuResolver(pagepath=self.page.pagepath,
                                        _page=self.page,
                                        pkg=pkg,**kwargs)
        return result
    


    