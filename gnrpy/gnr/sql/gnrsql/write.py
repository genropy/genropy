# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.write : Record write operations for GnrSqlDb
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
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

"""Mixin providing record write operations for ``GnrSqlDb``.

Contains ``insert``, ``update``, ``delete`` and their ``raw_*`` variants.
These methods are the primary override points for ``GnrSqlAppDb``.
"""

from __future__ import annotations

from typing import Any

from gnr.sql.gnrsql.helpers import GnrSqlException, in_triggerstack


class WriteMixin:
    """Insert, update, delete and related change-tracking hooks."""

    def notifyDbEvent(self, tblobj: Any, **kwargs: Any) -> None:
        """Notify external listeners of a database event.

        Base implementation is a no-op.  Overridden by ``GnrSqlAppDb``
        to broadcast real-time notifications.
        """
        pass  # pragma: no cover

    def _onDbChange(
        self,
        tblobj: Any,
        evt: str,
        record: dict[str, Any],
        old_record: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Internal hook invoked after every insert/update/delete.

        Handles:

        * Totalizer updates (if the table defines totalizers).
        * Change logging (if the table has ``logChanges`` attribute).

        Args:
            tblobj: The table object that was modified.
            evt: One of ``'I'`` (insert), ``'U'`` (update), ``'D'`` (delete).
            record: The record after the operation.
            old_record: The record before the operation (for updates).
            **kwargs: Forwarded from the caller (e.g. ``_raw=True``).
        """
        if tblobj.totalizers:
            tblobj.updateTotalizers(record, old_record=old_record, evt=evt, **kwargs)
        logchanges = tblobj.attributes.get('logChanges')
        if logchanges:
            if isinstance(logchanges, str):
                loggable_events = logchanges.split(',')
            else:
                loggable_events = ['I', 'U', 'D']
            if evt in loggable_events:
                tblobj.onLogChange(evt, record, old_record=old_record)
                self.table(self.changeLogTable).logChange(
                    tblobj, evt=evt, record=record
                )

    @in_triggerstack
    def insert(self, tblobj: Any, record: dict[str, Any], **kwargs: Any) -> None:
        """Insert a record into a table, firing all triggers.

        Execution order:

        1. ``checkPkey`` / ``protect_validate``
        2. Field triggers ``onInserting`` + table trigger + external pkg triggers
        3. Counter assignment
        4. ``dbo_onInserting`` (if defined on the table)
        5. Draft field protection (if applicable)
        6. Adapter-level ``INSERT``
        7. ``_onDbChange`` hook
        8. Field triggers ``onInserted`` + table trigger + external pkg triggers

        Args:
            tblobj: The table object to insert into.
            record: A dict-like object mapping column names to values.
            **kwargs: Forwarded to the adapter's ``insert()``.
        """
        tblobj.checkPkey(record)
        tblobj.protect_validate(record)
        tblobj._doFieldTriggers('onInserting', record)
        tblobj.trigger_onInserting(record)
        tblobj._doExternalPkgTriggers('onInserting', record)
        tblobj.trigger_assignCounters(record=record)
        if hasattr(tblobj, 'dbo_onInserting'):
            tblobj.dbo_onInserting(record, **kwargs)
        if tblobj.draftField:
            if hasattr(tblobj, 'protect_draft'):
                record[tblobj.draftField] = tblobj.protect_draft(record)
        self.adapter.insert(tblobj, record, **kwargs)
        self._onDbChange(tblobj, 'I', record=record, old_record=None)
        tblobj._doFieldTriggers('onInserted', record)
        tblobj.trigger_onInserted(record)
        tblobj._doExternalPkgTriggers('onInserted', record)

    def insertMany(self, tblobj: Any, records: list[dict[str, Any]], **kwargs: Any) -> None:
        """Bulk-insert multiple records bypassing triggers.

        Args:
            tblobj: The table object.
            records: A list of record dicts.
            **kwargs: Forwarded to the adapter's ``insertMany()``.
        """
        self.adapter.insertMany(tblobj, records, **kwargs)

    def raw_insert(self, tblobj: Any, record: dict[str, Any], **kwargs: Any) -> None:
        """Insert a record without firing triggers, but with change tracking.

        Args:
            tblobj: The table object.
            record: The record dict.
            **kwargs: Forwarded to the adapter.
        """
        self.adapter.insert(tblobj, record, **kwargs)
        self._onDbChange(tblobj, 'I', record=record, old_record=None, _raw=True, **kwargs)

    def raw_update(
        self,
        tblobj: Any,
        record: dict[str, Any],
        old_record: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Update a record without firing triggers, but with change tracking.

        Args:
            tblobj: The table object.
            record: The new record dict.
            old_record: The previous record dict.
            **kwargs: Forwarded to the adapter.
        """
        self.adapter.update(tblobj, record, **kwargs)
        self._onDbChange(
            tblobj, 'U', record=record, old_record=old_record, _raw=True, **kwargs
        )

    def raw_delete(self, tblobj: Any, record: dict[str, Any], **kwargs: Any) -> None:
        """Delete a record without firing triggers, but with change tracking.

        Args:
            tblobj: The table object.
            record: The record dict.
            **kwargs: Forwarded to the adapter.
        """
        self.adapter.delete(tblobj, record, **kwargs)
        self._onDbChange(tblobj, 'D', record=record, old_record=None, _raw=True, **kwargs)

    @in_triggerstack
    def update(
        self,
        tblobj: Any,
        record: dict[str, Any],
        old_record: dict[str, Any] | None = None,
        pkey: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Update a table record, firing all triggers.

        Execution order:

        1. ``protect_update`` / ``protect_validate``
        2. Field triggers ``onUpdating`` + table trigger + external pkg triggers
        3. ``dbo_onUpdating`` (if defined on the table)
        4. Counter assignment
        5. Adapter-level ``UPDATE``
        6. ``updateRelated``
        7. ``_onDbChange`` hook
        8. Field triggers ``onUpdated`` + table trigger + external pkg triggers

        Args:
            tblobj: The table object.
            record: The new record dict.
            old_record: The record before modification.
            pkey: Explicit primary key value (overrides the one in *record*).
            **kwargs: Forwarded to the adapter's ``update()``.
        """
        tblobj.protect_update(record, old_record=old_record)
        tblobj.protect_validate(record, old_record=old_record)
        tblobj._doFieldTriggers('onUpdating', record, old_record=old_record)
        tblobj.trigger_onUpdating(record, old_record=old_record)
        tblobj._doExternalPkgTriggers('onUpdating', record, old_record=old_record)
        if hasattr(tblobj, 'dbo_onUpdating'):
            tblobj.dbo_onUpdating(record, old_record=old_record, pkey=pkey, **kwargs)

        tblobj.trigger_assignCounters(record=record, old_record=old_record)
        self.adapter.update(tblobj, record, pkey=pkey, old_record=old_record, **kwargs)
        tblobj.updateRelated(record, old_record=old_record)
        self._onDbChange(tblobj, 'U', record=record, old_record=old_record, **kwargs)
        tblobj._doFieldTriggers('onUpdated', record, old_record=old_record)
        tblobj.trigger_onUpdated(record, old_record=old_record)
        tblobj._doExternalPkgTriggers('onUpdated', record, old_record=old_record)

    @in_triggerstack
    def delete(self, tblobj: Any, record: dict[str, Any], **kwargs: Any) -> None:
        """Delete a record from a table, firing all triggers.

        Checks the ``deletable`` attribute on the table, which can be
        a boolean or a permission tag string.

        Execution order:

        1. Deletability check
        2. ``protect_delete``
        3. Field triggers ``onDeleting`` + table trigger + external pkg triggers
        4. ``deleteRelated``
        5. ``dbo_onDeleting`` (if defined on the table)
        6. Adapter-level ``DELETE``
        7. ``_onDbChange`` hook
        8. Field triggers ``onDeleted`` + table trigger + external pkg triggers
        9. Counter release

        Args:
            tblobj: The table object.
            record: The record dict to delete.
            **kwargs: Forwarded to the adapter's ``delete()``.

        Raises:
            GnrSqlException: If the table does not allow deletion.
        """
        deletable = tblobj.attributes.get('deletable', True)
        if isinstance(deletable, str):
            # REVIEW: if self.application is None (standalone mode), this
            # will raise AttributeError.  Also, currentEnv['userTags']
            # will raise KeyError if not set.  Consider adding guards.
            deletable = self.application.checkResourcePermission(
                deletable, self.currentEnv['userTags']
            )
        if not deletable:
            raise GnrSqlException(
                'The records of table %s cannot be deleted' % tblobj.name_long
            )
        tblobj.protect_delete(record)
        tblobj._doFieldTriggers('onDeleting', record)
        tblobj.trigger_onDeleting(record)
        tblobj._doExternalPkgTriggers('onDeleting', record)
        tblobj.deleteRelated(record)
        if hasattr(tblobj, 'dbo_onDeleting'):
            tblobj.dbo_onDeleting(record, **kwargs)

        self.adapter.delete(tblobj, record, **kwargs)
        self._onDbChange(tblobj, 'D', record=record, **kwargs)
        tblobj._doFieldTriggers('onDeleted', record)
        tblobj.trigger_onDeleted(record)
        tblobj._doExternalPkgTriggers('onDeleted', record)
        tblobj.trigger_releaseCounters(record)
