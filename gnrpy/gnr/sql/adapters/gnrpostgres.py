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
from collections import defaultdict

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

from gnr.sql.adapters._gnrbaseadapter import GnrDictRow, GnrWhereTranslator, DbAdapterException
from gnr.sql.adapters._gnrbaseadapter import SqlDbAdapter as SqlDbBaseAdapter
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException
DEFAULT_INDEX_METHOD = 'btree'
RE_SQL_PARAMS = re.compile(r":(\S\w*)(\W|$)")
#IN_TO_ANY = re.compile(r'([$]\w+|[@][\w|@|.]+)\s*(NOT)?\s*(IN ([:]\w+))')
#IN_TO_ANY = re.compile(r'(?P<what>\w+.\w+)\s*(?P<not>NOT)?\s*(?P<inblock>IN\s*(?P<value>[:]\w+))',re.IGNORECASE)

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
import threading



class SqlDbAdapter(SqlDbBaseAdapter):
    typesDict = {'character varying': 'A', 'character': 'C', 'text': 'T',
                 'boolean': 'B', 'date': 'D',
                 'time without time zone': 'H',
                 'time with time zone': 'HZ',
                 'timestamp without time zone': 'DH',
                 'timestamp with time zone': 'DHZ',
                  'numeric': 'N', 'money': 'M',
                 'integer': 'I', 'bigint': 'L', 
                 'smallint': 'I', 
                 'double precision': 'R', 
                 'real': 'R',
                'bytea': 'O',
                'tsvector':'TSV',
                'vector':'VEC',
                'jsonb':'jsonb'}

    revTypesDict = {'A': 'character varying', 'T': 'text', 'C': 'character',
                    'X': 'text', 'P': 'text', 'Z': 'text', 'N': 'numeric', 'M': 'money',
                    'B': 'boolean', 'D': 'date',
                    'H': 'time without time zone',
                    'HZ': 'time with time zone',
                    'DH': 'timestamp without time zone',
                    'DHZ': 'timestamp with time zone',
                    'I': 'integer', 'L': 'bigint', 'R': 'real',
                    'serial': 'serial8', 'O': 'bytea','jsonb':'jsonb',
                    'TSV':'tsvector','VEC':'vector'}

    _lock = threading.Lock()
    paramstyle = 'pyformat'

    def __init__(self, *args, **kwargs):
        #self._lock = threading.Lock()

        super(SqlDbAdapter, self).__init__(*args, **kwargs)

    def defaultMainSchema(self):
        return 'public'

    def connect(self, storename=None,autoCommit=False):
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

    @classmethod
    def adaptSqlName(cls, name):
        return '"%s"' %name


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

    def lockTable(self, dbtable, mode='ACCESS EXCLUSIVE', nowait=False):
        if nowait:
            nowait = 'NO WAIT'
        else:
            nowait = ''
        sql = "LOCK %s IN %s MODE %s;" % (dbtable.model.sqlfullname, mode, nowait)
        self.dbroot.execute(sql)

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


    def dropTable(self, dbtable,cascade=False):
        """Drop table"""
        command = 'DROP TABLE IF EXISTS %s;'
        if cascade:
            command = 'DROP TABLE %s CASCADE;'
        tablename = dbtable if isinstance(dbtable, str) else dbtable.model.sqlfullname
        self.dbroot.execute(command % tablename)

    def dump(self, filename,dbname=None,excluded_schemas=None, options=None,**kwargs):
        """Dump an existing database
        :param filename: db name
        :param excluded_schemas: excluded schemas
        :param filename: dump options"""
        available_parameters = dict(
            data_only='-a', clean='-c', create='-C', no_owner='-O',
            schema_only='-s', no_privileges='-x', if_exists='--if-exists',
            quote_all_identifiers='--quote-all-identifiers',
            compress = '--compress='
        )
        from subprocess import call
        dbname = dbname or self.dbroot.dbname
        pars = {'dbname':dbname,
                'user':self.dbroot.user,
                'password':self.dbroot.password,
                'host':self.dbroot.host or 'localhost',
                'port':self.dbroot.port or '5432'}
        excluded_schemas = excluded_schemas or []
        options = options or Bag()
        dump_options = []
        for excluded_schema in excluded_schemas:
            dump_options.append('-N')
            dump_options.append(excluded_schema)
        if options['plain_text']:
            dump_options.append('-Fp')
            file_extension = '.sql'
        else:
            dump_options.append('-Fc')
            file_extension = '.pgd'
        for parameter_name, parameter_label in list(available_parameters.items()):
            parameter_value = options[parameter_name]
            if parameter_value:
                if parameter_label.endswith('='):
                    parameter_value = '%s%s'%(parameter_label,parameter_value)
                else:
                    parameter_value = parameter_label
                dump_options.append(parameter_value)
        if not filename.endswith(file_extension):
            filename = '%s%s' % (filename, file_extension)
        #args = ['pg_dump', dbname, '-U', self.dbroot.user, '-f', filename]+extras
        args = ['pg_dump',
            '--dbname=postgresql://%(user)s:%(password)s@%(host)s:%(port)s/%(dbname)s' %pars,
            '-f', filename]+dump_options
        callresult = call(args)
        return filename

    def restore(self, filename,dbname=None):
        """-- IMPLEMENT THIS --
        Drop an existing database

        :param filename: db name"""
        self.restore_dump(filename=filename, 
            dbname=dbname or self.dbroot.dbname, host=self.dbroot.host,
            port=self.dbroot.port, user=self.dbroot.user,
            password=self.dbroot.password)

    @classmethod
    def restore_dump(cls, filename=None, dbname=None, host=None,
        port=None, user=None, password=None):
        from subprocess import call
        from multiprocessing import cpu_count
        host = host or 'localhost'
        port = port or '5432'
        if filename.endswith('.pgd'):
            call(['pg_restore', f"""--dbname=postgresql://{user}:{password}@{host}:{port}/{dbname}""" , '-j', str(cpu_count()),filename])
        else:
            return call(['psql', f"postgresql://{user}:{password}@{host}:{port}/{dbname}", '-f', filename])

    def importRemoteDb(self, source_dbname,source_ssh_host=None,source_ssh_user=None,
                                source_dbuser=None,source_dbpassword=None,
                                source_dbhost=None,source_dbport=None,
                                dest_dbname=None):
        dest_dbname = dest_dbname or source_dbname
        import subprocess
        self.createDb(dbname=dest_dbname, encoding='unicode')
        srcdb = dict(user=source_dbuser or 'postgres',dbname=source_dbname,
                        password=source_dbpassword or 'postgres',
                        host = source_dbhost or 'localhost',
                        port = source_dbport or '5432')
        ps = subprocess.Popen((
            'ssh','%s@%s' %(source_ssh_user,source_ssh_host),
            '-C', "pg_dump --dbname=postgresql://%(user)s:%(password)s@%(host)s:%(port)s/%(dbname)s" %srcdb
            ),stdout=subprocess.PIPE)
        destdb = {'dbname':dest_dbname,
                'user':self.dbroot.user,
                'password':self.dbroot.password,
                'host':self.dbroot.host or 'localhost',
                'port':self.dbroot.port or '5432'
                }
        output = subprocess.check_output(('psql',
                                        'dbname=%(dbname)s user=%(user)s password=%(password)s host=%(host)s port=%(port)s' %destdb),
                                        stdin=ps.stdout)
        ps.wait()


    def listRemoteDatabases(self,source_ssh_host=None,source_ssh_user=None,
                                source_dbuser=None,source_dbpassword=None,
                                source_dbhost=None,source_dbport=None):
        import subprocess
        srcdb = dict(user=source_dbuser or 'postgres',
                        password=source_dbpassword or 'postgres',
                        host = source_dbhost or 'localhost',
                        port = source_dbport or '5432')
        ps = subprocess.Popen((
            'ssh','%s@%s' %(source_ssh_user,source_ssh_host),
            '-C', 'psql','-l','-t', "user=%(user)s password=%(password)s host=%(host)s port=%(port)s" %srcdb
            ),stdout=subprocess.PIPE)
        res = ps.stdout.read()
        ps.wait()
        result = []
        if not res:
            return []
        for dbr in res.split('\n'):
            dbname = dbr.split('|')[0].strip()
            if dbname:
                result.append(dbname)
        return result


    def createTableAs(self, sqltable, query, sqlparams):
        self.dbroot.execute("CREATE TABLE %s WITH OIDS AS %s;" % (sqltable, query), sqlparams)

    def vacuum(self, table='', full=False): #TODO: TEST IT, SEEMS TO LOCK SUBSEQUENT TRANSACTIONS!!!
        """Perform analyze routines on the db"""
        self.dbroot.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        if full:
            self.dbroot.execute('VACUUM FULL ANALYZE %s;' % table)
        else:
            self.dbroot.execute('VACUUM ANALYZE %s;' % table)
        self.dbroot.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)

    def setLocale(self,locale):
        pass
        #if not locale:
        #    return
        #if len(locale)==2:
        #    locale = '%s_%s' %(locale.lower(),locale.upper())
        #self.dbroot.execute("SET lc_time = '%s' " %locale.replace('-','_'))

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

    def dbExists(self, dbname):
        conn = self._managerConnection()
        curs = conn.cursor()
        curs.execute(self._list_databases())
        dbnames = [dbn[0] for dbn in curs.fetchall()]
        curs.close()
        conn.close()
        curs = None
        conn = None
        return dbname in dbnames

    def _list_databases(self):
        return 'SELECT datname FROM pg_catalog.pg_database;'

    def _list_schemata(self):
        return """SELECT schema_name FROM information_schema.schemata
              WHERE schema_name != 'information_schema' AND schema_name NOT LIKE 'pg_%%'"""

    def _list_tables(self):
        return """SELECT table_name FROM information_schema.tables
                                    WHERE table_schema=:schema"""

    def _list_views(self):
        return """SELECT table_name FROM information_schema.views WHERE table_schema=:schema"""

    def _list_extensions(self):
        return """SELECT name FROM pg_available_extensions;"""

    def _list_enabled_extensions(self):
        return """SELECT name FROM pg_available_extensions where installed_version IS NOT NULL;"""

    def _list_columns(self):
        return """SELECT column_name as col
                                  FROM information_schema.columns
                                  WHERE table_schema=:schema
                                  AND table_name=:table
                                  ORDER BY ordinal_position"""


    def dropExtension(self, extensions):
        """Disable a specific db extension"""
        extensions = extensions.split(',')
        enabled = self.listElements('enabled_extensions')
        commit = False
        for extension in extensions:
            if extension in enabled:
                self.dbroot.execute(self.dropExtensionSql(extension))
                commit = True
        return commit

    def createExtension(self, extensions):
        """Enable a specific db extension"""
        extensions = extensions.split(',')
        enabled = self.listElements('enabled_extensions')
        commit = False
        for extension in extensions:
            if not extension in enabled:
                self.dbroot.execute(self.createExtensionSql(extension))
                commit = True
        return commit

    def createExtensionSql(self,extension):
        return """CREATE extension %s;""" %extension

    def dropExtensionSql(self,extension):
        return """DROP extension IF EXISTS %s;""" %extension

    def relations(self):
        """Get a list of all relations in the db.
        Each element of the list is a list (or tuple) with this elements:
        [foreign_constraint_name, many_schema, many_tbl, [many_col, ...], unique_constraint_name, one_schema, one_tbl, [one_col, ...]]
        @return: list of relation's details
        """
        sql = """SELECT r.constraint_name AS ref,
                c1.table_schema AS ref_schema,
                c1.table_name AS ref_tbl,
                mcols.column_name AS ref_col,
                r.unique_constraint_name AS un_ref,
                c2.table_schema AS un_schema,
                c2.table_name AS un_tbl,
                ucols.column_name AS un_col,
                r.update_rule AS upd_rule,
                r.delete_rule AS del_rule,
                c1.initially_deferred AS init_defer

                FROM information_schema.referential_constraints AS r
                        JOIN information_schema.table_constraints AS c1
                                ON c1.constraint_catalog = r.constraint_catalog
                                        AND c1.constraint_schema = r.constraint_schema
                                        AND c1.constraint_name = r.constraint_name
                        JOIN information_schema.table_constraints AS c2
                                ON c2.constraint_catalog = r.unique_constraint_catalog
                                        AND c2.constraint_schema = r.unique_constraint_schema
                                        AND c2.constraint_name = r.unique_constraint_name
                        JOIN information_schema.key_column_usage as mcols
                                ON mcols.constraint_schema = r.constraint_schema
                                        AND mcols.constraint_name= r.constraint_name
                        JOIN information_schema.key_column_usage as ucols
                                ON ucols.constraint_schema = r.unique_constraint_schema
                                        AND ucols.constraint_name= r.unique_constraint_name
                                        """
        ref_constraints = self.dbroot.execute(sql).fetchall()
        ref_dict = {}
        for (
        ref, schema, tbl, col, un_ref, un_schema, un_tbl, un_col, upd_rule, del_rule, init_defer) in ref_constraints:
            r = ref_dict.get(ref, None)
            if r:
                if not col in r[3]:
                    r[3].append(col)
                if not un_col in r[7]:
                    r[7].append(un_col)
            else:
                ref_dict[ref] = [ref, schema, tbl, [col], un_ref, un_schema, un_tbl, [un_col], upd_rule, del_rule,
                                 init_defer]
        return list(ref_dict.values())

    def alterColumnSql(self, table=None, column=None, dtype=None):
        if not table:
            return 'ALTER COLUMN %s TYPE %s  USING %s::%s' % (column, dtype,column,dtype)
        return 'ALTER TABLE %s ALTER COLUMN %s TYPE %s  USING %s::%s' % (table, column, dtype,column,dtype)
    


    def getPkey(self, table, schema):
        """:param table: the :ref:`database table <table>` name, in the form ``packageName.tableName``
                      (packageName is the name of the :ref:`package <packages>` to which the table
                      belongs to)
        :param schema: schema name
        :return: list of columns wich are the primary key for the table"""
        sql = """SELECT k.column_name        AS col
                FROM   information_schema.key_column_usage      AS k
                JOIN   information_schema.table_constraints     AS c
                ON     c.constraint_catalog = k.constraint_catalog
                AND    c.constraint_schema  = k.constraint_schema
                AND    c.constraint_name    = k.constraint_name
                WHERE  k.table_schema       =:schema
                AND    k.table_name         =:table
                AND    c.constraint_type    ='PRIMARY KEY'
                ORDER BY k.ordinal_position"""
        return [r['col'] for r in self.dbroot.execute(sql, dict(schema=schema, table=table)).fetchall()]

    def getIndexesForTable(self, table, schema):
        """Get a (list of) dict containing details about all the indexes of a table.
        Each dict has those info: name, primary (bool), unique (bool), columns (comma separated string)

        :param table: the :ref:`database table <table>` name, in the form ``packageName.tableName``
                      (packageName is the name of the :ref:`package <packages>` to which the table
                      belongs to)
        :param schema: schema name
        :returns: list of index infos"""
        sql = """SELECT indcls.relname AS name, indisunique AS unique, indisprimary AS primary, indkey AS columns
                    FROM pg_index
               LEFT JOIN pg_class AS indcls ON indexrelid=indcls.oid
               LEFT JOIN pg_class AS tblcls ON indrelid=tblcls.oid
               LEFT JOIN pg_namespace ON pg_namespace.oid=tblcls.relnamespace
                   WHERE nspname=:schema AND tblcls.relname=:table;"""
        indexes = self.dbroot.execute(sql, dict(schema=schema, table=table)).fetchall()
        return indexes

    def getTableConstraints(self, table=None, schema=None):
        """Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        Every other info stored in information_schema.columns is available with the prefix '_pg_'"""
        sql = """SELECT constraint_type,column_name,tc.table_name,tc.table_schema,tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.constraint_column_usage AS cu
                ON cu.constraint_name=tc.constraint_name
                WHERE constraint_type='UNIQUE'
                %s%s;"""
        filtertable = ""
        if table:
            filtertable = " AND tc.table_name=:table"
        filterschema = ""
        if schema:
            filterschema = " AND tc.table_schema=:schema"
        result = self.dbroot.execute(sql % (filtertable,filterschema),
                                      dict(schema=schema,
                                           table=table)).fetchall()

        res_bag = Bag()
        for row in result:
            row=dict(row)
            res_bag.setItem('%(table_schema)s.%(table_name)s.%(column_name)s'%row,row['constraint_name'])
        return res_bag

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

    def getWhereTranslator(self):
        return GnrWhereTranslatorPG(self.dbroot)

    def unaccentFormula(self, field):
        return 'unaccent({prefix}{field})'.format(field=field,
                                                  prefix = '' if field[0] in ('@','$') else '$')

    def struct_auto_extension_attributes(self):
        return ['unaccent']

    def struct_table_fullname_sql(self,schema_name,table_name):
        return  f'"{schema_name}"."{table_name}"'
    
    def struct_drop_table_pkey_sql(self,schema_name,table_name):
        sqltablename = self.struct_table_fullname_sql(schema_name,table_name)
        return f"ALTER TABLE {sqltablename} DROP CONSTRAINT IF EXISTS {table_name}_pkey;"

    def struct_add_table_pkey_sql(self,schema_name,table_name,pkeys):
        sqltablename = self.struct_table_fullname_sql(schema_name,table_name)
        return f'ALTER TABLE {sqltablename} ADD PRIMARY KEY ({pkeys});'

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
                s.schema_name IN %s
            ORDER BY
                s.schema_name, t.table_name, c.ordinal_position;
        """
    
    def struct_get_schema_info(self, schemas=None):
        """
        Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        Every other info stored in information_schema.columns is available with the prefix '_pg_'.
        """
        columns = self.raw_fetch(self.struct_get_schema_info_sql(), (tuple(schemas),))
    
        for schema_name, table_name, \
            column_name, data_type, \
            char_max_length, is_nullable, column_default, \
            numeric_precision, numeric_scale in columns:
            
            col = dict(
                schema_name=schema_name,
                table_name=table_name,
                name=column_name,
                dtype=data_type,
                length=char_max_length,
                is_nullable=is_nullable,
                sqldefault=column_default,
                numeric_precision=numeric_precision,
                numeric_scale=numeric_scale
            )
            col = self._filterColInfo(col, '_pg_')
            if col['sqldefault'] and col['sqldefault'].startswith('nextval('):
                col['_pg_default'] = col.pop('sqldefault')
            dtype = col['dtype'] = self.typesDict.get(col['dtype'], 'T')  # Default 'T' per tipi non riconosciuti
            if dtype == 'N':
                precision = col.pop('_pg_numeric_precision', None)
                scale = col.pop('_pg_numeric_scale', None)
                if precision is not None and scale is not None:
                    col['size'] = f"{precision},{scale}"
                elif precision is not None:  # Solo precisione
                    col['size'] = f"{precision}"
            
            # Gestione del tipo ARRAY
            elif dtype == 'A':
                size = col.pop('length', None)
                if size:
                    col['size'] = f"0:{size}"
                else:
                    dtype = col['dtype'] = 'T'  # Default a tipo sconosciuto
            
            # Gestione del tipo CHARACTER VARYING o simili
            elif dtype == 'C':
                size = col.pop('length', None)
                if size is not None:
                    col['size'] = str(size)
            
            # Gestione SERIAL
            if dtype == 'L' and col.get('_pg_default'):
                col['dtype'] = 'serial'
            
            yield col
    

    def struct_get_constraints_sql(self):
        return """
            SELECT
                tc.constraint_schema AS schema_name,
                tc.table_name AS table_name,
                tc.constraint_name AS constraint_name,
                tc.constraint_type AS constraint_type,
                string_agg(kcu.column_name, ',' ORDER BY kcu.ordinal_position) AS columns, -- Stringa di colonne
                rc.update_rule AS on_update,
                rc.delete_rule AS on_delete,
                ccu.table_schema AS related_schema,
                ccu.table_name AS related_table,
                string_agg(ccu.column_name, ',' ORDER BY kcu.ordinal_position) AS related_columns, -- Stringa di colonne referenziate
                ch.check_clause AS check_clause,
                tc.is_deferrable AS deferrable,
                tc.initially_deferred AS initially_deferred
            FROM
                information_schema.table_constraints AS tc
            LEFT JOIN
                information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.constraint_schema = kcu.constraint_schema
                AND tc.table_name = kcu.table_name
            LEFT JOIN
                information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
                AND tc.constraint_schema = rc.constraint_schema
            LEFT JOIN
                information_schema.constraint_column_usage AS ccu
                ON rc.unique_constraint_name = ccu.constraint_name
                AND rc.unique_constraint_schema = ccu.constraint_schema
            LEFT JOIN
                information_schema.check_constraints AS ch
                ON tc.constraint_name = ch.constraint_name
                AND tc.constraint_schema = ch.constraint_schema
            WHERE
                tc.constraint_schema = ANY(%s)
            GROUP BY
                tc.constraint_schema, tc.table_name, tc.constraint_name, tc.constraint_type,
                rc.update_rule, rc.delete_rule, ccu.table_schema, ccu.table_name, ch.check_clause,
                tc.is_deferrable, tc.initially_deferred
            ORDER BY
                tc.constraint_schema, tc.table_name, tc.constraint_name;
        """

    def struct_get_constraints(self, schemas):
        query = self.struct_get_constraints_sql()
        constraints = defaultdict(lambda: defaultdict(dict))
        
        def parse_string_agg(string_agg_value):
            """Convert string_agg result to a list."""
            return string_agg_value.split(',') if string_agg_value else []

        def remove_duplicates_preserve_order(lst):
            """Remove duplicates from a list while preserving order."""
            seen = set()
            return [x for x in lst if not (x in seen or seen.add(x))]

        for row in self.raw_fetch(query, (schemas,)):
            (schema_name, table_name, constraint_name, constraint_type, columns, 
            on_update, on_delete, related_schema, related_table, related_columns, check_clause,
            deferrable, initially_deferred) = row

            # Convert columns and related_columns from string to list
            parsed_columns = remove_duplicates_preserve_order(parse_string_agg(columns))
            parsed_related_columns = remove_duplicates_preserve_order(parse_string_agg(related_columns))

            # Key for schema and table
            table_key = (schema_name, table_name)

            # Default constraint structure
            constraint_dict = {
                "constraint_name": constraint_name,
                "constraint_type": constraint_type,
                "columns": parsed_columns,
                "on_update": on_update,
                "on_delete": on_delete,
                "related_schema": related_schema,
                "related_table": related_table,
                "related_columns": parsed_related_columns,
                "check_clause": check_clause,
                "deferrable": deferrable == "YES",  # Convert to boolean
                "initially_deferred": initially_deferred == "YES"  # Convert to boolean
            }

            # Add constraints to the dictionary
            if constraint_type == "PRIMARY KEY":
                if "PRIMARY KEY" not in constraints[table_key]:
                    constraints[table_key]["PRIMARY KEY"] = constraint_dict
            else:
                if constraint_name not in constraints[table_key][constraint_type]:
                    constraints[table_key][constraint_type][constraint_name] = constraint_dict

        return constraints

    def struct_get_indexes_sql(self):
        return """
        SELECT
            n.nspname AS schema_name,               -- Schema name
            t.relname AS table_name,
            i.relname AS index_name,
            a.attname AS column_name,
            ix.indisunique AS is_unique,
            ix.indoption[array_position(ix.indkey, a.attnum)-1] & 1 AS desc_order,
            am.amname AS index_method,
            spc.spcname AS tablespace,
            pg_get_expr(ix.indpred, t.oid) AS where_clause,
            i.reloptions AS with_options,
            array_position(ix.indkey, a.attnum) AS ordinal_position,
            con.contype AS constraint_type
        FROM
            pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_am am ON i.relam = am.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            JOIN pg_namespace n ON t.relnamespace = n.oid  -- Schema join
            LEFT JOIN pg_tablespace spc ON i.reltablespace = spc.oid
            LEFT JOIN pg_constraint con ON con.conindid = i.oid
        WHERE
            t.relkind = 'r'  -- ordinary tables only
            AND n.nspname = ANY(%s)  -- Filter by schemas
        ORDER BY
            n.nspname, t.relname, i.relname, ordinal_position;
        """

    def struct_get_indexes(self, schemas):
        query = self.struct_get_indexes_sql()
        indexes = defaultdict(lambda: defaultdict(dict))
        for row in self.raw_fetch(query, (schemas,)):
            (schema_name, table_name, index_name, column_name, is_unique, 
            desc_order, index_method, tablespace, where_clause, 
            with_options, ordinal_position, constraint_type) = row
            
            # Chiave per schema e tabella
            table_key = (schema_name, table_name)
            
            # Inizializza il dizionario per l'indice se non esiste già
            if index_name not in indexes[table_key]:
                indexes[table_key][index_name] = {
                    "unique": is_unique,
                    "method": index_method if index_method != DEFAULT_INDEX_METHOD else None,
                    "tablespace": tablespace,
                    "where": where_clause,
                    "with_options": {},
                    "columns": {},
                    "constraint_type": constraint_type  # p, u, etc., or None for manual indexes
                }
            
            # Aggiunge le colonne e il relativo ordinamento
            sort_order = "DESC" if desc_order else None
            indexes[table_key][index_name]["columns"][column_name] = sort_order
            
            # Parse 'with_options' and store them in the dictionary
            if with_options:
                for option in with_options:
                    k, v = option.split('=')
                    indexes[table_key][index_name]["with_options"][k.strip()] = v.strip()
        
        return indexes
    
    def struct_create_index_sql(self,schema_name=None,
                                table_name=None,
                                columns=None,index_name=None,
                                unique=None,method=None,tablespace=None,
                                with_options=None,where=None):
        with_options = with_options or {}
        method = method or "btree"
        # Build the list of columns with specific sorting if present
        column_defs = []
        for column, order in columns.items():
            if order:
                column_defs.append(f"{column} {order}")
            else:
                column_defs.append(f"{column}")  # Default sorting if not specified

        # Join columns into a single string
        column_list = ", ".join(column_defs)

        # Build the WITH options clause
        with_parts = [f"{key} = {value}" for key, value in with_options.items()]
        with_clause = f"WITH ({', '.join(with_parts)})" if with_parts else ""
        
        # Add TABLESPACE clause if specified
        tablespace_clause = f"TABLESPACE {tablespace}" if tablespace else ""
        
        # Add WHERE clause if specified
        where_clause = f"WHERE {where}" if where else ""
        
        # Build full table name with schema if schema is provided
        full_table_name = self.struct_table_fullname_sql(schema_name,table_name)
        
        # Compose the final SQL statement
        unique_clause = ' UNIQUE ' if unique else " "

        sql = f"""
        CREATE{unique_clause}INDEX {index_name}
        ON {full_table_name}
        USING {method} ({column_list})
        {with_clause}
        {tablespace_clause}
        {where_clause}
        """
        
        # Return a clean, single-line SQL string
        result = " ".join(sql.split())
        return f'{result};'


    def struct_alter_column_sql(self, column_name=None, new_sql_type=None,**kwargs):
        """
        Generate SQL to alter the type of a column.
        """
        return f'ALTER COLUMN "{column_name}" TYPE {new_sql_type}'

    def struct_add_not_null_sql(self, column_name,**kwargs):
        """
        Generate SQL to add a NOT NULL constraint to a column.
        """
        return f'ALTER COLUMN "{column_name}" SET NOT NULL'

    def struct_drop_not_null_sql(self, column_name,**kwargs):
        """
        Generate SQL to drop a NOT NULL constraint from a column.
        """
        return f'ALTER COLUMN "{column_name}" DROP NOT NULL'


    def struct_drop_constraint_sql(self, constraint_name, **kwargs):
        """
        Generate SQL to drop a UNIQUE constraint from a column.
        """
        return f'DROP CONSTRAINT IF EXISTS "{constraint_name}"'

    def struct_foreign_key_sql(self, fk_name, columns, related_table, related_schema, related_columns, 
                           on_delete=None, on_update=None, deferrable=False, initially_deferred=False):
        """
        Generate SQL to create a foreign key constraint.

        Parameters:
            fk_name (str): The name of the foreign key constraint.
            columns (list): List of columns in the current table.
            related_table (str): The name of the related table.
            related_schema (str): The schema of the related table.
            related_columns (list): List of columns in the related table.
            on_delete (str, optional): Action to perform on delete (e.g., CASCADE, SET NULL).
            on_update (str, optional): Action to perform on update (e.g., CASCADE, SET NULL).
            deferrable (bool, optional): Whether the constraint is deferrable (default: False).
            initially_deferred (bool, optional): Whether the constraint is initially deferred (default: False).

        Returns:
            str: The SQL string to create the foreign key constraint.
        """
        columns_str = ', '.join(f'"{col}"' for col in columns)
        related_columns_str = ', '.join(f'"{col}"' for col in related_columns)
        on_delete_str = f" ON DELETE {on_delete}" if on_delete else ""
        on_update_str = f" ON UPDATE {on_update}" if on_update else ""
        deferrable_str = " DEFERRABLE" if deferrable else ""
        initially_deferred_str = " INITIALLY DEFERRED" if deferrable and initially_deferred else ""
        
        return (
            f'CONSTRAINT "{fk_name}" FOREIGN KEY ({columns_str}) '
            f'REFERENCES "{related_schema}"."{related_table}" ({related_columns_str})'
            f'{on_delete_str}{on_update_str}{deferrable_str}{initially_deferred_str}'
        )
    
    def struct_constraint_sql(self,constraint_name=None, constraint_type=None, columns=None, check_clause=None,**kwargs):
        """
        Generate SQL to create a constraint of type UNIQUE or CHECK.
        
        Parameters:
            constraint_name (str): The name of the constraint.
            constraint_type (str): The type of constraint ('UNIQUE', 'CHECK').
            columns (list, optional): List of columns for the constraint (required for 'UNIQUE').
            check_clause (str, optional): The condition for the 'CHECK' constraint.
        
        Returns:
            str: The SQL string to create the constraint.
        """
        if constraint_type == "UNIQUE":
            if not columns:
                raise ValueError("Columns must be specified for a UNIQUE constraint.")
            columns_str = ', '.join(f'"{col}"' for col in columns)
            return f'CONSTRAINT "{constraint_name}" UNIQUE ({columns_str})'
        
        elif constraint_type == "CHECK":
            if not check_clause:
                raise ValueError("Check clause must be specified for a CHECK constraint.")
            return f'CONSTRAINT "{constraint_name}" CHECK ({check_clause})'
        
        else:
            raise ValueError(f"Unsupported constraint type: {constraint_type}")
    

    def struct_drop_table_pkey(self, schema_name, table_name):
        """
        Generate SQL to drop a primary key from a table.
        """
        return f'ALTER TABLE "{schema_name}"."{table_name}" DROP CONSTRAINT IF EXISTS "{table_name}_pkey";'

    def struct_add_table_pkey(self, schema_name, table_name, columns):
        """
        Generate SQL to add a primary key to a table.
        """
        columns_str = ', '.join(f'"{col}"' for col in columns)
        return f'ALTER TABLE "{schema_name}"."{table_name}" ADD PRIMARY KEY ({columns_str});'



    def struct_get_extensions_sql(self):
        return """
        SELECT 
            e.extname AS extension_name,     -- Name of the extension
            e.extversion AS version,         -- Version of the extension
            e.extrelocatable AS relocatable, -- Whether the extension is relocatable
            e.extconfig AS config_tables,    -- Configuration tables of the extension
            e.extcondition AS conditions,    -- Conditions associated with the extension
            n.nspname AS schema_name         -- Schema associated with the extension objects
        FROM 
            pg_extension e
        JOIN 
            pg_namespace n ON e.extnamespace = n.oid
        ORDER BY 
            e.extname;
        """

    def struct_get_extensions(self):
        query = self.struct_get_extensions_sql()
        extensions = {}

        # Execute the query and process the results
        for row in self.raw_fetch(query, ()):
            (extension_name, version, relocatable, config_tables, conditions, schema_name) = row
            
            # Add the extension details to the dictionary
            extensions[extension_name] = {
                "version": version,
                "relocatable": relocatable,
                "config_tables": config_tables or [],
                "conditions": conditions or [],
                "schema_name": schema_name  # Schema where the extension objects are created
            }

        return extensions
    
    def struct_create_extension_sql(self, extension_name):
        """
        Generates the SQL to create an extension with optional schema, version, and cascade options.
        """
        return f"""CREATE EXTENSION IF NOT EXISTS {extension_name};"""
        


    def struct_get_event_triggers_sql(self):
        return """
        SELECT 
            evtname AS trigger_name,         -- Name of the event trigger
            evtevent AS event,              -- Event that fires the trigger (DDL command type)
            evtowner::regrole AS owner,     -- Owner of the event trigger
            obj_description(oid, 'pg_event_trigger') AS description, -- Description of the event trigger
            evtfoid::regprocedure AS function_name, -- Function invoked by the trigger
            evtenabled AS enabled_state,    -- Whether the trigger is enabled (O = enabled, D = disabled, R = replica)
            evttags AS event_tags           -- Tags for the event trigger
        FROM 
            pg_event_trigger
        ORDER BY 
            trigger_name;
        """


    def struct_get_event_triggers(self):
        query = self.struct_get_event_triggers_sql()
        event_triggers = {}

        # Execute the query and process the results
        for row in self.raw_fetch(query, ()):
            (trigger_name, event, owner, description, function_name, enabled_state, event_tags) = row
            
            # Add the event trigger details to the dictionary
            event_triggers[trigger_name] = {
                "event": event,
                "owner": owner,
                "description": description,
                "function_name": function_name,
                "enabled_state": enabled_state,
                "event_tags": event_tags or []
            }

        return event_triggers
    
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

class GnrWhereTranslatorPG(GnrWhereTranslator):
    def op_similar(self, column, value, dtype, sqlArgs,tblobj):
        "!!Similar"
        phonetic_column =  tblobj.column(column).attributes['phonetic']
        phonetic_mode = tblobj.column(column).table.column(phonetic_column).attributes['phonetic_mode']
        return '%s = %s(:%s)' % (phonetic_column, phonetic_mode, self.storeArgs(value, dtype, sqlArgs))

    def unaccent(self,v):
        return 'unaccent(%s)' %v


