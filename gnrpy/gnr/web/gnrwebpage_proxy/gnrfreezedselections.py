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

Three storage backends are available:

- **Pickle** (default): serializes the ``SqlSelection`` object and its data
  into separate ``.pik`` files.
- **SQLite**: stores each selection as a lightweight SQLite database
  alongside a ``selection_meta.json`` metadata file.
- **PostgreSQL**: stores each selection as a PostgreSQL UNLOGGED table
  in schema ``_qc``, with metadata in ``unlogged_meta.json``.

The active backend is selected through the ``freeze_backend`` preference
in the ``sys`` package (values: ``pickle``, ``sqlite``, ``postgres``),
or overridden per-page via the ``use_freeze_backend`` attribute.

Architecture
------------
``GnrFreezedSelections`` is a page proxy (``GnrBaseProxy``) that delegates
all storage operations to a backend object following the Strategy pattern::

    GnrFreezedSelections  (proxy, public API)
        |
        +-- GnrFreezedSelectionsPickle    (backend)
        +-- GnrFreezedSelectionsSqlite    (backend)
        +-- GnrFreezedSelectionsUnlogged  (backend, PostgreSQL)

All backends inherit from ``GnrFreezedSelectionsBackend`` and implement
the same methods: ``freezeSelection``, ``freezeSelectionUpdate``,
``unfreezeSelection``, ``freezedPkeys``, ``getFromFreezedSelection``.
"""

import datetime
import decimal
import hashlib
import json
import os
import pickle
import shutil
import sqlite3
import tempfile
import threading

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrlist import GnrNamedList
from gnr.sql.gnrsqldata import SqlSelection
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy


class _MetaEncoder(json.JSONEncoder):
    """JSON encoder for selection metadata that handles date/datetime/Decimal."""

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, datetime.date):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)


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

    def getFromFreezedSelection(self, dbtable=None, name=None,
                                row_start=0, row_count=0,
                                order_by=None, sum_columns=None,
                                page_id=None,
                                searchOn_seed=None, searchOn_field=None,
                                searchOn_columns=None):
        selection = self.unfreezeSelection(
            dbtable=dbtable, name=name, page_id=page_id)
        if selection is None:
            return None
        totalrows = len(selection)
        if order_by:
            selection.sort(order_by)
        result = dict(totalrows=totalrows, selection=selection)
        if sum_columns:
            sum_values = selection.sum(sum_columns)
            result['sum_columns'] = dict(zip(sum_columns, sum_values)) if sum_values else {}
        return result


class GnrFreezedSelectionsSqlite(GnrFreezedSelectionsBackend):
    """SQLite-based backend.

    Each frozen selection is stored as a ``selection_meta.json`` metadata file
    and a ``selection.sqlite`` database inside a dedicated folder.

    The SQLite database contains a single table ``selection_data`` with
    one column per selection field plus ``_rowidx`` as primary key.
    Column types are derived from ``colAttrs['dataType']``.

    When the client requests a different sort order, a materialised sort
    index table is created on first access and reused for subsequent
    page requests with the same order.
    """

    _folder_locks = {}
    _locks_lock = threading.Lock()

    def _get_lock(self, folder):
        """Return a per-folder threading.Lock, creating it if needed."""
        with self._locks_lock:
            if folder not in self._folder_locks:
                self._folder_locks[folder] = threading.Lock()
            return self._folder_locks[folder]

    def _meta_path(self, folder):
        """Return the path to ``selection_meta.json`` inside the given folder."""
        return os.path.join(folder, 'selection_meta.json')

    def _db_path(self, folder):
        """Return the path to ``selection.sqlite`` inside the given folder."""
        return os.path.join(folder, 'selection.sqlite')

    def _build_meta(self, selection):
        """Build the metadata dict from a selection (without I/O)."""
        return dict(
            tablename=selection.tablename,
            querypars=selection.querypars,
            colAttrs={k: dict(v) for k, v in selection.colAttrs.items()},
            allColumns=selection.allColumns,
            sortedBy=selection.sortedBy,
            key=selection.key,
            totalrows=len(selection.data)
        )

    def _save_meta(self, folder, meta):
        """Atomically write metadata dict to ``selection_meta.json``.

        Writes to a temporary file first, then uses ``os.replace``
        for an atomic swap.

        Args:
            folder: Target folder path.
            meta: Metadata dict to serialize.
        """
        meta_path = self._meta_path(folder)
        fd, tmp_path = tempfile.mkstemp(dir=folder, suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(meta, f, cls=_MetaEncoder)
            os.replace(tmp_path, meta_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _load_meta(self, folder):
        """Deserialize selection metadata from ``selection_meta.json``.

        Args:
            folder: Folder containing the metadata file.

        Returns:
            A dict with keys: ``tablename``, ``querypars``, ``colAttrs``,
            ``allColumns``, ``sortedBy``, ``key``.
        """
        with open(self._meta_path(folder)) as f:
            return json.load(f)

    def _sqlite_col_name(self, col_name):
        """Return the SQLite column name for a selection column.

        Maps ``'pkey'`` to ``'_pkey'`` to avoid clashing with SQLite
        internals; all other names pass through unchanged.
        """
        return '_pkey' if col_name == 'pkey' else col_name

    def _sqlite_col_type(self, dtype):
        """Map a Genropy dtype to a SQLite column type string."""
        if dtype in ('I', 'L'):
            return 'INTEGER'
        if dtype in ('N', 'R'):
            return 'REAL'
        return 'TEXT'

    @staticmethod
    def _make_converter(dtype):
        """Return a function that converts a SQLite value back to the original Python type."""
        if dtype == 'B':
            return lambda v: bool(v) if v is not None else None
        if dtype == 'N':
            return lambda v: decimal.Decimal(str(v)) if v is not None else None
        if dtype == 'D':
            return lambda v: (datetime.datetime.fromisoformat(v).date()
                              if v is not None else None)
        if dtype in ('DH', 'DHZ'):
            return lambda v: (datetime.datetime.fromisoformat(v)
                              if v is not None else None)
        return None

    def _build_converters(self, all_columns, col_attrs):
        """Build a list of converter functions (one per column) from colAttrs.

        Columns that need no conversion get None.
        Returns None if no column needs conversion (fast path).
        """
        converters = []
        any_needed = False
        for col in all_columns:
            attrs = col_attrs.get(col, {})
            dtype = attrs.get('dataType', 'T')
            conv = self._make_converter(dtype)
            converters.append(conv)
            if conv is not None:
                any_needed = True
        return converters if any_needed else None

    def _restore_rows(self, rows, converters):
        """Apply type converters to raw SQLite tuples, returning lists."""
        if converters is None:
            return [list(row) for row in rows]
        result = []
        for row in rows:
            values = list(row)
            for i, conv in enumerate(converters):
                if conv is not None:
                    values[i] = conv(values[i])
            result.append(values)
        return result

    def _parse_order_by(self, order_by):
        """Parse a Genropy order_by string into (sqlite_col, direction) pairs.

        Accepts formats like ``'col_name:a'``, ``'col_name:d'``,
        ``'col_name'`` (defaults to ASC), or comma-separated combinations.

        Returns:
            A list of ``(sqlite_col_name, 'ASC'|'DESC')`` tuples.
        """
        result = []
        for part in order_by.split(','):
            part = part.strip()
            if ':' in part:
                col, direction = part.rsplit(':', 1)
                direction = 'DESC' if direction.lower().startswith('d') else 'ASC'
            else:
                col = part
                direction = 'ASC'
            result.append((self._sqlite_col_name(col), direction))
        return result

    def _sort_table_name(self, order_by):
        """Derive a deterministic table name from an order_by string.

        Example: ``'_product_id_description:a'`` → ``'sort___product_id_description_a'``
        """
        safe = order_by.replace(',', '_').replace(':', '_').replace(' ', '')
        return 'sort_%s' % safe

    def _ensure_sort_table(self, conn, order_by):
        """Create the sort index table for the given order_by if it doesn't exist.

        The table has two INTEGER columns: ``_sortidx`` (PRIMARY KEY) and
        ``_rowidx`` (foreign key into ``selection_data``).  It is populated
        using ``ROW_NUMBER() OVER (ORDER BY ...)`` so that paginating by
        ``_sortidx`` returns rows in the desired order.

        Returns:
            The table name (to be used in subsequent queries).
        """
        table_name = self._sort_table_name(order_by)
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)).fetchone()
        if exists:
            return table_name
        parsed = self._parse_order_by(order_by)
        order_clause = ', '.join('%s %s' % (col, d) for col, d in parsed)
        conn.execute(
            'CREATE TABLE %s AS '
            'SELECT (ROW_NUMBER() OVER (ORDER BY %s)) - 1 AS _sortidx, '
            '_rowidx FROM selection_data' % (table_name, order_clause))
        conn.execute(
            'CREATE UNIQUE INDEX idx_%s ON %s (_sortidx)' % (
                table_name, table_name))
        conn.commit()
        return table_name

    def _prepare_rows(self, all_columns, data):
        """Convert selection data rows to flat lists for SQLite insert.

        Ensures Python types are stored in a format that ``_restore_rows``
        can reliably convert back:
        - ``Decimal`` → ``float`` (stored as REAL, restored to Decimal)
        - ``bool`` → ``int`` (stored as INTEGER, restored to bool)
        - ``date``/``datetime`` → ``str`` via isoformat (stored as TEXT)
        """
        rows = []
        for i, row in enumerate(data):
            values = [i]
            for col in all_columns:
                v = row[col]
                if isinstance(v, bool):
                    v = int(v)
                elif isinstance(v, decimal.Decimal):
                    v = float(v)
                elif isinstance(v, datetime.datetime):
                    v = v.isoformat()
                elif isinstance(v, datetime.date):
                    v = v.isoformat()
                values.append(v)
            rows.append(values)
        return rows

    def _create_and_populate(self, folder, meta, selection):
        """Create a fresh SQLite database and bulk-insert all rows.

        Uses ``sqlite3`` directly with ``executemany`` for maximum speed.
        Writes to a temporary file first and then atomically replaces
        the target path via ``os.replace`` to avoid race conditions with
        concurrent readers (scroll, sort).

        Args:
            folder: Target folder path.
            meta: Metadata dict with column definitions.
            selection: The ``SqlSelection`` whose data to persist.
        """
        db_path = self._db_path(folder)
        all_columns = meta['allColumns']
        sqlite_cols = [self._sqlite_col_name(c) for c in all_columns]
        col_defs = ['_rowidx INTEGER PRIMARY KEY']
        for col_name in all_columns:
            sqlite_col = self._sqlite_col_name(col_name)
            col_attrs = meta['colAttrs'].get(col_name, {})
            dtype = col_attrs.get('dataType', 'T')
            col_defs.append('%s %s' % (sqlite_col, self._sqlite_col_type(dtype)))
        create_sql = 'CREATE TABLE selection_data (%s)' % ', '.join(col_defs)
        insert_sql = 'INSERT INTO selection_data (_rowidx, %s) VALUES (%s)' % (
            ', '.join(sqlite_cols),
            ', '.join(['?'] * (len(sqlite_cols) + 1)))
        rows = self._prepare_rows(all_columns, selection.data)
        fd, tmp_path = tempfile.mkstemp(dir=folder, suffix='.sqlite.tmp')
        os.close(fd)
        try:
            conn = sqlite3.connect(tmp_path)
            conn.execute(create_sql)
            conn.executemany(insert_sql, rows)
            conn.commit()
            conn.close()
            os.replace(tmp_path, db_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def freezeSelection(self, selection, name, **kwargs):
        """Persist a selection to a new SQLite database.

        Always recreates the database from scratch: saves metadata,
        drops any existing SQLite file, creates the schema and inserts
        all rows.  Protected by a per-folder lock.

        Args:
            selection: The ``SqlSelection`` to freeze.
            name: Logical name used to build the folder path.
            **kwargs: Accepted for interface compatibility (unused).

        Returns:
            The folder path of the frozen selection.
        """
        folder = self.selection_folder(name)
        meta = self._build_meta(selection)
        with self._get_lock(folder):
            self._save_meta(folder, meta)
            self._create_and_populate(folder, meta, selection)
        return folder

    def freezeSelectionUpdate(self, selection):
        """Re-persist an already-frozen selection after in-memory changes.

        Completely rebuilds the SQLite database with the current
        selection data.  Does nothing if the selection has no ``freezepath``.
        Protected by a per-folder lock.

        Args:
            selection: The ``SqlSelection`` to update on disk.
        """
        if not selection.freezepath:
            return
        folder = os.path.dirname(selection.freezepath)
        if not os.path.isdir(folder):
            return
        meta = self._build_meta(selection)
        with self._get_lock(folder):
            self._save_meta(folder, meta)
            self._create_and_populate(folder, meta, selection)

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        """Restore a previously frozen selection from SQLite.

        Uses ``sqlite3`` directly for maximum speed.  Reads the metadata,
        fetches all rows ordered by ``_rowidx``, and reconstructs a
        ``SqlSelection`` bound to the **original** table.
        Protected by a per-folder lock.

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
        with self._get_lock(folder):
            meta = self._load_meta(folder)
            db_path = self._db_path(folder)
            if not os.path.exists(db_path):
                return None
            all_columns = meta['allColumns']
            sqlite_cols = [self._sqlite_col_name(c) for c in all_columns]
            select_sql = 'SELECT %s FROM selection_data ORDER BY _rowidx' % (
                ', '.join(sqlite_cols))
            conn = sqlite3.connect(db_path)
            rows = conn.execute(select_sql).fetchall()
            conn.close()
        original_dbtable = dbtable or self.proxy.db.table(meta['tablename'])
        col_attrs = meta['colAttrs']
        converters = self._build_converters(all_columns, col_attrs)
        index = {col: i for i, col in enumerate(all_columns)}
        data = [GnrNamedList(index, r)
                for r in self._restore_rows(rows, converters)]
        sortedBy = meta.get('sortedBy')
        if isinstance(sortedBy, list):
            sortedBy = ','.join(sortedBy)
        selection = SqlSelection(original_dbtable, data,
                                 index=index,
                                 colAttrs=col_attrs,
                                 querypars=meta.get('querypars'),
                                 sortedBy=sortedBy)
        selection.freezepath = os.path.join(folder, 'selection')
        if meta.get('key'):
            selection.setKey(meta['key'])
        if dbtable:
            assert original_dbtable == selection.dbtable, \
                'unfrozen selection does not belong to the given table'
        return selection

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        """Return the list of pkeys from a frozen selection.

        Uses ``sqlite3`` directly, querying only the ``_pkey`` column.
        Protected by a per-folder lock.

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
        db_path = self._db_path(folder)
        if not os.path.exists(db_path):
            return []
        with self._get_lock(folder):
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                'SELECT _pkey FROM selection_data').fetchall()
            conn.close()
        return [r[0] for r in rows]

    def _order_by_is_valid(self, order_by, all_columns):
        """Check that all columns in order_by exist in the SQLite schema."""
        sqlite_cols = {self._sqlite_col_name(c) for c in all_columns}
        for col, _ in self._parse_order_by(order_by):
            if col not in sqlite_cols:
                return False
        return True

    def _needs_sort_table(self, order_by, meta):
        """Check if order_by differs from the original sortedBy."""
        if not order_by:
            return False
        original = meta.get('sortedBy', '')
        if isinstance(original, list):
            original = ','.join(original)
        if order_by == original:
            return False
        return self._order_by_is_valid(order_by, meta['allColumns'])

    def _ensure_search_table(self, conn, seed, col_attrs, all_columns,
                             order_by=None, searchOn_columns=None):
        """Create (or reuse) a search index table for the given seed.

        Finds all TEXT-like columns (dtype in T, A or missing) and builds a
        WHERE clause with ``col LIKE '%seed%'`` ORed together.  The matching
        rows are stored in ``_search_idx`` with a sequential ``_searchidx``
        used for pagination.

        If ``searchOn_columns`` is provided (comma-separated string of
        visible column names), only those columns are searched.  Otherwise
        all TEXT-like columns are searched.

        If an ``order_by`` is provided the search results are sorted
        accordingly; otherwise the original ``_rowidx`` order is preserved.

        Returns:
            ``(search_table_name, filtered_totalrows)``
        """
        search_table = '_search_idx'
        conn.execute('DROP TABLE IF EXISTS %s' % search_table)
        visible_set = None
        if searchOn_columns:
            visible_set = set(searchOn_columns.split(','))
        text_cols = []
        for col in all_columns:
            if visible_set and col not in visible_set:
                continue
            attrs = col_attrs.get(col, {})
            dtype = attrs.get('dataType', 'T')
            if dtype in ('T', 'A', 'C'):
                text_cols.append(self._sqlite_col_name(col))
        if not text_cols:
            return None, 0
        concat_expr = " || ' ' || ".join(
            "COALESCE(%s, '')" % c for c in text_cols)
        tokens = seed.split()
        like_clauses = ' AND '.join(
            "%s LIKE '%%%s%%'" % (concat_expr, t.replace("'", "''"))
            for t in tokens)
        if order_by and self._order_by_is_valid(order_by, all_columns):
            parsed = self._parse_order_by(order_by)
            order_clause = ', '.join('%s %s' % (col, d) for col, d in parsed)
        else:
            order_clause = '_rowidx'
        conn.execute(
            'CREATE TABLE %s AS '
            'SELECT (ROW_NUMBER() OVER (ORDER BY %s)) - 1 AS _searchidx, '
            '_rowidx FROM selection_data WHERE %s'
            % (search_table, order_clause, like_clauses))
        conn.execute(
            'CREATE UNIQUE INDEX idx_%s ON %s (_searchidx)'
            % (search_table, search_table))
        conn.commit()
        count = conn.execute(
            'SELECT COUNT(*) FROM %s' % search_table).fetchone()[0]
        return search_table, count

    def getFromFreezedSelection(self, dbtable=None, name=None,
                                row_start=0, row_count=0,
                                order_by=None, sum_columns=None,
                                page_id=None,
                                searchOn_seed=None, searchOn_field=None,
                                searchOn_columns=None):
        """Return a page of rows from a frozen SQLite selection.

        Serves paginated data directly from SQLite using LIMIT/OFFSET-style
        slicing on ``_rowidx`` (original order) or on a materialised sort
        index table (when a different ``order_by`` is requested).

        When ``searchOn_seed`` is provided, a ``_search_idx`` table is created
        filtering rows where any TEXT column contains the seed.  Pagination
        and sums then operate on the filtered subset.

        Args:
            dbtable: Expected table (string or table object).
            name: Logical selection name.
            row_start: 0-based index of the first row to return.
            row_count: Number of rows to return (0 = all).
            order_by: Genropy sort string (e.g. ``'col:a'``).
            sum_columns: List of column names to SUM over the full dataset.
            page_id: Optional page_id override.
            searchOn_seed: Text to search for (LIKE match on TEXT columns).
            searchOn_field: Reserved for future per-field search.

        Returns:
            A dict with ``totalrows``, ``selection`` (a ``SqlSelection``
            containing only the requested page) and optionally
            ``sum_columns``, or ``None`` if the frozen selection does not
            exist.
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
        with self._get_lock(folder):
            meta = self._load_meta(folder)
            db_path = self._db_path(folder)
            if not os.path.exists(db_path):
                return None
            all_columns = meta['allColumns']
            sqlite_cols = [self._sqlite_col_name(c) for c in all_columns]
            col_attrs = meta['colAttrs']
            totalrows = meta.get('totalrows', 0)
            conn = sqlite3.connect(db_path)
            use_search = bool(searchOn_seed)
            use_sort_table = self._needs_sort_table(order_by, meta)
            if use_search:
                search_table, totalrows = self._ensure_search_table(
                    conn, searchOn_seed, col_attrs, all_columns,
                    order_by=order_by,
                    searchOn_columns=searchOn_columns)
                if search_table is None:
                    conn.close()
                    return None
            elif use_sort_table:
                self._ensure_sort_table(conn, order_by)
            data_cols = ', '.join('d.%s' % c for c in sqlite_cols)
            if use_search:
                if row_count:
                    select_sql = (
                        'SELECT %s FROM selection_data d '
                        'JOIN _search_idx x ON d._rowidx = x._rowidx '
                        'WHERE x._searchidx >= %d AND x._searchidx < %d '
                        'ORDER BY x._searchidx'
                    ) % (data_cols, row_start, row_start + row_count)
                else:
                    select_sql = (
                        'SELECT %s FROM selection_data d '
                        'JOIN _search_idx x ON d._rowidx = x._rowidx '
                        'ORDER BY x._searchidx'
                    ) % (data_cols,)
            elif use_sort_table:
                sort_table = self._sort_table_name(order_by)
                if row_count:
                    select_sql = (
                        'SELECT %s FROM selection_data d '
                        'JOIN %s s ON d._rowidx = s._rowidx '
                        'WHERE s._sortidx >= %d AND s._sortidx < %d '
                        'ORDER BY s._sortidx'
                    ) % (data_cols, sort_table, row_start,
                         row_start + row_count)
                else:
                    select_sql = (
                        'SELECT %s FROM selection_data d '
                        'JOIN %s s ON d._rowidx = s._rowidx '
                        'ORDER BY s._sortidx'
                    ) % (data_cols, sort_table)
            else:
                if row_count:
                    select_sql = (
                        'SELECT %s FROM selection_data d '
                        'WHERE d._rowidx >= %d AND d._rowidx < %d '
                        'ORDER BY d._rowidx'
                    ) % (data_cols, row_start, row_start + row_count)
                else:
                    select_sql = (
                        'SELECT %s FROM selection_data d ORDER BY d._rowidx'
                    ) % (data_cols,)
            rows = conn.execute(select_sql).fetchall()
            result = dict(totalrows=totalrows)
            if sum_columns:
                sum_exprs = ', '.join(
                    'SUM(%s)' % self._sqlite_col_name(c)
                    for c in sum_columns)
                if use_search:
                    sum_sql = (
                        'SELECT %s FROM selection_data d '
                        'JOIN _search_idx x ON d._rowidx = x._rowidx'
                    ) % sum_exprs
                else:
                    sum_sql = 'SELECT %s FROM selection_data' % sum_exprs
                sum_row = conn.execute(sum_sql).fetchone()
                result['sum_columns'] = dict(zip(sum_columns, sum_row))
            conn.close()
        original_dbtable = dbtable or self.proxy.db.table(meta['tablename'])
        converters = self._build_converters(all_columns, col_attrs)
        index = {col: i for i, col in enumerate(all_columns)}
        data = [GnrNamedList(index, r)
                for r in self._restore_rows(rows, converters)]
        sortedBy = order_by or meta.get('sortedBy')
        if isinstance(sortedBy, list):
            sortedBy = ','.join(sortedBy)
        selection = SqlSelection(original_dbtable, data,
                                 index=index,
                                 colAttrs=col_attrs,
                                 querypars=meta.get('querypars'),
                                 sortedBy=sortedBy)
        selection.freezepath = os.path.join(folder, 'selection')
        if meta.get('key'):
            selection.setKey(meta['key'])
        result['selection'] = selection
        return result


QC_SCHEMA = '_qc'
META_FILENAME = 'unlogged_meta.json'


def _make_pg_table_name(page_id, sel_name, max_len=63):
    """Build a PostgreSQL-safe table name from page_id and selection name."""
    raw = 'p%s_%s' % (page_id, sel_name)
    safe = ''.join(c if c.isalnum() or c == '_' else '_' for c in raw)
    if len(safe.encode('utf-8')) <= max_len:
        return safe[:max_len]
    h = hashlib.sha256(sel_name.encode('utf-8')).hexdigest()[:12]
    prefix = 'p%s_' % page_id
    safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in prefix)
    return (safe_prefix + h)[:max_len]


def _pg_col_type(dtype):
    """Map a Genropy dataType to a PostgreSQL column type."""
    return {
        'T': 'TEXT', 'A': 'TEXT', 'C': 'TEXT',
        'I': 'INTEGER', 'L': 'BIGINT',
        'N': 'NUMERIC', 'R': 'DOUBLE PRECISION',
        'B': 'BOOLEAN',
        'D': 'DATE', 'DH': 'TIMESTAMP', 'DHZ': 'TIMESTAMPTZ',
    }.get(dtype, 'TEXT')


def _pg_parse_order_by(order_by):
    """Parse a Genropy order_by string into a SQL ORDER BY clause."""
    parts = []
    for segment in order_by.split(','):
        segment = segment.strip()
        if not segment:
            continue
        if ':' in segment:
            col, direction = segment.rsplit(':', 1)
            direction = 'DESC' if direction.lower().startswith('d') else 'ASC'
        else:
            col = segment
            direction = 'ASC'
        parts.append('"%s" %s' % (col.strip(), direction))
    return ', '.join(parts)


class GnrFreezedSelectionsUnlogged(GnrFreezedSelectionsBackend):
    """PostgreSQL UNLOGGED TABLE backend for frozen selections.

    Each frozen selection is stored as a PostgreSQL UNLOGGED table in
    schema ``_qc`` with metadata in ``unlogged_meta.json`` on the filesystem.

    Fast path: ``CREATE UNLOGGED TABLE AS SELECT`` keeps data entirely
    server-side.  Slow path: ``CREATE TABLE`` + row-by-row ``INSERT``.
    """

    def __init__(self, proxy, schema=None):
        super().__init__(proxy)
        self.schema = schema or QC_SCHEMA
        self._schema_ready = False

    @property
    def db(self):
        return self.proxy.db

    def _execute(self, sql, args=None):
        self.db.execute(sql, args)

    def _fetchone(self, sql, args=None):
        return self.db.execute(sql, args, dbtable=None).fetchone()

    def _fetchall(self, sql, args=None):
        return self.db.execute(sql, args, dbtable=None).fetchall()

    def _ensure_schema(self):
        if self._schema_ready:
            return
        self._execute('CREATE SCHEMA IF NOT EXISTS %s' % self.schema)
        self.db.commit()
        self._schema_ready = True

    def _qualified(self, table_name):
        return '%s."%s"' % (self.schema, table_name)

    def _table_exists(self, table_name):
        row = self._fetchone(
            "SELECT 1 FROM pg_tables WHERE schemaname = %s AND tablename = %s",
            (self.schema, table_name))
        return row is not None

    def _drop_table(self, table_name):
        self._execute('DROP TABLE IF EXISTS %s' % self._qualified(table_name))

    def _meta_path(self, folder):
        return os.path.join(folder, META_FILENAME)

    def _save_meta(self, folder, meta):
        meta_path = self._meta_path(folder)
        fd, tmp_path = tempfile.mkstemp(dir=folder, suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(meta, f, cls=_MetaEncoder)
            os.replace(tmp_path, meta_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _load_meta(self, folder):
        meta_path = self._meta_path(folder)
        if not os.path.exists(meta_path):
            return None
        with open(meta_path) as f:
            return json.load(f)

    def _build_meta(self, table_name, selection):
        col_attrs = {k: dict(v) for k, v in selection.colAttrs.items()}
        sorted_by = selection.sortedBy
        if isinstance(sorted_by, list):
            sorted_by = ','.join(sorted_by)
        return dict(
            pg_table_name=table_name,
            tablename=selection.tablename,
            col_attrs=col_attrs,
            all_columns=selection.allColumns,
            sorted_by=sorted_by,
            querypars=selection.querypars,
            key=selection.key if hasattr(selection, 'key') else None,
            totalrows=len(selection),
        )

    def _create_via_query(self, table_name, selection):
        """Fast path: CREATE UNLOGGED TABLE AS SELECT."""
        querypars = selection.querypars
        if not querypars:
            return False
        dbtable = selection.dbtable
        if not dbtable:
            return False
        try:
            q = dbtable.query(**querypars)
            sql_text = q.sqltext
            sql_args = q.sqlargs
            if not sql_text:
                return False
            qualified = self._qualified(table_name)
            create_sql = (
                "CREATE UNLOGGED TABLE {qualified} AS "
                "SELECT (row_number() OVER ())::integer - 1 AS _rowidx, "
                "_inner_q.* FROM ({inner_query}) _inner_q"
            ).format(qualified=qualified, inner_query=sql_text)
            self._execute(create_sql, sql_args)
            return True
        except Exception:
            self._drop_table(table_name)
            return False

    def _create_via_insert(self, table_name, selection):
        """Slow path: create empty table + bulk insert from Python data."""
        all_columns = selection.allColumns
        col_attrs = selection.colAttrs
        qualified = self._qualified(table_name)
        col_defs = ['_rowidx INTEGER NOT NULL']
        for col in all_columns:
            attrs = col_attrs.get(col, {})
            dtype = attrs.get('dataType', 'T')
            col_defs.append('"%s" %s' % (col, _pg_col_type(dtype)))
        self._execute('CREATE UNLOGGED TABLE %s (%s)' % (
            qualified, ', '.join(col_defs)))
        col_names = ', '.join(['_rowidx'] + ['"%s"' % c for c in all_columns])
        placeholders = ', '.join(['%%s'] * (len(all_columns) + 1))
        insert_sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
            qualified, col_names, placeholders)
        data = selection.data
        for i, row in enumerate(data):
            values = [i]
            for col in all_columns:
                v = row[col]
                if isinstance(v, decimal.Decimal):
                    v = float(v)
                values.append(v)
            self._execute(insert_sql, values)

    def _create_rowidx_index(self, table_name):
        qualified = self._qualified(table_name)
        idx_name = 'idx_%s_rowidx' % table_name
        self._execute(
            'CREATE UNIQUE INDEX "%s" ON %s (_rowidx)' % (idx_name, qualified))

    def freezeSelection(self, selection, name, freezePkeys=False, **kwargs):
        self._ensure_schema()
        page_id = self.proxy.page_id
        table_name = _make_pg_table_name(page_id, name)
        folder = self.selection_folder(name)
        self._drop_table(table_name)
        if not self._create_via_query(table_name, selection):
            self._create_via_insert(table_name, selection)
        self._create_rowidx_index(table_name)
        meta = self._build_meta(table_name, selection)
        self._save_meta(folder, meta)
        self.db.commit()
        selection.freezepath = os.path.join(folder, 'selection')
        selection._pg_table_name = table_name
        return folder

    def freezeSelectionUpdate(self, selection):
        if not selection.freezepath:
            return
        folder = os.path.dirname(selection.freezepath)
        if not os.path.isdir(folder):
            return
        meta = self._load_meta(folder)
        if not meta:
            return
        self._ensure_schema()
        table_name = meta['pg_table_name']
        self._drop_table(table_name)
        self._create_via_insert(table_name, selection)
        self._create_rowidx_index(table_name)
        new_meta = self._build_meta(table_name, selection)
        self._save_meta(folder, new_meta)
        self.db.commit()
        selection.isChangedSelection = False
        selection.isChangedData = False
        selection.isChangedFiltered = False

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        assert name, 'name is mandatory'
        self._ensure_schema()
        if isinstance(dbtable, str):
            dbtable = self.proxy.db.table(dbtable)
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        meta = self._load_meta(folder) if os.path.isdir(folder) else None
        if not meta:
            return None
        table_name = meta['pg_table_name']
        if not self._table_exists(table_name):
            return None
        all_columns = meta['all_columns']
        col_attrs = meta['col_attrs']
        qualified = self._qualified(table_name)
        col_list = ', '.join('"%s"' % c for c in all_columns)
        rows = self._fetchall(
            'SELECT %s FROM %s ORDER BY _rowidx' % (col_list, qualified))
        original_dbtable = dbtable or self.proxy.db.table(meta['tablename'])
        index = {col: i for i, col in enumerate(all_columns)}
        data = [GnrNamedList(index, list(row)) for row in rows]
        sorted_by = meta.get('sorted_by')
        if isinstance(sorted_by, list):
            sorted_by = ','.join(sorted_by)
        selection = SqlSelection(
            original_dbtable, data,
            index=index,
            colAttrs=col_attrs,
            querypars=meta.get('querypars'),
            sortedBy=sorted_by)
        selection.freezepath = os.path.join(folder, 'selection')
        selection._pg_table_name = table_name
        if meta.get('key'):
            selection.setKey(meta['key'])
        if dbtable:
            assert original_dbtable == selection.dbtable, \
                'unfrozen selection does not belong to the given table'
        return selection

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        assert name, 'name is mandatory'
        self._ensure_schema()
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        meta = self._load_meta(folder) if os.path.isdir(folder) else None
        if not meta:
            return []
        table_name = meta['pg_table_name']
        if not self._table_exists(table_name):
            return []
        qualified = self._qualified(table_name)
        rows = self._fetchall(
            'SELECT "pkey" FROM %s ORDER BY _rowidx' % qualified)
        return [r[0] for r in rows]

    def getFromFreezedSelection(self, dbtable=None, name=None,
                                row_start=0, row_count=0,
                                order_by=None, sum_columns=None,
                                page_id=None,
                                searchOn_seed=None, searchOn_field=None,
                                searchOn_columns=None):
        assert name, 'name is mandatory'
        self._ensure_schema()
        if isinstance(dbtable, str):
            dbtable = self.proxy.db.table(dbtable)
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        meta = self._load_meta(folder) if os.path.isdir(folder) else None
        if not meta:
            return None
        table_name = meta['pg_table_name']
        if not self._table_exists(table_name):
            return None
        all_columns = meta['all_columns']
        col_attrs = meta['col_attrs']
        qualified = self._qualified(table_name)
        totalrows = meta.get('totalrows', 0)

        # WHERE (text search)
        where_clause = ''
        where_args = []
        if searchOn_seed:
            text_cols = []
            for col in all_columns:
                attrs = col_attrs.get(col, {})
                dtype = attrs.get('dataType', 'T')
                if dtype in ('T', 'A', 'C'):
                    text_cols.append("COALESCE(\"%s\"::text, '')" % col)
            if text_cols:
                concat_expr = " || ' ' || ".join(text_cols)
                tokens = searchOn_seed.split()
                clauses = []
                for token in tokens:
                    clauses.append('%s ILIKE %%s' % concat_expr)
                    where_args.append('%%%s%%' % token)
                where_clause = 'WHERE ' + ' AND '.join(clauses)
                count_row = self._fetchone(
                    'SELECT COUNT(*) FROM %s %s' % (qualified, where_clause),
                    where_args)
                totalrows = count_row[0] if count_row else 0

        # ORDER BY
        if order_by:
            order_clause = 'ORDER BY ' + _pg_parse_order_by(order_by)
        else:
            order_clause = 'ORDER BY _rowidx'

        # LIMIT / OFFSET
        limit_clause = ''
        limit_args = []
        if row_count:
            limit_clause = 'LIMIT %s OFFSET %s'
            limit_args = [row_count, row_start]
        elif row_start:
            limit_clause = 'OFFSET %s'
            limit_args = [row_start]

        # Main SELECT
        col_list = ', '.join('"%s"' % c for c in all_columns)
        select_sql = 'SELECT %s FROM %s %s %s %s' % (
            col_list, qualified, where_clause, order_clause, limit_clause)
        all_args = where_args + limit_args
        rows = self._fetchall(select_sql, all_args if all_args else None)

        result = dict(totalrows=totalrows)

        # SUMs
        if sum_columns:
            sum_exprs = ', '.join('SUM("%s")' % c for c in sum_columns)
            sum_sql = 'SELECT %s FROM %s %s' % (
                sum_exprs, qualified, where_clause)
            sum_row = self._fetchone(
                sum_sql, where_args if where_args else None)
            if sum_row:
                result['sum_columns'] = dict(zip(sum_columns, sum_row))
            else:
                result['sum_columns'] = {c: 0 for c in sum_columns}

        # Build SqlSelection for the page
        original_dbtable = dbtable or self.proxy.db.table(meta['tablename'])
        index = {col: i for i, col in enumerate(all_columns)}
        data = [GnrNamedList(index, list(row)) for row in rows]
        sorted_by = order_by or meta.get('sorted_by')
        if isinstance(sorted_by, list):
            sorted_by = ','.join(sorted_by)
        selection = SqlSelection(
            original_dbtable, data,
            index=index,
            colAttrs=col_attrs,
            querypars=meta.get('querypars'),
            sortedBy=sorted_by)
        selection.freezepath = os.path.join(folder, 'selection')
        selection._pg_table_name = table_name
        if meta.get('key'):
            selection.setKey(meta['key'])
        result['selection'] = selection
        return result

    def cleanupSelection(self, name, page_id=None):
        self._ensure_schema()
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        meta = self._load_meta(folder) if os.path.isdir(folder) else None
        if meta:
            self._drop_table(meta['pg_table_name'])
            meta_path = self._meta_path(folder)
            if os.path.exists(meta_path):
                os.remove(meta_path)
            self.db.commit()

    def cleanupPage(self, page_id=None):
        self._ensure_schema()
        page_id = page_id or self.proxy.page_id
        page_folder = self.proxy.pageLocalDocument('', page_id=page_id)
        if not os.path.isdir(page_folder):
            return
        for entry in os.listdir(page_folder):
            sel_folder = os.path.join(page_folder, entry)
            if not os.path.isdir(sel_folder):
                continue
            meta = self._load_meta(sel_folder)
            if meta:
                self._drop_table(meta['pg_table_name'])
                os.remove(self._meta_path(sel_folder))
        self.db.commit()

    def cleanupOrphans(self, live_page_ids):
        self._ensure_schema()
        live_set = set(live_page_ids)
        rows = self._fetchall(
            "SELECT tablename FROM pg_tables WHERE schemaname = %s",
            (self.schema,))
        for row in rows:
            tname = row[0]
            if not tname.startswith('p'):
                continue
            rest = tname[1:]
            sep = rest.find('_')
            if sep < 0:
                continue
            extracted_page_id = rest[:sep]
            if extracted_page_id not in live_set:
                self._drop_table(tname)
        self.db.commit()

    def cleanupAll(self):
        self._execute('DROP SCHEMA IF EXISTS %s CASCADE' % self.schema)
        self._schema_ready = False
        self._ensure_schema()


FREEZE_BACKENDS = {
    'pickle': GnrFreezedSelectionsPickle,
    'sqlite': GnrFreezedSelectionsSqlite,
    'postgres': GnrFreezedSelectionsUnlogged,
}


class GnrFreezedSelections(GnrBaseProxy):
    """Page proxy managing the lifecycle of frozen selections.

    Acts as the public API called by the page (``page.freezeSelection``,
    ``page.unfreezeSelection``, etc.) and by ``apphandler.getSelection``.

    On initialization selects the storage backend based on the
    ``freeze_backend`` preference (``pickle``, ``sqlite``, ``postgres``).
    Can be overridden per-page via ``use_freeze_backend``.
    """

    def init(self, **kwargs):
        """Initialize the proxy and select the storage backend."""
        backend_name = getattr(self.page, 'use_freeze_backend', None)
        if backend_name is None:
            backend_name = self.application.getPreference(
                'freeze_backend', pkg='sys') or 'pickle'
        backend_cls = FREEZE_BACKENDS.get(backend_name, GnrFreezedSelectionsPickle)
        self._backend = backend_cls(self)

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

    def getFromFreezedSelection(self, dbtable=None, name=None,
                                row_start=0, row_count=0,
                                order_by=None, sum_columns=None,
                                page_id=None,
                                searchOn_seed=None, searchOn_field=None,
                                searchOn_columns=None):
        """Return a page of rows from a frozen selection. Delegates to the active backend."""
        return self._backend.getFromFreezedSelection(
            dbtable=dbtable, name=name,
            row_start=row_start, row_count=row_count,
            order_by=order_by, sum_columns=sum_columns,
            page_id=page_id,
            searchOn_seed=searchOn_seed, searchOn_field=searchOn_field,
            searchOn_columns=searchOn_columns)

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
