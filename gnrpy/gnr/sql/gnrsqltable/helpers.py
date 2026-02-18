# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.helpers : Decorators and helper classes for SqlTable
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

"""Decorators and helper classes for ``SqlTable`` operations.

This module provides:

- :func:`add_sql_comment` — decorator that attaches caller/user info
  as a SQL comment to each operation.
- :func:`orm_audit_log` — decorator that logs ORM operations via the
  ``ormauditlogger``.
- :class:`RecordUpdater` — context manager for safe record update/insert/delete
  workflows.
"""

from __future__ import annotations

import json
import os
from functools import wraps
from typing import TYPE_CHECKING

from gnr.core.gnrlang import get_caller_info
from gnr.core.gnrbag import Bag
from gnr.sql import ormauditlogger

if TYPE_CHECKING:
    from gnr.sql.gnrsqltable.table import SqlTable


# ---------------------------------------------------------------------------
#  Decorators
# ---------------------------------------------------------------------------

def add_sql_comment(func):
    """Decorator that attaches caller/user info as a SQL comment.

    Populates ``self.db.currentEnv['sql_comment']`` and
    ``self.db.currentEnv['sql_details']`` before forwarding the call.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        self_instance = args[0]
        info = {
            "user": self_instance.db.currentEnv.get(
                'user', os.environ.get("USER", "") + "@cli"
            ),
        }
        info.update(get_caller_info())
        sql_comment = kwargs.get('sql_comment', None)
        if sql_comment:
            info['comment'] = sql_comment
        info['sqlcommand'] = func.__name__
        self_instance.db.currentEnv['sql_comment'] = (
            f'GNRCOMMENT - {json.dumps(info)}'
        )
        self_instance.db.currentEnv['sql_details'] = info
        return func(*args, **kwargs)
    return wrapper


def orm_audit_log(func):
    """Decorator that logs ORM operations via ``ormauditlogger``.

    Captures package, table, command, user, args, kwargs and caller info,
    then delegates to the matching ``ormauditlogger.<command>`` handler.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        self_instance = args[0]
        info = {
            "pkg": self_instance.pkg.name,
            "table": self_instance.name,
            "command": func.__name__,
            "user": self_instance.db.currentEnv.get(
                'user', os.environ.get("USER", "") + "@cli"
            ),
            "args": args[1:],
            "kwargs": kwargs,
            "caller_info": get_caller_info(),
        }
        getattr(ormauditlogger, func.__name__)(info)
        return func(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
#  RecordUpdater — context manager
# ---------------------------------------------------------------------------

class RecordUpdater:
    """Context manager for safe record update/insert/delete workflows.

    Usage::

        with table.recordToUpdate(pkey) as record:
            record['field'] = new_value
            # on exit the record is saved automatically

    Setting ``record[table.pkey] = False`` inside the block triggers
    a delete instead of an update.
    """

    def __init__(self, tblobj: SqlTable, pkey=None, mode=None,
                 raw=False, insertMissing=False, ignoreMissing=None,
                 for_update=None, assignId=None, **kwargs):
        self.tblobj = tblobj
        self.pkey = pkey
        self.mode = mode or 'record'
        self.kwargs = kwargs
        self.raw = raw
        self.insertMissing = insertMissing
        self.ignoreMissing = ignoreMissing
        self.assignId = assignId
        self.for_update = for_update or True
        self.insertMode = False

    def __enter__(self):
        self.record = self.tblobj.record(
            pkey=self.pkey,
            for_update=self.for_update,
            ignoreMissing=self.insertMissing or self.ignoreMissing,
            **self.kwargs,
        ).output(self.mode)

        if self.record.get(self.tblobj.pkey) is None:
            oldrecord = None
            if self.insertMissing:
                self.record = self.tblobj.newrecord(
                    resolver_one=False, resolver_many=False,
                    assignId=self.assignId,
                )
                for k, v in self.kwargs.items():
                    if k in self.tblobj.columns and v is not None:
                        self.record[k] = v
                self.insertMode = True
            else:
                self.record = None
        else:
            oldrecord = dict(self.record)
            for k, v in list(oldrecord.items()):
                if v and isinstance(v, Bag):
                    oldrecord[k] = v.deepcopy()

        self.oldrecord = oldrecord
        self.pkey = (
            oldrecord.get(self.tblobj.pkey) if oldrecord else self.pkey
        )
        return self.record

    def __exit__(self, exception_type, value, traceback):
        if not exception_type:
            if not self.record:
                return
            if self.raw:
                if self.record.get(self.tblobj.pkey) is False:
                    self.tblobj.raw_delete(self.oldrecord)
                elif self.insertMode:
                    self.tblobj.raw_insert(self.record)
                else:
                    self.tblobj.raw_update(
                        self.record, self.oldrecord, pkey=self.pkey,
                    )
            else:
                if self.record.get(self.tblobj.pkey) is False:
                    if not self.insertMode:
                        self.tblobj.delete(self.oldrecord)
                elif self.insertMode:
                    self.tblobj.insert(self.record)
                else:
                    self.tblobj.update(
                        self.record, self.oldrecord, pkey=self.pkey,
                    )
