# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.triggers : Hooks, protection, validation and events
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

"""Trigger hooks, protection checks, validation and DB-event notification.

Provides :class:`TriggersMixin` — a mixin for :class:`~gnrsqltable.table.SqlTable`
containing all ``trigger_on*`` hook methods, ``protect_*`` guards,
``diagnostic_*`` validators, lock/draft checks, DB event notifications,
and the ``touchRecords`` utility.
"""

from __future__ import annotations

from gnr.sql import logger


class TriggersMixin:
    """Trigger hooks, protection, validation and DB events."""

    # ------------------------------------------------------------------
    #  DB events
    # ------------------------------------------------------------------

    @property
    def dbevents(self):
        return self.db.dbevents[self.fullname]

    def notifyDbUpdate(self, record=None, where=None, **kwargs):
        self.db.notifyDbUpdate(self, recordOrPkey=record, where=where, **kwargs)

    def touchRecords(self, _pkeys=None, _wrapper=None, _wrapperKwargs=None,
                     _notifyOnly=False, pkey=None, order_by=None,
                     method=None, columns=None, **kwargs):
        """Touch (re-save or apply method to) a set of records.

        :param _pkeys: list of primary keys
        :param method: ``'update'`` or a callable/method name
        """
        if 'where' not in kwargs:
            if pkey:
                _pkeys = [pkey]
            if not _pkeys:
                return
            kwargs['where'] = '$%s IN :_pkeys' % self.pkey
            if isinstance(_pkeys, str):
                _pkeys = _pkeys.strip(',').split(',')
            kwargs['_pkeys'] = _pkeys
            kwargs.setdefault('subtable', '*')
            kwargs.setdefault('excludeDraft', False)
            kwargs.setdefault('ignorePartition', True)
            kwargs.setdefault('excludeLogicalDeleted', False)
        method = method or 'update'
        for_update = method == 'update'
        handler = getattr(self, method) if isinstance(method, str) else method
        onUpdating = None
        if method != 'update':
            columns = columns or getattr(handler, 'columns', None)
            for_update = getattr(handler, 'for_update', False)
            doUpdate = getattr(handler, 'doUpdate', False)
            order_by = getattr(handler, 'order_by', None)
            for_update = doUpdate or for_update
            if doUpdate:
                onUpdating = handler
                handler = self.update
        sel = self.query(
            addPkeyColumn=False,
            for_update=for_update,
            columns=columns or '*',
            order_by=order_by, **kwargs,
        ).fetch()
        if _wrapper:
            _wrapperKwargs = _wrapperKwargs or dict()
            sel = _wrapper(sel, **(_wrapperKwargs or dict()))
        if _notifyOnly:
            self.notifyDbUpdate(sel)
            return
        for row in sel:
            row._notUserChange = True
            old_record = dict(row)
            self.expandBagFields(row)
            self.expandBagFields(old_record)
            if onUpdating:
                onUpdating(row, old_record=old_record)
            handler(row, old_record=old_record)
        return sel

    # ------------------------------------------------------------------
    #  Trigger hooks (overridable)
    # ------------------------------------------------------------------

    @property
    def currentTrigger(self):
        trigger_stack = self.db.currentEnv.get('_trigger_stack')
        if trigger_stack:
            return trigger_stack.parentItem

    def trigger_onInserting(self, record):
        """Hook called *before* a record is inserted."""
        pass

    def trigger_onInserted(self, record):
        """Hook called *after* a record is inserted."""
        pass

    def trigger_onUpdating(self, record, old_record=None):
        """Hook called *before* a record is updated."""
        pass

    def trigger_onUpdated(self, record, old_record=None):
        """Hook called *after* a record is updated."""
        pass

    def trigger_onDeleting(self, record):
        """Hook called *before* a record is deleted."""
        pass

    def trigger_onDeleted(self, record):
        """Hook called *after* a record is deleted."""
        pass

    # ------------------------------------------------------------------
    #  Protection guards (overridable)
    # ------------------------------------------------------------------

    def protect_update(self, record, old_record=None):
        """Override to protect records from being updated."""
        pass

    def protect_delete(self, record):
        """Override to protect records from being deleted."""
        pass

    def protect_validate(self, record, old_record=None):
        """Override to add custom validation before save."""
        pass

    def hasProtectionColumns(self):
        """Override to declare custom protection columns."""
        return False

    # ------------------------------------------------------------------
    #  Diagnostics (overridable)
    # ------------------------------------------------------------------

    def diagnostic_errors(self, record, old_record=None):
        """Override to return diagnostic errors for *record*."""
        logger.warning('You should override this method for diagnostic')  # REVIEW: logs warning on every call if not overridden
        return

    def diagnostic_warnings(self, record, old_record=None):
        """Override to return diagnostic warnings for *record*."""
        logger.warning('You should override this method for diagnostic')  # REVIEW: logs warning on every call if not overridden
        return

    # ------------------------------------------------------------------
    #  Counter triggers (overridable)
    # ------------------------------------------------------------------

    def trigger_assignCounters(self, record=None, old_record=None):
        """Override to assign counter values on insert."""
        pass

    def trigger_releaseCounters(self, record=None):
        """Override to release counters on delete."""
        pass

    # ------------------------------------------------------------------
    #  Lock / draft / updatability
    # ------------------------------------------------------------------

    def _isReadOnly(self, record):
        if self.attributes.get('readOnly'):
            return True

    def _islocked_write(self, record):
        return self._isReadOnly(record) or self.islocked_write(record)

    def islocked_write(self, record):
        """Override to implement custom write-lock logic."""
        pass

    def _islocked_delete(self, record):
        return (
            (self._isReadOnly(record) is not False)  # REVIEW: 'is not False' — _isReadOnly returns True or None, so this is always True
            or self.islocked_delete(record)
        )

    def islocked_delete(self, record):
        """Override to implement custom delete-lock logic."""
        pass

    def isDraft(self, record):
        if self.draftField:
            return record.get(self.draftField)
        return False

    def check_updatable(self, record, ignoreReadOnly=None):
        """Check if *record* can be updated (without raising)."""
        from gnr.sql.gnrsqltable import EXCEPTIONS
        try:
            self.protect_update(record, record)
            return True
        except EXCEPTIONS['protect_update']:
            return False

    def check_deletable(self, record):
        """Check if *record* can be deleted (without raising)."""
        from gnr.sql.gnrsqltable import EXCEPTIONS
        try:
            self.protect_delete(record)
            return True
        except EXCEPTIONS['protect_delete']:
            return False

    # ------------------------------------------------------------------
    #  Log change hook
    # ------------------------------------------------------------------

    def onLogChange(self, evt, record, old_record=None):
        """Override to react to audit log events."""
        pass
