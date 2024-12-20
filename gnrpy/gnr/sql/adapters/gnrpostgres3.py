#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrpostgres : Genro postgres db connection.
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
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import re
import select
from collections.abc import Mapping


import psycopg
from psycopg import Cursor, IsolationLevel
from psycopg.rows import no_result
from psycopg import sql

from gnr.core.gnrlist import GnrNamedList
from gnr.sql.adapters._gnrbasepostgresadapter import PostgresSqlDbBaseAdapter
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException

RE_SQL_PARAMS = re.compile(r":(\S\w*)(\W|$)")

class SqlDbAdapter(PostgresSqlDbBaseAdapter):

    def connect(self, storename=None, autoCommit=False, **kw):
        """Return a new connection object: provides cursors accessible by col number or col name
        
        :returns: a new connection object"""
        kwargs = self.dbroot.get_connection_params(storename=storename)
        kwargs.pop('implementation',None)
        # remove None parameters, psycopg can't handle them
        kwargs = dict([(k, v) for k, v in list(kwargs.items()) if v != None])
        if 'port' in kwargs:
            kwargs['port'] = int(kwargs['port'])

        database = kwargs.pop('database', None)
        kwargs['dbname'] = kwargs.get('dbname') or database
        kwargs['autocommit'] = autoCommit
        
        try:
            conn = psycopg.connect(**kwargs)
        except psycopg.OperationalError:
            raise GnrNonExistingDbException(self.dbroot.dbname)
        conn.cursor_factory = GnrDictCursor
        return conn

    def vacuum(self, table='', full=False): #TODO: TEST IT, SEEMS TO LOCK SUBSEQUENT TRANSACTIONS!!!
        """Perform analyze routines on the db"""
        self.dbroot.connection.isolation_level=IsolationLevel.READ_UNCOMMITTED
        if full:
            self.dbroot.execute('VACUUM FULL ANALYZE %s;' % table)
        else:
            self.dbroot.execute('VACUUM ANALYZE %s;' % table)
        self.dbroot.connection.isolation_level=IsolationLevel.READ_COMMITTED
        
    def adaptTupleListSet(self,sql,sqlargs):
        
        for k,v in list(sqlargs.items()):
            if isinstance(v, list) or isinstance(v, set) or isinstance(v,tuple):
                if not isinstance(v,list):
                    v = list(v)
                if len(v)==0:
                    re_pattern = r"""((\"?t\d+)(_t\d+)*\"?.\"?\w+\"?" +)(NOT +)*(IN) *:%s""" %k
                    sql = re.sub(re_pattern,lambda m: 'TRUE' if m.group(4) else 'FALSE',sql,flags=re.I)
                else:
                    
                    def unroll_list(match):
                        sqlargs.pop(k,None)
                        base_name = match.group(2)
                        names_list = []
                        for i, value in enumerate(v):
                            value_name = f"{base_name}_{i}"
                            names_list.append(f':{value_name}')
                            sqlargs[value_name] = value
                        return f"{match.group(1)}({','.join(names_list)})"
                    re_pattern = r'( *IN) *(?::)(%s)'%k
                    sql = re.sub(re_pattern,unroll_list,sql,flags=re.I)
        


        return sql

    def prepareSqlText(self, sqltext, kwargs):
        """Change the format of named arguments in the query from ':argname' to '%(argname)s'.
        Replace the 'REGEXP' operator with '~*'

        :param sql: the sql string to execute
        :param kwargs: the params dict
        :returns: tuple (sql, kwargs)"""
        sqlargs = {}
        sqltext = self.adaptTupleListSet(sqltext,kwargs)
        sqltext = sqltext.replace('{',chr(2)).replace('}',chr(3))
        def subArgs(m):
            key = m.group(1)
            sqlargs[key]=kwargs[key]
            #sqlargs.append(kwargs[key])
            return f'{{{key}}}{m.group(2)} '
        #sql = RE_SQL_PARAMS.sub(r'%(\1)s\2', sql).replace('REGEXP', '~*')
        sqltext = RE_SQL_PARAMS.sub(subArgs, sqltext)
        sqltext= sqltext.replace('REGEXP', '~*')
        
        return sqltext, sqlargs

    def compileSql(self, maintable, columns, distinct='', joins=None, where=None,
                   group_by=None, having=None, order_by=None, limit=None, offset=None, for_update=None,maintable_as=None):
        def _smartappend(x, name, value):
            if value:
                x.append('%s %s' % (name, value))
        maintable_as = maintable_as or 't0'
        result = ['SELECT  %s%s' % (distinct, columns)]
        result.append(' FROM %s AS %s' % (maintable, maintable_as))
        joins = joins or []
        for join in joins:
            result.append('       %s' % join)
        
        _smartappend(result, 'WHERE', where)
        _smartappend(result, 'GROUP BY', group_by)
        _smartappend(result, 'HAVING', having)
        _smartappend(result, 'ORDER BY', order_by)
        _smartappend(result, 'LIMIT', limit)
        _smartappend(result, 'OFFSET', offset)
        if for_update:
            result.append(self._selectForUpdate(maintable_as=maintable_as,mode=for_update))
        
        return ' '.join(result)

    @classmethod
    def _classConnection(cls, host=None, port=None,
                         user=None, password=None):

        kwargs = dict(dbname='template1', host=host, port=port,
                      user=user, password=password, autocommit=True)
        kwargs = dict([(k, v) for k, v in list(kwargs.items()) if v != None])
        conn = psycopg.connect(**kwargs)
        #conn.isolation_level=IsolationLevel.READ_COMMITTED
        return conn
        
    def restore(self, filename,dbname=None):
        from subprocess import call
        dbname = dbname or self.dbroot.dbname
        if filename.endswith('.pgd'):
            call(['pg_restore','--dbname',dbname,'-U',self.dbroot.user,filename])
        else:
            return call(['psql', "dbname=%s user=%s password=%s" % (dbname, self.dbroot.user, self.dbroot.password), '-f', filename])
        
    
    def listen(self, msg, timeout=10, onNotify=None, onTimeout=None):
        """Listen for message 'msg' on the current connection using the Postgres LISTEN - NOTIFY method.
        onTimeout callbacks are executed on every timeout, onNotify on messages.
        Callbacks returns False to stop, or True to continue listening.
        
        :param msg: name of the message to wait for
        :param timeout: seconds to wait for the message
        :param onNotify: function to execute on arrive of message
        :param onTimeout: function to execute on timeout
        """
        self.dbroot.connection.isolation_level=IsolationLevel.READ_UNCOMMITTED
        curs = self.dbroot.execute('LISTEN %s;' % msg)
        listening = True
        conn = curs.connection
        selector = curs
        while listening:
            if select.select([selector], [], [], timeout) == ([], [], []):
                if onTimeout != None:
                    listening = onTimeout()
            else:
                if curs.isready() and onNotify != None:
                    listening = onNotify(conn.notifies.pop())
                
        self.dbroot.connection.isolation_level=IsolationLevel.READ_COMMITTED
        
    def notify(self, msg, autocommit=False):
        """Notify a message to listener processes using the Postgres LISTEN - NOTIFY method.
        
        :param msg: name of the message to notify
        :param autocommit: if False (default) you have to commit transaction, and the message is actually sent on commit"""
        self.dbroot.execute('NOTIFY %s;' % msg)
        if autocommit:
            self.dbroot.commit()

            
    def listElements(self, elType, **kwargs):
        """Get a list of element names
        
        :param elType: one of the following: schemata, tables, columns, views.
        :param kwargs: schema, table
        :returns: list of object names"""
        query = getattr(self, '_list_%s' % elType)()
        try:
            result = self.dbroot.execute(query, kwargs).fetchall()
        except psycopg.OperationalError:
            raise GnrNonExistingDbException(self.dbroot.dbname)
        return [r[0] for r in result]


    def alterColumnSql(self, table, column, dtype):
        return 'ALTER TABLE %s ALTER COLUMN %s TYPE %s  USING %s::%s' % (table, column, dtype,column,dtype)

    def struct_get_schema_info_sql(self):
        return """
            SELECT
                s.schema_name,
                t.table_name,
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.is_nullable,
                c.column_default,
                c.numeric_precision,
                c.numeric_scale
            FROM
                information_schema.schemata s
            LEFT JOIN
                information_schema.tables t
                ON s.schema_name = t.table_schema
            LEFT JOIN
                information_schema.columns c
                ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE
                s.schema_name = ANY(%s)
            ORDER BY
                s.schema_name, t.table_name, c.ordinal_position;
        """

            
    def getColInfo(self, table, schema, column=None):
        """Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        Every other info stored in information_schema.columns is available with the prefix '_pg_'"""
        sql = """SELECT c1.column_name as name,
                        c1.ordinal_position as position, 
                        c1.column_default as default, 
                        c1.is_nullable as notnull, 
                        c1.data_type as dtype, 
                        c1.character_maximum_length as length,
                        *
                      FROM information_schema.columns AS c1
                      WHERE c1.table_schema=:schema 
                      AND c1.table_name=:table 
                      %s
                      ORDER BY position"""
        filtercol = ""
        if column:
            filtercol = "AND column_name=:column"
        columns = self.dbroot.execute(sql % filtercol,
                                      dict(schema=schema,
                                           table=table,
                                           column=column)).fetchall()
        result = []
        for col in columns:
            col = dict(col)
            col = self._filterColInfo(col, '_pg_')
            dtype = col['dtype'] = self.typesDict.get(col['dtype'], 'T') #for unrecognized types default dtype is T
            col['notnull'] = (col['notnull'] == 'NO')
            if dtype == 'N':
                precision, scale = col.get('_pg_numeric_precision'), col.get('_pg_numeric_scale')
                if precision:
                    col['size'] = '%i,%i' % (precision, scale)
            elif dtype == 'A':
                size = col.get('length')
                if size:
                    col['size'] = '0:%i' % size
                else:
                    dtype = col['dtype'] = 'T'
            elif dtype == 'C':
                col['size'] = str(col.get('length'))
            result.append(col)
        if column:
            result = result[0]
        return result

def gnrdict_row(cursor,):
    desc = cursor.description
    if desc is None:
        return no_result
    def _gnrdict_row(values):
        if values is None:
            values = [None] * len(desc)
        return GnrNamedList(cursor.index, values=values)
    return _gnrdict_row


class GnrDictCursor(Cursor):
    """Base class for all dict-like cursors."""

    def __init__(self, *args, **kwargs):
        row_factory = gnrdict_row
        super(GnrDictCursor, self).__init__(*args, **kwargs)
        self._query_executed = 0
        self.row_factory = row_factory

    def fetchone(self):
        if self._query_executed:
            self._build_index()
        return super(GnrDictCursor, self).fetchone()

    def fetchmany(self, size=None):
        if size == None:
            res = super(GnrDictCursor, self).fetchmany()
        else:
            res = super(GnrDictCursor, self).fetchmany(size)
        if self._query_executed:
            self._build_index()
        return res

    def fetchall(self):
        if self._query_executed:
            self._build_index()
        return super(GnrDictCursor, self).fetchall()

    def __next__(self):
        if self._query_executed:
            self._build_index()
        res = super(GnrDictCursor, self).fetchone()
        if res is None:
            raise StopIteration()
        return res

    def execute(self, query, params=None, async_=0):
        self.index = {}
        self._query_executed = 1

        if isinstance(params, Mapping):
            query = sql.SQL(query).format(**params).as_string(self.connection)
            query = query.replace(chr(2),'{').replace(chr(3),'}')
        else:
            q_params = params
            if params is not None:
                q_params = [isinstance(x, tuple) and list(x) or x for x in params]
            return super(GnrDictCursor, self).execute(query, q_params)

        return super(GnrDictCursor, self).execute(query)
    
    def setConstraintsDeferred(self):
        self.execute("SET CONSTRAINTS all DEFERRED;")

    def callproc(self, procname, vars=None):
        self.index = {}
        self._query_executed = 1
        return super(GnrDictCursor, self).callproc(procname, vars)

    def _build_index(self):
        if self._query_executed == 1 and self.description:
            i = 0
            for desc_rec in self.description:
                desc = desc_rec[0]
                if desc not in self.index:
                    self.index[desc] = i
                    i+=1
            self._query_executed = 0
    


