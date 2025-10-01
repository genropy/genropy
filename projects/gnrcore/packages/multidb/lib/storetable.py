from gnr.app.gnrdbo import GnrDboTable


class StoreTable(GnrDboTable):

    def config_db_multidb(self,pkg):
        tblname = self._tblname
        tbl = pkg.table(tblname,storetable=True,multidb='one',inStartupData=False)
        tbl.column('dbstore',size=':30',name_long='!![en]DbStore',unique=True,indexed=True,validate_case='l',
                                                                validate_regex='![^A-Za-z0-9_]', 
                                                                validate_regex_error='!![en]Invalid characters')
        tbl.column('dbtemplate', name_long='!![en]Db template', name_short='!![en]Db template')
        tbl.column('preferences','X',name_long='!![en]Preferences')
        tbl.column('startup_data_ts',dtype='DHZ',name_long='Startup data ts')
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
        existing_db = dbstore in self.db.stores_handler.get_dbdict()
        if existing_db:
            self.db.stores_handler.refresh_dbstores()
            self.db.stores_handler.dbstore_align(dbstore)
            with self.recordToUpdate(dbstore=dbstore) as rec:
                rec['startup_data_ts'] = self.newUTCDatetime()
        else:
            self.db.stores_handler.create_dbstore(dbstore)
            self.db.stores_handler.dbstore_align(dbstore)
        
        self.db.commit()


    def multidb_setStartupData(self,pkey):
        record = self.record(pkey=pkey,for_update=True).output('dict')
        dbstore = record['dbstore']
        master_index = self.db.tablesMasterIndex()['_index_']
        tables = master_index.digest('#a.tbl')
        if self.db.currentPage:
            tables = self.db.currentPage.utils.quickThermo(tables,maxidx=len(tables),labelcb = lambda tbl:tbl)
        for tblname in tables:
            tbl = self.db.table(tblname)
            startupData = tbl.multidb=='*' or tbl.isInStartupData() or tblname in self.multidb_setStartupData_whitelist()
            if not startupData:
                continue
            main_f = tbl.query(addPkeyColumn=False,bagFields=True,subtable='*',columns=tbl.real_columns,
                                ignorePartition=True,excludeDraft=False).fetch()
            if not main_f:
                continue
            with self.db.tempEnv(storename=dbstore):
                tbl.insertMany(main_f)
            old_rec = dict(record)
        with self.db.tempEnv(storename=dbstore):
            self.db.application.pkgBroadcast('onDbUpgrade,onDbUpgrade_*')
            self.db.table('adm.counter').initializeApplicationSequences()
        record['startup_data_ts'] = self.newUTCDatetime()
        self.update(record,old_rec)
        self.db.commit()

    def multidb_setStartupData_whitelist(self):
        return []

    def trigger_onDeleted_multidb(self,record):
        if record['dbstore']:
            self.db.stores_handler.refresh_dbstores()
            self.db.application.site.domains.pop(record['dbstore'],None)
