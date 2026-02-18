# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel.obj : Base model object and package object
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

"""Base model objects: ``DbModelObj`` and ``DbPackageObj``.

``DbModelObj`` is the root class for every compiled model node
(packages, tables, columns, indexes, etc.).  ``DbPackageObj``
represents a single package within the model.
"""

from __future__ import annotations

from typing import Any

from gnr.core.gnrstructures import GnrStructObj
from gnr.sql.gnrsql_exceptions import GnrSqlMissingTable


class DbModelObj(GnrStructObj):
    """Base class for all compiled model objects.

    Handles mixin loading, provides access to the database root,
    and exposes common naming properties (``sqlname``, ``name_short``,
    ``name_long``, ``name_full``).
    """

    def init(self) -> None:
        """Initialize the object after construction.

        Resolves the database root reference, applies any registered
        mixins, and delegates to :meth:`doInit` for subclass-specific
        initialization.
        """
        self._dbroot = self.root.rootparent.db

        mixpath = self._getMixinPath()
        mixobj = self._getMixinObj()
        if mixpath:
            mixobj.mixin(self.db.model.mixins[mixpath], attributes='_plugins,_pluginId')
        mixin = self.attributes.get('mixin')
        if mixin:
            if ':' not in mixin:
                mixin = '%s:%s' % (self.module.__module__, mixin)
            mixobj.mixin(mixin)
        self.doInit()

    def _getMixinPath(self) -> str | None:
        """Return the mixin registry path for this object, or ``None``."""
        return None

    def _getMixinObj(self) -> Any:
        """Return the object that receives the mixin.

        Defaults to ``self``.  Overridden by ``DbTableObj`` to return
        the ``SqlTable`` proxy instead.
        """
        return self

    def doInit(self) -> None:
        """Subclass hook called at the end of :meth:`init`."""
        pass

    def __bool__(self) -> bool:
        return True

    def _get_dbroot(self) -> Any:
        return self._dbroot

    dbroot = property(_get_dbroot)
    db = dbroot

    def _get_adapter(self) -> Any:
        return self.dbroot.adapter

    adapter = property(_get_adapter)

    def _get_sqlname(self) -> str:
        return self.attributes.get('sqlname', self.name)

    sqlname = property(_get_sqlname)

    @property
    def adapted_sqlname(self) -> str:
        """Return the SQL name adapted for the current database engine."""
        return self.adapter.adaptSqlName(self.sqlname)

    def _set_name_short(self, name: str) -> None:
        self.attributes['name_short'] = name

    def _get_name_short(self) -> str:
        return self.attributes.get('name_short', self.attributes.get('name_long', self.name))

    name_short = property(_get_name_short, _set_name_short)

    def _set_name_long(self, name: str) -> None:
        self.attributes['name_long'] = name

    def _get_name_long(self) -> str:
        return self.attributes.get('name_long', self.name_short)

    name_long = property(_get_name_long, _set_name_long)

    def _set_name_full(self, name: str) -> None:
        self.attributes['name_full'] = name

    def _get_name_full(self) -> str:
        return self.attributes.get('name_full', self.name_long)

    name_full = property(_get_name_full, _set_name_full)

    def getTag(self) -> str:
        """Return the tag string for this object's SQL class."""
        return self.sqlclass or self._sqlclass

    def getAttr(self, attr: str | None = None, dflt: Any = None) -> Any:
        """Return an attribute value or the full attribute dict.

        Args:
            attr: The attribute name.  If ``None``, the entire
                attribute dict is returned.
            dflt: Default value when *attr* is not found.
        """
        if attr:
            return self.attributes.get(attr, dflt)
        else:
            return self.attributes


class DbPackageObj(DbModelObj):
    """Compiled model object representing a database package."""

    sqlclass = "package"

    def _getMixinPath(self) -> str:
        """Return the mixin registry path for this package."""
        return 'pkg.%s' % self.name

    def _get_tables(self) -> Any:
        """Return the table list for this package."""
        return self['tables'] or {}  # temporary FIX

    tables = property(_get_tables)

    def _get_sqlname(self) -> str:
        """Return the SQL schema name for this package."""
        return self.attributes.get('sqlschema', self.attributes.get('sqlname', self.name))

    sqlname = property(_get_sqlname)

    def dbtable(self, name: str) -> Any:
        """Return the ``SqlTable`` proxy for a table by name.

        Args:
            name: The table name within this package.

        Returns:
            The ``SqlTable`` instance, or ``None`` if the table's
            ``dbtable`` is not set.
        """
        return self.table(name).dbtable

    def table(self, name: str) -> Any:
        """Return a ``DbTableObj`` by name.

        Args:
            name: The table name within this package.

        Returns:
            The ``DbTableObj`` instance.

        Raises:
            GnrSqlMissingTable: If the table does not exist.
        """
        table = self['tables.%s' % name]
        if table is None:
            raise GnrSqlMissingTable(
                "Table '%s' undefined in package: '%s'" % (name, self.name)
            )
        return table

    def tableSqlName(self, tblobj: Any) -> str:
        """Return the SQL name for a table within this package.

        Applies the package's ``sqlprefix`` (defaults to the package
        name) to produce names like ``pkg_tablename``.

        Args:
            tblobj: A ``DbTableObj`` instance.

        Returns:
            The SQL table name.
        """
        sqlprefix = self.attributes.get('sqlprefix', True)
        if not sqlprefix:
            return tblobj.name
        else:
            if sqlprefix is True:
                sqlprefix = self.name
            return '%s_%s' % (sqlprefix, tblobj.name)

    def _get_sqlschema(self) -> str:
        """Return the SQL schema for this package."""
        return self.db.adapter.adaptSqlSchema(
            self.attributes.get('sqlschema', self.dbroot.main_schema)
        )

    sqlschema = property(_get_sqlschema)

    def toJson(self, **kwargs: Any) -> dict[str, Any]:
        """Return a JSON-serializable dict describing this package.

        Returns:
            A dict with ``code``, ``name``, and ``tables`` keys.
        """
        return dict(
            code=self.name,
            name=self.name_long,
            tables=[t.toJson() for t in self.tables.values()],
        )
