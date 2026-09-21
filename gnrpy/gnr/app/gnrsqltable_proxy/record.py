# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy app - see LICENSE for details
# module gnrsqltable_proxy.record : table level part of the record flows
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

"""Table level part of the getRecord, getRelatedRecord and getRelatedSelection
flows.

:class:`RecordHandler` is attached to every table of a ``GnrApp`` database by
``gnr.app.gnrdbo.TableBase.recordHandler``.  It is the sibling of
:class:`gnr.app.gnrsqltable_proxy.selection.SelectionHandler`, which serves the
getSelection flow: the two share nothing, because the record flows never touch
a where bag, a saved query, a frozen selection or column processing.

It never references a web page.  Everything the page provides — the resolved
``eager`` specification, the SQL context join conditions, the page handlers and
the applymethods — is applied by the caller or passed in as a callable.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import uniquify
from gnr.core.gnrstring import fromJson, toText
from gnr.sql.gnrsql_exceptions import GnrSqlException


class RecordHandler:
    """Record proxy of a single table."""

    def __init__(self, tblobj: Any) -> None:
        self.tblobj = tblobj

    @property
    def db(self) -> Any:
        """The database of the proxied table."""
        return self.tblobj.db

    # ------------------------------------------------------------------
    #  Loading a record
    # ------------------------------------------------------------------

    def composeVirtualColumns(self, virtual_columns: Optional[str] = None) -> Optional[str]:
        """Return the virtual column string the caption and the protection flags need.

        The caption columns, the ``always`` virtual columns and, when the table
        has protection columns, ``__protecting_reasons`` and
        ``__is_protected_row`` join the ones the caller asked for.  A table with
        neither caption columns nor protection columns leaves *virtual_columns*
        untouched.

        Args:
            virtual_columns: Comma separated virtual columns, or ``None``.

        Returns:
            The comma separated virtual columns to query.
        """
        tblobj = self.tblobj
        captioncolumns = tblobj.rowcaptionDecode()[0]
        hasProtectionColumns = tblobj.hasProtectionColumns()
        if not (captioncolumns or hasProtectionColumns):
            return virtual_columns
        columns_to_add = (captioncolumns or []) + (
            ['__protecting_reasons', '__is_protected_row'] if hasProtectionColumns else [])
        columns_to_add = [c.replace('$', '') for c in columns_to_add]
        result = virtual_columns.split(',') if virtual_columns else []
        result.extend([k for k, v in tblobj.model.virtual_columns.items()
                       if v.attributes.get('always') or k in columns_to_add])
        return ','.join(uniquify(result))

    def loadRecord(self, pkey: Optional[str] = None, lock: bool = False,
                   eager: Optional[Any] = None,
                   virtual_columns: Optional[str] = None,
                   sqlContextName: Optional[str] = None,
                   _storename: Optional[str] = None,
                   ignoreMissing: bool = True,
                   ignoreDuplicate: bool = True,
                   **kwargs: Any) -> Any:
        """Return the ``SqlRecord`` of the record the caller asked for.

        *lock* must already be the effective one: the caller downgrades a lock
        asked without a pkey, and only a surviving lock adds ``for_update``.

        Args:
            pkey: The primary key, or ``None`` when *kwargs* select the record.
            lock: ``True`` adds ``for_update`` to the query.
            eager: The eager specification, already resolved by the caller.
            virtual_columns: Comma separated virtual columns.
            sqlContextName: Named SQL context, forwarded to the record.
            _storename: Alternate store name.
            ignoreMissing: Return an empty record instead of raising.
            ignoreDuplicate: Return the first row instead of raising.
            **kwargs: Forwarded to ``tblobj.record``.

        Returns:
            The ``SqlRecord``, not yet turned into a Bag.
        """
        if pkey is not None:
            kwargs['pkey'] = pkey
        if lock:
            kwargs['for_update'] = True
        return self.tblobj.record(eager=eager, ignoreMissing=ignoreMissing,
                                  ignoreDuplicate=ignoreDuplicate,
                                  sqlContextName=sqlContextName,
                                  virtual_columns=self.composeVirtualColumns(virtual_columns),
                                  _storename=_storename, **kwargs)

    def recordToBag(self, rec: Any, pkey: Optional[str],
                    resolver_one: str, resolver_many: str,
                    sample_kwargs: Optional[dict] = None) -> Bag:
        """Return the record :class:`Bag` the client expects, in the output mode the pkey selects.

        The output mode comes from the pkey: ``*newrecord*`` and ``*sample*``
        have one of their own, everything else is a plain record Bag.

        Args:
            rec: The ``SqlRecord`` returned by :meth:`loadRecord`.
            pkey: The primary key the caller asked for.
            resolver_one: Client side resolver name for the one side.
            resolver_many: Client side resolver name for the many side.
            sample_kwargs: Parameters of the sample generator.

        Returns:
            The record :class:`Bag`.
        """
        if pkey == '*newrecord*':
            return rec.output('newrecord', resolver_one=resolver_one,
                              resolver_many=resolver_many)
        if pkey == '*sample*':
            return rec.output('sample', resolver_one=resolver_one,
                              resolver_many=resolver_many,
                              sample_kwargs=sample_kwargs)
        return rec.output('bag', resolver_one=resolver_one,
                          resolver_many=resolver_many)

    def resolvePkey(self, record: Bag, pkey: Optional[str],
                    default_kwargs: dict) -> tuple[str, bool]:
        """Return the pkey the loaded record really has and whether it is a new one.

        An empty record means a new one, whatever the caller asked for: the
        serialized key it asked for becomes a set of default values, so a
        composed key is not lost.

        Args:
            record: The record Bag.
            pkey: The primary key the caller asked for.
            default_kwargs: Mutated in place with the parsed serialized key.

        Returns:
            ``(pkey, newrecord)``.
        """
        tblobj = self.tblobj
        if record[tblobj.pkey]:
            return record[tblobj.pkey], False
        if pkey and pkey != '*newrecord*':
            default_kwargs.update(tblobj.parseSerializedKey(pkey))
        return '*newrecord*', True

    # ------------------------------------------------------------------
    #  Protection, handlers and defaults
    # ------------------------------------------------------------------

    def readProtectionFlags(self, record: Bag,
                            ignoreReadOnly: Optional[bool] = None) -> dict[str, bool]:
        """Return the write and delete protection flags of an existing record."""
        tblobj = self.tblobj
        return dict(
            _protect_write=(tblobj._islocked_write(record)
                            or not tblobj.check_updatable(record,
                                                          ignoreReadOnly=ignoreReadOnly)),
            _protect_delete=(tblobj._islocked_delete(record)
                             or not tblobj.check_deletable(record)))

    def findTableOnLoading(self) -> Optional[Callable]:
        """Return the ``onLoading`` method of the table, or ``None``.

        It runs before the default values, unlike the ``onLoading_*`` ones.
        """
        return getattr(self.tblobj, 'onLoading', None)

    def listTableLoadingHandlers(self) -> list:
        """Return every ``onLoading_*`` method of the table.

        They run after the default values, unlike ``onLoading``.
        """
        tblobj = self.tblobj
        return [getattr(tblobj, name) for name in dir(tblobj)
                if name.startswith('onLoading_')]

    def setRecordDefaults(self, record: Bag, defaults: dict) -> None:
        """Write into the record the default values it has a place for; returns nothing.

        A key the record has not got is dropped, which is why the caller seeds
        the missing ones with ``None`` first when it wants them all.  The model
        defaults are applied afterwards, so an explicit default wins.
        """
        for key, value in list(defaults.items()):
            if key in record:
                record[key] = value
        self.tblobj.extendDefaultValues(record)

    # ------------------------------------------------------------------
    #  Record status and counters
    # ------------------------------------------------------------------

    def readRecordStatus(self, record: Bag) -> dict[str, Any]:
        """Return the status keys the client reads: timestamp, deletion, draft, invalid fields.

        ``lastTS`` is produced with ``str()``, so a record with no timestamp
        gives the string ``'None'``.
        """
        tblobj = self.tblobj
        result: dict[str, Any] = {}
        if tblobj.lastTS:
            result['lastTS'] = str(record[tblobj.lastTS])
        if tblobj.logicalDeletionField and record[tblobj.logicalDeletionField]:
            result['_logical_deleted'] = True
        if tblobj.draftField and record[tblobj.draftField]:
            result['_draft'] = True
        invalidFields_fld = tblobj.attributes.get('invalidFields')
        if invalidFields_fld and record[invalidFields_fld]:
            result['_invalidFields'] = fromJson(record[invalidFields_fld])
        return result

    def applyCounters(self, record: Bag, recInfo: dict) -> None:
        """Write the promised counter values into a new record; returns nothing.

        The values go into the *record*, not into *recInfo*; *recInfo* only
        receives the recycle messages and, when the counter table fails, the
        ``_onLoadingError`` key.  Only ``GnrSqlException`` is caught.
        """
        if not self.tblobj.counterColumns():
            return
        try:
            self.tblobj._sequencesOnLoading(record, recInfo)
        except GnrSqlException as error:
            recInfo['_onLoadingError'] = str(error)

    # ------------------------------------------------------------------
    #  Related record
    # ------------------------------------------------------------------

    def resolveRelatedPkey(self, pkey: Optional[str], related_field: str,
                           kwargs: dict) -> Optional[str]:
        """Return the pkey of a related record, taken out of the query keywords when needed.

        With no explicit pkey the client sends the foreign key value under the
        name of this table's pkey, so it is popped from *kwargs*.  A missing
        value gives a new record instead of an error, unless the caller named
        the related field itself, which selects by that column.

        Args:
            pkey: The explicit pkey, or ``None``.
            related_field: The field of this table the relation points at.
            kwargs: Mutated in place when the value is popped.

        Returns:
            The pkey, or ``'*newrecord*'``.
        """
        if pkey is None:
            pkey = kwargs.pop(self.tblobj.pkey, None)
        if pkey in (None, '') and related_field not in kwargs:
            return '*newrecord*'
        return pkey

    # ------------------------------------------------------------------
    #  Related selection
    # ------------------------------------------------------------------

    def selectRelatedRecords(self, related_field: str, from_fld: str, target_fld: str,
                             relation_value: Optional[Any] = None,
                             condition: Optional[str] = None,
                             sqlContextName: Optional[str] = None,
                             queryCb: Optional[Callable] = None,
                             **kwargs: Any) -> Any:
        """Return the selection of the records related to *relation_value*.

        A falsy relation value does not skip the query: it forces ``limit=0``,
        so the caller still gets an empty selection with the column attributes.

        Args:
            related_field: The field of this table the relation points at.
            from_fld: The source field, for the join condition key.
            target_fld: The target field, for the join condition key.
            relation_value: The foreign key value to filter on.
            condition: Extra WHERE clause.
            sqlContextName: Named SQL context.
            queryCb: Called with the query before the selection is fetched;
                this is where the page applies the SQL context join conditions.
            **kwargs: Forwarded to ``relatedQuery``.

        Returns:
            The selection.
        """
        if not relation_value:
            kwargs['limit'] = 0
        query = self.tblobj.relatedQuery(field=related_field, value=relation_value,
                                         where=condition,
                                         sqlContextName=sqlContextName, **kwargs)
        if sqlContextName:
            if queryCb:
                queryCb(query)
            self._rootJoinCondition(query, target_fld, from_fld)
        return query.selection()

    def _rootJoinCondition(self, query: Any, target_fld: str, from_fld: str) -> None:
        """Re-apply the join condition of this relation on the wildcard pair.

        The condition registered under ``<target>_<from>`` only fires when the
        query walks that relation; re-registering it on ``'*'`` / ``'*'`` puts
        it on the root of the query, which is what the related grid needs.
        """
        conditionKey = '%s_%s' % (target_fld.replace('.', '_'),
                                  from_fld.replace('.', '_'))
        rootCond = query.joinConditions.get(conditionKey)
        if rootCond:
            query.setJoinCondition(target_fld='*', from_fld='*',
                                   condition=rootCond['condition'],
                                   one_one=rootCond['one_one'], **rootCond['params'])

    def relatedRecordsToBag(self, sel: Any, js_resolver_one: str,
                            sqlContextName: Optional[str] = None) -> tuple[Bag, dict]:
        """Return the rows :class:`Bag` of a related selection and the child resolver parameters.

        Each row becomes an empty node labelled with its pkey, carrying the
        columns as node attributes.  The returned parameters are the ones the
        client needs to build a resolver for a row that does not exist yet, so
        they list every column of the selection, while the rows carry only the
        four fixed keys.

        Returns:
            ``(rows, relOneParams)``.
        """
        dbtable = self.tblobj.fullname
        relOneParams = dict(_target_fld='%s.%s' % (dbtable, self.tblobj.pkey),
                            _from_fld='',
                            _resolver_name=js_resolver_one,
                            _sqlContextName=sqlContextName)
        result = Bag()
        for row in sel:
            row = dict(row)
            pkey = row.pop('pkey')
            spkey = toText(pkey)
            result.setItem('%s' % spkey, None, _pkey=spkey, _relation_value=pkey,
                           _attributes=row, _removeNullAttributes=False,
                           **relOneParams)
        relOneParams.update(dict([(k, None) for k in list(sel.colAttrs.keys())
                                  if not k == 'pkey']))
        return result, relOneParams
