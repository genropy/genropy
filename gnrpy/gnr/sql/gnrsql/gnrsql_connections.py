# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.connections : Physical database connection management
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

"""Mixin providing physical database connection management for ``GnrSqlDb``.

Handles connection pooling per thread/store, connection parameters
resolution, and multi-store connection dispatch.
"""

from __future__ import annotations

import _thread
from typing import Any

from gnr.sql.gnrsql.gnrsql_helpers import GnrSqlException


class ConnectionMixin:
    """Database connection lifecycle and store-based routing."""

    def closeConnection(self) -> None:
        """Close all connections for the current thread.

        Iterates over every open connection in the current thread's pool,
        rolls each one back (to release any pending transaction) and closes it.
        Errors during rollback/close are silently ignored.
        """
        thread_ident = _thread.get_ident()
        connections_dict = self._connections.get(thread_ident)
        if connections_dict:
            for conn_name in list(connections_dict.keys()):
                try:
                    conn = connections_dict.pop(conn_name)
                    conn.rollback()
                    conn.close()
                except Exception:  # pragma: no cover
                    pass

    def connectionKey(self, storename: str | None = None) -> str:
        """Return a unique key identifying the current connection slot.

        The key is composed of ``storename`` + ``connectionName``, separated
        by an underscore.  Used to partition deferred-callback queues and
        other per-connection state.

        Args:
            storename: Override the store part of the key.  Defaults to
                the currently active store.

        Returns:
            A string like ``'_main_db__main_connection'``.
        """
        storename = storename or self.currentEnv.get('storename') or self.rootstore
        return '_'.join((storename or self.currentStorename, self.currentConnectionName))

    def _get_store_connection(self, storename: str) -> Any:
        """Return (or create) a connection for the given *storename*.

        Connections are cached per ``(storename, connectionName)`` tuple
        inside the current thread's pool.

        Args:
            storename: The store to connect to.

        Returns:
            A database connection object with extra attributes
            ``storename``, ``committed`` and ``connectionName``.
        """
        thread_ident = _thread.get_ident()
        thread_connections = self._connections.setdefault(thread_ident, {})
        connectionTuple = (storename or self.currentStorename, self.currentConnectionName)
        connection = thread_connections.get(connectionTuple)
        if not connection:
            connection = self.adapter.connect(storename)
            connection.storename = storename
            connection.committed = False
            connection.connectionName = connectionTuple[1]
            thread_connections[connectionTuple] = connection
        return connection

    def _get_connection(self) -> Any:
        """Property implementation for ``.connection``.

        If ``currentStorename`` is ``'*'`` or a comma-separated list,
        returns a list of connections (one per store).  Otherwise returns
        a single connection.
        """
        storename = self.currentStorename
        if storename == '*' or ',' in storename:
            if storename == '*':
                storenames = list(self.dbstores.keys())
            else:
                storenames = storename.split(',')
            return [self._get_store_connection(s) for s in storenames]
        else:
            return self._get_store_connection(storename)

    connection = property(_get_connection)

    def get_store_parameters(self, storename: str) -> dict[str, Any] | None:
        """Return configuration parameters for the given store.

        Looks up ``dbstores`` first, then ``auxstores``.

        Args:
            storename: The store name to look up.

        Returns:
            A dict with keys like ``database``, ``host``, etc., or ``None``
            if the store is not configured.
        """
        return self.dbstores.get(storename) or self.auxstores.get(storename)

    def get_connection_params(self, storename: str | None = None) -> dict[str, Any]:
        """Return the low-level connection parameters for a given store.

        For the root store (or ``None``), returns the instance-level
        ``host``, ``dbname``, ``user``, ``password``, ``port``.
        For named stores, merges store-specific overrides on top of
        the instance defaults.

        Args:
            storename: The store to resolve.  ``None`` means root store.

        Returns:
            A dict suitable for passing to the adapter's ``connect()``.

        Raises:
            GnrSqlException: If *storename* is not configured.
        """
        if storename == self.rootstore or not storename:
            return dict(
                host=self.host,
                database=self.dbname,
                user=self.user,
                password=self.password,
                port=self.port,
            )
        storeattr = self.get_store_parameters(storename)
        if not storeattr:
            raise GnrSqlException(
                f'Not existing connection configuration for {storename}'
            )

        return dict(
            host=storeattr.get('host') or self.host,
            database=storeattr.get('database') or storeattr.get('dbname'),
            dbbranch=storeattr.get('dbbranch', None),
            user=storeattr.get('user') or self.user,
            password=storeattr.get('password') or self.password,
            port=storeattr.get('port') or self.port,
            implementation=storeattr.get('implementation') or self.implementation,
        )
