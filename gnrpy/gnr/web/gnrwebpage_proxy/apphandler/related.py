# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler.related : Related record and selection loading
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
``getRelatedSelection`` public-method flows.  Both are called from
the client-side resolver mechanism to load linked data.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import toJson, toText

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
        pkg, tbl, related_field = target_fld.split('.')
        table = '%s.%s' % (pkg, tbl)
        if pkey is None:
            tbl_pkey = self.db.table(table).pkey
            pkey = kwargs.pop(tbl_pkey, None)
        if pkey in (None, '') and not related_field in kwargs:  # SMELL: ``not x in y`` → ``x not in y``
            pkey = '*newrecord*'
        loadingParameters = loadingParameters or dict()
        loadingParameters.update(resolver_kwargs or dict())
        record, recInfo = self.getRecord(table=table, from_fld=from_fld, target_fld=target_fld, pkey=pkey,
                                         ignoreMissing=ignoreMissing, ignoreDuplicate=ignoreDuplicate,
                                         js_resolver_one=js_resolver_one, js_resolver_many=js_resolver_many,
                                         sqlContextName=sqlContextName, virtual_columns=virtual_columns,
                                         _storename=_storename,
                                         _eager_level=_eager_level, _eager_record_stack=_eager_record_stack,
                                         loadingParameters=loadingParameters, **kwargs)

        if sqlContextName:
            joinBag = self._getSqlContextConditions(sqlContextName, target_fld=target_fld, from_fld=from_fld)
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
            SMELL: *query_columns* is logged as an error but then used
            as a fallback for *columns*.  The parameter should be removed
            and callers updated.

            BUG: ``joinBag`` is set to ``None`` at line 352 in the
            original after being potentially populated at line 339,
            meaning the ``if joinBag`` check at line 361 will **always**
            be ``False`` and the ``applymethod`` branch is dead code.

            SMELL: ``getattr(self, 'self.newprocess', 'no')`` at line 383
            in original uses a dotted string ``'self.newprocess'`` as an
            attribute name — this will never match a real attribute and
            always returns ``'no'``.
        """
        if query_columns:
            logger.error('QUERY COLUMNS PARAMETER NOT EXPECTED!!')
        columns = columns or query_columns
        t = time.time()
        joinBag = None
        resultAttributes = dict()
        if sqlContextName:
            joinBag = self._getSqlContextConditions(sqlContextName, target_fld=target_fld, from_fld=from_fld)

        columns = columns or '*'
        pkg, tbl, related_field = target_fld.split('.')
        dbtable = '%s.%s' % (pkg, tbl)
        if not relation_value:
            kwargs['limit'] = 0

        query = self.db.table(dbtable).relatedQuery(field=related_field, value=relation_value, where=condition,
                                                     sqlContextName=sqlContextName, **kwargs)
        joinBag = None  # BUG: overwrites joinBag — applymethod branch below is dead code
        if sqlContextName:
            self._joinConditionsFromContext(query, sqlContextName)
            conditionKey = '%s_%s' % (target_fld.replace('.', '_'), from_fld.replace('.', '_'))
            rootCond = query.joinConditions.get(conditionKey)
            if rootCond:
                query.setJoinCondition(target_fld='*', from_fld='*', condition=rootCond['condition'],
                                       one_one=rootCond['one_one'], **rootCond['params'])
        sel = query.selection()
        if joinBag and joinBag.get('applymethod'):  # BUG: always False — joinBag is None (see above)
            applyPars = self._getApplyMethodPars(kwargs)
            applyresult = self.page.getPublicMethod('rpc', joinBag['applymethod'])(sel, **applyPars)
            if applyresult:
                resultAttributes.update(applyresult)

        result = Bag()
        relOneParams = dict(_target_fld='%s.%s' % (dbtable, self.db.table(dbtable).pkey),
                            _from_fld='',
                            _resolver_name=js_resolver_one,
                            _sqlContextName=sqlContextName
                            )
        for j, row in enumerate(sel):
            row = dict(row)
            pkey = row.pop('pkey')
            spkey = toText(pkey)
            result.setItem('%s' % spkey, None, _pkey=spkey, _relation_value=pkey,
                           _attributes=row, _removeNullAttributes=False, **relOneParams)

        relOneParams.update(dict([(k, None) for k in list(sel.colAttrs.keys()) if not k == 'pkey']))
        resultAttributes.update(dbtable=dbtable, totalrows=len(sel))
        resultAttributes.update({
            'servertime': int((time.time() - t) * 1000),
            'newproc': getattr(self, 'self.newprocess', 'no'),  # SMELL: dotted attr name — always 'no'
            'childResolverParams': '%s::JS' % toJson(relOneParams)
        })

        return (result, resultAttributes)
