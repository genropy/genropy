# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('push_notification', pkey='id', name_long='Push notification', 
                      name_plural='Push notifications')
        self.sysFields(tbl)
        tbl.column('message_identifier', size='22', name_long='Message identifier')
        tbl.column('sender', group='_', name_long='Sender'
                    ).relation('adm.user.username', 
                               relation_name='sent_notifications', 
                               onDelete='raise')
        tbl.column('subscription_id',size='22', group='_', name_long='Receiver Subscription'
                    ).relation('adm.push_subscription.id', relation_name='received_notifications', 
                               mode='foreignkey', onDelete='raise')
        tbl.column('send_ts', dtype='DHZ', name_long='Send TS')
        tbl.column('click_ts', dtype='DHZ', name_long='Click TS')
        tbl.column('title', name_long='Title')
        tbl.column('message',name_long='Message')
        tbl.column('url', name_long='Url')
        tbl.column('sending_error', name_long='Sending error')