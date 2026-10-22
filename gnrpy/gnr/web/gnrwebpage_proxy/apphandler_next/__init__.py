# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next : Web application handler, the copy under work
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

"""Web application handler — the copy that receives new work.

This package is a full copy of ``gnr.web.gnrwebpage_proxy.apphandler``, not a
subclass of it: :class:`GnrWebAppHandlerNext` shares no code with
:class:`gnr.web.gnrwebpage_proxy.apphandler.GnrWebAppHandler`, and no module
of this package imports from that one.  The frozen package keeps serving the
instances that do not opt in; every refactoring lands here.

The experimental flag ``<experimental><db next_app_handler="True"/></experimental>``
selects this handler, read in the ``app`` property of
:class:`gnr.web.gnrwebpage.GnrWebPage`.

The ``getSelection`` flow is the one of phase 2, on the app level table proxy
``tblobj.selectionProxy()``; the other flows are still the copied ones and
are refactored one phase at a time.  The 17 methods that had no caller
anywhere in the tree are not part of the copy; they are listed in
``.subtasks/alt-apphandler/bugs.md``.
"""

from __future__ import annotations

from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy

# --- Mixin imports ---
from gnr.web.gnrwebpage_proxy.apphandler_next.get_selection import GetSelectionMixin
from gnr.web.gnrwebpage_proxy.apphandler_next.get_record import GetRecordMixin
from gnr.web.gnrwebpage_proxy.apphandler_next.related import RelatedMixin
from gnr.web.gnrwebpage_proxy.apphandler_next.db_select import DbSelectMixin
from gnr.web.gnrwebpage_proxy.apphandler_next.batch import BatchMixin, BatchExecutor
from gnr.web.gnrwebpage_proxy.apphandler_next.export import ExportMixin
from gnr.web.gnrwebpage_proxy.apphandler_next.structure import StructureMixin
from gnr.web.gnrwebpage_proxy.apphandler_next.misc import MiscMixin

__all__ = ['GnrWebAppHandlerNext', 'BatchExecutor']


class GnrWebAppHandlerNext(
    GetSelectionMixin,
    GetRecordMixin,
    RelatedMixin,
    DbSelectMixin,
    BatchMixin,
    ExportMixin,
    StructureMixin,
    MiscMixin,
    GnrBaseProxy,
):
    """Web application handler proxy.

    Assembled from domain-specific mixins, each providing one logical
    flow (e.g. ``getSelection``, ``getRecord``, ``dbSelect``).
    Core methods shared across multiple mixins are defined here.

    MRO order matters: mixins are listed before :class:`GnrBaseProxy`
    so that any method override in a mixin takes precedence.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self, **kwargs: Any) -> None:
        """Initialize the handler after proxy attachment.

        Sets ``self.gnrapp`` from the site's application instance.
        Called by :class:`GnrBaseProxy` machinery.
        """
        self.gnrapp = self.page.site.gnrapp

    def event_onEnd(self) -> None:
        """Handle proxy end-of-life event.

        Closes the database connection.  The frozen handler goes through a
        ``_finalize(page)`` method whose *page* parameter it ignores and whose
        only caller passes the proxy, not a page; nothing else in ``gnrpy``,
        ``projects`` or ``resources`` calls it, so the copy has no such method.
        """
        self.db.closeConnection()

    # ------------------------------------------------------------------
    # Database access
    # ------------------------------------------------------------------

    @property
    def db(self) -> Any:
        """Return the database connection from the page."""
        return self.page.db

    # ------------------------------------------------------------------
    # Shared methods (used by multiple mixins)
    # ------------------------------------------------------------------

    def _getSqlContextConditions(self, contextName: str,
                                 target_fld: Optional[str] = None,
                                 from_fld: Optional[str] = None) -> Optional[Any]:
        """Retrieve SQL context conditions from the page store.

        Args:
            contextName: Name of the SQL context.
            target_fld: When provided together with *from_fld*, narrow
                the result to the specific relation key.
            from_fld: See *target_fld*.

        Returns:
            A :class:`Bag` of conditions, a single condition entry, or
            ``None``.
        """
        result = self.page.pageStore().getItem('_sqlctx.conditions.%s' % contextName)
        if result and target_fld and from_fld:
            result = result[('%s_%s' % (target_fld, from_fld)).replace('.', '_')]
        return result

    def _joinConditionsFromContext(self, obj: Any, sqlContextName: str) -> None:
        """Apply join conditions from the named SQL context to *obj*.

        Reads all conditions stored in the page store for *sqlContextName*
        and calls ``obj.setJoinCondition`` for each.  Parameter values
        starting with ``^`` are resolved from the page store; values
        matching ``<contextName>_<value>`` are resolved as methods on
        ``self``.

        Args:
            obj: A query or record object supporting ``setJoinCondition``.
            sqlContextName: Name of the SQL context.
        """
        sqlContextBag = self._getSqlContextConditions(sqlContextName)
        storedata = self.page.pageStore().data
        if sqlContextBag:
            for joinBag in list(sqlContextBag.values()):
                if joinBag['condition']:  # may be a relatedcolumns only
                    params = (joinBag['params'] or Bag()).asDict(ascii=True)
                    for k, v in list(params.items()):
                        if isinstance(v, str):
                            if v.startswith('^'):
                                params[k] = storedata[v[1:]]
                            elif hasattr(self, '%s_%s' % (sqlContextName, v)):
                                params[k] = getattr(self, '%s_%s' % (sqlContextName, v))()
                    obj.setJoinCondition(target_fld=joinBag['target_fld'], from_fld=joinBag['from_fld'],
                                         condition=joinBag['condition'],
                                         one_one=joinBag['one_one'], **params)

    def _getApplyMethodPars(self, kwargs: dict[str, Any],
                            **optkwargs: Any) -> dict[str, Any]:
        """Extract ``apply_*`` parameters from *kwargs*.

        Collects all keys starting with ``apply_`` (stripping the prefix)
        and merges them with *optkwargs*.  Also propagates ``subtable``
        if present.

        Args:
            kwargs: The original keyword arguments.
            **optkwargs: Additional parameters to merge in.

        Returns:
            A dict of apply-method parameters.
        """
        result = dict([(k[6:], v) for k, v in list(kwargs.items()) if k.startswith('apply_')])
        if optkwargs:
            result.update(optkwargs)
        if kwargs.get('subtable'):
            result['subtable'] = kwargs['subtable']
        return result

    def _customSqlOpCallbacks(self) -> dict:
        """Return the ``customSqlOp_*`` callbacks defined on the page."""
        page = self.page
        return dict([(x[12:], getattr(page, x)) for x in dir(page)
                     if x.startswith('customSqlOp_')])

    def _decodeWhereBag(self, tblobj: Any, where: Any,
                        kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Delegate the where bag decoding to the table proxy.

        Defined in the class body, not in :mod:`get_selection`, because the
        class body wins over a mixin and the frozen package defines
        ``_decodeWhereBag`` here.  Four call sites outside this package use it
        as public API.
        """
        return tblobj.selectionProxy().decodeWhereBag(
            where, kwargs, customOpCbDict=self._customSqlOpCallbacks())
