# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler.next : app handler built on the table selection proxy
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

"""Alternative web application handler.

:class:`GnrWebAppHandlerNext` produces the same results as
:class:`GnrWebAppHandler`, but the table level part of the ``getSelection``
flow runs on the app level table proxy ``tblobj.selectionHandler()``
(:class:`gnr.app.gnrsqltable_proxy.selection.SelectionHandler`) instead of on
the handler.  What is left here is the page side: the page store, the frozen
selections, the rpc method hooks, the locale and the permissions.

The saved queries and saved views are the one piece of table level work still
running on the inherited code: ``getSelection`` loads them inline, and the only
seam to redirect them to
:meth:`~gnr.app.gnrsqltable_proxy.selection.SelectionHandler.loadSavedQuery`
and :meth:`~gnr.app.gnrsqltable_proxy.selection.SelectionHandler.loadSavedView`
is a full override of ``getSelection``.  An override would also have to undo
two effects of the inherited prologue, which runs before the saved objects are
resolved: the fallback of ``limit`` to ``hardQueryLimit``, and the
``whereAsPlainText`` attribute, which the inherited flow adds only when the
caller itself passed a WHERE bag.  Both belong in ``get_selection.py``.

It is selected by the instance configuration ``<db app_handler="next"/>``, read
in the ``app`` property of :class:`gnr.web.gnrwebpage.GnrWebPage`.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler

__all__ = ['GnrWebAppHandlerNext']


class GnrWebAppHandlerNext(GnrWebAppHandler):
    """Web application handler delegating the table work to the table proxy.

    Only the methods that delegate are overridden; everything else is
    inherited from :class:`GnrWebAppHandler`.
    """

    # ------------------------------------------------------------------
    #  Page side services handed to the proxy
    # ------------------------------------------------------------------

    def _customSqlOpCallbacks(self) -> dict:
        """Return the ``customSqlOp_*`` callbacks defined on the page."""
        page = self.page
        return dict([(x[12:], getattr(page, x)) for x in dir(page)
                     if x.startswith('customSqlOp_')])

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
        return tblobj.selectionHandler().selectionColumns(columns, expressions=expr_dict)

    # ------------------------------------------------------------------
    #  Where bag, join conditions, external stores
    # ------------------------------------------------------------------

    def _decodeWhereBag(self, tblobj: Any, where: Any,
                        kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Delegate the where bag decoding to the table proxy."""
        return tblobj.selectionHandler().decodeWhereBag(
            where, kwargs, customOpCbDict=self._customSqlOpCallbacks())

    def _decodeJoinConditions(self, tblobj: Any, joinConditions: Any,
                              kwargs: dict) -> Union[dict, Any]:
        """Delegate the join condition decoding to the table proxy."""
        return tblobj.selectionHandler().decodeJoinConditions(joinConditions, kwargs)

    def _externalQueries(self, selection: Any = None,
                         external_queries: Optional[dict] = None) -> None:
        """Delegate the external store queries to the table proxy."""
        selection.dbtable.selectionHandler().externalQueries(
            selection=selection, external_queries=external_queries)

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
        selectionHandler = tblobj.selectionHandler()
        linkedSelectionKw = self._handleLinkedSelection(
            selectionName=selectionName) if selectionName else None
        where, kwargs = selectionHandler.selectionWhere(
            where=where, condition=condition, pkeys=pkeys,
            linkedSelectionKw=linkedSelectionKw,
            customOpCbDict=self._customSqlOpCallbacks(), kwargs=kwargs)
        if filteringPkeys and isinstance(filteringPkeys, str):
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
            where, kwargs = selectionHandler.filteringWhere(where, filteringPkeys, kwargs)
        if countOnly:
            return selectionHandler.countSelection(
                where=where, order_by=order_by, limit=limit, offset=offset,
                having=having, relationDict=relationDict, sqlparams=sqlparams,
                locale=self.page.locale, excludeLogicalDeleted=excludeLogicalDeleted,
                excludeDraft=excludeDraft, **kwargs)

        def applyContextJoins(query: Any) -> None:
            self._joinConditionsFromContext(query, sqlContextName)

        selection = selectionHandler.buildSelection(
            columns=columns, distinct=distinct, where=where, order_by=order_by,
            limit=limit, offset=offset, group_by=group_by, having=having,
            relationDict=relationDict, sqlparams=sqlparams, locale=self.page.locale,
            excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft,
            sortedBy=sortedBy, _aggregateRows=_aggregateRows,
            queryCb=applyContextJoins if sqlContextName else None, **kwargs)
        if queryMode in ('U', 'I', 'D'):
            selection = selectionHandler.queryModeSelection(
                selection=selection, queryMode=queryMode,
                frozenPkeys=self.page.freezedPkeys(tblobj, selectionName),
                columns=columns, distinct=distinct, order_by=order_by, limit=limit,
                offset=offset, group_by=group_by, having=having,
                relationDict=relationDict, sqlparams=sqlparams, locale=self.page.locale,
                excludeLogicalDeleted=excludeLogicalDeleted, excludeDraft=excludeDraft,
                sortedBy=sortedBy, _aggregateRows=_aggregateRows, **kwargs)
        return selection
