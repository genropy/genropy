from gnr.app.gnrdbo import GnrDboTable


class StoreTable(GnrDboTable):

    def config_db_multidb(self,pkg):
        tblname = self._tblname
        self.db.storetable = f'{pkg.parentNode.label}.{tblname}'
        tbl = pkg.table(tblname,storetable=True)
        tbl.column('dbstore',size=':30',name_long='!![en]DbStore',unique=True,indexed=True,validate_case='l',
                                                                validate_regex='![^A-Za-z0-9_]', 
                                                                validate_regex_error='!![en]Invalid characters')
        tbl.column('dbtemplate', name_long='!![en]Db template', name_short='!![en]Db template')
        tbl.column('preferences','X',name_long='!![en]Preferences')
        tbl.pyColumn('active_dbstore',dtype='B',name_long='Active dbstore')



    def multidb_removeStore(self,dbstore):
        pass

    def multidb_addStore(self,dbstore):
        pass

    def pyColumn_active_dbstore(self,record,**kwargs):
        if not record['dbstore']:
            return False
        return record["dbstore"] in self.db.dbstores
    


    def activate_dbstore(self,dbstore):
        dbname = None
        record = self.recordAs(record)
        dbname = '%s_%s' % (self.db.dbname, dbstore)

        #    self.db.stores_handler.add_dbstore_config(
        #        dbstore, dbname=dbname, save=True)
        #    record = dict(dbstore=dbstore, denominazione=denominazione)
        #    self.db.package('multidb').checkFullSyncTables(dbstores=[dbstore],
        #                                                packages=['glbl', 'erpy_base', 'erpy_coge','erpy_fatt','erpy_ftel'])
        #    self.db.table('erpy_studio.contabilita').insert(record)
        #self.db.commit()
