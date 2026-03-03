# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel.model : DbModel and DbModelSrc
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

"""Model orchestration classes: ``DbModel`` and ``DbModelSrc``.

``DbModel`` is the top-level model object that manages packages, tables,
columns, relations, mixins, and the build/check lifecycle.

``DbModelSrc`` is a :class:`GnrStructData` subclass that acts as the
source-tree builder — every ``package()``, ``table()``, ``column()``,
``virtual_column()``, ``relation()``, etc. call populates the model
source tree that ``DbModel.build()`` later compiles into live objects.
"""

from __future__ import annotations

import copy  # noqa: F401 — used transitively in some mixin paths

from typing import Any

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import extract_kwargs
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrlang import moduleDict
from gnr.core.gnrstructures import GnrStructData
from gnr.sql import logger
from gnr.sql.gnrsql_exceptions import GnrSqlException, GnrSqlRelationError
from gnr.sql.gnrsqlmodel.columns import DbVirtualColumnObj
from gnr.sql.gnrsqlmodel.containers import DbIndexObj
from gnr.sql.gnrsqlmodel.helpers import (
    ConfigureAfterStartError,
    bagItemFormula,
    toolFormula,
)
from gnr.sql.gnrsqlmodel.obj import DbModelObj
from gnr.sql.gnrsqlutils import ModelExtractor, SqlModelChecker


class DbModel:
    """Top-level database model orchestrator.

    Manages the full lifecycle of the model: building from source,
    loading/saving, adding relations, applying schema changes, and
    looking up packages/tables/columns.

    Attributes:
        db: The ``GnrSqlDb`` instance owning this model.
        src: The :class:`DbModelSrc` source tree.
        obj: The compiled :class:`DbModelObj` tree (populated after
            :meth:`build`).
        relations: A :class:`Bag` of all inter-table relations.
        mixins: A :class:`Bag` of registered mixin objects.
    """

    def __init__(self, db: Any) -> None:
        self.db = db
        self.onBuildingCb: list[dict[str, Any]] = []
        self.src: DbModelSrc = DbModelSrc.makeRoot()
        self.src.child('package_list', 'packages')
        self.src._dbmodel = self
        self.obj: Any = None
        self.relations: Bag = Bag()
        self._columnsWithRelations: dict[tuple[str, ...], dict[str, Any]] = {}
        self.mixins: Bag = Bag()

    @property
    def debug(self) -> bool:
        """Return the current debug flag from the database."""
        return self.db.debug

    def runOnBuildingCb(self) -> None:
        """Execute and drain all deferred on-building callbacks."""
        while self.onBuildingCb:
            cbpars = self.onBuildingCb.pop()
            cbpars['handler'](*cbpars['args'], **cbpars['kwargs'])

    def deferOnBuilding(self, cb: Any, *args: Any, **kwargs: Any) -> None:
        """Register a callback to be invoked during :meth:`build`.

        Args:
            cb: The callable to defer.
            *args: Positional arguments for *cb*.
            **kwargs: Keyword arguments for *cb*.
        """
        self.onBuildingCb.append({'handler': cb, 'args': args, 'kwargs': kwargs})

    def build(self) -> None:
        """Build the compiled model from the source tree.

        Steps:

        1. Apply table and package mixins (``config_db``, per-package
           customisations, ``config_db_custom``).
        2. Scan all classes with ``sqlclass`` / ``sqlresolver`` via
           :func:`moduleDict`.
        3. Compile the source tree into a :class:`DbModelObj` tree.
        4. Register all column relations via :meth:`addRelation`.
        """

        def _on_ins_column(n: Any, pkg_id: str) -> None:
            tag = n.attr.get('tag')
            if tag and 'column' in tag:
                n.attr['_owner_package'] = pkg_id

        def _doObjMixinConfig(objmix: Any, pkgsrc: Any) -> None:
            if hasattr(objmix, 'config_db'):
                objmix.config_db(pkgsrc)
            if self.db.application:
                for pkg_id in list(self.db.application.packages.keys()):
                    config_from_pkg = getattr(objmix, 'config_db_%s' % pkg_id, None)
                    if config_from_pkg:
                        pkgsrc.subscribe(
                            'customize_%s' % pkg_id,
                            insert=lambda node=None, **kwargs: _on_ins_column(node, pkg_id),
                        )
                        config_from_pkg(pkgsrc)
                        pkgsrc.unsubscribe('customize_%s' % pkg_id)

            if hasattr(objmix, 'config_db_custom'):
                objmix.config_db_custom(pkgsrc)

        if 'tbl' in self.mixins:
            for pkg in list(self.mixins['tbl'].keys()):
                pkgsrc = self.src['packages.%s' % pkg]
                tables = self.mixins['tbl.%s' % pkg]
                tablenames = list(tables.keys())
                tablenames.sort()
                for tblname in tablenames:
                    tblmix = tables[tblname]
                    tblmix.db = self.db
                    tblmix._tblname = tblname
                    if hasattr(tblmix, 'config_db'):
                        tblmix._cls = tblmix.config_db.__self__
                    _doObjMixinConfig(tblmix, pkgsrc)
                    tblsrc = pkgsrc.table(tblmix._tblname)
                    tblsrc._mixinobj = tblmix
                    tblmix.src = tblsrc
        onBuildingCalls: list[Any] = []
        if 'pkg' in self.mixins:
            for pkg, pkgmix in list(self.mixins['pkg'].items()):
                pkgsrc = self.src['packages.%s' % pkg]
                pkgmix.db = self.db
                _doObjMixinConfig(pkgmix, pkgsrc)
                if hasattr(pkgmix, 'onBuildingDbobj'):
                    onBuildingCalls.append(pkgmix.onBuildingDbobj)
        sqldict = moduleDict('gnr.sql.gnrsqlmodel', 'sqlclass,sqlresolver')
        for cb in onBuildingCalls:
            cb()
        # Source tree ready.
        self.runOnBuildingCb()
        if self.relations:
            self.relations.clear()
            logger.debug('relations %s', self.relations)
        self.obj = DbModelObj.makeRoot(self, self.src, sqldict)
        for many_relation_tuple, relation in self._columnsWithRelations.items():
            oneCol = relation.pop('related_column')
            self.addRelation(many_relation_tuple, oneCol, **relation)
        self._columnsWithRelations.clear()
        self.db.currentEnv.pop('_relations', None)

    @extract_kwargs(resolver=True, meta=True)
    def addRelation(
        self,
        many_relation_tuple: tuple[str, str, str],
        oneColumn: str,
        mode: str | None = None,
        storename: str | None = None,
        one_one: str | None = None,
        onDelete: str | None = None,
        onDelete_sql: str | None = None,
        onUpdate: str | None = None,
        onUpdate_sql: str | None = None,
        deferred: bool | None = None,
        eager_one: bool | None = None,
        eager_many: bool | None = None,
        relation_name: str | None = None,
        one_name: str | None = None,
        many_name: str | None = None,
        one_group: str | None = None,
        many_group: str | None = None,
        many_order_by: str | None = None,
        storefield: str | None = None,
        external_relation: bool | None = None,
        resolver_kwargs: dict[str, Any] | None = None,
        inheritProtect: bool | None = None,
        inheritLock: bool | None = None,
        meta_kwargs: dict[str, Any] | None = None,
        onDuplicate: str | None = None,
        between: str | None = None,
        cnd: str | None = None,
        join_on: str | None = None,
        virtual: bool | None = None,
        ignore_tenant: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Add a relation between two tables in the model.

        Registers both the many-side (``mode='O'``) and one-side
        (``mode='M'``) entries in :attr:`relations`, validates column
        sizes, and optionally triggers auto-static propagation.

        Args:
            many_relation_tuple: ``(pkg, table, column)`` of the foreign
                key side.
            oneColumn: Dotted path ``pkg.table.column`` of the primary
                key side.
            mode: Relation mode — ``'relation'`` (default),
                ``'foreignkey'``, or ``'insensitive'``.
            onDelete: Python-level delete action
                (``'cascade'`` / ``'ignore'`` / ``'raise'`` / ``'setnull'``).
            onDelete_sql: SQL-level delete action.
            relation_name: Override for the inverse-relation label.

        Raises:
            GnrSqlRelationError: If a duplicate relation key is detected.
        """
        # REVIEW: this method is ~100 lines with a bare except catching
        # everything including KeyboardInterrupt.  Consider narrowing
        # the exception types.
        try:
            many_pkg, many_table, many_field = many_relation_tuple
            many_relation = '.'.join(many_relation_tuple)
            one_pkg, one_table, one_field = oneColumn.split('.')
            one_relation = '.'.join((one_pkg, one_table, one_field))
            if not (many_field and one_field):
                logger.warning(
                    "pkg, table or field involved in the relation %s -> %s doesn't exist",
                    many_relation, one_relation,
                )
                return
            link_many_name = many_field
            private_relation = relation_name is None and one_one != '*'
            default_relation_name = many_table if one_one == '*' else '_'.join(many_relation_tuple)
            relation_name = relation_name or default_relation_name
            case_insensitive = (mode == 'insensitive')
            foreignkey = (mode == 'foreignkey')
            many_relkey = '%s.%s.@%s' % (many_pkg, many_table, link_many_name)
            many_table_obj = self.obj[many_pkg]['tables'][many_table]
            if ignore_tenant is False and many_table_obj.multi_tenant:
                logger.warning(
                    f"ignore_tenant cannot be False in {'.'.join(many_relation_tuple)}"
                )
            if deferred is None and (onDelete == 'setnull' or onDelete_sql == 'setnull'):
                deferred = True
            if many_relkey in self.relations:
                raise GnrSqlRelationError(
                    'Cannot add many relation %s because exist another relation to the '
                    'table %s with relation_name=%s' % (many_relkey, many_table, relation_name)
                )
            col_finder = self.column if not virtual else (lambda x: self.virtual_columns[x])
            self.relations.setItem(
                many_relkey, None, mode='O',
                many_relation=many_relation, many_rel_name=many_name, foreignkey=foreignkey,
                many_order_by=many_order_by, relation_name=relation_name,
                one_relation=one_relation,
                one_rel_name=one_name or self.column(
                    '.'.join(many_relation_tuple)
                ).attributes.get('name_long'),
                one_one=one_one, onDelete=onDelete,
                onDelete_sql=onDelete_sql, onDuplicate=onDuplicate,
                onUpdate=onUpdate, onUpdate_sql=onUpdate_sql, deferred=deferred,
                case_insensitive=case_insensitive, eager_one=eager_one, eager_many=eager_many,
                private_relation=private_relation, external_relation=external_relation,
                ignore_tenant=ignore_tenant,
                one_group=one_group, many_group=many_group, storefield=storefield,
                _storename=storename,
                between=between, cnd=cnd, join_on=join_on, virtual=virtual,
                resolver_kwargs=resolver_kwargs,
            )
            one_relkey = '%s.%s.@%s' % (one_pkg, one_table, relation_name)

            if one_relkey in self.relations:
                old_relattr = dict(self.relations.getAttr(one_relkey))
                raise GnrSqlRelationError(
                    f"Same relation_name '{relation_name}' in table "
                    f"{old_relattr['many_relation']} and {many_relation}"
                )
            meta_kwargs.update(kwargs)
            self.relations.setItem(
                one_relkey, None, mode='M',
                many_relation=many_relation, many_rel_name=many_name,
                many_order_by=many_order_by,
                one_relation=one_relation, one_rel_name=one_name, one_one=one_one,
                onDelete=onDelete, onDelete_sql=onDelete_sql,
                private_relation=private_relation,
                onUpdate=onUpdate, onUpdate_sql=onUpdate_sql, deferred=deferred,
                external_relation=external_relation,
                case_insensitive=case_insensitive, eager_one=eager_one, eager_many=eager_many,
                ignore_tenant=ignore_tenant,
                one_group=one_group, many_group=many_group, storefield=storefield,
                _storename=storename,
                between=between, cnd=cnd, join_on=join_on, virtual=virtual,
                inheritLock=inheritLock, inheritProtect=inheritProtect,
                onDuplicate=onDuplicate, **meta_kwargs,
            )
            if not virtual:
                self.checkRelationIndex(many_pkg, many_table, many_field)
                self.checkRelationIndex(one_pkg, one_table, one_field)
                col_one_size = self.table(
                    one_table, pkg=one_pkg
                ).column(one_field).attributes.get('size')
                col_many_size = self.table(
                    many_table, pkg=many_pkg
                ).column(many_field).attributes.get('size')
            else:
                col_one_size = col_many_size = None
            if col_one_size != col_many_size:
                message = (
                    'Different size in relation {fkey}:{many_size} - '
                    '{pkey}:{one_size} '.format(
                        fkey=str('.'.join(many_relation_tuple)),
                        many_size=col_many_size,
                        pkey=str(oneColumn),
                        one_size=col_one_size,
                    )
                )
                logger.warning(message)

            if (onDelete == 'cascade' and self.db.auto_static_enabled) or (
                meta_kwargs.get('childmode')
            ):
                self.checkAutoStatic(
                    one_pkg=one_pkg, one_table=one_table, one_field=one_field,
                    many_pkg=many_pkg, many_table=many_table, many_field=many_field,
                )

        except Exception as e:
            if self.debug:
                raise
            logger.error(
                'The relation %s - %s cannot be added: %s',
                str('.'.join(many_relation_tuple)),
                str(oneColumn),
                getattr(e, 'description', str(e)),
            )

    def checkRelationIndex(
        self, pkg: str, table: str, column: str,
    ) -> None:
        """Ensure an index exists for a relation column.

        Creates an index named ``<table>_<column>_key`` if the column
        is not the primary key and no such index already exists.

        Args:
            pkg: Package name.
            table: Table name.
            column: Column name.
        """
        tblobj = self.table(table, pkg=pkg)
        indexname = '%s_%s_key' % (table, column)
        if column != tblobj.pkey and indexname not in tblobj.indexes:
            tblobj.indexes.children[indexname] = DbIndexObj(
                parent=tblobj.indexes, attrs=dict(columns=column),
            )

    def checkAutoStatic(
        self,
        one_pkg: str | None = None,
        one_table: str | None = None,
        one_field: str | None = None,
        many_pkg: str | None = None,
        many_table: str | None = None,
        many_field: str | None = None,
    ) -> None:
        """Propagate system fields from parent to child table.

        When a cascade-delete relation exists and ``auto_static`` is
        enabled, copies ``draftField`` and ``logicalDeletionField``
        from the one-side table to the many-side table as alias columns.

        Args:
            one_pkg: Primary-key side package.
            one_table: Primary-key side table.
            one_field: Primary-key side column.
            many_pkg: Foreign-key side package.
            many_table: Foreign-key side table.
            many_field: Foreign-key side column.
        """
        manytable_src = self.src['packages'][many_pkg]['tables'][many_table]
        onetable_src = self.src['packages'][one_pkg]['tables'][one_table]
        manytblobj = self.obj[many_pkg]['tables'][many_table]
        for systemField in ('draftField', 'logicalDeletionField'):
            one_sf = onetable_src.attributes.get(systemField)
            many_sf = manytable_src.attributes.get(systemField)
            if one_sf and many_sf is None:
                manytable_src.aliasColumn(
                    one_sf,
                    '@{many_field}.{one_sf}'.format(many_field=many_field, one_sf=one_sf),
                    name_long='!![en]{many_field} {one_sf}'.format(
                        many_field=many_field, one_sf=one_sf,
                    ),
                    group='zz', static=True,
                )
                manytable_src.attributes[systemField] = one_sf
                manytblobj.attributes[systemField] = one_sf

    def load(self, source: Any = None) -> None:
        """Load the model source from an XML source.

        Args:
            source: XML model (disk file, text, or URL).
        """
        self.src.update(source)

    def importFromDb(self) -> None:
        """Import the model source by extracting it from the live database."""
        exporter = ModelExtractor(self.db)
        root = DbModelSrc.makeRoot()
        exporter.extractModelSrc(root=root)
        self.src.update(root)

    def save(self, path: str) -> None:
        """Save the current model source as an XML file.

        Args:
            path: Destination file path.
        """
        self.src.save(path)

    def check(self, applyChanges: bool = False) -> bool:
        """Verify compatibility between the database and the model.

        Args:
            applyChanges: If ``True``, apply the required SQL changes
                immediately.

        Returns:
            ``True`` if there are pending model changes.
        """
        checker = SqlModelChecker(self.db)
        self.modelChanges = checker.checkDb()
        self.modelBagChanges = checker.bagChanges
        if applyChanges:
            self.applyModelChanges()
        return bool(self.modelChanges)

    def enableForeignKeys(self, enable: bool = True) -> None:
        """Enable or disable foreign key constraints.

        Args:
            enable: ``True`` to enable, ``False`` to disable.
        """
        checker = SqlModelChecker(self.db)
        self.modelChanges = checker.checkDb(enableForeignKeys=enable)
        self.modelBagChanges = checker.bagChanges
        self.applyModelChanges()

    @property
    def checker(self) -> SqlModelChecker:
        """Return a fresh :class:`SqlModelChecker` instance."""
        return SqlModelChecker(self.db)

    def applyModelChanges(self) -> None:
        """Execute pending model-change SQL statements.

        Handles ``CREATE DATABASE`` as a special first statement,
        then executes remaining DDL and commits.
        """
        if not self.modelChanges:
            return
        if self.modelChanges[0].startswith('CREATE DATABASE'):
            self.db.adapter.createDb()
            self.modelChanges.pop(0)
        for change in self.modelChanges:
            self.db.execute(change, _adaptArguments=False)
        self.db.commit()

    def _doMixin(self, path: str, obj: Any) -> None:
        """Register a mixin at the given path.

        Args:
            path: Dotted mixin path (e.g. ``'pkg.mypackage'``).
            obj: The mixin object.

        Raises:
            ConfigureAfterStartError: If the database has already started.
        """
        if self.db.started:
            raise ConfigureAfterStartError(path)
        self.mixins[path] = obj

    def packageMixin(self, pkg: str, obj: Any) -> None:
        """Register a package-level mixin.

        Args:
            pkg: Package name.
            obj: The mixin object.
        """
        self._doMixin('pkg.%s' % pkg, obj)

    def tableMixin(self, tblpath: str, obj: Any) -> None:
        """Register a table-level mixin.

        Args:
            tblpath: Dotted path ``pkg.table``.
            obj: The mixin object.
        """
        self._doMixin('tbl.%s' % tblpath, obj)

    def package(self, pkg: str) -> Any:
        """Return a compiled package object.

        Args:
            pkg: The package name.

        Returns:
            A :class:`DbPackageObj` instance, or ``None``.
        """
        return self.obj[pkg]

    def table(self, tblname: str, pkg: str | None = None) -> Any:
        """Return a compiled table object.

        Args:
            tblname: Table name, optionally qualified as ``pkg.table``.
            pkg: Explicit package name (overridden if *tblname*
                contains a dot).

        Returns:
            A :class:`DbTableObj` instance, or ``None``.

        Raises:
            ValueError: If *pkg* cannot be determined.
        """
        if '.' in tblname:
            pkg, tblname = tblname.split('.')[:2]
        if pkg is None:
            raise ValueError(
                "table() called with '%(tblname)s' instead of "
                "'<packagename>.%(tblname)s'" % {'tblname': tblname}
            )
        if self.obj:
            if not self.obj[pkg]:
                return
            return self.obj[pkg].table(tblname)
        else:
            return self.src['packages'][pkg]['tables'][tblname]

    def column(self, colname: str) -> Any:
        """Return a compiled column object.

        Args:
            colname: Dotted path — ``pkg.table.column`` or
                ``table.column`` (package inferred from first table
                found).

        Returns:
            A :class:`DbColumnObj` or :class:`DbVirtualColumnObj`.
        """
        colpath = colname.split('.')
        if len(colpath) == 2:
            pkg = None
            tblname, colname = colpath
        else:
            pkg, tblname, colname = colpath
        return self.table(tblname, pkg=pkg).column(colname)


class DbModelSrc(GnrStructData):
    """Source-tree builder for the GenroPy database model.

    Each method (``package``, ``table``, ``column``, ``virtual_column``,
    ``relation``, etc.) appends a node to the model source tree.  The
    tree is later compiled by :meth:`DbModel.build` into live
    :class:`DbModelObj` instances.
    """

    def package(
        self,
        name: str,
        sqlschema: str | None = None,
        comment: str | None = None,
        name_short: str | None = None,
        name_long: str | None = None,
        name_full: str | None = None,
        **kwargs: Any,
    ) -> DbModelSrc:
        """Add a package to the model source tree.

        Args:
            name: The package name.
            sqlschema: SQL schema name override.
            comment: Human-readable comment.
            name_short: Short display name.
            name_long: Long display name.
            name_full: Full display name.

        Returns:
            The package source node.
        """
        if 'packages' not in self:
            self.child('package_list', 'packages')

        return self.child(
            'package', 'packages.%s' % name,
            comment=comment, sqlschema=sqlschema,
            name_short=name_short, name_long=name_long,
            name_full=name_full, **kwargs,
        )

    def externalPackage(self, name: str) -> Any:
        """Return a reference to an external package node.

        Args:
            name: The package name.
        """
        return self.root('packages.%s' % name)

    def table(
        self,
        name: str,
        pkey: str | None = None,
        lastTS: str | None = None,
        rowcaption: str | None = None,
        sqlname: str | None = None,
        sqlschema: str | None = None,
        comment: str | None = None,
        name_short: str | None = None,
        name_long: str | None = None,
        name_full: str | None = None,
        **kwargs: Any,
    ) -> DbModelSrc:
        """Add a table to the model source tree.

        Args:
            name: The table name.
            pkey: Primary key column name.
            lastTS: Timestamp column for last-modification tracking.
            rowcaption: Textual representation template for a record.
            sqlname: SQL name override.
            sqlschema: SQL schema name override.
            comment: Human-readable comment.
            name_short: Short display name.
            name_long: Long display name.
            name_full: Full display name.

        Returns:
            The table source node.
        """
        if 'tables' not in self:
            self.child('table_list', 'tables')
        pkg = self.parentNode.label
        return self.child(
            'table', 'tables.%s' % name, comment=comment,
            name_short=name_short, name_long=name_long, name_full=name_full,
            pkey=pkey, lastTS=lastTS, rowcaption=rowcaption, pkg=pkg,
            fullname='%s.%s' % (pkg, name),
            **kwargs,
        )

    def subtable(self, name: str, condition: str | None = None, **kwargs: Any) -> Any:
        """Insert a subtable definition.

        Dispatches to :meth:`_subtable_package` or
        :meth:`_subtable_table` depending on whether ``self`` is a
        package or a table node.

        Args:
            name: The subtable name.
            condition: SQL condition for table-level subtables.

        Returns:
            The subtable source node.
        """
        if self.attributes['tag'] == 'package':
            return self._subtable_package(name, **kwargs)
        else:
            return self._subtable_table(name, condition=condition, **kwargs)

    def _subtable_package(
        self,
        name: str,
        maintable: str | None = None,
        relation_name: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create a package-level subtable inheriting from a main table.

        Copies all columns and relations from the main table, adds a
        ``__subtable`` discriminator column, and registers appropriate
        subtable conditions on both sides.

        Args:
            name: Subtable name.
            maintable: ``pkg.table`` path of the main table.
            relation_name: Override for the inverse relation name.

        Returns:
            The subtable source node.
        """
        pkey = kwargs.pop('pkey', None)
        if pkey:
            import warnings
            warnings.warn(
                "you cannot set pkey inside subtable",
                category=DeprecationWarning, stacklevel=2,
            )
        pkg, tblname = maintable.split('.')
        maintable_src = self.parent[pkg]['tables'][tblname]
        maintable_attributes = maintable_src.attributes
        name_plural = relation_name or kwargs.get('name_plural') or name
        result = self.table(name, maintable=maintable, **kwargs)
        resultattr = result.attributes
        for k, v in maintable_attributes.items():
            if not k.startswith('partition_'):
                resultattr.setdefault(k, v)
        maintable_src.column('__subtable', size=':64', group='_', indexed=True)
        for n in maintable_src['columns']:
            attributes = dict(n.attr)
            attributes.pop('tag')
            attributes.pop('indexed', None)
            attributes['sql_inherited'] = True
            value = n.value
            col = result.column(n.label, **attributes)
            if value:
                for rn in value:
                    rnattr = dict(rn.attr)
                    if rnattr.get('relation_name'):
                        rnattr['relation_name'] = (
                            kwargs.get('relation_name')
                            or f'{name_plural.lower().replace(" ", "_")}'
                        )
                    related_column = rnattr.pop('related_column')
                    col.relation(related_column, **rnattr)
        subtablename = f'{self.attributes.get("pkgcode")}.{name}'
        result.column(
            '__subtable', sql_value=f"'{subtablename}'", default=name,
            group='_', sql_inherited=True,
        )
        maintable_src.subtable(
            name, condition='$__subtable=:sn',
            condition_sn=name,
            table=subtablename,
            name_plural=kwargs.get('name_plural'),
        )
        maintable_src.subtable(
            '_main', condition='$__subtable IS NULL',
            name_plural=maintable_attributes.get('name_plural'),
        )
        maintable_attributes['default_subtable'] = '_main'
        result.subtable('_main', condition='$__subtable=:sn', condition_sn=name)
        resultattr['default_subtable'] = '_main'
        return result

    def _subtable_table(
        self,
        name: str,
        condition: str | None = None,
        name_long: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create a table-level subtable with a filter condition.

        Args:
            name: Subtable name.
            condition: SQL WHERE condition.
            name_long: Display name.

        Returns:
            The subtable source node.
        """
        if 'subtables' not in self:
            self.child('subtable_list', 'subtables')
        condition_kwargs = dictExtract(kwargs, 'condition_')
        self.attributes.setdefault('group_subtables', '!![en]Subtables')
        self.formulaColumn(
            f'subtable_{name}', condition, dtype='B',
            name_long=name_long or name, group='subtables',
            _addClass=f'subtable_{name}',
            **{f'var_{k}': v for k, v in condition_kwargs.items()},
        )
        return self.child('subtable', f'subtables.{name}', condition=condition, **kwargs)

    @extract_kwargs(col=True)
    def colgroup(
        self,
        name: str,
        name_long: str | None = None,
        col_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Define a column group.

        Column groups visually and logically group related columns.
        Columns created as children of the returned node automatically
        inherit the group label and ordering.

        Args:
            name: Group name.
            name_long: Display name.
            col_kwargs: Default keyword arguments applied to all child
                columns.

        Returns:
            The column-group source node.
        """
        self.attributes.setdefault(f'group_{name}', name_long or name)
        if 'colgroups' not in self:
            self.child('colgroup_list', 'colgroups')
        cg = self.child(
            'colgroup', f'colgroups.{name}',
            name_long=name_long, **kwargs,
        )
        cg._destinationNode = self

        def _decorateChildAttributes(
            destination: Any, tag: str, kwargs: dict[str, Any],
        ) -> None:
            kwargs['group'] = f'{name}.{len(destination) + 1:03}'
            kwargs['colgroup_label'] = cg.parentNode.label
            kwargs['colgroup_name_long'] = cg.attributes.get(
                'name_long', kwargs['colgroup_label'],
            )
            for k, v in col_kwargs.items():
                kwargs.setdefault(k, v)

        cg._decorateChildAttributes = _decorateChildAttributes
        return cg

    @extract_kwargs(variant=dict(slice_prefix=False), ext=True)
    def column(
        self,
        name: str,
        dtype: str | None = None,
        size: str | None = None,
        default: Any = None,
        notnull: bool | None = None,
        unique: bool | None = None,
        indexed: Any = None,
        sqlname: str | None = None,
        comment: str | None = None,
        name_short: str | None = None,
        name_long: str | None = None,
        name_full: str | None = None,
        group: str | None = None,
        onInserting: str | None = None,
        onUpdating: str | None = None,
        onDeleting: str | None = None,
        localized: Any = None,
        variant: str | None = None,
        variant_kwargs: dict[str, Any] | None = None,
        ext_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Insert a physical column into a table.

        Handles ``name::dtype`` shorthand, localized columns,
        package-extension hooks, and virtual-column coexistence
        (updating the virtual column attributes if one already exists
        with the same name).

        Args:
            name: Column name (optionally ``name::dtype``).
            dtype: Data type code.
            size: Size constraint (``'min:max'`` or fixed length).
            default: Default value.
            notnull: If ``True``, the column is mandatory.
            unique: If ``True``, enforce SQL UNIQUE.
            indexed: If truthy, create an index.
            sqlname: SQL name override.
            comment: Human-readable comment.
            name_short: Short display name.
            name_long: Long display name.
            name_full: Full display name.
            group: Logical column group path.
            localized: Localization flag or language string.
            variant: Variant name.
            variant_kwargs: Per-variant keyword arguments.
            ext_kwargs: Per-package extension keyword arguments.

        Returns:
            The column source node.
        """
        from gnr.core.gnrstring import boolean as str_boolean

        if isinstance(indexed, str):
            indexed = str_boolean(indexed)
        if isinstance(unique, str):
            unique = str_boolean(unique)
        if '::' in name:
            name, dtype = name.split('::')
        if 'columns' not in self:
            self.child('column_list', 'columns')
        vc = self.getNode(f'virtual_columns.{name}')
        if localized is True:
            dblanguages = self.root._dbmodel.db.extra_kw.get('languages')
            if dblanguages and ',' in dblanguages:
                localized = dblanguages.lower()
            else:
                localized = None
        if vc:
            colattr = dict(
                dtype=dtype, name_short=name_short,
                name_long=name_long, name_full=name_full,
                comment=comment,
                unique=unique, indexed=indexed,
                group=group, **kwargs,
            )
            vc.attr.update({k: v for k, v in colattr.items() if v is not None})
            return vc.value
        kwargs.update(variant_kwargs)
        kwargs.update(ext_kwargs)
        result = self.child(
            'column', f'columns.{name}', dtype=dtype, size=size,
            comment=comment, sqlname=sqlname, localized=localized,
            name_short=name_short, name_long=name_long, name_full=name_full,
            default=default, notnull=notnull, unique=unique, indexed=indexed,
            group=group, onInserting=onInserting, onUpdating=onUpdating,
            onDeleting=onDeleting,
            variant=variant, **kwargs,
        )
        tblsrc = self._destinationNode if hasattr(self, '_destinationNode') else self

        if ext_kwargs:
            for pkgExt, extKwargs in ext_kwargs.items():
                if pkgExt not in self.root._dbmodel.db.application.packages:
                    continue
                pkgobj = self.root._dbmodel.db.application.packages[pkgExt]
                handler = getattr(pkgobj, 'ext_config', None)
                if handler:
                    extKwargs = extKwargs if isinstance(extKwargs, dict) else {pkgExt: extKwargs}
                    handler(tblsrc, colname=name, colattr=result.attributes, **extKwargs)
                    return result

        if localized:
            currpkgobj = self.root._dbmodel.db.application.packages[tblsrc.attributes['pkg']]
            localization_handler = getattr(currpkgobj, 'handleLocalizedColumn', None)
            if localization_handler:
                localization_handler(
                    tblsrc, colname=name, colattr=result.attributes,
                    languages=localized,
                )
        return result

    @extract_kwargs(variant=dict(slice_prefix=True))
    def virtual_column(
        self,
        name: str,
        relation_path: str | None = None,
        sql_formula: str | None = None,
        select: Any = None,
        exists: Any = None,
        py_method: str | None = None,
        _override: bool | None = None,
        variant: str | None = None,
        variant_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Insert a virtual (computed/alias) column into a table.

        Args:
            name: Column name (optionally ``name::dtype``).
            relation_path: Dotted relation path for alias columns.
            sql_formula: SQL expression for formula columns.
            select: Sub-select definition.
            exists: EXISTS sub-query definition.
            py_method: Python method name for computed columns.
            _override: If ``True``, override an existing physical column
                with the same name.
            variant: Variant name.
            variant_kwargs: Per-variant keyword arguments.

        Returns:
            The virtual-column source node.

        Raises:
            GnrSqlException: If a physical column with the same name
                exists and ``_override`` is not set.
        """
        if '::' in name:
            name, dtype = name.split('::')
        if 'virtual_columns' not in self:
            self.child('virtual_columns_list', 'virtual_columns')
        columns = self['columns']
        if columns and name in columns:
            if _override:
                columns.popNode(name)
            else:
                error = (
                    "Column {colname} already defined in table {tablename} "
                    "as a real column. Use _override to override it".format(
                        colname=name,
                        tablename=self.attributes.get('fullname'),
                    )
                )
                raise GnrSqlException(error)

        kwargs.update(variant_kwargs)
        vcsrc = self.child(
            'virtual_column', 'virtual_columns.%s' % name,
            relation_path=relation_path, select=select, exists=exists,
            sql_formula=sql_formula, py_method=py_method,
            virtual_column=True, variant=variant, **kwargs,
        )
        modelobj = self.root._dbmodel.obj
        if self.root._dbmodel.db.auto_static_enabled and modelobj:
            # REVIEW: this runtime insertion into the compiled model
            # during source-tree building is fragile — consider
            # deferring to build().
            tblname = self.parentNode.label
            pkgname = self.parentNode.parentNode.parentNode.label
            virtual_columns = modelobj[pkgname]['tables'][tblname]['virtual_columns']
            obj = DbVirtualColumnObj(structnode=vcsrc.parentNode, parent=virtual_columns)
            virtual_columns.children[obj.name.lower()] = obj
        return vcsrc

    def aliasColumn(self, name: str, relation_path: str, **kwargs: Any) -> Any:
        """Insert an alias column (shorthand for ``virtual_column``).

        Args:
            name: Column name.
            relation_path: Dotted relation path.

        Returns:
            The virtual-column source node.
        """
        return self.virtual_column(name, relation_path=relation_path, **kwargs)

    def joinColumn(self, name: str, **kwargs: Any) -> Any:
        """Insert a join column.

        Args:
            name: Column name.

        Returns:
            The virtual-column source node.
        """
        return self.virtual_column(name, join_column=True, **kwargs)

    def compositeColumn(
        self, name: str, columns: str | None = None, static: bool = True, **kwargs: Any,
    ) -> Any:
        """Insert a composite column combining multiple physical columns.

        Builds a SQL formula that concatenates the given columns into a
        JSON-style array string (``[val1, val2, ...]``).

        Args:
            name: Column name.
            columns: Comma-separated list of source column names
                (optionally prefixed with ``$``).
            static: If ``True``, cache the computed value.

        Returns:
            The virtual-column source node.
        """
        chunks: list[str] = []
        composed_of: list[str] = []
        for column in columns.split(','):
            if column.startswith('$'):
                column = column[1:]
            dtype, val = self.column(column).attributes.get('dtype', 'T'), f'${column}'
            if dtype in ('A', 'C', 'T'):
                val = f""" '"' ||  ${column} || '"' """
            elif dtype not in ('L', 'F', 'R', 'B'):
                val = rf""" '"' ||  ${column} || '\:\:{dtype}"' """
            composed_of.append(column)
            chunks.append(val)
        composed_of_str = ','.join(composed_of)
        if columns != composed_of_str:
            logger.warning(
                f"compositeColumn {name} has columns='{columns}'. "
                f"It should be '{composed_of_str}'."
            )

        sql_formula = " ||', '||".join(chunks)
        sql_formula = f"'[' || {sql_formula} || ']' "
        return self.virtual_column(
            name, composed_of=composed_of_str, static=static,
            sql_formula=sql_formula, dtype='JS', **kwargs,
        )

    def bagItemColumn(
        self,
        name: str,
        bagcolumn: str | None = None,
        itempath: str | None = None,
        dtype: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Insert a column that extracts a value from a Bag-typed column.

        Uses XPath on the XML representation of the Bag column to
        extract a scalar value.

        Args:
            name: Column name.
            bagcolumn: Name of the Bag-typed source column.
            itempath: Dot-separated path inside the Bag.
            dtype: Target data type.

        Returns:
            The virtual-column source node.
        """
        sql_formula = bagItemFormula(
            bagcolumn=bagcolumn, itempath=itempath, dtype=dtype, kwargs=kwargs,
        )
        return self.virtual_column(
            name, sql_formula=sql_formula,
            dtype=dtype, bagcolumn=bagcolumn, itempath=itempath, **kwargs,
        )

    def toolColumn(
        self, name: str, tool: str | None = None, dtype: str | None = None, **kwargs: Any,
    ) -> Any:
        """Insert a column that renders a link to an external tool.

        Args:
            name: Column name.
            tool: Tool identifier.
            dtype: Data type (``'P'`` for image, otherwise anchor).

        Returns:
            The virtual-column source node.
        """
        sql_formula = toolFormula(tool, dtype=dtype, kwargs=kwargs)
        return self.virtual_column(
            name, sql_formula=sql_formula,
            dtype=dtype, **kwargs,
        )

    def subQueryColumn(
        self,
        name: str,
        query: Any = None,
        mode: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Insert a column backed by a sub-query.

        Supports ``json`` aggregation, ``xml`` aggregation, or plain
        scalar/aggregate sub-selects.

        Args:
            name: Column name.
            query: Sub-query definition (dict or select spec).
            mode: Aggregation mode — ``'json'``, ``'xml'``, or ``None``.

        Returns:
            The virtual-column source node.
        """
        if mode == 'json':
            tname = f"{self.attributes.get('fullname').replace('.', '_')}_{name}"
            sql_formula = (
                f"SELECT json_agg(row_to_json({tname}_json)) "
                f"FROM #nestedselect {tname}_json"
            )
            return self.virtual_column(
                name, sql_formula=sql_formula, select_nestedselect=query,
                subquery=True, format='json_table', **kwargs,
            )
        if mode == 'xml':
            tname = f"{self.attributes.get('fullname').replace('.', '_')}_{name}"
            columns = query['columns'].replace('$', '')
            sql_formula = (
                f"SELECT xmlagg(xmlelement(name {tname}_xml,"
                f"xmlforest({columns}))) FROM #nestedselect {tname}_xml"
            )
            return self.virtual_column(
                name, sql_formula=sql_formula, select_nestedselect=query,
                subquery=True, **kwargs,
            )
        return self.virtual_column(
            name, select=query, subquery=True, subquery_aggr=mode, **kwargs,
        )

    def formulaColumn(
        self,
        name: str,
        sql_formula: str | None = None,
        select: Any = None,
        exists: Any = None,
        dtype: str = 'A',
        **kwargs: Any,
    ) -> Any:
        """Insert a formula column with an explicit SQL expression.

        Args:
            name: Column name.
            sql_formula: SQL expression.
            select: Sub-select definition.
            exists: EXISTS sub-query definition.
            dtype: Data type (default ``'A'``).

        Returns:
            The virtual-column source node.
        """
        return self.virtual_column(
            name, sql_formula=sql_formula, select=select,
            exists=exists, dtype=dtype, **kwargs,
        )

    def pyColumn(self, name: str, py_method: str | None = None, **kwargs: Any) -> Any:
        """Insert a Python-computed column.

        Args:
            name: Column name.
            py_method: Method name on the table's Python class.  Defaults
                to ``'pyColumn_<name>'``.

        Returns:
            The virtual-column source node.
        """
        py_method = py_method or 'pyColumn_%s' % name
        return self.virtual_column(name, py_method=py_method, **kwargs)

    def aliasTable(self, name: str, relation_path: str, **kwargs: Any) -> Any:
        """Insert a related table alias.

        Args:
            name: Alias name (optionally ``name::dtype``).
            relation_path: Dotted relation path.

        Returns:
            The alias source node.
        """
        if '::' in name:
            name, dtype = name.split('::')
        if 'table_aliases' not in self:
            self.child('tblalias_list', 'table_aliases')
        return self.child(
            'table_alias', 'table_aliases.@%s' % name,
            relation_path=relation_path, **kwargs,
        )

    table_alias = aliasTable

    def index(
        self,
        columns: str | list[str] | tuple[str, ...] | None = None,
        name: str | None = None,
        unique: bool | None = None,
    ) -> Any:
        """Add an index to the table.

        Args:
            columns: Column name(s) — string, list, or tuple.
            name: Explicit index name.  Defaults to
                ``<table>_<columns>_key``.
            unique: If ``True``, create a UNIQUE index.

        Returns:
            The index source node.
        """
        if isinstance(columns, (list, tuple)):
            columns = ','.join(columns)
        if not name:
            name = '%s_%s_key' % (self.parentNode.label, columns.replace(',', '_'))
        if 'indexes' not in self:
            self.child('index_list', 'indexes')

        child = self.child('index', 'indexes.%s' % name, columns=columns, unique=unique)
        return child

    def relation(
        self,
        related_column: str | None = None,
        related_table: str | None = None,
        mode: str = 'relation',
        one_name: str | None = None,
        many_name: str | None = None,
        eager_one: Any = None,
        eager_many: Any = None,
        one_one: str | None = None,
        child: Any = None,
        one_group: str | None = None,
        many_group: str | None = None,
        onUpdate: str | None = None,
        onUpdate_sql: str = 'cascade',
        onDelete: str | None = None,
        onDelete_sql: str | None = None,
        deferred: bool | None = None,
        relation_name: str | None = None,
        onDuplicate: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Add a relation between two tables.

        This method is called on a column source node and creates a
        child ``relation`` node linking the current column to
        *related_column*.

        Args:
            related_column: Target column path
                (``pkg.table.column`` or ``table.column``).
            related_table: Unused — kept for backwards compatibility.
            mode: Relation mode (``'relation'``, ``'foreignkey'``,
                ``'insensitive'``).
            one_name: Display name for the one-to-many side.
            many_name: Display name for the many-to-one side.
            eager_one: Eager-loading flag for the one side.
            eager_many: Eager-loading flag for the many side.
            one_one: If ``'*'``, treat as one-to-one.
            onDelete: Python-level delete action.
            onDelete_sql: SQL-level delete action.
            onUpdate: Python-level update action.
            onUpdate_sql: SQL-level update action (default
                ``'cascade'``).
            deferred: If ``True``, defer constraint checking.
            relation_name: Override for the inverse-relation label.

        Returns:
            The relation source node.
        """
        fkey_group = self.attributes.get('group')
        if one_group is None and fkey_group and fkey_group != '_':
            self.attributes['group'] = '_'
            one_group = fkey_group
            self.attributes['one_group'] = one_group
        return self.setItem(
            'relation', self.__class__(),
            related_column=related_column, mode=mode,
            one_name=one_name, many_name=many_name, one_one=one_one, child=child,
            one_group=one_group, many_group=many_group, deferred=deferred,
            onUpdate=onUpdate, onDelete=onDelete,
            eager_one=eager_one, eager_many=eager_many,
            onUpdate_sql=onUpdate_sql, onDelete_sql=onDelete_sql,
            relation_name=relation_name, onDuplicate=onDuplicate, **kwargs,
        )
