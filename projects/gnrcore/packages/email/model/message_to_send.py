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

    def addMessageToQueue(self,message_id):
        dbstore = self.db.currentEnv.get('storename')
        with self.db.tempEnv(storename=False):
            self.insert(self.newrecord(message_id=message_id,dbstore=dbstore))

    def removeMessageFromQueue(self,message_id):
        with self.db.tempEnv(storename=False):
            self.deleteSelection('message_id',message_id)

    def sendMessages(self):
        self.dispatchMessages(self.db.table('email.message').sendMessage)

    def dispatchMessages(self,dispatchCb,**kwargs):
        result = []
        with self.db.tempEnv(storename=False):
            messages_to_send = self.query(**kwargs).fetchGrouped('dbstore')
        for dbstore,message_pkeys in messages_to_send.items():
            with self.db.tempEnv(storename=dbstore or False):
                for m_pkey in message_pkeys:
                    result.append(dispatchCb(m_pkey))
