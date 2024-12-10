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


try:
    import psycopg2
except ImportError:
    try:
        from psycopg2cffi import compat
        compat.register()
    except ImportError:
        try:
            from psycopg2ct import compat
            compat.register()
        except ImportError:
            pass
    import psycopg2

from psycopg2.extensions import cursor as _cursor
from psycopg2.extensions import connection as _connection
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED

from gnr.sql.adapters._gnrbasepostgresadapter import PostgresSqlDbBaseAdapter
from gnr.sql.adapters._gnrbaseadapter import GnrDictRow, DbAdapterException
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException


RE_SQL_PARAMS = re.compile(r":(\S\w*)(\W|$)")

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)


class SqlDbAdapter(PostgresSqlDbBaseAdapter):
    
    def connect(self, storename=None, autoCommit=False):
        """Return a new connection object: provides cursors accessible by col number or col name

        :returns: a new connection object"""
        kwargs = self.dbroot.get_connection_params(storename=storename)
        kwargs.pop('implementation',None)
        #kwargs = dict(host=dbroot.host, database=dbroot.dbname, user=dbroot.user, password=dbroot.password, port=dbroot.port)
        kwargs = dict(
                [(k, v) for k, v in list(kwargs.items()) if v != None]) # remove None parameters, psycopg can't handle them
        kwargs[
        'connection_factory'] = GnrDictConnection # build a DictConnection: provides cursors accessible by col number or col name
        self._lock.acquire()
        if 'port' in kwargs:
            kwargs['port'] = int(kwargs['port'])
        try:
            conn = psycopg2.connect(**kwargs)
            if autoCommit:
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        except psycopg2.OperationalError:
            raise GnrNonExistingDbException(self.dbroot.dbname)
        finally:
            self._lock.release()
        return conn

    def adaptTupleListSet(self,sql,sqlargs):
        for k,v in list(sqlargs.items()):
            if isinstance(v, list) or isinstance(v, set) or isinstance(v,tuple):
                if not isinstance(v,tuple):
                    sqlargs[k] = tuple(v)
                if len(v)==0:
                    re_pattern = r"""((\"?t\d+)(_t\d+)*\"?.\"?\w+\"?" +)(NOT +)*(IN) *:%s""" %k
                    sql = re.sub(re_pattern,lambda m: 'TRUE' if m.group(4) else 'FALSE',sql,flags=re.I)
        return sql

    def prepareSqlText(self, sql, kwargs):
        """Change the format of named arguments in the query from ':argname' to '%(argname)s'.
        Replace the 'REGEXP' operator with '~*'.

        :param sql: the sql string to execute.
        :param kwargs: the params dict
        :returns: tuple (sql, kwargs)
        """
        sql = self.adaptTupleListSet(sql,kwargs)
        return RE_SQL_PARAMS.sub(r'%(\1)s\2', sql).replace('REGEXP', '~*'), kwargs


    def _managerConnection(self):
        return self._classConnection(host=self.dbroot.host, 
            port=self.dbroot.port,
            user=self.dbroot.user, 
            password=self.dbroot.password)

    @classmethod
    def _classConnection(cls, host=None, port=None,
        user=None, password=None):
        kwargs = dict(host=host, database='template1', user=user,
                    password=password, port=port)
        kwargs = dict([(k, v) for k, v in list(kwargs.items()) if v != None])
        conn = psycopg2.connect(**kwargs)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    @classmethod
    def _createDb(cls, dbname=None, host=None, port=None,
        user=None, password=None, encoding='unicode'):
        conn = cls._classConnection(host=host, user=user,
            password=password, port=port)
        curs = conn.cursor()
        try:
            curs.execute(cls.createDbSql(dbname, encoding))
            conn.commit()
        except:
            raise DbAdapterException(f"Could not create database {dbname}")
        finally:
            curs.close()
            conn.close()
            curs = None
            conn = None

    def createDb(self, dbname=None, encoding='unicode'):
        if not dbname:
            dbname = self.dbroot.get_dbname()
        self._createDb(dbname=dbname, host=self.dbroot.host, port=self.dbroot.port,
            user=self.dbroot.user, password=self.dbroot.password)

    @classmethod
    def createDbSql(cls, dbname, encoding):
        return f"""CREATE DATABASE "{dbname}" ENCODING '{encoding}';"""


    @classmethod
    def _dropDb(cls, dbname=None, host=None, port=None,
        user=None, password=None):
        conn = cls._classConnection(host=host, user=user,
            password=password, port=port)
        curs = conn.cursor()
        curs.execute(f'DROP DATABASE IF EXISTS "{dbname}";')
        curs.close()
        conn.close()
        curs = None
        conn = None

    def dropDb(self, dbname=None):
        self._dropDb(dbname=dbname, host=self.dbroot.host, port=self.dbroot.port,
            user=self.dbroot.user, password=self.dbroot.password)




    @classmethod
    def _restore_dump(cls, filename=None, dbname=None, host=None,
        port=None, user=None, password=None):
        from subprocess import call
        from multiprocessing import cpu_count
        host = host or 'localhost'
        port = port or '5432'
        if filename.endswith('.pgd'):
            call(['pg_restore', f"""--dbname=postgresql://{user}:{password}@{host}:{port}/{dbname}""" , '-j', str(cpu_count()),filename])
        else:
            return call(['psql', f"postgresql://{user}:{password}@{host}:{port}/{dbname}", '-f', filename])

    def restore(self, filename,dbname=None):
        self._restore_dump(filename=filename, 
            dbname=dbname or self.dbroot.dbname, host=self.dbroot.host,
            port=self.dbroot.port, user=self.dbroot.user,
            password=self.dbroot.password)


    def listen(self, msg, timeout=10, onNotify=None, onTimeout=None):
        """Listen for message 'msg' on the current connection using the Postgres LISTEN - NOTIFY method.
        onTimeout callbacks are executed on every timeout, onNotify on messages.
        Callbacks returns False to stop, or True to continue listening.

        :param msg: name of the message to wait for
        :param timeout: seconds to wait for the message
        :param onNotify: function to execute on arrive of message
        :param onTimeout: function to execute on timeout
        """
        self.dbroot.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        curs = self.dbroot.execute('LISTEN %s;' % msg)
        listening = True
        conn = curs.connection
        if psycopg2.__version__.startswith('2.0'):
            selector = curs
            #pg_go = curs.isready
        else:
            selector = conn
            #pg_go = conn.poll
        while listening:
            if select.select([selector], [], [], timeout) == ([], [], []):
                if onTimeout != None:
                    listening = onTimeout()
            else:
                if psycopg2.__version__.startswith('2.0'):
                    if curs.isready() and onNotify != None:
                        listening = onNotify(conn.notifies.pop())
                else:
                    conn.poll()
                    while conn.notifies and listening and onNotify != None:
                        listening = onNotify(conn.notifies.pop())
        self.dbroot.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)

    def notify(self, msg, autocommit=False):
        """Notify a message to listener processes using the Postgres LISTEN - NOTIFY method.

        :param msg: name of the message to notify
        :param autocommit: if False (default) you have to commit transaction, and the message is actually sent on commit"""
        self.dbroot.execute('NOTIFY %s;' % msg)
        if autocommit:
            self.dbroot.commit()


    def listElements(self, elType, comment=None, **kwargs):
        """Get a list of element names

        :param elType: one of the following: schemata, tables, columns, views.
        :param kwargs: schema, table
        :returns: list of object names"""
        query = getattr(self, '_list_%s' % elType)()
        try:
            result = self.dbroot.execute(query, kwargs).fetchall()
        except psycopg2.OperationalError:
            raise GnrNonExistingDbException(self.dbroot.dbname)
        if comment:
            return [(r[0],None) for r in result]
        return [r[0] for r in result]

    def alterColumnSql(self, table=None, column=None, dtype=None):
        if not table:
            return 'ALTER COLUMN %s TYPE %s  USING %s::%s' % (column, dtype,column,dtype)
        return 'ALTER TABLE %s ALTER COLUMN %s TYPE %s  USING %s::%s' % (table, column, dtype,column,dtype)
    



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
        iterator = self.columnAdapter(columns)
        return iterator if not column else next(iterator)

    def columnAdapter(self,columns):
        """
        Create adjustments for `columns` datatypes
        related to the specific driver
        """
        for col in columns:
            col = dict(col)
            col = self._filterColInfo(col, '_pg_')
            col['notnull'] = (col['notnull'] == 'NO')
            dtype = col['dtype'] = self.typesDict.get(col['dtype'], 'T') #for unrecognized types default dtype is T
            if dtype == 'N':
                precision, scale = col.get('_pg_numeric_precision'), col.get('_pg_numeric_scale')
                if precision:
                    col['size'] = f'{precision},{scale}'
            elif dtype == 'A':
                size = col.pop('length',None)
                if size:
                    col['size'] = f'0:{size}'
                else:
                    dtype = col['dtype'] = 'T'
            elif dtype == 'C':
                col['size'] = str(col.get('length'))
            yield col


    
    #def struct_create_event_trigger_sql(self, trigger_name, event, function_name, when=None, tags=None):
    #    """
    #    Generates the SQL to create an event trigger.
    #    """
    #    # WHEN clause
    #    when_clause = f"WHEN TAG IN ({', '.join(f"'{tag}'" for tag in tags)})" if tags else ""
    #    
    #    # Compose the final SQL statement
    #    sql = f"""
    #    CREATE EVENT TRIGGER {trigger_name}
    #    ON {event}
    #    EXECUTE FUNCTION {function_name}
    #    {when_clause};
    #    """
    #    
    #    # Return a clean, single-line SQL string
    #    return " ".join(sql.split())
    
class GnrDictConnection(_connection):
    """A connection that uses DictCursor automatically."""


    def __init__(self, *args, **kwargs):
        super(GnrDictConnection, self).__init__(*args, **kwargs)

    def cursor(self, name=None):
        if name:
            cur = super(GnrDictConnection, self).cursor(name, cursor_factory=GnrDictCursor)
        else:
            cur = super(GnrDictConnection, self).cursor(cursor_factory=GnrDictCursor)
        return cur

class GnrDictCursor(_cursor):
    """Base class for all dict-like cursors."""

    def __init__(self, *args, **kwargs):
        row_factory = GnrDictRow
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

    def execute(self, query, vars=None, async_=0):
        self.index = {}
        self._query_executed = 1
        if psycopg2.__version__.startswith('2.0'):
            return super(GnrDictCursor, self).execute(query, vars, async_)
        return super(GnrDictCursor, self).execute(query, vars)

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


