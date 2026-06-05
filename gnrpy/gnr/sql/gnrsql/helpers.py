# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql._helpers : Standalone helpers for GnrSqlDb
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

"""Standalone helpers, decorators, exceptions and utility classes for GnrSqlDb.

This module contains all the non-method components that support ``GnrSqlDb``:

* **Decorators**: ``in_triggerstack``, ``sql_audit``
* **Exceptions**: ``GnrSqlException``, ``GnrSqlExecException``,
  ``GnrMissedCommitException``
* **Context manager**: ``TempEnv``
* **Utility classes**: ``TriggerStack``, ``TriggerStackItem``, ``DbLocalizer``
* **Constants**: ``MAIN_CONNECTION_NAME``
"""

from __future__ import annotations

from functools import wraps
from time import time
from typing import TYPE_CHECKING, Any, Callable

from gnr.core.gnrlang import GnrException
from gnr.sql import sqlauditlogger

if TYPE_CHECKING:
    from gnr.sql.gnrsql.db import GnrSqlDb

MAIN_CONNECTION_NAME: str = '_main_connection'

__version__ = '1.0b'


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def in_triggerstack(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a write method so that its invocation is tracked on the trigger stack.

    The decorator pushes a ``TriggerStackItem`` onto the thread-local
    ``_trigger_stack`` before calling *func* and pops it afterwards.
    This allows triggers to inspect the current call chain (e.g. to know
    whether a delete was caused by a cascade).

    Args:
        func: The method to decorate (``insert``, ``update`` or ``delete``).

    Returns:
        The decorated method.
    """
    # REVIEW: if func raises, pop() is never called and the trigger stack
    # is left in a dirty state.  Consider wrapping in try/finally.
    funcname = func.__name__

    def decore(self: GnrSqlDb, *args: Any, **kwargs: Any) -> Any:
        currentEnv = self.currentEnv
        trigger_stack = currentEnv.get('_trigger_stack')
        if not trigger_stack:
            trigger_stack = TriggerStack()
            currentEnv['_trigger_stack'] = trigger_stack
        trigger_stack.push(funcname, *args, **kwargs)
        result = func(self, *args, **kwargs)
        trigger_stack.pop()
        return result

    return decore


def sql_audit(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that logs SQL execution timing via the audit logger.

    Captures the ``sql_details`` dict from the current environment,
    measures wall-clock time of the wrapped call, and logs the result
    through ``sqlauditlogger`` using the SQL command verb as the log method.

    Args:
        func: The method to decorate (typically ``execute``).

    Returns:
        The decorated method.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        self_instance = args[0]
        sql = args[1]
        sql_details = self_instance.currentEnv.get("sql_details", {})
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        sql_details['time'] = end_time - start_time
        # REVIEW: sql.split(" ")[0] is fragile — if the SQL starts with
        # a comment (e.g. "-- user\nSELECT ...") the verb will be "--"
        # which may not exist on sqlauditlogger.  Consider stripping
        # leading comments before extracting the verb.
        getattr(sqlauditlogger, sql.split(" ")[0])(sql, extra=sql_details)
        return result

    return wrapper


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GnrSqlException(GnrException):
    """Base exception for the Genro SQL layer.

    Attributes:
        code: ``GNRSQL-001``
        description: Human-readable description of the exception.
    """

    code = 'GNRSQL-001'
    description = '!!Genro SQL base exception'


class GnrSqlExecException(GnrSqlException):
    """Raised when an SQL statement fails to execute.

    Attributes:
        code: ``GNRSQL-002``
        description: Human-readable description of the exception.
    """

    code = 'GNRSQL-002'
    description = '!!Genro SQL execution exception'


# REVIEW: GnrMissedCommitException inherits from GnrException rather than
# GnrSqlException.  This means it won't be caught by `except GnrSqlException`.
# Intentional?  If not, consider changing the base class.
class GnrMissedCommitException(GnrException):
    """Raised when pending db-events have not been committed.

    Typically thrown by :meth:`GnrSqlDb.autoCommit` when at least one
    event in the queue does **not** carry ``autoCommit=True``.

    Attributes:
        code: ``GNRSQL-099``
        description: Human-readable description of the exception.
    """

    code = 'GNRSQL-099'
    description = '!!Genro Missed commit exception'


# ---------------------------------------------------------------------------
# TempEnv context manager
# ---------------------------------------------------------------------------

class TempEnv:
    """Context manager that temporarily overrides keys in ``db.currentEnv``.

    On enter, the specified keyword arguments are injected into the
    thread-local environment dictionary.  On exit, the original values
    are restored and any keys that were *added* (not overwritten) are
    removed — but only if they still hold the value that was set on enter,
    to avoid clobbering changes made inside the ``with`` block.

    Example::

        with db.tempEnv(storename='store_a') as db:
            # db.currentEnv['storename'] == 'store_a'
            ...
        # original storename (or absent) is restored here

    Args:
        db: The ``GnrSqlDb`` instance whose environment will be modified.
        **kwargs: Key/value pairs to set in the environment.
    """

    def __init__(self, db: GnrSqlDb, **kwargs: Any) -> None:
        self.db = db
        self.kwargs = kwargs

    def __enter__(self) -> GnrSqlDb:
        currentEnv = self.db.currentEnv
        self.savedValues: dict[str, Any] = {}
        self.addedKeys: list[tuple[str, Any]] = []
        for k, v in self.kwargs.items():
            if k in currentEnv:
                self.savedValues[k] = currentEnv.get(k)
            else:
                self.addedKeys.append((k, v))
            currentEnv[k] = v
        return self.db

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        currentEnv = self.db.currentEnv
        # REVIEW: the equality check `currentEnv.get(k) == v` uses value
        # equality.  For mutable objects (dicts, lists) this may give false
        # positives — a nested function could mutate v in place, making the
        # check always True.  Consider using `currentEnv.get(k) is v`
        # (identity) instead.
        for k, v in self.addedKeys:
            if currentEnv.get(k) == v:
                currentEnv.pop(k, None)
        currentEnv.update(self.savedValues)


# ---------------------------------------------------------------------------
# TriggerStack
# ---------------------------------------------------------------------------

class TriggerStack:
    """A stack that tracks nested write operations (insert/update/delete).

    Used by the :func:`in_triggerstack` decorator to let triggers inspect
    the current call chain.  Each entry is a :class:`TriggerStackItem`.
    """

    def __init__(self) -> None:
        self.stack: list[TriggerStackItem] = []

    def push(
        self,
        event: str,
        tblobj: Any,
        record: dict[str, Any] | None = None,
        old_record: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Push a new item onto the stack.

        Args:
            event: The operation name (``'insert'``, ``'update'``, ``'delete'``).
            tblobj: The table object being modified.
            record: The record dict involved in the operation.
            old_record: The previous version of the record (for updates).
            **kwargs: Additional keyword arguments (currently unused).
        """
        self.stack.append(
            TriggerStackItem(self, event, tblobj, record=record, old_record=old_record)
        )

    def pop(self) -> None:
        """Pop the most recent item from the stack."""
        self.stack.pop()

    def __len__(self) -> int:
        return len(self.stack)

    @property
    def parentItem(self) -> TriggerStackItem | None:
        """Return the current top-of-stack item, or ``None`` if empty."""
        return self.stack[-1] if len(self) > 0 else None

    def item(self, n: int) -> TriggerStackItem | None:
        """Return the *n*-th item in the stack, or ``None`` if out of range.

        Args:
            n: Zero-based index into the stack.
        """
        try:
            return self.stack[n]
        except Exception:
            return None


class TriggerStackItem:
    """A single entry in the :class:`TriggerStack`.

    Attributes:
        trigger_stack: The owning stack.
        parent: The previous stack item, or ``None`` if this is the first.
        event: The operation name.
        table: The full table name (``'pkg.table'``).
        record: The record dict.
        old_record: The previous record dict (updates only).
    """

    def __init__(
        self,
        trigger_stack: TriggerStack,
        event: str,
        tblobj: Any,
        record: dict[str, Any] | None = None,
        old_record: dict[str, Any] | None = None,
    ) -> None:
        self.trigger_stack = trigger_stack
        lastItem = trigger_stack.stack[-1] if trigger_stack.stack else None
        self.parent = lastItem
        self.event = event
        self.table = tblobj.fullname
        self.record = record
        self.old_record = old_record


# ---------------------------------------------------------------------------
# DbLocalizer
# ---------------------------------------------------------------------------

class DbLocalizer:
    """Fallback localizer used when no application is attached.

    Returns every string unchanged (identity translation).
    """

    def translate(self, v: str) -> str:
        """Return *v* unchanged.

        Args:
            v: The string to translate.

        Returns:
            The same string, unmodified.
        """
        return v
