# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.transactions : Commit, rollback and deferred callbacks
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

"""Mixin providing transaction control and deferred callbacks for ``GnrSqlDb``.

Includes ``commit``, ``rollback``, the deferred-callback queues
(``deferToCommit`` / ``deferAfterCommit``), and database maintenance
helpers (``analyze``, ``vacuum``, ``listen``, ``notify``).
"""

from __future__ import annotations

import _thread
from typing import Any, Callable

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException, getUuid
from gnr.sql.gnrsql.helpers import GnrMissedCommitException


class TransactionMixin:
    """Commit, rollback, deferred-callback queues and db maintenance."""

    # Queue identifiers are defined as class attributes on GnrSqlDb;
    # we reference them through self.QUEUE_DEFER_TO_COMMIT etc.

    def commit(self) -> None:
        """Commit all uncommitted connections for the current thread.

        For each uncommitted connection whose ``connectionName`` matches
        the currently active connection:

        1. Execute the ``DEFER_TO_COMMIT`` queue.
        2. Check for pending exceptions; if any, raise them.
        3. Call ``connection.commit()``.
        4. Execute the ``DEFER_AFTER_COMMIT`` queue.
        5. Mark the connection as committed.

        Finally, calls :meth:`onDbCommitted`.

        Raises:
            GnrException: If there are pending exceptions queued via
                :meth:`deferredRaise`.
        """
        trconns = self._connections.get(_thread.get_ident(), {})
        while True:
            connections = filter(
                lambda c: not c.committed and c.connectionName == self.currentConnectionName,
                trconns.values(),
            )
            connections = list(connections)
            if not connections:
                break
            connection = connections[0]
            with self.tempEnv(storename=connection.storename, onCommittingStep=True):
                self._invoke_deferred_cbs(self.QUEUE_DEFER_TO_COMMIT)

            pending_exceptions = self.currentEnv.get('_pendingExceptions')

            # REVIEW: _pendingExceptions is never cleared after the raise,
            # so if the caller catches this exception and retries commit(),
            # the same exceptions will be raised again.  Consider clearing
            # the list here or in a finally block.
            if pending_exceptions:
                raise GnrException(
                    '\n'.join([str(exception) for exception in pending_exceptions])
                )
            connection.commit()
            connection.committed = True
            with self.tempEnv(storename=connection.storename, onCommittingStep=True):
                self._invoke_deferred_cbs(self.QUEUE_DEFER_AFTER_COMMIT)

        self.onDbCommitted()

    def _invoke_deferred_cbs(self, queue: str) -> None:
        """Execute all deferred callables in the named *queue*.

        Processes blocks in sorted order, removing each block after
        its callables have been executed.

        Args:
            queue: The queue identifier (e.g. ``QUEUE_DEFER_TO_COMMIT``).
        """
        queue_name = f"{queue}_{self.connectionKey()}"
        deferreds_blocks = self.currentEnv.setdefault(queue_name, Bag())
        while deferreds_blocks:
            deferreds_blocks.sort()
            block = deferreds_blocks['#0']
            self.executeDeferred(block)
            deferreds_blocks.pop('#0')

    def executeDeferred(self, deferreds: Bag) -> None:
        """Execute callables from a single deferred block.

        Each item in *deferreds* is a tuple ``(cb, args, kwargs)``.
        After calling each one, if the callable does *not* have
        ``deferredCommitRecursion=True``, its node is popped to
        prevent re-execution.

        Args:
            deferreds: A :class:`Bag` of ``(callable, args, kwargs)`` tuples.
        """
        while deferreds:
            node = deferreds.popNode('#0')
            cb, args, kwargs = node.value
            cb(*args, **kwargs)
            allowRecursion = getattr(cb, 'deferredCommitRecursion', False)
            if not allowRecursion:
                deferreds.popNode(node.label)

    def deferredRaise(self, exception: Exception) -> None:
        """Queue an exception to be raised at commit time.

        Args:
            exception: The exception to raise when ``commit()`` is called.
        """
        self.currentEnv.setdefault('_pendingExceptions', []).append(exception)

    def deferToCommit(self, cb: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Schedule a callable to run just **before** the next commit.

        Args:
            cb: The callable to defer.
            *args: Positional arguments for *cb*.
            **kwargs: Keyword arguments for *cb*.  Special keys:
                ``_deferredBlock`` and ``_deferredId`` control grouping
                and deduplication.

        Returns:
            The kwargs dict (possibly shared with an existing deferred entry
            if deduplicated).
        """
        return self.deferCallable(self.QUEUE_DEFER_TO_COMMIT, cb, *args, **kwargs)

    def deferAfterCommit(self, cb: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Schedule a callable to run just **after** the next commit.

        Args:
            cb: The callable to defer.
            *args: Positional arguments for *cb*.
            **kwargs: Keyword arguments for *cb*.  Special keys:
                ``_deferredBlock`` and ``_deferredId`` control grouping
                and deduplication.

        Returns:
            The kwargs dict (possibly shared with an existing deferred entry
            if deduplicated).
        """
        return self.deferCallable(self.QUEUE_DEFER_AFTER_COMMIT, cb, *args, **kwargs)

    def deferCallable(
        self, queue: str, cb: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Add a callable to a named deferred queue.

        Callables are grouped into blocks (defaulting to ``'_base_'``).
        Within each block, callables are keyed by ``(id(cb), deferredId)``
        to allow deduplication: if the same key already exists, the
        existing kwargs dict is returned instead of adding a duplicate.

        Args:
            queue: The queue identifier.
            cb: The callable to defer.
            *args: Positional arguments for *cb*.
            **kwargs: Keyword arguments; ``_deferredBlock`` and
                ``_deferredId`` are extracted and not passed to *cb*.

        Returns:
            The kwargs dict associated with the deferred entry.
        """
        deferredBlock = kwargs.pop('_deferredBlock', None) or '_base_'
        queue_name = f"{queue}_{self.connectionKey()}"
        deferreds_blocks = self.currentEnv.setdefault(queue_name, Bag())
        if deferredBlock not in deferreds_blocks:
            deferreds_blocks[deferredBlock] = Bag()
        deferreds = deferreds_blocks[deferredBlock]
        deferredId = kwargs.pop('_deferredId', None)
        if not deferredId:
            deferredId = getUuid()
        deferkw = kwargs
        deferredKey = '{}/{}'.format(id(cb), deferredId)
        if deferredKey not in deferreds:
            deferreds.setItem(
                deferredKey, (cb, args, deferkw), deferredBlock=deferredBlock
            )
        else:
            cb, args, deferkw = deferreds[deferredKey]
        return deferkw

    def systemDbEvent(self) -> bool:
        """Return ``True`` if the current operation is a system-level db event."""
        return self.currentEnv.get('_systemDbEvent', False)

    @property
    def dbevents(self) -> dict[str, Any] | None:
        """The db-events dict for the current connection, or ``None``."""
        return self.currentEnv.get('dbevents_%s' % self.connectionKey())

    def autoCommit(self) -> None:
        """Commit if all pending db-events have ``autoCommit=True``.

        Raises:
            GnrMissedCommitException: If at least one event does not
                have ``autoCommit=True``.
        """
        if not self.dbevents:
            return
        if all(
            [all([v.get('autoCommit') for v in t]) for t in list(self.dbevents.values())]
        ):
            self.commit()
        else:
            raise GnrMissedCommitException('Db events not committed')

    def onDbCommitted(self) -> None:
        """Hook called after a successful commit.

        Base implementation is a no-op.  Overridden by ``GnrSqlAppDb``
        to broadcast notifications.
        """
        pass

    def setConstraintsDeferred(self) -> None:
        """Set all deferrable constraints to deferred for the current transaction.

        Only effective if the cursor supports ``setConstraintsDeferred()``.
        """
        cursor = self.adapter.cursor(self.connection)
        if hasattr(cursor, 'setConstraintsDeferred'):
            cursor.setConstraintsDeferred()

    def rollback(self) -> None:
        """Roll back the current connection's transaction."""
        self.connection.rollback()

    def listen(self, *args: Any, **kwargs: Any) -> None:
        """Start listening for a database notification channel (Postgres).

        Args:
            *args: Forwarded to the adapter.
            **kwargs: Forwarded to the adapter.
        """
        self.adapter.listen(*args, **kwargs)

    def notify(self, *args: Any, **kwargs: Any) -> None:
        """Send a notification on a database channel (Postgres).

        Args:
            *args: Forwarded to the adapter.
            **kwargs: Forwarded to the adapter.
        """
        self.adapter.notify(*args, **kwargs)

    def analyze(self) -> None:
        """Run ``ANALYZE`` on the database to update query planner statistics."""
        self.adapter.analyze()

    def vacuum(self) -> None:
        """Run ``VACUUM`` on the database to reclaim storage."""
        self.adapter.vacuum()
