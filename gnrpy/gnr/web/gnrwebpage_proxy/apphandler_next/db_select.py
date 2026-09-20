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

"""FilteringSelect (dbSelect) mixin.

Provides :class:`DbSelectMixin` — the server side implementation of the
``dbSelect`` widget, which searches a table incrementally while the user types,
plus the three other table services the same widget family needs.

This module is the copy that receives new work.  The module of the same
name under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never
imported from here.

Everything that needs only the table and the database lives on the app level
table proxy ``tblobj.dbSelectHandler()``
(:class:`gnr.app.gnrsqltable_proxy.db_select.DbSelectHandler`).  What stays
here is what needs the page: the store switch, the app configuration, the
``selectmethod`` and ``applymethod`` hooks, the locale and the localizer, the
empty label row and the result attributes.

The methods with no caller anywhere in the tree are not part of the copy:
``dbSelect_selection``.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrdecorator import public_method


class DbSelectMixin:
    """Mixin for FilteringSelect (dbSelect) operations."""

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

        This is the main entry point for the FilteringSelect widget.  It has
        two branches and they are exclusive: with *_id* it fetches the single
        row the widget currently shows, with a query string it searches.  With
        neither it returns an empty Bag, and the *applymethod* still runs, on
        ``None``.

        Args:
            dbtable: Fully qualified table name (``"pkg.table"``).
            columns: Columns to search on.
            auxColumns: Additional columns shown in the dropdown.
            hiddenColumns: Columns fetched but not displayed.
            rowcaption: Custom row caption format.
            _id: When set, fetch the record with this primary key.
            _querystring: Search text typed by the user.
            querystring: Alternative search text parameter; *_querystring*
                wins when both are given.
            ignoreCase: Case-insensitive search.  Part of the select handler
                contract; the default handler does not read it.
            exclude: Comma-separated list of pkeys to exclude.
            excludeDraft: Exclude draft records.
            condition: Additional SQL WHERE condition.
            limit: Maximum number of results; the app configuration
                ``dbselect?limit`` when absent.
            alternatePkey: Use this field instead of the primary key.
            order_by: SQL ORDER BY clause.
            selectmethod: Page RPC replacing the default search.
            applymethod: Page RPC post-processing the selection.
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
        self._dbSelectUseStore(_storename)
        resultClass = ''
        if selectmethod or not condition:
            weakCondition = False
        t0 = time.time()
        querystring = _querystring or querystring
        limit = self._dbSelectLimit(limit)
        tblobj = self.db.table(dbtable)
        handler = tblobj.dbSelectHandler()
        querycolumns, showcolumns, resultcolumns = handler.searchColumns(
            columns=columns, rowcaption=rowcaption, auxColumns=auxColumns,
            hiddenColumns=hiddenColumns, alternatePkey=alternatePkey)
        selection = None
        errors = []
        if _id:
            selection, errors = handler.recordById(
                _id, resultcolumns, condition=condition,
                weakCondition=weakCondition, alternatePkey=alternatePkey,
                excludeDraft=excludeDraft, **kwargs)
        elif querystring:
            selection, resultClass = self._dbSelectSearch(
                handler, self._dbSelectHandlerMethod(selectmethod),
                querystring.strip('*'), querycolumns, showcolumns,
                resultcolumns, condition=condition, weakCondition=weakCondition,
                preferred=preferred, invalidItemCondition=invalidItemCondition,
                exclude=exclude, limit=limit, order_by=order_by,
                ignoreCase=ignoreCase, excludeDraft=excludeDraft, **kwargs)
        applyresult = None
        if applymethod:
            applyresult = self.page.getPublicMethod('rpc', applymethod)(selection, **kwargs)
        result, resultAttrs = self._dbSelectOutput(
            handler, selection, showcolumns, rowcaption=rowcaption,
            applyresult=applyresult, nullRow=not notnull and not _id,
            emptyLabel=emptyLabel, emptyLabel_first=emptyLabel_first,
            emptyLabel_class=emptyLabel_class)
        resultAttrs['resultClass'] = resultClass
        resultAttrs['dbselect_time'] = time.time() - t0
        if errors:
            resultAttrs['errors'] = ','.join(errors)
        return (result, resultAttrs)

    def _dbSelectUseStore(self, _storename: Optional[str]) -> None:
        """Switch the thread to the store the widget asked for.

        A truthy name selects that store, the literal ``False`` resets to the
        main one, ``None`` touches nothing.  The switch is **not** undone when
        the call ends: it stays on the database environment of the thread for
        the rest of the request.  That is the behaviour of the frozen handler
        and it is reproduced on purpose; the record flows scope the same
        parameter to their own query instead.
        """
        if _storename:
            self.db.use_store(_storename)
        elif _storename is False:
            self.db.use_store()

    def _dbSelectLimit(self, limit: Optional[int]) -> int:
        """The page size: the caller's, or the ``dbselect?limit`` app default."""
        if limit is None:
            limit = self.gnrapp.config.get('dbselect?limit', 10)
        return int(limit)

    def _dbSelectHandlerMethod(self, selectmethod: Optional[str]) -> Callable:
        """Resolve the search callable: a page RPC, or the default search."""
        if selectmethod:
            return self.page.getPublicMethod('rpc', selectmethod)
        return self.dbSelect_default

    def _dbSelectSearch(self, handler: Any, selectHandler: Callable,
                        querystring: str, querycolumns: list,
                        showcolumns: list, resultcolumns: list,
                        condition: Optional[str] = None,
                        weakCondition: Any = False,
                        preferred: Optional[str] = None,
                        invalidItemCondition: Optional[str] = None,
                        exclude: Optional[Any] = None,
                        limit: Optional[int] = None,
                        order_by: Optional[str] = None,
                        ignoreCase: bool = True, excludeDraft: bool = True,
                        **kwargs: Any) -> tuple[Any, str]:
        """Run the search, once more without the condition when it is weak.

        A wholly numeric query is turned into a suffix match before anything
        else, so that typing the tail of a number finds it.

        *weakCondition* means "this condition is a preference": when the search
        comes back empty it is tried again, without the condition if it is
        ``True`` and with the caller's one if it is a string — a string weak
        condition is an extra filter, AND-ed to the caller's condition for the
        first attempt only.

        Returns:
            A tuple ``(selection, resultClass)``; *resultClass* is
            ``'relaxedCondition'`` when the second attempt ran.
        """
        if querystring.isdigit():
            querystring = '%%%s' % querystring
        preferred = handler.searchPreferred(preferred)
        weakCondition = handler.searchWeakCondition(weakCondition)
        search_pars = dict(
            tblobj=handler.tblobj, querycolumns=querycolumns,
            querystring=querystring,
            resultcolumns=handler.searchResultColumns(
                resultcolumns, preferred=preferred,
                invalidItemCondition=invalidItemCondition),
            exclude=exclude, limit=limit,
            order_by=handler.searchOrderBy(order_by, showcolumns,
                                           preferred=preferred),
            identifier='pkey', ignoreCase=ignoreCase,
            excludeDraft=excludeDraft, **kwargs)
        firstCondition = ('(%s) AND (%s)' % (condition or 'TRUE', weakCondition)
                          if isinstance(weakCondition, str) else condition)
        selection = selectHandler(condition=firstCondition, **search_pars)
        if not selection and weakCondition:
            selection = selectHandler(
                condition=None if weakCondition is True else condition,
                **search_pars)
            return selection, 'relaxedCondition'
        return selection, ''

    def _dbSelectOutput(self, handler: Any, selection: Any, showcolumns: list,
                        rowcaption: Optional[str] = None,
                        applyresult: Optional[dict] = None,
                        nullRow: bool = True,
                        emptyLabel: Optional[str] = None,
                        emptyLabel_first: Optional[bool] = None,
                        emptyLabel_class: Optional[str] = None
                        ) -> tuple[Bag, dict]:
        """Turn the selection into the Bag the widget reads.

        An empty or missing selection produces an empty Bag and no attributes
        at all: no columns, no headers, no empty label row, and the applymethod
        result dropped.  That is the behaviour of the frozen handler.

        Returns:
            A tuple ``(result_bag, attributes_dict)``.
        """
        if not selection:
            return Bag(), {}
        result = selection.output('selection', locale=self.page.locale,
                                  caption=rowcaption or True)
        columns, headers = handler.selectionHeaders(selection, showcolumns,
                                                    self.page._)
        resultAttrs = {'columns': columns, 'headers': headers}
        if applyresult:
            resultAttrs.update(applyresult)
        if nullRow:
            result.setItem('null_row', None, caption=emptyLabel or '', _pkey=None,
                           _customClasses=emptyLabel_class,
                           _position='<' if emptyLabel_first else None)
        return result, resultAttrs

    @public_method
    def tableAnalyzeStore(self, table: Optional[str] = None,
                          where: Optional[str] = None,
                          group_by: Optional[list] = None,
                          **kwargs: Any) -> tuple[Any, dict]:
        """Analyze table data with aggregation (totalize).

        The totalized Bag is pickled through ``page.lazyBag`` under the
        ``page:explorer`` static location and the resolver is returned already
        resolved, so the caller gets the Bag and the page keeps the file.

        Args:
            table: Fully qualified table name.
            where: SQL WHERE clause.
            group_by: The grouping specification.  It is consumed twice with
                two meanings, as the column list and as the totalize
                specification; the callables in it are only for the second.

        Returns:
            A tuple ``(store_bag, timings_dict)``.
        """
        t0 = time.time()
        page = self.page
        handler = page.db.table(table).dbSelectHandler()
        selection = handler.analyzeSelection(where=where, group_by=group_by,
                                             **kwargs)
        explorer_id = page.getUuid()
        t1 = time.time()
        totalizeBag = selection.totalize(group_by=group_by, collectIdx=False,
                                         keep=['pkey'])
        t2 = time.time()
        store = page.lazyBag(totalizeBag, name=explorer_id,
                             location='page:explorer')()
        t3 = time.time()
        return store, dict(query_time=t1 - t0, totalize_time=t2 - t1,
                           resolver_load_time=t3 - t2)

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

        The signature is a contract: it is the default value of the select
        handler and a page ``selectmethod`` is called with exactly these
        keywords.  *identifier* and *ignoreCase* are part of it and this
        implementation does not read either.

        Args:
            tblobj: The table object.
            querycolumns: Columns to search on.
            querystring: Search text.
            resultcolumns: Columns to return.
            condition: Additional SQL condition.
            exclude: Comma-separated pkeys to exclude, or an iterable.
            limit: Maximum results.
            order_by: SQL ORDER BY.
            identifier: The key column name.  Not read here.
            ignoreCase: Case-insensitive search.  Not read here.

        Returns:
            A selection result.
        """
        return tblobj.dbSelectHandler().searchSelection(
            querycolumns=querycolumns, querystring=querystring,
            resultcolumns=resultcolumns, condition=condition, exclude=exclude,
            limit=limit, order_by=order_by, **kwargs)

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
        return self.db.table(table).dbSelectHandler().valuesString(
            caption_field=caption_field, alt_pkey_field=alt_pkey_field,
            **kwargs)

    @public_method
    def getMultiFetch(self, queries: Optional[Bag] = None) -> Bag:
        """Execute multiple queries in batch.

        Each node of *queries* describes one query: ``table`` names the table
        and is required, ``columns`` defaults to all of them, the ``dbenv_*``
        attributes become a scoped database environment and everything else
        goes to the query.  The caller's Bag is left as it was.

        Args:
            queries: A :class:`Bag`, one node per query.

        Returns:
            A :class:`Bag` with one entry per query, keyed by the node label.
        """
        result = Bag()
        for query in queries:
            qattr = dict(query.attr)
            columns = qattr.pop('columns', '*')
            table = qattr.pop('table')
            dbenv_kw = dictExtract(qattr, 'dbenv_', True)
            with self.db.tempEnv(**dbenv_kw):
                result[query.label] = self.db.table(table).dbSelectHandler(
                ).fetchAsBag(columns=columns, **qattr)
        return result
