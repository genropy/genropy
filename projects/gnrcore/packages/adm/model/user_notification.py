#!/usr/bin/env python
# encoding: utf-8


from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import TableTemplateToHtml
from gnr.core.gnrbag import Bag


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('user_notification', pkey='id', name_long='User notification', name_plural='!!User notifications')
        self.sysFields(tbl)
        tbl.column('user_id',size='22' ,group='_',name_long='!!User').relation(
                    'user.id',relation_name='user_notifications',mode='foreignkey',onDelete='cascade',onDuplicate='ignore')
        tbl.column('notification_id',size='22' ,group='_',name_long='!!Notification').relation(
                    'notification.id',relation_name='notification_users',mode='foreignkey',onDelete='cascade',onDuplicate='ignore')
        tbl.column('confirmed',dtype='B',name_long='!!Confirmed')
        tbl.column('notification',dtype='X',name_long='Custom Notification')


    @public_method
    def getNotification(self,pkey=None):
        user_id,notification_template,notification_title,confirm_label,notification_bag = self.readColumns(
                                    pkey=pkey,columns="""$user_id,@notification_id.template,@notification_id.title,
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
        f = self.query(where="""$user_id=:uid AND $confirmed IS NOT TRUE
                                AND (@notification_id.start_date IS NULL OR @notification_id.start_date<=:today)
                                AND (@notification_id.end_date IS NULL OR @notification_id.end_date>=:today)""",
                       uid=user_id,today=self.db.workdate,limit=1,order_by='$__ins_ts asc').fetch()
        user_notification_id = f[0]['id'] if f else None
        if user_notification_id:
            return user_notification_id


    def updateGenericNotification(self,user_id=None,user_tags=None):
        # Only dynamic notifications gain new users over time, and only while
        # they are inside their active date window. Static lists are frozen at
        # the snapshot taken when the notification was saved.
        notification_tbl = self.db.table('adm.notification')
        dynamic_notification = notification_tbl.query(where="""$dynamic_list IS TRUE
                                                               AND NOT $existing_for_current_user
                                                               AND ($start_date IS NULL OR $start_date<=:today)
                                                               AND ($end_date IS NULL OR $end_date>=:today)""",
                                                      env_user_id=user_id,today=self.db.workdate).fetch()
        commit = False
        for n in dynamic_notification:
            if notification_tbl.userMatchesAudience(n,user_id):
                if not self.checkDuplicate(user_id=user_id,notification_id=n['id']):
                    commit = True
                    self.insert(dict(user_id=user_id,notification_id=n['id']))
        if commit:
            self.db.commit()









        