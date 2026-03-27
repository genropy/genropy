# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from gnr.web import logger


class GnrBadgeProxy(GnrBaseProxy):

    @public_method
    def getBadgeHandler(self, table=None, handler=None, condition=None, **kwargs):
        """Generic badge content resolver shared by menuLineBadge and tabBadge.

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
            logger.warning("getBadgeHandler 'condition' parameter is deprecated. "
                           "Use '#' or '#:columnName' handler syntax instead")
            return self.page.db.table(table).query(where=condition, **kwargs).count()
        if not handler:
            return
        if not handler.startswith('#'):
            return self.getPublicMethod('rpc', f'_table.{table}.{handler}')(**kwargs)

        where = None
        tblobj = self.page.db.table(table)
        if ':' in handler:
            fieldpath = handler.split(':')[1]
            positiveCondition = True
            if fieldpath.startswith('!'):
                fieldpath = fieldpath[1:]
                positiveCondition = False
            if fieldpath[0] not in ('$', '@'):
                fieldpath = f'${fieldpath}'
            column = tblobj.column(fieldpath)
            if column is None:
                raise ValueError(f"Column {fieldpath} not found in table {table}")
            dtype = column.attributes.get('dtype')
            if dtype == 'B':
                where = f'{fieldpath} IS TRUE' if positiveCondition else f'{fieldpath} IS NOT TRUE'
            elif dtype in ('N', 'L', 'I', 'R'):
                if positiveCondition:
                    where = f'{fieldpath} IS NOT NULL AND {fieldpath}!=0'
                else:
                    where = f'{fieldpath} IS NULL OR {fieldpath}=0'
            else:
                where = f'{fieldpath} IS NOT NULL' if positiveCondition else f'{fieldpath} IS NULL'
        return tblobj.query(where=where, **kwargs).count() or None
