#!/usr/bin/env python
# encoding: utf-8
from gnr.core.gnrbag import Bag

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
        tbl.column('dynamic_list','B',name_long='!!Dynamic list', name_short='!!Dynamic')
        tbl.column('start_date','D',name_long='!!Start date')
        tbl.column('end_date','D',name_long='!!End date')
        
        tbl.formulaColumn('existing_for_current_user',"""
                (EXISTS(SELECT * FROM adm.adm_user_notification AS un WHERE un.user_id=:env_user_id AND un.notification_id=#THIS.id))
            """,dtype='B')

        tbl.formulaColumn('confirmed_count',select=dict(table='adm.user_notification',
                                                        columns='COUNT(*)',
                                                        where='$notification_id=#THIS.id AND $confirmed IS TRUE'),
                                            dtype='L',name_long='!!Confirmed users',
                                            name_short='!!Conf.users')

        tbl.formulaColumn('pending_count',select=dict(table='adm.user_notification',
                                                      columns='COUNT(*)',
                                                      where='$notification_id=#THIS.id AND $confirmed IS NOT TRUE'),
                                          dtype='L',name_long='!!Pending users',
                                          name_short='!!Pend.users')

    def trigger_onInserting(self, record):
        if self._hasNoAudienceRule(record):
            record['all_users'] = True

    def trigger_onInserted(self, record):
        self.updateUserNotificationsFromQuery(record)

    def trigger_onUpdating(self, record, old_record=None):
        if self._hasNoAudienceRule(record):
            record['all_users'] = True

    def trigger_onUpdated(self, record, old_record=None):
        if self.fieldsChanged('linked_query,tag_rule,all_users,group_code,dynamic_list,start_date,end_date',
                              record, old_record):
            self.updateUserNotificationsFromQuery(record)

    def _hasNoAudienceRule(self, record):
        # all_users is implied only when no explicit audience criterion is set
        return not (record['linked_query'] or record['tag_rule'] or record['group_code'])

    def audienceWhere(self, notification_record):
        """Build the (where, kwargs) selecting adm.user rows that match this
        notification audience. Shared by the bulk snapshot and the per-user
        login alignment so both evaluate the audience identically.
        Returns (None, {}) when the notification targets all users."""
        if notification_record['all_users']:
            return None, {}
        where = []
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
        if notification_record.get('linked_query'):
            wherebag = Bag(notification_record['linked_query'])['query.where']
            condition, selection_kwargs = self.db.table('adm.user').sqlWhereFromBag(
                                    wherebag, selection_kwargs)
            where.append(condition)
        return (' AND '.join(where) if where else None), selection_kwargs

    def userMatchesAudience(self, notification_record, user_id):
        """Return True if the given user matches the notification audience.
        Used for the dynamic per-user alignment at login."""
        where, selection_kwargs = self.audienceWhere(notification_record)
        user_where = '$id=:__audience_uid'
        if where:
            user_where = f'({where}) AND {user_where}'
        selection_kwargs['__audience_uid'] = user_id
        return self.db.table('adm.user').query(where=user_where, **selection_kwargs).count() > 0

    def updateUserNotificationsFromQuery(self, notification_record):
        user_tbl = self.db.table('adm.user')
        user_notification_tbl = self.db.table('adm.user_notification')
        where, selection_kwargs = self.audienceWhere(notification_record)
        users = user_tbl.query(where=where, **selection_kwargs).selection().output('pkeylist')

        # Delete previous unconfirmed notifications for this notification_id
        user_notification_tbl.deleteSelection(where='$notification_id=:notif_id AND $confirmed IS NOT TRUE',
                                              notif_id=notification_record['id'])

        for user_id in users:
            if user_notification_tbl.checkDuplicate(user_id=user_id,notification_id=notification_record['id']):
                continue
            new_notf = user_notification_tbl.newrecord(user_id=user_id,notification_id=notification_record['id'])
            user_notification_tbl.insert(new_notf)