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
  (via ``GnrSqlDb``) alongside a ``selection_meta.json`` metadata file.

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

    selection_meta.json    -- selection metadata (tablename, colAttrs, querypars, ...)
    selection.sqlite       -- SQLite database with one table: selection_data
"""

import datetime
import decimal
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
        row_start = int(row_start)
        row_count = int(row_count)
        if row_count:
            selection._data = selection._data[row_start:row_start + row_count]
        result = dict(totalrows=totalrows, selection=selection)
        if sum_columns and selection._sum_values:
            result['sum_columns'] = selection._sum_values
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
        meta = dict(
            tablename=selection.tablename,
            querypars=selection.querypars,
            colAttrs={k: dict(v) for k, v in selection.colAttrs.items()},
            allColumns=selection.allColumns,
            sortedBy=selection.sortedBy,
            key=selection.key,
            totalrows=len(selection.data)
        )
        if selection._sum_values:
            meta['_sum_values'] = selection._sum_values
        return meta

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

    def _search_state_path(self, folder):
        """Return the path to ``_search_state.json`` inside the given folder."""
        return os.path.join(folder, '_search_state.json')

    def _load_search_state(self, folder):
        """Load search state from ``_search_state.json``, or None if absent."""
        path = self._search_state_path(folder)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def _save_search_state(self, folder, state):
        """Atomically write search state to ``_search_state.json``."""
        path = self._search_state_path(folder)
        fd, tmp_path = tempfile.mkstemp(dir=folder, suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(state, f, cls=_MetaEncoder)
            os.replace(tmp_path, path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _clear_search_state(self, folder, conn):
        """Drop the search view and remove the search state file."""
        conn.execute('DROP VIEW IF EXISTS _search_view')
        conn.commit()
        path = self._search_state_path(folder)
        if os.path.exists(path):
            os.unlink(path)

    def _build_like_clause(self, seed, col_attrs, all_columns, searchOn_columns=None):
        """Build the WHERE clause for text search on TEXT-like columns.

        Returns the LIKE clause string, or None if no searchable columns exist.
        """
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
            return None
        concat_expr = " || ' ' || ".join(
            "COALESCE(%s, '')" % c for c in text_cols)
        tokens = seed.split()
        if not tokens:
            return None
        like_clauses = ' AND '.join(
            "%s LIKE '%%%s%%'" % (concat_expr, t.replace("'", "''"))
            for t in tokens)
        return like_clauses

    def _ensure_search_view(self, folder, conn, seed, col_attrs, all_columns,
                            sum_columns=None, searchOn_columns=None):
        """Create the search VIEW and compute search state (totalrows, sums).

        If a search state already exists for the same seed, reuses it.
        Otherwise drops any existing view, creates a new one, computes
        COUNT and SUMs, and saves the state to ``_search_state.json``.

        Returns:
            ``(totalrows, sum_values_dict_or_None)``
        """
        existing_state = self._load_search_state(folder)
        if existing_state and existing_state.get('seed') == seed:
            return existing_state['totalrows'], existing_state.get('sum_values')
        self._clear_search_state(folder, conn)
        like_clause = self._build_like_clause(seed, col_attrs, all_columns,
                                              searchOn_columns=searchOn_columns)
        if like_clause is None:
            return 0, None
        conn.execute(
            'CREATE VIEW _search_view AS '
            'SELECT * FROM selection_data WHERE %s' % like_clause)
        conn.commit()
        totalrows = conn.execute(
            'SELECT COUNT(*) FROM _search_view').fetchone()[0]
        sum_values = None
        if sum_columns:
            sum_exprs = ', '.join(
                'SUM(%s)' % self._sqlite_col_name(c) for c in sum_columns)
            sum_row = conn.execute(
                'SELECT %s FROM _search_view' % sum_exprs).fetchone()
            sum_values = dict(zip(sum_columns, sum_row))
        state = dict(seed=seed, totalrows=totalrows)
        if sum_values:
            state['sum_values'] = sum_values
        self._save_search_state(folder, state)
        return totalrows, sum_values

    def getFromFreezedSelection(self, dbtable=None, name=None,
                                row_start=0, row_count=0,
                                order_by=None, sum_columns=None,
                                page_id=None,
                                searchOn_seed=None, searchOn_field=None,
                                searchOn_columns=None):
        """Return a page of rows from a frozen SQLite selection.

        Uses ``ORDER BY ... LIMIT ... OFFSET`` for pagination and sorting.
        When ``searchOn_seed`` is provided, a ``_search_view`` VIEW filters
        rows where TEXT columns match the seed.  Search metadata (totalrows,
        sum_values) are cached in ``_search_state.json`` and reused across
        paginations with the same seed.

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
            searchOn_columns: Comma-separated column names to restrict search.

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
            result = dict(totalrows=totalrows)
            if searchOn_seed:
                search_totalrows, search_sums = self._ensure_search_view(
                    folder, conn, searchOn_seed, col_attrs, all_columns,
                    sum_columns=sum_columns,
                    searchOn_columns=searchOn_columns)
                result['totalrows'] = search_totalrows
                source_table = '_search_view'
                if search_sums:
                    result['sum_columns'] = search_sums
            else:
                self._clear_search_state(folder, conn)
                source_table = 'selection_data'
                if sum_columns and meta.get('_sum_values'):
                    result['sum_columns'] = meta['_sum_values']
            data_cols = ', '.join(sqlite_cols)
            if order_by and self._order_by_is_valid(order_by, all_columns):
                parsed = self._parse_order_by(order_by)
                order_clause = ', '.join(
                    '%s %s' % (col, d) for col, d in parsed)
            else:
                order_clause = '_rowidx'
            if row_count:
                select_sql = (
                    'SELECT %s FROM %s ORDER BY %s LIMIT %d OFFSET %d'
                ) % (data_cols, source_table, order_clause,
                     row_count, row_start)
            else:
                select_sql = (
                    'SELECT %s FROM %s ORDER BY %s'
                ) % (data_cols, source_table, order_clause)
            rows = conn.execute(select_sql).fetchall()
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
