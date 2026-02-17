# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel.table : DbTableObj compiled model object
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

"""Compiled model object for a database table.

``DbTableObj`` is the largest model class, handling column resolution,
relation navigation, virtual-column management, and JSON serialization.
"""

from __future__ import annotations

import copy
from typing import Any

from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.sql import AdapterCapabilities
from gnr.sql import logger
from gnr.sql.gnrsql_exceptions import (
    GnrSqlException, GnrSqlMissingField, GnrSqlMissingColumn, GnrSqlRelationError,
)
from gnr.sql.gnrsqlmodel.obj import DbModelObj
from gnr.sql.gnrsqlmodel.columns import DbVirtualColumnObj, AliasColumnWrapper
from gnr.sql.gnrsqlmodel.resolvers import RelationTreeResolver
from gnr.sql.gnrsqlmodel.helpers import bagItemFormula
from gnr.sql.gnrsqltable import SqlTable


class DbTableObj(DbModelObj):
    """Compiled model object representing a database table.

    Manages the table's columns (real and virtual), indexes, relations,
    subtables, and provides methods for column/relation resolution and
    JSON serialization.
    """

    sqlclass = 'table'

    def doInit(self) -> None:
        """Initialize the table: create the ``SqlTable`` proxy and data structures."""
        self.dbtable.onIniting()
        self._sqlnamemapper = {}
        self._indexedColumn = {}
        self._fieldTriggers = {}
        self.allcolumns = []
        self.dbtable.onInited()

    def afterChildrenCreation(self) -> None:
        """Ensure required child containers exist after model build."""
        objclassdict = self.root.objclassdict
        if not self.columns:
            self.children['columns'] = objclassdict['column_list'](parent=self)
        if not self.indexes:
            self.children['indexes'] = objclassdict['index_list'](parent=self)
        if 'virtual_columns' not in self.children:
            self.children['virtual_columns'] = objclassdict['virtual_columns_list'](parent=self)
        if not self.table_aliases:
            self.children['table_aliases'] = objclassdict['tblalias_list'](parent=self)
        indexesobj = self.indexes
        for colname, indexargs in list(self._indexedColumn.items()):
            indexname = "%s_%s_key" % (self.name, indexargs['columns'].replace(',', '_'))
            indexesobj.children[indexname] = objclassdict['index'](parent=self.indexes, attrs=indexargs)

        if not self.relations:
            self.children['relations'] = self.newRelationResolver(cacheTime=-1)

    def newRelationResolver(self, **kwargs: Any) -> RelationTreeResolver:
        """Create a new ``RelationTreeResolver`` for this table.

        Args:
            **kwargs: Extra keyword arguments forwarded to the resolver.

        Returns:
            A configured ``RelationTreeResolver`` instance.
        """
        child_kwargs = {
            'main_tbl': '%s.%s' % (self.pkg.name, self.name),
            'tbl_name': self.name,
            'pkg_name': self.pkg.name,
        }
        child_kwargs.update(kwargs)
        relationTree = RelationTreeResolver(**child_kwargs)
        relationTree.setDbroot(self.dbroot)
        return relationTree

    def _getMixinPath(self) -> str:
        return 'tbl.%s.%s' % (self.pkg.name, self.name)

    def _getMixinObj(self) -> Any:
        self.dbtable = SqlTable(self)
        return self.dbtable

    # -- Properties -----------------------------------------------------------

    @property
    def maintable(self) -> Any:
        """Return the main table object for subtables, or ``None``."""
        if hasattr(self, '_maintable'):
            return self._maintable
        maintable = self.attributes.get('maintable')
        self._maintable = self.db.table(maintable) if maintable else None
        return self._maintable

    @property
    def multi_tenant(self) -> Any:
        """Return the multi-tenant flag, inheriting from the package if unset."""
        multi_tenant = self.attributes.get('multi_tenant', None)
        if multi_tenant is None:
            return self.pkg.attributes.get('multi_tenant')
        return multi_tenant

    def _get_pkg(self) -> Any:
        """Return the ``DbPackageObj`` containing this table."""
        return self.parent.parent

    pkg = property(_get_pkg)

    def _get_fullname(self) -> str:
        """Return the model full name (``pkg.table``)."""
        return '%s.%s' % (self.pkg.name, self.name)

    fullname = property(_get_fullname)

    def _get_name_plural(self) -> str:
        """Return the plural name for UI display."""
        return self.attributes.get('name_plural') or self.name_long

    name_plural = property(_get_name_plural)

    @property
    def _refsqltable(self) -> Any:
        """Return the reference table for SQL naming (self or maintable)."""
        return self.maintable or self

    def _get_sqlschema(self, ignore_tenant: bool | None = None) -> str | None:
        """Return the SQL schema, considering multi-tenancy."""
        schema = self._refsqltable.attributes.get('sqlschema', self._refsqltable.pkg.sqlschema)
        tenant_schema = self.db.currentEnv.get('tenant_schema')
        if tenant_schema == '_main_':
            ignore_tenant = True
        return (
            (tenant_schema or schema)
            if (self._refsqltable.multi_tenant and not ignore_tenant)
            else schema
        )

    sqlschema = property(_get_sqlschema)

    def _get_sqlname(self) -> str:
        """Return the SQL table name."""
        sqlname = self._refsqltable.attributes.get('sqlname')
        if not sqlname:
            sqlname = self._refsqltable.pkg.tableSqlName(self._refsqltable)
        return sqlname

    sqlname = property(_get_sqlname)

    def _get_sqlfullname(self, ignore_tenant: bool | None = None) -> str:
        """Return the fully-qualified SQL table name (``schema.table``)."""
        if not self.db.adapter.has_capability(AdapterCapabilities.SCHEMAS):
            return self.adapted_sqlname
        else:
            schema = self._get_sqlschema(ignore_tenant)
            if schema:
                return '%s.%s' % (self.db.adapter.adaptSqlName(schema), self.adapted_sqlname)
            return self.adapted_sqlname

    sqlfullname = property(_get_sqlfullname)

    def _get_sqlnamemapper(self) -> dict[str, str]:
        return self._sqlnamemapper

    sqlnamemapper = property(_get_sqlnamemapper)

    def _get_pkeys(self) -> list[str]:
        """Return the list of primary key column names.

        For composite keys (defined via ``composed_of``), returns
        the individual column names.
        """
        if not self.pkey:
            logger.critical('Missing pkey in table %s', self.fullname)
            return []
        if self.column(self.pkey) is None:
            raise AssertionError(
                f'Missing column defined as pkey {self.pkey} in table {self.fullname}'
            )
        if self.column(self.pkey).attributes.get('composed_of'):
            return self.column(self.pkey).attributes.get('composed_of').split(',')
        return [self.pkey]

    pkeys = property(_get_pkeys)

    def _get_pkey(self) -> str:
        """Return the primary key column name."""
        return self.attributes.get('pkey', '')

    pkey = property(_get_pkey)

    def _get_lastTS(self) -> str:
        """Return the last-timestamp column name."""
        return self.attributes.get('lastTS', '')

    lastTS = property(_get_lastTS)

    def _get_logicalDeletionField(self) -> str:
        """Return the logical deletion field name."""
        return self.attributes.get('logicalDeletionField', '')

    logicalDeletionField = property(_get_logicalDeletionField)

    def _get_draftField(self) -> str:
        """Return the draft field name."""
        return self.attributes.get('draftField', '')

    draftField = property(_get_draftField)

    def _get_noChangeMerge(self) -> str:
        """Return the noChangeMerge flag."""
        return self.attributes.get('noChangeMerge', '')

    noChangeMerge = property(_get_noChangeMerge)

    def _get_rowcaption(self) -> str:
        """Return the row caption expression.

        Falls back to ``$caption_field`` or ``$pkey`` if not explicitly set.
        """
        attr = self.attributes
        rowcaption = attr.get('rowcaption')
        if not rowcaption and attr.get('caption_field'):
            rowcaption = '$%(caption_field)s' % attr
        rowcaption = rowcaption or '$%(pkey)s' % attr
        return rowcaption

    rowcaption = property(_get_rowcaption)

    @property
    def newrecord_caption(self) -> str:
        """Return the caption for new records."""
        return self.attributes.get('newrecord_caption', self.name_long)

    def _get_queryfields(self) -> str | None:
        """Return custom query fields, if any."""
        return self.attributes.get('queryfields', None)

    queryfields = property(_get_queryfields)

    def _get_columns(self) -> Any:
        """Return the column list object."""
        return self['columns']

    columns = property(_get_columns)

    def _get_indexes(self) -> Any:
        """Return the index list object."""
        return self['indexes']

    indexes = property(_get_indexes)

    def _get_relations(self) -> Any:
        """Return the relations resolver/container."""
        return self['relations']

    relations = property(_get_relations)

    @property
    def subtables(self) -> Any:
        """Return the subtable list, or ``None``."""
        return self['subtables']

    @property
    def dependencies(self) -> list[tuple[str, bool]]:
        """Return the list of foreign-key dependencies as ``(table, deferred)`` tuples."""
        r = []
        for x, deferred, foreignkey, onDelete in self.relations_one.digest(
            '#v,#a.deferred,#a.foreignkey,#a.onDelete'
        ):
            reltbl = '.'.join(x.split('.')[0:-1])
            if foreignkey and reltbl != self.fullname:
                r.append((reltbl, deferred or onDelete == 'setnull'))
        return r

    def pluggedColumns(self, packages: list[str] | None = None) -> list[str]:
        """Return column names added by external packages.

        Args:
            packages: Optional list of package names to filter.
        """
        pkgId = self.pkg.id
        return [
            colname for colname, colobj in self.columns.items()
            if (colobj.attributes.get('_owner_package', pkgId) != pkgId
                and (not packages or pkgId in packages))
        ]

    # -- Virtual columns ------------------------------------------------------

    def getVirtualColumn(self, fld: str, sqlparams: dict[str, Any] | None = None) -> Any:
        """Resolve a virtual column by name, with optional parameter override.

        Args:
            fld: The virtual column name.
            sqlparams: Optional dict of SQL parameters that may contain
                column-definition overrides.

        Returns:
            A ``DbVirtualColumnObj`` or ``None``.
        """
        result = self.virtual_columns[fld]
        if result is not None:
            return result
        vc_pars = sqlparams.get(fld, None)
        if vc_pars is None:
            return
        pars = dict(vc_pars)
        fld = pars.pop('field')
        col = self.getVirtualColumn(fld, sqlparams=sqlparams)
        if col is None:
            return
        sn = copy.deepcopy(col._GnrStructObj__structnode)
        sn.label = fld
        snattr = sn.attr
        snattr.update(pars)
        result = DbVirtualColumnObj(structnode=sn, parent=self['virtual_columns'])
        return result

    @property
    def virtual_columns(self) -> Any:
        """Return the virtual columns, including dynamic and local ones.

        Caches the result in ``currentEnv`` to avoid repeated computation
        within the same request.
        """
        # REVIEW: this property has side effects — it mutates
        # virtual_columns.children and stores into currentEnv.
        # Not thread-safe: concurrent requests could race between
        # the cache check and the cache write.
        vc_key = '_virtual_columns_{}'.format(self.dbtable.fullname.replace('.', '_'))
        env_virtual_columns = self.db.currentEnv.get(vc_key)
        if env_virtual_columns:
            return env_virtual_columns
        virtual_columns = self['virtual_columns']
        local_virtual_columns = self.db.localVirtualColumns(self.fullname)
        if local_virtual_columns:
            for node in local_virtual_columns:
                obj = DbVirtualColumnObj(structnode=node, parent=virtual_columns)
                virtual_columns.children[obj.name.lower()] = obj
        for node in self.dynamic_columns:
            obj = DbVirtualColumnObj(structnode=node, parent=virtual_columns)
            virtual_columns.children[obj.name.lower()] = obj
        self._handle_variant_columns(virtual_columns=virtual_columns)
        self.db.currentEnv[vc_key] = virtual_columns
        return virtual_columns

    @property
    def composite_columns(self) -> Bag:
        """Return a Bag of virtual columns that are composite (``composed_of``)."""
        return Bag([
            (colname, colobj)
            for colname, colobj in self['virtual_columns'].items()
            if colobj.attributes.get('composed_of')
        ])

    @property
    def static_virtual_columns(self) -> Bag:
        """Return a Bag of virtual columns marked as static."""
        return Bag([
            (colname, colobj)
            for colname, colobj in self['virtual_columns'].items()
            if colobj.attributes.get('static')
        ])

    @property
    def dynamic_columns(self) -> Bag:
        """Return a Bag of dynamically-generated formula columns.

        Scans the ``SqlTable`` proxy for methods named
        ``formulaColumn_*`` and collects their results.
        """
        result = Bag()
        dbtable = self.dbtable
        fmethods = [
            v for v in [
                getattr(dbtable, k) for k in dir(dbtable) if k.startswith('formulaColumn_')
            ]
        ]
        for f in fmethods:
            r = f()
            if not isinstance(r, list):
                r = [r]
            for c in r:
                kw = dict(c)
                kw['tag'] = 'virtual_column'
                kw['virtual_column'] = True
                result.setItem(kw.pop('name'), None, **kw)
        return result

    @property
    def full_virtual_columns(self) -> Any:
        """Return virtual columns including custom ones."""
        virtual_columns = self.virtual_columns
        custom_virtual_columns = self.db.customVirtualColumns(self.fullname)
        if custom_virtual_columns:
            for node in custom_virtual_columns:
                obj = DbVirtualColumnObj(structnode=node, parent=virtual_columns)
                virtual_columns.children[obj.name.lower()] = obj
        return virtual_columns

    def _handle_variant_columns(self, virtual_columns: Any = None) -> None:
        """Process variant columns and add them to the virtual columns list.

        For each column with a ``variant`` attribute, calls the
        corresponding ``variantColumn_*`` method on the ``SqlTable``
        proxy and adds the result as virtual columns.
        """
        variant_columns = Bag()
        for colname, colobj in self.columns.items() + virtual_columns.items():
            colattr = colobj.attributes
            variant = colattr.get('variant')
            if not variant:
                continue
            for variant_name in variant.split(','):
                variant_kwargs = dictExtract(
                    colattr,
                    'variant_{variant_name}_'.format(variant_name=variant_name),
                )
                r = getattr(
                    self.dbtable,
                    'variantColumn_{variant_name}'.format(variant_name=variant_name),
                )(colname, **variant_kwargs)
                if not isinstance(r, list):
                    r = [r]
                for c in r:
                    kw = dict(c)
                    kw['tag'] = 'virtual_column'
                    kw['virtual_column'] = True
                    variant_columns.setItem(kw.pop('name'), None, **kw)
        for node in variant_columns:
            obj = DbVirtualColumnObj(structnode=node, parent=virtual_columns)
            virtual_columns.children[obj.name.lower()] = obj

    def _get_table_aliases(self) -> Any:
        """Return the table aliases list."""
        return self['table_aliases']

    table_aliases = property(_get_table_aliases)

    def starColumns(self, bagFields: bool = False) -> list[str]:
        """Return the list of ``$column`` expressions for SELECT *.

        Args:
            bagFields: If ``True``, include Bag (XML) columns.
        """
        result = [
            '${}'.format(colname)
            for colname, colobj in self.columns.items()
            if bagFields or colobj.dtype != 'X'
        ]
        result += ['${}'.format(colname) for colname in self.static_virtual_columns.keys()]
        return result

    def getColPermissions(self, name: str, **checkPermissions: Any) -> dict[str, Any]:
        """Return column-level permissions for the given column.

        Args:
            name: The column name.
            **checkPermissions: Permission context kwargs.
        """
        user_conf = self.dbtable.getUserConfiguration(**checkPermissions)
        colconf = user_conf.getAttr('cols_permission.%s' % name) or dict()
        return dict([('user_%s' % k, v) for k, v in list(colconf.items()) if v is not None])

    def subtable(self, name: str) -> Any:
        """Return a subtable by name.

        Args:
            name: The subtable name.
        """
        return self['subtables.{name}'.format(name=name)]

    # -- Column resolution ----------------------------------------------------

    def column(self, name: str) -> Any:
        """Resolve a column by name or relation path.

        Handles physical columns, virtual columns (aliases, formulas,
        computed), and ``@relation.column`` paths.

        Args:
            name: A column name, or a relation path starting with ``@``.

        Returns:
            A column object, or ``None``.

        Raises:
            GnrSqlMissingColumn: If the column or relation does not exist.
        """
        col = None
        colalias = None
        if name.startswith('$'):
            name = name[1:]
        if not name.startswith('@'):
            col = self['columns.%s' % name]
            if col is not None:
                return col
            colalias = self['virtual_columns.%s' % name]
            if colalias is not None:
                if colalias.virtual:
                    return colalias
                elif colalias.relation_path:
                    name = colalias.relation_path
                elif colalias.sql_formula or colalias.select or colalias.exists:
                    return colalias
                elif colalias.join_column:
                    return colalias
                elif colalias.composed_of:
                    return colalias
                elif colalias.py_method:
                    return colalias
                else:
                    raise GnrSqlMissingColumn(
                        'Invalid column %s in table %s' % (name, self.name_full)
                    )
        if name.startswith('@'):
            relcol = self._relatedColumn(name)
            if relcol is None:
                raise GnrSqlMissingColumn(
                    'relation %s does not exist in table %s' % (name, self.name_full)
                )
            if colalias is None:
                return relcol
            if 'virtual_column' not in colalias.attributes:
                raise GnrSqlException('Col alias must be virtual_column')
            return AliasColumnWrapper(relcol, colalias.attributes)

    def _relatedColumn(self, fieldpath: str) -> Any:
        """Resolve a ``@relation.column`` path to a column object.

        Args:
            fieldpath: A relation path (e.g. ``@member_id.name``).

        Returns:
            The resolved column object.

        Raises:
            GnrSqlMissingField: If the relation path cannot be resolved.
        """
        relpath = fieldpath.split('.')
        firstrel = relpath.pop(0)
        attrs = self.relations.getAttr(firstrel)
        if not attrs:
            tblalias = self['table_aliases.%s' % firstrel]
            if tblalias is None:
                raise GnrSqlMissingField('Missing field %s' % fieldpath)
            else:
                relpath = tblalias.relation_path.split('.') + relpath
                reltbl = self
        else:
            joiner = attrs['joiner']
            if joiner['mode'] == 'O':
                relpkg, reltbl, relfld = joiner['one_relation'].split('.')
            else:
                relpkg, reltbl, relfld = joiner['many_relation'].split('.')
            reltbl = self.dbroot.package(relpkg).table(reltbl)

        return reltbl.column('.'.join(relpath))

    def virtualColumnAttributes(self, name: str) -> dict[str, Any]:
        """Return merged attributes for a virtual column.

        If the virtual column has a ``relation_path``, the related
        column's attributes are merged with the virtual column's own.

        Args:
            name: The virtual column name.
        """
        column = self.virtual_columns[name]
        if not column.attributes.get('relation_path'):
            return column.attributes
        attributes = dict(self.column(name).attributes)
        attributes.update(column.attributes)
        return attributes

    def fullRelationPath(self, name: str) -> str:
        """Resolve aliases and return the full relation path.

        Args:
            name: A column name or ``@relation.path``.

        Returns:
            The fully resolved relation path string.
        """
        if name.startswith('$'):
            name = name[1:]
        if not name.startswith('@') and name not in list(self['columns'].keys()):
            colalias = self['virtual_columns.%s' % name]
            if colalias is not None:
                if colalias.relation_path:
                    name = colalias.relation_path
        if name.startswith('@'):
            rel, pathlist = name.split('.', 1)
            if 'table_aliases' in self and rel in self['table_aliases']:
                relpath = self['table_aliases.%s' % rel].relation_path
                rel, pathlist = ('%s.%s' % (relpath, pathlist)).split('.', 1)
            colobj = self.column(rel[1:])
            if colobj is not None:
                reltbl = colobj.relatedTable()
            else:
                reltbl = '.'.join(
                    self.relations.getNode(rel).attr['joiner']['many_relation'].split('.')[0:2]
                )
                reltbl = self.db.table(reltbl)
            return '%s.%s' % (rel, reltbl.fullRelationPath(pathlist))
        else:
            return name

    def resolveRelationPath(self, relpath: str) -> str:
        """Recursively resolve a relation path, expanding table aliases.

        Args:
            relpath: A dotted relation path.

        Returns:
            The fully resolved relation path.

        Raises:
            GnrSqlRelationError: If a relation segment cannot be found.
        """
        if relpath in self.relations:
            return relpath  # it is a real relation path with no aliases

        relpath = relpath.split('.')
        firstrel = relpath.pop(0)

        attrs = self.relations.getAttr(firstrel)
        if not attrs:
            tblalias = self['table_aliases.%s' % firstrel]
            if tblalias is None:
                raise GnrSqlRelationError('Cannot find %s in %s' % (tblalias, self.name))
            else:
                relpath = tblalias.relation_path.split('.') + relpath
                return self.resolveRelationPath('.'.join(relpath))
        else:
            joiner = attrs['joiner']
            if joiner['mode'] == 'O':
                relpkg, reltbl, relfld = joiner['one_relation'].split('.')
            else:
                relpkg, reltbl, relfld = joiner['many_relation'].split('.')
            reltbl = self.dbroot.package(relpkg).table(reltbl)
            return '%s.%s' % (firstrel, reltbl.resolveRelationPath('.'.join(relpath)))

    # -- Relation helpers -----------------------------------------------------

    def _get_relations_one(self) -> Bag:
        """Return a Bag of all many-to-one relations from this table."""
        result = Bag()
        for k, joiner in self.relations.digest('#k,#a.joiner'):
            if joiner and joiner['mode'] == 'O':
                result.setItem(
                    joiner['many_relation'].split('.')[-1],
                    joiner['one_relation'], joiner,
                )
        return result

    relations_one = property(_get_relations_one)

    def _get_relations_many(self) -> Bag:
        """Return a Bag of all one-to-many relations from this table."""
        result = Bag()
        for k, joiner in self.relations.digest('#k,#a.joiner'):
            if joiner and joiner['mode'] == 'M':
                result.setItem(
                    joiner['many_relation'].replace('.', '_'),
                    joiner['one_relation'].split('.')[-1], joiner,
                )
        return result

    relations_many = property(_get_relations_many)

    def _get_relatingColumns(self) -> list[str]:
        """Return column paths that reference this table's primary key."""
        return self.relations_many.digest('#a.many_relation')

    relatingColumns = property(_get_relatingColumns)

    def getRelation(self, relpath: str) -> dict[str, str] | None:
        """Return the many/one endpoints for a relation path.

        Args:
            relpath: The relation path key.

        Returns:
            A dict with ``'many'`` and ``'one'`` keys, or ``None``.
        """
        joiner = self.relations.getAttr(relpath, 'joiner')
        if joiner:
            return {'many': joiner['many_relation'], 'one': joiner['one_relation']}

    def getRelationBlock(self, relpath: str) -> dict[str, str]:
        """Return a structured dict of relation components.

        Args:
            relpath: The relation path key.
        """
        joiner = self.relations.getAttr(relpath, 'joiner')
        mpkg, mtbl, mfld = joiner['many_relation'].split('.')
        opkg, otbl, ofld = joiner['one_relation'].split('.')
        return dict(
            mode=joiner['mode'], mpkg=mpkg, mtbl=mtbl, mfld=mfld,
            opkg=opkg, otbl=otbl, ofld=ofld,
        )

    def bagItemFormula(
        self,
        bagcolumn: str | None = None,
        itempath: str | None = None,
        dtype: str | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> str:
        """Delegate to the module-level ``bagItemFormula`` helper."""
        return bagItemFormula(bagcolumn=bagcolumn, itempath=itempath, dtype=dtype, kwargs=kwargs)

    def getJoiner(self, related_table: str) -> dict[str, Any] | None:
        """Find the joiner dict connecting this table to another.

        Searches both outgoing (one-to-many) and incoming relations.

        Args:
            related_table: The related table path (``pkg.table``).

        Returns:
            The joiner dict, or ``None`` if no relation exists.
        """
        reltableobj = self.db.table(related_table)
        related_field = reltableobj.column(reltableobj.pkey).fullname
        for n in self.relations:
            joiner = n.attr.get('joiner')
            if joiner:
                if joiner.get('one_relation') == related_field:
                    return joiner
        relating_field = self.column(self.pkey).fullname
        for n in reltableobj.relations:
            joiner = n.attr.get('joiner')
            if joiner:
                if joiner.get('one_relation') == relating_field:
                    return joiner

    def getTableJoinerPath(
        self, table: str, deepLimit: int = 5, eager: bool = False,
    ) -> list[list[dict[str, Any]]]:
        """Find all relation paths to a target table.

        Uses iterative deepening to find paths up to *deepLimit* hops.

        Args:
            table: The target table path (``pkg.table``).
            deepLimit: Maximum relation depth to search.
            eager: Currently unused.

        Returns:
            A list of paths, each being a list of joiner dicts.
        """
        targetField = '%s.%s' % (table, self.db.table(table).pkey)
        currtable = self.fullname
        for maxdeep in range(1, deepLimit):
            result = self._getTableJoinerPath_step(
                currtable, deep=1, maxdeep=maxdeep,
                targetTable=table, targetField=targetField, omitPrivate=True,
            )
            if not result:
                result = self._getTableJoinerPath_step(
                    currtable, deep=1, maxdeep=maxdeep,
                    targetTable=table, targetField=targetField, omitPrivate=False,
                )
            if result:
                return result
        return []

    def _getTableJoinerPath_step(
        self,
        currtable: str,
        deep: int | None = None,
        maxdeep: int | None = None,
        targetTable: str | None = None,
        targetField: str | None = None,
        omitPrivate: bool | None = None,
    ) -> list[list[dict[str, Any]]]:
        """Recursive step for :meth:`getTableJoinerPath`."""
        relations = self.db.model.relations(currtable)
        result = []
        failed = []
        for rel in relations:
            attr = dict(rel.attr)
            if omitPrivate and attr.get('private_relation'):
                continue
            attr['relpath'] = rel.label
            mode = attr['mode']
            one_pkg, one_tbl, one_field = attr['one_relation'].split('.')
            many_pkg, many_tbl, many_field = attr['many_relation'].split('.')
            if mode == 'O':
                attr['table'] = '%s.%s' % (one_pkg, one_tbl)
                if attr['one_relation'] == targetField:
                    attr['relpath'] = many_field
                    result.append([attr])
                else:
                    failed.append(attr)
            else:
                attr['table'] = '%s.%s' % (many_pkg, many_tbl)
                if targetTable == attr['table']:
                    attr['relpath'] = '%s.%s' % (rel.label, self.db.table(attr['table']).pkey)
                    result.append([attr])
                else:
                    failed.append(attr)
        if result:
            return result
        if deep < maxdeep:
            for attr in failed:
                step_result = self._getTableJoinerPath_step(
                    attr['table'], deep=deep + 1, maxdeep=maxdeep,
                    targetTable=targetTable, targetField=targetField,
                    omitPrivate=omitPrivate,
                )
                for s in step_result:
                    result.append([attr] + s)
        return result

    def manyRelationsList(self, cascadeOnly: bool = False) -> list[tuple[str, str]]:
        """Return a list of ``(table, fkey)`` tuples for one-to-many relations.

        Args:
            cascadeOnly: If ``True``, only include cascade-delete relations.
        """
        result = list()
        relations = list(self.relations.keys())
        for k in relations:
            n = self.relations.getNode(k)
            joiner = n.attr.get('joiner')
            if joiner and joiner['mode'] == 'M' and (
                not cascadeOnly
                or (joiner.get('onDelete') == 'cascade'
                    or joiner.get('onDelete_sql') == 'cascade')
            ):
                fldlist = joiner['many_relation'].split('.')
                tblname = '.'.join(fldlist[0:2])
                fkey = fldlist[-1]
                result.append((tblname, fkey))
        return result

    def oneRelationsList(self, foreignkeyOnly: bool = False) -> list[tuple[str, str, str]]:
        """Return a list of ``(table, pkey, fkey)`` for many-to-one relations.

        Args:
            foreignkeyOnly: If ``True``, only include SQL foreign keys.
        """
        result = list()
        for n in self.relations_one:
            attr = n.attr
            if not foreignkeyOnly or attr.get('foreignkey'):
                fldlist = attr['one_relation'].split('.')
                tblname = '.'.join(fldlist[0:2])
                fkey = attr['many_relation'].split('.')[-1]
                pkey = fldlist[-1]
                result.append((tblname, pkey, fkey))
        return result

    def toJson(self, **kwargs: Any) -> dict[str, Any]:
        """Return a JSON-serializable dict describing this table.

        Returns:
            A dict with ``code``, ``name``, ``pkey``, and ``columns``.
        """
        return dict(
            code=self.name,
            name=self.name_long,
            pkey=self.pkey,
            columns=[
                c.toJson() for c in (
                    self.columns.values()
                    + [v for k, v in self.virtual_columns.items() if not k.startswith('__')]
                )
            ],
        )
