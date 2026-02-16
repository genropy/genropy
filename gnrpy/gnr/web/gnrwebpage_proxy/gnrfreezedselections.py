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
        +-- GnrFreezedSelectionsPickle       (backend)
        +-- GnrFreezedSelectionsSql          (common SQL logic)
                +-- GnrFreezedSelectionsSqlite    (SQLite dialect)
                +-- GnrFreezedSelectionsUnlogged  (PostgreSQL dialect)

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
        row_start = int(row_start)
        row_count = int(row_count)
        if row_count:
            selection._data = selection._data[row_start:row_start + row_count]
        result = dict(totalrows=totalrows, selection=selection)
        if sum_columns and selection._sum_values:
            result['sum_columns'] = selection._sum_values
        return result


# ---------------------------------------------------------------------------
#  GnrFreezedSelectionsSql — common SQL logic for SQLite and PostgreSQL
# ---------------------------------------------------------------------------

class GnrFreezedSelectionsSql(GnrFreezedSelectionsBackend):
    """Common SQL logic shared by SQLite and PostgreSQL backends.

    Subclasses must override the dialect-specific methods:

    - ``_quote_col(col_name)`` — column quoting
    - ``_col_type(dtype)`` — SQL column type for a Genropy dtype
    - ``_like_operator`` — property returning ``'LIKE'`` or ``'ILIKE'``
    - ``_placeholder`` — property returning ``'?'`` or ``'%s'``
    - ``_open_connection(folder)`` — open a DB connection for the selection
    - ``_close_connection(conn)`` — close a DB connection
    - ``_execute_sql(conn, sql, args)`` — execute SQL (no result)
    - ``_fetchone_sql(conn, sql, args)`` — execute SQL, return one row
    - ``_fetchall_sql(conn, sql, args)`` — execute SQL, return all rows
    - ``_commit_sql(conn)`` — commit the connection

    Subclasses implement ``freezeSelection``, ``freezeSelectionUpdate``,
    ``unfreezeSelection``, ``freezedPkeys`` using their own storage
    mechanics.  The common ``getFromFreezedSelection`` is fully implemented
    here.
    """

    # -- Dialect hooks (must be overridden) ----------------------------------

    @property
    def _like_operator(self):
        raise NotImplementedError

    @property
    def _placeholder(self):
        raise NotImplementedError

    def _quote_col(self, col_name):
        raise NotImplementedError

    def _col_type(self, dtype):
        raise NotImplementedError

    def _open_connection(self, folder, meta):
        raise NotImplementedError

    def _close_connection(self, conn):
        raise NotImplementedError

    def _execute_sql(self, conn, sql, args=None):
        raise NotImplementedError

    def _fetchone_sql(self, conn, sql, args=None):
        raise NotImplementedError

    def _fetchall_sql(self, conn, sql, args=None):
        raise NotImplementedError

    def _commit_sql(self, conn):
        raise NotImplementedError

    def _source_table(self, meta):
        """Return the SQL source identifier for the selection data table."""
        raise NotImplementedError

    def _search_view_name(self, meta):
        """Return the SQL identifier for the search view.

        On SQLite this is just ``_search_view`` (local to the file).
        On PostgreSQL it must be schema-qualified and unique per selection.
        """
        return '_search_view'

    def _post_build_selection(self, selection, folder, meta):
        """Hook for subclasses to attach backend-specific attributes."""
        pass

    # -- Meta I/O -----------------------------------------------------------

    def _meta_path(self, folder):
        """Return the path to the metadata JSON file inside the given folder."""
        return os.path.join(folder, 'selection_meta.json')

    def _save_meta(self, folder, meta):
        """Atomically write metadata dict to the metadata JSON file."""
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
        """Deserialize selection metadata from the metadata JSON file."""
        meta_path = self._meta_path(folder)
        if not os.path.exists(meta_path):
            return None
        with open(meta_path) as f:
            return json.load(f)

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

    # -- Type converters ----------------------------------------------------

    @staticmethod
    def _make_converter(dtype):
        """Return a function that converts a DB value back to the original Python type."""
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
        """Build a list of converter functions (one per column) from colAttrs."""
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
        """Apply type converters to raw DB tuples, returning lists."""
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

    def _prepare_rows(self, all_columns, data):
        """Convert selection data rows to flat lists for SQL insert."""
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

    # -- ORDER BY parsing ---------------------------------------------------

    def _parse_order_by(self, order_by):
        """Parse a Genropy order_by string into (quoted_col, direction) pairs."""
        result = []
        for part in order_by.split(','):
            part = part.strip()
            if ':' in part:
                col, direction = part.rsplit(':', 1)
                direction = 'DESC' if direction.lower().startswith('d') else 'ASC'
            else:
                col = part
                direction = 'ASC'
            result.append((self._quote_col(col), direction))
        return result

    def _order_by_is_valid(self, order_by, all_columns):
        """Check that all columns in order_by exist in the schema."""
        valid_cols = {self._quote_col(c) for c in all_columns}
        for col, _ in self._parse_order_by(order_by):
            if col not in valid_cols:
                return False
        return True

    # -- Search state caching -----------------------------------------------

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

    def _clear_search_state(self, folder, conn, meta=None):
        """Drop the search view and remove the search state file."""
        view_name = self._search_view_name(meta)
        self._execute_sql(conn, 'DROP VIEW IF EXISTS %s' % view_name)
        self._commit_sql(conn)
        path = self._search_state_path(folder)
        if os.path.exists(path):
            os.unlink(path)

    # -- Search (LIKE / ILIKE) ----------------------------------------------

    def _build_like_clause(self, seed, col_attrs, all_columns,
                           searchOn_columns=None):
        """Build the WHERE clause for text search on TEXT-like columns.

        Values are inlined (with proper escaping) rather than parameterised
        because ``CREATE VIEW`` does not accept bind parameters.

        Returns the clause string, or ``None`` if no searchable columns
        exist or the seed yields no tokens.
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
                text_cols.append(self._quote_col(col))
        if not text_cols:
            return None
        concat_expr = " || ' ' || ".join(
            "COALESCE(%s, '')" % c for c in text_cols)
        tokens = seed.split()
        if not tokens:
            return None
        like_op = self._like_operator
        clauses = []
        for t in tokens:
            escaped = t.replace("'", "''")
            clauses.append("%s %s '%%%s%%'" % (concat_expr, like_op, escaped))
        return ' AND '.join(clauses)

    def _ensure_search_view(self, folder, conn, seed, col_attrs, all_columns,
                            source_table, meta=None, sum_columns=None,
                            searchOn_columns=None):
        """Create the search VIEW and compute search state (totalrows, sums).

        If a search state already exists for the same seed, reuses it.
        Otherwise drops any existing view, creates a new one, computes
        COUNT and SUMs, and saves the state to ``_search_state.json``.

        Returns:
            ``(totalrows, sum_values_dict_or_None)``
        """
        view_name = self._search_view_name(meta)
        existing_state = self._load_search_state(folder)
        if existing_state and existing_state.get('seed') == seed:
            return existing_state['totalrows'], existing_state.get('sum_values')
        self._clear_search_state(folder, conn, meta=meta)
        like_clause = self._build_like_clause(
            seed, col_attrs, all_columns,
            searchOn_columns=searchOn_columns)
        if like_clause is None:
            return 0, None
        create_sql = (
            'CREATE VIEW %s AS '
            'SELECT * FROM %s WHERE %s' % (view_name, source_table, like_clause))
        self._execute_sql(conn, create_sql)
        self._commit_sql(conn)
        totalrows = self._fetchone_sql(
            conn, 'SELECT COUNT(*) FROM %s' % view_name)[0]
        sum_values = None
        if sum_columns:
            sum_exprs = ', '.join(
                'SUM(%s)' % self._quote_col(c) for c in sum_columns)
            sum_row = self._fetchone_sql(
                conn, 'SELECT %s FROM %s' % (sum_exprs, view_name))
            sum_values = dict(zip(sum_columns, sum_row))
        state = dict(seed=seed, totalrows=totalrows)
        if sum_values:
            state['sum_values'] = sum_values
        self._save_search_state(folder, state)
        return totalrows, sum_values

    # -- Build SqlSelection from rows ----------------------------------------

    def _build_selection(self, rows, all_columns, col_attrs, meta,
                         dbtable, order_by, folder):
        """Reconstruct a SqlSelection from raw DB rows."""
        converters = self._build_converters(all_columns, col_attrs)
        index = {col: i for i, col in enumerate(all_columns)}
        data = [GnrNamedList(index, r)
                for r in self._restore_rows(rows, converters)]
        sortedBy = order_by or meta.get('sortedBy')
        if isinstance(sortedBy, list):
            sortedBy = ','.join(sortedBy)
        original_dbtable = dbtable or self.proxy.db.table(meta['tablename'])
        selection = SqlSelection(original_dbtable, data,
                                 index=index,
                                 colAttrs=col_attrs,
                                 querypars=meta.get('querypars'),
                                 sortedBy=sortedBy)
        selection.freezepath = os.path.join(folder, 'selection')
        if meta.get('key'):
            selection.setKey(meta['key'])
        self._post_build_selection(selection, folder, meta)
        return selection

    # -- getFromFreezedSelection (common logic) ------------------------------

    def getFromFreezedSelection(self, dbtable=None, name=None,
                                row_start=0, row_count=0,
                                order_by=None, sum_columns=None,
                                page_id=None,
                                searchOn_seed=None, searchOn_field=None,
                                searchOn_columns=None):
        """Return a page of rows from a frozen SQL selection.

        Uses ``ORDER BY ... LIMIT ... OFFSET`` for pagination and sorting.
        When ``searchOn_seed`` is provided, a ``_search_view`` VIEW filters
        rows where TEXT columns match the seed.  Search metadata (totalrows,
        sum_values) are cached in ``_search_state.json`` and reused across
        paginations with the same seed.

        This method is fully implemented in the base class; subclasses
        only need to provide dialect-specific hooks.
        """
        assert name, 'name is mandatory'
        if isinstance(dbtable, str):
            dbtable = self.proxy.db.table(dbtable)
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        if not os.path.isdir(folder):
            return None
        meta = self._load_meta(folder)
        if not meta:
            return None
        all_columns = meta['allColumns']
        col_attrs = meta['colAttrs']
        totalrows = meta.get('totalrows', 0)
        conn = self._open_connection(folder, meta)
        try:
            result = dict(totalrows=totalrows)
            source_table = self._source_table(meta)
            view_name = self._search_view_name(meta)
            if searchOn_seed:
                search_totalrows, search_sums = self._ensure_search_view(
                    folder, conn, searchOn_seed, col_attrs, all_columns,
                    source_table=source_table,
                    meta=meta,
                    sum_columns=sum_columns,
                    searchOn_columns=searchOn_columns)
                result['totalrows'] = search_totalrows
                query_table = view_name
                if search_sums:
                    result['sum_columns'] = search_sums
            else:
                self._clear_search_state(folder, conn, meta=meta)
                query_table = source_table
                if sum_columns and meta.get('_sum_values'):
                    result['sum_columns'] = meta['_sum_values']
            data_cols = ', '.join(self._quote_col(c) for c in all_columns)
            if order_by and self._order_by_is_valid(order_by, all_columns):
                parsed = self._parse_order_by(order_by)
                order_clause = ', '.join(
                    '%s %s' % (col, d) for col, d in parsed)
            else:
                order_clause = '_rowidx'
            if row_count:
                select_sql = (
                    'SELECT %s FROM %s ORDER BY %s LIMIT %d OFFSET %d'
                ) % (data_cols, query_table, order_clause,
                     int(row_count), int(row_start))
                rows = self._fetchall_sql(conn, select_sql)
            else:
                select_sql = (
                    'SELECT %s FROM %s ORDER BY %s'
                ) % (data_cols, query_table, order_clause)
                rows = self._fetchall_sql(conn, select_sql)
        finally:
            self._close_connection(conn)
        selection = self._build_selection(
            rows, all_columns, col_attrs, meta,
            dbtable, order_by, folder)
        result['selection'] = selection
        return result


# ---------------------------------------------------------------------------
#  GnrFreezedSelectionsSqlite — SQLite dialect
# ---------------------------------------------------------------------------

class GnrFreezedSelectionsSqlite(GnrFreezedSelectionsSql):
    """SQLite-based backend.

    Each frozen selection is stored as a ``selection_meta.json`` metadata file
    and a ``selection.sqlite`` database inside a dedicated folder.

    The SQLite database contains a single table ``selection_data`` with
    one column per selection field plus ``_rowidx`` as primary key.
    Column types are derived from ``colAttrs['dataType']``.
    """

    _folder_locks = {}
    _locks_lock = threading.Lock()

    def _get_lock(self, folder):
        """Return a per-folder threading.Lock, creating it if needed."""
        with self._locks_lock:
            if folder not in self._folder_locks:
                self._folder_locks[folder] = threading.Lock()
            return self._folder_locks[folder]

    # -- Dialect hooks -------------------------------------------------------

    @property
    def _like_operator(self):
        return 'LIKE'

    @property
    def _placeholder(self):
        return '?'

    def _quote_col(self, col_name):
        """Map column names: ``'pkey'`` → ``'_pkey'``, others unchanged."""
        return '_pkey' if col_name == 'pkey' else col_name

    def _col_type(self, dtype):
        if dtype in ('I', 'L'):
            return 'INTEGER'
        if dtype in ('N', 'R'):
            return 'REAL'
        return 'TEXT'

    def _source_table(self, meta):
        return 'selection_data'

    def _db_path(self, folder):
        return os.path.join(folder, 'selection.sqlite')

    def _open_connection(self, folder, meta):
        db_path = self._db_path(folder)
        if not os.path.exists(db_path):
            return None
        return sqlite3.connect(db_path)

    def _close_connection(self, conn):
        if conn is not None:
            conn.close()

    def _execute_sql(self, conn, sql, args=None):
        if args:
            conn.execute(sql, args)
        else:
            conn.execute(sql)

    def _fetchone_sql(self, conn, sql, args=None):
        if args:
            return conn.execute(sql, args).fetchone()
        return conn.execute(sql).fetchone()

    def _fetchall_sql(self, conn, sql, args=None):
        if args:
            return conn.execute(sql, args).fetchall()
        return conn.execute(sql).fetchall()

    def _commit_sql(self, conn):
        conn.commit()

    # -- SQLite-specific storage ---------------------------------------------

    def _create_and_populate(self, folder, meta, selection):
        """Create a fresh SQLite database and bulk-insert all rows."""
        db_path = self._db_path(folder)
        all_columns = meta['allColumns']
        sqlite_cols = [self._quote_col(c) for c in all_columns]
        col_defs = ['_rowidx INTEGER PRIMARY KEY']
        for col_name in all_columns:
            sqlite_col = self._quote_col(col_name)
            col_attrs = meta['colAttrs'].get(col_name, {})
            dtype = col_attrs.get('dataType', 'T')
            col_defs.append('%s %s' % (sqlite_col, self._col_type(dtype)))
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
        """Persist a selection to a new SQLite database."""
        folder = self.selection_folder(name)
        meta = self._build_meta(selection)
        with self._get_lock(folder):
            self._save_meta(folder, meta)
            self._create_and_populate(folder, meta, selection)
        return folder

    def freezeSelectionUpdate(self, selection):
        """Re-persist an already-frozen selection after in-memory changes."""
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
        """Restore a previously frozen selection from SQLite."""
        assert name, 'name is mandatory'
        if isinstance(dbtable, str):
            dbtable = self.proxy.db.table(dbtable)
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        if not os.path.isdir(folder):
            return None
        meta = self._load_meta(folder)
        if not meta:
            return None
        with self._get_lock(folder):
            db_path = self._db_path(folder)
            if not os.path.exists(db_path):
                return None
            all_columns = meta['allColumns']
            sqlite_cols = [self._quote_col(c) for c in all_columns]
            select_sql = 'SELECT %s FROM selection_data ORDER BY _rowidx' % (
                ', '.join(sqlite_cols))
            conn = sqlite3.connect(db_path)
            rows = conn.execute(select_sql).fetchall()
            conn.close()
        selection = self._build_selection(
            rows, all_columns, meta['colAttrs'], meta,
            dbtable, None, folder)
        if dbtable:
            assert (dbtable or self.proxy.db.table(meta['tablename'])) == selection.dbtable, \
                'unfrozen selection does not belong to the given table'
        return selection

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        """Return the list of pkeys from a frozen selection."""
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

    def getFromFreezedSelection(self, dbtable=None, name=None,
                                row_start=0, row_count=0,
                                order_by=None, sum_columns=None,
                                page_id=None,
                                searchOn_seed=None, searchOn_field=None,
                                searchOn_columns=None):
        """SQLite override: wraps the common logic with a per-folder lock."""
        assert name, 'name is mandatory'
        folder = self.proxy.pageLocalDocument(name, page_id=page_id)
        if not os.path.isdir(folder):
            return None
        with self._get_lock(folder):
            return super().getFromFreezedSelection(
                dbtable=dbtable, name=name,
                row_start=row_start, row_count=row_count,
                order_by=order_by, sum_columns=sum_columns,
                page_id=page_id,
                searchOn_seed=searchOn_seed, searchOn_field=searchOn_field,
                searchOn_columns=searchOn_columns)


# ---------------------------------------------------------------------------
#  GnrFreezedSelectionsUnlogged — PostgreSQL dialect
# ---------------------------------------------------------------------------

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


class GnrFreezedSelectionsUnlogged(GnrFreezedSelectionsSql):
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

    # -- Dialect hooks -------------------------------------------------------

    @property
    def _like_operator(self):
        return 'ILIKE'

    @property
    def _placeholder(self):
        return '%s'

    def _quote_col(self, col_name):
        return '"%s"' % col_name

    def _col_type(self, dtype):
        return _pg_col_type(dtype)

    def _source_table(self, meta):
        return self._qualified(meta['pg_table_name'])

    def _open_connection(self, folder, meta):
        self._ensure_schema()
        return self.db

    def _close_connection(self, conn):
        pass

    def _escape_pct(self, sql):
        """Escape literal '%' so psycopg2/gnrsql don't interpret them."""
        return sql.replace('%', '%%')

    def _execute_sql(self, conn, sql, args=None):
        if not args:
            sql = self._escape_pct(sql)
        self.db.execute(sql, args)

    def _fetchone_sql(self, conn, sql, args=None):
        if not args:
            sql = self._escape_pct(sql)
        return self.db.execute(sql, args, dbtable=None).fetchone()

    def _fetchall_sql(self, conn, sql, args=None):
        if not args:
            sql = self._escape_pct(sql)
        return self.db.execute(sql, args, dbtable=None).fetchall()

    def _commit_sql(self, conn):
        self.db.commit()

    def _post_build_selection(self, selection, folder, meta):
        selection._pg_table_name = meta.get('pg_table_name')

    def _search_view_name(self, meta):
        """PG search views must be schema-qualified and unique per selection."""
        if meta and meta.get('pg_table_name'):
            return '%s."_sv_%s"' % (self.schema, meta['pg_table_name'])
        return '%s."_search_view"' % self.schema

    # -- Meta path override: PG uses a different filename --------------------

    def _meta_path(self, folder):
        return os.path.join(folder, META_FILENAME)

    # -- PG-specific build_meta: includes pg_table_name ----------------------

    def _build_meta(self, selection, table_name=None):
        """Build metadata dict.  When called from freezeSelection the
        ``table_name`` argument provides the PG table name.  When called
        from the common getFromFreezedSelection (via _build_selection)
        the base class version is used and table_name is None."""
        meta = super()._build_meta(selection)
        if table_name:
            meta['pg_table_name'] = table_name
        return meta

    # -- PG type converters: PG returns native Python types ------------------

    def _build_converters(self, all_columns, col_attrs):
        """PostgreSQL returns native Python types (date, Decimal, bool),
        so no converters are needed."""
        return None

    # -- PG-specific infrastructure ------------------------------------------

    def _ensure_schema(self):
        if self._schema_ready:
            return
        self.db.execute('CREATE SCHEMA IF NOT EXISTS %s' % self.schema)
        self.db.commit()
        self._schema_ready = True

    def _qualified(self, table_name):
        return '%s."%s"' % (self.schema, table_name)

    def _table_exists(self, table_name):
        row = self._fetchone_sql(
            None,
            "SELECT 1 FROM pg_tables WHERE schemaname = %s AND tablename = %s",
            (self.schema, table_name))
        return row is not None

    def _drop_table(self, table_name):
        self.db.execute('DROP TABLE IF EXISTS %s CASCADE' % self._qualified(table_name))

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
            self.db.execute(create_sql, sql_args)
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
            col_defs.append('"%s" %s' % (col, self._col_type(dtype)))
        self.db.execute('CREATE UNLOGGED TABLE %s (%s)' % (
            qualified, ', '.join(col_defs)))
        col_keys = ['_rowidx'] + list(all_columns)
        col_names = ', '.join(['_rowidx'] + ['"%s"' % c for c in all_columns])
        placeholders = ', '.join([':' + k for k in col_keys])
        insert_sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
            qualified, col_names, placeholders)
        data = selection.data
        for i, row in enumerate(data):
            values = dict(_rowidx=i)
            for col in all_columns:
                v = row[col]
                if isinstance(v, decimal.Decimal):
                    v = float(v)
                values[col] = v
            self.db.execute(insert_sql, values)

    def _create_rowidx_index(self, table_name):
        qualified = self._qualified(table_name)
        idx_name = 'idx_%s_rowidx' % table_name
        self.db.execute(
            'CREATE UNIQUE INDEX "%s" ON %s (_rowidx)' % (idx_name, qualified))

    # -- Public API (PG-specific freeze/unfreeze) ----------------------------

    def freezeSelection(self, selection, name, freezePkeys=False, **kwargs):
        self._ensure_schema()
        page_id = self.proxy.page_id
        table_name = _make_pg_table_name(page_id, name)
        folder = self.selection_folder(name)
        if selection._outputTable:
            # Table already created by CREATE UNLOGGED TABLE AS SELECT
            totalrows = self._fetchone_sql(
                None, 'SELECT COUNT(*) FROM %s' % self._qualified(table_name))[0]
            selection._totalrows = totalrows
        else:
            self._drop_table(table_name)
            if not self._create_via_query(table_name, selection):
                self._create_via_insert(table_name, selection)
        self._create_rowidx_index(table_name)
        meta = self._build_meta(selection, table_name=table_name)
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
        new_meta = self._build_meta(selection, table_name=table_name)
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
        all_columns = meta['allColumns']
        col_attrs = meta['colAttrs']
        qualified = self._qualified(table_name)
        col_list = ', '.join(self._quote_col(c) for c in all_columns)
        rows = self._fetchall_sql(
            None, 'SELECT %s FROM %s ORDER BY _rowidx' % (col_list, qualified))
        selection = self._build_selection(
            rows, all_columns, col_attrs, meta,
            dbtable, None, folder)
        if dbtable:
            assert (dbtable or self.proxy.db.table(meta['tablename'])) == selection.dbtable, \
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
        rows = self._fetchall_sql(
            None, 'SELECT "pkey" FROM %s ORDER BY _rowidx' % qualified)
        return [r[0] for r in rows]

    # -- outputTableName for _outputTable injection ---------------------------

    def outputTableName(self, name):
        """Return the qualified _outputTable string for a given selectionName.

        The format ``UL:_qc."<table>"`` tells SqlQuery._get_sqltext to wrap
        the query as ``CREATE UNLOGGED TABLE ... AS SELECT ...``.
        """
        page_id = self.proxy.page_id
        table_name = _make_pg_table_name(page_id, name)
        self._ensure_schema()
        self._drop_table(table_name)
        return 'UL:%s' % self._qualified(table_name)

    # -- PG-specific cleanup -------------------------------------------------

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
        rows = self._fetchall_sql(
            None,
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
        self.db.execute('DROP SCHEMA IF EXISTS %s CASCADE' % self.schema)
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

    def outputTableName(self, name):
        """Return the _outputTable name if the backend supports it, else None."""
        if hasattr(self._backend, 'outputTableName'):
            return self._backend.outputTableName(name)
        return None

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
