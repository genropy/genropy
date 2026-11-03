# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel.containers : Container/list objects and index
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

"""Container and list model objects.

Small leaf classes for table aliases, column groups, subtables,
various list containers, and index objects.
"""

from __future__ import annotations

import os
import re
from typing import Any

from gnr.core.gnrdict import dictExtract
from gnr.sql.gnrsql_exceptions import GnrSqlException
from gnr.sql.gnrsqlmodel.obj import DbModelObj


class DbTableAliasObj(DbModelObj):
    """Compiled model object for a table alias."""

    sqlclass = 'table_alias'

    def _get_relation_path(self) -> str:
        """Return the relation path for this alias."""
        return self.attributes['relation_path']

    relation_path = property(_get_relation_path)


class DbColgroupObj(DbModelObj):
    """Compiled model object for a column group."""

    sqlclass = 'colgroup'


class DbSubtableObj(DbModelObj):
    """Compiled model object for a subtable definition."""

    sqlclass = 'subtable'

    def getCondition(self, sqlparams: dict[str, Any] | None = None) -> str:
        """Return the SQL condition for this subtable.

        Substitutes condition parameter placeholders with namespaced
        keys to avoid collisions.

        Args:
            sqlparams: Mutable dict that receives the parameter bindings.

        Returns:
            The condition SQL string with substituted parameter names.
        """
        kw = dict(self.attributes)
        condition_kw = dictExtract(kw, 'condition_')
        condition = kw.pop('condition')
        for k, v in condition_kw.items():
            if v not in ('*', None):
                newk = 'subtable_condition_{k}'.format(k=k)
                condition = re.sub(
                    "(:)(%s)(\\W|$)" % k,
                    lambda m: '%s%s%s' % (m.group(1), newk, m.group(3)),
                    condition,
                )
                sqlparams[newk] = v
        return condition


class DbTblAliasListObj(DbModelObj):
    """List container for table aliases."""

    sqlclass = "tblalias_list"


class DbColAliasListObj(DbModelObj):
    """List container for virtual/alias columns."""

    sqlclass = "virtual_columns_list"


class DbColumnListObj(DbModelObj):
    """List container for physical columns."""

    sqlclass = "column_list"


class DbColgroupListObj(DbModelObj):
    """List container for column groups."""

    sqlclass = "colgroup_list"


class DbSubtableListObj(DbModelObj):
    """List container for subtable definitions."""

    sqlclass = "subtable_list"


class DbIndexListObj(DbModelObj):
    """List container for indexes."""

    sqlclass = "index_list"


class DbPackageListObj(DbModelObj):
    """List container for packages."""

    sqlclass = "package_list"


class DbTableListObj(DbModelObj):
    """List container for tables."""

    sqlclass = "table_list"


class DbIndexObj(DbModelObj):
    """Compiled model object for a database index."""

    sqlclass = "index"

    def _get_sqlname(self) -> str:
        """Return the SQL name for this index.

        Defaults to ``tablename_columns_idx`` if not explicitly set.
        """
        return self.attributes.get(
            'sqlname',
            '%s_%s_idx' % (self.table.sqlname, self.getAttr('columns').replace(',', '_')),
        )

    sqlname = property(_get_sqlname)

    def _get_table(self) -> Any:
        """Return the ``DbTableObj`` owning this index."""
        return self.parent.parent

    table = property(_get_table)


class DbSqlScriptListObj(DbModelObj):
    """List container for the SQL scripts of a table or a package."""

    sqlclass = "sql_script_list"

    def expandedText(self, tenant_schema: str | None = None) -> str:
        """Return the expanded scripts joined in declaration order.

        Args:
            tenant_schema: The tenant schema the scripts are expanded for.
        """
        return '\n'.join(script.expandedText(tenant_schema=tenant_schema)
                         for script in self.children.values())


class DbSqlScriptObj(DbModelObj):
    """Compiled model object for a SQL script declared with ``sql()``.

    The script belongs to a table or to a package. Its text is the ``text``
    attribute, or the content of ``sql_file`` in the ``model`` folder of a
    package. Every ``{name}`` marker is replaced by a model property of the
    owner or by a ``marker_<name>`` attribute; other braces stay untouched.
    """

    sqlclass = "sql_script"

    def _get_owner(self) -> Any:
        """Return the ``DbTableObj`` or ``DbPackageObj`` owning this script."""
        return self.parent.parent

    owner = property(_get_owner)

    def _get_isTableScript(self) -> bool:
        """Return ``True`` when the script belongs to a table."""
        return self.owner.sqlclass == 'table'

    isTableScript = property(_get_isTableScript)

    def rawText(self) -> str:
        """Return the script text before marker replacement."""
        text = self.attributes.get('text')
        if text is not None:
            return text
        sql_file = self.attributes['sql_file']
        owner = self.owner
        pkg = self.attributes.get('pkg') or (owner.pkg.name if self.isTableScript else owner.name)
        application = self.db.application
        if application is None:
            raise GnrSqlException(
                f"sql_file '{sql_file}' needs an application to find package '{pkg}'")
        path = os.path.join(application.packages[pkg].packageFolder, 'model', sql_file)
        with open(path) as sql_file_handle:
            return sql_file_handle.read()

    def modelMarkers(self, tenant_schema: str | None = None) -> dict[str, Any]:
        """Return the model properties the script can reference.

        Args:
            tenant_schema: The tenant schema the script is expanded for;
                ``None`` for the package schema.
        """
        owner = self.owner
        if not self.isTableScript:
            return dict(sqlschema=owner.sqlname, name=owner.name, pkg=owner.name)
        schema = tenant_schema or owner.pkg.sqlname
        return dict(
            sqlschema=schema,
            sqlname=owner.sqlname,
            sqlfullname='%s.%s' % (self.adapter.adaptSqlName(schema), owner.adapted_sqlname),
            fullname=owner.fullname,
            name=owner.name,
            pkey=owner.pkey,
            pkeys=','.join(owner.pkeys),
            lastTS=owner.lastTS,
            logicalDeletionField=owner.logicalDeletionField,
            draftField=owner.draftField,
            pkg=owner.pkg.name,
        )

    def expandedText(self, tenant_schema: str | None = None) -> str:
        """Return the script text with every known marker replaced.

        Args:
            tenant_schema: The tenant schema the script is expanded for.

        Raises:
            GnrSqlException: If a ``marker_*`` attribute shadows a model
                property, or if the text uses a marker that has no value.
        """
        markers = self.modelMarkers(tenant_schema=tenant_schema)
        declared = dictExtract(self.attributes, 'marker_')
        shadowed = set(declared).intersection(markers)
        if shadowed:
            raise GnrSqlException(
                f"sql() markers {sorted(shadowed)} shadow model properties of {self.owner.name}")
        markers.update(declared)
        text = self.rawText()
        for name, value in markers.items():
            token = '{%s}' % name
            if token not in text:
                continue
            if value is None or value == '':
                raise GnrSqlException(f"Marker {token} has no value in {self.owner.name}")
            text = text.replace(token, str(value))
        return text

