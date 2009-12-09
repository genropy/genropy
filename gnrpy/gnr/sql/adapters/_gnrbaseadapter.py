#-*- coding: UTF-8 -*-
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

from gnr.core.gnrbag import Bag
from gnr.core.gnrlist import GnrNamedList
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.core.gnrdate import decodeDatePeriod

class SqlDbAdapter(object):
    """Base class for sql adapters.
    All the methods of this class can be overwritten for specific db adapters, 
    but only a few must be implemented in a specific adapter."""
    typesDict = {'character varying':'A', 'character':'A', 'text':'T', 
                 'boolean':'B', 'date':'D', 'time without time zone':'H', 'timestamp without time zone':'DH',
                 'timestamp with time zone':'DH','numeric':'N','money':'M',
                 'integer':'I', 'bigint':'L','smallint':'I', 'double precision':'R', 'real':'R', 'bytea':'O'}
    
    revTypesDict = {'A':'character varying', 'C':'character', 'T':'text', 
                    'X':'text','P':'text','Z':'text','N':'numeric','M':'money',
                 'B':'boolean', 'D':'date', 'H':'time without time zone', 'DH':'timestamp without time zone',
                 'I':'integer', 'L':'bigint', 'R':'real',
                 'serial':'serial8','O':'bytea'}
        
    def __init__(self, dbroot, **kwargs):
        self.dbroot = dbroot
        self.options = kwargs
        
    def connect(self):
        """-- IMPLEMENT THIS --
        Build and return a new connection object: ex. return dbapi.connect()
        The returned connection MUST provide cursors accessible by col number or col name (as list or as dict)
        @return: a new connection object"""
        raise NotImplementedException()
    
    def cursor(self, connection, cursorname=None):
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
        
    def dump(self,filename):
        """-- IMPLEMENT THIS --
        Dump a database to a given path
        @param name: db name
        """
        raise NotImplementedException()
        
    def restore(self,filename):
        """-- IMPLEMENT THIS --
        Restore a database from existing path
        @param name: db name
        """
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
        Usually an adapter accept as elType the following: schemata, tables, columns, views
        @param elType: type of structure element to list
        @param kwargs: optional parameters, eg. for elType "columns" kwargs could be {'schema':'public', 'table':'mytable'}
        @return: list of object names"""
        raise NotImplementedException()

    def relations(self):
        """-- IMPLEMENT THIS --
        Get a list of all relations in the db. 
        Each element of the list is a list (or tuple) with this elements:
        [foreign_constraint_name, many_schema, many_tbl, [many_col, ...], unique_constraint_name, one_schema, one_tbl, [one_col, ...]]
        @return: list of relation's details
        """
        raise NotImplementedException()
    
    def getPkey(self, table, schema):
        """-- IMPLEMENT THIS --
        @param table: table name
        @param schema: schema name
        @return: list of columns wich are the primary key for the table"""
        raise NotImplementedException()
    
    def getColInfo(self, table, schema, column):
        """-- IMPLEMENT THIS --
        Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        A specifica adapter can add to the dict other available infos"""
        raise NotImplementedException()
    
    def _filterColInfo(self, colinfo, prefix):
        """Utility method to be used by getColInfo implementations.
        Prepend each non-standard key in the colinfo dict with prefix.
        @param colinfo: dict of column infos
        @param prefix: adapter specific prefix
        @return: a new colinfo dict"""
        d = dict([(k,v) for k,v in colinfo.items() if k in ('name','default','notnull','dtype','position','length')])
        d.update(dict([(prefix+k,v) for k,v in colinfo.items() if k not in ('name','default','notnull','dtype','position','length')]))
        return d
    
    def getIndexesForTable(self, table, schema):
        """-- IMPLEMENT THIS --
        Get a (list of) dict containing details about all the indexes of a table.
        Each dict has those info: name, primary (bool), unique (bool), columns (comma separated string)
        @param table: table name
        @param schema: schema name
        @return: list of index infos"""
        raise NotImplementedException()

    def prepareSqlText(self, sql, kwargs):
        """Subclass in adapter if you want to change some sql syntax or params types.
        Example: for a search condition using regex, sqlite wants 'REGEXP', while postgres wants '~*'
        @param sql: the sql string to execute.
        @param kwargs: the params dict
        @return: tuple (sql, kwargs)
        """
        return sql, kwargs
    
    def existsRecord(self, dbtable, record_data):
        """Test if a record yet exists in the db.
        @param dbtable: a SqlTable object
        @param record_data: a dict compatible object containing at least one entry for the pkey column of the table."""
        tblobj=dbtable.model
        pkey = tblobj.pkey
        result = self.dbroot.execute('SELECT 1 FROM %s WHERE %s=:id LIMIT 1;' % (tblobj.sqlfullname, tblobj.sqlnamemapper[pkey]), 
                                     dict(id=record_data[pkey])).fetchall()
        if result:
            return True
        
    
    def compileSql(self, maintable, columns, distinct='', joins=None, where=None,
                   group_by=None, having=None, order_by=None, limit=None, offset=None, for_update=None):
        def _smartappend(x, name, value):
            if value:
                x.append('%s %s' % (name, value))
        result = ['SELECT  %s%s' %  (distinct, columns)]
        result.append(' FROM %s AS t0' % (maintable, )) 
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
            result.append(self._selectForUpdate())
        return '\n'.join(result)
    
    def _selectForUpdate(self):
        return 'FOR UPDATE OF t0'
        
    def prepareRecordData(self, record_data):
        """Normalize a record_data object before actually execute an sql write command.
        Delete items which name starts with '@': eager loaded relations don't have to be written as fields.
        Convert Bag values to xml, to be stored in text or blob fields.
        [Convert all fields names to lowercase ascii characters.] REMOVED
        @param record_data: a dict compatible object
        """
        data_out = {}
        for k in record_data.keys():
            if not k.startswith('@'):
                v=record_data[k]
                if isinstance(v, Bag):
                    v = v.toXml()
               #data_out[str(k.lower())] = v
                data_out[str(k)] = v
        return data_out
        
    def lockTable(self, dbtable, mode, nowait):
        """-- IMPLEMENT THIS --
        Lock a table
        @param name: db name
        @param encoding: database text encoding
        """
        raise NotImplementedException()
        
        
    def insert(self, dbtable, record_data):
        """Insert a record in the db. 
        All fields in record_data will be added: all keys must correspond to a column in the db.
        @param dbtable: an SqlTable object
        @param record_data: a dict compatible object"""
        tblobj=dbtable.model
        record_data = self.prepareRecordData(record_data)
        sql_flds = []
        data_keys = []
        for k in record_data.keys():
            sql_flds.append(tblobj.sqlnamemapper[k])
            data_keys.append(':%s' % k)
        sql = 'INSERT INTO %s(%s) VALUES (%s);' % (tblobj.sqlfullname, ','.join(sql_flds), ','.join(data_keys))
        return self.dbroot.execute(sql, record_data)
    
    def update(self, dbtable, record_data, pkey=None):
        """Update a record in the db. 
        All fields in record_data will be updated: all keys must correspond to a column in the db.
        @param dbtable: a SqlTable object
        @param record_data: a dict compatible object"""
        
        tblobj=dbtable.model
        record_data = self.prepareRecordData(record_data)
        sql_flds = []
        for k in record_data.keys():
            sql_flds.append('%s=%s' % (tblobj.sqlnamemapper[k], ':%s' % k))
        pkeyColumn = tblobj.pkey
        if pkey:
            pkeyColumn='__pkey__'
            record_data[pkeyColumn]=pkey
        sql = 'UPDATE %s SET %s WHERE %s=:%s;' % (tblobj.sqlfullname, ','.join(sql_flds), tblobj.sqlnamemapper[tblobj.pkey], pkeyColumn)
        return self.dbroot.execute(sql, record_data)
    
    def delete(self, dbtable, record_data):
        """Delete a record from the db. 
        All fields in record_data will be added: all keys must correspond to a column in the db.
        @param dbtable: a SqlTable object
        @param record_data: a dict compatible object containing at least one entry for the pkey column of the table."""
        tblobj=dbtable.model
        record_data = self.prepareRecordData(record_data)
        pkey = tblobj.pkey
        sql = 'DELETE FROM %s WHERE %s=:%s;' % (tblobj.sqlfullname, tblobj.sqlnamemapper[pkey], pkey)
        return self.dbroot.execute(sql, record_data)
    
    def sql_deleteSelection(self, dbtable, pkeyList):
        """Delete a selection from the table. It works only in SQL so
        no python trigger is executed.
        @param dbtable: the table object
        @param pkeyList: records to delete
        """
        tblobj=dbtable.model
        sql = 'DELETE FROM %s WHERE %s IN :pkeyList;' % (tblobj.sqlfullname, tblobj.sqlnamemapper[tblobj.pkey])
        return self.dbroot.execute(sql, sqlargs=dict(pkeyList=pkeyList))
        
    def emptyTable(self, dbtable):
        """Delete all table rows
        @param dbtable: a SqlTable object"""
        tblobj=dbtable.model
        sql = 'DELETE FROM %s;' % (tblobj.sqlfullname)
        return self.dbroot.execute(sql)
        
    def analyze(self):
        """Perform analyze routines on the db"""
        self.dbroot.execute('ANALYZE;')

    def vacuum(self, table='', full=False):
        """Perform analyze routines on the db"""
        self.dbroot.execute('VACUUM ANALYZE %s;' % table)

    def addForeignKeySql(self, c_name, o_pkg, o_tbl, o_fld, m_pkg, m_tbl, m_fld, on_up, on_del, init_deferred):
        statement = 'ALTER TABLE %s.%s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s.%s (%s)' % (m_pkg, m_tbl, c_name, m_fld, o_pkg, o_tbl, o_fld)
        for on_command,on_value in (('ON DELETE',on_del),('ON UPDATE',on_up)):
            if on_value: statement += ' %s %s'%(on_command,on_value)
        statement = '%s %s'%(statement,init_deferred or '')
        return statement

    def createSchemaSql(self, sqlschema):
        """Returns the sql command to create a new database schema"""
        return 'CREATE SCHEMA %s;' % sqlschema
        
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

    def addColumn(self, sqltable, sqlname, dtype='T', size=None, notnull=None, pkey=None):
        sqlcol = self.columnSqlDefinition(sqlname, dtype=dtype, size=size, notnull=notnull, pkey=pkey)
        self.dbroot.execute('ALTER TABLE %s ADD COLUMN %s' % (sqltable, sqlcol))

    def columnSqlDefinition(self, sqlname, dtype, size, notnull, pkey):
        """
        returns the statement string for creating a table's column
        """
        sql = '%s %s' % (sqlname, self.revTypesDict[dtype])
        if dtype == 'A':
            if ':' in size:
                sql = '%s(%s)' % (sql, size.split(':')[1])
            else:
                sql = '%s %s(%s)' % (sqlname, self.revTypesDict['C'], size)
                
        if notnull:
            sql = sql + ' NOT NULL'
        if pkey:
            sql = sql + ' PRIMARY KEY'
        return sql
    
    def dropTable(self, sqltable):
        """Create a new database schema"""
        if '.' in sqltable:
            sqlschema, table = sqltable.split('.')
        else:
            sqlschema = self.defaultMainSchema
            table = sqltable
        if table in self.listElements('tables', schema=sqlschema):
            self.dbroot.execute('DROP TABLE %s;' % sqltable)
            
    def dropIndex(self, index_name, sqlschema=None):
        """drop an index
        @param index_name: name of the index (unique in schema)"""
        if sqlschema:
            index_name='%s.%s' % (sqlschema,index_name)
        return "DROP INDEX IF EXISTS %s;" % index_name
    
    def createIndex(self, index_name, columns, table_sql, sqlschema=None, unique=None):
        """create a new index
        @param index_name: name of the index (unique in schema)
        @param columns: comma separated list of columns to include in the index
        @param table_sql: actual sql name of the table
        @parm sqlschema: actual sql name of the schema
        @unique: boolean for unique indexing"""
        if sqlschema: 
            table_sql = '%s.%s' % (sqlschema, table_sql)
        if unique:
            unique = 'UNIQUE '
        else:
            unique = ''
        return "CREATE %sINDEX %s ON %s (%s);" % (unique, index_name, table_sql, columns)
        
    def createDbSql(self, dbname, encoding):
        pass

    def getWhereTranslator(self):
        return GnrWhereTranslator()

class GnrWhereTranslator(object):
    def __init__(self):
        self.catalog = GnrClassCatalog()
        
    def __call__(self, tblobj, wherebag, sqlArgs, workdate=None, locale=None):
        if sqlArgs is None:
            sqlArgs = {}
        self.locale = getattr(wherebag, '_locale', None)
        self.workdate = getattr(wherebag, '_workdate', None)
        result = self.innerFromBag(tblobj, wherebag, sqlArgs, 0)
        self.locale = None
        self.workdate = None
        return '\n'.join(result)
        
    def opCaption(self,op):
         h = getattr(self, 'op_%s' % op.lower(),None)
         if not h and op.startswith('not_'):
             return 'Not %s'% getattr(self, 'op_%s' % op[4:].lower()).__doc__
         return h.__doc__
         
    def innerFromBag(self, tblobj, wherebag, sqlArgs, level):
        """<condition column="fattura_num" op="ISNULL" rem='senza fattura' />
        <condition column="@anagrafica.provincia" op="IN" jc='AND'>MI,FI,TO</condition>
        <group not="true::B" jc='AND'>
                <condition column="" op=""/>
                <condition column="" op="" jc='OR'/>
        </group>"""
        
        result = []
        for node in wherebag:
            attr=node.getAttr()
            value=node.getValue()
            if isinstance(value, basestring) and value.startswith('?'):
                value=sqlArgs.get(value[1:])
            jc=attr.get('jc', '').upper()
            negate=attr.get('not')
            if isinstance(value, Bag):
                onecondition = ('\n'+'    '*level).join(self.innerFromBag(tblobj,value,sqlArgs,level+1))
                onecondition = '(\n'+'    '*level+onecondition+'\n'+'    '*level+')'
            else:
                op = attr['op']
                column = attr['column']
                dtype = tblobj.column(column).dtype
                if not column[0] in '@$':
                    column = '$%s' % column
                if dtype in('D','DH'):
                    value, op = self.decodeDates(value, op, dtype)
                if not dtype in ('A','T') and op in ('contains','notcontains','startswith','endswith','regex','wordstart'):
                    value=str(value)
                    column='CAST (%s as text)'%column
                    dtype='A'
                ophandler = getattr(self, 'op_%s' % op,None)
                if not ophandler and op.startswith('not_'):
                    ophandler=getattr(self, 'op_%s' % op[4:])
                    onecondition = '(NOT %s)'% ophandler(column, value, dtype, sqlArgs)
                else:
                    onecondition = ophandler(column, value, dtype, sqlArgs)
            if negate:
                onecondition = '(NOT %s)' % onecondition
            result.append(' %s %s' % (jc, onecondition ))
        return result

    def decodeDates(self, value, op, dtype):    
        if op == 'isnull':
            return value, op
        if op == 'in' and ',' in value: # is a in search with multiple (single date) arguments: don't use periods!!!
            value = ','.join([decodeDatePeriod(v, workdate=self.workdate, locale=self.locale,dtype=dtype) for v in value.split(',')])
            return value, op
            
        value = decodeDatePeriod(value, workdate=self.workdate, locale=self.locale,dtype=dtype)
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
                
    def storeArgs(self, value, dtype, sqlArgs):
        if not dtype in ('A','T'):
            if isinstance(value, list):
                value = [self.catalog.fromText(v, dtype) for v in value]
            elif isinstance(value, basestring):
                value=self.catalog.fromText(value, dtype)
        argLbl ='v_%i' %  len(sqlArgs)
        sqlArgs[argLbl]=value
        return argLbl

    def op_startswithchars(self, column, value, dtype, sqlArgs):
        "Starts with Chars"
        return '%s LIKE :%s' % (column, self.storeArgs('%s%%' % value, dtype, sqlArgs))
        
    def op_equal(self, column, value, dtype, sqlArgs):
        "Equal to"
        return '%s = :%s' % (column, self.storeArgs(value, dtype, sqlArgs))
   #def op_not_equal(self, column, value, dtype, sqlArgs):
   #    "Not equal to"
   #    return '%s <> :%s' % (column, self.storeArgs(value, dtype, sqlArgs))
        
    def op_startswith(self, column, value, dtype, sqlArgs):
        "Starts with"
        return '%s ILIKE :%s'  % (column, self.storeArgs('%s%%' % value, dtype, sqlArgs))
        
    def op_not_startswith(self, column, value, dtype, sqlArgs):
        "Not starts with"
        return ' (NOT %s) '% self.op_startswith(column, value, dtype, sqlArgs)
        
    def op_wordstart(self, column, value, dtype, sqlArgs):
        "Word start"
        value = value.replace('(','\(').replace(')','\)').replace('[','\[').replace(']','\]')
        return '%s ~* :%s' % (column, self.storeArgs('(^|\\W)%s' % value, dtype, sqlArgs))
        
    def op_contains(self, column, value, dtype, sqlArgs):
        "Contains"
        return '%s ILIKE :%s' % (column, self.storeArgs('%%%s%%' % value, dtype, sqlArgs))
        
    def op_not_contains(self, column, value, dtype, sqlArgs):
        "Doesn't contain"
        return '%s NOT ILIKE :%s' % (column, self.storeArgs('%%%s%%' % value, dtype, sqlArgs))
        
    def op_greater(self, column, value, dtype, sqlArgs):
        "Greater than"
        return '%s > :%s' % (column, self.storeArgs(value,dtype,sqlArgs))
        
    def op_greatereq(self, column, value, dtype, sqlArgs):
        "Greater or equal to"
        return '%s >= :%s' % (column, self.storeArgs(value, dtype, sqlArgs))
        
    def op_less(self, column, value, dtype, sqlArgs):
        "Less than"
        return '%s < :%s' % (column, self.storeArgs(value, dtype, sqlArgs))
        
    def op_lesseq(self, column, value, dtype, sqlArgs):
        "Less or equal to"
        return '%s <= :%s' % (column, self.storeArgs(value, dtype, sqlArgs))
        
    def op_between(self, column, value, dtype, sqlArgs):
        "Between"
        v1, v2 = value.split(';')
        return '%s BETWEEN :%s AND :%s' % (column, self.storeArgs(v1,dtype,sqlArgs),self.storeArgs(v2,dtype,sqlArgs))
        
    def op_isnull(self, column, value, dtype, sqlArgs):
        "Is null"
        return '%s IS NULL' % column
    
    def op_not_isnull(self, column, value, dtype, sqlArgs):
        "Is not null"
        return '%s IS NOT NULL' % column
        
    def op_in(self, column, value, dtype, sqlArgs):
        "In"
        values_string = self.storeArgs(value.split(','), dtype, sqlArgs)
        return '%s IN :%s' % (column, values_string)
    
    def op_not_in(self, column, value, dtype, sqlArgs):
        "Not in"
        values_string = self.storeArgs(value.split(','), dtype, sqlArgs)
        return '%s NOT IN :%s' % (column, values_string)
            
    def op_regex(self, column, value, dtype, sqlArgs):
        "Regular expression"
        return '%s ~* :%s' % (column, self.storeArgs(value, dtype, sqlArgs))

class GnrDictRow(GnrNamedList):
    """A row object that allow by-column-name access to data, the capacity to add columns and alter data."""
    def __init__(self, cursor, values=None):
        self._index = cursor.index
        if values is None:
            self[:] = [None] * len(cursor.description)
        else:
            self[:] = values
        

class NotImplementedException(Exception): 
    pass
