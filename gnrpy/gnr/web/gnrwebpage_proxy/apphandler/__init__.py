# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler : Web application handler (sub-package)
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

"""Web application handler — assembled class and core methods.

This package replaces the former monolithic ``apphandler.py`` module.
The public API is unchanged::

    from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler
    from gnr.web.gnrwebpage_proxy.apphandler import BatchExecutor

:class:`GnrWebAppHandler` is composed via mixins — one per logical
flow — plus :class:`GnrBaseProxy` as the base.  Core / shared methods
that are used by multiple mixins live directly in this file.
"""

from __future__ import annotations

from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy

# --- Mixin imports ---
from gnr.web.gnrwebpage_proxy.apphandler.get_selection import GetSelectionMixin
from gnr.web.gnrwebpage_proxy.apphandler.get_record import GetRecordMixin
from gnr.web.gnrwebpage_proxy.apphandler.related import RelatedMixin
from gnr.web.gnrwebpage_proxy.apphandler.db_select import DbSelectMixin
from gnr.web.gnrwebpage_proxy.apphandler.batch import BatchMixin, BatchExecutor
from gnr.web.gnrwebpage_proxy.apphandler.export import ExportMixin
from gnr.web.gnrwebpage_proxy.apphandler.structure import StructureMixin
from gnr.web.gnrwebpage_proxy.apphandler.misc import MiscMixin

# Re-export BatchExecutor for backward compatibility
__all__ = ['GnrWebAppHandler', 'BatchExecutor']


class GnrWebAppHandler(
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

        Closes the database connection.
        """
        self._finalize(self)

    def _finalize(self, page: Any) -> None:
        """Close the database connection.

        Args:
            page: Unused — kept for signature compatibility.

        Note:
            SMELL: The *page* parameter is accepted but never used;
            the method always operates on ``self.db``.  The call site
            passes ``self`` as *page* which is the proxy, not the page.
        """
        self.db.closeConnection()

    # ------------------------------------------------------------------
    # Database access
    # ------------------------------------------------------------------

    @property
    def db(self) -> Any:
        """Return the database connection from the page."""
        return self.page.db

    def getDb(self, dbId: Optional[str] = None) -> Any:
        """Return the database connection.

        Args:
            dbId: Ignored — kept for backward compatibility with
                ``DataResolver.__getitem__`` protocol.

        Returns:
            The database connection (same as ``self.db``).

        Note:
            SMELL: *dbId* is accepted but never used.  The original
            comment says "is a __getitem__ for back compatibility".
        """
        return self.db

    __getitem__ = getDb

    # ------------------------------------------------------------------
    # Application identity
    # ------------------------------------------------------------------

    def _getAppId(self) -> str:
        """Resolve the application identifier from the site config.

        Returns:
            The application instance name.

        Note:
            BUG: ``self.page.request.uri.split['/']`` uses ``[]``
            (subscript on the *method object*) instead of ``()``
            (calling the method).  Should be ``.split('/')[2]``.

            SMELL: Caches to ``self._appId`` using ``hasattr`` check
            instead of a sentinel — ``hasattr`` can mask other
            ``AttributeError`` exceptions.
        """
        if not hasattr(self, '_appId'):
            instances = list(self.page.site.config['instances'].keys())
            if len(instances) == 1:
                self._appId = instances[0]
            else:
                self._appId = self.page.request.uri.split['/'][2]  # BUG: .split['/'] → .split('/')
                if not self._appId in instances:  # SMELL: ``not x in y`` → ``x not in y``
                    self._appId = instances[0]
        return self._appId

    appId = property(_getAppId)

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

    def _decodeWhereBag(self, tblobj: Any, where: Any,
                        kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Decode a :class:`Bag`-encoded WHERE clause into SQL.

        Optionally prepends a ``currentFilter`` wrapper.  Delegates to
        ``tblobj.sqlWhereFromBag`` with custom operator callbacks
        discovered from the page.

        Args:
            tblobj: The table object.
            where: A :class:`Bag` encoding the WHERE conditions.
            kwargs: Mutable dict — ``currentFilter`` is popped if present;
                additional SQL params may be added by ``sqlWhereFromBag``.

        Returns:
            A ``(sql_where_string, updated_kwargs)`` tuple.
        """
        currentFilter = kwargs.pop('currentFilter', None)
        if currentFilter:
            new_where = Bag()
            new_where.setItem('filter', currentFilter)
            new_where.setItem('where', where, jc='and')
            where = new_where
        page = self.page
        customOpCbDict = dict([(x[12:], getattr(page, x)) for x in dir(page) if x.startswith('customSqlOp_')])
        return tblobj.sqlWhereFromBag(where, kwargs, customOpCbDict=customOpCbDict)
