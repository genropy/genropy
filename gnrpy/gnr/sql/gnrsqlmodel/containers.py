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

import re
from typing import Any

from gnr.core.gnrdict import dictExtract
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
