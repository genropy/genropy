# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy app - see LICENSE for details
# module gnrsqltable_proxy.selection : table level part of the getSelection flow
# Copyright (c)     : 2004 - 2026 Softwell sas - Milano
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

"""Table level part of the getSelection flow.

:class:`SelectionProxy` is attached to every table of a ``GnrApp`` database by
``gnr.app.gnrdbo.TableBase.selectionProxy``.  It holds the part of the
``getSelection`` flow that only needs the table and the database: column
processing, WHERE bag decoding, join condition decoding, external store
queries, saved queries and views, the default query construction, the record
count and the serialization of a query for the client.

It never references a web page.  Everything the page provides — the
``customSqlOp_*`` callbacks, the resolved expression dictionary, the locale, the
pkeys of a frozen selection, the join conditions of a SQL context — is passed in
as a parameter or as a callable.

The custom operator callbacks arrive in two shapes, and the difference is not
cosmetic: a method that always decodes a WHERE bag takes the dictionary
(``customOpCbDict``), a method that decodes one only for some inputs takes a
zero argument callable that returns it (``customOpCb``), so the caller does not
scan the page for ``customSqlOp_*`` methods on every call that has no bag.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.core.gnrstring import templateReplace


class SelectionProxy:
    """Selection proxy of a single table."""

    def __init__(self, tblobj: Any) -> None:
        self.tblobj = tblobj

    @property
    def db(self) -> Any:
        """The database of the proxied table."""
        return self.tblobj.db

    # ------------------------------------------------------------------
    #  Columns
    # ------------------------------------------------------------------

    def columnsFromStruct(self, viewbag: Bag,
                          columns: Optional[list] = None) -> Optional[str]:
        """Extract column names from a view structure :class:`Bag`.

        Args:
            viewbag: The view structure :class:`Bag`.
            columns: Accumulator list, used by the recursion.

        Returns:
            A comma separated column string, or ``None`` when *viewbag* is
            empty.
        """
        if columns is None:
            columns = []
        if not viewbag:
            return

        for node in viewbag:
            fld = node.getAttr('field')
            if node.getAttr('formula'):
                continue
            if fld:
                if not (fld[0] in ('$', '@')):
                    fld = '$' + fld
                columns.append(fld)
            if isinstance(node.value, Bag):
                self.columnsFromStruct(node.value, columns)
        return ','.join(columns)

    def selectionColumns(self, columns: Union[str, Bag],
                         expressions: Optional[dict] = None) -> tuple[str, dict]:
        """Process and normalize a column specification.

        Handles Bag based column specs, bracket notation for multi table
        columns, expression substitution and the automatic protection and
        invalid columns.

        A bracket group ``tbl[a,b]`` prefixes every column up to the closing
        bracket and stops there.  The handler version of this code tests the
        closing bracket after stripping it, so the group never ends and every
        following column keeps the prefix; here the group end is remembered
        before the bracket is removed.

        Args:
            columns: Raw column specification.
            expressions: Already resolved expression dictionary, ``{name: sql}``.
                The page resolves it from its own ``expr_*`` method.

        Returns:
            A tuple ``(columns_string, external_queries_dict)``.
        """
        tblobj = self.tblobj
        external_queries = {}
        if isinstance(columns, Bag):
            columns = self.columnsFromStruct(columns)
        if not columns:
            columns = tblobj.attributes.get('baseview') or '*'
        if '[' in columns or ':' in columns:
            columns = columns.replace('\n', '').replace('\t', '')
            maintable = []
            colaux = columns.split(',')
            columns = []
            for col in colaux:
                if ':' in col:
                    external_relkey, external_field = col.split(':')
                    external_queries.setdefault(external_relkey, []).append(external_field)
                    continue
                if '[' in col:
                    tbl, col = col.split('[')
                    maintable = [tbl]
                group_end = col.endswith(']')
                if group_end:
                    col = col[:-1]
                columns.append('.'.join(maintable + [col.rstrip(']')]))
                if group_end:
                    maintable = []
            columns = ','.join(columns)
        if expressions:
            expr_dict = dict([(k, '%s AS %s' % (v, k)) for k, v in list(expressions.items())])
            columns = templateReplace(columns, expr_dict, safeMode=True)
        if tblobj.hasProtectionColumns():
            columns = '%s,$__is_protected_row AS _is_readonly_row,$__protecting_reasons' % columns

        if tblobj.hasInvalidCheck():
            columns = '%s,$__is_invalid_row AS _is_invalid_row,$__invalid_reasons' % columns

        return columns, external_queries

    # ------------------------------------------------------------------
    #  Where bag and join conditions
    # ------------------------------------------------------------------

    def decodeWhereBag(self, where: Any, kwargs: dict[str, Any],
                       customOpCbDict: Optional[dict] = None) -> tuple[str, dict[str, Any]]:
        """Decode a :class:`Bag` encoded WHERE clause into SQL.

        Args:
            where: A :class:`Bag` encoding the WHERE conditions.
            kwargs: Mutable dict — ``currentFilter`` is popped if present, and
                ``sqlWhereFromBag`` may add SQL parameters to it.
            customOpCbDict: Custom operator callbacks, collected by the caller
                from its own ``customSqlOp_*`` methods.

        Returns:
            A ``(sql_where_string, updated_kwargs)`` tuple.
        """
        currentFilter = kwargs.pop('currentFilter', None)
        if currentFilter:
            new_where = Bag()
            new_where.setItem('filter', currentFilter)
            new_where.setItem('where', where, jc='and')
            where = new_where
        return self.tblobj.sqlWhereFromBag(where, kwargs, customOpCbDict=customOpCbDict)

    def decodeJoinConditions(self, joinConditions: Any,
                             kwargs: dict) -> Union[dict, Any]:
        """Decode join conditions from a :class:`Bag` to a dict.

        Args:
            joinConditions: A :class:`Bag` of join conditions, or an already
                decoded dict, returned as is.
            kwargs: Query parameters, modified in place by ``sqlWhereFromBag``.

        Returns:
            A dict mapping relation names to condition/one_one pairs.
        """
        if not isinstance(joinConditions, Bag):
            return joinConditions
        result = dict()
        for jc in list(joinConditions.values()):
            sqlcondition, kwargs = self.tblobj.sqlWhereFromBag(jc['condition'], kwargs)
            result[jc['relation']] = dict(condition=sqlcondition, one_one=jc['one_one'])
        return result

    def recordCount(self, where: Any = '', condition: Optional[str] = None,
                    distinct: bool = False, columns: str = '',
                    relationDict: Optional[dict] = None,
                    sqlparams: Optional[dict] = None,
                    customOpCb: Callable = dict, **kwargs: Any) -> int:
        """Count the records matching *where* and *condition*.

        Args:
            where: SQL WHERE clause or a :class:`Bag` to decode.
            condition: Extra condition ANDed to *where*.
            distinct: Use ``SELECT DISTINCT``.
            columns: Column expression for the query.
            relationDict: Symbolic relation names.
            sqlparams: Additional SQL parameters.
            customOpCb: Called, only when *where* is a :class:`Bag`, to get the
                custom operator callbacks of the where bag.  The default
                answers with no callback.

        Returns:
            The record count.
        """
        if isinstance(where, Bag):
            where, kwargs = self.decodeWhereBag(where, kwargs,
                                                customOpCbDict=customOpCb())
        if condition:
            where = '( %s ) AND ( %s )' % (where, condition) if where else condition
        return self.tblobj.query(columns=columns, distinct=distinct, where=where,
                                 relationDict=relationDict, sqlparams=sqlparams,
                                 **kwargs).count()

    # ------------------------------------------------------------------
    #  Query serialization
    # ------------------------------------------------------------------

    def rpcQuery(self, distinct: Optional[bool] = None,
                 columns: Optional[str] = None,
                 where: Optional[Bag] = None,
                 condition: Optional[str] = None,
                 order_by: Optional[str] = None,
                 limit: Optional[int] = None,
                 group_by: Optional[str] = None,
                 having: Optional[str] = None,
                 excludeLogicalDeleted: bool = True,
                 excludeDraft: bool = True,
                 customOpCbDict: Optional[dict] = None, **kwargs: Any) -> Bag:
        """Serialize the query parameters so the client can store the query.

        The parameters are split into the ones the WHERE bag names, the ones
        the condition names, the ones read from the database environment and
        the rest, and the generated SQL text is added.

        Args:
            where: The WHERE conditions, a :class:`Bag`.
            customOpCbDict: Custom operator callbacks for the where bag.

        Returns:
            A :class:`Bag` with every query parameter and the SQL text.
        """
        query_pars = dict(distinct=distinct, condition=condition,
                          columns=columns,
                          order_by=order_by, limit=limit,
                          group_by=group_by,
                          having=having,
                          excludeLogicalDeleted=excludeLogicalDeleted,
                          excludeDraft=excludeDraft, **kwargs)
        decoded_query_pars = dict(query_pars)
        where_pars = {}
        condition_pars = {}

        def findPars(n: Any) -> None:
            if n.attr.get('parname'):
                where_pars[n.attr.get('parname')] = n.getValue()

        textwhere, decoded_query_pars = self.decodeWhereBag(
            where, decoded_query_pars, customOpCbDict=customOpCbDict)
        where.walk(findPars)
        if condition:
            textwhere = '({}) AND ({})'.format(textwhere, condition)

        q = self.tblobj.query(where=textwhere, **decoded_query_pars)
        currenv = dict(self.db.currentEnv)
        sqltext = q.sqltext
        allpars = re.findall(r':(\S\w*)(\W|$)', q.sqltext)
        env_pars = {k[4:]: currenv[k[4:]] for k, chunk in allpars if k[4:] in currenv}
        if condition:
            for par, chunk in re.findall(r':(\S\w*)(\W|$)', condition):
                condition_pars[par] = query_pars[par]
        if not where_pars:
            for par, chunk in allpars:
                if par in decoded_query_pars and par not in env_pars and par not in condition_pars:
                    where_pars[par] = decoded_query_pars[par]
        other_pars = {}
        for k, v in query_pars.items():
            if k not in where_pars and \
                    k not in condition_pars and \
                    k not in env_pars:
                other_pars[k] = v
        rpcquery = Bag()
        rpcquery['columns'] = columns
        rpcquery['query_where'] = where
        rpcquery['query_condition'] = condition
        rpcquery['query_pars'] = Bag(query_pars)
        rpcquery['where_pars'] = Bag(where_pars)
        rpcquery['condition_pars'] = Bag(condition_pars)
        rpcquery['env_pars'] = Bag(env_pars)
        rpcquery['other_pars'] = Bag(other_pars)
        rpcquery['where_as_html'] = self.db.whereTranslator.toHtml(self.tblobj, where)
        rpcquery['sqlquery'] = sqltext
        return rpcquery

    # ------------------------------------------------------------------
    #  External stores
    # ------------------------------------------------------------------

    def externalQueries(self, selection: Any = None,
                        external_queries: Optional[dict] = None) -> None:
        """Query the external stores named in the columns and merge the results.

        Args:
            selection: The main selection, updated in place.
            external_queries: Dict mapping relation keys to field lists.
        """
        storedict = dict()
        for r in selection.data:
            storedict.setdefault(r['_external_store'], []).append(r)
        for store, subsel in storedict.items():
            with self.db.tempEnv(storename=store):
                for k, v in external_queries.items():
                    ksplitted = k.split('.')
                    tblobj = self.db.table('.'.join(ksplitted[:2]))
                    relkey = ksplitted[-1]
                    extfkeyname = '%s_fkey' % k.replace('.', '_')
                    fkeys = [r[extfkeyname] for r in selection.data]
                    columns = ','.join(v + ['$%s AS %s' % (relkey, extfkeyname)])
                    resdict = tblobj.query(columns=columns, where='$%s IN :fkeys' % relkey,
                                           fkeys=fkeys, addPkeyColumn=False).fetchAsDict(key=extfkeyname)
                    for r in subsel:
                        if r[extfkeyname] in resdict:
                            r.update(resdict[r[extfkeyname]])

    # ------------------------------------------------------------------
    #  Saved queries and views
    # ------------------------------------------------------------------

    def loadSavedQuery(self, savedQuery: str) -> Any:
        """Load a saved query of this table from ``adm.userobject``.

        The user is not a parameter: ``adm.userobject`` resolves it from the
        database environment, as it does for every other caller.

        Args:
            savedQuery: Identifier or code of the saved query.

        Returns:
            The stored data — a :class:`Bag` with ``where``, ``queryLimit``,
            ``currViewPath`` and ``customOrderBy``.
        """
        userobject_tbl = self.db.table('adm.userobject')
        return userobject_tbl.loadUserObject(userObjectIdOrCode=savedQuery, objtype='query',
                                             tbl=self.tblobj.fullname)[0]

    def loadSavedView(self, savedView: str) -> Any:
        """Load a saved view of this table from ``adm.userobject``.

        Args:
            savedView: Identifier or code of the saved view.

        Returns:
            The stored data — the columns of the view.
        """
        userobject_tbl = self.db.table('adm.userobject')
        return userobject_tbl.loadUserObject(userObjectIdOrCode=savedView, objtype='view',
                                             tbl=self.tblobj.fullname)[0]

    # ------------------------------------------------------------------
    #  Default query construction
    # ------------------------------------------------------------------

    def selectionWhere(self, where: Any = None, condition: Optional[str] = None,
                       pkeys: Optional[Any] = None,
                       linkedSelectionKw: Optional[dict] = None,
                       customOpCb: Callable = dict,
                       kwargs: Optional[dict] = None) -> tuple[Any, dict]:
        """Build the WHERE clause of a default selection.

        Applies, in this order, the linked selection, the explicit pkeys and the
        :class:`Bag` encoded where, then ANDs *condition* unless *pkeys* is set.

        Args:
            where: SQL WHERE clause or a :class:`Bag`.
            condition: Extra condition.
            pkeys: Explicit pkey list, or a comma separated string.
            linkedSelectionKw: The ``where``/``linkedPkeys`` pair of a linked
                selection, as the page resolves it.
            customOpCb: Called, only when *where* is a :class:`Bag` and neither
                *linkedSelectionKw* nor *pkeys* replaces it, to get the custom
                operator callbacks of the where bag.  The default answers with
                no callback.
            kwargs: Query parameters, updated and returned.

        Returns:
            A ``(where, kwargs)`` tuple.
        """
        tblobj = self.tblobj
        kwargs = kwargs if kwargs is not None else {}
        if linkedSelectionKw:
            where = linkedSelectionKw['where']
            kwargs['_masterPkeys'] = linkedSelectionKw['linkedPkeys']
        elif pkeys:
            if isinstance(pkeys, str):
                pkeys = pkeys.strip(',').split(',')
            # an empty pkeys list cannot reach this point: a falsy pkeys never
            # enters the branch and a truthy string always yields at least one
            # element (bugs.md D4)
            if len(pkeys) == 1:
                where = 't0.%s =:_pkey' % tblobj.pkey
                kwargs['_pkey'] = pkeys[0]
            else:
                where = 't0.%s in :pkeys' % tblobj.pkey
                kwargs['pkeys'] = pkeys
        elif isinstance(where, Bag):
            kwargs.pop('where_attr', None)
            where, kwargs = self.decodeWhereBag(where, kwargs, customOpCbDict=customOpCb())
        if condition and not pkeys:
            where = ' ( %s ) AND ( %s ) ' % (where, condition) if where else condition
        return where, kwargs

    def filteringWhere(self, where: Any, filteringPkeys: list,
                       kwargs: dict) -> tuple[Any, dict]:
        """AND the filtering pkeys into the WHERE clause.

        Args:
            where: The WHERE clause built so far.
            filteringPkeys: The pkeys, already resolved to a list by the caller.
            kwargs: Query parameters, updated and returned.

        Returns:
            A ``(where, kwargs)`` tuple.
        """
        tblobj = self.tblobj
        if len(filteringPkeys) == 0:
            filteringWhere = 't0.%s IS NULL' % tblobj.pkey
        elif len(filteringPkeys) == 1:
            filteringWhere = 't0.%s =:_filteringPkey' % tblobj.pkey
            kwargs['_filteringPkey'] = filteringPkeys[0]
        else:
            filteringWhere = 't0.%s in :_filteringPkeys' % tblobj.pkey
            kwargs['_filteringPkeys'] = filteringPkeys
        where = filteringWhere if not where else ' ( %s ) AND ( %s ) ' % (filteringWhere, where)
        return where, kwargs

    def countRows(self, where: Any = None, order_by: Optional[str] = None,
                  limit: Optional[int] = None, offset: Optional[int] = None,
                  having: Optional[str] = None,
                  relationDict: Optional[dict] = None,
                  sqlparams: Optional[dict] = None,
                  locale: Optional[str] = None,
                  excludeLogicalDeleted: Any = True,
                  excludeDraft: bool = True, **kwargs: Any) -> int:
        """Count the distinct pkeys matching the query.

        *limit*, *offset*, *order_by* and *having* are applied to the count
        query, so a limited query counts at most *limit* rows.

        Returns:
            The number of rows.
        """
        pkey = self.tblobj.pkey
        query = self.tblobj.query(columns='$%s' % pkey, where=where,
                                  distinct=True,
                                  order_by=order_by, limit=limit, offset=offset,
                                  group_by='$%s' % pkey, having=having,
                                  relationDict=relationDict, sqlparams=sqlparams,
                                  locale=locale,
                                  excludeLogicalDeleted=excludeLogicalDeleted,
                                  excludeDraft=excludeDraft, **kwargs)
        return len(query.fetch())

    def buildSelection(self, columns: Optional[str] = None,
                       distinct: Optional[bool] = None,
                       where: Any = None, order_by: Optional[str] = None,
                       limit: Optional[int] = None, offset: Optional[int] = None,
                       group_by: Optional[str] = None, having: Optional[str] = None,
                       relationDict: Optional[dict] = None,
                       sqlparams: Optional[dict] = None,
                       locale: Optional[str] = None,
                       excludeLogicalDeleted: Any = True,
                       excludeDraft: bool = True,
                       sortedBy: Optional[str] = None,
                       _aggregateRows: bool = True,
                       queryCb: Optional[Callable] = None, **kwargs: Any) -> Any:
        """Build the query and return its selection.

        Args:
            queryCb: Called with the query before it is executed, so the caller
                can apply the join conditions of a SQL context.

        Returns:
            The selection.
        """
        query = self.tblobj.query(columns=columns, distinct=distinct, where=where,
                                  order_by=order_by, limit=limit, offset=offset,
                                  group_by=group_by, having=having,
                                  relationDict=relationDict, sqlparams=sqlparams,
                                  locale=locale,
                                  excludeLogicalDeleted=excludeLogicalDeleted,
                                  excludeDraft=excludeDraft, **kwargs)
        if queryCb:
            queryCb(query)
        return query.selection(sortedBy=sortedBy, _aggregateRows=_aggregateRows)

    def queryModeSelection(self, selection: Any = None, queryMode: Optional[str] = None,
                           frozenPkeys: Optional[Any] = None,
                           columns: Optional[str] = None,
                           distinct: Optional[bool] = None,
                           order_by: Optional[str] = None,
                           limit: Optional[int] = None, offset: Optional[int] = None,
                           group_by: Optional[str] = None, having: Optional[str] = None,
                           relationDict: Optional[dict] = None,
                           sqlparams: Optional[dict] = None,
                           locale: Optional[str] = None,
                           excludeLogicalDeleted: Any = True,
                           excludeDraft: bool = True,
                           sortedBy: Optional[str] = None,
                           _aggregateRows: bool = True, **kwargs: Any) -> Any:
        """Combine *selection* with the pkeys of a frozen selection.

        Args:
            selection: The selection just built.
            queryMode: ``'U'`` union, ``'I'`` intersection, ``'D'`` difference.
            frozenPkeys: Pkeys of the frozen selection, read by the caller.

        Returns:
            The selection of the combined pkeys.
        """
        _qmpkeys = set(frozenPkeys)
        currentpkeys = set(selection.output('pkeylist'))
        if queryMode == 'U':
            rpkeys = _qmpkeys.union(currentpkeys)
        elif queryMode == 'I':
            rpkeys = _qmpkeys.intersection(currentpkeys)
        else:
            rpkeys = _qmpkeys.difference(currentpkeys)
        return self.buildSelection(columns=columns, distinct=distinct,
                                   where='${} IN :_rpkeys'.format(self.tblobj.pkey),
                                   _rpkeys=rpkeys,
                                   order_by=order_by, limit=limit, offset=offset,
                                   group_by=group_by, having=having,
                                   relationDict=relationDict, sqlparams=sqlparams,
                                   locale=locale,
                                   excludeLogicalDeleted=excludeLogicalDeleted,
                                   excludeDraft=excludeDraft, sortedBy=sortedBy,
                                   _aggregateRows=_aggregateRows, **kwargs)
