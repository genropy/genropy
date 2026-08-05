# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('message_to_send', pkey='message_id',
                        name_long='!!Sending messages', order_by='$__ins_ts')
        self.sysFields(tbl, id=False)
        tbl.column('message_id', size='22', group='_', name_long='Message'
                   ).relation('message.id', one_one=True, onDelete='cascade',
                              relation_name='sending_index')
        tbl.aliasColumn('proxy_priority', '@message_id.proxy_priority')
        tbl.aliasColumn('batch_code', '@message_id.batch_code')

    def addMessageToQueue(self, message_id):
        if not self.existsRecord(message_id):
            self.insert(self.newrecord(message_id=message_id))

    def removeMessageFromQueue(self, message_id):
        if isinstance(message_id, list):
            self.deleteSelection(where='$message_id IN :pkeys', pkeys=message_id)
        else:
            self.deleteSelection('message_id', message_id)

    def trigger_onInserted(self, record=None):
        self.db.deferAfterCommit(self.proxyRunNow, _deferredId='_proxy_communication_')

    def proxyRunNow(self):
        mailproxy = self.pkg.getMailProxy(raise_if_missing=False)
        if mailproxy:
            mailproxy.run_now()
