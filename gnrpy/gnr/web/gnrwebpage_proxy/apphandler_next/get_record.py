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

"""Record loading mixin — the copy that receives new work.

Provides :class:`GetRecordMixin` — the ``getRecord`` public-method flow
and its private helpers for lock management, eager relation expansion
and default value population.

The module of the same name under ``gnr.web.gnrwebpage_proxy.apphandler`` is
frozen and is never imported from here.  The method bodies are the ones of
that module; what differs is a block that needs only the table and the
database, replaced by one call on the table proxy ``tblobj.recordHandler()``
(:class:`gnr.app.gnrsqltable_proxy.record.RecordHandler`), and a recorded
defect fix, marked in place with its ``bugs.md`` number.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from gnr.core.gnrdecorator import public_method, extract_kwargs

__all__ = ['GetRecordMixin']


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
            SMELL: The lock call is commented out and ``locked`` is
            hard-coded to ``False``, meaning this method is effectively
            a no-op.  The surrounding loop ``for f in aux`` iterates
            over an empty list.  The entire locking mechanism appears
            to be disabled.  The body is kept because it is the only
            trace of the disabled record locking; removing it would
            remove that trace without changing any behaviour.
        """
        # locked, aux = self.page.site.lockRecord(
        #     self.page, tblobj.fullname, record[tblobj.pkey])
        locked = False  # SMELL: lock disabled — always False
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
            default_kwargs: Default values for new records (extracted by
                ``@extract_kwargs(default=True)``).
            eager: Eager-loading specification.
            virtual_columns: Comma-separated virtual columns to include.
            _storename: Alternate store name.
            _resolver_kwargs: Extra resolver parameters.
            _eager_level: Current nesting depth for eager expansion.
            _eager_record_stack: Stack of parent records (cycle guard).
            onLoadingHandler: Explicit onLoading handler name.
            sample_kwargs: Parameters for sample-data generation
                (extracted by ``@extract_kwargs(sample=True)``).
            ignoreReadOnly: Override read-only checks.

        Returns:
            A ``(record_bag, recInfo_dict)`` tuple.

        Note:
            SMELL: The method accepts ~30 parameters, many of which are
            internal bookkeeping (``_eager_level``, ``_eager_record_stack``,
            ``_resolver_kwargs``).  These should arguably travel via a
            context object rather than explicit keyword arguments.

            SMELL: ``_resolver_kwargs`` is accepted but never used inside
            this method — it is consumed only by ``_handleEagerRelations``
            indirectly through ``getRelatedRecord``.
        """
        t = time.time()
        dbtable = dbtable or table
        if pkg:
            dbtable = '%s.%s' % (pkg, dbtable)
        tblobj = self.db.table(dbtable)
        recordHandler = tblobj.recordHandler()
        if pkey is None and lock:
            lock = False
        default_kwargs = default_kwargs or {}
        rec = recordHandler.loadRecord(pkey=pkey, lock=lock,
                                       eager=eager or self.page.eagers.get(dbtable),
                                       ignoreMissing=ignoreMissing, ignoreDuplicate=ignoreDuplicate,
                                       sqlContextName=sqlContextName, virtual_columns=virtual_columns,
                                       _storename=_storename, **kwargs)
        if sqlContextName:
            self._joinConditionsFromContext(rec, sqlContextName)
        record = recordHandler.recordToBag(rec, pkey, js_resolver_one, js_resolver_many,
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
            recInfo.update(recordHandler.readProtectionFlags(record, ignoreReadOnly=ignoreReadOnly))
            if lock:
                self._getRecord_locked(tblobj, record, recInfo)
        loadingParameters = loadingParameters or {}
        loadingParameters.update(default_kwargs)
        if _eager_record_stack:
            loadingParameters['_eager_record_stack'] = _eager_record_stack
        method = None
        table_onLoading = recordHandler.findTableOnLoading()
        if table_onLoading:
            table_onLoading(record, newrecord, loadingParameters, recInfo)
        table_onloading_handlers = recordHandler.listTableLoadingHandlers()
        onLoadingHandler = onLoadingHandler or loadingParameters.pop('method', None)
        if onLoadingHandler:
            handler = self.page.getPublicMethod('rpc', onLoadingHandler)
        else:
            if dbtable == self.page.maintable:
                method = 'onLoading'  # TODO: fall back on the next case if onLoading is missing?
            else:
                method = self.page.onLoadingRelatedMethod(dbtable, sqlContextName=sqlContextName)
            handler = getattr(self.page, method, None)

        if handler or table_onloading_handlers:
            if default_kwargs and newrecord:
                self.setRecordDefaults(tblobj, record, default_kwargs)
            for h in table_onloading_handlers:
                h(record, newrecord, loadingParameters, recInfo)
            if handler:
                handler(record, newrecord, loadingParameters, recInfo)
        elif newrecord and loadingParameters:
            for k in default_kwargs:
                if k not in record:
                    record[k] = None
            self.setRecordDefaults(tblobj, record, loadingParameters)

        if applymethod:
            applyPars = self._getApplyMethodPars(kwargs, newrecord=newrecord, loadingParameters=loadingParameters,
                                                 recInfo=recInfo, tblobj=tblobj)
            applyresult = self.page.getPublicMethod('rpc', applymethod)(record, **applyPars)
            if applyresult:
                recInfo.update(applyresult)

        recInfo['servertime'] = int((time.time() - t) * 1000)
        recInfo.update(recordHandler.readRecordStatus(record))
        recInfo['table'] = dbtable
        _eager_record_stack = _eager_record_stack or []
        self._handleEagerRelations(record, _eager_level, _eager_record_stack=_eager_record_stack)
        if newrecord and not recInfo.get('from_fld'):
            recordHandler.applyCounters(record, recInfo)
        recInfo['caption'] = tblobj.recordCaption(record, newrecord)
        return (record, recInfo)

    # ------------------------------------------------------------------
    # Eager relation expansion
    # ------------------------------------------------------------------

    def _handleEagerRelations(self, record: Any, _eager_level: int,
                              _eager_record_stack: Optional[list] = None) -> None:
        """Expand eagerly-loaded one-to-one relations in *record*.

        Walks every node of the record :class:`Bag`; when a node carries
        an ``_eager_one`` attribute it replaces the lazy resolver with
        the fully loaded related record (via ``self.getRelatedRecord``).

        Args:
            record: The record :class:`Bag` to scan.
            _eager_level: Current nesting depth (incremented on recursion).
            _eager_record_stack: Stack of ancestor records to prevent
                infinite cycles.

        Note:
            SMELL: The method mutates the *record* in-place by setting
            ``n._resolver = None`` to disable the lazy resolver and then
            replacing ``n.value``.  This side-effect-heavy approach makes
            the method hard to test in isolation.

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
                kwargs = {}
                resolver_kwargs = attr.get('_resolver_kwargs') or dict()
                for k, v in list(resolver_kwargs.items()):
                    if str(v).startswith('='):
                        v = v[1:]
                        resolver_kwargs[k] = record.get(v[1:]) if v.startswith('.') else None
                kwargs['resolver_kwargs'] = resolver_kwargs
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

    # ------------------------------------------------------------------
    # Default value population
    # ------------------------------------------------------------------

    def setRecordDefaults(self, tblobj: Any, record: Any,
                          defaults: dict[str, Any]) -> None:
        """Populate a new record with default values.

        Only sets keys that already exist in the record schema.  After
        explicit defaults are applied, ``tblobj.extendDefaultValues``
        is called for model-level defaults.

        Args:
            tblobj: The table object.
            record: The record :class:`Bag` to populate.
            defaults: Mapping of field-name → default-value.
        """
        tblobj.recordHandler().setRecordDefaults(record, defaults)
