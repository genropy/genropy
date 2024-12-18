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

from datetime import datetime
from past.utils import old_div
import re
import datetime

from gnr.core.gnrbag import Bag
from gnr.core.gnrlist import GnrNamedList
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.core.gnrdate import decodeDatePeriod

FLDMASK = dict(qmark='%s=?',named=':%s',pyformat='%%(%s)s')


class SqlDbAdapter(object):
    """Base class for sql adapters.
    
    All the methods of this class can be overwritten for specific db adapters,
    but only a few must be implemented in a specific adapter."""

    typesDict = {'character varying': 'A', 'character': 'A', 'text': 'T',
                 'boolean': 'B', 'date': 'D', 
                 'time without time zone': 'H', 
                 'time with time zone': 'HZ',
                 'timestamp without time zone': 'DH',
                 'interval':'DT',
                 'timestamp with time zone': 'DHZ',
                 'numeric': 'N', 'money': 'M',
                 'integer': 'I', 'bigint': 'L', 'smallint': 'I', 'double precision': 'R', 'real': 'R', 'bytea': 'O'}

    revTypesDict = {'A': 'character varying', 'C': 'character', 'T': 'text',
                    'X': 'text', 'P': 'text', 'Z': 'text', 'N': 'numeric', 'M': 'money',
                    'B': 'boolean', 'D': 'date', 
                    'H': 'time without time zone',
                    'HZ': 'time without time zone',
                    'DH': 'timestamp without time zone',
                    'DHZ': 'timestamp with time zone',
                    'DT':'interval',
                    'I': 'integer', 'L': 'bigint', 'R': 'real',
                    'serial': 'serial8', 'O': 'bytea'}

    # True if the database supports multiple connections. If False,
    # switching environments will be a no-op::
    #
    #     with self.db.tempEnv(connectionName='system'):
    #         # your code here
    #         pass
    support_multiple_connections = True
    paramstyle = 'named'
    allowAlterColumn=True

    def __init__(self, dbroot, **kwargs):
        self.dbroot = dbroot
        self.options = kwargs

    def use_schemas(self):
        return True

    def connect(self, storename=None):
        """-- IMPLEMENT THIS --
        Build and return a new connection object: ex. return dbapi.connect()
        The returned connection MUST provide cursors accessible by col number or col name (as list or as dict)
        @return: a new connection object"""
        raise NotImplementedException()

    def cursor(self, connection, cursorname=None):
        if isinstance(connection, list):
            if cursorname:
                return [c.cursor(cursorname) for c in connection]
            else:
                return [c.cursor() for c in connection]
        if cursorname:
            return connection.cursor(cursorname)
        else:
            return connection.cursor()

    def listen(self, msg, timeout=None, onNotify=None, onTimeout=None):
        """-- IMPLEMENT THIS --
        Listen for interprocess message 'msg' 
        onTimeout callbacks are executed on every timeout, onNotify on messages.
        Callbacks returns False to stop, or True to continue listening.
        @param msg: name of the message to wait for
        @param timeout: seconds to wait for the message
        @param onNotify: function to execute on arrive of message
        @param onTimeout: function to execute on timeout
        """
        raise NotImplementedException()

    def notify(self, msg, autocommit=False):
        """-- IMPLEMENT THIS --
        Notify a message to listener processes.
        @param msg: name of the message to notify
        @param autocommit: dafault False, if specific implementation of notify uses transactions, commit the current transaction"""
        raise NotImplementedException()

    def createdb(self, name, encoding=None):
        """-- IMPLEMENT THIS --
        Create a new database
        @param name: db name
        @param encoding: database text encoding
        """
        raise NotImplementedException()

    def dropdb(self, name):
        """-- IMPLEMENT THIS --
        Drop an existing database
        @param name: db name
        """
        raise NotImplementedException()

    def dump(self, filename,dbname=None,**kwargs):
        """-- IMPLEMENT THIS --
        Dump a database to a given path
        @param name: db name
        """
        raise NotImplementedException()

    def restore(self, filename,dbname=None):
        """-- IMPLEMENT THIS --
        Restore a database from existing path
        @param name: db name
        """
        raise NotImplementedException()
    
    def importRemoteDb(self, source_dbname,source_ssh_host=None,source_ssh_user=None,
                                source_ssh_dbuser=None,source_ssh_dbpassword=None,
                                source_ssh_dbhost=None,dest_dbname=None):
        raise NotImplementedException()

    def listRemoteDatabases(self,source_ssh_host=None,source_ssh_user=None,
                                source_ssh_dbuser=None,source_ssh_dbpassword=None,
                                source_ssh_dbhost=None):
        raise NotImplementedException()

    def defaultMainSchema(self):
        """-- IMPLEMENT THIS --
        Drop an existing database
        @return: the name of the default schema
        """
        raise NotImplementedException()

    def listElements(self, elType, **kwargs):
        """-- IMPLEMENT THIS --
        Get a list of element names: elements can be any kind of structure supported by a specific db.
        Usually an adapter accept as elType the following: schemata, tables, columns, views. Return
        the list of object names

        :param elType: type of structure element to list
        :param kwargs: optional parameters, eg. for elType "columns" kwargs
                       could be {'schema':'public', 'table':'mytable'}"""
        raise NotImplementedException()
        
    def relations(self):
        """-- IMPLEMENT THIS --
        Get a list of all relations in the db and return it. 
        Each element of the list is a list (or tuple) with this elements:
        [foreign_constraint_name, many_schema, many_tbl, [many_col, ...],
        unique_constraint_name, one_schema, one_tbl, [one_col, ...]]"""
        raise NotImplementedException()

    def getPkey(self, table, schema):
        """-- IMPLEMENT THIS --
        
        :param table: the :ref:`database table <table>` name, in the form ``packageName.tableName``
                      (packageName is the name of the :ref:`package <packages>` to which the table
                      belongs to)
        :param schema: schema name
        :returns: list of columns which are the :ref:`primary key <pkey>` for the table"""
        raise NotImplementedException()

    def getColInfo(self, table, schema, column):
        """-- IMPLEMENT THIS --
        Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        A specific adapter can add to the dict other available infos"""
        raise NotImplementedException()

    def _filterColInfo(self, colinfo, prefix):
        """Utility method to be used by getColInfo implementations.
        Prepend each non-standard key in the colinfo dict with prefix.
        
        :param colinfo: dict of column infos
        :param prefix: adapter specific prefix
        :returns: a new colinfo dict"""
        standard_keys = ('name', 'default', 'notnull', 'dtype', 'position', 'length')
        d = {k: v for k, v in colinfo.items() if k in standard_keys}
        d.update({f"{prefix}{k}": v for k, v in colinfo.items() if k not in standard_keys})
        return d

    def getIndexesForTable(self, table, schema):
        """-- IMPLEMENT THIS --
        Get a (list of) dict containing details about all the indexes of a table.
        Each dict has those info: name, primary (bool), unique (bool), columns (comma separated string)
        
        :param table: the :ref:`database table <table>` name, in the form ``packageName.tableName``
                      (packageName is the name of the :ref:`package <packages>` to which the table
                      belongs to)
        :param schema: the schema name
        :returns: list of index infos"""
        raise NotImplementedException()
        
    def getTableConstraints(self, table=None, schema=None):
        """Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        
        Other info may be present with an adapter-specific prefix."""
        raise NotImplementedException()

    def prepareSqlText(self, sql, kwargs):
        """Subclass in adapter if you want to change some sql syntax or params types.
        Example: for a search condition using regex, sqlite wants 'REGEXP', while postgres wants '~*'
        
        :param sql: the sql string to execute.
        :param  **kwargs: the params dict
        :returns: tuple (sql, kwargs)"""
        sql = self.adaptTupleListSet(sql,kwargs)
        return sql, kwargs

    def adaptTupleListSet(self,sql,sqlargs):
        # iter over sqlargs, and if the value is an iterable (but not strings)
        # search and replace in the sql query
        
        for k, v in [(k, v) for k, v in list(sqlargs.items()) if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set)]:
            sqllist = '(%s) ' % ','.join([':%s%i' % (k, i) for i, ov in enumerate(v)])
            sqlargs.pop(k)
            sqlargs.update(dict([('%s%i' % (k, i), ov) for i, ov in enumerate(v)]))
            sql = re.sub(r':%s(\W|$)' % k, sqllist+'\\1', sql)
        return sql

    def schemaName(self, name):
        return self.dbroot.fixed_schema or name
        
    def adaptSqlName(self,name):
        return name

    def adaptSqlSchema(self,name):
        return self.schemaName(name)

    def asTranslator(self, as_):
        return '"%s"'%as_

    def existsRecord(self, dbtable, record_data):
        """Test if a record yet exists in the db.
        
        :param dbtable: specify the :ref:`database table <table>`. More information in the
                        :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
        :param record_data: a dict compatible object containing at least one entry for the pkey column of the table."""
        tblobj = dbtable.model
        pkey = tblobj.pkey
        result = self.dbroot.execute(
                'SELECT 1 FROM %s WHERE %s=:id LIMIT 1;' % (tblobj.sqlfullname, tblobj.sqlnamemapper[pkey]),
                dict(id=record_data[pkey]), dbtable=dbtable.fullname).fetchall()
        if result:
            return True

    def rangeToSql(self, column, prefix, rangeStart=None, rangeEnd=None, includeStart=True, includeEnd=True):
        """Get the sql condition for an interval, in query args add parameters prefix_start, prefix_end"""
        #if rangeStart and rangeEnd:
        #    return 'BETWEEN :%s_start AND :%s_end' %(prefix,prefix)
        result = []
        if rangeStart:
            cond = '%s >%s :%s_start' % (column, (includeStart and '=') or'', prefix)
            result.append(cond)
        if rangeEnd:
            cond = '%s <%s :%s_end' % (column, (includeEnd and '=') or'', prefix)
            result.append(cond)
        result = ' AND '.join(result)
        return result

    def sqlFireEvent(self, link_txt, path, column,**kwargs):
        kw = dict(onclick= """genro.fireEvent(' ||quote_literal('%s')|| ',' ||quote_literal(%s)||')""" %(path, column),href="#" )
        kw.update(kw)
        result = """'<a %s >%s</a>'""" % (' '.join(['%s="%s"' %(k,v) for k,v in list(kw.items())]), link_txt)
        return result

    def setLocale(self,locale):
        pass
        
    def ageAtDate(self, dateColumn, dateArg=None, timeUnit='day'):
        """Returns the sql clause to obtain the age of a dateColum measured as difference from the dateArg or the workdate
           And expressed with given timeUnit.
           @param dateColumn: a D or DH column
           @dateArg: name of the parameter that contains the reference date
           @timeUnit: year,month,week,day,hour,minute,second. Defaulted to day"""
        dateArg = dateArg or 'env_workdate'
        timeUnitDict = dict(year=365 * 24 * 60 * 60, month=old_div(365 * 24 * 60 * 60, 12), week=7 * 24 * 60 * 60,
                            day=24 * 60 * 60, hour=60 * 60, minute=60, second=1)
        return """CAST((EXTRACT (EPOCH FROM(cast(:%s as date))) - 
                        EXTRACT (EPOCH FROM(%s)))/%i as bigint)""" % (dateArg, dateColumn,
                                                                      timeUnitDict.get(timeUnit, None) or timeUnitDict[
                                                                                                          'day'])

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
        return '\n'.join(result)

    def _selectForUpdate(self,maintable_as=None,mode=None):
        mode = '' if mode is True else mode
        return 'FOR UPDATE OF %s %s' %(maintable_as,mode)


    # FIXME: tblobj is allowed to be None (being the default) in the function prototype
    # but the implementation won't allow this value, searching for attributes related
    # to table object
    def prepareRecordData(self, record_data, tblobj=None,blackListAttributes=None, **kwargs):
        """Normalize a *record_data* object before actually execute an sql write command.
        Delete items which name starts with '@': eager loaded relations don't have to be
        written as fields. Convert Bag values to xml, to be stored in text or blob fields.
        [Convert all fields names to lowercase ascii characters.] REMOVED
        
        :param record_data: a dict compatible object
        :param tblobj: the :ref:`database table <table>` object
        """
        data_out = {}
        tbl_virtual_columns = tblobj.virtual_columns
        for k in list(record_data.keys()):
            if not (k.startswith('@') or k=='pkey' or  k in tbl_virtual_columns):
                v = record_data[k]
                if isinstance(v, Bag):
                    if blackListAttributes:
                        for innernode in v.traverse():
                            for blackattr in blackListAttributes:
                                innernode.attr.pop(blackattr,None)
                    v = v.toXml() if v else None
                    #data_out[str(k.lower())] = v
                data_out[str(k)] = v
        sql_value_cols = [k for k,v in list(tblobj.columns.items()) if 'sql_value' in v.attributes and not k in data_out]
        for k in sql_value_cols:
            data_out[k] = None
        return data_out

    def lockTable(self, dbtable, mode, nowait):
        """-- IMPLEMENT THIS --
        Lock a table
        """
        raise NotImplementedException()
        
    def insert(self, dbtable, record_data,**kwargs):
        """Insert a record in the db
        All fields in record_data will be added: all keys must correspond to a column in the db.
        
        :param dbtable: specify the :ref:`database table <table>`. More information in the
                        :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
        :param record_data: a dict compatible object
        """
        tblobj = dbtable.model
        record_data = self.prepareRecordData(record_data,tblobj=tblobj,**kwargs)
        sql_flds = []
        data_keys = []
        for k,v in record_data.items():
            sqlcolname = tblobj.sqlnamemapper.get(k)
            if not sqlcolname: 
                # skip aliasColumns
                continue
            sql_value = tblobj.column(k).attributes.get('sql_value')
            if (v is not None) or (sql_value is not None):
                sql_flds.append(sqlcolname)
                data_keys.append(sql_value or ':%s' % k)
        sql = 'INSERT INTO %s(%s) VALUES (%s);' % (tblobj.sqlfullname, ','.join(sql_flds), ','.join(data_keys))
        return self.dbroot.execute(sql, record_data, dbtable=dbtable.fullname)


    def insertMany(self, dbtable, records,**kwargs):
        tblobj = dbtable.model
        pkeyColumn = tblobj.pkey
        for record in records:
            if record.get(pkeyColumn) is None:
                record[pkeyColumn] = dbtable.newPkeyValue(record)
        sql_flds = []
        columns = []
        sqlnamemapper_items = [x for x in list(tblobj.sqlnamemapper.items()) if x[0] in list(records[0].keys())]
        for colname,sqlcolname in sqlnamemapper_items:
            sql_flds.append(sqlcolname)
            columns.append(colname)
        fldmask = FLDMASK.get(self.paramstyle)
        sql = 'INSERT INTO %s(%s) VALUES (%s);' % (tblobj.sqlfullname, ','.join(sql_flds), ','.join([fldmask %col for col in columns]))
        records = [self.prepareRecordData(record,tblobj=tblobj) for record in records]
        cursor = self.cursor(self.dbroot.connection)
        result = cursor.executemany(sql,records)
        return result


    def changePrimaryKeyValue(self, dbtable, pkey=None,newpkey=None,**kwargs):
        tblobj = dbtable.model
        pkeyColumn =  tblobj.sqlnamemapper[tblobj.pkey]
        sql = "UPDATE %s SET %s=:newpkey WHERE %s=:currpkey;" % (tblobj.sqlfullname, pkeyColumn,pkeyColumn)
        return self.dbroot.execute(sql, dbtable=dbtable.fullname,sqlargs=dict(currpkey=pkey,newpkey=newpkey))

    def update(self, dbtable, record_data, pkey=None,**kwargs):
        """Update a record in the db. 
        All fields in record_data will be updated: all keys must correspond to a column in the db.
        
        :param dbtable: specify the :ref:`database table <table>`. More information in the
                        :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
        :param record_data: a dict compatible object
        :param pkey: the :ref:`primary key <pkey>`
        """
        tblobj = dbtable.model
        record_data = self.prepareRecordData(record_data,tblobj=tblobj,**kwargs)
        sql_flds = []
        for k in list(record_data.keys()):
            sqlcolname = tblobj.sqlnamemapper.get(k)
            sql_par_prefix = ':'
            if sqlcolname:
                sql_value = tblobj.column(k).attributes.get('sql_value')
                if sql_value:
                    sql_par_prefix = ''
                    k = sql_value
                sql_flds.append('%s=%s%s' % (sqlcolname, sql_par_prefix,k))
        pkeyColumn = tblobj.pkey
        if pkey:
            pkeyColumn = '__pkey__'
            record_data[pkeyColumn] = pkey
        sql = 'UPDATE %s SET %s WHERE %s=:%s;' % (
        tblobj.sqlfullname, ','.join(sql_flds), tblobj.sqlnamemapper[tblobj.pkey], pkeyColumn)
        return self.dbroot.execute(sql, record_data, dbtable=dbtable.fullname)

    def delete(self, dbtable, record_data,**kwargs):
        """Delete a record from the db
        All fields in record_data will be added: all keys must correspond to a column in the db
        
        :param dbtable: specify the :ref:`database table <table>`. More information in the
                        :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
        :param record_data: a dict compatible object containing at least one entry for the pkey column of the table
        """
        tblobj = dbtable.model
        record_data = self.prepareRecordData(record_data,tblobj=tblobj,**kwargs)
        pkey = tblobj.pkey
        sql = 'DELETE FROM %s WHERE %s=:%s;' % (tblobj.sqlfullname, tblobj.sqlnamemapper[pkey], pkey)
        return self.dbroot.execute(sql, record_data, dbtable=dbtable.fullname)

    def sql_deleteSelection(self, dbtable, pkeyList):
        """Delete a selection from the table. It works only in SQL so no python trigger is executed
        
        :param dbtable: specify the :ref:`database table <table>`. More information in the
                        :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
        :param pkeyList: records to delete
        """
        tblobj = dbtable.model
        sql = 'DELETE FROM %s WHERE %s IN :pkeyList;' % (tblobj.sqlfullname, tblobj.sqlnamemapper[tblobj.pkey])
        return self.dbroot.execute(sql, sqlargs=dict(pkeyList=pkeyList), dbtable=dbtable.fullname)

    def emptyTable(self, dbtable, truncate=None, cascade=None):
        """Delete all table rows of the specified *dbtable* table
            :param dbtable: specify the :ref:`database table <table>`. More information in the
            :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
        """
        tblobj = dbtable.model
        if truncate:
            sql = 'TRUNCATE %s %s;' % (tblobj.sqlfullname, 'CASCADE' * cascade)
        else:
            sql = 'DELETE FROM %s;' % (tblobj.sqlfullname)
        return self.dbroot.execute(sql, dbtable=dbtable.fullname)

    def fillFromSqlTable(self, dbtable, sqltablename):
        """Copy all table rows from table sqltablename into dbtable
        :param dbtable: specify the :ref:`database table <table>`. More information in the
        :ref:`sqltablename` name of the source table
        """
        tblobj = dbtable.model
        columns = ', '.join(tblobj.columns.keys())
        sql = """INSERT INTO {dest_table}({columns})
                 SELECT {columns} FROM {source_table};""".format(dest_table = tblobj.sqlfullname, 
                                                        source_table = sqltablename,columns=columns)
        return self.dbroot.execute(sql, dbtable=dbtable.fullname)

    def analyze(self):
        """Perform analyze routines on the db"""
        self.dbroot.execute('ANALYZE;')

    def vacuum(self, table='', full=False):
        """Perform analyze routines on the database
        
        :param table: the :ref:`database table <table>` name, in the form ``packageName.tableName``
                      (packageName is the name of the :ref:`package <packages>` to which the table
                      belongs to)
        :param full: boolean. TODO"""
        self.dbroot.execute('VACUUM ANALYZE %s;' % table)

    def string_agg(self,fieldpath,separator):
        return f"string_agg({fieldpath},'{separator}')"

    def addForeignKeySql(self, c_name, o_pkg, o_tbl, o_fld, m_pkg, m_tbl, m_fld, on_up, on_del, init_deferred):
        statement = 'ALTER TABLE %s.%s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s.%s (%s)' % (
        m_pkg, m_tbl, c_name, m_fld, o_pkg, o_tbl, o_fld)
        drop_statement = 'ALTER TABLE %s.%s DROP CONSTRAINT IF EXISTS %s;' % (m_pkg, m_tbl, c_name)
        for on_command, on_value in (('ON DELETE', on_del), ('ON UPDATE', on_up)):
            if on_value: statement += ' %s %s' % (on_command, on_value)
        statement = '%s %s %s' % (drop_statement,statement, init_deferred or '')
        return statement

    def addUniqueConstraint(self, pkg, tbl, fld):
        statement = 'ALTER TABLE %s.%s ADD CONSTRAINT un_%s_%s_%s UNIQUE (%s)' % (pkg, tbl, pkg, tbl.strip('"'), fld, fld)
        return statement

    def createExtensionSql(self,extension):
        "override this"
        pass

    def dropExtensionSql(self,extension):
        "override this"
        pass

    def dropExtension(self, extensions):
        """Disable a specific db extension"""
        pass

    def createExtension(self, extensions):
        """Enable a specific db extension"""
        pass

    def createSchemaSql(self, sqlschema):
        """Returns the sql command to create a new database schema"""
        return 'CREATE SCHEMA %s;' % self.adaptSqlName(sqlschema)

    def createSchema(self, sqlschema):
        """Create a new database schema"""
        if not sqlschema in self.listElements('schemata'):
            self.dbroot.execute(self.createSchemaSql(sqlschema))

    def dropSchema(self, sqlschema):
        """Drop database schema"""
        if sqlschema in self.listElements('schemata'):
            self.dbroot.execute('DROP SCHEMA %s CASCADE;' % sqlschema)

    def createTableAs(self, sqltable, query, sqlparams):
        self.dbroot.execute("CREATE TABLE %s AS %s;" % (sqltable, query), sqlparams)

    def addColumn(self, sqltable, sqlname, dtype='T', size=None, notnull=None, pkey=None, unique=None):
        sqlcol = self.columnSqlDefinition(sqlname, dtype=dtype, size=size, notnull=notnull, pkey=pkey, unique=unique)
        self.dbroot.execute('ALTER TABLE %s ADD COLUMN %s' % (sqltable, sqlcol))

    def renameColumn(self, sqltable, sqlname,sqlnewname):
        #automag_deposito_sede_id_idx
        kwargs = dict(sqltable=sqltable,sqlname=sqlname,sqlnewname=sqlnewname)
        tbl_flatname = sqltable.split('.')[1]
        kwargs['old_index_name'] = '%s_%s_idx' %(sqltable,sqlname)
        kwargs['new_index_name'] = '%s_%s_idx' %(tbl_flatname,sqlnewname)

        kwargs['old_fkey_name'] = 'fk_%s_%s' %(tbl_flatname,sqlname)
        kwargs['new_fkey_name'] = 'fk_%s_%s' %(tbl_flatname,sqlnewname)

        command = """
            ALTER TABLE %(sqltable)s RENAME COLUMN %(sqlname)s TO %(sqlnewname)s;
            DROP INDEX IF EXISTS %(old_index_name)s;
            ALTER TABLE %(sqltable)s DROP CONSTRAINT IF EXISTS %(old_fkey_name)s;
        """
        self.dbroot.execute(command %kwargs)

    def dropColumn(self, sqltable,sqlname,cascade=False):
        """Drop column"""
        command = 'ALTER TABLE %s DROP COLUMN %s;'
        if cascade:
            command = 'ALTER TABLE %s DROP COLUMN %s CASCADE;'
        self.dbroot.execute(command % (sqltable,sqlname))

    def columnSqlDefinition(self, sqlname, dtype, size, notnull, pkey, unique,extra_sql=None):
        """Return the statement string for creating a table's column
        """
        sql = '"%s" %s' % (sqlname, self.columnSqlType(dtype, size))
        if notnull:
            sql = sql + ' NOT NULL'
        if pkey:
            sql = sql + ' PRIMARY KEY'
        if unique:
            sql = sql + ' UNIQUE'
        return f"{sql} {extra_sql or ''}"

    def columnSqlType(self, dtype, size=None):
        if dtype != 'N' and size:
            if ':' in size:
                size = size.split(':')[1]
                dtype = 'A'
            else:
                dtype = 'C'
        if size:
            return '%s(%s)' % (self.revTypesDict[dtype], size)
        else:
            return self.revTypesDict[dtype]

    def alterColumnSql(self, table, column, dtype):
        return 'ALTER TABLE %s ALTER TABLE %s TYPE %s' % (table, column, dtype)

    def dropEmptyTables(self,schema=None):
        tables = self.listElements('tables',schema=schema)
        for tbl in tables:
            tblfullname = '%s.%s' %(schema,tbl)
            if not self.dbroot.execute("""SELECT COUNT(*) FROM %s""" %tblfullname).fetchone()[0]:
                self.dropTable(tblfullname,cascade=True)

    def dropTable(self, dbtable,cascade=False):
        """Drop table"""
        command = 'DROP TABLE %s;'
        if cascade:
            command = 'DROP TABLE %s CASCADE;'
        tablename = dbtable if isinstance(dbtable, str) else dbtable.model.sqlfullname
        self.dbroot.execute(command % tablename)

    def dropIndex(self, index_name, sqlschema=None):
        """Drop an index
        
        :param index_name: name of the index (unique in schema)
        :param sqlschema: actual sql name of the schema. For more information check the :ref:`about_schema`
                          documentation section"""
        if sqlschema:
            index_name = '%s.%s' % (sqlschema, index_name)
        return "DROP INDEX IF EXISTS %s;" % index_name

    def createIndex(self, index_name, columns, table_sql, sqlschema=None, unique=None):
        """Create a new index
        
        :param index_name: name of the index (unique in schema)
        :param columns: comma separated string (or list or tuple) of :ref:`columns` to include in the index
        :param table_sql: actual sql name of the table
        :param sqlschema: actual sql name of the schema. For more information check the :ref:`about_schema`
                          documentation section
        :unique: boolean for unique indexing"""
        table_sql = self.adaptSqlName(table_sql)
        
        if sqlschema:
            sqlschema  = self.adaptSqlName(sqlschema)
            table_sql = '%s.%s' % (sqlschema, table_sql)
        if unique:
            unique = 'UNIQUE '
        else:
            unique = ''
        columns = ','.join([self.adaptSqlName(c) for c in columns.split(',')])
        
        return "CREATE %sINDEX %s ON %s (%s);" % (unique, index_name, table_sql, columns)

    def createDbSql(self, dbname, encoding):
        pass

    def unaccentFormula(self, field):
        return field

    def getWhereTranslator(self):
        return GnrWhereTranslator(self.dbroot)

class GnrWhereTranslator(object):
    def __init__(self, db):
        self.db = db
        self.catalog = GnrClassCatalog()
        self.opDict = dict([(k[3:], None) for k in dir(self) if k.startswith('op_')])

    def __call__(self, tblobj, wherebag, sqlArgs, customOpCbDict=None):
        if sqlArgs is None:
            sqlArgs = {}
        self.parnames = {}
        self.customOpCbDict = customOpCbDict
        result = self.innerFromBag(tblobj, wherebag, sqlArgs, 0)
        return '\n'.join(result)

    def opCaption(self, op, localize=False):
        h = getattr(self, 'op_%s' % op.lower(), None)
        if not h and op.startswith('not_'):
            return 'Not %s' % getattr(self, 'op_%s' % op[4:].lower()).__doc__
        result = h.__doc__
        if localize and self.db.localizer:
            result = self.db.localizer.translate(result,language=self.db.currentEnv.get('locale'))
        return result

    def _relPathToCaption(self, table, relpath):
        if not relpath: return ''
        tbltree = self.db.relationExplorer(table, dosort=False, pyresolver=True)
        localize = self.db.localizer.translate
        locale = self.db.currentEnv.get('locale')
        fullcaption = tbltree.cbtraverse(relpath, lambda node: localize(node.getAttr('name_long'),language=locale))
        return ':'.join(fullcaption)

    def toText(self, tblobj, wherebag, level=0, decodeDate=False):
        result = []
        for k, node in enumerate(wherebag.getNodes()):
            attr = node.getAttr()
            value = node.getValue()
            if k:
                jc = attr.get('jc_caption', '')
            else:
                jc = ''
            negate = attr.get('not') == 'not'
            if isinstance(value, Bag):
                onecondition = ('\n' + '    ' * level).join(self.toText(tblobj, value, level + 1))
                onecondition = '(\n' + '    ' * level + onecondition + '\n' + '    ' * level + ')'
            else:
                op = attr.get('op_caption')
                column = attr.get('column_caption')
                if not op and attr.get('op'):
                    op = self.opCaption(attr['op'],localize=True)
                if not column and attr.get('column'):
                    column = self._relPathToCaption(tblobj.fullname, attr.get('column'))
                if not op or not column:
                    continue
                if decodeDate:
                    if tblobj.column(attr.get('column')).dtype in('D', 'DH','DHZ'):
                        value, op = self.decodeDates(value, op, 'D')
                        op = self.opCaption(op, localize=True)
                op = op.lower()
                onecondition = '%s %s %s' % (column, op, value)
            if onecondition:
                if negate:
                    onecondition = ' %s %s  ' % (attr.get('not_caption', ''), onecondition)
                result.append(' %s %s' % (jc, onecondition ))
        return result

    def toHtml(self, tblobj, wherebag, level=0, decodeDate=False):
        result = []
        for k, node in enumerate(wherebag.getNodes()):
            attr = node.getAttr()
            value = node.getValue()
            if k:
                jc = attr.get('jc_caption', '')
            else:
                jc = ''
            negate = attr.get('not') == 'not'
            if isinstance(value, Bag):
                onecondition =  '<div class="slqnested"> %s </div>' %(self.toHtml(tblobj, value, level + 1))#'(\n' + '    ' * level + onecondition + '\n' + '    ' * level + ')'
            else:
                op = attr.get('op_caption')
                column = attr.get('column_caption')
                if not op and attr.get('op'):
                    op = self.opCaption(attr['op'],localize=True)
                if not column and attr.get('column'):
                    column = self._relPathToCaption(tblobj.fullname, attr.get('column'))
                if not op or not column:
                    continue
                if decodeDate:
                    if tblobj.column(attr.get('column')).dtype in('D', 'DH','DHZ'):
                        value, op = self.decodeDates(value, op, 'D')
                        op = self.opCaption(op, localize=True)
                op = op.lower()
                onecondition = '<span class="sqlcol">%s</span> <span class="sqlop">%s</span> <span class="sqlvalue">%s</span>' % (column, op, value)
            if onecondition:
                if negate:
                    onecondition = ' <span class="sqlnot">%s</span> %s  ' % (attr.get('not_caption', ''), onecondition)
                result.append('<div class="sqlcondition"> <span class="sqljc">%s</span> %s </div>' % (jc, onecondition ))

        return ''.join(result)


    def innerFromBag(self, tblobj, wherebag, sqlArgs, level):
        """<condition column="fattura_num" op="ISNULL" rem='senza fattura' />
        <condition column="@anagrafica.provincia" op="IN" jc='AND'>MI,FI,TO</condition>
        <group not="true::B" jc='AND'>
                <condition column="" op=""/>
                <condition column="" op="" jc='OR'/>
        </group>"""

        result = []
        for node in wherebag:
            attr = node.getAttr()
            value = node.getValue()
            if isinstance(value, str) and value.startswith('?'):
                value = sqlArgs.get(value[1:])
            jc = attr.get('jc', '').upper()
            if not result:
                jc = ''
            negate = attr.get('not') == 'not'
            if isinstance(value, Bag):
                onecondition = ('\n' + '    ' * level).join(self.innerFromBag(tblobj, value, sqlArgs, level + 1))
                onecondition = '(\n' + '    ' * level + onecondition + '\n' + '    ' * level + ')'
            else:
                op = attr.get('op')
                column = attr.get('column')
                parname = attr.get('parname')
                if not parname:
                    parname = column.replace('@','_').replace('.','_') if column else node.label
                if parname in self.parnames:
                    self.parnames[parname]+=1
                    parname = '{}_{}'.format(parname,self.parnames[parname])
                    self.parnames[parname] = 1
                else:
                    self.parnames[parname] = 1
                if not op or not column:
                    #ingnoring empty query lines
                    continue
                colobj=tblobj.column(column)
                if colobj is None:
                    raise tblobj.exception('not_existing_column', column=column)
                dtype = colobj.dtype

                if value is None and attr.get('value_caption'):
                    value = sqlArgs.pop(attr['value_caption'],'')
                onecondition = self.prepareCondition(column, op, value, dtype, sqlArgs,tblobj=tblobj,parname=parname)

            if onecondition:
                if negate:
                    onecondition = ' NOT %s  ' % onecondition
                result.append(' %s ( %s )' % (jc, onecondition ))
        return result

    def checkValueIsField(self,value):
        return value and isinstance(value, str) and value[0] in '$@'

    def prepareCondition(self, column, op, value, dtype, sqlArgs,tblobj=None,parname=None):
        if not dtype:
            dtype = tblobj.column(column).dtype
        if not column[0] in '@$':
            column = '$%s' % column
        if dtype in ('D', 'DH','DHZ'):
            if not self.checkValueIsField(value):
                value, op = self.decodeDates(value, op, 'D')
            if dtype=='DH' or dtype=='DHZ':
                column = 'date(%s)' % column
        if not dtype in ('A', 'T') and op in (
        'contains', 'notcontains', 'startswith', 'endswith', 'regex', 'wordstart'):
            value = str(value)
            column = 'CAST (%s as text)' % column
            dtype = 'A'
        if op=='equal' and isinstance(value,list):
            op = 'in'
        ophandler = getattr(self, 'op_%s' % op, None)
        if ophandler:
            result = ophandler(column=column, value=value, dtype=dtype, sqlArgs=sqlArgs,tblobj=tblobj,parname=parname)
        else:
            ophandler = self.customOpCbDict.get(op)
            assert ophandler, 'undefined ophandler'
            result = ophandler(column=column, value=value, dtype=dtype, sqlArgs=sqlArgs, whereTranslator=self,tblobj=tblobj,parname=parname)
        return result

    def decodeDates(self, value, op, dtype):
        if isinstance(value, datetime.date):
            return value, op
        if op == 'isnull':
            return value, op
        if op == 'in' and ',' in value: # is a in search with multiple (single date) arguments: don't use periods!!!
            value = ','.join(
                    [decodeDatePeriod(v, workdate=self.db.workdate, locale=self.db.locale, dtype=dtype) for v in
                     value.split(',')])
            return value, op
        value = decodeDatePeriod(value, workdate=self.db.workdate, locale=self.db.locale, dtype=dtype)
        mode = None
        if value.startswith(';'):
            mode = 'to'
        elif value.endswith(';'):
            mode = 'from'
        elif ';' in value:
            mode = 'period'

        if op in ('greater', 'greatereq'):  # keep the higher date
            if mode in ('period', 'to'):
                value = value.split(';')[1]
            else:
                value = value.strip(';')
        elif op in ('less', 'lesseq'):      # keep the lower date
            value = value.split(';')[0]

        else:
            # equal, between and textual operators are ignored
            # the right operator is choosen according to the value to find
            if mode == 'to':               # find data lower then value
                op = 'lesseq'
                value = value.strip(';')
            elif mode == 'from':           # find data higher then value
                op = 'greatereq'
                value = value.strip(';')
            elif mode == 'period':         # find data between period (value)
                op = 'between'
            else:                          # value is a single date
                op = 'equal'
        return value, op

    def storeArgs(self, value, dtype, sqlArgs, parname=None):
        if not dtype in ('A', 'T') and not self.checkValueIsField(value):
            if isinstance(value, list):
                value = [self.catalog.fromText(v, dtype) for v in value]
            elif isinstance(value, (bytes,str)):
                value = self.catalog.fromText(value, dtype)
        argLbl = parname or 'v_%i' % len(sqlArgs)
        sqlArgs[argLbl] = value
        return argLbl

    def op_startswithchars(self, column, value, dtype, sqlArgs,tblobj, parname=None):
        "!!Starts with Chars"
        return self.unaccentTpl(tblobj,column,'LIKE',mask=":%s || '%%%%'")  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_equal(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Equal to"
        return self.unaccentTpl(tblobj,column,'=')  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_startswith(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Starts with"
        return self.unaccentTpl(tblobj,column,'ILIKE',mask=":%s || '%%%%'")  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_wordstart(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Word start"
        value = value.replace('(', r'\(').replace(')', r'\)').replace('[', r'\[').replace(']', r'\]')
        return self.unaccentTpl(tblobj,column,'~*',mask="'(^|\\W)' || :%s")  % (column, self.storeArgs(value, dtype, sqlArgs,parname=parname))

    def op_contains(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Contains"
        return self.unaccentTpl(tblobj,column,'ILIKE',mask="'%%%%' || :%s || '%%%%'")  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_greater(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Greater than"
        return self.unaccentTpl(tblobj,column,'>')  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_greatereq(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Greater or equal to"
        return self.unaccentTpl(tblobj,column,'>=')  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_less(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Less than"
        return self.unaccentTpl(tblobj,column,'<')  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_lesseq(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Less or equal to"
        return self.unaccentTpl(tblobj,column,'<=')  % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))

    def op_between(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Between"
        v1, v2 = value.split(';')
        return '%s BETWEEN :%s AND :%s' % (
            column, self.storeArgs(v1, dtype, sqlArgs, parname='{}_from'.format(parname)), self.storeArgs(v2, dtype, sqlArgs, parname='{}_to'.format(parname))
        )

    def op_isnull(self, column, value, dtype, sqlArgs, tblobj,**kwargs):
        "!!Is null"
        return '%s IS NULL' % column

    def op_istrue(self, column, value, dtype, sqlArgs, tblobj,**kwargs):
        "!!Is true"
        return '%s IS TRUE' % column

    def op_isfalse(self, column, value, dtype, sqlArgs, tblobj,**kwargs):
        "!!Is false"
        return '%s IS FALSE' % column

    def op_nullorempty(self, column, value, dtype, sqlArgs, tblobj,**kwargs):
        "!!Is null or empty"
        if dtype in ('L', 'N', 'M', 'R'):
            return self.op_isnull(column, value, dtype, sqlArgs,tblobj,
            **kwargs)
        return " (%s IS NULL OR %s ='')" % (column, column)

    def op_in(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!In"
        if isinstance(value, str):
            value = value.split(',')
        values_string = self.storeArgs(value, dtype, sqlArgs, parname=parname)
        return '%s IN :%s' % (column, values_string)

    def op_regex(self, column, value, dtype, sqlArgs, tblobj, parname=None):
        "!!Regular expression"
        return '%s ~* :%s' % (column, self.storeArgs(value, dtype, sqlArgs, parname=parname))


   #def whereFromText(self, table, whereTxt, customColumns=None):
   #    result = []
   #    sqlArgs = {}
   #    tblobj = self.db.table(table)
   #    pattern = '(AND|OR)'
   #    whereList = re.compile(pattern).split(whereTxt)
   #    condList = [cond for cond in whereList if cond not in ('AND', 'OR')]

    def unaccentTpl(self,tblobj,column,token,mask=None):
        if not mask:
            mask = ':%s'
        if tblobj.column(column) is not None and tblobj.column(column).attributes.get('unaccent'):
            return  ' '.join([self.unaccent('%s'),token,self.unaccent(mask)])
        return ' '.join(['%s',token,mask])

    def unaccent(self,v):
        return v

    def whereFromDict(self, table, whereDict, customColumns=None):
        result = []
        sqlArgs = {}
        tblobj = self.db.table(table)
        for k, v in list(whereDict.items()):
            negate = ''
            op = 'equal'
            ksplit = k.split('_')
            if ksplit[-1].lower() in self.opDict:
                op = ksplit.pop().lower()
            if ksplit[-1].lower() == 'not':
                negate = ' NOT '
                ksplit.pop()
            column = '_'.join(ksplit)
            if customColumns and column in customColumns:
                custom = customColumns[column]
                if callable(custom):
                    condition = custom(column, sqlArgs)
                if isinstance(custom, str):
                    dtype = tblobj.column(custom).dtype
                    column = custom
                elif isinstance(custom, tuple):
                    column, dtype = custom
                else:
                    raise
            else:
                colobj = tblobj.column('$%s' % column)
                if colobj is None:
                    raise
                dtype = colobj.dtype
            condition = self.prepareCondition(column, op, v, dtype, sqlArgs,tblobj=tblobj)
            result.append('%s%s' % (negate, condition))
        return result, sqlArgs


class GnrDictRow(GnrNamedList):
    """A row object that allow by-column-name access to data, the capacity to add columns and alter data."""

    def __init__(self, cursor, values=None):
        self._index = cursor.index
        if values is None:
            self[:] = [None] * len(cursor.description)
        else:
            self[:] = values

class DbAdapterException(Exception):
    pass

class NotImplementedException(Exception):
    pass
