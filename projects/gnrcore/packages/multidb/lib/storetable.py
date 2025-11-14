from gnr.app.gnrdbo import GnrDboTable


class StoreTable(GnrDboTable):

    def config_db_multidb(self,pkg):
        tblname = self._tblname
        self.db.storetable = f'{pkg.parentNode.label}.{tblname}'
        tbl = pkg.table(tblname,storetable=True,multidb='one')
        tbl.column('dbstore',size=':30',name_long='!![en]DbStore',unique=True,indexed=True,validate_case='l',
                                                                validate_regex='![^A-Za-z0-9_]', 
                                                                validate_regex_error='!![en]Invalid characters')
        tbl.column('dbtemplate', name_long='!![en]Db template', name_short='!![en]Db template')
        tbl.column('preferences','X',name_long='!![en]Preferences')
        tbl.pyColumn('active_dbstore',dtype='B',name_long='Active dbstore')


    def pyColumn_active_dbstore(self,record,**kwargs):
        if not record['dbstore']:
            return False
        return record["dbstore"] in self.db.dbstores
    


    def multidb_getForcedStore(self,record):
        return record['dbstore']



    def multidb_removeStore(self,dbstore):
        pass

    def multidb_fullSyncActivationWhitelist(self):
        return


    def multidb_activateDbstore(self,record):
        record = self.recordAs(record,'dict')
        dbstore = record['dbstore']
        if not dbstore:
            raise self.exception('business_logic',msg=f'dbstore in record {record[self.pkey]}')
        self.db.stores_handler.create_dbstore(dbstore)
        self.db.stores_handler.dbstore_align(dbstore)
        self.db.package('multidb').checkFullSyncTables(dbstores=[dbstore],
                                                    packages=self.multidb_fullSyncActivationWhitelist())
        self.touchRecords(_pkeys=[record[self.pkey]])
