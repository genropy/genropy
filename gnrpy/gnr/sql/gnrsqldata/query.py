#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_query : SQL query builder and data resolver
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
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

import re
import json
import datetime
from collections import OrderedDict

from gnr.core.gnrbag import Bag, BagResolver
from gnr.sql.gnrsqldata.compiler import SqlQueryCompiler
from gnr.sql.gnrsqldata.selection import SqlSelection


class SqlDataResolver(BagResolver):
    """TODO"""
    classKwargs = {'cacheTime': 0,
                   'readOnly': True,
                   'db': None}
    classArgs = ['tablename']

    def resolverSerialize(self):
        """TODO"""
        attr = {}
        attr['resolvermodule'] = self.__class__.__module__
        attr['resolverclass'] = self.__class__.__name__
        attr['args'] = list(self._initArgs)
        attr['kwargs'] = dict(self._initKwargs)
        attr['kwargs'].pop('db')
        attr['kwargs']['_serialized_app_db'] = 'maindb'
        return attr

    def init(self):
        """TODO"""
    ##raise str(self._initKwargs)
    #if 'get_app' in self._initKwargs:
    #self.db = self._initKwargs['get_app'].db
        #if '.' in self.table:
        #    self.package, self.table = self.table.split('.')
        #self.tblstruct = self.dbroot.package(self.package).table(self.table)
        self.dbtable = self.db.table(self.tablename)
        self.onCreate()

    def onCreate(self):
        """TODO"""
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
                 **kwargs):
        self.dbtable = dbtable
        self.sqlparams = sqlparams or {}
        columns = columns or '*'
        self.subtable = subtable
        self.joinConditions = joinConditions or {}
        self.sqlContextName = sqlContextName
        self.relationDict = relationDict or {}
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

    def setJoinCondition(self, target_fld=None, from_fld=None, relation=None,condition=None, one_one=False, **kwargs):
        """TODO

        :param target_fld: TODO
        :param from_fld: TODO
        :param condition: set a :ref:`sql_condition` for the join
        :param one_one: boolean. TODO
        """

        cond = dict(condition=condition, one_one=one_one, params=kwargs)
        self.joinConditions[relation or '%s_%s' % (target_fld.replace('.', '_'), from_fld.replace('.', '_'))] = cond

        #def resolver(self, mode='bag'):
        #return SqlSelectionResolver(self.dbtable.fullname,  db=self.db, mode=mode,
        #relationDict=self.relationDict, sqlparams=self.sqlparams,
        #joinConditions=self.joinConditions, bagFields=self.bagFields, **self.querypars)

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
                                locale=self.locale).compiledQuery(count=count,
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

    def handlePyColumns(self,data):
        if not self.compiled.pyColumns:
            return
        pcdict = dict(self.compiled.pyColumns)
        for field in  list(self.dbtable.model.virtual_columns.keys()):
            if not field in pcdict:
                continue
            handler = pcdict[field]
            if handler:
                for d in data:
                    #d[field] = handler(d,field=field)
                    result = handler(d,field=field)
                    d[field] = result

    def handleBagColumns(self,data):
        if not self.compiled.evaluateBagColumns:
            return
        for d in data:
            for field,separateCols in self.compiled.evaluateBagColumns:
                val = Bag(d[field])
                if separateCols:
                    for k,v in val.getLeaves():
                        d['{}_{}'.format(field,k.replace('.','_'))] = v
                    d[field] = None
                else:
                    d[field] = val


    def fetchPkeys(self):
        fetch = self.fetch()
        pkeyfield = self.dbtable.pkey
        return [r[pkeyfield] for r in fetch]

    def fetchAsJson(self, key=None):

        fetch = self.fetch()
        key = key or self.dbtable.pkey
        class GnrDictRowEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                return str(obj)
        return json.dumps([ {k: v for k, v in r.items()} for r in fetch], cls=GnrDictRowEncoder)

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
        return (self.sqltext, self.sqlparams)

    def _dofetch(self, pyWhere=None):
        """private: called by _get_selection"""
        if pyWhere:
            cursor, rowset = self.serverfetch(arraysize=100)
            index = cursor.index
            data = []
            for rows in rowset:
                data.extend([r for r in rows if pyWhere(r)])
        else:
            cursor = self.cursor()
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
        """Get a cursor on dbserver"""
        return self.db.execute(self.sqltext, self.sqlparams, cursorname='*',storename=self.storename)

    def serverfetch(self, arraysize=30):
        """Get fetch of the :meth:`servercursor()` method.

        :param arraysize: TODO"""
        cursor = self.servercursor()
        cursor.arraysize = arraysize
        rows = cursor.fetchmany()
        return cursor, self._cursorGenerator(cursor, rows)

    def iterfetch(self, arraysize=30):
        """TODO

        :param arraysize: TODO"""
        for r in self.serverfetch(arraysize=arraysize)[1]:
            yield r

    def _cursorGenerator(self, cursor, firstRows=None):
        if firstRows:
            yield firstRows
        rows = True
        while rows:
            rows = cursor.fetchmany()
            yield rows
        cursor.close()

    def count(self):
        """Return rowcount. It does not save a selection"""
        with self.db.tempEnv(currentImplementation=self.dbtable.dbImplementation):
            compiledQuery = self.compileQuery(count=True)
            cursor = self.db.execute(compiledQuery.get_sqltext(self.db), self.sqlparams, dbtable=self.dbtable.fullname,storename=self.storename)
        if isinstance(cursor, list):
            n = 0
            for c in cursor:
                l = c.fetchall()
                partial = len(l) # for group or distinct query select -1 for each group
                if partial == 1 and c.description[0][0] == 'gnr_row_count': # for plain query select count(*)
                    partial = l[0][0]
                c.close()
                n+=partial
        else:
            l = cursor.fetchall()
            n = len(l) # for group or distinct query select -1 for each group
            if n == 1 and cursor.description[0][0] == 'gnr_row_count': # for plain query select count(*)
                n = l[0][0]
            cursor.close()
        return n
