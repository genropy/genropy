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

"""Related record and selection mixin.

Provides :class:`RelatedMixin` — the ``getRelatedRecord`` and
``getRelatedSelection`` public method flows.  Both serve the client side
relation resolvers: ``relOneResolver`` calls the first, ``relManyResolver``
the second (``gnrjs/gnr_d11/js/genro_rpc.js:880,962``).

The table level part lives on the app level table proxy
``tblobj.recordHandler()``: the pkey of a related record, the related query
with its join condition re-application, and the rows Bag.  What stays here is
the SQL context lookup, the applymethods and the result attributes, which are
client protocol.

This module is the copy that receives new work.  The module of the same name
under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never imported
from here.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import toJson

logger = logging.getLogger('gnr.web.apphandler.related')


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
            pkg: Accepted and never read: the package comes from *target_fld*.
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
            _debug_info: Accepted and never read.  The client sends it on
                every ``relOneResolver`` call.

        Returns:
            A ``(record_bag, recInfo_dict)`` tuple (from ``getRecord``).

        Note:
            A missing foreign key silently produces a blank record instead of
            raising, which can mask a data integrity problem.
        """
        table, related_field = self._splitTargetFld(target_fld)
        pkey = self.db.table(table).recordHandler().relatedRecordPkey(
            pkey, related_field, kwargs)
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
            # the result is discarded here, unlike in getRelatedSelection
            self.page.getPublicMethod('rpc', joinBag['applymethod'])(
                record, **self._getApplyMethodPars(kwargs))
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
            relation_value: The FK value to filter on.  A falsy one gives an
                empty selection, not an error.
            columns: Accepted and never read — see the note.
            query_columns: Same, plus an error in the log.
            condition: Additional WHERE clause.
            js_resolver_one: Client-side resolver for one-to-one.
            sqlContextName: Named SQL context for join conditions.

        Returns:
            A ``(result_bag, resultAttributes_dict)`` tuple.

        Note:
            *columns* and *query_columns* have no effect: neither reaches
            ``relatedQuery``, so the selection always carries the default
            columns of the table.  Reproduced as it is, because what the
            client expects to receive is not decided here; recorded as D19 in
            ``.subtasks/alt-apphandler/bugs.md``.

            ``newproc`` is the constant ``'no'`` for the same reason as in the
            getSelection flow: the attribute name is the literal dotted string
            ``'self.newprocess'``.  Reproduced, recorded as D3.
        """
        if query_columns:
            logger.error('QUERY COLUMNS PARAMETER NOT EXPECTED!!')
        t = time.time()
        resultAttributes = dict()
        joinBag = self._sqlContextJoinBag(sqlContextName, target_fld, from_fld)
        dbtable, related_field = self._splitTargetFld(target_fld)
        recordHandler = self.db.table(dbtable).recordHandler()

        sel = recordHandler.relatedSelection(
            related_field, from_fld, target_fld, relation_value=relation_value,
            condition=condition, sqlContextName=sqlContextName,
            queryCb=lambda query: self._joinConditionsFromContext(query, sqlContextName),
            **kwargs)
        if joinBag and joinBag.get('applymethod'):
            applyresult = self.page.getPublicMethod('rpc', joinBag['applymethod'])(
                sel, **self._getApplyMethodPars(kwargs))
            if applyresult:
                resultAttributes.update(applyresult)

        result, relOneParams = recordHandler.relatedRowsBag(
            sel, js_resolver_one, sqlContextName=sqlContextName)
        resultAttributes.update(dbtable=dbtable, totalrows=len(sel))
        resultAttributes.update({
            'servertime': int((time.time() - t) * 1000),
            'newproc': getattr(self, 'self.newprocess', 'no'),
            'childResolverParams': '%s::JS' % toJson(relOneParams)
        })

        return (result, resultAttributes)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _splitTargetFld(self, target_fld: str) -> tuple[str, str]:
        """Split ``pkg.table.field`` into the table name and the field name."""
        pkg, tbl, related_field = target_fld.split('.')
        return '%s.%s' % (pkg, tbl), related_field

    def _sqlContextJoinBag(self, sqlContextName: Optional[str],
                           target_fld: str, from_fld: str) -> Optional[Any]:
        """The join condition of one relation inside a SQL context, or ``None``."""
        if not sqlContextName:
            return None
        return self._getSqlContextConditions(sqlContextName,
                                             target_fld=target_fld,
                                             from_fld=from_fld)
