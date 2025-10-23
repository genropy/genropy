# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('message_to_send', pkey='message_id', 
                      name_long='[en]Sending messages',order_by='$__ins_ts')
        self.sysFields(tbl,id=False)
        tbl.column('dbstore', name_long='Dbstore')
        tbl.column('message_id',size='22', group='_', name_long='Message'
                    ).relation('message.id',one_one=True,
                               relation_name='sending_index')  
        tbl.aliasColumn('proxy_priority','@message_id.proxy_priority')  

    def addMessageToQueue(self,message_id):
        dbstore = self.db.currentEnv.get('storename')
        with self.db.tempEnv(storename=False):
            self.insert(self.newrecord(message_id=message_id,dbstore=dbstore))

    def removeMessageFromQueue(self,message_id):
        with self.db.tempEnv(storename=False):
            self.deleteSelection('message_id',message_id)


    def sendMessages(self):
        """Sending message without proxy. One-by_one. Called by action in message_to_send resources"""
        results = []
        dispatch_cb = self.db.table('email.message').sendMessage
        with self.db.tempEnv(storename=False):
            messages_to_send = self.query().fetchGrouped('dbstore')
        for dbstore, rows in messages_to_send.items():
            target_store = dbstore or False
            with self.db.tempEnv(storename=target_store):
                for row in rows:
                    results.append(dispatch_cb(row['message_id']))
        return results

    def trigger_onInserted(self,record=None):
        self.db.deferToCommit(self.proxyRunNow,_deferredId='_proxy_communication_')
    
    def proxyRunNow(self):
        mailproxy = self.db.application.site.getService('mailproxy')
        if mailproxy:
            mailproxy.run_now()