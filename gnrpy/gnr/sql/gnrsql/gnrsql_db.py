# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.db : GnrSqlDb main class (assembles all mixins)
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

"""Core ``GnrSqlDb`` class that assembles all mixin behaviours.

The mixin resolution order (left to right) is:

1. :class:`~gnrsql.connections.ConnectionMixin`
2. :class:`~gnrsql.env.EnvMixin`
3. :class:`~gnrsql.execute.ExecuteMixin`
4. :class:`~gnrsql.write.WriteMixin`
5. :class:`~gnrsql.transactions.TransactionMixin`
6. :class:`~gnrsql.query.QueryMixin`
7. :class:`~gnrsql.schema.SchemaMixin`
8. :class:`GnrObject` (base)

All inter-mixin dependencies pass through ``self``, so there are
no circular imports between mixin modules.
"""

from __future__ import annotations

import os
from typing import Any

from gnr.core.gnrclasses import GnrClassCatalog
from gnr.core.gnrlang import GnrObject, importModule
from gnr.core.gnrstring import boolean

from gnr.sql.gnrsql.gnrsql_helpers import (
    DbLocalizer,
    GnrMissedCommitException,
    GnrSqlException,
    GnrSqlExecException,
)
from gnr.sql.gnrsql.gnrsql_connections import ConnectionMixin
from gnr.sql.gnrsql.gnrsql_env import EnvMixin
from gnr.sql.gnrsql.gnrsql_execute import ExecuteMixin
from gnr.sql.gnrsql.gnrsql_query import QueryMixin
from gnr.sql.gnrsql.gnrsql_schema import SchemaMixin
from gnr.sql.gnrsql.gnrsql_transactions import TransactionMixin
from gnr.sql.gnrsql.gnrsql_write import WriteMixin


class GnrSqlDb(
    ConnectionMixin,
    EnvMixin,
    ExecuteMixin,
    WriteMixin,
    TransactionMixin,
    QueryMixin,
    SchemaMixin,
    GnrObject,
):
    """Main entry point for the Genro SQL layer.

    A ``GnrSqlDb`` instance:

    * manages the logical structure of a database (the *model*),
    * manages connections, environments and stores,
    * provides high-level read/write/DDL operations that hide the
      adapter layer.

    Attributes:
        rootstore: The name of the root (default) store.
        QUEUE_DEFER_TO_COMMIT: Queue id for pre-commit deferred callables.
        QUEUE_DEFER_AFTER_COMMIT: Queue id for post-commit deferred callables.
    """

    rootstore: str = '_main_db'

    QUEUE_DEFER_TO_COMMIT: str = "to_commit_defer_calls"
    QUEUE_DEFER_AFTER_COMMIT: str = "after_commit_defer_calls"

    def __init__(
        self,
        implementation: str = 'sqlite',
        dbname: str = 'mydb',
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
        port: str | int | None = None,
        main_schema: str | None = None,
        debugger: Any = None,
        application: Any = None,
        read_only: bool | None = None,
        fixed_schema: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialise the database instance.

        Args:
            implementation: Database backend identifier.  One of
                ``'sqlite'``, ``'postgres'``, ``'postgres3'``, or a
                colon-separated ``'name:module.path'`` for custom adapters.
            dbname: The database name.
            host: Database server host (``None`` for SQLite).
            user: Database user name.
            password: Database password.
            port: Connection port.
            main_schema: The default schema name.  If ``None``, the
                adapter's default is used.
            debugger: Optional callable invoked after each SQL execution.
            application: The Genro application instance, or ``None``
                for standalone usage.
            read_only: If ``True``, prevent write operations.
            fixed_schema: Force all schema references to this value.
            **kwargs: Extra parameters stored in ``extra_kw``.
        """
        self.implementation = self.dbpar(implementation)
        self._currentEnv: dict[int, dict[str, Any]] = {}
        self._connections: dict[int, dict[tuple[str, str], Any]] = {}
        self.adapters: dict[str, Any] = {}
        self.dbname = self.dbpar(dbname)
        self.dbbranch = self.dbpar(kwargs.get("dbbranch", "production"))
        self.host = self.dbpar(host)
        self.port = self.dbpar(str(port) if port else None)
        self.user = self.dbpar(user)
        self.password = self.dbpar(password)
        self.fixed_schema = self.dbpar(fixed_schema)
        self.read_only = read_only
        self.typeConverter = GnrClassCatalog()
        self.debugger = debugger
        self.application = application
        self.model = self.createModel()

        if ':' in self.implementation:
            self.implementation, adapter_module = self.implementation.split(':')
        else:
            adapter_module = f'gnr.sql.adapters.gnr{self.implementation}'

        self.adapters[self.implementation] = importModule(adapter_module).SqlDbAdapter(self)

        if main_schema is None:
            main_schema = self.adapter.defaultMainSchema()
        self.main_schema = main_schema
        self.extra_kw = dict(kwargs)
        self._connections = {}
        self.started = False
        self.exceptions = {
            'base': GnrSqlException,
            'exec': GnrSqlExecException,
            'missedCommit': GnrMissedCommitException,
        }

    # -- Configuration and startup ------------------------------------------

    def dbpar(self, parvalue: str | None) -> str | None:
        """Expand a configuration value that references an environment variable.

        If *parvalue* starts with ``$``, the remainder is looked up in
        ``os.environ``.  Otherwise it is returned unchanged.

        Args:
            parvalue: The raw configuration value.

        Returns:
            The resolved value, or ``None``.
        """
        if parvalue and parvalue.startswith("$"):
            return os.environ.get(parvalue[1:])
        return parvalue

    @property
    def whereTranslator(self) -> Any:
        """The adapter's WHERE-clause translator."""
        return self.adapter.whereTranslator

    @property
    def adapter(self) -> Any:
        """The SQL adapter for the current implementation.

        If the ``currentEnv`` overrides ``currentImplementation``, that
        adapter is loaded on demand and cached.
        """
        implementation = self.currentEnv.get('currentImplementation') or self.implementation
        if implementation not in self.adapters:
            self.adapters[implementation] = importModule(
                'gnr.sql.adapters.gnr%s' % implementation
            ).SqlDbAdapter(self)
        return self.adapters[implementation]

    @property
    def debug(self) -> bool:
        """Whether debug mode is active.

        Always ``False`` in the base class.  Overridden by ``GnrSqlAppDb``.
        """
        return False

    # -- Store properties (overridden by GnrSqlAppDb) -----------------------

    @property
    def stores_handler(self) -> Any:
        """The stores handler, or ``None`` in standalone mode."""
        return None

    @property
    def multidb_config(self) -> dict[str, Any]:
        """Multi-database configuration dict.  Empty in standalone mode."""
        return {}

    @property
    def dbstores(self) -> dict[str, Any]:
        """Dict of configured database stores."""
        if self.stores_handler:
            return self.stores_handler.dbstores
        return {}

    @property
    def auxstores(self) -> dict[str, Any]:
        """Dict of auxiliary (read-only) stores."""
        if self.stores_handler:
            return self.stores_handler.auxstores
        return {}

    @property
    def storetable(self) -> str | None:
        """The table used to store store configurations, if any."""
        return self.multidb_config.get('storetable')

    @property
    def multidb_prefix(self) -> str:
        """The prefix applied to store database names."""
        prefix = self.multidb_config.get('prefix') or self.dbname
        return f'{prefix}_' if prefix else ''

    @property
    def multidomain(self) -> bool:
        """Whether multi-domain mode is active."""
        return boolean(self.multidb_config.get('multidomain'))

    @property
    def tenant_table(self) -> str | None:
        """The table used for multi-tenant schema resolution, if any."""
        if hasattr(self, '_tenant_table'):
            return self._tenant_table
        tenant_table = None
        for pkg in self.packages.values():
            tenant_table = pkg.attributes.get('tenant_table') or tenant_table
        self._tenant_table = tenant_table
        return self._tenant_table

    @property
    def reuse_relation_tree(self) -> bool | None:
        """Whether to reuse the relation tree resolver across queries.

        Returns ``None`` in standalone mode (no application).
        """
        if self.application:
            return boolean(self.application.config['db?reuse_relation_tree']) is not False

    @property
    def auto_static_enabled(self) -> bool | None:
        """Whether auto-static column resolution is enabled.

        Returns ``None`` in standalone mode (no application).
        """
        if self.application:
            return boolean(self.application.config['db?auto_static_enabled']) is not False

    # -- Model --------------------------------------------------------------

    def createModel(self) -> Any:
        """Create and return a new ``DbModel`` for this database instance."""
        from gnr.sql.gnrsqlmodel import DbModel

        return DbModel(self)

    def startup(self, restorepath: str | None = None) -> None:
        """Build the model and mark the database as started.

        Args:
            restorepath: If provided, restore from this archive before
                building the model.
        """
        if restorepath:
            self.autoRestore(restorepath)
        self.model.build()
        self.started = True

    @property
    def localizer(self) -> Any:
        """The localizer for translating user-facing strings.

        Returns the application's localizer if an application is attached,
        otherwise a no-op :class:`DbLocalizer`.
        """
        return self.application.localizer if self.application else DbLocalizer
