# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.execute : SQL statement execution for GnrSqlDb
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

"""Mixin providing SQL statement execution for ``GnrSqlDb``.

Contains the main ``execute`` method and the multi-cursor parallel
execution helper.
"""

from __future__ import annotations

import re
from multiprocessing.pool import ThreadPool
from time import time
from typing import Any

from gnr.core.gnrlang import getUuid
from gnr.sql import logger
from gnr.sql.gnrsql.gnrsql_helpers import sql_audit


class ExecuteMixin:
    """Low-level SQL execution and cursor management."""

    @sql_audit
    def execute(
        self,
        sql: str,
        sqlargs: dict[str, Any] | None = None,
        cursor: Any = None,
        cursorname: str | None = None,
        autocommit: bool = False,
        dbtable: str | None = None,
        storename: str | None = None,
        _adaptArguments: bool = True,
    ) -> Any:
        """Execute a SQL statement and return the resulting cursor.

        Handles:

        * ``env_*`` parameter substitution from ``currentEnv``
        * byte-to-string conversion of arguments
        * escaped-prefix stripping (``\\$``, ``\\@``)
        * optional named server-side cursors
        * multi-store parallel execution when ``storename`` is ``'*'``
          or a comma-separated list
        * automatic rollback on error
        * optional auto-commit

        Args:
            sql: The SQL statement to execute.  May contain ``:env_*``
                placeholders that are resolved from ``currentEnv``.
            sqlargs: Optional dict of SQL parameter bindings.
            cursor: An existing cursor to reuse.  If ``None`` a new one
                is created from the adapter.
            cursorname: If provided, a named (server-side) cursor is used.
                Pass ``'*'`` to auto-generate a unique name.
            autocommit: If ``True``, ``commit()`` is called after execution.
            dbtable: Optional table path.  When given, the table's
                ``use_dbstores()`` may force execution on the root store.
            storename: Override the target store.  ``False`` means root store.
            _adaptArguments: If ``True`` (default), the adapter's
                ``prepareSqlText`` is called to translate named parameters.

        Returns:
            The database cursor after execution.

        Raises:
            Exception: Re-raises any exception from the database driver
                after logging and rolling back.
        """
        env_pars_match = re.findall(r':env_(\S\w*)(\W|$)', sql)
        envargs = {f'env_{k}': self.currentEnv.get(k) for k, chunk in env_pars_match}
        if 'env_workdate' in envargs:
            envargs['env_workdate'] = envargs['env_workdate'] or self.workdate
        if self.currentEnv.get('storename'):
            envargs['env_storename'] = self.currentEnv['storename']
        envargs.update(sqlargs or {})
        if storename is False:
            storename = self.rootstore
        storename = storename or envargs.get('env_storename', self.rootstore)
        sqlargs = envargs
        sql_comment = self.currentEnv.get('sql_comment') or self.currentEnv.get('user')

        for k, v in list(sqlargs.items()):
            if isinstance(v, bytes):
                v = v.decode('utf-8')
                sqlargs[k] = v
            if isinstance(v, str):
                if v.startswith(r'\$') or v.startswith(r'\@'):
                    sqlargs[k] = v[1:]

        # FIXME: we'll need an external package table to test this
        if dbtable and self.table(dbtable).use_dbstores(**sqlargs) is False:  # pragma: no cover
            storename = self.rootstore
        with self.tempEnv(storename=storename):
            sql = f'-- {sql_comment}\n{sql}'
            if _adaptArguments:
                sql = sql.replace(r'\:', chr(1))
                sql, sqlargs = self.adapter.prepareSqlText(sql, sqlargs)
                sql = sql.replace(chr(1), ':')
            try:
                t_0 = time()
                if not cursor:
                    if cursorname:
                        if cursorname == '*':
                            cursorname = 'c%s' % re.sub(r"\W", '_', getUuid())
                        cursor = self.adapter.cursor(self.connection, cursorname)
                    else:
                        # REVIEW: cenv is assigned but never used.
                        cenv = self.currentEnv
                        cursor = self.adapter.cursor(self.connection)

                if isinstance(cursor, list):
                    # Since sqlite won't support different cursors in different
                    # threads, we simply serialize the cursor execution.
                    if self.implementation == "sqlite":
                        for c in cursor:
                            c.execute(sql, sqlargs)
                            c.connection.committed = False
                    else:
                        self._multiCursorExecute(cursor, sql, sqlargs)
                else:
                    cursor.execute(sql, sqlargs)
                    cursor.connection.committed = False
                if self.debugger:
                    self.debugger(
                        sql=sql, sqlargs=sqlargs, dbtable=dbtable, delta_time=time() - t_0
                    )

            except Exception as e:
                logger.warning(
                    'error executing:%s - with kwargs:%s \n\n', sql, str(sqlargs)
                )
                self.rollback()
                raise

            if autocommit:
                self.commit()

        return cursor

    def _multiCursorExecute(
        self, cursor_list: list[Any], sql: str, sqlargs: dict[str, Any]
    ) -> None:
        """Execute *sql* in parallel across multiple store cursors.

        Uses a :class:`~multiprocessing.pool.ThreadPool` of size 4.
        Each cursor's ``_STORENAME_`` placeholder in *sql* is replaced
        with the connection's actual store name.

        Args:
            cursor_list: A list of cursors, one per store.
            sql: The SQL statement (may contain ``_STORENAME_``).
            sqlargs: The parameter bindings.
        """
        # REVIEW: a new ThreadPool(4) is created on every call and never
        # shut down — this leaks threads.  Consider reusing a single pool
        # or calling p.close()/p.join() after p.map().
        p = ThreadPool(4)

        def _executeOnThread(cursor: Any) -> None:
            cursor.execute(
                sql.replace("_STORENAME_", cursor.connection.storename), sqlargs
            )

        p.map(_executeOnThread, cursor_list)
