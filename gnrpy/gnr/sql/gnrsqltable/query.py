# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.query : Query building and WHERE translation
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Query building, WHERE translation and column utilities.

Provides :class:`QueryMixin` — a mixin for :class:`~gnrsqltable.table.SqlTable`
that contains the core ``query()`` method, related-query helpers, WHERE
translation, and column-string parsing utilities.
"""

from __future__ import annotations

from gnr.core import gnrstring
from gnr.core.gnrdecorator import extract_kwargs
from gnr.sql.gnrsqldata import SqlQuery

from gnr.sql.gnrsqltable.helpers import add_sql_comment, orm_audit_log


class QueryMixin:
    """Query building, WHERE translation and column helpers."""

    # ------------------------------------------------------------------
    #  Key parsing and related queries
    # ------------------------------------------------------------------

    def parseSerializedKey(self, key, field=None):
        """Parse a serialized composite primary key into a dict.

        :param key: serialized key string
        :param field: field name (defaults to table pkey)
        :returns: dict mapping key components to values
        """
        field = field or self.pkey
        composed_of = self.column(field).attributes.get('composed_of')
        if not composed_of:
            return {field: key}
        pkeykeys = composed_of.strip('[]').split(',')
        pkeyvalues = self.db.typeConverter.fromJson(key)
        return dict(zip(pkeykeys, pkeyvalues))

    def relatedQueryPars(self, where=None, field=None, value=None,
                         kwargs=None):
        where = [where] if where else []
        if value and self.column(field).attributes.get('composed_of'):
            joinDict = self.parseSerializedKey(value, field=field)
        else:
            joinDict = {field: value}
        for k, v in joinDict.items():
            where.append(f'${k}=:rq_val_{k}')
            kwargs[f'rq_val_{k}'] = v
        return dict(where=' AND '.join(where), **kwargs)

    def relatedQuery(self, where=None, field=None, value=None, **kwargs):
        return self.query(
            **self.relatedQueryPars(
                where=where, field=field, value=value, kwargs=kwargs,
            ),
        )

    # ------------------------------------------------------------------
    #  WHERE translation
    # ------------------------------------------------------------------

    def opTranslate(self, column, op, value, dtype=None, sqlArgs=None):
        return self.whereTranslator.prepareCondition(
            column, op, value, dtype, sqlArgs, tblobj=self,
        )

    @property
    def whereTranslator(self):
        with self.db.tempEnv(currentImplementation=self.dbImplementation):
            return self.db.whereTranslator

    def sqlWhereFromBag(self, wherebag, sqlArgs=None, **kwargs):
        """Build a SQL WHERE clause from a Bag.

        :param wherebag: a Bag describing the conditions
        :param sqlArgs: dict to collect SQL parameters
        """
        if sqlArgs is None:
            sqlArgs = {}
        self.model.virtual_columns
        result = self.whereTranslator(self, wherebag, sqlArgs, **kwargs)
        return result, sqlArgs

    def frozenSelection(self, fpath):
        """Restore a pickled selection and verify it belongs to this table.

        :param fpath: file path of the frozen selection
        """
        selection = self.db.unfreezeSelection(fpath)
        assert selection.dbtable == self, (
            'the frozen selection does not belong to this table'
        )
        return selection

    # ------------------------------------------------------------------
    #  Core query method
    # ------------------------------------------------------------------

    @extract_kwargs(jc=True)
    @add_sql_comment
    @orm_audit_log
    def query(self, columns=None, where=None, order_by=None,
              distinct=None, limit=None, offset=None,
              group_by=None, having=None, for_update=False,
              relationDict=None, sqlparams=None,
              excludeLogicalDeleted=True, excludeDraft=True,
              addPkeyColumn=True, subtable=None,
              ignoreTableOrderBy=False, ignorePartition=False,
              locale=None, mode=None, _storename=None,
              checkPermissions=False, aliasPrefix=None,
              joinConditions=None, jc_kwargs=None, **kwargs):
        """Build and return a :class:`~gnr.sql.gnrsqldata.SqlQuery`.

        :param columns: SELECT columns expression
        :param where: WHERE clause
        :param order_by: ORDER BY clause
        :param distinct: if ``True``, SELECT DISTINCT
        :param limit: max rows
        :param offset: row offset
        :param group_by: GROUP BY clause
        :param having: HAVING clause
        :param for_update: lock rows for update
        :param excludeLogicalDeleted: skip logically deleted records
        :param excludeDraft: skip draft records
        :param addPkeyColumn: auto-add pkey column
        """
        joinConditions = joinConditions or {}
        for v in list(jc_kwargs.values()):
            rel, cond = v.split(':', 1)
            one_one = None
            if rel.endswith('*'):
                one_one = True
                rel = rel[0:-1]
            joinConditions[rel] = dict(
                condition=cond, params=dict(), one_one=one_one,
            )
        packageStorename = self.pkg.attributes.get('storename')
        if packageStorename and _storename is None:
            _storename = packageStorename
        query = SqlQuery(
            self, columns=columns, where=where, order_by=order_by,
            distinct=distinct, limit=limit, offset=offset,
            group_by=group_by, having=having, for_update=for_update,
            relationDict=relationDict, sqlparams=sqlparams,
            excludeLogicalDeleted=excludeLogicalDeleted,
            excludeDraft=excludeDraft,
            ignorePartition=ignorePartition,
            addPkeyColumn=addPkeyColumn,
            ignoreTableOrderBy=ignoreTableOrderBy,
            locale=locale, _storename=_storename,
            checkPermissions=checkPermissions, jc_kwargs=jc_kwargs,
            aliasPrefix=aliasPrefix, joinConditions=joinConditions,
            subtable=subtable, **kwargs,
        )
        return query

    # ------------------------------------------------------------------
    #  Column string utilities
    # ------------------------------------------------------------------

    def columnsFromString(self, columns=None):
        """Parse a columns specification into a list of ``$col`` references.

        :param columns: comma-separated string or list of column names
        """
        result = []
        if not columns:
            return result
        if isinstance(columns, str):
            columns = gnrstring.splitAndStrip(columns)
        for col in columns:
            if col[0] not in ('@', '$', '('):
                col = '$%s' % col
            result.append(col)
        return result

    def getQueryFields(self, columns=None, captioncolumns=None):
        """Return query fields from column specs or caption columns."""
        columns = columns or self.model.queryfields or captioncolumns
        return self.columnsFromString(columns)

    def colToAs(self, col):
        """Convert a column reference to its alias name."""
        return self.db.colToAs(col)

    def relationName(self, relpath):
        """Return the human-readable name for a relation path."""
        relpath = self.model.resolveRelationPath(relpath)
        attributes = self.model.relations.getAttr(relpath)
        joiner = attributes['joiner']
        if joiner['mode'] == 'M':
            relpkg, reltbl, relfld = joiner['many_relation'].split('.')
            targettbl = '%s.%s' % (relpkg, reltbl)
            result = (
                joiner.get('many_rel_name')
                or self.db.table(targettbl).name_plural
            )
        else:
            relpkg, reltbl, relfld = joiner['one_relation'].split('.')
            targettbl = '%s.%s' % (relpkg, reltbl)
            result = (
                joiner.get('one_rel_name')
                or self.db.table(targettbl).name_long
            )
        return result
