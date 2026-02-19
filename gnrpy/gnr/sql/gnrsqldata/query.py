#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_query : SQL query builder and data resolver
# Copyright (c) : 2004 - 2026 Softwell srk - Milano
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

"""SQL query builder and data resolver.

This module provides:

- ``SqlDataResolver``: a ``BagResolver`` subclass for lazy table-data loading
  inside Bag hierarchies. Rarely used directly; serves as base for
  application-level data resolvers.

- ``SqlQuery``: the main entry point for building and executing SQL queries.
  Compiles the query through ``SqlQueryCompiler``, then offers multiple
  consumption modes:

  - ``selection()`` → ``SqlSelection`` (row-set with sort/filter/output)
  - ``fetch()`` / ``fetchAsDict()`` / ``fetchAsBag()`` / ``fetchGrouped()``
  - ``fetchPkeys()`` / ``fetchAsJson()``
  - ``count()`` / ``cursor()`` / ``servercursor()``
"""

import re
import json
import datetime
from collections import OrderedDict

from gnr.core.gnrbag import Bag, BagResolver
from gnr.sql.gnrsqldata.compiler import SqlQueryCompiler
from gnr.sql.gnrsqldata.selection import SqlSelection


class SqlDataResolver(BagResolver):
    """Lazy BagResolver that loads table data on first Bag access.

    Subclass this to create application-level data resolvers that populate
    a Bag node with query results when the node is first read.

    Attributes:
        tablename: Positional class argument — the ``pkg.table`` to query.
        db: The ``GnrSqlDb`` instance (injected at construction).
        dbtable: The resolved ``SqlTable`` object (set in ``init()``).
    """
    classKwargs = {'cacheTime': 0,
                   'readOnly': True,
                   'db': None}
    classArgs = ['tablename']

    def resolverSerialize(self):
        """Serialize the resolver state for Bag persistence.

        Returns:
            dict: Module, class, args and kwargs for reconstruction.
        """
        attr = {}
        attr['resolvermodule'] = self.__class__.__module__
        attr['resolverclass'] = self.__class__.__name__
        attr['args'] = list(self._initArgs)
        attr['kwargs'] = dict(self._initKwargs)
        attr['kwargs'].pop('db')
        attr['kwargs']['_serialized_app_db'] = 'maindb'
        return attr

    def init(self):
        """Resolve ``tablename`` into a ``dbtable`` reference.

        Called automatically by ``BagResolver`` after construction.
        Delegates to ``onCreate()`` for subclass-specific initialization.
        """
        # REVIEW: commented-out code block (original lines 53-58) --
        # leftovers from an old init mechanism via ``get_app``.
        # Can be removed.
        self.dbtable = self.db.table(self.tablename)
        self.onCreate()

    def onCreate(self):
        """Hook for subclass initialization after ``dbtable`` is resolved.

        Override in subclasses to perform custom setup. Default is no-op.
        """
        pass

class SqlQuery(object):
    """The SqlQuery class represents the way in which data can be extracted from a db.
    You can get data with these SqlQuery methods:

    * the :meth:`~gnr.sql.gnrsqldata.SqlQuery.count` method
    * the :meth:`~gnr.sql.gnrsqldata.SqlQuery.cursor` method
    * the :meth:`~gnr.sql.gnrsqldata.SqlQuery.fetch` method
    * the :meth:`~gnr.sql.gnrsqldata.SqlQuery.selection` method (return a :class:`~gnr.sql.gnrsqldata.SqlSelection` class)
    * the :meth:`~gnr.sql.gnrsqldata.SqlQuery.servercursor` method

    The ``__init__`` method passes:

    :param dbtable: specify the :ref:`database table <table>`. More information in the
                    :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
    :param columns: it represents the :ref:`table columns <columns>` to be returned by the "SELECT"
                    clause in the traditional sql query. For more information, check the
                    :ref:`sql_columns` section
    :param where: the sql "WHERE" clause. For more information check the :ref:`sql_where` section.
    :param order_by: corresponding to the sql "ORDER BY" operator. For more information check the
                     :ref:`sql_order_by` section
    :param distinct: boolean, ``True`` for getting a "SELECT DISTINCT"
    :param limit: number of result's rows. Corresponding to the sql "LIMIT" operator. For more
                  information, check the :ref:`sql_limit` section
    :param offset: the same of the sql "OFFSET"
    :param group_by: the sql "GROUP BY" clause. For more information check the :ref:`sql_group_by` section
    :param having: the sql "HAVING" clause. For more information check the :ref:`sql_having`
    :param for_update: boolean. TODO
    :param relationDict: a dict to assign a symbolic name to a :ref:`relation`. For more information
                         check the :ref:`relationdict` documentation section
    :param sqlparams: a dictionary which associates sqlparams to their values
    :param bagFields: boolean. If ``True`` include fields of type Bag (``X``) when columns is ``*`` or
                      contains ``*@relname.filter``
    :param joinConditions: special conditions for joining related tables. See the
                           :meth:`setJoinCondition() <gnr.sql.gnrsqldata.SqlQuery.setJoinCondition()>`
                           method
    :param sqlContextName: the name of the sqlContext to be reported for subsequent related selection.
                            (see the
                           :meth:`setJoinCondition() <gnr.web.gnrwebpage.GnrWebPage.setJoinCondition>` method)
    :param excludeLogicalDeleted: boolean. If ``True``, exclude from the query all the records that are
                                  "logical deleted"
    :param addPkeyColumn: boolean. If ``True``, add a column with the :ref:`pkey` attribute
    :param locale: the current locale (e.g: en, en_us, it)"""
    def __init__(self, dbtable, columns=None, where=None, order_by=None,
                 distinct=None, limit=None, offset=None,
                 group_by=None, having=None, for_update=False,
                 relationDict=None, sqlparams=None, bagFields=False,
                 joinConditions=None, sqlContextName=None,
                 excludeLogicalDeleted=True,excludeDraft=True,
                 ignorePartition=False,subtable=None,
                 addPkeyColumn=True, ignoreTableOrderBy=False,
                 locale=None,_storename=None,
                 checkPermissions=None,
                 aliasPrefix=None,
                 mangler=None,
                 mainquery_kw=None,
                 **kwargs):
        self.dbtable = dbtable
        self.sqlparams = sqlparams or {}
        columns = columns or '*'
        self.subtable = subtable
        self.joinConditions = joinConditions or {}
        self.sqlContextName = sqlContextName
        self.relationDict = relationDict or {}
        self.enable_sq_join = kwargs.pop('enable_sq_join', None)
        self.query_kw = dict(kwargs)
        self.sqlparams.update(kwargs)
        self.excludeLogicalDeleted = excludeLogicalDeleted
        self.excludeDraft = excludeDraft
        self.ignorePartition = ignorePartition
        self.addPkeyColumn = addPkeyColumn and dbtable.pkey is not None
        self.ignoreTableOrderBy = ignoreTableOrderBy
        self.locale = locale
        self.storename = _storename
        self.checkPermissions = checkPermissions
        self.aliasPrefix = aliasPrefix
        self.mangler = mangler
        self.mainquery_kw = mainquery_kw or {}
        test = " ".join([v for v in (columns, where, order_by, group_by, having) if v])
        rels = set(re.findall(r'\$(\w*)', test))
        params = set(re.findall(r'\:(\w*)', test))

        self.bagFields = bagFields or for_update
        self.querypars = dict(columns=columns, where=where, order_by=order_by,
                              distinct=distinct, group_by=group_by,
                              limit=limit, offset=offset,for_update=for_update,
                              having=having,bagFields=self.bagFields,
                            excludeLogicalDeleted=self.excludeLogicalDeleted,
                            excludeDraft=self.excludeDraft,
                            addPkeyColumn=self.addPkeyColumn,
                            ignorePartition=self.ignorePartition,
                            ignoreTableOrderBy=self.ignoreTableOrderBy,
                            storename=self.storename,
                            subtable=self.subtable)
        self.db = self.dbtable.db
        self._compiled = None

    def setJoinCondition(self, target_fld=None, from_fld=None, relation=None,
                         condition=None, one_one=False, **kwargs):
        """Register an extra join condition for a specific relation.

        Args:
            target_fld: Fully-qualified target field (``pkg.table.column``).
            from_fld: Fully-qualified source field.
            relation: Optional relation name key (alternative to
                ``target_fld``/``from_fld`` pair).
            condition: SQL condition string (may reference ``$tbl``).
            one_one: If ``True``, treat a one-to-many relation as one-to-one.
            **kwargs: Additional bind parameters for the condition.
        """
        cond = dict(condition=condition, one_one=one_one, params=kwargs)
        self.joinConditions[relation or '%s_%s' % (target_fld.replace('.', '_'), from_fld.replace('.', '_'))] = cond

        # REVIEW: commented-out ``resolver()`` method (lines 168-171) --
        # leftover from an old ``SqlSelectionResolver``. Can be removed.

    def _get_sqltext(self):
        return self.compiled.get_sqltext(self.db)

    sqltext = property(_get_sqltext)

    def _get_compiled(self):
        if self._compiled is None:
            self._compiled = self.compileQuery()
        return self._compiled

    compiled = property(_get_compiled)

    def compileQuery(self, count=False):
        """Return the :meth:`compiledQuery() <SqlQueryCompiler.compiledQuery()>` method.

        :param count: boolean. If ``True``, optimize the sql query to get the number of resulting rows (like count(*))"""
        return SqlQueryCompiler(self.dbtable.model,
                                joinConditions=self.joinConditions,
                                sqlContextName=self.sqlContextName,
                                sqlparams=self.sqlparams,
                                aliasPrefix=self.aliasPrefix,
                                locale=self.locale,
                                mangler=self.mangler,
                                query_kw=self.query_kw,
                                mainquery_kw=self.mainquery_kw,
                                query=self).compiledQuery(count=count,
                                                          relationDict=self.relationDict,
                                                          **self.querypars)

    def cursor(self):
        """Get a cursor of the current selection."""
        with self.db.tempEnv(currentImplementation=self.dbtable.dbImplementation):
            cursor = self.db.execute(self.sqltext, self.sqlparams, dbtable=self.dbtable.fullname,storename=self.storename)
        return cursor

    def fetch(self):
        """Get a cursor of the current selection and fetch it"""
        cursor = self.cursor()
        if isinstance(cursor, list):
            result = []
            for c in cursor:
                result.extend(c.fetchall())
                c.close()
            return result
        result = cursor.fetchall()
        cursor.close()
        self.handlePyColumns(result)
        self.handleBagColumns(result)
        return result

    def handlePyColumns(self, data):
        """Evaluate Python-computed virtual columns on fetched rows.

        Iterates over declared ``pyColumns`` and calls each handler
        function for every row in *data*, storing the result back into
        the row dict.

        Args:
            data: List of row dicts (modified in place).
        """
        if not self.compiled.pyColumns:
            return
        pcdict = dict(self.compiled.pyColumns)
        for field in list(self.dbtable.model.virtual_columns.keys()):
            if not field in pcdict:
                continue
            handler = pcdict[field]
            if handler:
                for d in data:
                    # REVIEW: commented-out line ``d[field] = handler(...)``
                    # followed by identical uncommented line -- debug leftover.
                    result = handler(d, field=field)
                    d[field] = result

    def handleBagColumns(self, data):
        """Post-process Bag-type columns (``#BAG`` / ``#BAGCOLS``) in fetched rows.

        For each declared ``evaluateBagColumns`` entry, parses the raw
        string value into a ``Bag``. If ``separateCols`` is ``True``,
        flattens the Bag leaves into individual dict keys.

        Args:
            data: List of row dicts (modified in place).
        """
        if not self.compiled.evaluateBagColumns:
            return
        for d in data:
            for field, separateCols in self.compiled.evaluateBagColumns:
                val = Bag(d[field])
                if separateCols:
                    for k,v in val.getLeaves():
                        d['{}_{}'.format(field,k.replace('.','_'))] = v
                    d[field] = None
                else:
                    d[field] = val


    def fetchPkeys(self):
        """Fetch and return only the primary key values.

        Returns:
            list: Primary key values for all matching rows.
        """
        fetch = self.fetch()
        pkeyfield = self.dbtable.pkey
        return [r[pkeyfield] for r in fetch]

    def fetchAsJson(self, key=None):
        """Fetch rows and serialize as a JSON string.

        Args:
            key: Unused (present for signature compatibility).

        Returns:
            str: JSON array of row dicts.
        """
        fetch = self.fetch()
        key = key or self.dbtable.pkey
        # REVIEW: GnrDictRowEncoder is defined as an inner class inside the
        # method -- it could be extracted to module level for reusability
        # and clarity.
        class GnrDictRowEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                return str(obj)
        return json.dumps([{k: v for k, v in r.items()} for r in fetch], cls=GnrDictRowEncoder)

    def fetchAsDict(self, key=None, ordered=False, pkeyOnly=False):
        """Return the :meth:`~gnr.sql.gnrsqldata.SqlQuery.fetch` method as a dict with as key
        the parameter key you gave (or the pkey if you don't specify any key) and as value the
        record you get from the query

        :param key: the key you give (if ``None``, it takes the pkey).
        :param ordered: boolean. if ``True``, return the fetch using a :class:`OrderedDict`,
                        otherwise (``False``) return the fetch using a normal dict.
        :pkeyOnly: boolean  if ``True``, the values of the dict are the pkeys and not the record"""

        fetch = self.fetch()
        key = key or self.dbtable.pkey
        if ordered:
            factory = OrderedDict
        else:
            factory = dict
        if pkeyOnly:
            return factory([(r[key], r[self.dbtable.pkey]) for r in fetch])
        return factory([(r[key], r) for r in fetch])

    def fetchAsBag(self, key=None):
        """Return the :meth:`~gnr.sql.gnrsqldata.SqlQuery.fetch` method as a Bag of the given key

        :param key: the key you give (if ``None``, it takes the pkey). """
        fetch = self.fetch()
        key = key or self.dbtable.pkey
        return Bag(sorted([(r[key], None, dict(r)) for r in fetch]))

    def fetchGrouped(self, key=None, asBag=False,ordered=False):
        """Return the :meth:`~gnr.sql.gnrsqldata.SqlQuery.fetch` method as a dict of the given key

        :param key: the key you give (if ``None``, it takes the pkey).
        :param asBag: boolean. If ``True``, return the result as a Bag. If False, return the
                      result as a dict"""
        fetch = self.fetch()
        key = key or self.dbtable.pkey
        if asBag:
            result = Bag()
        elif ordered:
            result = OrderedDict()
        else:
            result = {}
        for r in fetch:
            k = r[key]
            if not k in result:
                result[k] = [r]
            else:
                result[k].append(r)
        return result

    def test(self):
        """Return the compiled SQL text and parameters without executing.

        Useful for debugging and logging.

        Returns:
            tuple: ``(sql_text, sql_params)``
        """
        return (self.sqltext, self.sqlparams)

    def _dofetch(self, pyWhere=None):
        """Execute the query and return raw index and data.

        Args:
            pyWhere: Optional Python-side filter callback applied row-by-row
                during fetch (server-cursor mode).

        Returns:
            tuple: ``(index, data)`` where *index* is a column-name → position
            dict and *data* is a list of row dicts.
        """
        if pyWhere:
            # Server-side cursor mode: fetch in chunks and filter in Python
            cursor, rowset = self.serverfetch(arraysize=100)
            index = cursor.index
            data = []
            for rows in rowset:
                data.extend([r for r in rows if pyWhere(r)])
        else:
            cursor = self.cursor()
            # Multi-store scenario: cursor is a list of cursors
            if isinstance(cursor, list):
                data = []
                for c in cursor:
                    data.extend(c.fetchall() or [])
                    index = c.index
                    c.close()
                return index, data
            data = cursor.fetchall() or []
            index = cursor.index
        self.handlePyColumns(data)
        self.handleBagColumns(data)
        return index, data

    def selection(self, pyWhere=None, key=None, sortedBy=None, _aggregateRows=False):
        """Execute the query and return a SqlSelection

        :param pyWhere: a callback that can be used to reduce the selection during the fetch
        :param key: TODO
        :param sortedBy: TODO
        :param _aggregateRows: boolean. TODO"""
        index, data = self._dofetch(pyWhere=pyWhere)
        querypars = dict(self.querypars)
        querypars.update(self.sqlparams)
        return SqlSelection(self.dbtable, data,
                            index=index,
                            querypars=querypars,
                            colAttrs=self._prepColAttrs(index),
                            joinConditions=self.joinConditions,
                            sqlContextName=self.sqlContextName,
                            key=key,
                            sortedBy=sortedBy,
                            explodingColumns=self.compiled.explodingColumns,
                            checkPermissions = self.checkPermissions,
                            _aggregateRows=_aggregateRows,
                            _aggregateDict = self.compiled.aggregateDict
                            )

    def _prepColAttrs(self, index):
        """Build column-attribute metadata for ``SqlSelection``.

        For each column in the result set, looks up the corresponding
        database column to gather attributes like ``dtype``, ``name_long``,
        ``print_width``, and permission overrides.

        Args:
            index: Column-name → position dict from the cursor.

        Returns:
            dict: Column-name → attributes dict.
        """
        colAttrs = {}
        for k in list(index.keys()):
            if k == 'pkey':
                fld = self.dbtable.pkey
            else:
                f = self.compiled.aliasDict.get(k, k)
                f = f.strip()
                f = f.strip('$')
                fld = self.compiled.relationDict.get(f, f)
            col = self.dbtable.column(fld)
            if col is not None:
                attrs = dict(col.attributes)
                if self.checkPermissions:
                    attrs.update(col.getPermissions(**self.checkPermissions))
                attrs.pop('comment', None)
                attrs['dataType'] = attrs.pop('dtype', 'T')
                attrs['label'] = attrs.pop('name_long', k)
                attrs['print_width'] = col.print_width
                colAttrs[k] = attrs
        return colAttrs

    def servercursor(self):
        """Open a named server-side cursor for large result sets.

        Returns:
            cursor: A named cursor (server-side) for chunk-based fetching.
        """
        return self.db.execute(self.sqltext, self.sqlparams, cursorname='*', storename=self.storename)

    def serverfetch(self, arraysize=30):
        """Fetch from a server-side cursor in chunks.

        Args:
            arraysize: Number of rows per chunk.

        Returns:
            tuple: ``(cursor, row_generator)`` where the generator yields
            lists of rows in chunks of *arraysize*.
        """
        cursor = self.servercursor()
        cursor.arraysize = arraysize
        rows = cursor.fetchmany()
        return cursor, self._cursorGenerator(cursor, rows)

    def iterfetch(self, arraysize=30):
        """Iterate over rows using a server-side cursor.

        Args:
            arraysize: Number of rows per chunk.

        Yields:
            Row chunks from the server-side cursor.
        """
        for r in self.serverfetch(arraysize=arraysize)[1]:
            yield r

    def _cursorGenerator(self, cursor, firstRows=None):
        """Generator that yields row chunks from a server-side cursor.

        Args:
            cursor: The server-side cursor.
            firstRows: Optional first chunk already fetched.

        Yields:
            list: Chunks of rows until the cursor is exhausted.
        """
        if firstRows:
            yield firstRows
        rows = True
        while rows:
            rows = cursor.fetchmany()
            yield rows
        cursor.close()

    def count(self):
        """Return the number of matching rows without building a selection.

        For plain queries, uses ``COUNT(*)``; for ``GROUP BY`` or
        ``DISTINCT`` queries, counts the resulting groups/rows.

        Returns:
            int: The total row count.
        """
        with self.db.tempEnv(currentImplementation=self.dbtable.dbImplementation):
            compiledQuery = self.compileQuery(count=True)
            cursor = self.db.execute(compiledQuery.get_sqltext(self.db), self.sqlparams,
                                     dbtable=self.dbtable.fullname, storename=self.storename)
        # Multi-store scenario: cursor is a list
        if isinstance(cursor, list):
            n = 0
            for c in cursor:
                # REVIEW: variable ``l`` shadows the builtin ``len`` -- renaming
                # to ``rows`` would improve readability.
                l = c.fetchall()
                # For GROUP BY / DISTINCT: row count = number of groups
                partial = len(l)
                # For plain COUNT(*): single row with gnr_row_count
                if partial == 1 and c.description[0][0] == 'gnr_row_count':
                    partial = l[0][0]
                c.close()
                n += partial
        else:
            l = cursor.fetchall()
            n = len(l)
            if n == 1 and cursor.description[0][0] == 'gnr_row_count':
                n = l[0][0]
            cursor.close()
        return n

    def _next_mangler_key(self, prefix):
        """Generate a unique mangler key for parameter namespacing.

        Each call increments a per-prefix counter stored in the database
        environment, producing keys like ``sq0``, ``sq1``, ``cq0``, etc.

        Args:
            prefix: Short string prefix (e.g. ``'sq'`` for subqueries,
                ``'cq'`` for compound queries).

        Returns:
            str: A unique key like ``'cq0'``, ``'cq1'``, etc.
        """
        env = self.db.currentEnv
        counters = env.setdefault('_mangler_counters', {})
        idx = counters.get(prefix, 0)
        counters[prefix] = idx + 1
        return '%s%d' % (prefix, idx)


# ===========================================================================
# REVIEW NOTES (query.py)
# ===========================================================================
#
# 1. REVIEW: commented-out code in SqlDataResolver.init()
#    Original lines 53-58 contain leftovers from an old ``get_app``
#    mechanism. Can be removed.
#
# 2. REVIEW: commented-out ``resolver()`` method (after setJoinCondition)
#    Reference to a non-existent ``SqlSelectionResolver``. Dead code.
#
# 3. REVIEW: GnrDictRowEncoder defined inside fetchAsJson()
#    Inner class re-created on every call. Extracting to module level
#    would improve readability and performance (marginally).
#
# 4. REVIEW: variable ``l`` in count()
#    Shadows the builtin ``len``. Rename to ``rows`` or ``fetched``.
#
# 5. REVIEW: handlePyColumns -- commented-out line
#    ``#d[field] = handler(d,field=field)`` followed by identical
#    uncommented code. Debug leftover that can be removed.
#
# 6. REVIEW: _dofetch -- inconsistent multi-cursor handling
#    In the ``pyWhere`` branch, ``cursor.close()`` is not called.
#    In the ``isinstance(cursor, list)`` branch, ``index`` is overwritten
#    on each iteration (could be undefined if the list is empty).
#
# 7. REVIEW: ``rels`` and ``params`` computed in __init__ (lines 172-174)
#    The variables ``rels`` and ``params`` are computed via regex but
#    never used afterwards. Evaluate whether they are leftovers from an
#    old validation mechanism.
# ===========================================================================
