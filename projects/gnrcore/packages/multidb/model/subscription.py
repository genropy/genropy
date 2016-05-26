# encoding: utf-8
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from copy import deepcopy
from gnrpkg.multidb.utils import GnrMultidbException

FIELD_BLACKLIST = ('__ins_ts','__mod_ts','__version','__del_ts','__moved_related')

class Table(object):

    def multidbExceptionClass(self):
        return GnrMultidbException


    def config_db(self, pkg):
        tbl =  pkg.table('subscription',pkey='id',name_long='!!Subscription',
                      name_plural='!!Subscriptions',broadcast='tablename,dbstore',ignoreUnify=True)
        self.sysFields(tbl)
        tbl.column('tablename',name_long='!!Tablename') #table fullname 
        #tbl.column('rec_pkey',name_long='!!Pkey') # if rec_pkey == * means all records
        tbl.column('dbstore',name_long='!!Store')
    
    def checkSubscribedRecord(self,table=None,pkey=None,dbstore=None):
        sub_record = dict()
        fkey = self.tableFkey(table)
        sub_record['tablename'] = table
        sub_record[fkey] = pkey
        sub_record['dbstore'] = dbstore
        if self.checkDuplicate(**sub_record):
            return
        self.insert(sub_record)
        
    def copyRecords(self,table,dbstore=None,pkeys=None):
        tblobj = self.db.table(table)
        queryargs = dict()
        if pkeys:
            queryargs = dict(where='$pkey IN :pkeys',pkeys=pkeys)
        if tblobj.attributes.get('hierarchical'):
            queryargs.setdefault('order_by','$hierarchical_pkey')
        records = tblobj.query(addPkeyColumn=False,bagFields=True,excludeLogicalDeleted=False,**queryargs).fetch()
        with self.db.tempEnv(storename=dbstore):
            for rec in records:
                tblobj.insertOrUpdate(Bag(dict(rec)))
            self.db.deferredCommit()  
    
    @public_method
    def addRowsSubscription(self,table,pkeys=None,dbstore=None):
        for pkey in pkeys:
            self.addSubscription(table,pkey=pkey,dbstore=dbstore)
        self.db.commit()
    
    def addSubscription(self,table=None,pkey=None,dbstore=None):
        tblobj = self.db.table(table)
        fkey = self.tableFkey(tblobj)
        record = dict(dbstore=dbstore,tablename=table)
        record[fkey] = pkey
        handler = getattr(tblobj,'onAddSubscription',None)
        if handler:
            handler(pkey,dbstore)
        if not self.checkDuplicate(**dict(record)):
            self.insert(record)

    
    @public_method
    def delRowsSubscription(self,table,pkeys=None,dbstore=None):
        for pkey in pkeys:
            self.delSubscription(table,pkey=pkey,dbstore=dbstore)
        self.db.commit()
    
    def delSubscription(self,table=None,pkey=None,dbstore=None):
        fkey = self.tableFkey(table)        
        f = self.query(where='$dbstore=:dbstore AND $tablename=:tablename AND $%s =:fkey' %fkey,for_update=True,
                            excludeLogicalDeleted=False,
                            dbstore=dbstore,tablename=table,fkey=pkey,addPkeyColumn=False).fetch()
        if f:
            self.delete(f[0])
    
    def trigger_onInserted(self,record):
        self.syncStore(record,'I')
    
    def trigger_onUpdated(self,record,old_record=None):
        self.syncStore(record,'U')

    def trigger_onDeleted(self,record):        
        self.syncStore(record,'D')

   #def cloneSubscriptions(self,table,sourcePkey,destPkey):
   #    sourcestores = self.query(where="""$tablename=:t AND $%s =:fkey""" %self.tableFkey(table),t=table,fkey=sourcePkey,columns='$dbstore').fetch()
   #    for store in sourcestores:
   #        self.addSubscription(table=table,pkey=destPkey,dbstore=store['dbstore'])

    def syncStore(self,subscription_record=None,event=None,storename=None,
                  tblobj=None,pkey=None,master_record=None,master_old_record=None,mergeUpdate=None):
        if subscription_record:
            table = subscription_record['tablename']
            pkey = subscription_record[self.tableFkey(table)]
            tblobj = self.db.table(table)
            storename = subscription_record['dbstore']
        if not self.db.dbstores.get(storename):
            return
        if master_record:
            data_record = deepcopy(master_record)
        else:
            data_record = tblobj.query(where='$%s=:pkey' %tblobj.pkey,pkey=pkey,addPkeyColumn=False,bagFields=True,excludeLogicalDeleted=False).fetch()
            if data_record:
                data_record = data_record[0]
            else:
                return
        with self.db.tempEnv(storename=storename,_systemDbEvent=True,_multidbSync=True):
            f = tblobj.query(where='$%s=:pkey' %tblobj.pkey,pkey=pkey,for_update=True,
                            addPkeyColumn=False,bagFields=True,excludeLogicalDeleted=False).fetch()
            if event == 'I':
                if not f:
                    tblobj.insert(data_record)
                else:
                    tblobj.update(data_record,f[0])
                self.db.deferredCommit()
            else:
                if f:
                    old_record = f[0]
                    if event=='U':
                        if mergeUpdate:
                            for k,v in data_record.items(): 
                                if (v!=old_record[k]) and (old_record[k] != master_old_record[k]):
                                    data_record.pop(k)
                        tblobj.update(data_record,old_record=old_record)
                    else:
                        tblobj.delete(data_record)
                    self.db.deferredCommit()
                elif event=='U':
                    tblobj.insert(data_record)   
                    self.db.deferredCommit()
                    
    def onPlugToForm(self,field):
        if self.db.currentPage.dbstore:
            return False
        return dict(lbl_color='red')
        
    def tableFkey(self,table):
        if isinstance(table,basestring):
            table = self.db.table(table)
        return '%s_%s' %(table.fullname.replace('.','_'),table.pkey)


    def getSubscriptionId(self,tblobj=None,pkey=None,dbstore=None):
        fkeyname = self.tableFkey(tblobj)
        f = self.query(where="""$tablename=:tablename AND 
                            $%s=:pkey AND 
                            $dbstore=:dbstore""" %fkeyname,
                            dbstore=dbstore,
                            tablename=tblobj.fullname,pkey=pkey).fetch()
        return f[0]['id'] if f else None
        
    def onSubscriberTrigger(self,tblobj,record,old_record=None,event=None):
        syncAllStores = tblobj.attributes.get('multidb_allRecords') or record.get('__multidb_default_subscribed')
        if self.db.usingRootstore():
            subscribedStores = self.getSubscribedStores(tblobj=tblobj,record=record,syncAllStores=syncAllStores)
            mergeUpdate = tblobj.attributes.get('multidb_onLocalWrite')=='merge'
            pkey = record[tblobj.pkey]
            for storename in subscribedStores:
                self.syncStore(event=event,storename=storename,tblobj=tblobj,pkey=pkey,
                                master_record=record,master_old_record=old_record,mergeUpdate=mergeUpdate)
        elif not self.db.currentEnv.get('_multidbSync'):
            self.onSubscriberTrigger_slavestore(tblobj,record,old_record=old_record,event=event,syncAllStores=syncAllStores)

    def getSubscribedStores(self,tblobj,record,syncAllStores=None):
        subscribedStores = []
        if tblobj.attributes.get('multidb_forcedStore'):
            store = tblobj.multidb_getForcedStore(record)
            if store:
                subscribedStores.append(store)
        elif syncAllStores:
            subscribedStores = self.db.dbstores.keys()
        else:
            tablename = tblobj.fullname
            fkeyname = self.tableFkey(tblobj)
            pkey = record[tblobj.pkey]
            subscribedStores = self.query(where='$tablename=:tablename AND $%s=:pkey' %fkeyname,
                                    columns='$dbstore',addPkeyColumn=False,
                                    tablename=tablename,pkey=pkey,distinct=True).fetch()                
            subscribedStores = [s['dbstore'] for s in subscribedStores]
        return subscribedStores

    def onSubscriberTrigger_slavestore(self,tblobj,record,old_record=None,event=None,syncAllStores=None):
        pkey = record[tblobj.pkey]
        if event=='I':
            print 'record',record,'table',tblobj.fullname
            raise GnrMultidbException(description='Multidb exception',msg="You cannot insert a record in a synced store %s" %tblobj.fullname)
        elif event=='D':
            if syncAllStores:
                raise GnrMultidbException(description='Multidb exception',msg="You cannot delete this record from a synced store")
            else:
                subscription_id = self.getSubscriptionId(tblobj=tblobj,dbstore=self.db.currentEnv.get('storename'),pkey=pkey)
                if subscription_id:
                    self.raw_delete(subscription_id) # in order to avoid subscription delete trigger
        else: #update
            onLocalWrite = tblobj.attributes.get('multidb_onLocalWrite') or 'raise'
            if onLocalWrite!='merge':
                raise GnrMultidbException(description='Multidb exception',msg="You cannot update this record in a synced store")


    def onSlaveUpdating(self,tblobj,record,old_record=None):
        if self.db.usingRootstore():
            return
        if self.db.currentEnv.get('_multidbSync'):
            if record.get(tblobj.logicalDeletionField)\
            and not old_record.get(tblobj.logicalDeletionField)\
            and record.get('__moved_related'):
                moved_related = Bag(record['__moved_related'])
                destPkey = moved_related['destPkey']
                destRecord = tblobj.query(where='$%s=:dp' %tblobj.pkey, 
                                          dp=destPkey).fetch()
                with self.db.tempEnv(connectionName='system'):
                    if destRecord:
                        destRecord = destRecord[0]
                    else:
                        storename = self.db.currentEnv['storename']
                        with self.db.tempEnv(storename=self.db.rootstore):
                            self.addSubscription(table=tblobj.fullname,pkey=destPkey,dbstore=storename)
                        
                        f = tblobj.query(where='$%s=:dp' %tblobj.pkey, 
                                              dp=destPkey).fetch()
                        destRecord = f[0]
                    tblobj.unifyRelatedRecords(sourceRecord=record,destRecord=destRecord,moved_relations=moved_related)
        else:
            onLocalWrite = tblobj.attributes.get('multidb_onLocalWrite') or 'raise'
            if onLocalWrite!='merge':
                raise GnrMultidbException(description='Multidb exception',msg="You cannot update this record in a synced store")



    def decoreMergedRecord(self,tblobj,record):
        main_record = tblobj.record(pkey=record[tblobj.pkey],
                                bagFields=True,excludeLogicalDeleted=False,
                                _storename=False).output('record')
        changelist = []
        for k,v in main_record.items():
            if k not in FIELD_BLACKLIST:
                if record[k] != v:
                    changelist.append(k)
                    record.setAttr(k,wdg__class='multidb_local_change',multidb_mainvalue=v)
        return ','.join(changelist)


    def getRecordDiff(self,main_record,store_record):
        result = dict()
        for k,v in main_record.items():
            if k not in FIELD_BLACKLIST:
                if store_record[k] != v:
                    result[k] = (v,store_record[k])
        return result




