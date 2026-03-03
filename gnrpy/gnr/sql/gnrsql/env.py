# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.env : Thread-local environment management for GnrSqlDb
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

"""Mixin providing thread-local environment management for ``GnrSqlDb``.

The *currentEnv* is a plain ``dict`` keyed by thread id, holding per-request
state such as ``workdate``, ``locale``, ``storename``, ``user``, etc.
"""

from __future__ import annotations

import _thread

from datetime import date
from typing import Any

from gnr.core.gnrlocale import defaultLocale
from gnr.sql._typing import GnrSqlDbBaseMixin
from gnr.sql.gnrsql.helpers import TempEnv


class EnvMixin(GnrSqlDbBaseMixin):
    """Thread-local environment, workdate, locale and store selection."""

    # -- TempEnv factory ----------------------------------------------------

    def tempEnv(self, **kwargs: Any) -> TempEnv:
        """Return a :class:`TempEnv` context manager for this db instance.

        Args:
            **kwargs: Key/value pairs to set temporarily in ``currentEnv``.

        Returns:
            A context manager that restores the previous env on exit.
        """
        return TempEnv(self, **kwargs)

    # -- currentEnv property ------------------------------------------------

    def clearCurrentEnv(self) -> None:
        """Reset the current thread's environment to an empty dict."""
        self._currentEnv[_thread.get_ident()] = {}

    def _get_currentEnv(self) -> dict[str, Any]:
        """Return the env dict for the current thread, creating it if needed."""
        return self._currentEnv.setdefault(_thread.get_ident(), {})

    def _set_currentEnv(self, env: dict[str, Any]) -> None:
        """Replace the env dict for the current thread."""
        self._currentEnv[_thread.get_ident()] = env

    currentEnv = property(_get_currentEnv, _set_currentEnv)

    # -- workdate property --------------------------------------------------

    def _get_workdate(self) -> date:
        """Return the workdate for the current thread.

        Falls back to ``date.today()`` if not explicitly set.
        """
        return self.currentEnv.get('workdate') or date.today()

    def _set_workdate(self, workdate: date) -> None:
        """Set the workdate for the current thread."""
        self.currentEnv['workdate'] = workdate

    workdate = property(_get_workdate, _set_workdate)

    # -- locale property ----------------------------------------------------

    def _get_locale(self) -> str | None:
        """Return the locale for the current thread.

        Falls back to the system locale if not explicitly set.
        """
        return self.currentEnv.get('locale') or defaultLocale() 

    def _set_locale(self, locale: str) -> None:
        """Set the locale for the current thread."""
        self.currentEnv['locale'] = locale

    locale = property(_get_locale, _set_locale)

    # -- env manipulation ---------------------------------------------------

    def updateEnv(self, _excludeNoneValues: bool = False, **kwargs: Any) -> None:
        """Update the current thread's environment with the given key/value pairs.

        Args:
            _excludeNoneValues: If ``True``, keys whose value is ``None``
                are silently skipped instead of being stored.
            **kwargs: Key/value pairs to merge into ``currentEnv``.
        """
        if _excludeNoneValues:
            currentEnv = self.currentEnv
            for k, v in list(kwargs.items()):
                if v is not None:
                    currentEnv[k] = v
        else:
            self.currentEnv.update(kwargs)

    def getUserConfiguration(self, **kwargs: Any) -> None:
        """Return the user configuration for the current session.

        Base implementation returns ``None``.  Overridden by
        ``GnrSqlAppDb`` to return application-level user configuration.
        """
        pass

    # -- store helpers ------------------------------------------------------

    def use_store(self, storename: str | None = None) -> None:
        """Switch the current thread to a different database store.

        Args:
            storename: The store to activate.  Pass ``None`` to reset.
        """
        self.updateEnv(storename=storename)

    def get_dbname(self) -> str:
        """Return the database name for the currently active store.

        Returns:
            The database name.

        Raises:
            KeyError: If the active store is not configured.
        """
        storename = self.currentEnv.get('storename')
        if storename:
            store_params = self.get_store_parameters(storename)
            if not store_params:
                raise KeyError(f'Store {storename} not configured')
            return store_params['database']
        return self.dbname

    def getTenantSchemas(self) -> list[str]:
        """Return a list of tenant schema names from the tenant table.

        Returns:
            A list of schema name strings, or an empty list if no
            tenant table is configured.
        """
        if not self.tenant_table:
            return []
        tblobj = self.table(self.tenant_table)
        tenant_column = tblobj.attributes.get('tenant_column') or 'tenant_schema'
        f = tblobj.query(
            ignorePartition=True,
            subtable='*',
            where=f'${tenant_column} IS NOT NULL',
            columns=f'${tenant_column}',
        ).fetch()
        return [r[tenant_column] for r in f]

    def getApplicationSchemas(self) -> list[str]:
        """Return the SQL schema names for all loaded packages."""
        return [pkg.sqlname for pkg in self.packages.values()]

    def readOnlySchemas(self) -> list[str]:
        """Return the SQL schema names of read-only packages."""
        return [
            pkg.sqlname
            for pkg in self.packages.values()
            if pkg.attributes.get('readOnly')
        ]

    # -- store identity helpers ---------------------------------------------

    def usingRootstore(self) -> bool:
        """Return ``True`` if the current store is the root store."""
        return self.currentStorename == self.rootstore

    def usingMainConnection(self) -> bool:
        """Return ``True`` if the current connection is the main connection."""
        from gnr.sql.gnrsql.helpers import MAIN_CONNECTION_NAME

        return self.currentConnectionName == MAIN_CONNECTION_NAME

    @property
    def currentStorename(self) -> str:
        """The name of the currently active store, defaulting to ``rootstore``."""
        return self.currentEnv.get('storename') or self.rootstore

    @property
    def currentConnectionName(self) -> str:
        """The name of the currently active connection."""
        from gnr.sql.gnrsql.helpers import MAIN_CONNECTION_NAME

        return self.currentEnv.get('connectionName') or MAIN_CONNECTION_NAME

    def setLocale(self) -> None:
        """Apply the current thread's locale setting to the database adapter."""
        if self.currentEnv.get('locale'):
            self.adapter.setLocale(self.currentEnv['locale'])
