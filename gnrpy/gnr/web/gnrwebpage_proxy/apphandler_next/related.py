# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.related : Related record and selection loading
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

"""Related record and selection mixin — the copy that receives new work.

Provides :class:`RelatedMixin` — the ``getRelatedRecord`` and
``getRelatedSelection`` public-method flows.  Both are called from
the client-side resolver mechanism to load linked data.

The module of the same name under ``gnr.web.gnrwebpage_proxy.apphandler`` is
frozen and is never imported from here.  The method bodies are the ones of
that module; what differs is a block that needs only the table and the
database, replaced by one call on the table proxy ``tblobj.recordProxy()``
(:class:`gnr.app.gnrsqltable_proxy.record.RecordProxy`), a recorded defect
fix marked in place with its ``bugs.md`` number, and the two helpers the two
flows share, ``_splitTargetFld`` and ``_sqlContextJoinBag``.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import toJson

logger = logging.getLogger('gnr.web.apphandler.related')

__all__ = ['RelatedMixin']


class RelatedMixin:
    """Mixin for related-record and related-selection loading.

    Cross-mixin dependencies (resolved via ``self`` in the assembled
    class's MRO):

    * ``getRecord`` — from ``get_record.py``
    * ``_getSqlContextConditions`` — from ``__init__.py``
    * ``_joinConditionsFromContext`` — from ``__init__.py``
    * ``_getApplyMethodPars`` — from ``__init__.py``
    """

    # ------------------------------------------------------------------
    # Related record
    # ------------------------------------------------------------------

    @public_method
    def getRelatedRecord(self, from_fld: Optional[str] = None,
                         target_fld: Optional[str] = None,
                         pkg: Optional[str] = None,
                         pkey: Optional[str] = None,
                         ignoreMissing: bool = True,
                         ignoreDuplicate: bool = True,
                         js_resolver_one: str = 'relOneResolver',
                         js_resolver_many: str = 'relManyResolver',
                         sqlContextName: Optional[str] = None,
                         virtual_columns: Optional[str] = None,
                         _eager_level: int = 0,
                         _eager_record_stack: Optional[list] = None,
                         _storename: Optional[str] = None,
                         resolver_kwargs: Optional[dict] = None,
                         loadingParameters: Optional[dict] = None,
                         _debug_info: Optional[str] = None,
                         **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        """Load a record from a related table.

        Derives the target table and field from *target_fld* (which is in
        ``"pkg.table.field"`` format), then delegates to ``self.getRecord``.
        When the source pkey is missing or empty the record is created as
        ``*newrecord*``.

        Args:
            from_fld: Fully qualified source field (``"pkg.table.field"``).
            target_fld: Fully qualified target field (``"pkg.table.field"``).
            pkg: Package prefix.
            pkey: Explicit primary key of the related record.
            ignoreMissing: Silently return empty on missing record.
            ignoreDuplicate: Silently return first on duplicate.
            js_resolver_one: Client-side resolver for one-to-one.
            js_resolver_many: Client-side resolver for one-to-many.
            sqlContextName: Named SQL context for join conditions.
            virtual_columns: Comma-separated virtual columns.
            _eager_level: Current nesting depth for eager expansion.
            _eager_record_stack: Stack of ancestor records.
            _storename: Alternate store name.
            resolver_kwargs: Extra parameters merged into loading params.
            loadingParameters: Extra parameters forwarded to ``getRecord``.
            _debug_info: Optional debug annotation (unused in logic).

        Returns:
            A ``(record_bag, recInfo_dict)`` tuple (from ``getRecord``).

        Note:
            SMELL: The condition ``not related_field in kwargs`` uses
            ``not x in y`` instead of the more readable ``x not in y``.

            REVIEW: When *pkey* is ``None`` **and** the related field is
            not in *kwargs*, the method forces ``pkey = '*newrecord*'``.
            This means that any missing FK silently produces a blank
            record instead of raising an error, which can mask data
            integrity issues.
        """
        table, related_field = self._splitTargetFld(target_fld)
        pkey = self.db.table(table).recordProxy().resolveRelatedPkey(pkey, related_field, kwargs)
        loadingParameters = loadingParameters or dict()
        loadingParameters.update(resolver_kwargs or dict())
        record, recInfo = self.getRecord(table=table, from_fld=from_fld, target_fld=target_fld, pkey=pkey,
                                         ignoreMissing=ignoreMissing, ignoreDuplicate=ignoreDuplicate,
                                         js_resolver_one=js_resolver_one, js_resolver_many=js_resolver_many,
                                         sqlContextName=sqlContextName, virtual_columns=virtual_columns,
                                         _storename=_storename,
                                         _eager_level=_eager_level, _eager_record_stack=_eager_record_stack,
                                         loadingParameters=loadingParameters, **kwargs)

        joinBag = self._sqlContextJoinBag(sqlContextName, target_fld, from_fld)
        if joinBag and joinBag['applymethod']:
            applyPars = self._getApplyMethodPars(kwargs)
            self.page.getPublicMethod('rpc', joinBag['applymethod'])(record, **applyPars)
        return (record, recInfo)

    # ------------------------------------------------------------------
    # Related selection
    # ------------------------------------------------------------------

    @public_method
    def getRelatedSelection(self, from_fld: str, target_fld: str,
                            relation_value: Optional[Any] = None,
                            columns: str = '',
                            query_columns: Optional[str] = None,
                            condition: Optional[str] = None,
                            js_resolver_one: str = 'relOneResolver',
                            sqlContextName: Optional[str] = None,
                            **kwargs: Any) -> tuple[Bag, dict[str, Any]]:
        """Load a selection of related records.

        Executes a ``relatedQuery`` on the target table, filtering by
        *relation_value* on the *target_fld* field.

        Args:
            from_fld: Fully qualified source field.
            target_fld: Fully qualified target field (``"pkg.table.field"``).
            relation_value: The FK value to filter on.
            columns: Columns to include.
            query_columns: Deprecated alias for *columns*.
            condition: Additional WHERE clause.
            js_resolver_one: Client-side resolver for one-to-one.
            sqlContextName: Named SQL context for join conditions.

        Returns:
            A ``(result_bag, resultAttributes_dict)`` tuple.

        Note:
            bugs.md D2: the frozen module sets ``joinBag`` back to ``None``
            after filling it, so its ``applymethod`` branch is dead code and
            the applymethod of a SQL context join condition is silently
            skipped on this side of the relation while the ``getRelatedRecord``
            side runs it.  Here the join condition is read once and kept.

            bugs.md D19: *columns* and *query_columns* never reach
            ``relatedQuery``, so the selection always carries the default
            columns of the table.  The behaviour is reproduced; the three dead
            assignments are dropped.

            SMELL: ``getattr(self, 'self.newprocess', 'no')`` uses a dotted
            string as an attribute name — it never matches a real attribute
            and always returns ``'no'`` (bugs.md D3, reproduced).
        """
        if query_columns:
            logger.error('QUERY COLUMNS PARAMETER NOT EXPECTED!!')
        t = time.time()
        resultAttributes = dict()
        joinBag = self._sqlContextJoinBag(sqlContextName, target_fld, from_fld)
        dbtable, related_field = self._splitTargetFld(target_fld)
        recordProxy = self.db.table(dbtable).recordProxy()

        sel = recordProxy.selectRelatedRecords(related_field, from_fld, target_fld,
                                             relation_value=relation_value, condition=condition,
                                             sqlContextName=sqlContextName,
                                             queryCb=lambda query: self._joinConditionsFromContext(
                                                 query, sqlContextName),
                                             **kwargs)
        if joinBag and joinBag.get('applymethod'):
            applyPars = self._getApplyMethodPars(kwargs)
            applyresult = self.page.getPublicMethod('rpc', joinBag['applymethod'])(sel, **applyPars)
            if applyresult:
                resultAttributes.update(applyresult)

        result, relOneParams = recordProxy.relatedRecordsToBag(sel, js_resolver_one,
                                                            sqlContextName=sqlContextName)
        resultAttributes.update(dbtable=dbtable, totalrows=len(sel))
        resultAttributes.update({
            'servertime': int((time.time() - t) * 1000),
            'newproc': getattr(self, 'self.newprocess', 'no'),  # SMELL: dotted attr name — always 'no'
            'childResolverParams': '%s::JS' % toJson(relOneParams)
        })

        return (result, resultAttributes)

    # ------------------------------------------------------------------
    # Blocks the two flows share
    # ------------------------------------------------------------------

    def _splitTargetFld(self, target_fld: str) -> tuple[str, str]:
        """Split ``pkg.table.field`` into the table name and the field name.

        Called by :meth:`getRelatedRecord` and by :meth:`getRelatedSelection`.
        """
        pkg, tbl, related_field = target_fld.split('.')
        return '%s.%s' % (pkg, tbl), related_field

    def _sqlContextJoinBag(self, sqlContextName: Optional[str],
                           target_fld: str, from_fld: str) -> Optional[Any]:
        """The join condition of one relation inside a SQL context, or ``None``.

        Called by :meth:`getRelatedRecord` and by :meth:`getRelatedSelection`.
        """
        if not sqlContextName:
            return None
        return self._getSqlContextConditions(sqlContextName, target_fld=target_fld,
                                             from_fld=from_fld)
