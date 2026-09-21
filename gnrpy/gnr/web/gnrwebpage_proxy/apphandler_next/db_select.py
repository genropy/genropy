# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.db_select : FilteringSelect (dbSelect) operations
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

"""FilteringSelect (dbSelect) mixin — the copy that receives new work.

Provides :class:`DbSelectMixin` — the server-side implementation of
the ``dbSelect`` widget, which performs incremental search queries
against database tables for autocomplete/dropdown functionality.

The module of the same name under ``gnr.web.gnrwebpage_proxy.apphandler`` is
frozen and is never imported from here.  The method bodies are the ones of
that module; what differs is a block that needs only the table and the
database, replaced by one call on the table proxy ``tblobj.dbSelectHandler()``
(:class:`gnr.app.gnrsqltable_proxy.db_select.DbSelectHandler`), and a recorded
defect fix, marked in place with its ``bugs_dbselect.md`` number.

``ESCAPE_SPECIAL`` is on the proxy, where the regex stage of the search is;
nothing outside these two modules ever imported it.  ``dbSelect_selection`` has
no caller anywhere in the tree and is not part of the copy.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrdecorator import public_method

__all__ = ['DbSelectMixin']


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
        dbSelectHandler = tblobj.dbSelectHandler()
        querycolumns = dbSelectHandler.composeQueryColumns(columns=columns, rowcaption=rowcaption)
        showcolumns = dbSelectHandler.composeShowColumns(rowcaption=rowcaption, auxColumns=auxColumns)
        resultcolumns = dbSelectHandler.composeResultColumns(rowcaption=rowcaption, auxColumns=auxColumns,
                                                             hiddenColumns=hiddenColumns,
                                                             alternatePkey=alternatePkey)
        selection = None
        identifier = 'pkey'
        resultAttrs = {}
        errors = []
        if _id:
            selection, errors = dbSelectHandler.selectRecordById(_id, resultcolumns, condition=condition,
                                                           weakCondition=weakCondition,
                                                           alternatePkey=alternatePkey,
                                                           excludeDraft=excludeDraft, **kwargs)
        elif querystring:
            querystring = querystring.strip('*')
            if querystring.isdigit():
                querystring = "%s%s" % ('%', querystring)
            if selectmethod:
                selectHandler = self.page.getPublicMethod('rpc', selectmethod)
            else:
                selectHandler = self.dbSelect_default
            preferred = dbSelectHandler.resolvePreferredExpression(preferred)
            weakCondition = dbSelectHandler.resolveWeakCondition(weakCondition)
            resultcolumns = dbSelectHandler.addSearchFlagColumns(resultcolumns, preferred=preferred,
                                                                invalidItemCondition=invalidItemCondition)
            order_by = dbSelectHandler.composeSearchOrderBy(order_by, showcolumns, preferred=preferred)
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
            result = selection.output('selection', locale=self.page.locale, caption=rowcaption or True)
            showcols, colHeaders = dbSelectHandler.composeColumnHeaders(selection, showcolumns, self.page._)
            resultAttrs = {'columns': showcols, 'headers': colHeaders}
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
        selection = page.db.table(table).dbSelectHandler().selectRecordsToTotalize(where=where, group_by=group_by,
                                                                            **kwargs)
        explorer_id = page.getUuid()
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

        Note:
            The signature is a contract: it is the default value of the select
            handler and a page ``selectmethod`` is called with exactly these
            keywords.  *identifier* and *ignoreCase* are part of it and this
            implementation reads neither.

            bugs_dbselect.md DS5: the frozen handler shares one ``sqlArgs``
            dict between the ``contains`` and the ``startswith`` stages, so the
            second one carries the bind parameter of the first.
        """
        return tblobj.dbSelectHandler().searchRecords(querycolumns=querycolumns, querystring=querystring,
                                                        resultcolumns=resultcolumns, condition=condition,
                                                        exclude=exclude, limit=limit, order_by=order_by,
                                                        **kwargs)

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
        return self.db.table(table).dbSelectHandler().composeValuesString(caption_field=caption_field,
                                                                   alt_pkey_field=alt_pkey_field,
                                                                   **kwargs)

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

        Note:
            bugs_dbselect.md DS6: the frozen handler pops ``columns`` and
            ``table`` off the caller's Bag node, so the caller gets its own Bag
            back stripped; here the copy is taken first.

            bugs_dbselect.md DS7: the documented ``columns`` default ``'*'``
            went through ``columnsFromString``, which turns it into ``$*`` and
            the database rejects it; here ``'*'`` reaches the query unchanged.
        """
        result = Bag()
        for query in queries:
            qattr = dict(query.attr)
            columns = qattr.pop('columns', '*')
            table = qattr.pop('table')
            dbenv_kw = dictExtract(qattr, 'dbenv_', True)
            with self.db.tempEnv(**dbenv_kw):
                result[query.label] = self.db.table(table).dbSelectHandler().fetchRecordsAsBag(columns=columns,
                                                                                        **qattr)
        return result
