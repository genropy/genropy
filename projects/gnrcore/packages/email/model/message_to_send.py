# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('message_to_send', pkey='message_id',
                        name_long='!!Sending messages', order_by='$__ins_ts')
        self.sysFields(tbl, id=False)
        tbl.column('message_id', size='22', group='_', name_long='Message'
                   ).relation('message.id', one_one=True, onDelete='cascade',
                              relation_name='sending_index')

    def addMessageToQueue(self, message_id):
        if not self.existsRecord(message_id):
            self.insert(self.newrecord(message_id=message_id))

    def removeMessageFromQueue(self, message_id):
        self.deleteSelection('message_id', message_id)
