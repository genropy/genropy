# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.get_record : Record loading flow
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

"""Record loading mixin.

Provides :class:`GetRecordMixin` — the ``getRecord`` public method flow and
its helpers.

The table level part lives on the app level table proxy
``tblobj.recordHandler()`` (:class:`gnr.app.gnrsqltable_proxy.record.RecordHandler`):
the record query, the output mode, the pkey re-derivation, the protection
flags, the table ``onLoading`` handlers, the default values, the status keys
and the counters.  What stays here is what needs the page: the eager
specification read from ``page.eagers``, the SQL context join conditions, the
resolution of the page side ``onLoading`` handler, the applymethod, the
``recInfo`` assembly and the eager relation expansion, which recurses into
``getRelatedRecord``.

This module is the copy that receives new work.  The module of the same name
under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never imported
from here.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from gnr.core.gnrdecorator import public_method, extract_kwargs


class GetRecordMixin:
    """Mixin for the ``getRecord`` flow.

    Loads a single database record by primary key, applies locking,
    protection flags, onLoading handlers, eager relation expansion,
    counter-column sequences and caption computation.

    Cross-mixin dependencies (resolved via ``self`` in the assembled
    class's MRO):

    * ``_joinConditionsFromContext`` — from ``__init__.py``
    * ``_getApplyMethodPars`` — from ``__init__.py``
    * ``getRelatedRecord`` — from ``related.py``
    """

    # ------------------------------------------------------------------
    # Lock helper
    # ------------------------------------------------------------------

    def _getRecord_locked(self, tblobj: Any, record: Any,
                          recInfo: dict[str, Any]) -> None:
        """Check and record locking information on a record.

        Args:
            tblobj: The table object.
            record: The loaded record.
            recInfo: Mutable dict of record metadata; updated with
                ``lockId`` and ``locking_*`` keys when locked.

        Note:
            The whole body is inert and has been for as long as the history
            goes back: the ``site.lockRecord`` call is commented out, so
            ``locked`` is the literal ``False`` and ``aux`` the empty list,
            and neither the early return nor the loop can run.  It is kept
            because it is the only trace of the disabled record locking, and
            removing it would remove that trace without changing anything.
            Recorded in ``.subtasks/alt-apphandler/bugs.md``.
        """
        # locked, aux = self.page.site.lockRecord(
        #     self.page, tblobj.fullname, record[tblobj.pkey])
        locked = False
        aux = []
        if locked:
            recInfo['lockId'] = aux
            return
        for f in aux:
            recInfo['locking_%s' % f] = aux[f]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    @public_method
    @extract_kwargs(default=True, sample=True)
    def getRecord(self, table: Optional[str] = None,
                  dbtable: Optional[str] = None,
                  pkg: Optional[str] = None,
                  pkey: Optional[str] = None,
                  ignoreMissing: bool = True,
                  ignoreDuplicate: bool = True,
                  lock: bool = False,
                  readOnly: bool = False,
                  from_fld: Optional[str] = None,
                  target_fld: Optional[str] = None,
                  sqlContextName: Optional[str] = None,
                  applymethod: Optional[str] = None,
                  js_resolver_one: str = 'relOneResolver',
                  js_resolver_many: str = 'relManyResolver',
                  loadingParameters: Optional[dict] = None,
                  default_kwargs: Optional[dict] = None,
                  eager: Optional[str] = None,
                  virtual_columns: Optional[str] = None,
                  _storename: Optional[str] = None,
                  _resolver_kwargs: Optional[dict] = None,
                  _eager_level: int = 0,
                  _eager_record_stack: Optional[list] = None,
                  onLoadingHandler: Optional[str] = None,
                  sample_kwargs: Optional[dict] = None,
                  ignoreReadOnly: Optional[bool] = None,
                  **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        """Load a single record by primary key.

        This is the main RPC entry point for client-side record loading.
        It handles new-record creation, record locking, protection flags,
        ``onLoading`` callbacks, ``applymethod`` post-processing, eager
        relation expansion and counter-column sequences.

        Args:
            table: Logical table name (``"pkg.table"``).
            dbtable: Physical table name; defaults to *table*.
            pkg: Package prefix — prepended to *dbtable* when set.
            pkey: Primary key.  ``"*newrecord*"`` creates a blank record,
                ``"*sample*"`` returns sample data.
            ignoreMissing: Silently return empty on missing record.
            ignoreDuplicate: Silently return first on duplicate.
            lock: Acquire a row lock (``FOR UPDATE``).
            readOnly: When ``True`` skip write/delete protection checks.
            from_fld: Source field for related-record context.
            target_fld: Target field for related-record context.
            sqlContextName: Named SQL context for join conditions.
            applymethod: Page method called after loading to post-process
                the record.
            js_resolver_one: Client-side resolver for one-to-one relations.
            js_resolver_many: Client-side resolver for one-to-many relations.
            loadingParameters: Extra parameters forwarded to ``onLoading``.
                Mutated in place: the defaults are merged into it and its
                ``method`` key is popped.
            default_kwargs: Default values for new records (extracted by
                ``@extract_kwargs(default=True)``).
            eager: Eager-loading specification.
            virtual_columns: Comma-separated virtual columns to include.
            _storename: Alternate store name.
            _resolver_kwargs: Accepted and never read.  The client sends it on
                every ``relOneResolver`` call, and the named parameter keeps it
                out of the keywords that reach the record query.
            _eager_level: Current nesting depth for eager expansion.
            _eager_record_stack: Stack of parent records (cycle guard).
            onLoadingHandler: Explicit onLoading handler name.
            sample_kwargs: Parameters for sample-data generation
                (extracted by ``@extract_kwargs(sample=True)``).
            ignoreReadOnly: Override read-only checks.

        Returns:
            A ``(record_bag, recInfo_dict)`` tuple.

        Note:
            The ordering of three steps is load bearing and must not be
            rearranged.  ``recInfo['table']`` holds the *logical* table while
            every handler runs and becomes ``dbtable`` only afterwards, so the
            handlers see one name and the client another.  The table
            ``onLoading`` runs before the default values and the
            ``onLoading_*`` ones after them.  The applymethod result is merged
            before the status keys and the caption, so it cannot override
            them.
        """
        t = time.time()
        dbtable = dbtable or table
        if pkg:
            dbtable = '%s.%s' % (pkg, dbtable)
        tblobj = self.db.table(dbtable)
        recordHandler = tblobj.recordHandler()
        lock = bool(lock and pkey is not None)
        default_kwargs = default_kwargs or {}

        rec = recordHandler.loadRecord(
            pkey=pkey, lock=lock,
            eager=eager or self.page.eagers.get(dbtable),
            virtual_columns=virtual_columns, sqlContextName=sqlContextName,
            _storename=_storename, ignoreMissing=ignoreMissing,
            ignoreDuplicate=ignoreDuplicate, **kwargs)
        if sqlContextName:
            self._joinConditionsFromContext(rec, sqlContextName)
        record = recordHandler.outputRecord(rec, pkey, js_resolver_one,
                                            js_resolver_many,
                                            sample_kwargs=sample_kwargs)
        if pkey == '*sample*':
            return record, dict(_pkey=pkey, caption='!!Sample data')

        pkey, newrecord = recordHandler.resolvePkey(record, pkey, default_kwargs)
        recInfo = dict(_pkey=pkey,
                       _newrecord=newrecord,
                       sqlContextName=sqlContextName, _storename=_storename,
                       from_fld=from_fld, ignoreReadOnly=ignoreReadOnly,
                       table=table)
        if not newrecord and not readOnly:
            recInfo.update(recordHandler.protectionFlags(
                record, ignoreReadOnly=ignoreReadOnly))
            if lock:
                self._getRecord_locked(tblobj, record, recInfo)

        loadingParameters = loadingParameters or {}
        loadingParameters.update(default_kwargs)
        if _eager_record_stack:
            loadingParameters['_eager_record_stack'] = _eager_record_stack
        table_onLoading = recordHandler.tableOnLoading()
        if table_onLoading:
            table_onLoading(record, newrecord, loadingParameters, recInfo)
        table_handlers = recordHandler.tableLoadingHandlers()
        handler = self._onLoadingHandler(dbtable, onLoadingHandler,
                                         loadingParameters, sqlContextName)
        self._applyLoadingHandlers(recordHandler, record, recInfo, handler,
                                   table_handlers, newrecord=newrecord,
                                   default_kwargs=default_kwargs,
                                   loadingParameters=loadingParameters)

        if applymethod:
            applyPars = self._getApplyMethodPars(kwargs, newrecord=newrecord,
                                                 loadingParameters=loadingParameters,
                                                 recInfo=recInfo, tblobj=tblobj)
            applyresult = self.page.getPublicMethod('rpc', applymethod)(record, **applyPars)
            if applyresult:
                recInfo.update(applyresult)

        recInfo['servertime'] = int((time.time() - t) * 1000)
        recInfo.update(recordHandler.recordStatus(record))
        recInfo['table'] = dbtable
        _eager_record_stack = _eager_record_stack or []
        self._handleEagerRelations(record, _eager_level,
                                   _eager_record_stack=_eager_record_stack)
        if newrecord and not recInfo.get('from_fld'):
            recordHandler.applyCounters(record, recInfo)
        recInfo['caption'] = tblobj.recordCaption(record, newrecord)
        return (record, recInfo)

    # ------------------------------------------------------------------
    # onLoading handlers and default values
    # ------------------------------------------------------------------

    def _onLoadingHandler(self, dbtable: str, onLoadingHandler: Optional[str],
                          loadingParameters: dict,
                          sqlContextName: Optional[str]) -> Optional[Callable]:
        """Resolve the page side ``onLoading`` handler of a record.

        An explicit handler name wins, and the ``method`` key of
        *loadingParameters* is the fallback name — it is popped out of the
        caller's dict, as the legacy flow does.  With no name at all the
        maintable uses ``onLoading`` and every other table the name
        ``page.onLoadingRelatedMethod`` builds.

        Returns:
            The bound page method, or ``None`` when the page has not got it.
        """
        onLoadingHandler = onLoadingHandler or loadingParameters.pop('method', None)
        if onLoadingHandler:
            return self.page.getPublicMethod('rpc', onLoadingHandler)
        if dbtable == self.page.maintable:
            # TODO: fall back on the next case if onLoading is missing?
            method = 'onLoading'
        else:
            method = self.page.onLoadingRelatedMethod(dbtable,
                                                      sqlContextName=sqlContextName)
        return getattr(self.page, method, None)

    def _applyLoadingHandlers(self, recordHandler: Any, record: Any,
                              recInfo: dict, handler: Optional[Callable],
                              table_handlers: list, newrecord: bool = False,
                              default_kwargs: Optional[dict] = None,
                              loadingParameters: Optional[dict] = None) -> None:
        """Apply the default values and run the loading handlers.

        The two branches use two different dictionaries on purpose.  With at
        least one handler the defaults are the ``default_*`` keywords only,
        and only for a new record; with no handler at all they are
        *loadingParameters*, which already carries the ``default_*`` ones, and
        every default key the record has not got is first seeded with ``None``
        so that ``setRecordDefaults``, which skips absent keys, can write it.
        """
        if handler or table_handlers:
            if default_kwargs and newrecord:
                recordHandler.setRecordDefaults(record, default_kwargs)
            for table_handler in table_handlers:
                table_handler(record, newrecord, loadingParameters, recInfo)
            if handler:
                handler(record, newrecord, loadingParameters, recInfo)
        elif newrecord and loadingParameters:
            for key in default_kwargs:
                if key not in record:
                    record[key] = None
            recordHandler.setRecordDefaults(record, loadingParameters)

    def setRecordDefaults(self, tblobj: Any, record: Any,
                          defaults: dict[str, Any]) -> None:
        """Delegate the default values to the table proxy.

        The name stays on the handler: it is the one the legacy flow exposes.
        """
        tblobj.recordHandler().setRecordDefaults(record, defaults)

    # ------------------------------------------------------------------
    # Eager relation expansion
    # ------------------------------------------------------------------

    def _handleEagerRelations(self, record: Any, _eager_level: int,
                              _eager_record_stack: Optional[list] = None) -> None:
        """Expand eagerly-loaded one-to-one relations in *record*.

        Walks every node of the record :class:`Bag`; when a node carries
        an ``_eager_one`` attribute it replaces the lazy resolver with
        the fully loaded related record (via ``self.getRelatedRecord``).

        The expansion stays on the handler because ``getRelatedRecord`` is a
        ``@public_method`` a page may override, and because it mutates the
        record in place: ``n._resolver`` is cleared, ``n.value`` becomes the
        related record and ``n.attr['_resolvedInfo']`` its recInfo.

        Args:
            record: The record :class:`Bag` to scan.
            _eager_level: Current nesting depth (incremented on recursion).
            _eager_record_stack: Stack of ancestor records to prevent
                infinite cycles.

        Note:
            REVIEW: The ``_eager_one == 'weak'`` guard only fires at
            level 0.  It is unclear why level 1+ eager-weak relations
            should be skipped — this may prevent legitimate nested eager
            loading.
        """
        for n in record.nodes:
            _eager_one = n.attr.get('_eager_one')
            if _eager_one is True or (_eager_one == 'weak' and _eager_level == 0):
                n._resolver = None
                attr = n.attr
                target_fld = str(attr['_target_fld'])
                kwargs = {'resolver_kwargs': self._eagerResolverKwargs(
                    record, attr.get('_resolver_kwargs'))}
                kwargs[target_fld.split('.')[2]] = record[attr['_auto_relation_value']]
                relatedRecord, relatedInfo = self.getRelatedRecord(
                    from_fld=attr['_from_fld'], target_fld=target_fld,
                    sqlContextName=attr.get('_sqlContextName'),
                    virtual_columns=attr.get('_virtual_columns'),
                    _eager_level=_eager_level + 1, _storename=attr.get('_storename'),
                    _eager_record_stack=[record] + _eager_record_stack,
                    **kwargs)
                n.value = relatedRecord
                n.attr['_resolvedInfo'] = relatedInfo

    def _eagerResolverKwargs(self, record: Any,
                             resolver_kwargs: Optional[dict]) -> dict:
        """Resolve the ``=`` prefixed resolver parameters of an eager node.

        ``'=.field'`` is read from the record being expanded.  ``'=path'``
        without the dot is a client datastore path, which the server has not
        got, so it becomes ``None`` — the client resolves that form itself.
        Everything else passes through.  The dict of the node is updated in
        place, as the legacy flow does.
        """
        resolver_kwargs = resolver_kwargs or dict()
        for k, v in list(resolver_kwargs.items()):
            if str(v).startswith('='):
                v = v[1:]
                resolver_kwargs[k] = record.get(v[1:]) if v.startswith('.') else None
        return resolver_kwargs
