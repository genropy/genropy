# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler.get_selection : Selection/query engine
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

"""Selection/query engine mixin.

Provides :class:`GetSelectionMixin` — the ``getSelection`` flow, which
is the primary mechanism for loading tabular data into grids.  Includes
the main ``getSelection`` entry point and all its supporting private
methods: query building, column processing, linked selections,
external queries and the default query executor.
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import templateReplace, splitAndStrip


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
        tblobj = self.db.table(table)
        if isinstance(where, Bag):
            where, kwargs = self._decodeWhereBag(tblobj, where, kwargs)
        if condition:
            where = '( %s ) AND ( %s )' % (where, condition) if where else condition
        return tblobj.query(columns=columns, distinct=distinct, where=where,
                            relationDict=relationDict, sqlparams=sqlparams, **kwargs).count()

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
            BUG: At line 785 in original, ``formats[7:]`` should be
            ``formats[k[7:]]`` — the slice ``7:`` on the dict key is
            used as a dict key assignment, but the code writes
            ``formats[7:] = ...`` which raises ``TypeError`` since
            dicts don't support slice assignment.

            SMELL: The method has ~40 parameters — a strong indicator
            that it should be decomposed into smaller units or use a
            parameter object.
        """
        t = time.time()
        tblobj = self.db.table(table)
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
                formats[7:] = kwargs.pop(k)  # BUG: slice assignment on dict — should be ``formats[k[7:]] = ...``
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
                userobject_tbl = self.db.table('adm.userobject')
                where = userobject_tbl.loadUserObject(userObjectIdOrCode=savedQuery,
                                                      objtype='query', tbl=tblobj.fullname)[0]
                if where['where']:
                    limit = where['queryLimit']
                    savedView = savedView or where['currViewPath']
                    customOrderBy = customOrderBy or where['customOrderBy']
                    where = where['where']
            if savedView:
                userobject_tbl = self.db.table('adm.userobject')
                columns = userobject_tbl.loadUserObject(userObjectIdOrCode=savedView,
                                                        objtype='view', tbl=tblobj.fullname)[0]
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
                self._externalQueries(selection=selection, external_queries=external_queries)
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
        resultAttributes['hardQueryLimitOver'] = hardQueryLimit and resultAttributes['totalrows'] == hardQueryLimit
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
        """
        external_queries = {}
        if isinstance(columns, Bag):
            columns = self._columnsFromStruct(columns)
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
                if col.endswith(']'):
                    col = col[:-1]
                columns.append('.'.join(maintable + [col.rstrip(']')]))
                if col.endswith(']'):
                    maintable = []
            columns = ','.join(columns)
        if expressions:
            expr_dict = getattr(self.page, 'expr_%s' % expressions)()
            expr_dict = dict([(k, '%s AS %s' % (v, k)) for k, v in list(expr_dict.items())])
            columns = templateReplace(columns, expr_dict, safeMode=True)
        hasProtectionColumns = tblobj.hasProtectionColumns()
        if hasProtectionColumns:
            columns = '%s,$__is_protected_row AS _is_readonly_row,$__protecting_reasons' % columns

        if tblobj.hasInvalidCheck():
            columns = '%s,$__is_invalid_row AS _is_invalid_row,$__invalid_reasons' % columns

        return columns, external_queries

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

        Note:
            SMELL: Calls ``self.app._decodeWhereBag`` (line 973 in
            original) instead of ``self._decodeWhereBag`` — the ``app``
            attribute is ``self`` (since the page's ``app`` property
            returns this handler), but the indirection is confusing.
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

        textwhere, decoded_query_pars = self.app._decodeWhereBag(tblobj, where, decoded_query_pars)
        # SMELL: self.app._decodeWhereBag — self.app is self, so this is self._decodeWhereBag with extra indirection
        where.walk(findPars)
        if condition:
            textwhere = '({}) AND ({})'.format(textwhere, condition)

        q = tblobj.query(where=textwhere, **decoded_query_pars)
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
        rpcquery['where_as_html'] = self.db.whereTranslator.toHtml(tblobj, where)
        rpcquery['sqlquery'] = sqltext
        return rpcquery

    def _externalQueries(self, selection: Any = None,
                         external_queries: Optional[dict] = None) -> None:
        """Execute queries on external stores and merge results.

        When columns reference external stores (via ``:`` notation),
        this method queries each external store and merges the results
        back into the main selection.

        Args:
            selection: The main selection.
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
        sqlContextBag = None
        _qmpkeys = None
        if sqlContextName:
            sqlContextBag = self._getSqlContextConditions(sqlContextName)

        linkedSelectionKw = self._handleLinkedSelection(selectionName=selectionName) if selectionName else None
        if linkedSelectionKw:
            where = linkedSelectionKw['where']
            kwargs['_masterPkeys'] = linkedSelectionKw['linkedPkeys']
        elif pkeys:
            if isinstance(pkeys, str):
                pkeys = pkeys.strip(',').split(',')
            if len(pkeys) == 0:
                kwargs['limit'] = 0
            elif len(pkeys) == 1:
                where = 't0.%s =:_pkey' % tblobj.pkey
                kwargs['_pkey'] = pkeys[0]
            else:
                where = 't0.%s in :pkeys' % tblobj.pkey
                kwargs['pkeys'] = pkeys
        elif isinstance(where, Bag):
            kwargs.pop('where_attr', None)
            where, kwargs = self._decodeWhereBag(tblobj, where, kwargs)
        if condition and not pkeys:
            where = ' ( %s ) AND ( %s ) ' % (where, condition) if where else condition
        if filteringPkeys:
            if isinstance(filteringPkeys, str):
                filteringWhere = None
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
                if len(filteringPkeys) == 0:
                    filteringWhere = 't0.%s IS NULL' % tblobj.pkey
                elif len(filteringPkeys) == 1:
                    filteringWhere = 't0.%s =:_filteringPkey' % tblobj.pkey
                    kwargs['_filteringPkey'] = filteringPkeys[0]
                else:
                    filteringWhere = 't0.%s in :_filteringPkeys' % tblobj.pkey
                    kwargs['_filteringPkeys'] = filteringPkeys
                if filteringWhere:
                    where = filteringWhere if not where else ' ( %s ) AND ( %s ) ' % (filteringWhere, where)

        if countOnly:
            columns = f"${tblobj.pkey}"
            query = tblobj.query(columns=columns, where=where,
                                 distinct=True,
                                 order_by=order_by, limit=limit, offset=offset,
                                 group_by=f'${tblobj.pkey}', having=having,
                                 relationDict=relationDict, sqlparams=sqlparams, locale=self.page.locale,
                                 excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft, **kwargs)
            return len(query.fetch())
        query = tblobj.query(columns=columns, distinct=distinct, where=where,
                             order_by=order_by, limit=limit, offset=offset, group_by=group_by, having=having,
                             relationDict=relationDict, sqlparams=sqlparams, locale=self.page.locale,
                             excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft, **kwargs)
        if sqlContextName:
            self._joinConditionsFromContext(query, sqlContextName)
        selection = query.selection(sortedBy=sortedBy, _aggregateRows=_aggregateRows)
        if queryMode in ('U', 'I', 'D'):
            _qmpkeys = set(self.page.freezedPkeys(tblobj, selectionName))
            currentpkeys = set(selection.output('pkeylist'))
            if queryMode == 'U':
                rpkeys = _qmpkeys.union(currentpkeys)
            elif queryMode == 'I':
                rpkeys = _qmpkeys.intersection(currentpkeys)
            else:
                rpkeys = _qmpkeys.difference(currentpkeys)
            query = tblobj.query(columns=columns, distinct=distinct,
                                 where='${} IN :_rpkeys'.format(tblobj.pkey),
                                 _rpkeys=rpkeys,
                                 order_by=order_by, limit=limit, offset=offset, group_by=group_by, having=having,
                                 relationDict=relationDict, sqlparams=sqlparams, locale=self.page.locale,
                                 excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft, **kwargs)
            selection = query.selection(sortedBy=sortedBy, _aggregateRows=_aggregateRows)

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
        if not isinstance(joinConditions, Bag):
            return joinConditions
        result = dict()
        for jc in list(joinConditions.values()):
            sqlcondition, kwargs = tblobj.sqlWhereFromBag(jc['condition'], kwargs)
            result[jc['relation']] = dict(condition=sqlcondition, one_one=jc['one_one'])
        return result

    def _columnsFromStruct(self, viewbag: Bag,
                           columns: Optional[list] = None) -> Optional[str]:
        """Extract column names from a view structure :class:`Bag`.

        Recursively walks the structure and collects field paths,
        skipping formula columns.

        Args:
            viewbag: The view structure :class:`Bag`.
            columns: Accumulator list (used in recursion).

        Returns:
            A comma-separated column string, or ``None`` if *viewbag*
            is empty.
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
                self._columnsFromStruct(node.value, columns)
        return ','.join(columns)
