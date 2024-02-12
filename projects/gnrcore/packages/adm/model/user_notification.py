#!/usr/bin/env python
# encoding: utf-8


from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import TableTemplateToHtml
from gnr.core.gnrbag import Bag


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('user_notification', pkey='id', name_long='User notification', name_plural='!!User notifications')
        self.sysFields(tbl)
        tbl.column('user_id',size='22' ,group='_',name_long='!!User').relation('user.id',relation_name='user_notifications',mode='foreignkey',onDelete='cascade')
        tbl.column('notification_id',size='22' ,group='_',name_long='!!Notification').relation('notification.id',relation_name='notification_users',mode='foreignkey',onDelete='cascade')
        tbl.column('confirmed',dtype='B',name_long='!!Confirmed')
        tbl.column('notification',dtype='X',name_long='Custom Notification')


    @public_method
    def getNotification(self,pkey=None):
        user_id,notification_template,notification_title,confirm_label,notification_bag = self.readColumns(pkey=pkey,columns="""$user_id,@notification_id.template,@notification_id.title,
                                                                                                                                 @notification_id.confirm_label,$notification""")
        usertbl = self.db.table('adm.user')
        source_record = usertbl.record(pkey=user_id).output('bag')
        htmlbuilder = TableTemplateToHtml(usertbl)
        #notification = htmlbuilder(record=source_record,template=Bag(notification_template)['compiled'],letterhead_id=letterhead_id,pdf=False)
        notification = None
        notification_bag = Bag(notification_bag) if notification_bag else Bag()
        if notification_template:
            notification = htmlbuilder.contentFromTemplate(record=user_id,template=Bag(notification_template)['compiled'])
        notification = notification_bag['body'] or notification
        notification_title = notification_bag['title'] or notification_title
        confirm_label = notification_bag['confirm_label'] or confirm_label
        return dict(notification=notification,title=notification_title,confirm_label=confirm_label)


    @public_method
    def confirmNotification(self,pkey=None):
        with self.recordToUpdate(pkey) as rec:
            rec['confirmed'] = True
        self.db.commit()
        return self.nextUserNotification(rec['user_id'])

    def nextUserNotification(self,user_id=None):
        f = self.query(where='$user_id=:uid AND $confirmed IS NOT TRUE',uid=user_id,limit=1,order_by='$__ins_ts asc').fetch()
        user_notification_id = f[0]['id'] if f else None
        if user_notification_id:
            return user_notification_id
        

    def updateGenericNotification(self,user_id=None,user_tags=None):
        generic_notification = self.db.table('adm.notification').query(where="""($all_users IS TRUE OR $tag_rule IS NOT NULL )
                                                                                AND NOT $existing_for_current_user
                                                                                """,env_user_id=user_id).fetch()
        commit = False
        for n in generic_notification:
            if n['all_users'] or self.db.application.checkResourcePermission(n['tag_rule'],user_tags):
                if not self.checkDuplicate(user_id=user_id,notification_id=n['id']):
                    commit = True
                    self.insert(dict(user_id=user_id,notification_id=n['id']))
        if commit:
            self.db.commit()









        