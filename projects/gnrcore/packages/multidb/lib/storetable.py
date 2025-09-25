from gnr.app.gnrdbo import GnrDboTable


class StoreTable(GnrDboTable):

    def config_db_multidb(self,pkg):
        tblname = self._tblname
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
        print('self.db.dbstores',self.db.dbstores)
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
        if self.db.application.site.multidomain:
            self.db.application.site.setDomain(dbstore)
        if dbstore in self.db.stores_handler.get_dbdict():
            self.db.stores_handler.refresh_dbstores()
        else:
            self.db.stores_handler.create_dbstore(dbstore)
            self.db.stores_handler.dbstore_align(dbstore)
            master_index = self.db.tablesMasterIndex()['_index_']
            for tbl in master_index.digest('#a.tbl'):
                tbl = self.db.table(tbl)
                startupData = tbl.multidb=='*' or tbl.isInStartupData()
                if not startupData:
                    continue
                main_f = tbl.query(addPkeyColumn=False,bagFields=True,subtable='*',columns=tbl.real_columns,
                                    ignorePartition=True,excludeDraft=False).fetch()
                if not main_f:
                    continue
                print('insert for table',tbl.fullname)
                with self.db.tempEnv(storename=dbstore):
                    tbl.insertMany(main_f)
            with self.db.tempEnv(storename=dbstore):
                self.db.commit()

    def trigger_onDeleted_multidb(self,record):
        if record['dbstore']:
            self.db.stores_handler.refresh_dbstores()
            self.db.application.site.domains.pop(record['dbstore'],None)
