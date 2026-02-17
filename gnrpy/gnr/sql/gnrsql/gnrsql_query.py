# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.query : Query API and model navigation for GnrSqlDb
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

"""Mixin providing query API and model navigation for ``GnrSqlDb``.

Contains ``query``, ``queryCompile``, ``table``, ``package``, and the
model introspection helpers (``tablesMasterIndex``, ``tableTreeBag``, etc.).
"""

from __future__ import annotations

import re
from typing import Any, Callable, Generator

from gnr.core.gnrbag import Bag
from gnr.sql import logger
from gnr.sql.gnrsql.gnrsql_helpers import GnrSqlException
from gnr.sql.gnrsql_exceptions import GnrSqlMissingTable


class QueryMixin:
    """High-level query API and model navigation."""

    def package(self, pkg: str) -> Any:
        """Return a package object by name.

        Args:
            pkg: The package name.

        Returns:
            The package object from the model.
        """
        return self.model.package(pkg)

    def _get_packages(self) -> Any:
        """Property getter for ``packages``."""
        return self.model.obj

    packages = property(_get_packages)

    def tablesMasterIndex(
        self,
        hard: bool = False,
        filterCb: Callable[[Any], bool] | None = None,
        filterPackages: list[str] | None = None,
    ) -> Bag:
        """Build a dependency-ordered index of all tables.

        Tables are sorted so that each table appears after all its
        non-deferred dependencies.  Used primarily during data import
        to respect foreign-key ordering.

        Args:
            hard: If ``True``, include cross-package dependencies even
                when the dependency's package was loaded earlier.
            filterCb: Optional predicate to filter tables.
            filterPackages: Restrict to these package names.

        Returns:
            A :class:`Bag` with table fullnames as keys, in dependency order.

        Raises:
            GnrSqlException: If circular dependencies prevent resolution.
        """
        packages = self.packages.keys()
        filterPackages = filterPackages or packages
        toImport: list[Any] = []
        dependencies: dict[str, set[str]] = {}
        for k, pkg in enumerate(packages):
            if pkg not in filterPackages:
                continue
            pkgobj = self.package(pkg)
            tables = list(pkgobj.tables.values())
            if filterCb:
                tables = list(filter(filterCb, tables))
            toImport.extend(tables)
            for tbl in tables:
                dset: set[str] = set()
                for d, isdeferred in tbl.dependencies:
                    dpkg = d.split('.')[0]
                    if dpkg not in filterPackages:
                        continue
                    if not isdeferred and (packages.index(dpkg) <= k or hard):
                        dset.add(d)
                dependencies[tbl.fullname] = dset
        imported: set[str] = set()
        deferred: dict[str, set[str]] = {}
        blocking: dict[str, set[str]] = {}
        result = Bag()
        self._tablesMasterIndex_step(
            toImport=toImport,
            imported=imported,
            dependencies=dependencies,
            result=result,
            deferred=deferred,
            blocking=blocking,
        )
        if len(deferred) == 0:
            return result
        for k, v in list(deferred.items()):
            logger.info("Table %s blocked by %s", k, v)
        raise GnrSqlException(description='Blocked dependencies')

    def _tablesMasterIndex_step(
        self,
        toImport: list[Any] | None = None,
        imported: set[str] | None = None,
        dependencies: dict[str, set[str]] | None = None,
        result: Bag | None = None,
        deferred: dict[str, set[str]] | None = None,
        blocking: dict[str, set[str]] | None = None,
    ) -> None:
        """Single pass of the dependency-resolution algorithm.

        Iterates over *toImport*, adding each table whose dependencies
        are satisfied to *result*.  Tables that cannot yet be resolved
        are placed in *deferred* / *blocking* for the next pass.

        Args:
            toImport: Tables remaining to be processed.
            imported: Set of already-resolved table fullnames.
            dependencies: Map of ``fullname -> set of dependency fullnames``.
            result: Accumulator :class:`Bag` for resolved tables.
            deferred: Tables that still have unresolved deps.
            blocking: Reverse map: ``dep -> set of tables it blocks``.
        """
        while toImport:
            tbl = toImport.pop(0)
            tblname = tbl.fullname
            depset = dependencies[tblname]
            if depset.issubset(imported):
                imported.add(tblname)
                result.setItem(tblname, None)
                result.setItem(
                    '_index_.%s' % tblname.replace('.', '/'), None, tbl=tblname
                )
                blocked_tables = blocking.pop(tblname, None)
                if blocked_tables:
                    for k in blocked_tables:
                        deferred[k].remove(tblname)
                        if not deferred[k]:
                            deferred.pop(k)
                        m = self.table(k).model
                        if m not in toImport:
                            toImport.append(m)
            else:
                deltatbl = depset - imported
                deferred[tblname] = deltatbl
                for k in deltatbl:
                    blocking.setdefault(k, set()).add(tblname)

    def tableTreeBag(
        self,
        packages: list[str] | None = None,
        omit: bool | None = None,
        tabletype: str | None = None,
    ) -> Bag:
        """Build a hierarchical Bag of packages and their tables.

        Args:
            packages: List of package names to include (or exclude if
                *omit* is ``True``).  Pass ``'*'`` to start from all packages.
            omit: If ``True``, *packages* is treated as an exclusion list.
            tabletype: Filter tables by their ``tabletype`` attribute.

        Returns:
            A nested :class:`Bag` keyed by ``pkg/table``.
        """
        result = Bag()
        packages = list(self.packages.keys()) if packages == '*' else packages
        for pkg, pkgobj in list(self.packages.items()):
            if (pkg in packages and omit) or (pkg not in packages and not omit):
                continue
            pkgattr = dict(pkgobj.attributes)
            pkgattr['caption'] = pkgobj.attributes.get('name_long', pkg)
            result.setItem(pkg, Bag(), **pkgattr)
            for tbl, tblobj in list(pkgobj.tables.items()):
                tblattr = dict(tblobj.attributes)
                if tabletype and tblattr.get('tabletype') != tabletype:
                    continue
                tblattr['caption'] = tblobj.attributes.get('name_long', pkg)
                result[pkg].setItem(tbl, None, **tblattr)
            if len(result[pkg]) == 0:
                result.pop(pkg)
        return result

    @property
    def tables(self) -> Generator[Any, None, None]:
        """Yield every ``dbtable`` object across all packages."""
        for pkgobj in self.packages.values():
            for tblobj in pkgobj.tables.values():
                yield tblobj.dbtable

    def filteredTables(
        self, filterStr: str | None = None
    ) -> Generator[Any, None, None]:
        """Yield tables whose fullname matches the given filter.

        Args:
            filterStr: A comma-separated list of prefixes.  A table is
                yielded if its ``fullname`` starts with any of them.
                If ``None``, all tables are yielded.
        """
        regex_pattern = None
        if filterStr is not None:
            patterns = filterStr.split(',')
            regex_pattern = rf"^({'|'.join(re.escape(p) for p in patterns)})(\.|$)"
        for tblobj in self.tables:
            if regex_pattern is None or bool(re.match(regex_pattern, tblobj.fullname)):
                yield tblobj

    def table(self, tblname: str, pkg: str | None = None) -> Any:
        """Return a table object by name.

        Args:
            tblname: The table name in ``'pkg.table'`` format.
            pkg: Optional explicit package name.

        Returns:
            The table's ``dbtable`` proxy object.

        Raises:
            GnrSqlMissingTable: If the table does not exist in the model.
        """
        srctbl = self.model.table(tblname, pkg=pkg)
        if hasattr(srctbl, 'dbtable'):
            return srctbl.dbtable
        if srctbl is None:
            raise GnrSqlMissingTable(f"Missing package providing table {tblname}")
        # during building model
        return srctbl._mixinobj

    def query(self, table: str, **kwargs: Any) -> Any:
        """Create and return a query object for the given table.

        Args:
            table: The table name in ``'pkg.table'`` format.
            **kwargs: Forwarded to the table's ``query()`` method.

        Returns:
            An :class:`SqlQuery` instance.
        """
        return self.table(table).query(**kwargs)

    def queryCompile(
        self,
        table: str | None = None,
        columns: str = '*',
        where: str | None = None,
        order_by: str | None = None,
        distinct: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
        group_by: str | None = None,
        having: str | None = None,
        for_update: bool = False,
        relationDict: dict[str, Any] | None = None,
        sqlparams: dict[str, Any] | None = None,
        excludeLogicalDeleted: bool = True,
        excludeDraft: bool = True,
        addPkeyColumn: bool = True,
        ignorePartition: bool = False,
        locale: str | None = None,
        mode: str | None = None,
        _storename: str | None = None,
        aliasPrefix: str | None = None,
        ignoreTableOrderBy: bool | None = None,
        subtable: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Compile a query to raw SQL text.

        Builds a query, extracts its SQL, and replaces any extra
        ``kwargs`` parameters with ``env_*`` references so they can
        be resolved at execution time.

        Args:
            table: The table name in ``'pkg.table'`` format.
            columns: Column specification string.
            where: SQL WHERE clause.
            order_by: SQL ORDER BY clause.
            distinct: Whether to apply DISTINCT.
            limit: Maximum number of rows.
            offset: Row offset.
            group_by: SQL GROUP BY clause.
            having: SQL HAVING clause.
            for_update: If ``True``, add ``FOR UPDATE``.
            relationDict: Pre-resolved relation dict.
            sqlparams: Additional SQL parameters.
            excludeLogicalDeleted: Exclude soft-deleted records.
            excludeDraft: Exclude draft records.
            addPkeyColumn: Ensure the pkey column is selected.
            ignorePartition: Bypass partition filtering.
            locale: Override locale for translation.
            mode: Query mode.
            _storename: Override store name.
            aliasPrefix: Prefix for column aliases.
            ignoreTableOrderBy: If set, ignore the table's default ordering.
            subtable: Subtable filter name.
            **kwargs: Extra parameter bindings injected into ``currentEnv``.

        Returns:
            The compiled SQL text as a string.
        """
        q = self.table(table).query(
            columns=columns,
            where=where,
            order_by=order_by,
            distinct=distinct,
            limit=limit,
            offset=offset,
            group_by=group_by,
            having=having,
            for_update=for_update,
            relationDict=relationDict,
            sqlparams=sqlparams,
            excludeLogicalDeleted=excludeLogicalDeleted,
            excludeDraft=excludeDraft,
            ignorePartition=ignorePartition,
            addPkeyColumn=addPkeyColumn,
            locale=locale,
            _storename=_storename,
            aliasPrefix=aliasPrefix,
            ignoreTableOrderBy=ignoreTableOrderBy,
            subtable=subtable,
        )
        result = q.sqltext
        if kwargs:
            prefix = str(id(kwargs))
            currentEnv = self.currentEnv
            for k, v in list(kwargs.items()):
                newk = '%s_%s' % (prefix, k)
                currentEnv[newk] = v
                result = re.sub(
                    "(:)(%s)(\\W|$)" % k,
                    lambda m: '%senv_%s%s' % (m.group(1), newk, m.group(3)),
                    result,
                )
        return result

    def colToAs(self, col: str) -> str:
        """Convert a column path to a valid SQL alias.

        Replaces all non-word characters with underscores and prepends
        an underscore if the result starts with a digit.

        Args:
            col: The column path (e.g. ``'@rel.col_name'``).

        Returns:
            A sanitised alias string.
        """
        as_ = re.sub(r'\W', '_', col)
        if as_[0].isdigit():
            as_ = '_' + as_
        return as_

    def relationExplorer(
        self,
        table: str,
        prevCaption: str = '',
        prevRelation: str = '',
        translator: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Return a relation explorer for the given table.

        Delegates to the table's own ``relationExplorer`` method.

        Args:
            table: The table name in ``'pkg.table'`` format.
            prevCaption: Accumulated caption prefix.
            prevRelation: Accumulated relation path prefix.
            translator: Optional translation callable.
            **kwargs: Forwarded to the table's ``relationExplorer()``.

        Returns:
            A relation explorer object.
        """
        return self.table(table).relationExplorer(
            prevCaption=prevCaption,
            prevRelation=prevRelation,
            translator=translator,
            **kwargs,
        )

    def localVirtualColumns(self, table: str) -> None:
        """Return local virtual columns for a table.

        Base implementation returns ``None``.  Overridden by
        ``GnrSqlAppDb`` to provide application-level virtual columns.

        Args:
            table: The table name.
        """
        return None

    def toJson(self, **kwargs: Any) -> list[Any]:
        """Return a JSON-serialisable representation of all packages.

        Returns:
            A list of per-package JSON dicts.
        """
        return [t.toJson() for t in self.packages.values()]
