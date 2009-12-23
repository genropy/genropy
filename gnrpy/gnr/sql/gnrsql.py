#-*- coding: UTF-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql : Genro sql db connection.
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

__version__='1.0b'

import re
from gnr.core.gnrlog import gnrlogging
gnrlogger = gnrlogging.getLogger('gnr.sql.gnrsql')

from gnr.core.gnrlang import getUuid
from gnr.core.gnrlang import GnrObject
from gnr.core.gnrlang import gnrImport
from gnr.core.gnrbag import Bag
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.sql.gnrsqlmodel import DbModel
from gnr.sql.gnrsql_exceptions import GnrSqlException,GnrSqlExecutionException,\
                                      GnrSqlSaveChangesException

#from gnr.sql.adapters import *

import thread

IN_OPERATOR_PATCH=re.compile(r'\s\S+\sIN\s\(\)')

class GnrSqlDb(GnrObject):
    """
       This is the main class of the gnrsql module.
       A GnrSqlDb object has the following purposes:
         -manage the logical structure of a database, called database's model.
         -manage operations on db at high level, hiding adapter's layer and
         connections.
    """
    def __init__(self, implementation='sqlite', dbname='mydb',
                 host=None, user=None, password=None, port=None,
                 main_schema=None,debugger=None):
        """
        This is the constructor method of the GnrSqlDb class. 
        @param implementation: 'sqlite' or 'postgres' or other sql implementations.
        @param dbname: the name for your db.
        @param host: the database server host (for sqlite is None)
        @param user: a database user's name (for sqlite is None)
        @param password: the user's password (for sqlite is None)
        @param port: the connection port (for sqlite is None)
        @param main_schema: the database main_schema
        """
        
        self.dbname = dbname
        self.implementation=implementation
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.typeConverter = GnrClassCatalog()
        self.debugger=debugger
        
        # All available adapter modules are already imported.
        # GnrSqlDb instantiates the SqlDbAdapter specified by 
        # the parameter implementation.
        #self.adapter = globals()['gnr%s' % implementation].SqlDbAdapter(self)
        self.adapter = gnrImport('gnr.sql.adapters.gnr%s' % implementation).SqlDbAdapter(self)
        self.whereTranslator = self.adapter.getWhereTranslator()
        if main_schema is None: 
            main_schema = self.adapter.defaultMainSchema()
        self.main_schema = main_schema
        self.model = DbModel(self)
        self._connections = {}
        self.started = False
        
#    def __del__(self): # deprecated?
#        self.closeConnection()
#        object.__del__(self)
        
    #------------------------Configure and Startup-----------------------------
    def startup(self):
        """Build the model.obj from the model.src"""
        self.model.build()
        self.started = True
        
    def packageSrc(self, name):
        """Return a DbModelSrc corresponding to the required package
        @param name: the package name"""
        return self.model.src.package(name)
    
    def packageMixin(self, name, obj):
        """Register a mixin for a package.
        @param name: the target package's name
        @param obj: a class or an object to mixin
        """
        self.model.packageMixin(name, obj)
        
    def tableMixin(self, tblpath, obj):
        """Register an object or a class to mixin to a table.
        @param name: the target package's name
        @param obj: a class or an object to mixin
        """
        self.model.tableMixin(tblpath, obj)
        
    def loadModel(self, source=None):
        """Load the model.src from a xml source
        @param source: xml model (diskfile or text or url)
        """
        self.model.load(source)
        
    def importModelFromDb(self):
        """Load the model.src extracting it from the database's
        information schema.
        """
        self.model.importFromDb()
        
    def saveModel(self, path):
        """Save the current model as xml file at path
        @param path: the file path
        """
        self.model.save(path)
        
    def checkDb(self, applyChanges=False):
        """Check if there the database structure is compatible with the current model
        @param applyChanges: boolean. If True, all the changes are executed and committed
        """
        return self.model.check(applyChanges=applyChanges)
        
    def closeConnection(self):
        """Close a connection"""
        if self._connections.get(thread.get_ident()) != None:
            try:
                self._connections[thread.get_ident()].close()
                self._connections[thread.get_ident()] = None
            except Exception:
                self._connections[thread.get_ident()] = None
     #          pass
     #      finally:
     #          self._connections[thread.get_ident()] = None
    
    
    def _get_connection(self):
        """property .connection
        If there's not connection open and return connection to database"""
        if not self._connections.get(thread.get_ident()):
            self._connections[thread.get_ident()] = self.adapter.connect()
        return self._connections[thread.get_ident()]
    connection = property(_get_connection)
    
    def execute(self, sql, sqlargs=None, cursor=None, cursorname=None, autocommit=False):
        
        """Execute the sql statement using given kwargs"""
        # transform list and tuple parameters in named values.
        # Eg.   WHERE foo IN:bar ----> WHERE foo in (:bar_1, :bar_2..., :bar_n)
        sqlargs = sqlargs or {}
        for k, v in [(k, v) for k, v in sqlargs.items() if isinstance(v, list) or isinstance(v, tuple)]:
            sqllist = '(%s) ' % ','.join([':%s%i' % (k, i) for i, ov in enumerate(v)])
            sqlargs.pop(k)
            sqlargs.update(dict([('%s%i' % (k, i), ov) for i, ov in enumerate(v)]))
            sql = re.sub(':%s(\W|$)' % k, sqllist , sql)
        sql = re.sub(IN_OPERATOR_PATCH,' FALSE', sql)

        sql, sqlargs = self.adapter.prepareSqlText(sql, sqlargs)
        #gnrlogger.info('Executing:%s - with kwargs:%s \n\n',sql,unicode(kwargs))
        #print 'sql:\n',sql

        try:
            if not cursor:
                #if not self.connection: self.connection=self.adapter.connect()
                if cursorname:
                    if cursorname == '*':
                        cursorname = 'c%s' % re.sub('\W', '_', getUuid())
                    cursor = self.adapter.cursor(self.connection, cursorname)
                    #cursor = self.connection.cursor(cursorname=cursorname)
                else:
                    cursor = self.adapter.cursor(self.connection)
                    #cursor = self.connection.cursor()
            if self.debugger:
                self.debugger(cursor=cursor, sql=sql, sqlargs=sqlargs)
            cursor.execute(sql, sqlargs)
        except Exception, e:
            #print sql
            gnrlogger.warning('error executing:%s - with kwargs:%s \n\n', sql, unicode(sqlargs))
            #raise str('error %s executing:%s - with kwargs:%s \n\n' % (str(e), sql, unicode(sqlargs).encode('ascii', 'ignore')))
            self.rollback()
            raise e
        if autocommit:
            self.commit()
        return cursor
        
    def insert(self, tblobj, record):
        """Insert a record in the table.
        @param tblobj: the table object
        @param record: an object implementing dict interface as colname, colvalue
        """
        newkey = tblobj.checkPkey(record)
        tblobj._doFieldTriggers('onInserting', record)
        tblobj.trigger_onInserting(record)
        self.adapter.insert(tblobj, record)
        tblobj.trigger_onInserted(record)

    def update(self, tblobj, record, old_record=None, pkey=None):
        """Update a record of the table.
        @param tblobj: the table object
        @param record: an object implementing dict interface as colname, colvalue
        """
        tblobj._doFieldTriggers('onUpdating', record)
        tblobj.trigger_onUpdating(record, old_record=old_record)
        self.adapter.update(tblobj, record, pkey=pkey)
        tblobj.trigger_onUpdated(record, old_record=old_record)

        
    def delete(self, tblobj, record):
        """Delete a record from the table.
        @param tblobj: the table object
        @param record: an object implementing dict interface as colname, colvalue
        """
        tblobj._doFieldTriggers('onDeleting', record)
        tblobj.trigger_onDeleting(record)
        tblobj.deleteRelated(record)
        self.adapter.delete(tblobj, record)
        tblobj.trigger_onDeleted(record)
        
    def commit(self):
        """Commit a transaction"""
        self.connection.commit()
        
    def rollback(self):
        """Rollback a transaction """
        self.connection.rollback()
            
    def listen(self, *args, **kwargs):
        """Listen for a database event (postgres)"""
        self.adapter.listen(*args, **kwargs)
        
    def notify(self, *args, **kwargs):
        """Database Notify"""
        self.adapter.notify(*args, **kwargs)
    
    def analyze(self):
        """Analyze db"""
        self.adapter.analyze()
        
    def vacuum(self):
        """Analyze db"""
        self.adapter.vacuum()
        
    #------------------ PUBLIC METHODS--------------------------
    
    def package(self, pkg):
        """Returns a package object
        @param pkw: package name"""
        return self.model.package(pkg)
    
    def _get_packages(self):
        """Returns a package object
        @param pkw: package name"""
        return self.model.obj
    packages = property(_get_packages)
    
    def table(self, tblname, pkg=None):
        """returns a table object
        @param table: table name
        @param pkg: package name"""
        return self.model.table(tblname, pkg=pkg).dbtable
    
    def query(self, table, **kwargs):
        """See gnrsqltable.SqlTable.query"""
        return self.table(table).query(**kwargs)
        
    def colToAs(self, col):
        as_ = re.sub('\W','_',col)
        if as_[0].isdigit(): as_ = '_' + as_
        return as_
        
    def relationExplorer(self, table, prevCaption='', prevRelation='',
                        transaltor=None, **kwargs):
        return self.table(table).relationExplorer(prevCaption=prevCaption, 
                                                  prevRelation=prevRelation,
                                                  transaltor=transaltor, **kwargs)
        
    def createDb(self, name, encoding='unicode'):
        """Create a db with given name and encoding
        @param name
        @param encoding"""
        self.adapter.createDb(name, encoding=encoding)
        
    def dropDb(self, name):
        """Drop a db with given name
        @param name"""
        self.adapter.dropDb(name)
        
    def dump(self,filename):
        """Dump db to a given path
        @param name"""
        self.adapter.dump(filename)
        
    def restore(self,filename):
        """Restore db to a given path
        @param name"""
        #self.dropDb(self.dbname)
        #self.createDb(self.dbname)
        self.adapter.restore(filename)
        
    def createSchema(self, name):
        """Create a db schema
        @param name"""
        self.adapter.createSchema(name)
        
    def dropSchema(self, name):
        """Drop a db schema
        @param name"""
        self.adapter.dropSchema(name)

    def importXmlData(self, path):
        """Populates a database from an xml file
        @param path: filepath
        """
        data = Bag(path)
        for table, pkg in data.digest('#k,#a.pkg'):
            for n in data[table]:
                self.table(table, pkg=pkg).insertOrUpdate(n.attr)
if __name__=='__main__':
    pass
    
    