# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.schema : DDL, model I/O and data import/export for GnrSqlDb
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

"""Mixin providing DDL operations, model I/O and data import/export.

Groups together database-level operations that modify the schema
(``createDb``, ``dropDb``, ``checkDb``, etc.) and bulk data
operations (``importArchive``, ``importXmlData``, ``dump``, ``restore``).
"""

from __future__ import annotations

import os
import pickle
import shutil
from typing import Any, Callable

from gnr.core.gnrbag import Bag
from gnr.sql import logger
from gnr.sql._typing import GnrSqlDbBaseMixin
from gnr.sql.gnrsqlmigration import SqlMigrator


class SchemaMixin(GnrSqlDbBaseMixin):
    """DDL, model persistence, dump/restore and data import."""

    # -- Model I/O ----------------------------------------------------------

    def packageSrc(self, name: str) -> Any:
        """Return the model source for the named package.

        Args:
            name: The package name.

        Returns:
            A ``DbModelSrc`` node.
        """
        return self.model.src.package(name)

    def packageMixin(self, name: str, obj: Any) -> None:
        """Register a mixin class or object for a package.

        Args:
            name: The target package name.
            obj: The class or object to mix in.
        """
        self.model.packageMixin(name, obj)

    def tableMixin(self, tblpath: str, obj: Any) -> None:
        """Register a mixin class or object for a table.

        Args:
            tblpath: The table path (``'pkg.table'``).
            obj: The class or object to mix in.
        """
        self.model.tableMixin(tblpath, obj)

    def loadModel(self, source: str | None = None) -> None:
        """Load the model source from an XML file, text or URL.

        Args:
            source: The XML model source.  If ``None``, loads from
                the default location.
        """
        self.model.load(source)

    def importModelFromDb(self) -> None:
        """Populate the model source from the database's information schema."""
        self.model.importFromDb()

    def saveModel(self, path: str) -> None:
        """Save the current model to an XML file.

        Args:
            path: The destination file path.
        """
        self.model.save(path)

    def checkDb(self, applyChanges: bool = False) -> Any:
        """Check the database schema against the current model.

        Args:
            applyChanges: If ``True``, apply and commit all pending changes.

        Returns:
            The result of the model check (adapter-specific).
        """
        return self.model.check(applyChanges=applyChanges)

    def diffOrmToSql(self) -> Any:
        """Return the list of changes between the ORM model and the live database.

        Returns:
            A list of migration change objects.
        """
        migrator = SqlMigrator(self)
        return migrator.getChanges()

    def syncOrmToSql(self) -> None:
        """Apply any pending ORM-to-SQL migrations."""
        migrator = SqlMigrator(self)
        changes = migrator.getChanges()
        if changes:
            migrator.applyChanges()

    # -- Data import --------------------------------------------------------

    def importArchive(
        self, archive: Bag, thermo_wrapper: Callable[..., Any] | None = None
    ) -> None:
        """Import records from a Bag archive, skipping existing primary keys.

        Args:
            archive: A :class:`Bag` keyed by ``'pkg/table'`` with lists
                of record dicts as values.
            thermo_wrapper: Optional progress-bar wrapper for the table list.
        """
        tables = list(archive.keys())
        if thermo_wrapper:
            tables = thermo_wrapper(
                tables,
                maximum=len(tables),
                message=lambda item, k, m, **kwargs: '%s %i/%i' % (item, k, m),
                line_code='tables',
            )
        for tbl in tables:
            records = archive[tbl]
            if not records:
                continue
            tblobj = self.table(tbl.replace('/', '.'))
            pkeysToAdd = [r[tblobj.pkey] for r in records]
            f = tblobj.query(
                where='$%s IN :pkeys' % tblobj.pkey,
                pkeys=pkeysToAdd,
                addPkeyColumns=False,
                excludeLogicalDeleted=False,
                excludeDraft=False,
                columns='$%s' % tblobj.pkey,
                subtable='*',
            ).fetch()
            pkeysToAdd = set(pkeysToAdd) - set([r[tblobj.pkey] for r in f])
            rlist = [dict(r) for r in records if r[tblobj.pkey] in pkeysToAdd]
            if rlist:
                self.setConstraintsDeferred()
                onArchiveImport = getattr(tblobj, 'onArchiveImport', None)
                if onArchiveImport:
                    onArchiveImport(rlist)
                for r in rlist:
                    if r.get('__syscode'):
                        r['__syscode'] = None
                tblobj.insertMany(rlist)

    def autoRestore(
        self,
        path: str,
        sqltextCb: Callable[[str], str] | None = None,
        onRestored: Callable[..., Any] | None = None,
    ) -> None:
        """Restore a full multi-store archive from a zip or directory.

        Drops existing stores, restores the main database and each
        additional store from the archive.

        Args:
            path: Path to a ``.zip`` file or an extracted directory.
            sqltextCb: Optional callback that pre-processes the SQL dump
                file path before restore.
            onRestored: Optional callback invoked after each restore,
                receiving ``(self, dbname=...)``.

        Raises:
            AssertionError: If *path* does not exist.
        """
        # REVIEW: assert is stripped when running with python -O.  Consider
        # raising a proper exception (e.g. FileNotFoundError) instead.
        assert os.path.exists(path), 'Restore archive %s does not exist' % path
        extractpath = path.replace('.zip', '')
        destroyFolder = False
        if not os.path.isdir(path):
            from zipfile import ZipFile

            myzip = ZipFile(path, 'r')
            myzip.extractall(extractpath)
            destroyFolder = True
        stores: dict[str, str] = {}
        for f in os.listdir(extractpath):
            if f.startswith('.'):
                continue
            dbname = os.path.splitext(f)[0]
            stores[dbname] = os.path.join(extractpath, f)
        dbstoreconfig = Bag(stores.pop('_dbstores'))
        mainfilepath = stores.pop('mainstore', None)
        try:
            storeconfs = (
                self.stores_handler.raw_multdb_dbstores().values()
                if self.stores_handler
                else []
            )
        except Exception:
            storeconfs = []
        for storeconf in storeconfs:
            self.dropDb(storeconf['database'])
        if mainfilepath:
            self._autoRestore_one(
                dbname=self.dbname,
                filepath=mainfilepath,
                sqltextCb=sqltextCb,
                onRestored=onRestored,
            )
        for storename, filepath in list(stores.items()):
            dbattr = dbstoreconfig.getAttr(storename)
            dbname = dbattr.pop('dbname')
            self._autoRestore_one(
                dbname=dbname,
                filepath=filepath,
                sqltextCb=sqltextCb,
                onRestored=onRestored,
            )
        if destroyFolder:
            shutil.rmtree(extractpath)

    def _autoRestore_one(
        self,
        dbname: str | None = None,
        filepath: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Drop, create and restore a single database.

        Args:
            dbname: The database name.
            filepath: The dump file to restore from.
            **kwargs: Forwarded to ``restore()``.
        """
        logger.debug('drop %s', dbname)
        self.dropDb(dbname)
        logger.debug('create %s', dbname)
        self.createDb(dbname)
        logger.debug('restore %s from %s ', dbname, filepath)
        self.restore(filepath, dbname=dbname, **kwargs)

    # -- DDL ----------------------------------------------------------------

    def createDb(self, name: str, encoding: str = 'unicode') -> None:
        """Create a new database.

        Args:
            name: The database name.
            encoding: The character encoding (default ``'unicode'``).
        """
        self.adapter.createDb(name, encoding=encoding)

    def dropDb(self, name: str) -> None:
        """Drop a database.

        Args:
            name: The database name.
        """
        self.adapter.dropDb(name)

    def dropTable(self, table: str, cascade: bool | None = None) -> None:
        """Drop a table from the database.

        Args:
            table: The table name (``'pkg.table'``).
            cascade: If ``True``, cascade the drop to dependent objects.
        """
        self.adapter.dropTable(self.table(table), cascade=cascade)

    def dropColumn(self, column: str, cascade: bool | None = None) -> None:
        """Drop a column from a table.

        Args:
            column: The column path (``'pkg.table.column'``).
            cascade: If ``True``, cascade the drop.
        """
        col = self.model.column(column)
        self.adapter.dropColumn(col.table.sqlfullname, col.sqlname, cascade=cascade)

    def dump(self, filename: str, dbname: str | None = None, **kwargs: Any) -> Any:
        """Dump the database to a file.

        Args:
            filename: The output file path.
            dbname: Override the database name.
            **kwargs: Forwarded to the adapter's ``dump()``.

        Returns:
            Adapter-specific result.
        """
        return self.adapter.dump(filename, dbname=dbname, **kwargs)

    def restore(
        self,
        filename: str,
        dbname: str | None = None,
        sqltextCb: Callable[[str], str] | None = None,
        onRestored: Callable[..., Any] | None = None,
    ) -> None:
        """Restore a database from a dump file.

        Args:
            filename: The dump file path.
            dbname: Override the target database name.
            sqltextCb: Optional callback that pre-processes *filename*
                before passing it to the adapter.
            onRestored: Optional callback invoked after restore,
                receiving ``(self, dbname=...)``.
        """
        if sqltextCb:
            filename = sqltextCb(filename)
        self.adapter.restore(filename, dbname=dbname)
        if onRestored:
            onRestored(self, dbname=dbname)

    def createSchema(self, name: str) -> None:
        """Create a database schema (Postgres).

        Args:
            name: The schema name.
        """
        self.adapter.createSchema(name)

    def dropSchema(self, name: str) -> None:
        """Drop a database schema (Postgres).

        Args:
            name: The schema name.
        """
        self.adapter.dropSchema(name)

    # -- XML / pickle I/O ---------------------------------------------------

    def importXmlData(self, path: str) -> None:
        """Populate the database from an XML data file.

        For each table in the XML, calls ``insertOrUpdate`` for every
        record node.

        Args:
            path: The XML file path.
        """
        data = Bag(path)
        for table, pkg in data.digest('#k,#a.pkg'):
            for n in data[table]:
                self.table(table, pkg=pkg).insertOrUpdate(n.attr)

    def freezedPkeys(self, fpath: str) -> list[Any]:
        """Load a pickled list of primary keys from disk.

        Args:
            fpath: Base file path (``'_pkeys.pik'`` is appended).

        Returns:
            The list of primary keys, or an empty list if the file
            does not exist.
        """
        filename = '%s_pkeys.pik' % fpath
        if not os.path.exists(filename):
            return []
        with open(filename, 'rb') as f:
            return pickle.load(f)

    def unfreezeSelection(self, fpath: str) -> Any:
        """Restore a pickled selection object from disk.

        Reconnects the selection's ``dbtable`` to the current db instance.

        Args:
            fpath: Base file path (``'.pik'`` is appended).

        Returns:
            The restored selection, or ``None`` if the file does not exist.
        """
        filename = '%s.pik' % fpath
        if not os.path.exists(filename):
            return
        with open('%s.pik' % fpath, 'rb') as f:
            selection = pickle.load(f)
        selection.dbtable = self.table(selection.tablename)
        return selection
