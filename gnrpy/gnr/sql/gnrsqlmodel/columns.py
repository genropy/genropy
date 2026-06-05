# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel.columns : Column model objects
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

"""Column model objects: real columns, virtual columns and alias wrappers.

Provides ``DbBaseColumnObj`` (shared base), ``DbColumnObj`` (physical columns),
``DbVirtualColumnObj`` (computed/alias columns) and ``AliasColumnWrapper``
(thin proxy for alias resolution).
"""

from __future__ import annotations

from typing import Any

from gnr.core.gnrstring import boolean
from gnr.sql.gnrsqlmodel.obj import DbModelObj


class DbBaseColumnObj(DbModelObj):
    """Base class for both real and virtual column objects.

    Provides common properties (``dtype``, ``readonly``, ``pkg``,
    ``table``, ``sqlfullname``, ``fullname``) and relation-lookup
    helpers.
    """

    def _get_dtype(self) -> str:
        """Return the GenroPy data type code (default ``'T'``)."""
        return self.attributes.get('dtype', 'T')

    dtype = property(_get_dtype)

    def _get_isReserved(self) -> bool:
        """Return ``True`` if the column belongs to a reserved group."""
        return self.attributes.get('group', '').startswith('_')

    isReserved = property(_get_isReserved)

    def _get_readonly(self) -> bool:
        """Return ``True`` if the column is read-only."""
        return (self.attributes.get('readonly', 'N').upper() == 'Y')

    readonly = property(_get_readonly)

    def _get_encrypted(self) -> str | None:
        """Return the encryption mode (``'R'``, ``'Q'``, ``'X'``) or ``None``."""
        return self.attributes.get('encrypted')

    encrypted = property(_get_encrypted)

    def _get_pkg(self) -> Any:
        """Return the ``DbPackageObj`` owning this column."""
        return self.parent.parent.pkg

    pkg = property(_get_pkg)

    def _get_table(self) -> Any:
        """Return the ``DbTableObj`` owning this column."""
        return self.parent.parent

    table = property(_get_table)

    def _get_sqlschema(self) -> str:
        """Return the SQL schema for this column's table."""
        return 'sqlschema', self.table.sqlschema

    sqlschema = property(_get_sqlschema)

    def _get_sqlfullname(self) -> str:
        """Return the fully-qualified SQL name (``schema.table.column``)."""
        return '%s.%s' % (self.table.sqlfullname, self.sqlname)

    sqlfullname = property(_get_sqlfullname)

    def _get_fullname(self) -> str:
        """Return the model full name (``pkg.table.column``)."""
        return '%s.%s' % (self.table.fullname, self.name)

    fullname = property(_get_fullname)

    def _set_print_width(self, size: Any) -> None:
        self.attributes['print_width'] = size

    def _get_print_width(self) -> Any:
        # REVIEW: property getter with side effect — mutates
        # self.attributes on first access.
        if 'print_width' not in self.attributes:
            self.attributes['print_width'] = self.table.dbtable.getColumnPrintWidth(self)
        return self.attributes['print_width']

    print_width = property(_get_print_width, _set_print_width)

    def getPermissions(self, **kwargs: Any) -> Any:
        """Return column-level permissions from the user configuration."""
        return self.table.getColPermissions(self.name, **kwargs)

    def doInit(self) -> None:
        """Set default ``dtype`` and apply custom-type attribute mixins."""
        if not self.attributes.get('dtype'):
            if self.attributes.get('size'):
                self.attributes['dtype'] = 'A'
            else:
                self.attributes['dtype'] = 'T'
        enc = self.attributes.get('encrypted')
        if enc is True:
            self.attributes['encrypted'] = 'R'
        attributes_mixin_handler = getattr(
            self.pkg, 'custom_type_%s' % self.attributes['dtype'], None
        )
        if attributes_mixin_handler:
            attributes_mixin = dict(attributes_mixin_handler())
            self.attributes['dtype'] = attributes_mixin.pop('dtype')
            attributes_mixin.update(self.attributes)
            self.attributes = attributes_mixin

    def toJson(self, **kwargs: Any) -> dict[str, Any]:
        """Return a JSON-serializable dict describing this column.

        Returns:
            A dict with keys ``code``, ``name``, ``dtype``,
            ``column_class``, and optionally ``related_to``.
        """
        result = dict(
            code=self.name,
            name=self.name_long,
            dtype=self.dtype,
            column_class=self.sqlclass,
        )
        relatedColumn = self.relatedColumn()
        if relatedColumn:
            result['related_to'] = relatedColumn.fullname
        return result

    def _fillRelatedColumn(self, related_column: str) -> str:
        """Normalize a related-column path to ``pkg.table.column`` form.

        Args:
            related_column: A two- or three-part dotted path.

        Returns:
            The fully qualified ``pkg.table.column`` string.
        """
        relation_list = related_column.split('.')
        if len(relation_list) == 3:
            pkg, tbl, column = relation_list
        else:
            tbl, column = relation_list
            pkg = self.pkg.name
        return f'{pkg}.{tbl}.{column}'

    def relatedTable(self) -> Any:
        """Return the ``DbTableObj`` related through this column, if any."""
        joiner = self.relatedColumnJoiner()
        if joiner:
            return self.dbroot.model.table(joiner['one_relation'])

    def relatedColumn(self) -> Any:
        """Return the ``DbColumnObj`` related through this column, if any."""
        joiner = self.relatedColumnJoiner()
        if joiner:
            return self.dbroot.model.column(joiner['one_relation'])

    def relatedColumnJoiner(self) -> dict[str, Any] | None:
        """Return the joiner dict for the column's outgoing relation.

        Returns:
            The joiner dict if this column has a many-to-one relation,
            or ``None``.
        """
        r = self.table.relations.getAttr('@%s' % self.name)
        if r and r['joiner']['many_relation'] == self.fullname:
            return r['joiner']


class DbColumnObj(DbBaseColumnObj):
    """Compiled model object for a physical database column."""

    sqlclass = 'column'

    def _captureChildren(self, children: Any) -> bool:
        self.column_relation = children['relation'] if children else None
        return False

    def _get_sqlname(self) -> str:
        """Return the SQL column name, considering localization.

        For localized columns, returns the language-specific column name
        (e.g. ``description_it``) when the current locale differs from
        the default language.
        """
        base_sqlname = self.attributes.get('sqlname', self.name)
        if self.attributes.get('localized'):
            default_language = self.db.currentEnv.get('default_language')
            current_language = self.db.currentEnv.get('current_language')
            if default_language and current_language and current_language != default_language:
                return f"{base_sqlname}_{current_language}"
        return base_sqlname

    sqlname = property(_get_sqlname)

    def doInit(self) -> None:
        """Initialize the column: register relations, indexes and triggers."""
        super(DbColumnObj, self).doInit()
        self.table.sqlnamemapper[self.name] = self.adapted_sqlname
        column_relation = self.structnode.value['relation']
        if column_relation is not None:
            reldict = dict(column_relation.attributes)
            reldict['related_column'] = self._fillRelatedColumn(reldict['related_column'])
            if 'cnd' in reldict:
                reldict['mode'] = 'custom'
            self.dbroot.model._columnsWithRelations[
                (self.pkg.name, self.table.name, self.name)
            ] = reldict
        indexed = boolean(self.attributes.get('indexed'))
        unique = boolean(self.attributes.get('unique'))
        if indexed or unique:
            self.table._indexedColumn[self.name] = {'columns': self.name, 'unique': unique}
        trigger_table = self.attributes.get('trigger_table')
        for trigType in ('onInserting', 'onUpdating', 'onDeleting',
                         'onInserted', 'onUpdated', 'onDeleted'):
            trigFunc = self.attributes.get(trigType)
            if trigFunc:
                self.table._fieldTriggers.setdefault(trigType, []).append(
                    (self.name, trigFunc, trigger_table)
                )

    def rename(self, newname: str) -> None:
        """Rename this column in the database.

        Args:
            newname: The new SQL column name.
        """
        self.db.adapter.renameColumn(self.table.sqlname, self.sqlname, newname)


class DbVirtualColumnObj(DbBaseColumnObj):
    """Compiled model object for a virtual (computed/alias) column."""

    sqlclass = 'virtual_column'

    def _captureChildren(self, children: Any) -> bool:
        if children and 'relation' in children:
            self.column_relation = children['relation']
            return False
        return True

    def doInit(self) -> None:
        """Initialize the virtual column: register virtual relations."""
        super(DbVirtualColumnObj, self).doInit()
        column_relation = None
        if self.structnode.value and 'relation' in self.structnode.value:
            column_relation = self.structnode.value['relation']
        if column_relation is not None:
            self.attributes['virtual'] = True
            reldict = dict(column_relation.attributes)
            reldict['related_column'] = self._fillRelatedColumn(reldict['related_column'])
            if self.attributes.get('join_column'):
                self.attributes['relation_path'] = (
                    f'@{self.name}.{reldict["related_column"].split(".")[-1]}'
                )
            reldict['virtual'] = True
            reldict['one_name'] = reldict.get('one_name') or self.name_long
            self.dbroot.model._columnsWithRelations[
                (self.pkg.name, self.table.name, self.name)
            ] = reldict

    def _get_relation_path(self) -> str | None:
        """Return the relation path, if this is an alias column."""
        return self.attributes.get('relation_path')

    relation_path = property(_get_relation_path)

    def _get_composed_of(self) -> str | None:
        """Return the comma-separated list of composed columns, if any."""
        return self.attributes.get('composed_of')

    composed_of = property(_get_composed_of)

    def _get_join_column(self) -> bool | None:
        """Return ``True`` if this is a join column."""
        return self.attributes.get('join_column')

    join_column = property(_get_join_column)

    def _get_sql_formula(self) -> str | None:
        """Return the SQL formula expression, if any."""
        return self.attributes.get('sql_formula')

    sql_formula = property(_get_sql_formula)

    def _get_select(self) -> Any:
        """Return the sub-select definition, if any."""
        return self.attributes.get('select')

    select = property(_get_select)

    def _get_exists(self) -> Any:
        """Return the EXISTS sub-query definition, if any."""
        return self.attributes.get('exists')

    exists = property(_get_exists)

    def _get_py_method(self) -> str | None:
        """Return the Python method name for computed columns."""
        return self.attributes.get('py_method')

    py_method = property(_get_py_method)

    def _get_readonly(self) -> bool:
        """Virtual columns are always read-only."""
        return True

    readonly = property(_get_readonly)

    @property
    def virtual(self) -> bool:
        """Return ``True`` if this column is explicitly marked virtual."""
        return self.attributes.get('virtual', False)


class AliasColumnWrapper(DbModelObj):
    """Thin wrapper that merges alias attributes onto an original column.

    Used when resolving alias columns: the wrapper presents the merged
    attributes of the original column and the alias definition, while
    delegating attribute lookups to the original column.
    """

    def __init__(
        self,
        originalColumn: Any = None,
        aliasAttributes: dict[str, Any] | None = None,
    ) -> None:
        mixedattributes = dict(originalColumn.attributes)
        # REVIEW: pop('tag') and pop('relation_path') without defaults
        # will raise KeyError if the keys are missing.
        colalias_attributes = dict(aliasAttributes)
        colalias_attributes.pop('tag')
        self.relation_path = colalias_attributes.pop('relation_path')
        mixedattributes.update(colalias_attributes)
        virtual_column = mixedattributes.pop('virtual_column', None)
        if virtual_column:
            self.sqlclass = 'virtual_column'
        self.originalColumn = originalColumn
        self.attributes = mixedattributes

    def __getattr__(self, name: str) -> Any:
        return getattr(self.originalColumn, name)
