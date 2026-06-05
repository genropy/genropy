#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_selection : SQL selection result wrapper
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU.
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""SQL Selection result wrapper.

This module defines :class:`SqlSelection`, the object returned by executing
a :class:`~gnr.sql.gnrsqldata.query.SqlQuery`.  A ``SqlSelection`` holds the
result rows together with column metadata and provides a rich set of output
methods (Bag, dict-list, tab-text, Excel, HTML, XML, JSON, …), as well as
sorting, filtering, freezing-to-disk (via pickle) and analytical
aggregation (via :class:`~gnr.core.gnranalyzingbag.AnalyzingBag`).

Typical lifecycle::

    query = tbl.query(columns='$name, $age', where='$age > :min_age',
                      min_age=18)
    sel = query.selection()          # -> SqlSelection
    data = sel.output('dictlist')    # list[dict]
    sel.sort('name')
    sel.freeze('/tmp/my_selection')  # persist to disk

The class is **not** intended to be instantiated directly; use
``SqlQuery.selection()`` or ``SqlQuery.fetch()`` instead.
"""

import os
import shutil
import pickle
import itertools
import tempfile
from xml.sax import saxutils

from gnr.core.gnrdecorator import deprecated
from gnr.core.gnrlang import uniquify, MinValue
from gnr.core.gnrlist import GnrNamedList
from gnr.core import gnrclasses
from gnr.core import gnrstring
from gnr.core import gnrlist
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.core.gnrbag import Bag, BagAsXml
from gnr.core.gnranalyzingbag import AnalyzingBag
from gnr.sql.gnrsql_exceptions import GnrSqlException, SelectionExecutionError
from gnr.sql.gnrsqldata.record import SqlRelatedRecordResolver


class SqlSelection(object):
    """Result set produced by executing a :class:`~gnr.sql.gnrsqldata.query.SqlQuery`.

    A ``SqlSelection`` wraps the raw row data returned by the database and
    exposes a rich API to:

    * **output** the data in many formats (Bag, dict-list, tab-text, Excel,
      HTML, XML, JSON, …) via :meth:`output`;
    * **sort** and **filter** the rows in-memory;
    * **freeze** the selection to disk (pickle-based) and reload it later;
    * **totalize** / **analyze** data using
      :class:`~gnr.core.gnranalyzingbag.AnalyzingBag`.

    The class is not meant to be instantiated directly — use
    ``SqlQuery.selection()`` or ``SqlQuery.fetch()`` instead.
    """

    def __init__(self, dbtable, data, index=None, colAttrs=None, key=None, sortedBy=None,
                 joinConditions=None, sqlContextName=None, explodingColumns=None, checkPermissions=None,
                 querypars=None,_aggregateRows=False,_aggregateDict=None):
        """Initialise a SqlSelection.

        Args:
            dbtable: The :class:`~gnr.sql.gnrsql_table.SqlTable` that
                originated the query.
            data: A list of :class:`~gnr.core.gnrlist.GnrNamedList` rows
                returned by the SQL driver.
            index: A ``dict`` mapping column names to their positional index
                inside each row.
            colAttrs: A ``dict`` mapping column names to their attribute
                dictionaries (label, dataType, format, …).
            key: Optional column name to use as row key (defaults to
                ``'pkey'`` if present in *index*).
            sortedBy: Column(s) to sort by immediately after construction.
            joinConditions: Join conditions forwarded to record resolvers.
            sqlContextName: SQL context name forwarded to record resolvers.
            explodingColumns: Columns subject to row-explosion / aggregation.
            checkPermissions: Permission-check flag propagated to child
                operations.
            querypars: Original query parameters (kept for reference).
            _aggregateRows: If ``True``, duplicate ``pkey`` rows are merged
                by aggregating the *explodingColumns*.
            _aggregateDict: Optional aggregation descriptor dict used when
                *_aggregateRows* is ``True``.
        """
        self._frz_data = None
        self._frz_filtered_data = None
        self.dbtable = dbtable
        self.querypars = querypars
        self.tablename = dbtable.fullname
        self.colAttrs = colAttrs or {}
        self.explodingColumns = explodingColumns
        self.aggregateDict = _aggregateDict
        # REVIEW: uses `== True` instead of simple truthiness check;
        #   `if _aggregateRows:` would be more pythonic.
        if _aggregateRows == True:
            data = self._aggregateRows(data, index, explodingColumns,aggregateDict=_aggregateDict)
        self._data = data
        if key:
            self.setKey(key)
        elif 'pkey' in index:
            self.key = 'pkey'
        else:
            self.key = None
        self.sortedBy = sortedBy
        if sortedBy:
            self.sort(sortedBy)
        self._keyDict = None
        self._filtered_data = None
        self._index = index
        self.columns = self.allColumns
        self.freezepath = None
        self.analyzeBag = None
        self.isChangedSelection = True
        self.isChangedData = True
        self.isChangedFiltered = True
        self.joinConditions = joinConditions
        self.sqlContextName = sqlContextName
        self.checkPermissions = checkPermissions

    def _aggregateRows(self, data, index, explodingColumns, aggregateDict=None):
        """Merge rows that share the same ``pkey`` by aggregating *explodingColumns*.

        When a query includes exploding (one-to-many) columns, the SQL result
        may contain multiple rows for the same record.  This method collapses
        them into a single row, collecting the varying column values into lists
        and optionally building sub-field dictionaries described by
        *aggregateDict*.

        Args:
            data: Raw row list from the database.
            index: Column-name → position mapping.
            explodingColumns: Column names that may carry multiple values per
                record.
            aggregateDict: Optional ``{col: (subfld, key_in_sub, pivot_col)}``
                descriptor for structured aggregation.

        Returns:
            The (possibly reduced) list of rows.
        """
        if self.explodingColumns:
            newdata = []
            datadict = {}
            # Determine which exploding columns need list-aggregation
            # (exclude one_one and columns handled by aggregateDict).
            mixColumns = [c for c in explodingColumns if c in index and not self.colAttrs[c].get('one_one') and not( aggregateDict and (c in aggregateDict))]
            for d in data:
                if not d['pkey'] in datadict:
                    # --- First occurrence of this pkey: seed lists ---
                    for col in mixColumns:
                        d[col] = [d[col]]
                    if aggregateDict:
                        # Build nested sub-field dicts for structured aggregation
                        for k,v in list(aggregateDict.items()):
                            subfld = v[0]
                            d[subfld] = d.get(subfld) or {}
                            sr = d[subfld].setdefault(d[v[2]],{})
                            sr[v[1]] = d[k]
                    newdata.append(d)
                    datadict[d['pkey']] = d
                else:
                    # --- Duplicate pkey: merge into existing master row ---
                    masterRow = datadict[d['pkey']]
                    for col in mixColumns:
                        if d[col] not in masterRow[col]:
                            masterRow[col].append(d[col])
                            # masterRow[col].sort()
                            masterRow[col].sort(key=lambda x: MinValue if x is None else x)
                    if aggregateDict:
                        for k,v in list(aggregateDict.items()):
                            subfld = v[0]
                            sr = masterRow[subfld].setdefault(d[v[2]],{})
                            sr[v[1]] = d[k]
            data = newdata
            # Post-processing: let the table apply field-level aggregation
            for d in data:
                for col in mixColumns:
                    d[col] = self.dbtable.fieldAggregate(col,d[col],fieldattr= self.colAttrs[col],onSelection=True)
        return data

    def setKey(self, key):
        """Assign a key column and populate it with row indices.

        Each row receives a sequential integer value under *key*, and the
        column is added to ``_index`` if not already present.

        Args:
            key: Column name to use as key (e.g. ``'rowidx'``).
        """
        self.key = key
        for i, r in enumerate(self._data):
            r[key] = i
        if key not in self._index:
            self._index[key] = len(self._index)

    def _get_allColumns(self):
        """Return all column names ordered by their positional index.

        Returns:
            list[str]: Column names in index order.
        """
        items = list(self._index.items())
        result = [None] * len(items)
        for k, v in items:
            result[v] = k
        return result

    allColumns = property(_get_allColumns)

    def _get_db(self):
        """Return the database connection from the owning table.

        Returns:
            The :class:`~gnr.sql.gnrsql.GnrSqlDb` instance.
        """
        return self.dbtable.db

    db = property(_get_db)

    def _get_keyDict(self):
        """Build and cache a dictionary mapping key-column values to rows.

        Returns:
            dict: ``{key_value: row}`` for every row in :attr:`data`.
        """
        if not self._keyDict:
            self._keyDict = dict([(r[self.key], r) for r in self.data])
        return self._keyDict

    keyDict = property(_get_keyDict)

    def output(self, mode, columns=None, offset=0, limit=None,
               filterCb=None, subtotal_rows=None, formats=None, locale=None, dfltFormats=None,
               asIterator=False, asText=False, **kwargs):
        """Return the selection data in the requested format.

        This is the main entry point for data extraction.  The *mode*
        argument selects the output method (``out_<mode>`` or
        ``iter_<mode>``).

        Args:
            mode: Output format name.  Common values include:

                * ``'pkeylist'`` — flat list of primary keys;
                * ``'records'`` — list of full record Bags;
                * ``'data'`` — raw row data (GnrNamedList);
                * ``'dictlist'`` — list of dicts;
                * ``'bag'`` / ``'grid'`` / ``'selection'`` — Bag-based
                  structures;
                * ``'tabtext'`` — tab-separated text;
                * ``'json'`` — JSON string;
                * ``'xls'`` — Excel file;
                * ``'html'`` — HTML table string.
            columns: Column name(s) to include (string or list).  Defaults
                to all columns.
            offset: Number of rows to skip from the start.
            limit: Maximum number of rows to return.
            filterCb: Optional ``(row) -> bool`` callback applied before
                slicing.
            subtotal_rows: Path into :attr:`analyzeBag` identifying which
                rows to include (used for subtotal rendering).
            formats: ``{column: format_string}`` dict for text conversion.
            locale: Locale string for formatting (e.g. ``'it'``, ``'en_us'``).
            dfltFormats: Fallback ``{type: format_string}`` dict.
            asIterator: If ``True``, use the ``iter_<mode>`` variant
                (returns a generator instead of a materialised collection).
            asText: If ``True``, apply text conversion to cell values.
            **kwargs: Forwarded to the output method.

        Returns:
            The formatted output — type depends on *mode*.

        Raises:
            SelectionExecutionError: If *mode* does not correspond to any
                ``out_<mode>`` / ``iter_<mode>`` method.
        """
        # --- subtotal filtering: restrict to rows in the analyzeBag node ---
        if subtotal_rows :
            subtotalNode = self.analyzeBag.getNode(subtotal_rows) if self.analyzeBag else None
            if subtotalNode and subtotalNode.attr:
                filterCb = lambda r: r[self.key] in subtotalNode.attr['idx']
        # For pkeylist / records we only need the pkey column
        if mode == 'pkeylist' or mode == 'records':
            columns = 'pkey'
        if isinstance(columns, str):
            columns = gnrstring.splitAndStrip(columns, ',')
        if not columns:
            columns = self.allColumns
            if self.aggregateDict:
                # Exclude aggregate-source columns from default output
                columns = [c for c in columns if c not in self.aggregateDict]
        self.columns = columns
        if mode == 'data':
            # Special sentinel: _out yields raw rows without column extraction
            columns = ['**rawdata**']

        # Choose between generator (iter_*) and materialised (out_*) methods
        if asIterator:
            prefix = 'iter'
        else:
            prefix = 'out'

        if mode == 'tabtext':
            asText = True
        if asText and not formats:
            formats = dict([(k, self.colAttrs.get(k, dict()).get('format')) for k in self.columns])

        outmethod = '%s_%s' % (prefix, mode)
        if hasattr(self, outmethod):
            outgen = self._out(columns=columns, offset=offset, limit=limit, filterCb=filterCb)
            if formats:
                outgen = self.toTextGen(outgen, formats=formats, locale=locale, dfltFormats=dfltFormats or {})
            # Dispatch to the concrete output method
            return getattr(self, outmethod)(outgen, **kwargs)
        else:
            raise SelectionExecutionError('Not existing mode: %s' % outmethod)

    def __len__(self):
        """Return the number of rows in the active (possibly filtered) data."""
        return len(self.data)

    def _get_data(self):
        """Return the active row list (filtered if a filter is set, otherwise full).

        Returns:
            list: The currently active row list.
        """
        if self._filtered_data is not None:
            return self._filtered_data
        else:
            return self._data

    data = property(_get_data)

    def _get_filtered_data(self):
        """Lazy-load filtered data from disk if frozen, then return it.

        Returns:
            list or None: The filtered row list, or ``None`` if no filter is
            active.
        """
        if self._frz_filtered_data == 'frozen':
            self._freeze_filtered('r')
        return self._frz_filtered_data

    def _set_filtered_data(self, value):
        """Set the filtered-data backing store."""
        self._frz_filtered_data = value

    _filtered_data = property(_get_filtered_data, _set_filtered_data)

    def _get_full_data(self):
        """Lazy-load full (unfiltered) data from disk if frozen, then return it.

        Returns:
            list: The complete row list.
        """
        if self._frz_data == 'frozen':
            self._freeze_data('r')
        return self._frz_data

    def _set_full_data(self, value):
        """Set the full-data backing store."""
        self._frz_data = value

    _data = property(_get_full_data, _set_full_data)

    def _freezeme(self):
        """Pickle the selection object itself (metadata) to disk.

        Before serialisation the heavy attributes (``dbtable``, ``_data``,
        ``_filtered_data``) are temporarily replaced with sentinel values so
        that only the lightweight selection metadata is persisted.  The row
        data is frozen separately by :meth:`_freeze_data` and
        :meth:`_freeze_filtered`.

        The file is written atomically via a temporary file + ``shutil.move``.
        """
        # REVIEW: uses `!= None` instead of `is not None` -- not idiomatic
        #   and may give unexpected results with objects that override __eq__.
        if self.analyzeBag != None:
            self.analyzeBag.makePicklable()
        # Temporarily save heavy data before pickling
        saved = self.dbtable, self._data, self._filtered_data
        # REVIEW: the expression `'frozen' * bool(self._filtered_data) or None`
        #   is cryptic.  Equivalent to: if _filtered_data is truthy → 'frozen',
        #   otherwise → None.  A ternary would be more readable:
        #   `'frozen' if self._filtered_data else None`.
        self.dbtable, self._data, self._filtered_data = None, 'frozen', 'frozen' * bool(self._filtered_data) or None
        selection_path = '%s.pik' % self.freezepath
        dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection',suffix='.pik')
        with os.fdopen(dumpfile_handle, "wb") as f:
            pickle.dump(self, f)
        # Atomic move: il file di destinazione viene sovrascritto solo a dump completato
        shutil.move(dumpfile_path, selection_path)
        # Ripristino degli attributi originali
        self.dbtable, self._data, self._filtered_data = saved

    def _freeze_data(self, readwrite):
        """Write or read the full (unfiltered) row data to/from a pickle file.

        Args:
            readwrite: ``'w'`` to write (freeze) data, ``'r'`` to read
                (thaw) data.
        """
        pik_path = '%s_data.pik' % self.freezepath
        if readwrite == 'w':
            # --- write: dump data to a temp file, then atomic move ---
            dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection_data',suffix='.pik')
            with os.fdopen(dumpfile_handle, "wb") as f:
                pickle.dump(self._data, f)
            shutil.move(dumpfile_path, pik_path)
        else:
            # --- read: reload data from pickle ---
            with open(pik_path, 'rb') as f:
                self._data = pickle.load(f)

    def _freeze_pkeys(self, readwrite):
        """Write or read the primary-key list to/from a pickle file.

        Args:
            readwrite: ``'w'`` to write, ``'r'`` to read.

        Returns:
            On read (``'r'``), returns the list of pkeys.  On write returns
            ``None``.
        """
        if not self.dbtable.pkey:
            return
        pik_path = '%s_pkeys.pik' % self.freezepath
        if readwrite == 'w':
            dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection_data',suffix='.pik')
            with os.fdopen(dumpfile_handle, "wb") as f:
                pickle.dump(self.output('pkeylist'), f)
            shutil.move(dumpfile_path, pik_path)
        else:
            with open(pik_path, 'rb') as f:
                return pickle.load(f)

    def _freeze_filtered(self, readwrite):
        """Write or read the filtered row data to/from a pickle file.

        When writing with no active filter (``_filtered_data is None``), the
        existing pickle file is removed if present.

        Args:
            readwrite: ``'w'`` to write (freeze), ``'r'`` to read (thaw).
        """
        fpath = '%s_filtered.pik' % self.freezepath
        if readwrite == 'w' and self._filtered_data is None:
            # No filter active: clean up stale pickle file if present
            if os.path.isfile(fpath):
                os.remove(fpath)
        else:
            if readwrite == 'w':
                dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection_filtered',suffix='.pik')
                # REVIEW(BUG-PROBABILE): il file viene aperto con mode "w"
                #   (testo) ma pickle.dump scrive bytes.  Dovrebbe essere "wb"
                #   come in _freeze_data.  Su Python 3 questo causerà un
                #   TypeError: write() argument must be str, not bytes.
                with os.fdopen(dumpfile_handle, "w") as f:
                    pickle.dump(self._filtered_data, f)
                shutil.move(dumpfile_path, fpath)
            else:
                # --- read: reload filtered data from pickle ---
                with open(fpath, 'rb') as f:
                    self._filtered_data = pickle.load(f)

    def freeze(self, fpath, autocreate=False, freezePkeys=False):
        """Persist the entire selection to disk as pickle files.

        Three (or four) files are created under *fpath*:

        * ``<fpath>.pik`` — the lightweight selection metadata
          (via :meth:`_freezeme`);
        * ``<fpath>_data.pik`` — the full row data;
        * ``<fpath>_filtered.pik`` — the filtered row data (if a filter is
          active);
        * ``<fpath>_pkeys.pik`` — the primary-key list (only when
          *freezePkeys* is ``True``).

        Args:
            fpath: Base path (without extension) for the pickle files.
            autocreate: If ``True``, create the target directory if it does
                not exist.
            freezePkeys: If ``True``, also persist the primary-key list.
        """
        self.freezepath = fpath
        self.isChangedSelection = False
        self.isChangedData = False
        self.isChangedFiltered = False
        if autocreate:
            dirname = os.path.dirname(fpath)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        self._freezeme()
        self._freeze_data('w')
        self._freeze_filtered('w')
        if freezePkeys:
            self._freeze_pkeys('w')

    def freezeUpdate(self):
        """Incrementally update the frozen files for parts that have changed.

        Only the components whose ``isChanged*`` flag is ``True`` are
        re-written, which is cheaper than a full :meth:`freeze`.
        """
        if self.isChangedData:
            self._freeze_data('w')
        if self.isChangedFiltered:
            self._freeze_filtered('w')

        isChangedSelection = self.isChangedSelection
        self.isChangedSelection = False # clear all changes flag before freeze self
        self.isChangedData = False
        self.isChangedFiltered = False
        if isChangedSelection:
            self._freezeme()

    def getByKey(self, k):
        """Return the row whose key column equals *k*.

        Args:
            k: The value to look up in :attr:`keyDict`.

        Returns:
            The matching :class:`~gnr.core.gnrlist.GnrNamedList` row.

        Raises:
            KeyError: If *k* is not found.
        """
        return self.keyDict[k]

    def sort(self, *args):
        """Sort the active row data in-place by the given column(s).

        Column specifiers may use Genro path syntax (``@`` / ``.``); these
        are normalised to underscores.  A single comma-separated string is
        also accepted.

        Args:
            *args: One or more column names, optionally suffixed with ``:d``
                for descending order.
        """
        args = list(args)
        # Normalise Genro-path separators to underscores
        args = [x.replace('.','_').replace('@','_') for x in args]
        if len(args) == 1 and (',' in args[0]):
            args = gnrstring.splitAndStrip(args[0], ',')
        if args != self.sortedBy:
            if self.explodingColumns:
                # Strip wildcard '*' from exploding-column sort specs
                for k, arg in enumerate(args):
                    if arg.split(':')[0] in self.explodingColumns:
                        args[k] = arg.replace('*', '')
            self.sortedBy = args
            gnrlist.sortByItem(self.data, *args)
            if self.key == 'rowidx':
                self.setKey('rowidx')
            self.isChangedSelection = True #prova
            if not self._filtered_data:
                self.isChangedData = True
            else:
                self.isChangedFiltered = True


    def filter(self, filterCb=None):
        """Apply (or clear) an in-memory filter on the row data.

        When *filterCb* is provided, only rows for which
        ``filterCb(row)`` returns truthy are retained (the original data is
        preserved and can be restored by calling ``filter()`` with no
        arguments).

        Args:
            filterCb: A callable ``(row) -> bool``.  Pass ``None`` to remove
                the current filter.
        """
        if filterCb:
            self._filtered_data = list(filter(filterCb, self._data))
        else:
            self._filtered_data = None
        self.isChangedFiltered = True

    def extend(self, selection, merge=True):
        """Append all rows from another selection to this one.

        Args:
            selection: Another :class:`SqlSelection` whose rows will be
                copied into this selection.
            merge: If ``False``, a column-index mismatch raises
                :class:`GnrSqlException`.  If ``True`` (default) the check
                is skipped.

        Raises:
            GnrSqlException: When *merge* is ``False`` and the two
                selections have different column indices.
        """
        # REVIEW: the `merge=True` and `merge=False` branches execute exactly
        #   the same code (build `l` the same way) -- the only difference is
        #   the mismatch check.  The `merge` parameter is effectively inert
        #   and the variable `l` in the `not merge` branch is overwritten
        #   by the subsequent branch anyway.
        if not merge:
            if self._index != selection._index:
                raise GnrSqlException("Selections columns mismatch")
            else:
                l = [self.newRow(r) for r in selection.data]
        else:
            l = [self.newRow(r) for r in selection.data]
        self.data.extend(l)

    def apply(self, cb):
        """Apply a transformation callback to every row of the full data set.

        The callback *cb* is invoked for each row and its return value
        determines the action:

        * **dict** — the row is updated in-place with the returned dict;
        * **None** — the row is removed;
        * **list** — the row is replaced by the list of new rows (each
          element is passed through :meth:`newRow`).

        Args:
            cb: A callable ``(row) -> dict | list | None``.
        """
        rowsToChange = []
        for i, r in enumerate(self._data):
            result = cb(r)
            if isinstance(result, dict):
                # In-place update: merge returned dict into the row
                r.update(result)
            else:
                # Deferred removal / replacement — collected for reverse pass
                rowsToChange.append((i, result))

        if rowsToChange:
            # Process in reverse order to keep indices valid after pop()
            rowsToChange.reverse()
            for i, change in rowsToChange:
                if change is None:
                    # Remove the row
                    self._data.pop(i)
                else:
                    # Replace the row with multiple new rows
                    self._data.pop(i)
                    change.reverse()
                    for r in change:
                        self.insert(i, r)

        self.isChangedData = True

    def insert(self, i, values):
        """Insert a new row at position *i* in the full data list.

        Args:
            i: Zero-based index at which the new row is inserted.
            values: A dict (or dict-like) of column values for the new row.
        """
        self._data.insert(i, self.newRow(values))

    def append(self, values):
        """Append a new row at the end of the full data list.

        Args:
            values: A dict (or dict-like) of column values for the new row.

        .. note::
            REVIEW: the original docstring declared a ``:param i:`` parameter
            that does not exist in the method signature.
        """
        self._data.append(self.newRow(values))

    def newRow(self, values):
        """Create a new :class:`~gnr.core.gnrlist.GnrNamedList` row from *values*.

        The row is initialised with the selection's column index and populated
        with the supplied values, but is **not** automatically appended to the
        data list.

        Args:
            values: A dict (or dict-like) of column values.

        Returns:
            GnrNamedList: The newly created row.
        """
        r = GnrNamedList(self._index)
        r.update(values)
        return r

    def remove(self, cb):
        """Remove rows for which *cb(row)* returns truthy.

        Args:
            cb: A callable ``(row) -> bool``.  Rows where *cb* returns
                ``True`` are removed.
        """
        # REVIEW(PROBABLE-BUG): `not(cb)` applies the `not` operator to the
        #   callable itself (not to its result), and always returns ``False``
        #   because a callable is truthy.  As a consequence,
        #   ``filter(False, self._data)`` returns an empty list and the method
        #   wipes ALL data.
        #   The intent was probably: `filter(lambda r: not cb(r), self._data)`.
        self._data = list(filter(not(cb), self._data))
        self.isChangedData = True

    def totalize(self, group_by=None, sum=None, collect=None, distinct=None,
                 keep=None, key=None, captionCb=None, **kwargs):
        """Build (or clear) an analytical aggregation over the selection data.

        Delegates to :class:`~gnr.core.gnranalyzingbag.AnalyzingBag.analyze`
        and stores the result in :attr:`analyzeBag`.

        Args:
            group_by: Column(s) to group by.  Genro-path separators
                (``@``, ``.``, ``$``) are normalised.  Pass ``None`` to
                clear the current aggregation.
            sum: Column(s) to sum within each group.
            collect: Column(s) to collect (list aggregation).
            distinct: Column(s) for distinct-value aggregation.
            keep: Column(s) whose first value is kept per group.
            key: Column used as row identifier (defaults to ``self.key``).
                Pass ``'#'`` to disable key usage.
            captionCb: Optional callback for generating group captions.
            **kwargs: Forwarded to
                :meth:`AnalyzingBag.analyze`.

        Returns:
            The :class:`~gnr.core.gnranalyzingbag.AnalyzingBag` instance
            (or ``None`` if *group_by* was ``None``).
        """
        if group_by is None:
            self.analyzeBag = None
        else:
            self.analyzeBag = self.analyzeBag or AnalyzingBag()
            if key is None:
                key = self.key
            elif key == '#':
                key = None
            if group_by:
                group_by = [x.replace('@', '_').replace('.', '_').replace('$', '') if isinstance(x, str) else x
                            for x in group_by]
            if keep:
                keep = [x.replace('@', '_').replace('.', '_').replace('$', '') if isinstance(x, str) else x for x
                        in keep]
            self.analyzeKey = key
            self.analyzeBag.analyze(self, group_by=group_by, sum=sum, collect=collect,
                                    distinct=distinct, keep=keep, key=key, captionCb=captionCb, **kwargs)
        return self.analyzeBag

    @deprecated
    def analyze(self, group_by=None, sum=None, collect=None, distinct=None, keep=None, key=None, **kwargs):
        """Deprecated alias for :meth:`totalize`.

        .. deprecated:: 0.7
            Use :meth:`totalize` instead.
        """
        self.totalize(group_by=group_by, sum=sum, collect=collect, distinct=distinct, keep=keep, key=key, **kwargs)

    def totalizer(self, path=None):
        """Return the :attr:`analyzeBag` or a sub-node of it.

        Args:
            path: Optional Bag path to drill into.  If ``None`` (or if
                :attr:`analyzeBag` is not set), the full Bag is returned.

        Returns:
            The :class:`~gnr.core.gnranalyzingbag.AnalyzingBag` (or a
            sub-node) or ``None`` if no aggregation has been performed.
        """
        if path and self.analyzeBag:
            return self.analyzeBag[path]
        else:
            return self.analyzeBag

    def totalizerSort(self, path=None, pars=None):
        """Sort a sub-tree of the :attr:`analyzeBag`.

        Args:
            path: Bag path identifying the node to sort.
            pars: Sort parameters forwarded to ``Bag.sort()``.  If ``None``,
                the default sort is applied.
        """
        tbag = self.totalizer(path)
        if pars:
            tbag.sort(pars)
        else:
            tbag.sort()

    def totals(self, path=None, columns=None):
        """Extract aggregated totals from the :attr:`analyzeBag`.

        Args:
            path: Bag path identifying the totalizer node to read.
            columns: Column names (string or list) whose aggregated values
                are extracted from each node's attributes.

        Returns:
            list[dict]: One dict per node, containing the requested columns.
        """
        if isinstance(columns, str):
            columns = gnrstring.splitAndStrip(columns, ',')

        tbag = self.totalizer(path)

        result = []
        for tnode in tbag:
            tattr = tnode.getAttr()
            result.append(dict([(k, tattr[k]) for k in columns]))

        return result


    def sum(self, columns=None):
        """Compute column-wise sums over the active data.

        ``None`` values are skipped during summation.

        Args:
            columns: Column name(s) — a comma-separated string or a list.

        Returns:
            list: One sum per requested column, in the same order.  Returns
            an empty list if *columns* is empty or the selection has no rows.
        """
        if isinstance(columns, str):
            columns = columns.split(',')
        result  = list()
        if not columns or not self.data:
            return result
        # Transpose: rows × columns → columns × rows
        data = list(zip(*[[r[c] for c in columns] for r in self.data]))
        for k,c in enumerate(columns):
            result.append(sum([r for r in data[k] if r is not None]))
        return result


    def _out(self, columns=None, offset=0, limit=None, filterCb=None):
        """Core generator that yields rows for the output pipeline.

        Applies optional filtering, offset/limit slicing and column
        extraction.  When *columns* is the sentinel ``['**rawdata**']``,
        raw :class:`GnrNamedList` rows are yielded without extraction.

        Args:
            columns: List of column names to extract, or ``['**rawdata**']``.
            offset: Number of rows to skip.
            limit: Maximum number of rows to yield.
            filterCb: Optional ``(row) -> bool`` pre-filter.

        Yields:
            Extracted ``(column, value)`` pairs or raw rows.
        """
        # Apply optional row filter
        if filterCb:
            source = filter(filterCb, self.data)
        else:
            source = self.data
        # Compute slice boundaries
        if limit:
            stop = offset + limit
        else:
            stop = None
        # Drop columns the current user is not allowed to see
        columns = [cname for cname in columns if not self.colAttrs.get(cname,{}).get('user_forbidden')]
        if columns != ['**rawdata**']:
            # Normal path: yield (column_name, value) pairs per row
            for r in itertools.islice(source, offset, stop):
                yield r.extractItems(columns)
        else:
            # Raw-data path: yield the full GnrNamedList row
            for r in itertools.islice(source, offset, stop):
                yield r

    def toTextGen(self, outgen, formats, locale, dfltFormats):
        """Wrap an output generator converting cell values to text strings.

        Each ``(column, value)`` pair is converted using
        :func:`gnr.core.gnrstring.toText` with the appropriate format.

        Args:
            outgen: The upstream row generator (yields lists of
                ``(column, value)`` pairs).
            formats: ``{column: format_string}`` mapping.
            locale: Locale string for formatting.
            dfltFormats: ``{type: format_string}`` fallback mapping.

        Yields:
            Rows with text-converted values.
        """
        def _toText(cell):
            k, v = cell
            v = gnrstring.toText(v, format=formats.get(k) or dfltFormats.get(type(v)), locale=locale)
            return (k, v)

        for r in outgen:
            yield list(map(_toText, r))

    def __iter__(self):
        """Iterate over the active (possibly filtered) rows."""
        return self.data.__iter__()

    def out_listItems(self, outsource):
        """Return the output generator as-is (pass-through).

        Args:
            outsource: The row generator from :meth:`_out`.

        Returns:
            The unmodified generator.
        """
        return outsource

    def out_count(self, outsource):
        """Count and return the number of rows produced by *outsource*.

        Args:
            outsource: The row generator from :meth:`_out`.

        Returns:
            int: The row count.
        """
        # REVIEW: the original comment read "dubbio secondo me non dovrebbe
        #   esserci" (doubtful, I don't think this should be here).  Indeed,
        #   consuming the entire generator just to count rows is inefficient:
        #   `len(self.data)` (or the filtered/sliced data) could be used
        #   directly without materialising the generator.
        n = 0
        for r in outsource:
            n += 1
        return n

    def out_distinctColumns(self, outsource):
        """Return per-column lists of unique values.

        Args:
            outsource: The row generator.

        Returns:
            list[list]: One list of unique values per column.
        """
        return [uniquify(x) for x in zip(*[[v for k, v in r] for r in outsource])]

    def out_distinct(self, outsource):
        """Return a set of distinct row tuples (values only, no column names).

        Args:
            outsource: The row generator.

        Returns:
            set[tuple]: Distinct value-tuples.
        """
        return set([tuple([col[1] for col in r]) for r in outsource])

    def out_generator(self, outsource):
        """Return the row generator as-is (pass-through, same as ``out_listItems``).

        Args:
            outsource: The row generator.

        Returns:
            The unmodified generator.
        """
        return outsource

    def iter_data(self, outsource):
        """Iterator variant of :meth:`out_data` — returns the generator as-is.

        Args:
            outsource: The row generator.

        Returns:
            The unmodified generator.
        """
        return outsource

    def out_data(self, outsource):
        """Materialise the generator into a list of raw rows.

        Args:
            outsource: The row generator.

        Returns:
            list: Materialised rows.
        """
        return [r for r in outsource]

    def iter_dictlist(self, outsource):
        """Yield each row as a plain ``dict``.

        Args:
            outsource: The row generator.

        Yields:
            dict: One dict per row.
        """
        for r in outsource:
            yield dict(r)

    def out_dictlist(self, outsource):
        """Return all rows as a list of plain dicts.

        Args:
            outsource: The row generator.

        Returns:
            list[dict]: One dict per row.
        """
        return [dict(r) for r in outsource]

    def out_json(self, outsource):
        """Return all rows as a JSON string.

        Args:
            outsource: The row generator.

        Returns:
            str: JSON-encoded list of dicts.
        """
        return gnrstring.toJson(self.out_dictlist(outsource))

    def out_list(self, outsource):
        """Return rows as a list of value-only lists (column names stripped).

        Args:
            outsource: The row generator.

        Returns:
            list[list]: One inner list of values per row.
        """
        return [[v for k, v in r] for r in outsource]

    def out_pkeylist(self, outsource):
        """Return a flat list of primary-key values.

        Args:
            outsource: The row generator (expected to yield ``[('pkey', val), ...]``).

        Returns:
            list: Primary-key values.
        """
        return [r[0][1] for r in outsource]

    def iter_pkeylist(self, outsource):
        """Yield primary-key values one at a time.

        Args:
            outsource: The row generator.

        Yields:
            Primary-key values.
        """
        for r in outsource:
            yield r[0][1]

    def out_template(self, outsource, rowtemplate=None, joiner=''):
        """Render each row through a string template and join the results.

        Args:
            outsource: The row generator.
            rowtemplate: A template string with ``$column`` placeholders.
            joiner: String used to join the rendered rows (default ``''``).

        Returns:
            str: The joined rendered string.
        """
        result = []
        for r in outsource:
            result.append(gnrstring.templateReplace(rowtemplate,dict(r),safeMode=True))
        return joiner.join(result)

    def out_records(self, outsource, virtual_columns=None):
        """Return full record Bags for each row (re-fetched from the database).

        Args:
            outsource: The row generator (only pkey is extracted).
            virtual_columns: Optional virtual columns to include.

        Returns:
            list[Bag]: One Bag-mode record per row.
        """
        return [self.dbtable.record(r[0][1], mode='bag',virtual_columns=virtual_columns) for r in outsource]

    def iter_records(self, outsource):
        """Yield full record Bags one at a time (re-fetched from the database).

        Args:
            outsource: The row generator.

        Yields:
            Bag: One Bag-mode record per row.
        """
        for r in outsource:
            yield self.dbtable.record(r[0][1], mode='bag')

    def out_bag(self, outsource, recordResolver=False):
        """Return a Bag with ``headers`` and ``rows`` sub-Bags.

        Args:
            outsource: The row generator.
            recordResolver: If ``True``, attach lazy record resolvers.

        Returns:
            Bag: ``{'headers': <Bag>, 'rows': <Bag>}``.
        """
        b = Bag()
        headers = Bag()
        for k in self.columns:
            headers.addItem(k, None, _attributes=self.colAttrs.get(k, {}))
        b['headers'] = headers
        b['rows'] = self.buildAsBag(outsource, recordResolver)
        return b

    def buildAsBag(self, outsource, recordResolver):
        """Build a Bag of row-Bags with optional record resolvers.

        Each node is keyed by the row's pkey (or ``'r_<index>'``) and
        decorated with a ``nodecaption`` attribute.

        Args:
            outsource: The row generator.
            recordResolver: If ``True``, a :class:`SqlRelatedRecordResolver`
                is attached as a ``'_'`` sub-node for each row.

        Returns:
            Bag: One node per row.
        """
        result = Bag()
        defaultTable = self.dbtable.fullname
        for j, row in enumerate(outsource):
            row = Bag(row)
            pkey = row.pop('pkey')
            if not pkey:
                spkey = 'r_%i' % j
            else:
                spkey = gnrstring.toText(pkey)

            nodecaption = self.dbtable.recordCaption(row)
            # REVIEW: commented-out code block (rowcaptionDecode, templateReplace).
            #   If no longer needed, consider removing.
            #fields, mask = self.dbtable.rowcaptionDecode()
            #cols = [(c, gnrstring.toText(row[c])) for c in fields]
            #if '$' in mask:
            #nodecaption = gnrstring.templateReplace(mask, dict(cols))
            #else:
            #nodecaption = mask % tuple([v for k,v in cols])

            result.addItem('%s' % spkey, row, nodecaption=nodecaption)
            if pkey and recordResolver:
                result['%s._' % spkey] = SqlRelatedRecordResolver(db=self.db, cacheTime=-1, mode='bag',
                                                                  target_fld='%s.%s' % (defaultTable, self.dbtable.pkey),
                                                                  relation_value=pkey,
                                                                  joinConditions=self.joinConditions,
                                                                  sqlContextName=self.sqlContextName)

        return result

    def out_recordlist(self, outsource, recordResolver=True):
        """Return a Bag of fully-built record Bags (via ``dbtable.buildrecord``).

        Args:
            outsource: The row generator.
            recordResolver: Unused in this implementation (kept for
                interface compatibility).

        Returns:
            Bag: One record-Bag per row.
        """
        result = Bag()
        content = None
        for j, row in enumerate(outsource):
            row = dict(row)
            content = self.dbtable.buildrecord(row)
            result.addItem('r_%i' % j, content, _pkey=row.get('pkey'))
        return result

    def out_baglist(self, outsource, recordResolver=False, labelIsPkey=False):
        """Return a Bag of row-Bags, optionally keyed by pkey.

        Columns with ``dtype='X'`` are automatically converted to sub-Bags.

        Args:
            outsource: The row generator.
            recordResolver: Unused in this implementation (kept for
                interface compatibility).
            labelIsPkey: If ``True``, use the pkey as the Bag node label
                instead of ``'r_<index>'``.
        """
        result = Bag()
        for j, row in enumerate(outsource):
            row = dict(row)
            pkey = row.pop('pkey', None)
            if labelIsPkey:
                label = pkey
            else:
                label = 'r_%i' % j
            content = Bag(row)
            for k,v in list(content.items()):
                if self.dbtable.column(k) is not None and self.dbtable.column(k).attributes.get('dtype')=='X':
                    content[k] = Bag(content[k])
            if pkey is not None:
                content['_pkey'] = pkey
            result.addItem(label,content , _pkey=pkey)
        return result

    def out_selection(self, outsource, recordResolver=False, caption=False):
        """Return a Bag where each item represents a row, keyed by pkey.

        Row data is stored as node attributes, and the node value is either
        an empty string or a :class:`SqlRelatedRecordResolver` (when
        *recordResolver* is ``True``).

        Args:
            outsource: The row generator.
            recordResolver: If ``True``, attach lazy record resolvers as
                node values.
            caption: If truthy, add a ``'caption'`` attribute to each row.
                Pass a string to use as a custom caption template, or
                ``True`` to use the table's default.

        Returns:
            Bag: One node per row, keyed by sanitised pkey.
        """
        result = Bag()
        content = ''
        for j, row in enumerate(outsource):
            row = dict(row)
            pkey = row.pop('pkey', None)
            # Build a safe Bag key from the pkey
            if not pkey:
                spkey = 'r_%i' % j
            else:
                spkey = gnrstring.toText(pkey).replace('.', '_')
            # Optionally attach a lazy record resolver
            if pkey and recordResolver:
                content = SqlRelatedRecordResolver(db=self.db, cacheTime=-1, mode='bag',
                                                   target_fld='%s.%s' % (self.dbtable.fullname, self.dbtable.pkey),
                                                   relation_value=pkey,
                                                   joinConditions=self.joinConditions,
                                                   sqlContextName=self.sqlContextName)
            # Optionally compute a caption for the row
            if caption:
                if isinstance(caption, str):
                    rowcaption = caption
                else:
                    rowcaption = None
                row['caption'] = self.dbtable.recordCaption(row, rowcaption=rowcaption)
            result.addItem('%s' % spkey, content,
                           _pkey=pkey, _attributes=row, _removeNullAttributes=False)
        return result

    def out_grid(self, outsource, recordResolver=True, **kwargs):
        """Return a Bag suitable for a Genro grid widget.

        Delegates to :meth:`buildAsGrid`.

        Args:
            outsource: The row generator.
            recordResolver: If ``True``, attach lazy record resolvers.
            **kwargs: Forwarded to :meth:`buildAsGrid`.

        Returns:
            Bag: Grid-ready Bag.
        """
        return self.buildAsGrid(outsource, recordResolver, **kwargs)

    def buildAsGrid(self, outsource, recordResolver, virtual_columns=None, **kwargs):
        """Build a Bag suitable for a Genro grid widget.

        Each row becomes a node keyed by pkey, with row data stored as node
        attributes.  If *recordResolver* is ``True``, the node value is a
        lazy :class:`SqlRelatedRecordResolver`.

        Args:
            outsource: The row generator.
            recordResolver: If ``True``, attach lazy record resolvers.
            virtual_columns: Optional virtual columns forwarded to the
                resolver.
            **kwargs: Currently unused (reserved for future extensions).

        Returns:
            Bag: Grid-ready Bag.
        """
        result = Bag()
        content = None
        for j, row in enumerate(outsource):
            row = Bag(row)
            pkey = row.pop('pkey')
            if not pkey:
                spkey = 'r_%i' % j
            else:
                spkey = gnrstring.toText(pkey)
            if pkey and recordResolver:
                content = SqlRelatedRecordResolver(db=self.db, cacheTime=-1, mode='bag',
                                                   target_fld='%s.%s' % (self.dbtable.fullname, self.dbtable.pkey),
                                                   relation_value=pkey, joinConditions=self.joinConditions,
                                                   virtual_columns=virtual_columns,
                                                   sqlContextName=self.sqlContextName)

            result.addItem('%s' % spkey.replace('.','_'), content, _pkey=spkey, _attributes=dict(row), _removeNullAttributes=False)
        return result

    def out_fullgrid(self, outsource, recordResolver=True):
        """Return a Bag with ``structure`` and ``data`` keys for a full grid.

        Args:
            outsource: The row generator.
            recordResolver: If ``True``, attach lazy record resolvers.

        Returns:
            Bag: ``{'structure': <Bag>, 'data': <Bag>}``.
        """
        result = Bag()
        result['structure'] = self._buildGridStruct()
        result['data'] = self.buildAsGrid(outsource, recordResolver)
        return result

    def _buildGridStruct(self, examplerow=None):
        """Build the ``structure`` Bag used by Genro grid widgets.

        The structure contains a ``view > row > cell*`` hierarchy describing
        column metadata (name, width, dtype, …).

        Args:
            examplerow: An optional example row used by
                :meth:`_cellStructFromCol` for type inference.

        Returns:
            Bag: Grid structure descriptor.
        """
        structure = Bag()
        r = structure.child('view').child('row')
        for colname in self.columns:
            if colname not in ('pkey', 'rowidx'):
                r.child('cell', childname=colname, **self._cellStructFromCol(colname, examplerow=examplerow))
        return structure

    def _cellStructFromCol(self, colname, examplerow=None):
        """Build a cell-descriptor dict for a single column.

        The dict contains keys like ``name``, ``field``, ``width``, ``dtype``
        suitable for inclusion in a grid structure Bag.

        Args:
            colname: Column name.
            examplerow: Optional example row (currently unused but accepted
                for interface compatibility).

        Returns:
            dict: Cell descriptor.
        """
        kwargs = dict(self.colAttrs.get(colname, {}))
        # Strip internal / server-only attributes
        for k in ('tag','sql_formula','_owner_package','virtual_column','_sysfield','_sendback','group','readOnly'):
             kwargs.pop(k, None)
        kwargs['name'] = kwargs.pop('label', None)
        kwargs['field'] = colname
        size = kwargs.pop('size', None)
        size = kwargs.pop('print_width', size)
        kwargs['width'] = None
        kwargs['dtype'] = kwargs.pop('dataType', None)
        if not kwargs['dtype']:
            kwargs['dtype'] = GnrClassCatalog.convert().asTypedText(45)[-1]
        if size:
            if isinstance(size, str):
                if ':' in size:
                    size = size.split(':')[1]
            kwargs['width'] = '%iem' % int(int(size) * .7)
        return kwargs

    def out_xmlgrid(self, outsource):
        """Return a Bag with XML-encoded grid data and structure.

        Each row is serialised as an XML self-closing element with typed
        attribute values.

        Args:
            outsource: The row generator (must include ``'rowidx'`` column).

        Returns:
            Bag: ``{'data': BagAsXml, 'structure': Bag}``.
        """
        result = Bag()

        dataXml = []
        catalog = gnrclasses.GnrClassCatalog()
        # REVIEW: commented-out code block (xmlheader, structCellTmpl,
        #   structXml, structure, dataXml='<data>...', BagAsXml concat).
        #   If no longer needed, consider removing.
        #xmlheader = "<?xml version='1.0' encoding='UTF-8'?>\n"
        #structCellTmpl='<%(field)s  name="%(name)s" field="%(field)s" dataType="%(dataType)s" width="%(width)s" tag="cell"/>'
        dataCellTmpl = '<r_%i  %s/>'
        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        #structXml = '\n'.join([structCellTmpl % self._cellStructFromCol(colname) for colname in columns])
        #structure = '<structure><view_0 tag="view"><row_0 tag="row">%s</row_0></view_0></structure>' % structXml
        for row in outsource:
            row = dict(row)
            rowstring = ' '.join(
                    ['%s=%s' % (colname, saxutils.quoteattr(catalog.asTypedText(row[colname]))) for colname in columns])
            dataXml.append(dataCellTmpl % (row['rowidx'], rowstring))
        result['data'] = BagAsXml('\n'.join(dataXml))
        result['structure'] = self._buildGridStruct(row)
        #dataXml='<data>%s</data>' %
        # result = '%s\n<GenRoBag><result>%s\n%s</result></GenRoBag>' % (xmlheader,structure,dataXml)
        #result = BagAsXml('%s\n%s' % (structure,dataXml))
        return result

    @property
    def colHeaders(self):
        """Return localised header labels for the active columns.

        Excludes ``'pkey'`` and ``'rowidx'`` columns.

        Returns:
            list[str]: Translated column labels.
        """
        def translate(txt):
            return self.dbtable.db.localizer.translate(txt)


        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        headers = []
        for colname in columns:
            colattr = self.colAttrs.get(colname, dict())
            headers.append(translate(colattr.get('label', colname)))
        return headers

    def out_html(self, outsource):
        """Return an HTML ``<table>`` string with headers and data rows.

        ``None`` values are rendered as ``&nbsp;``.

        Args:
            outsource: The row generator.

        Returns:
            str: HTML table markup.
        """
        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        result = ['<table><thead>',''.join(['<th>{}<th>'.format(h) for h in self.colHeaders]),'</thead>','<tbody>']
        for row in outsource:
            row = dict(row)
            result.append('<tr>{}</tr>'.format(''.join(['<td>{}<td>'.format('&nbsp;' if row[col] is None else row[col]) for col in columns])))
        result.append('</tbody></table>')
        return '\n'.join(result)

    def out_tabtext(self, outsource):
        """Return data as tab-separated text with a header line.

        Newlines, carriage returns and tabs within cell values are replaced
        with spaces.

        Args:
            outsource: The row generator (expected to yield text-converted
                rows when ``asText=True`` is active).

        Returns:
            str: Tab-separated text.
        """
        headers = self.colHeaders
        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        result = ['\t'.join(headers)]
        for row in outsource:
            r = dict(row)
            # REVIEW: no handling for None values -- if r[col] is None,
            #   the .replace() call will raise AttributeError.
            #   A `str(r[col] or '')` or explicit guard may be needed.
            result.append(
                    '\t'.join([r[col].replace('\n', ' ').replace('\r', ' ').replace('\t', ' ') for col in columns]))
        return '\n'.join(result)

    def out_xls(self, outsource, filepath=None, headers=None):
        """Write the selection data to an Excel file.

        Tries ``openpyxl`` first (xlsx); falls back to the legacy ``xlwt``
        writer (xls).

        Args:
            outsource: The row generator.
            filepath: Destination file path.  If ``None``, a temporary file
                is used.
            headers: Custom header labels.  Pass ``False`` to use column
                names as headers.  Defaults to :attr:`colHeaders`.
        """
        try:
            import openpyxl # noqa: F401
            from gnr.core.gnrxls import XlsxWriter as ExcelWriter
        except ImportError:
            from gnr.core.gnrxls import XlsWriter as ExcelWriter

        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        coltypes = dict([(k, v['dataType']) for k, v in self.colAttrs.items()])
        if headers is None:
            headers = self.colHeaders
        elif headers is False:
            headers = columns
        writer = ExcelWriter(columns=columns, coltypes=coltypes,
                            headers=headers,
                            filepath=filepath,
                           font='Times New Roman',
                           format_float='#,##0.00', format_int='#,##0')
        writer(data=outsource)


# ===========================================================================
# REVIEW NOTES (selection.py)
# ===========================================================================
#
# Summary of all oddities, probable bugs, and dead code found during the
# review of this file.  Each item is marked with a REVIEW marker in the
# source code.
#
# 1. __init__ -- `_aggregateRows == True`
#    Uses `== True` instead of simple truthiness check.
#    More pythonic: `if _aggregateRows:`.
#
# 2. _freezeme -- `self.analyzeBag != None`
#    Uses `!= None` instead of `is not None`.  May give unexpected results
#    with objects that override __eq__.
#
# 3. _freezeme -- `'frozen' * bool(self._filtered_data) or None`
#    Cryptic expression.  Equivalent to a ternary
#    `'frozen' if self._filtered_data else None` but far less readable.
#
# 4. _freeze_filtered -- `os.fdopen(dumpfile_handle, "w")`  [PROBABLE BUG]
#    File is opened in text mode ("w") but pickle.dump writes bytes.
#    On Python 3 this causes TypeError.  Should be "wb" as in _freeze_data.
#
# 5. extend -- `merge` parameter nearly inert
#    The `merge=True` and `merge=False` branches execute the same code
#    (build `l` identically); the only difference is the mismatch check
#    on column indices.  The parameter is effectively useless.
#
# 6. append -- wrong docstring
#    The original docstring declared a parameter `:param i:` that does not
#    exist in the method signature.
#
# 7. remove -- `not(cb)`  [PROBABLE BUG]
#    `not(cb)` applies the `not` operator to the callable itself (not its
#    result) and always returns False (a callable is truthy).
#    `filter(False, self._data)` returns an empty list, wiping ALL data.
#    The intent was probably:
#    `filter(lambda r: not cb(r), self._data)`.
#
# 8. out_count -- inefficiency
#    The method consumes the entire generator just to count rows.
#    `len(self.data)` could be used directly.
#
# 9. out_tabtext -- no handling for None
#    If a cell value is None, the `.replace()` call will raise
#    AttributeError.  A guard like `str(v or '')` is missing.
#
# 10. buildAsBag -- commented-out code block
#     Old implementation of rowcaptionDecode/templateReplace.  If no longer
#     needed, consider removing.
#
# 11. out_xmlgrid -- commented-out code blocks
#     Old XML markup (xmlheader, structCellTmpl, structure, BagAsXml
#     concat).  If no longer needed, consider removing.
#
# 12. _buildGridStruct -- (via out_xmlgrid) related commented-out code
#     See point 11.
#
# ===========================================================================
