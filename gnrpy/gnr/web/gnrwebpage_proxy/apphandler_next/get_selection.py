# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.get_selection : Selection/query engine
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

"""Selection and query flow of :class:`GnrWebAppHandlerNext`.

This module is the copy that receives new work.  The module of the same name
under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never imported
from here.

The table level part of the flow runs on the app level table proxy
``tblobj.selectionProxy()``
(:class:`gnr.app.gnrsqltable_proxy.selection.SelectionProxy`).  What is left
here is the page side: the page store, the frozen selections, the rpc method
hooks, the locale and the permissions.  The long methods are split into
helpers with one job each.

Four results differ from the ones :class:`GnrWebAppHandler` produces, each of
them a defect of the handler fixed here and covered by a test that asserts the
divergence.  They are listed in ``.subtasks/alt-apphandler/bugs.md``:

- a ``format_<column>`` keyword reaches the column it names;
- a saved query gets the ``whereAsPlainText`` attribute, and an empty saved
  ``queryLimit`` no longer bypasses ``hardQueryLimit`` (issue #1359);
- ``hardQueryLimitOver`` is computed from the length of the selection, so a
  frozen selection read again with a ``hardQueryLimit`` no longer raises;
- a bracket group of columns ends at its closing bracket.

``_handleLinkedSelection`` is carried over unchanged from the frozen module.
``_externalQueries`` and ``_columnsFromStruct`` are not: the proxy owns that
code, this flow calls it there, and no caller anywhere in ``gnrpy``,
``projects``, ``resources`` or ``gnrjs`` names the handler copies.
"""

from __future__ import annotations

import time
from typing import Any, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import splitAndStrip

__all__ = ['GetSelectionMixin']


class GetSelectionMixin:
    """Mixin for the selection and query flow, on the table selection proxy.

    ``_customSqlOpCallbacks`` and ``_decodeWhereBag``, which the rest of the
    handler shares, live in the class body of the package ``__init__``.
    """

    # ------------------------------------------------------------------
    #  Record count
    # ------------------------------------------------------------------

    @public_method
    def getRecordCount(self, field: Optional[str] = None,
                       value: Any = None,
                       table: str = '', distinct: bool = False,
                       columns: str = '', where: Union[str, Bag] = '',
                       relationDict: Optional[dict] = None,
                       sqlparams: Optional[dict] = None,
                       condition: Optional[str] = None,
                       **kwargs: Any) -> int:
        """Count records matching the given criteria, counting on the proxy.

        The parameters are the ones of the frozen
        :meth:`gnr.web.gnrwebpage_proxy.apphandler.get_selection.GetSelectionMixin.getRecordCount`.
        The page side is the resolution of a fully qualified *field* into the
        table that owns it, and the custom operator callbacks.
        """
        if field:
            if not table:
                pkg, table, field = splitAndStrip(field, '.', fixed=-3)
                table = '%s.%s' % (pkg, table)
            where = '$%s = :value' % field
            kwargs['value'] = value
        return self.db.table(table).selectionProxy().recordCount(
            where=where, condition=condition, distinct=distinct, columns=columns,
            relationDict=relationDict, sqlparams=sqlparams,
            customOpCb=self._customSqlOpCallbacks, **kwargs)

    # ------------------------------------------------------------------
    #  getSelection: the prologue
    # ------------------------------------------------------------------

    def _mergeQueryExtras(self, kwargs: dict, multiStores: Optional[str] = None,
                          queryExtraPars: Optional[Bag] = None,
                          formulaVariants: Optional[Bag] = None) -> dict:
        """Merge the store name, the extra parameters and the formula variants.

        The three are unrelated to each other and all three end up as plain
        query keywords: *multiStores* as ``_storename``, *queryExtraPars* as one
        keyword per entry, *formulaVariants* as one dict keyword per cell.
        """
        if multiStores:
            kwargs['_storename'] = multiStores
        if queryExtraPars:
            kwargs.update(queryExtraPars.asDict(ascii=True))
        if formulaVariants:
            for cell, variant in formulaVariants.items():
                kwargs[cell] = variant.asDict()
        return kwargs

    def _limitWithHardQueryLimit(self, limit: Optional[int],
                                 hardQueryLimit: Optional[int]) -> Optional[int]:
        """Return *limit*, falling back to the hard query limit."""
        if limit is None and hardQueryLimit is not None:
            return hardQueryLimit
        return limit

    def _popColumnFormats(self, kwargs: dict) -> dict:
        """Pop the ``format_<column>`` keywords and key them by column name.

        :class:`GnrWebAppHandler` assigns to ``formats[7:]``, a slice of the
        dict, so the format never reaches the column it names.
        """
        formats = {}
        for k in list(kwargs.keys()):
            if k.startswith('format_'):
                formats[k[7:]] = kwargs.pop(k)
        return formats

    # ------------------------------------------------------------------
    #  getSelection: selection name and saved objects
    # ------------------------------------------------------------------

    def _resolveSelectionName(self, selectionName: str) -> tuple[str, bool]:
        """Resolve the name of the selection and say whether it may be reused.

        A name starting with ``'*'`` asks to freeze under that name and never
        to reuse what is already frozen: ``'*'`` alone becomes the page id,
        ``'*name'`` becomes ``'name'``.  Any other name is used as it is.

        Returns:
            A ``(selectionName, reusable)`` tuple.
        """
        if selectionName.startswith('*'):
            resolved = self.page.page_id if selectionName == '*' else selectionName[1:]
            return resolved, False
        return selectionName, bool(selectionName)

    def _unfreezeAndResortSelection(self, tblobj: Any, selectionName: str,
                                    sortedBy: Optional[str]) -> Any:
        """Unfreeze the named selection, re-sorting and re-freezing it.

        The write is the point: when the caller asks for a sorting the frozen
        selection does not have, the selection is sorted and written back
        through ``freezeSelectionUpdate`` before it is returned.

        Returns:
            The frozen selection, or ``None`` when no selection is frozen
            under that name and a new one has to be built.
        """
        selection = self.page.unfreezeSelection(tblobj, selectionName)
        if selection is not None and sortedBy \
                and ','.join(selection.sortedBy or []) != sortedBy:
            selection.sort(sortedBy)
            self.page.freezeSelectionUpdate(selection)
        return selection

    def _savedQueryPars(self, selectionProxy: Any, savedQuery: str,
                        limit: Optional[int] = None,
                        savedView: Optional[str] = None,
                        customOrderBy: Optional[Bag] = None) -> tuple:
        """Read a saved query and return the parameters it overrides.

        :class:`GnrWebAppHandler` keeps the loaded record itself in the
        ``where`` variable when that record carries no WHERE, and hands the
        record to the where bag decoder; here the saved WHERE is taken
        whatever it contains, so an empty one means no filter.

        Returns:
            A ``(where, limit, savedView, customOrderBy)`` tuple.
        """
        record = selectionProxy.loadSavedQuery(savedQuery)
        if record['where']:
            limit = record['queryLimit']
            savedView = savedView or record['currViewPath']
            customOrderBy = customOrderBy or record['customOrderBy']
        return record['where'], limit, savedView, customOrderBy

    def _customOrderByClause(self, customOrderBy: Bag) -> str:
        """Build the ORDER BY clause of a custom ordering bag."""
        order_by = []
        for fieldpath, sorting in customOrderBy.digest('#v.fieldpath,#v.sorting'):
            fieldpath = '$%s' % fieldpath if not fieldpath.startswith('@') else fieldpath
            order_by.append('%s %s' % (fieldpath, 'asc' if sorting else 'desc'))
        return ' , '.join(order_by)

    # ------------------------------------------------------------------
    #  getSelection: after the query
    # ------------------------------------------------------------------

    def _freezeNamedSelection(self, selection: Any, selectionName: str,
                              table: str) -> None:
        """Freeze the selection and record its path in the user store."""
        selection.setKey('rowidx')
        selectionPath = self.page.freezeSelection(selection, selectionName,
                                                  freezePkeys=True)
        self.page.userStore().setItem(
            'current.table.%s.last_selection_path' % table.replace('.', '_'),
            selectionPath)

    def _selectionResult(self, selection: Any, tblobj: Any, row_start: int = 0,
                         row_count: int = 0, formats: Optional[dict] = None,
                         recordResolver: bool = True, numberedRows: bool = True,
                         structure: bool = False) -> Bag:
        """Turn the selection into the :class:`Bag` the grid reads.

        With *structure* the returned :class:`Bag` is not the data: it carries
        the data under ``data`` and the grid structure under ``structure``.
        """
        generator = selection.output(mode='generator', offset=row_start,
                                     limit=row_count, formats=formats)
        addClassesDict = dict([(k, v['_addClass'])
                               for k, v in list(selection.colAttrs.items())
                               if '_addClass' in v])
        data = self.gridSelectionData(selection, generator,
                                      logicalDeletionField=tblobj.logicalDeletionField,
                                      recordResolver=recordResolver,
                                      numberedRows=numberedRows,
                                      _addClassesDict=addClassesDict)
        if not structure:
            return data
        result = Bag()
        result['data'] = data
        result['structure'] = self.gridSelectionStruct(selection)
        return result

    def _sumColumnsAttributes(self, selection: Any, sum_columns: str) -> dict:
        """Sum the requested columns; a column the selection lacks sums to False."""
        result = {}
        requested = sum_columns.split(',')
        available = [c for c in requested if c in selection.columns]
        totals = selection.sum(available)
        if totals:
            for i, col in enumerate(available):
                result['sum_%s' % col] = totals[i]
                requested.remove(col)
        for col in requested:
            result['sum_%s' % col] = False
        return result

    def _prevSelectedIdx(self, selection: Any, prevSelectedDict: dict) -> list:
        """Return the row indexes of the rows selected by the previous call."""
        keys = list(prevSelectedDict.keys())
        return [r['rowidx'] for r in selection.data if r['pkey'] in keys]

    def _notifySlaveSelections(self, selectionName: str) -> None:
        """Ask the live slave grids to refresh, and forget the dead pages."""
        storekey = 'slaveSelections.%s' % selectionName
        if not self.page.pageStore().getItem(storekey):
            return
        with self.page.pageStore() as store:
            slaveSelections = store.getItem(storekey)
            if not slaveSelections:
                return
            for page_id, grids in list(slaveSelections.items()):
                if self.page.site.register.exists(page_id, register_name='page'):
                    for nodeId in list(grids.keys()):
                        self.page.clientPublish('%s_refreshLinkedSelection' % nodeId,
                                                value=True, page_id=page_id)
                else:
                    slaveSelections.popNode(page_id)

    # ------------------------------------------------------------------
    #  getSelection
    # ------------------------------------------------------------------

    @public_method
    def getSelection(self, table: str = '', distinct: bool = False,
                     columns: str = '', where: Union[str, Bag] = '',
                     condition: Optional[str] = None,
                     order_by: Optional[str] = None,
                     limit: Optional[int] = None,
                     offset: Optional[int] = None,
                     group_by: Optional[str] = None,
                     having: Optional[str] = None,
                     relationDict: Optional[dict] = None,
                     sqlparams: Optional[dict] = None,
                     row_start: str = '0', row_count: str = '0',
                     filteringPkeys: Optional[Any] = None,
                     recordResolver: bool = True,
                     selectionName: str = '',
                     queryMode: Optional[str] = None,
                     structure: bool = False,
                     numberedRows: bool = True,
                     pkeys: Optional[Any] = None,
                     fromSelection: Optional[str] = None,
                     applymethod: Optional[str] = None,
                     totalRowCount: bool = False,
                     selectmethod: Optional[str] = None,
                     expressions: Optional[str] = None,
                     sum_columns: Optional[str] = None,
                     sortedBy: Optional[str] = None,
                     excludeLogicalDeleted: Any = True,
                     excludeDraft: bool = True,
                     hardQueryLimit: Optional[int] = None,
                     savedQuery: Optional[str] = None,
                     savedView: Optional[str] = None,
                     externalChanges: Optional[Any] = None,
                     prevSelectedDict: Optional[dict] = None,
                     checkPermissions: Optional[Any] = None,
                     queryBySample: bool = False,
                     weakLogicalDeleted: bool = False,
                     customOrderBy: Optional[Bag] = None,
                     queryExtraPars: Optional[Bag] = None,
                     joinConditions: Optional[Any] = None,
                     multiStores: Optional[str] = None,
                     saveRpcQuery: Optional[bool] = None,
                     gridVisibleColumns: Optional[str] = None,
                     formulaVariants: Optional[Bag] = None,
                     countOnly: bool = False,
                     **kwargs: Any) -> tuple[Bag, dict]:
        """Load a selection of records for grid display.

        The parameters are the ones of the frozen
        :meth:`gnr.web.gnrwebpage_proxy.apphandler.get_selection.GetSelectionMixin.getSelection`.
        The flow is the same, split into helpers, with the table work on
        ``tblobj.selectionProxy()``; the four divergences are listed in the
        module docstring.

        Returns:
            A tuple ``(data_bag, attributes_dict)``.
        """
        t = time.time()
        tblobj = self.db.table(table)
        selectionProxy = tblobj.selectionProxy()
        row_start = int(row_start)
        row_count = int(row_count)
        kwargs = self._mergeQueryExtras(kwargs, multiStores=multiStores,
                                        queryExtraPars=queryExtraPars,
                                        formulaVariants=formulaVariants)
        limit = self._limitWithHardQueryLimit(limit, hardQueryLimit)
        wherebag = where if isinstance(where, Bag) else None
        if saveRpcQuery:
            rpcquery = self._prepareRpcQuery(tblobj=tblobj, distinct=distinct,
                                             columns=gridVisibleColumns or columns,
                                             where=where, condition=condition,
                                             order_by=order_by, limit=limit,
                                             group_by=group_by, having=having,
                                             excludeLogicalDeleted=excludeLogicalDeleted,
                                             excludeDraft=excludeDraft, **kwargs)
            return Bag(), dict(rpcquery=rpcquery.toXml())
        resultAttributes = {}
        if checkPermissions is True:
            checkPermissions = self.page.permissionPars
        formats = self._popColumnFormats(kwargs)
        selectionName, reusable = self._resolveSelectionName(selectionName)
        selection = self._unfreezeAndResortSelection(tblobj, selectionName,
                                                     sortedBy) if reusable else None
        newSelection = selection is None
        debug = 'fromDb' if newSelection else 'fromPickle'
        if newSelection:
            if savedQuery:
                where, limit, savedView, customOrderBy = self._savedQueryPars(
                    selectionProxy, savedQuery, limit=limit, savedView=savedView,
                    customOrderBy=customOrderBy)
                # the two prologue derivations that read what the saved
                # query has just replaced, issue #1359
                wherebag = where if isinstance(where, Bag) else None
                limit = self._limitWithHardQueryLimit(limit, hardQueryLimit)
            if savedView:
                columns = selectionProxy.loadSavedView(savedView)
            if selectmethod:
                selecthandler = self.page.getPublicMethod('rpc', selectmethod)
            else:
                selecthandler = self._default_getSelection
            columns, external_queries = self._getSelection_columns(tblobj, columns,
                                                                   expressions=expressions)
            if fromSelection:
                pkeys = self.page.unfreezeSelection(tblobj, fromSelection).output('pkeylist')
            if customOrderBy:
                order_by = self._customOrderByClause(customOrderBy)
                sortedBy = None
            if joinConditions:
                kwargs['joinConditions'] = self._decodeJoinConditions(tblobj, joinConditions,
                                                                      kwargs)
            selection_pars = dict(tblobj=tblobj, table=table, distinct=distinct,
                                  columns=columns, where=where,
                                  condition=condition, queryMode=queryMode,
                                  order_by=order_by, limit=limit, offset=offset,
                                  group_by=group_by, having=having,
                                  relationDict=relationDict, sqlparams=sqlparams,
                                  recordResolver=recordResolver,
                                  selectionName=selectionName,
                                  pkeys=pkeys, sortedBy=sortedBy,
                                  excludeLogicalDeleted=excludeLogicalDeleted,
                                  excludeDraft=excludeDraft,
                                  checkPermissions=checkPermissions,
                                  filteringPkeys=filteringPkeys, countOnly=countOnly,
                                  **kwargs)
            selection = selecthandler(**selection_pars)
            if countOnly:
                return Bag(), dict(table=table, selectionName=selectionName,
                                   totalrows=selection)
            if selection is False:
                return Bag(), dict(table=table, selectionName=selectionName)
            elif selectmethod and isinstance(selection, list):
                # reproduced as it is: the call has no table object and fails
                self._default_getSelection()
            if not selection and weakLogicalDeleted and \
                    excludeLogicalDeleted and excludeLogicalDeleted != 'mark':
                selection_pars['excludeLogicalDeleted'] = 'mark'
                selection = selecthandler(**selection_pars)
            if external_queries:
                selectionProxy.externalQueries(selection=selection,
                                                 external_queries=external_queries)
            if applymethod:
                applyPars = self._getApplyMethodPars(kwargs)
                applyresult = self.page.getPublicMethod('rpc', applymethod)(selection,
                                                                            **applyPars)
                if applyresult:
                    resultAttributes.update(applyresult)
            if selectionName:
                self._freezeNamedSelection(selection, selectionName, table)
            resultAttributes.update(table=table, method='app.getSelection',
                                    selectionName=selectionName, row_count=row_count,
                                    totalrows=len(selection))
        result = self._selectionResult(selection, tblobj, row_start=row_start,
                                       row_count=row_count, formats=formats,
                                       recordResolver=recordResolver,
                                       numberedRows=numberedRows, structure=structure)
        # 'newproc' is the constant 'no': the frozen handler reads the
        # attribute named by the literal string 'self.newprocess', which
        # nothing defines, and nothing in the tree sets 'newprocess' either
        # (bugs.md E5).  The emitted value is the same.
        resultAttributes.update({'debug': debug,
                                 'servertime': int((time.time() - t) * 1000),
                                 'newproc': 'no'})
        if totalRowCount:
            resultAttributes['totalRowCount'] = tblobj.query(
                where=condition, excludeLogicalDeleted=excludeLogicalDeleted,
                excludeDraft=excludeDraft, **kwargs).count()
        if sum_columns:
            resultAttributes.update(self._sumColumnsAttributes(selection, sum_columns))
        if prevSelectedDict:
            resultAttributes['prevSelectedIdx'] = self._prevSelectedIdx(selection,
                                                                        prevSelectedDict)
        if wherebag:
            resultAttributes['whereAsPlainText'] = tblobj.whereTranslator.toHtml(tblobj,
                                                                                 wherebag)
        resultAttributes['hardQueryLimitOver'] = hardQueryLimit and \
            len(selection) == hardQueryLimit
        self._notifySlaveSelections(selectionName)
        return (result, resultAttributes)

    # ------------------------------------------------------------------
    #  Columns
    # ------------------------------------------------------------------

    def _getSelection_columns(self, tblobj: Any, columns: Union[str, Bag],
                              expressions: Optional[str] = None) -> tuple[str, dict]:
        """Delegate the column processing to the table proxy.

        The named expression set is the only page service involved: it is
        resolved here and handed over as a plain dict.
        """
        expr_dict = getattr(self.page, 'expr_%s' % expressions)() if expressions else None
        return tblobj.selectionProxy().selectionColumns(columns, expressions=expr_dict)

    # ------------------------------------------------------------------
    #  Where bag, join conditions, rpc query
    # ------------------------------------------------------------------

    def _decodeJoinConditions(self, tblobj: Any, joinConditions: Any,
                              kwargs: dict) -> Union[dict, Any]:
        """Delegate the join condition decoding to the table proxy."""
        return tblobj.selectionProxy().decodeJoinConditions(joinConditions, kwargs)

    def _prepareRpcQuery(self, tblobj: Any = None, distinct: Optional[bool] = None,
                         columns: Optional[str] = None,
                         where: Optional[Any] = None,
                         condition: Optional[str] = None,
                         order_by: Optional[str] = None,
                         limit: Optional[int] = None,
                         group_by: Optional[str] = None,
                         having: Optional[str] = None,
                         excludeLogicalDeleted: bool = True,
                         excludeDraft: bool = True,
                         **kwargs: Any) -> Bag:
        """Delegate the query serialization to the table proxy."""
        return tblobj.selectionProxy().rpcQuery(
            distinct=distinct, columns=columns, where=where, condition=condition,
            order_by=order_by, limit=limit, group_by=group_by, having=having,
            excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft,
            customOpCbDict=self._customSqlOpCallbacks(), **kwargs)

    # ------------------------------------------------------------------
    #  Default query executor
    # ------------------------------------------------------------------

    def _default_getSelection(self, tblobj: Any = None, table: Optional[str] = None,
                              distinct: Optional[bool] = None,
                              columns: Optional[str] = None,
                              where: Optional[Any] = None,
                              condition: Optional[str] = None,
                              order_by: Optional[str] = None,
                              limit: Optional[int] = None,
                              offset: Optional[int] = None,
                              group_by: Optional[str] = None,
                              having: Optional[str] = None,
                              relationDict: Optional[dict] = None,
                              sqlparams: Optional[dict] = None,
                              recordResolver: Optional[bool] = None,
                              selectionName: Optional[str] = None,
                              pkeys: Optional[Any] = None,
                              filteringPkeys: Optional[Any] = None,
                              queryMode: Optional[str] = None,
                              sortedBy: Optional[str] = None,
                              sqlContextName: Optional[str] = None,
                              excludeLogicalDeleted: Any = True,
                              excludeDraft: bool = True,
                              _aggregateRows: bool = True,
                              countOnly: bool = False,
                              **kwargs: Any) -> Any:
        """Run the default query, with the table work on the table proxy.

        What stays here: the linked selection, the rpc method that resolves
        *filteringPkeys*, the locale, the join conditions of the SQL context and
        the pkeys of the frozen selection used by *queryMode*.
        """
        selectionProxy = tblobj.selectionProxy()
        linkedSelectionKw = self._handleLinkedSelection(
            selectionName=selectionName) if selectionName else None
        where, kwargs = selectionProxy.selectionWhere(
            where=where, condition=condition, pkeys=pkeys,
            linkedSelectionKw=linkedSelectionKw,
            customOpCb=self._customSqlOpCallbacks, kwargs=kwargs)
        if filteringPkeys and isinstance(filteringPkeys, str):
            filteringPkeys, order_by, sortedBy = self._resolveFilteringPkeys(
                tblobj, filteringPkeys, where=where, relationDict=relationDict,
                sqlparams=sqlparams, limit=limit, order_by=order_by,
                sortedBy=sortedBy, kwargs=kwargs)
            where, kwargs = selectionProxy.filteringWhere(where, filteringPkeys, kwargs)
        if countOnly:
            return selectionProxy.countRows(
                where=where, order_by=order_by, limit=limit, offset=offset,
                having=having, relationDict=relationDict, sqlparams=sqlparams,
                locale=self.page.locale, excludeLogicalDeleted=excludeLogicalDeleted,
                excludeDraft=excludeDraft, **kwargs)

        def applyContextJoins(query: Any) -> None:
            self._joinConditionsFromContext(query, sqlContextName)

        selection = selectionProxy.buildSelection(
            columns=columns, distinct=distinct, where=where, order_by=order_by,
            limit=limit, offset=offset, group_by=group_by, having=having,
            relationDict=relationDict, sqlparams=sqlparams, locale=self.page.locale,
            excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft,
            sortedBy=sortedBy, _aggregateRows=_aggregateRows,
            queryCb=applyContextJoins if sqlContextName else None, **kwargs)
        if queryMode in ('U', 'I', 'D'):
            selection = selectionProxy.queryModeSelection(
                selection=selection, queryMode=queryMode,
                frozenPkeys=self.page.freezedPkeys(tblobj, selectionName),
                columns=columns, distinct=distinct, order_by=order_by, limit=limit,
                offset=offset, group_by=group_by, having=having,
                relationDict=relationDict, sqlparams=sqlparams, locale=self.page.locale,
                excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft,
                sortedBy=sortedBy, _aggregateRows=_aggregateRows, **kwargs)
        return selection

    def _resolveFilteringPkeys(self, tblobj: Any, filteringPkeys: str,
                               kwargs: dict,
                               where: Any = None,
                               relationDict: Optional[dict] = None,
                               sqlparams: Optional[dict] = None,
                               limit: Optional[int] = None,
                               order_by: Optional[str] = None,
                               sortedBy: Optional[str] = None) -> tuple:
        """Turn a *filteringPkeys* string into the list of pkeys it names.

        A comma separated string is the list itself.  Any other string is the
        name of an rpc method of the page: it receives the WHERE built so far
        and may answer with a list of pkeys or with a selection, which may in
        turn force its own ordering.  A name no method answers to is the single
        pkey.

        Returns:
            A ``(filteringPkeys, order_by, sortedBy)`` tuple.
        """
        if ',' in filteringPkeys:
            return filteringPkeys.split(','), order_by, sortedBy
        handler = self.page.getPublicMethod('rpc', filteringPkeys)
        if not handler:
            return [filteringPkeys], order_by, sortedBy
        filteringPkeys = handler(tblobj=tblobj, where=where, relationDict=relationDict,
                                 sqlparams=sqlparams, limit=limit, **kwargs)
        if filteringPkeys and not isinstance(filteringPkeys, list):
            if hasattr(filteringPkeys, 'forcedOrderBy'):
                order_by = filteringPkeys.forcedOrderBy
                sortedBy = None
            filteringPkeys = filteringPkeys.output('pkeylist')
        return filteringPkeys, order_by, sortedBy

    # ------------------------------------------------------------------
    #  Carried over unchanged from the frozen module
    # ------------------------------------------------------------------

    def _handleLinkedSelection(self, selectionName: Optional[str] = None) -> Optional[dict]:
        """Handle master-slave linked selection subscriptions.

        Manages subscribe/unsubscribe commands between linked grids
        across pages, and returns the WHERE clause and pkeys needed
        to filter the slave selection.

        Args:
            selectionName: Name of the selection.

        Returns:
            A dict with ``where`` and ``linkedPkeys`` keys, or ``None``
            if no linked selection is active.
        """
        with self.page.pageStore() as slaveStore:
            lsKey = 'linkedSelectionPars.%s' % selectionName
            linkedSelectionPars = slaveStore.getItem(lsKey)
            if not linkedSelectionPars:
                return
            linkedPkeys = linkedSelectionPars['pkeys']
            command = linkedSelectionPars['command']
            if command:
                linkedSelectionPars['command'] = None
                gridNodeId = linkedSelectionPars['gridNodeId']
                if linkedSelectionPars['linkedPageId']:
                    with self.page.pageStore(linkedSelectionPars['linkedPageId']) as masterStore:
                        slavekey = 'slaveSelections.%(linkedSelectionName)s' % linkedSelectionPars
                        slaveSelections = masterStore.getItem(slavekey) or Bag()
                        grids = slaveSelections[self.page.page_id] or Bag()
                        if command == 'subscribe':
                            grids[gridNodeId] = True
                        else:
                            grids.popNode(gridNodeId)
                        if grids:
                            slaveSelections[self.page.page_id] = grids
                        else:
                            slaveSelections.popNode(self.page.page_id)
                        if slaveSelections:
                            masterStore.setItem(slavekey, slaveSelections)
                        else:
                            masterStore.popNode(slavekey)
                if command == 'unsubscribe':
                    for k in list(linkedSelectionPars.keys()):
                        linkedSelectionPars[k] = None
                slaveStore.setItem(lsKey, linkedSelectionPars)
        if linkedSelectionPars['masterTable']:
            if not linkedPkeys:
                linkedPkeys = self.page.freezedPkeys(
                    self.db.table(linkedSelectionPars['masterTable']),
                    linkedSelectionPars['linkedSelectionName'],
                    page_id=linkedSelectionPars['linkedPageId'])
            where = ' OR '.join([" (%s IN :_masterPkeys) " % r for r in linkedSelectionPars['relationpath'].split(',')])
            return dict(where=' ( %s ) ' % where,
                        linkedPkeys=linkedPkeys.split(',') if isinstance(linkedPkeys, str) else linkedPkeys)
