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

"""Selection/query engine mixin — the copy that receives new work.

Provides :class:`GetSelectionMixin` — the ``getSelection`` flow, which
is the primary mechanism for loading tabular data into grids.  Includes
the main ``getSelection`` entry point and all its supporting private
methods: query building, column processing, linked selections,
external queries and the default query executor.

The module of the same name under ``gnr.web.gnrwebpage_proxy.apphandler`` is
frozen and is never imported from here.  The method bodies are the ones of
that module; what differs is a block that needs only the table and the
database, replaced by one call on the table proxy ``tblobj.selectionProxy()``
(:class:`gnr.app.gnrsqltable_proxy.selection.SelectionProxy`), and a recorded
defect fix, marked in place with its ``bugs.md`` number.

``_externalQueries`` and ``_columnsFromStruct`` are not part of this copy: the
proxy owns that code, this flow calls it there, and no caller anywhere in
``gnrpy``, ``projects``, ``resources`` or ``gnrjs`` names the handler copies.
"""

from __future__ import annotations

import time
from typing import Any, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import splitAndStrip

__all__ = ['GetSelectionMixin']


class GetSelectionMixin:
    """Mixin for the ``getSelection`` flow.

    This is the largest and most complex flow in the handler.  It
    supports:

    - Standard SQL queries with WHERE, ORDER BY, GROUP BY, HAVING
    - Query-by-sample (WHERE bag decoded from client)
    - Saved queries and saved views
    - Linked (master-slave) selections
    - External store queries
    - Custom select methods
    - Count-only mode
    - Sum columns
    - Previous selection diff (prevSelectedDict)

    ``_customSqlOpCallbacks`` and ``_decodeWhereBag``, which the rest of the
    handler shares, live in the class body of the package ``__init__``.
    """

    @public_method
    def getRecordCount(self, field: Optional[str] = None,
                       value: Any = None,
                       table: str = '', distinct: bool = False,
                       columns: str = '', where: Union[str, Bag] = '',
                       relationDict: Optional[dict] = None,
                       sqlparams: Optional[dict] = None,
                       condition: Optional[str] = None,
                       **kwargs: Any) -> int:
        """Count records matching the given criteria.

        Args:
            field: When set, build a simple ``$field = :value`` WHERE.
                May be a fully qualified ``pkg.table.field`` path.
            value: Value to match against *field*.
            table: Fully qualified table name.
            distinct: Use ``SELECT DISTINCT``.
            columns: Column expression for the query.
            where: SQL WHERE clause or a :class:`Bag` to decode.
            relationDict: Symbolic relation names.
            sqlparams: Additional SQL parameters.
            condition: Extra condition ANDed to *where*.

        Returns:
            The record count.
        """
        if field:
            if not table:
                pkg, table, field = splitAndStrip(field, '.', fixed=-3)
                table = '%s.%s' % (pkg, table)
            where = '$%s = :value' % field
            kwargs['value'] = value
        return self.db.table(table).selectionProxy().countRecords(
            where=where, condition=condition, distinct=distinct, columns=columns,
            relationDict=relationDict, sqlparams=sqlparams,
            customOpCb=self._customSqlOpCallbacks, **kwargs)

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

        This is the primary entry point for all grid data loading.
        It handles query construction, execution, freezing, pagination,
        and result formatting.

        Args:
            table: Fully qualified table name.
            distinct: Use SELECT DISTINCT.
            columns: Column specification.
            where: SQL WHERE clause or a :class:`Bag` (query-by-sample).
            condition: Extra condition ANDed with *where*.
            order_by: SQL ORDER BY clause.
            limit: Maximum rows.
            offset: Row offset.
            group_by: SQL GROUP BY clause.
            having: SQL HAVING clause.
            relationDict: Symbolic relation names.
            sqlparams: Additional SQL parameters.
            row_start: Pagination start (string, converted to int).
            row_count: Pagination size (string, converted to int).
            filteringPkeys: Pkeys or method name to filter results.
            recordResolver: Add resolver attributes for lazy record loading.
            selectionName: Name for freezing the selection.
            queryMode: Query set operation (``"U"``/``"I"``/``"D"``).
            structure: Return structure alongside data.
            numberedRows: Use numbered row keys.
            pkeys: Explicit pkey list (bypasses WHERE).
            fromSelection: Frozen selection to use as pkey source.
            applymethod: Post-processing method name.
            totalRowCount: Include total count in attributes.
            selectmethod: Custom select method name.
            expressions: Named expression set for column substitution.
            sum_columns: Comma-separated columns to sum.
            sortedBy: Sort specification for the selection.
            excludeLogicalDeleted: Exclude logically deleted records.
            excludeDraft: Exclude draft records.
            hardQueryLimit: Hard limit on result rows.
            savedQuery: Saved query identifier.
            savedView: Saved view identifier.
            externalChanges: Unused.
            prevSelectedDict: Previously selected pkeys (for diff).
            checkPermissions: Permission parameters.
            queryBySample: Unused.
            weakLogicalDeleted: Retry without logical deletion filter.
            customOrderBy: Custom ordering :class:`Bag`.
            queryExtraPars: Extra query parameters :class:`Bag`.
            joinConditions: Join condition specifications.
            multiStores: Database store name.
            saveRpcQuery: Return serialized query instead of data.
            gridVisibleColumns: Columns visible in the grid.
            formulaVariants: Formula variant specifications.
            countOnly: Return only the count, not the data.

        Returns:
            A tuple ``(data_bag, attributes_dict)``.

        Note:
            SMELL: The method has ~40 parameters — a strong indicator
            that it should be decomposed into smaller units or use a
            parameter object.

            Four results differ from the ones :class:`GnrWebAppHandler`
            produces, each a defect of the frozen handler fixed here and
            covered by a test that asserts the divergence: the
            ``format_<column>`` keyword (A9), the ``whereAsPlainText`` and the
            ``queryLimit`` of a saved query (#1359), ``hardQueryLimitOver`` on
            a frozen selection (E10) and the end of a bracket column group
            (F4, in the proxy).
        """
        t = time.time()
        tblobj = self.db.table(table)
        selectionProxy = tblobj.selectionProxy()
        row_start = int(row_start)
        row_count = int(row_count)
        newSelection = True
        if multiStores:
            kwargs['_storename'] = multiStores
        formats = {}
        if queryExtraPars:
            kwargs.update(queryExtraPars.asDict(ascii=True))
        if limit is None and hardQueryLimit is not None:
            limit = hardQueryLimit
        wherebag = where if isinstance(where, Bag) else None
        if formulaVariants:
            for k, v in formulaVariants.items():
                kwargs[k] = v.asDict()
        if saveRpcQuery:
            rpcquery = self._prepareRpcQuery(tblobj=tblobj, distinct=distinct,
                                             columns=gridVisibleColumns or columns,
                                             where=where, condition=condition,
                                             order_by=order_by, limit=limit, group_by=group_by, having=having,
                                             excludeLogicalDeleted=excludeLogicalDeleted,
                                             excludeDraft=excludeDraft, **kwargs)
            return Bag(), dict(rpcquery=rpcquery.toXml())
        resultAttributes = {}
        if checkPermissions is True:
            checkPermissions = self.page.permissionPars
        for k in list(kwargs.keys()):
            if k.startswith('format_'):
                formats[k[7:]] = kwargs.pop(k)  # bugs.md A9: the frozen handler writes ``formats[7:]``
        if selectionName.startswith('*'):
            if selectionName == '*':
                selectionName = self.page.page_id
            else:
                selectionName = selectionName[1:]
        elif selectionName:
            selection = self.page.unfreezeSelection(tblobj, selectionName)
            if selection is not None:
                if sortedBy and ','.join(selection.sortedBy or []) != sortedBy:
                    selection.sort(sortedBy)
                    self.page.freezeSelectionUpdate(selection)
                debug = 'fromPickle'
                newSelection = False
        if newSelection:
            debug = 'fromDb'
            if savedQuery:
                savedrecord = selectionProxy.loadSavedQueryRecord(savedQuery)
                if savedrecord['where']:
                    limit = savedrecord['queryLimit']
                    savedView = savedView or savedrecord['currViewPath']
                    customOrderBy = customOrderBy or savedrecord['customOrderBy']
                # bugs.md C1: the frozen handler keeps the loaded record in
                # ``where`` when the record carries no WHERE
                where = savedrecord['where']
                # bugs.md #1359: the two derivations of the prologue read the
                # caller's where and limit, which the saved query has replaced
                wherebag = where if isinstance(where, Bag) else None
                if limit is None and hardQueryLimit is not None:
                    limit = hardQueryLimit
            if savedView:
                columns = selectionProxy.loadSavedViewColumns(savedView)
            if selectmethod:
                selecthandler = self.page.getPublicMethod('rpc', selectmethod)
            else:
                selecthandler = self._default_getSelection
            columns, external_queries = self._getSelection_columns(tblobj, columns, expressions=expressions)
            if fromSelection:
                fromSelection = self.page.unfreezeSelection(tblobj, fromSelection)
                pkeys = fromSelection.output('pkeylist')
            if customOrderBy:
                order_by = []
                for fieldpath, sorting in customOrderBy.digest('#v.fieldpath,#v.sorting'):
                    fieldpath = '$%s' % fieldpath if not fieldpath.startswith('@') else fieldpath
                    sorting = 'asc' if sorting else 'desc'
                    order_by.append('%s %s' % (fieldpath, sorting))
                order_by = ' , '.join(order_by)
                sortedBy = None
            if joinConditions:
                joinConditions = self._decodeJoinConditions(tblobj, joinConditions, kwargs)
                kwargs['joinConditions'] = joinConditions

            selection_pars = dict(tblobj=tblobj, table=table, distinct=distinct, columns=columns, where=where,
                                  condition=condition, queryMode=queryMode,
                                  order_by=order_by, limit=limit, offset=offset, group_by=group_by, having=having,
                                  relationDict=relationDict, sqlparams=sqlparams,
                                  recordResolver=recordResolver, selectionName=selectionName,
                                  pkeys=pkeys, sortedBy=sortedBy, excludeLogicalDeleted=excludeLogicalDeleted,
                                  excludeDraft=excludeDraft, checkPermissions=checkPermissions,
                                  filteringPkeys=filteringPkeys, countOnly=countOnly, **kwargs)
            selection = selecthandler(**selection_pars)
            if countOnly:
                return Bag(), dict(table=table, selectionName=selectionName, totalrows=selection)
            if selection is False:
                return Bag(), dict(table=table, selectionName=selectionName)
            elif selectmethod and isinstance(selection, list):
                self._default_getSelection()  # SMELL: called with no args — likely a bug or dead code

            if not selection and weakLogicalDeleted and \
                    excludeLogicalDeleted and excludeLogicalDeleted != 'mark':
                selection_pars['excludeLogicalDeleted'] = 'mark'
                selection = selecthandler(**selection_pars)
            if external_queries:
                selectionProxy.mergeExternalStoreColumns(selection=selection,
                                                 external_queries=external_queries)
            if applymethod:
                applyPars = self._getApplyMethodPars(kwargs)
                applyresult = self.page.getPublicMethod('rpc', applymethod)(selection, **applyPars)
                if applyresult:
                    resultAttributes.update(applyresult)

            if selectionName:
                selection.setKey('rowidx')
                selectionPath = self.page.freezeSelection(selection, selectionName, freezePkeys=True)
                self.page.userStore().setItem('current.table.%s.last_selection_path' % table.replace('.', '_'),
                                              selectionPath)
            resultAttributes.update(table=table, method='app.getSelection', selectionName=selectionName,
                                    row_count=row_count,
                                    totalrows=len(selection))
        generator = selection.output(mode='generator', offset=row_start, limit=row_count, formats=formats)
        _addClassesDict = dict([(k, v['_addClass']) for k, v in list(selection.colAttrs.items()) if '_addClass' in v])
        data = self.gridSelectionData(selection, generator, logicalDeletionField=tblobj.logicalDeletionField,
                                      recordResolver=recordResolver, numberedRows=numberedRows,
                                      _addClassesDict=_addClassesDict)
        if not structure:
            result = data
        else:
            result = Bag()
            result['data'] = data
            result['structure'] = self.gridSelectionStruct(selection)
        resultAttributes.update({'debug': debug, 'servertime': int((time.time() - t) * 1000),
                                 'newproc': getattr(self, 'self.newprocess', 'no')})

        if totalRowCount:
            resultAttributes['totalRowCount'] = tblobj.query(where=condition,
                                                             excludeLogicalDeleted=excludeLogicalDeleted,
                                                             excludeDraft=excludeDraft,
                                                             **kwargs).count()

        if sum_columns:
            sum_columns_list = sum_columns.split(',')
            sum_columns_filtered = [c for c in sum_columns_list if c in selection.columns]
            totals = selection.sum(sum_columns_filtered)
            if totals:
                for i, col in enumerate(sum_columns_filtered):
                    resultAttributes['sum_%s' % col] = totals[i]
                    sum_columns_list.remove(col)
            for col in sum_columns_list:
                resultAttributes['sum_%s' % col] = False
        if prevSelectedDict:
            keys = list(prevSelectedDict.keys())
            resultAttributes['prevSelectedIdx'] = [m['rowidx'] for m in [r for r in selection.data if r['pkey'] in keys]]
        if wherebag:
            resultAttributes['whereAsPlainText'] = tblobj.whereTranslator.toHtml(tblobj, wherebag)
        # bugs.md E10: ``totalrows`` is written only on the new selection
        # path, so the frozen handler raises KeyError on a frozen one
        resultAttributes['hardQueryLimitOver'] = hardQueryLimit and len(selection) == hardQueryLimit
        if self.page.pageStore().getItem('slaveSelections.%s' % selectionName):
            with self.page.pageStore() as store:
                slaveSelections = store.getItem('slaveSelections.%s' % selectionName)
                if slaveSelections:
                    for page_id, grids in list(slaveSelections.items()):
                        if self.page.site.register.exists(page_id, register_name='page'):
                            for nodeId in list(grids.keys()):
                                self.page.clientPublish('%s_refreshLinkedSelection' % nodeId,
                                                        value=True, page_id=page_id)
                        else:
                            slaveSelections.popNode(page_id)
        return (result, resultAttributes)

    # -----------------------------------------------------------------------
    #  Private methods of the getSelection flow
    # -----------------------------------------------------------------------

    def _getSelection_columns(self, tblobj: Any, columns: Union[str, Bag],
                              expressions: Optional[str] = None) -> tuple[str, dict]:
        """Process and normalize column specifications.

        Handles Bag-based column specs, bracket notation for
        multi-table columns, expression substitution, and automatic
        addition of protection/invalid columns.

        Args:
            tblobj: The table object.
            columns: Raw column specification.
            expressions: Named expression set for substitution.

        Returns:
            A tuple ``(columns_string, external_queries_dict)``.

        Note:
            The named expression set is the only page service of the block:
            it is resolved here and handed over as a plain dict.
        """
        expr_dict = getattr(self.page, 'expr_%s' % expressions)() if expressions else None
        return tblobj.selectionProxy().composeSelectionColumns(columns, expressions=expr_dict)

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
        """Serialize query parameters for RPC transmission.

        Builds the SQL query, extracts parameters from environment and
        WHERE bag, and packages everything into a :class:`Bag` that can
        be sent to the client for later re-execution.

        Args:
            tblobj: The table object.
            distinct: Use SELECT DISTINCT.
            columns: Column specification.
            where: WHERE clause (expected to be a :class:`Bag`).
            condition: Extra SQL condition.
            order_by: ORDER BY clause.
            limit: Row limit.
            group_by: GROUP BY clause.
            having: HAVING clause.
            excludeLogicalDeleted: Exclude logically deleted records.
            excludeDraft: Exclude draft records.

        Returns:
            A :class:`Bag` with all query parameters and the generated
            SQL text.
        """
        return tblobj.selectionProxy().serializeQuery(
            distinct=distinct, columns=columns, where=where, condition=condition,
            order_by=order_by, limit=limit, group_by=group_by, having=having,
            excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft,
            customOpCbDict=self._customSqlOpCallbacks(), **kwargs)

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
        """Default query executor for ``getSelection``.

        Handles pkey-based queries, WHERE bag decoding, linked selections,
        filtering pkeys, SQL context conditions, query mode operations
        (union/intersection/difference), and count-only mode.

        Args:
            tblobj: The table object.
            table: Fully qualified table name.
            distinct: Use SELECT DISTINCT.
            columns: Column specification.
            where: SQL WHERE clause.
            condition: Extra condition.
            order_by: ORDER BY clause.
            limit: Row limit.
            offset: Row offset.
            group_by: GROUP BY clause.
            having: HAVING clause.
            relationDict: Symbolic relation names.
            sqlparams: Additional SQL parameters.
            recordResolver: Unused in this method.
            selectionName: Selection name (for linked selection lookup).
            pkeys: Explicit pkey list.
            filteringPkeys: Pkeys or method for filtering.
            queryMode: Set operation (``"U"``/``"I"``/``"D"``).
            sortedBy: Sort specification.
            sqlContextName: SQL context name.
            excludeLogicalDeleted: Exclude logically deleted records.
            excludeDraft: Exclude draft records.
            _aggregateRows: Aggregate duplicate rows.
            countOnly: Return count instead of selection.

        Returns:
            A selection object, an integer count (when *countOnly*),
            or ``False`` when no results.
        """
        selectionProxy = tblobj.selectionProxy()
        linkedSelectionKw = self._handleLinkedSelection(selectionName=selectionName) if selectionName else None
        linkedSelectionKw = linkedSelectionKw or {}
        where, kwargs = selectionProxy.composeWhere(where=where, condition=condition, pkeys=pkeys,
                                                      masterWhere=linkedSelectionKw.get('where'),
                                                      masterPkeys=linkedSelectionKw.get('linkedPkeys'),
                                                      customOpCb=self._customSqlOpCallbacks,
                                                      kwargs=kwargs)
        if filteringPkeys:
            if isinstance(filteringPkeys, str):
                if ',' in filteringPkeys:
                    filteringPkeys = filteringPkeys.split(',')
                else:
                    handler = self.page.getPublicMethod('rpc', filteringPkeys)
                    if handler:
                        filteringPkeys = handler(tblobj=tblobj,
                                                 where=where, relationDict=relationDict,
                                                 sqlparams=sqlparams, limit=limit, **kwargs)
                        if filteringPkeys and not isinstance(filteringPkeys, list):
                            if hasattr(filteringPkeys, 'forcedOrderBy'):
                                order_by = filteringPkeys.forcedOrderBy
                                sortedBy = None
                            filteringPkeys = filteringPkeys.output('pkeylist')
                    else:
                        filteringPkeys = [filteringPkeys]
                where, kwargs = selectionProxy.composeFilteringWhere(where, filteringPkeys, kwargs)

        if countOnly:
            return selectionProxy.countDistinctRecords(where=where,
                                              order_by=order_by, limit=limit, offset=offset,
                                              having=having,
                                              relationDict=relationDict, sqlparams=sqlparams,
                                              locale=self.page.locale,
                                              excludeLogicalDeleted=excludeLogicalDeleted,
                                              excludeDraft=excludeDraft, **kwargs)

        def applyContextJoins(query: Any) -> None:
            self._joinConditionsFromContext(query, sqlContextName)

        selection = selectionProxy.selectRecords(columns=columns, distinct=distinct, where=where,
                                                    order_by=order_by, limit=limit, offset=offset,
                                                    group_by=group_by, having=having,
                                                    relationDict=relationDict, sqlparams=sqlparams,
                                                    locale=self.page.locale,
                                                    excludeLogicalDeleted=excludeLogicalDeleted,
                                                    excludeDraft=excludeDraft, sortedBy=sortedBy,
                                                    _aggregateRows=_aggregateRows,
                                                    queryCb=applyContextJoins if sqlContextName else None,
                                                    **kwargs)
        if queryMode in ('U', 'I', 'D'):
            selection = selectionProxy.selectCombinedRecords(selection=selection, queryMode=queryMode,
                                                            frozenPkeys=self.page.freezedPkeys(tblobj,
                                                                                               selectionName),
                                                            columns=columns, distinct=distinct,
                                                            order_by=order_by, limit=limit, offset=offset,
                                                            group_by=group_by, having=having,
                                                            relationDict=relationDict, sqlparams=sqlparams,
                                                            locale=self.page.locale,
                                                            excludeLogicalDeleted=excludeLogicalDeleted,
                                                            excludeDraft=excludeDraft, sortedBy=sortedBy,
                                                            _aggregateRows=_aggregateRows, **kwargs)

        return selection

    def _decodeJoinConditions(self, tblobj: Any, joinConditions: Any,
                              kwargs: dict) -> Union[dict, Any]:
        """Decode join conditions from a :class:`Bag` to a dict.

        Args:
            tblobj: The table object.
            joinConditions: A :class:`Bag` of join conditions, or a
                pre-decoded dict (returned as-is).
            kwargs: Query parameters (modified in place by
                ``sqlWhereFromBag``).

        Returns:
            A dict mapping relation names to condition/one_one pairs.
        """
        return tblobj.selectionProxy().decodeJoinConditions(joinConditions, kwargs)
