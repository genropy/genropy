from contextlib import ExitStack, contextmanager

from gnr.app.gnrdbo import GnrDboTable
from gnr.app import pkglog as logger
from gnr.sql.adapters._gnrbaseadapter import DbAdapterException


class StoreTable(GnrDboTable):

    def config_db_multidb(self,pkg):
        tblname = self._tblname
        tbl = pkg.table(tblname,storetable=True,multidb='one',inStartupData=False)
        tbl.column('dbstore',size=':30',name_long='!![en]DbStore',unique=True,indexed=True,validate_case='l',
                                                                validate_regex='![^A-Za-z0-9_]', 
                                                                validate_regex_error='!![en]Invalid characters')
        tbl.column('dbtemplate', name_long='!![en]Db template', name_short='!![en]Db template')
        tbl.column('preferences','X',name_long='!![en]Preferences')
        tbl.column('provisioning_status', size=':20', name_long='!![en]Provisioning status')
        tbl.column('provisioning_error', dtype='T', name_long='!![en]Provisioning error')
        tbl.column('startup_data_ts',dtype='DHZ',name_long='Startup data ts')
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


    @contextmanager
    def _multidb_provisioningLock(self, dbstore):
        with ExitStack() as stack:
            try:
                stack.enter_context(self.db.adapter.databaseLock(f'{self.db.multidb_prefix}{dbstore}'))
            except DbAdapterException as exc:
                raise self.exception('business_logic',
                                     msg='!![en]Workspace %(store)s is being provisioned by another request',
                                     store=dbstore) from exc
            yield

    def _multidb_setProvisioningStatus(self, pkey, status, error=None):
        with self.recordToUpdate(pkey) as rec:
            rec['provisioning_status'] = status
            rec['provisioning_error'] = error
        self.db.commit()
        self.db.stores_handler.refresh_dbstores()

    def multidb_activateDbstore(self, record):
        record = self.recordAs(record, 'dict')
        dbstore = record['dbstore']
        if not dbstore:
            raise self.exception('business_logic', msg='!![en]Missing database store name')
        with self._multidb_provisioningLock(dbstore):
            # Re-read after acquiring the cross-process lock; the input can be stale.
            record = self.record(pkey=record[self.pkey]).output('dict')
            status = record.get('provisioning_status')
            handler = self.db.stores_handler
            dbname = f'{self.db.multidb_prefix}{dbstore}'
            existing_db = self.db.adapter.dbExists(dbname)
            if status == 'ready':
                if not existing_db:
                    raise self.exception('business_logic',
                                         msg='!![en]The activated database is missing; restore it before continuing')
                handler.refresh_dbstores()
                handler.dbstore_align(dbstore)
                return
            legacy_import = existing_db and (not status or status in ('aligning_import', 'failed_import'))
            previous_aux = handler.auxstores.get(dbstore)
            phase = 'create'
            try:
                self._multidb_setProvisioningStatus(
                    record[self.pkey], 'aligning_import' if legacy_import else 'creating')
                if not existing_db:
                    # dbtemplate names a startup-data archive, not a database.
                    self.db.createDb(dbname, template=self.attributes.get('db_creation_template'))
                phase = 'align'
                self._multidb_setProvisioningStatus(
                    record[self.pkey], 'aligning_import' if legacy_import else 'aligning')
                # Pending stores are not published. Only this worker needs the
                # connection configuration while building their schema.
                handler.add_auxstore(dbstore, dbattr=dict(dbname=dbname))
                handler.dbstore_align(dbstore)
                if legacy_import:
                    with self.recordToUpdate(record[self.pkey]) as rec:
                        rec['startup_data_ts'] = self.newUTCDatetime()
                self._multidb_setProvisioningStatus(record[self.pkey], 'ready')
            except Exception as exc:
                self.db.rollback()
                logger.exception('Store %s: provisioning failed during %s', dbstore, phase)
                try:
                    self._multidb_setProvisioningStatus(
                        record[self.pkey], 'failed_import' if legacy_import else 'failed',
                        f'{phase}: {exc}')
                except Exception:
                    self.db.rollback()
                    logger.exception('Store %s: unable to record the provisioning failure', dbstore)
                raise self.exception(
                    'business_logic',
                    msg='!![en]Workspace %(store)s failed during %(phase)s: %(error)s',
                    store=dbstore, phase=phase, error=str(exc)) from exc
            finally:
                if previous_aux is None:
                    handler.auxstores.pop(dbstore, None)
                else:
                    handler.auxstores[dbstore] = previous_aux

    def multidb_setStartupData(self, pkey):
        record = self.record(pkey=pkey).output('dict')
        with self._multidb_provisioningLock(record['dbstore']):
            record = self.record(pkey=pkey).output('dict')
            if record['startup_data_ts']:
                return
            if record.get('provisioning_status') not in (None, 'ready'):
                raise self.exception('business_logic',
                                     msg='!![en]Complete workspace activation first')
            try:
                self._multidb_setStartupData(pkey)
            except Exception:
                self.db.rollback()
                raise

    def _multidb_setStartupData(self,pkey):
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
            self.db.application.dbUpgradeBroadcast()
            self.db.table('adm.counter').initializeApplicationSequences()
        record['startup_data_ts'] = self.newUTCDatetime()
        self.update(record,old_rec)
        self.db.commit()

    def multidb_setStartupData_whitelist(self):
        return []

    def trigger_onDeleted_multidb(self,record):
        if record['dbstore']:
            self.db.stores_handler.refresh_dbstores()
            site = self.db.application.site
            site.domains.remove(record['dbstore'])
            if site.multidomain:
                domainIdentifier = site.get_domainIdentifier(record['dbstore'])
                self.db.deferAfterCommit(self.multidb_stopDomainRegister,
                                         domainIdentifier=domainIdentifier,
                                         _deferredId=domainIdentifier)

    def multidb_stopDomainRegister(self,domainIdentifier=None):
        try:
            self.db.application.site.register.gnrdaemon_proxy.siteregister_stop(domainIdentifier)
        except Exception:
            logger.exception('Unable to stop the site register of %s', domainIdentifier)
