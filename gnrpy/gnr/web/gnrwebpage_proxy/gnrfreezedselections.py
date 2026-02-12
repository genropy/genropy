# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrfreezedselections : proxy for freezed selection lifecycle
# Copyright (c)     : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Proxy for freezed selection lifecycle.

This is the **only** entry point for persisting and restoring SQL selections
on the page's connection folder.  No external code should call
``SqlSelection.freeze`` or ``GnrSqlDb.unfreezeSelection`` directly.

Two storage backends are available:

- **Pickle** (default): serializes the ``SqlSelection`` object and its data
  into separate ``.pik`` files.
- **SQLite**: stores each selection as a lightweight SQLite database
  (via ``GnrSqlDb``) alongside a ``columns.json`` metadata file.

The active backend is selected through the ``freeze_on_sqlite`` preference
in the ``sys`` package, or overridden per-page via the ``use_freeze_sqlite``
attribute (useful for testing).

Architecture
------------
``GnrFreezedSelections`` is a page proxy (``GnrBaseProxy``) that delegates
all storage operations to a backend object following the Strategy pattern::

    GnrFreezedSelections  (proxy, public API)
        |
        +-- GnrFreezedSelectionsPickle   (backend)
        +-- GnrFreezedSelectionsSqlite   (backend)

Both backends inherit from ``GnrFreezedSelectionsBackend`` and implement
the same four methods: ``freezeSelection``, ``freezeSelectionUpdate``,
``unfreezeSelection``, ``freezedPkeys``.

Disk layout
-----------
For each frozen selection a dedicated folder is created at
``<connectionFolder>/<page_id>/<selectionName>/``.

Pickle backend contents::

    selection.pik          -- serialized SqlSelection (without data)
    selection_data.pik     -- pickled row data
    selection_pkeys.pik    -- pickled list of primary keys
    selection_filtered.pik -- pickled filtered data (if any)

SQLite backend contents::

    columns.json           -- column definitions + query metadata
    selection.sqlite       -- GnrSqlDb sqlite with one table: sel.selection_data
"""

import json
import os
import pickle
import shutil
import tempfile

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrlist import GnrNamedList
from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.gnrsqldata import SqlSelection
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy


class GnrFreezedSelectionsBackend(object):
    """Base class for freeze/unfreeze storage backends.

    Holds a reference to the owning ``GnrFreezedSelections`` proxy,
    giving access to ``proxy.db``, ``proxy.pageLocalDocument()`` etc.

    Provides the common ``selection_folder`` method that both backends
    use to obtain (and create) the per-selection storage folder.

    Args:
        proxy: The ``GnrFreezedSelections`` proxy instance.
    """

    def __init__(self, proxy):
        self.proxy = proxy

    def selection_folder(self, name, page_id=None):
        """Return (and create if needed) the folder for a named selection.

        The folder path is ``pageLocalDocument(name)`` -- a directory inside
        the connection/page area.  Both pickle and sqlite backends store
        their files inside this folder.

        Args:
            name: Logical selection name.
            page_id: Optional page_id override (for cross-page access).

        Returns:
            Absolute path to the selection folder.
        """
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return folder


class GnrFreezedSelectionsPickle(GnrFreezedSelectionsBackend):
    """Pickle-based backend (default).

    Serializes the ``SqlSelection`` and its data into separate ``.pik``
    files inside the selection folder.  All pickle I/O is managed here;
    ``SqlSelection`` is treated as a pure in-memory container.

    File layout inside the selection folder::

        selection.pik          -- the SqlSelection object (data replaced by None)
        selection_data.pik     -- the row data list
        selection_pkeys.pik    -- primary key list (optional)
        selection_filtered.pik -- filtered data list (optional)
    """

    def _pickle_dump(self, obj, path):
        """Atomically write a pickled object to *path*.

        Uses a temporary file + rename to avoid corrupt files on crash.

        Args:
            obj: The Python object to pickle.
            path: Destination file path.
        """
        handle, tmp_path = tempfile.mkstemp(suffix='.pik')
        with os.fdopen(handle, 'wb') as f:
            pickle.dump(obj, f)
        shutil.move(tmp_path, path)

    def freezeSelection(self, selection, name, freezePkeys=False, **kwargs):
        """Persist a selection to disk as pickle files.

        Saves the selection object (with data stripped out), the row data,
        and optionally the primary keys into separate pickle files.

        Args:
            selection: The ``SqlSelection`` to freeze.
            name: Logical name used to build the folder path.
            freezePkeys: If ``True``, also persist the primary key list.

        Returns:
            The folder path of the frozen selection.
        """
        folder = self.selection_folder(name)
        base = os.path.join(folder, 'selection')

        saved_dbtable = selection.dbtable
        saved_data = selection._frz_data
        saved_filtered = selection._frz_filtered_data

        selection.dbtable = None
        selection._frz_data = None
        selection._frz_filtered_data = None
        selection.freezepath = base
        self._pickle_dump(selection, '%s.pik' % base)

        selection.dbtable = saved_dbtable
        selection._frz_data = saved_data
        selection._frz_filtered_data = saved_filtered

        self._pickle_dump(saved_data, '%s_data.pik' % base)

        if saved_filtered is not None:
            self._pickle_dump(saved_filtered, '%s_filtered.pik' % base)
        else:
            filtered_path = '%s_filtered.pik' % base
            if os.path.isfile(filtered_path):
                os.remove(filtered_path)

        if freezePkeys:
            self._pickle_dump(selection.output('pkeylist'),
                              '%s_pkeys.pik' % base)

        return folder

    def freezeSelectionUpdate(self, selection):
        """Re-persist an already-frozen selection after in-memory changes.

        Only rewrites the files whose content has changed, based on the
        ``isChangedData``, ``isChangedFiltered`` and ``isChangedSelection``
        flags.

        Args:
            selection: The ``SqlSelection`` to update on disk.
        """
        base = selection.freezepath
        if not base:
            return

        if selection.isChangedData:
            self._pickle_dump(selection._frz_data, '%s_data.pik' % base)

        if selection.isChangedFiltered:
            if selection._frz_filtered_data is not None:
                self._pickle_dump(selection._frz_filtered_data,
                                  '%s_filtered.pik' % base)
            else:
                filtered_path = '%s_filtered.pik' % base
                if os.path.isfile(filtered_path):
                    os.remove(filtered_path)

        if selection.isChangedSelection:
            saved_dbtable = selection.dbtable
            saved_data = selection._frz_data
            saved_filtered = selection._frz_filtered_data

            selection.dbtable = None
            selection._frz_data = None
            selection._frz_filtered_data = None
            self._pickle_dump(selection, '%s.pik' % base)

            selection.dbtable = saved_dbtable
            selection._frz_data = saved_data
            selection._frz_filtered_data = saved_filtered

        selection.isChangedSelection = False
        selection.isChangedData = False
        selection.isChangedFiltered = False

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        """Restore a previously frozen selection from pickle files.

        Loads the selection object and immediately populates it with
        data and filtered data from their respective pickle files.
        The returned selection is fully usable with no lazy loading.

        Args:
            dbtable: Expected table (string or table object).
            name: Logical name matching the one used during freeze.
            page_id: Optional page_id override (for cross-page access).

        Returns:
            The restored ``SqlSelection``, or ``None`` if not found.

        Raises:
            AssertionError: If *name* is empty or the restored selection
                belongs to a different table than *dbtable*.
        """
        assert name, 'name is mandatory'
        if isinstance(dbtable, str):
            dbtable = self.proxy.db.table(dbtable)
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        base = os.path.join(folder, 'selection')
        selection_path = '%s.pik' % base
        if not os.path.exists(selection_path):
            return None

        with open(selection_path, 'rb') as f:
            selection = pickle.load(f)

        selection.dbtable = self.proxy.db.table(selection.tablename)
        selection.freezepath = base

        data_path = '%s_data.pik' % base
        with open(data_path, 'rb') as f:
            selection._frz_data = pickle.load(f)

        filtered_path = '%s_filtered.pik' % base
        if os.path.exists(filtered_path):
            with open(filtered_path, 'rb') as f:
                selection._frz_filtered_data = pickle.load(f)

        if dbtable and selection is not None:
            assert dbtable == selection.dbtable, \
                'unfrozen selection does not belong to the given table'
        return selection

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        """Return the list of pkeys from a frozen selection.

        Reads the pkeys pickle file directly without loading the full
        selection data.

        Args:
            dbtable: Expected table (string or table object).
            name: Logical name matching the one used during freeze.
            page_id: Optional page_id override.

        Returns:
            A list of primary key values, or an empty list if not found.
        """
        assert name, 'name is mandatory'
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        pkeys_path = os.path.join(folder, 'selection_pkeys.pik')
        if not os.path.exists(pkeys_path):
            return []
        with open(pkeys_path, 'rb') as f:
            return pickle.load(f)


class GnrFreezedSelectionsSqlite(GnrFreezedSelectionsBackend):
    """SQLite-based backend.

    Each frozen selection is stored as a ``columns.json`` metadata file
    and a ``selection.sqlite`` database inside a dedicated folder.

    The SQLite database is managed through ``GnrSqlDb`` with a single
    package ``sel`` containing one table ``selection_data``.  Column types
    are taken from the selection's ``colAttrs['dataType']``.
    """

    def _meta_path(self, folder):
        """Return the path to ``columns.json`` inside the given folder."""
        return os.path.join(folder, 'columns.json')

    def _db_path(self, folder):
        """Return the path to ``selection.sqlite`` inside the given folder."""
        return os.path.join(folder, 'selection.sqlite')

    def _save_meta(self, folder, selection):
        """Serialize selection metadata to ``columns.json``.

        Saved fields: ``tablename``, ``querypars``, ``colAttrs``,
        ``allColumns``, ``sortedBy``, ``key``.

        Args:
            folder: Target folder path.
            selection: The ``SqlSelection`` whose metadata to save.
        """
        meta = dict(
            tablename=selection.tablename,
            querypars=selection.querypars,
            colAttrs={k: dict(v) for k, v in selection.colAttrs.items()},
            allColumns=selection.allColumns,
            sortedBy=selection.sortedBy,
            key=selection.key
        )
        with open(self._meta_path(folder), 'w') as f:
            json.dump(meta, f)

    def _load_meta(self, folder):
        """Deserialize selection metadata from ``columns.json``.

        Args:
            folder: Folder containing the metadata file.

        Returns:
            A dict with keys: ``tablename``, ``querypars``, ``colAttrs``,
            ``allColumns``, ``sortedBy``, ``key``.
        """
        with open(self._meta_path(folder)) as f:
            return json.load(f)

    def _sqlite_db(self, folder, meta):
        """Create a ``GnrSqlDb`` instance with the model matching the selection columns.

        Builds the in-memory model (package ``sel``, table ``selection_data``)
        with one column per entry in ``meta['allColumns']``, plus the internal
        ``_rowidx`` column used as primary key.  Column types are read from
        ``colAttrs[col]['dataType']`` (set by ``_prepColAttrs`` during query).

        Args:
            folder: Folder containing ``selection.sqlite``.
            meta: Metadata dict as returned by ``_load_meta``.

        Returns:
            A configured and started ``GnrSqlDb`` instance.
        """
        db_path = self._db_path(folder)
        db = GnrSqlDb(implementation='sqlite', dbname=db_path)
        pkg = db.packageSrc('sel')
        pkg.attributes.update(name_short='sel', name_long='sel',
                              name_full='sel')
        tbl = pkg.table('selection_data', pkey='_rowidx',
                        name_short='selection_data',
                        name_long='Selection Data')
        tbl.column('_rowidx', 'L')
        for col_name in meta['allColumns']:
            sqlite_col = '_pkey' if col_name == 'pkey' else col_name
            col_attrs = meta['colAttrs'].get(col_name, {})
            dtype = col_attrs.get('dataType', 'T')
            tbl.column(sqlite_col, dtype)
        db.startup()
        return db

    def _reset_sqlite(self, folder, meta):
        """Delete any existing SQLite file and create a fresh empty database.

        Args:
            folder: Folder containing (or that will contain) ``selection.sqlite``.
            meta: Metadata dict with column definitions.

        Returns:
            A ``GnrSqlDb`` instance with the physical table already created.
        """
        db_path = self._db_path(folder)
        if os.path.exists(db_path):
            os.remove(db_path)
        db = self._sqlite_db(folder, meta)
        db.checkDb(applyChanges=True)
        return db

    def _populate_sqlite(self, db, selection):
        """Insert all rows from a selection into the SQLite database.

        Each row is stored with an additional ``_rowidx`` field preserving
        the original row order.

        Args:
            db: An open ``GnrSqlDb`` instance (from ``_reset_sqlite``).
            selection: The ``SqlSelection`` whose data to persist.
        """
        tbl = db.table('sel.selection_data')
        for i, row in enumerate(selection.data):
            record = dict(row)
            if 'pkey' in record:
                record['_pkey'] = record.pop('pkey')
            record['_rowidx'] = i
            tbl.insert(record)
        db.commit()
        db.closeConnection()

    def freezeSelection(self, selection, name, **kwargs):
        """Persist a selection to a new SQLite database.

        Always recreates the database from scratch: saves metadata,
        drops any existing SQLite file, creates the schema and inserts
        all rows.

        Args:
            selection: The ``SqlSelection`` to freeze.
            name: Logical name used to build the folder path.
            **kwargs: Accepted for interface compatibility (unused).

        Returns:
            The folder path of the frozen selection.
        """
        folder = self.selection_folder(name)
        self._save_meta(folder, selection)
        meta = self._load_meta(folder)
        db = self._reset_sqlite(folder, meta)
        self._populate_sqlite(db, selection)
        return folder

    def freezeSelectionUpdate(self, selection):
        """Re-persist an already-frozen selection after in-memory changes.

        Completely rebuilds the SQLite database with the current
        selection data.  Does nothing if the selection has no ``freezepath``.

        Args:
            selection: The ``SqlSelection`` to update on disk.
        """
        if not selection.freezepath:
            return
        folder = os.path.dirname(selection.freezepath)
        if not os.path.isdir(folder):
            return
        self._save_meta(folder, selection)
        meta = self._load_meta(folder)
        db = self._reset_sqlite(folder, meta)
        self._populate_sqlite(db, selection)

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        """Restore a previously frozen selection from SQLite.

        Reads the metadata, fetches all rows ordered by ``_rowidx``,
        and reconstructs a ``SqlSelection`` bound to the **original** table.
        The returned selection is identical to what the pickle backend
        would produce: same dbtable, same index, same colAttrs.

        Args:
            dbtable: Expected table (string or table object).
            name: Logical name matching the one used during freeze.
            page_id: Optional page_id override (for cross-page access).

        Returns:
            The restored ``SqlSelection``, or ``None`` if the folder
            or database file does not exist.

        Raises:
            AssertionError: If *name* is empty or the restored selection
                belongs to a different table than *dbtable*.
        """
        assert name, 'name is mandatory'
        if isinstance(dbtable, str):
            dbtable = self.proxy.db.table(dbtable)
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        if not os.path.isdir(folder):
            return None
        meta_path = self._meta_path(folder)
        if not os.path.exists(meta_path):
            return None
        meta = self._load_meta(folder)
        db_path = self._db_path(folder)
        if not os.path.exists(db_path):
            return None
        db = self._sqlite_db(folder, meta)
        sel_tbl = db.table('sel.selection_data')
        sqlite_columns = ['$_pkey' if c == 'pkey' else '$%s' % c
                          for c in meta['allColumns']]
        columns = ','.join(sqlite_columns)
        rows = sel_tbl.query(
            columns=columns, order_by='$_rowidx',
            addPkeyColumn=False
        ).fetch()
        db.closeConnection()
        original_dbtable = dbtable or self.proxy.db.table(meta['tablename'])
        all_columns = meta['allColumns']
        index = {col: i for i, col in enumerate(all_columns)}
        data = []
        for row in rows:
            values = [row['_pkey'] if col == 'pkey' else row[col]
                      for col in all_columns]
            data.append(GnrNamedList(index, values))
        selection = SqlSelection(original_dbtable, data,
                                 index=index,
                                 colAttrs=meta['colAttrs'],
                                 querypars=meta.get('querypars'),
                                 sortedBy=meta.get('sortedBy'))
        selection.freezepath = os.path.join(folder, 'selection')
        if meta.get('key'):
            selection.setKey(meta['key'])
        if dbtable:
            assert original_dbtable == selection.dbtable, \
                'unfrozen selection does not belong to the given table'
        return selection

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        """Return the list of pkeys from a frozen selection.

        Opens the SQLite database and queries only the ``pkey``
        column, avoiding full data deserialization.

        Args:
            dbtable: Expected table (string or table object).
            name: Logical name matching the one used during freeze.
            page_id: Optional page_id override.

        Returns:
            A list of primary key values, or an empty list if not found.
        """
        assert name, 'name is mandatory'
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        if not os.path.isdir(folder):
            return []
        meta_path = self._meta_path(folder)
        if not os.path.exists(meta_path):
            return []
        meta = self._load_meta(folder)
        db_path = self._db_path(folder)
        if not os.path.exists(db_path):
            return []
        db = self._sqlite_db(folder, meta)
        tbl = db.table('sel.selection_data')
        rows = tbl.query(columns='$_pkey').fetch()
        db.closeConnection()
        return [r['_pkey'] for r in rows]


class GnrFreezedSelections(GnrBaseProxy):
    """Page proxy managing the lifecycle of frozen selections.

    Acts as the public API called by the page (``page.freezeSelection``,
    ``page.unfreezeSelection``, etc.) and by ``apphandler.getSelection``.

    On initialization selects the storage backend:

    - If ``page.use_freeze_sqlite`` is set, uses that value directly
      (useful for testing without touching preferences).
    - Otherwise reads the ``freeze_on_sqlite`` preference from the
      ``sys`` package (default: ``False``).
    """

    def init(self, **kwargs):
        """Initialize the proxy and select the storage backend.

        Called automatically by the proxy framework after the page is set up.
        """
        use_sqlite = getattr(self.page, 'use_freeze_sqlite', None)
        if use_sqlite is None:
            use_sqlite = self.application.getPreference(
                'freeze_on_sqlite', pkg='sys') or False
        if use_sqlite:
            self._backend = GnrFreezedSelectionsSqlite(self)
        else:
            self._backend = GnrFreezedSelectionsPickle(self)

    def freezeSelection(self, selection, name, **kwargs):
        """Persist a selection to disk. Delegates to the active backend."""
        return self._backend.freezeSelection(selection, name, **kwargs)

    def freezeSelectionUpdate(self, selection):
        """Re-persist a selection after in-memory changes. Delegates to the active backend."""
        self._backend.freezeSelectionUpdate(selection)

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        """Restore a frozen selection from disk. Delegates to the active backend."""
        return self._backend.unfreezeSelection(
            dbtable=dbtable, name=name, page_id=page_id)

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        """Return pkeys from a frozen selection. Delegates to the active backend."""
        return self._backend.freezedPkeys(
            dbtable=dbtable, name=name, page_id=page_id)

    @public_method
    def getUserSelection(self, selectionName=None, selectedRowidx=None,
                         filterCb=None, columns=None, sortBy=None,
                         condition=None, table=None, condition_args=None,
                         limit=None):
        """Return a frozen selection optionally filtered, sorted or re-queried.

        This is the main RPC entry point used by the client to retrieve
        data from a previously frozen selection.

        Args:
            selectionName: Name of the frozen selection (mandatory).
            selectedRowidx: Set or comma-separated string of row indices to keep.
            filterCb: Name of a public page method to use as filter callback.
            columns: If ``'pkey'`` returns a pkey list; if set, re-queries the
                database with those columns using the frozen pkeys as filter.
            sortBy: Column name to sort the result by.
            condition: Additional SQL condition appended to the re-query WHERE.
            table: Table name or object (overrides the selection's own table).
            condition_args: Dict of extra arguments for the condition.
            limit: Row limit; if different from the original query's limit,
                re-executes the query with the new limit.

        Returns:
            A ``SqlSelection`` (when *columns* is not set), a list of pkeys
            (when ``columns='pkey'``), or a new ``SqlSelection`` with the
            requested columns.
        """
        assert selectionName, 'selectionName is mandatory'
        page_id = self.sourcepage_id or self.page_id
        if isinstance(table, str):
            table = self.db.table(table)
        selection = self.unfreezeSelection(
            dbtable=table, name=selectionName, page_id=page_id)
        table = table or selection.dbtable
        if not columns and limit is not None:
            qpars = dict(selection.querypars)
            selection_limit = qpars.get('limit')
            if selection_limit != limit:
                qpars['limit'] = limit
                selection = table.query(**qpars).selection(
                    _aggregateRows=True)
        if filterCb:
            filterCb = self.getPublicMethod('rpc', filterCb)
            selection.filter(filterCb)
        elif selectedRowidx:
            if isinstance(selectedRowidx, str):
                selectedRowidx = [int(x) for x in selectedRowidx.split(',')]
                selectedRowidx = set(selectedRowidx)
            selection.filter(lambda r: r['rowidx'] in selectedRowidx)
        if sortBy:
            selection.sort(sortBy)
        if not columns:
            return selection
        if columns == 'pkey':
            return selection.output('pkeylist')
        condition_args = condition_args or {}
        pkeys = selection.output('pkeylist')
        where = 't0.%s in :pkeys' % table.pkey
        if condition:
            where = '%s AND %s' % (where, condition)
        selection = table.query(columns=columns, where=where,
                                pkeys=pkeys, addPkeyColumn=False,
                                excludeLogicalDeleted=False,
                                ignorePartition=True, subtable='*',
                                excludeDraft=False, limit=limit,
                                **condition_args).selection(
                                    _aggregateRows=True)
        if sortBy:
            selection.sort(sortBy)
        return selection

    @public_method
    def freezedSelectionPkeys(self, table=None, selectionName=None,
                              caption_field=None):
        """Return pkeys (and optionally captions) from a frozen selection.

        Args:
            table: Table name or object.
            selectionName: Name of the frozen selection.
            caption_field: If set, returns dicts with ``pkey`` and ``caption`` keys.

        Returns:
            A list of pkey values, or a list of dicts if *caption_field* is set.
        """
        selection = self.unfreezeSelection(
            dbtable=table, name=selectionName)
        l = selection.output('dictlist')
        return [dict(pkey=r['pkey'], caption=r['caption_field'])
                if caption_field else r['pkey'] for r in l]

    @public_method
    def sumOnFreezedSelection(self, selectionName=None, where=None,
                              table=None, sum_column=None, **kwargs):
        """Return the sum of a column over a frozen selection.

        Args:
            selectionName: Name of the frozen selection.
            where: Unused (kept for interface compatibility).
            table: Table name or object.
            sum_column: Column name to sum.

        Returns:
            The numeric sum, or ``0`` if the selection is not found.
        """
        selection = self.unfreezeSelection(
            dbtable=table, name=selectionName)
        if selection is None:
            return 0
        return selection.sum(sum_column)

    @public_method
    def checkFreezedSelection(self, changelist=None, selectionName=None,
                              where=None, table=None, **kwargs):
        """Check if a frozen selection is affected by database changes.

        Examines a list of change events (insert/update/delete) and
        determines whether any of them would alter the frozen selection's
        content.

        Args:
            changelist: List of dicts with ``dbevent`` ('I'/'U'/'D') and ``pkey``.
            selectionName: Name of the frozen selection.
            where: Optional WHERE clause (string or Bag) to narrow the check.
            table: Table name or object.
            **kwargs: Extra query parameters.

        Returns:
            ``True`` if the selection is affected by the changes, ``False`` otherwise.
        """
        selection = self.unfreezeSelection(
            dbtable=table, name=selectionName)
        if selection is None:
            return False
        eventdict = {}
        for change in changelist:
            eventdict.setdefault(change['dbevent'], []).append(change['pkey'])
        deleted = eventdict.get('D', [])
        if deleted:
            if bool([r for r in selection.data if r['pkey'] in deleted]):
                return True
        updated = eventdict.get('U', [])
        if updated:
            if bool([r for r in selection.data if r['pkey'] in updated]):
                return True
        inserted = eventdict.get('I', [])
        kwargs.pop('where_attr', None)
        tblobj = self.db.table(table)
        wherelist = ['( $%s IN :_pkeys )' % tblobj.pkey]
        if isinstance(where, Bag):
            where, kwargs = self.page.app._decodeWhereBag(
                tblobj, where, kwargs)
        if where:
            wherelist.append(' ( %s ) ' % where)
        condition = kwargs.pop('condition', None)
        if condition:
            wherelist.append(condition)
        where = ' AND '.join(wherelist)
        kwargs.pop('columns', None)
        kwargs['limit'] = 1
        if bool(tblobj.query(where=where, _pkeys=inserted + updated,
                             **kwargs).fetch()):
            return True
        return False
