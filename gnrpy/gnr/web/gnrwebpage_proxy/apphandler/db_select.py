# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler.db_select : FilteringSelect (dbSelect) operations
# Copyright (c)     : 2004 - 2007 Softwell sas - Milano
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

"""FilteringSelect (dbSelect) mixin.

Provides :class:`DbSelectMixin` — the server-side implementation of
the ``dbSelect`` widget, which performs incremental search queries
against database tables for autocomplete/dropdown functionality.
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from gnr.core import gnrlist
from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrdecorator import public_method

ESCAPE_SPECIAL = re.compile(r'[\[\\\^\$\.\|\?\*\+\(\)\]\{\}]')
"""Regex to escape special characters in user search input before
building regex-based SQL conditions."""


class DbSelectMixin:
    """Mixin for FilteringSelect (dbSelect) operations.

    Implements the progressive search strategy used by the ``dbSelect``
    widget: first try ``startswith``, then ``contains``, then regex
    word-boundary matching, then ``ILIKE`` fallback.
    """

    @public_method
    def dbSelect(self, dbtable: Optional[str] = None, columns: Optional[str] = None,
                 auxColumns: Optional[str] = None, hiddenColumns: Optional[str] = None,
                 rowcaption: Optional[str] = None,
                 _id: Optional[str] = None, _querystring: str = '',
                 querystring: Optional[str] = None, ignoreCase: bool = True,
                 exclude: Optional[str] = None, excludeDraft: bool = True,
                 condition: Optional[str] = None, limit: Optional[int] = None,
                 alternatePkey: Optional[str] = None, order_by: Optional[str] = None,
                 selectmethod: Optional[str] = None,
                 applymethod: Optional[str] = None, notnull: Optional[bool] = None,
                 weakCondition: bool = False, _storename: Optional[str] = None,
                 preferred: Optional[str] = None,
                 emptyLabel: Optional[str] = None, emptyLabel_first: Optional[bool] = None,
                 emptyLabel_class: Optional[str] = None,
                 invalidItemCondition: Optional[str] = None,
                 **kwargs: Any) -> tuple[Bag, dict]:
        """Perform an incremental database search for the dbSelect widget.

        This is the main entry point for the FilteringSelect widget.
        When ``_id`` is provided, it fetches a specific record by key.
        When ``querystring`` is provided, it performs a progressive
        search with fallback strategies.

        Args:
            dbtable: Fully qualified table name (``"pkg.table"``).
            columns: Columns to search on.
            auxColumns: Additional columns shown in the dropdown.
            hiddenColumns: Columns fetched but not displayed.
            rowcaption: Custom row caption format.
            _id: When set, fetch the record with this primary key.
            _querystring: Search text typed by the user.
            querystring: Alternative search text parameter.
            ignoreCase: Case-insensitive search.
            exclude: Comma-separated list of pkeys to exclude.
            excludeDraft: Exclude draft records.
            condition: Additional SQL WHERE condition.
            limit: Maximum number of results.
            alternatePkey: Use this field instead of the primary key.
            order_by: SQL ORDER BY clause.
            selectmethod: Custom RPC method name for the query.
            applymethod: Post-processing method name.
            notnull: When ``True`` no empty-label row is added.
            weakCondition: Apply *condition* only if it yields results.
            _storename: Database store to use.
            preferred: SQL expression marking preferred rows.
            emptyLabel: Label for the null/empty option.
            emptyLabel_first: Place the empty option first.
            emptyLabel_class: CSS class for the empty option.
            invalidItemCondition: SQL expression to flag invalid items.

        Returns:
            A tuple ``(result_bag, attributes_dict)``.
        """
        if _storename:
            self.db.use_store(_storename)
        elif _storename is False:
            self.db.use_store()
        resultClass = ''
        if selectmethod or not condition:
            weakCondition = False
        t0 = time.time()
        querystring = _querystring or querystring  # SMELL: dual parameter for same purpose
        if limit is None:
            limit = self.gnrapp.config.get('dbselect?limit', 10)
        limit = int(limit)
        result = Bag()
        tblobj = self.db.table(dbtable)
        captioncolumns = tblobj.rowcaptionDecode(rowcaption)[0]
        querycolumns = tblobj.getQueryFields(columns, captioncolumns)
        showcolumns = gnrlist.merge(captioncolumns, tblobj.columnsFromString(auxColumns))
        resultcolumns = gnrlist.merge(showcolumns, captioncolumns, tblobj.columnsFromString(hiddenColumns))
        if alternatePkey and alternatePkey not in resultcolumns:
            resultcolumns.append("$%s" % alternatePkey if not alternatePkey.startswith('$') else alternatePkey)
        selection = None
        identifier = 'pkey'
        resultAttrs = {}
        errors = []
        if _id:
            fullwhere = None
            if alternatePkey:
                where = '$%s = :id' % alternatePkey
            else:
                where = '$%s = :id' % identifier

            fullwhere = '( %s ) AND ( %s ) ' % (where, condition) if (condition and weakCondition is not True) else where
            whereargs = {}
            whereargs.update(kwargs)
            selection = tblobj.query(columns=','.join(resultcolumns),
                                     where=fullwhere, excludeLogicalDeleted=False,
                                     excludeDraft=excludeDraft,
                                     limit=1, id=_id, **kwargs).selection()
            if condition and not selection:
                selection = tblobj.query(columns=','.join(resultcolumns),
                                     where=where, excludeLogicalDeleted=False,
                                     excludeDraft=excludeDraft,
                                     limit=1, id=_id, **kwargs).selection()
                errors.append('current value does not fit condition')

        elif querystring:
            querystring = querystring.strip('*')
            if querystring.isdigit():
                querystring = "%s%s" % ('%', querystring)
            if selectmethod:
                selectHandler = self.page.getPublicMethod('rpc', selectmethod)
            else:
                selectHandler = self.dbSelect_default
            order_list = []
            preferred = tblobj.attributes.get('preferred') if preferred is None else preferred
            weakCondition = weakCondition or tblobj.attributes.get('weakCondition')
            if preferred:
                order_list.append('( %s ) desc' % preferred)
                resultcolumns.append("""(CASE WHEN %s IS NOT TRUE THEN 'not_preferred_row' ELSE '' END) AS _customclasses_preferred""" % preferred)
            if invalidItemCondition:
                resultcolumns.append("""(%s IS TRUE) AS _is_invalid_item""" % invalidItemCondition)
            order_by = order_by or tblobj.attributes.get('order_by') or showcolumns[0]
            order_list.append(order_by if order_by[0] in ('$', '@') else '$%s' % order_by)
            order_by = ', '.join(order_list)
            cond = '(%s) AND (%s)' % (condition or 'TRUE', weakCondition) if isinstance(weakCondition, str) else condition
            selection = selectHandler(tblobj=tblobj, querycolumns=querycolumns, querystring=querystring,
                                      resultcolumns=resultcolumns, condition=cond, exclude=exclude,
                                      limit=limit, order_by=order_by,
                                      identifier=identifier, ignoreCase=ignoreCase, excludeDraft=excludeDraft, **kwargs)
            if not selection and weakCondition:
                resultClass = 'relaxedCondition'
                selection = selectHandler(tblobj=tblobj, querycolumns=querycolumns, querystring=querystring,
                                          resultcolumns=resultcolumns, exclude=exclude,
                                          limit=limit, order_by=order_by,
                                          condition=None if weakCondition is True else condition,
                                          identifier=identifier, ignoreCase=ignoreCase, excludeDraft=excludeDraft, **kwargs)
        applyresult = None
        if applymethod:
            applyresult = self.page.getPublicMethod('rpc', applymethod)(selection, **kwargs)
        if selection:
            showcols = [tblobj.colToAs(c.lstrip('$')) for c in showcolumns]
            result = selection.output('selection', locale=self.page.locale, caption=rowcaption or True)
            colHeaders = [selection.colAttrs[k].get('name_short') or selection.colAttrs[k]['label'] for k in showcols]
            colHeaders = [self.page._(c) for c in colHeaders]
            resultAttrs = {'columns': ','.join(showcols), 'headers': ','.join(colHeaders)}
            if applyresult:
                resultAttrs.update(applyresult)
            if not notnull and not _id:
                emptyLabel = emptyLabel or ''
                _position = '<' if emptyLabel_first else None
                result.setItem('null_row', None, caption=emptyLabel, _pkey=None,
                               _customClasses=emptyLabel_class, _position=_position)

        resultAttrs['resultClass'] = resultClass
        resultAttrs['dbselect_time'] = time.time() - t0
        if errors:
            resultAttrs['errors'] = ','.join(errors)
        return (result, resultAttrs)

    @public_method
    def dbSelect_selection(self, tblobj: Any, querystring: str,
                           columns: Optional[str] = None,
                           auxColumns: Optional[str] = None,
                           **kwargs: Any) -> Any:
        """Perform a dbSelect query using pre-defined column sets.

        A simplified entry point that resolves columns and delegates to
        :meth:`dbSelect_default`.

        Args:
            tblobj: The table object.
            querystring: Search text.
            columns: Search columns.
            auxColumns: Additional display columns.

        Returns:
            A selection result.
        """
        querycolumns = tblobj.getQueryFields(columns)
        showcolumns = gnrlist.merge(querycolumns, tblobj.columnsFromString(auxColumns))
        captioncolumns = tblobj.rowcaptionDecode()[0]
        resultcolumns = gnrlist.merge(showcolumns, captioncolumns)
        querystring = querystring or ''
        querystring = querystring.strip('*')
        return self.dbSelect_default(tblobj, querycolumns, querystring, resultcolumns, **kwargs)

    @public_method
    def tableAnalyzeStore(self, table: Optional[str] = None,
                          where: Optional[str] = None,
                          group_by: Optional[list] = None,
                          **kwargs: Any) -> tuple[Any, dict]:
        """Analyze table data with aggregation (totalize).

        Args:
            table: Fully qualified table name.
            where: SQL WHERE clause.
            group_by: List of grouping specifications.

        Returns:
            A tuple ``(store_bag, timing_dict)``.

        Note:
            SMELL: The ``group_by`` parameter is used both as a column
            list (filtering out callables) and as a grouping spec passed
            to ``selection.totalize()`` — overloaded semantics.
        """
        t0 = time.time()
        page = self.page
        tblobj = page.db.table(table)
        columns = [x for x in group_by if not callable(x)]
        selection = tblobj.query(where=where, columns=','.join(columns), **kwargs).selection()
        explorer_id = page.getUuid()
        freeze_path = page.site.getStaticPath('page:explorers', explorer_id)
        t1 = time.time()
        totalizeBag = selection.totalize(group_by=group_by, collectIdx=False, keep=['pkey'])
        t2 = time.time()
        store = page.lazyBag(totalizeBag, name=explorer_id, location='page:explorer')()
        t3 = time.time()
        return store, dict(query_time=t1 - t0, totalize_time=t2 - t1, resolver_load_time=t3 - t2)

    def dbSelect_default(self, tblobj: Any, querycolumns: list[str],
                         querystring: str, resultcolumns: list[str],
                         condition: Optional[str] = None,
                         exclude: Optional[str] = None,
                         limit: Optional[int] = None,
                         order_by: Optional[str] = None,
                         identifier: Optional[str] = None,
                         ignoreCase: Optional[bool] = None,
                         **kwargs: Any) -> Any:
        """Default implementation of the dbSelect search strategy.

        Tries progressively broader searches:

        1. ``contains`` on the first query column
        2. ``startswith`` if too many results
        3. Regex word-boundary matching on all columns
        4. ``ILIKE`` fallback on all columns

        Args:
            tblobj: The table object.
            querycolumns: Columns to search on.
            querystring: Search text.
            resultcolumns: Columns to return.
            condition: Additional SQL condition.
            exclude: Comma-separated pkeys to exclude.
            limit: Maximum results.
            order_by: SQL ORDER BY.
            identifier: Key column name.
            ignoreCase: Case-insensitive search.

        Returns:
            A selection result.
        """
        def getSelection(where: Optional[str], **searchargs: Any) -> Any:
            whereargs = {}
            whereargs.update(kwargs)
            whereargs.update(searchargs)
            if where and condition:
                where = '( %s ) AND ( %s ) ' % (where, condition)
            else:
                where = where or condition
            return tblobj.query(where=where, columns=','.join(resultcolumns), limit=limit,
                                order_by=order_by or querycolumns[0], exclude_list=exclude_list,
                                **whereargs).selection(_aggregateRows=True)

        exclude_list = None
        if exclude:
            if isinstance(exclude, str):
                exclude_list = [t.strip() for t in exclude.split(',')]
            else:
                exclude_list = [t for t in exclude if t]  # None values break the query
            if exclude_list:
                exclude_cond = 'NOT ($pkey IN :exclude_list )'
                if condition:
                    condition = '%s AND %s' % (condition, exclude_cond)
                else:
                    condition = exclude_cond

        kwargs.pop('where', None)
        srclist = querystring.split()

        if not srclist:
            return getSelection(None)
        searchval = '%s%%' % ('%% '.join(srclist))
        sqlArgs = dict()
        cond = tblobj.opTranslate(querycolumns[0], 'contains', searchval, sqlArgs=sqlArgs)
        result = getSelection(cond, **sqlArgs)
        if len(result) >= (limit or 50):
            cond = tblobj.opTranslate(querycolumns[0], 'startswith', searchval, sqlArgs=sqlArgs)
            result = getSelection(cond, **sqlArgs)

        columns_concat = " || ' ' || ".join(["CAST ( COALESCE(%s,'') AS TEXT ) " % c for c in querycolumns])
        if len(result) == 0:
            regsrc = [x for x in re.split(" ", ESCAPE_SPECIAL.sub('', querystring)) if x]
            if regsrc:
                whereargs = dict([('w%i' % i, '(^|\\W)%s' % w.strip()) for i, w in enumerate(regsrc)])
                where = " AND ".join(["(%s)  ~* :w%i" % (columns_concat, i) for i, w in enumerate(regsrc)])
                result = getSelection(where, **whereargs)

        if len(result) == 0:
            whereargs = dict([('w%i' % i, '%%%s%%' % w.strip()) for i, w in enumerate(srclist)])
            where = " AND ".join(["(%s)  ILIKE :w%i" % (columns_concat, i) for i, w in enumerate(srclist)])
            result = getSelection(where, **whereargs)

        return result

    @public_method
    def getValuesString(self, table: Optional[str] = None,
                        caption_field: Optional[str] = None,
                        alt_pkey_field: Optional[str] = None,
                        **kwargs: Any) -> str:
        """Return a comma-separated ``key:caption`` string for table rows.

        Args:
            table: Fully qualified table name.
            caption_field: Field to use as caption.
            alt_pkey_field: Alternative primary key field.

        Returns:
            A string like ``"key1:caption1,key2:caption2,..."``.
        """
        tblobj = self.db.table(table)
        pkey = alt_pkey_field or tblobj.pkey
        caption_field = caption_field or tblobj.attributes.get('caption_field') or tblobj.pkey
        f = tblobj.query(columns='$%s,$%s' % (pkey, caption_field), **kwargs).fetch()
        return ','.join(['%s:%s' % (r[pkey], (r[caption_field] or '').replace(',', ' ')) for r in f])

    @public_method
    def getMultiFetch(self, queries: Optional[Bag] = None) -> Bag:
        """Execute multiple queries in batch.

        Args:
            queries: A :class:`Bag` where each node specifies a query
                with ``table``, ``columns`` and additional parameters
                as attributes.

        Returns:
            A :class:`Bag` with one key per query, each containing the
            fetched results.
        """
        result = Bag()
        for query in queries:
            columns = query.attr.pop('columns', '*')
            table = query.attr.pop('table')
            tblobj = self.db.table(table)
            columns = ','.join(tblobj.columnsFromString(columns))
            qattr = dict(query.attr)
            dbenv_kw = dictExtract(qattr, 'dbenv_', True)
            with self.db.tempEnv(**dbenv_kw):
                result[query.label] = tblobj.query(columns=columns, **qattr).fetchAsBag('pkey')
        return result
