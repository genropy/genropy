#!/usr/bin/env python
# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('notification', pkey='id', name_long='!!Notification', 
                                        name_plural='!!Notifications',caption_field='title')
        self.sysFields(tbl)
        
        tbl.column('title' ,name_long='!!Title')
        tbl.column('template','X',name_long='!!Template')
        tbl.column('confirm_label',name_long='!!Confirm label')
        tbl.column('tag_rule',name_long='!!Tag rule')
        tbl.column('group_code',name_long='!!Group code')
        tbl.column('all_users','B',name_long='!!For all users')
        tbl.column('letterhead_id',size='22',group='_',name_long='!!Letterhead').relation('htmltemplate.id',relation_name='notifications',mode='foreignkey')
        tbl.column('linked_query', dtype='X', name_long='!![en]Linked query',_sendback=True)
        
        tbl.formulaColumn('existing_for_current_user',"""
                (EXISTS(SELECT * FROM adm.adm_user_notification AS un WHERE un.user_id=:env_user_id AND un.notification_id=#THIS.id))
            """,dtype='B')

    def trigger_onInserting(self, record):
        if not record['linked_query']:
            record['all_users'] = True
    
    def trigger_onInserted(self, record, old_record=None):
        if record['linked_query'] and self.fieldsChanged('linked_query,tag_rule,all_users,group_code', record, old_record):
            self.updateUserNotificationsFromQuery(record)
            
    def trigger_onUpdating(self, record, old_record=None):
        if not record['linked_query']:
            record['all_users'] = True
            
    def trigger_onUpdated(self, record, old_record=None):
        if record['linked_query'] and self.fieldsChanged('linked_query,tag_rule,all_users,group_code', record, old_record):
            self.updateUserNotificationsFromQuery(record)
            
    def updateUserNotificationsFromQuery(self, notification_record):
        where = []
        user_tbl = self.db.table('adm.user')
        user_notification_tbl = self.db.table('adm.user_notification')
        selection_kwargs = {}

        # Check if user has at least one of the specified groups
        if notification_record.get('group_code'):
            groups = [g.strip() for g in notification_record['group_code'].split(',') if g.strip()]
            if groups:
                group_conditions = []
                for i, g in enumerate(groups):
                    group_conditions.append(f"$all_groups LIKE :group_{i}")
                    selection_kwargs[f'group_{i}'] = f'%{g}%'
                where.append('(' + ' OR '.join(group_conditions) + ')')

        # Check if user has at least one of the specified tags
        if notification_record.get('tag_rule'):
            tags = [t.strip() for t in notification_record['tag_rule'].split(',') if t.strip()]
            if tags:
                tag_conditions = []
                for i, t in enumerate(tags):
                    tag_conditions.append(f"$auth_tags LIKE :tag_{i}")
                    selection_kwargs[f'tag_{i}'] = f'%{t}%'
                where.append('(' + ' OR '.join(tag_conditions) + ')')

        # Add linked query condition
        condition, selection_kwargs = self.db.table('adm.user').sqlWhereFromBag(
                            notification_record['linked_query']['query.where'], selection_kwargs)
        where.append(condition)
        users = user_tbl.query(where=' AND '.join(where),**selection_kwargs).selection().output('pkeylist')

        # Delete previous unconfirmed notifications for this notification_id
        user_notification_tbl.deleteSelection(where='$notification_id=:notif_id AND $confirmed IS NOT TRUE',
                                              notif_id=notification_record['id'])

        for user_id in users:
            if user_notification_tbl.checkDuplicate(user_id=user_id,notification_id=notification_record['id']):
                continue
            new_notf = user_notification_tbl.newrecord(user_id=user_id,notification_id=notification_record['id'])
            user_notification_tbl.insert(new_notf)