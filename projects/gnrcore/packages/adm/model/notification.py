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
        # Dynamic by default: this is how notifications behaved before the
        # column existed, so the rows that predate it (NULL) and the new ones
        # (True) keep enrolling users at login. Static is an explicit opt-out.
        tbl.column('dynamic_list','B',default=True,
                   name_long='!!Dynamic list', name_short='!!Dynamic')
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
        # The audience is photographed as soon as the notification is saved:
        # for a static list this snapshot *is* the list, and a dynamic one
        # still has to reach the users matching right now. With `all_users`
        # that means one adm.user_notification row per user, written inside
        # the insert transaction: saving a notification costs one insert per
        # user of the installation. That is the intended price of a snapshot.
        self.updateUserNotificationsFromQuery(record)

    def trigger_onUpdating(self, record, old_record=None):
        if self._hasNoAudienceRule(record):
            record['all_users'] = True

    def trigger_onUpdated(self, record, old_record=None):
        # Only a change to the audience criteria re-photographs the list: the
        # snapshot drops the pending rows and rebuilds membership from the
        # current population, so firing it on `dynamic_list` or on the date
        # window would silently re-photograph a static list -- extending the
        # window of a static notification would enrol exactly the newcomers
        # it is meant to exclude, and drop the users who no longer match.
        if self.fieldsChanged('linked_query,tag_rule,all_users,group_code', record, old_record):
            self.updateUserNotificationsFromQuery(record)

    def _hasNoAudienceRule(self, record):
        # all_users is implied only when no explicit audience criterion is set
        return not (record['linked_query'] or record['tag_rule'] or record['group_code'])

    def audienceWhere(self, notification_record):
        """Build the (where, kwargs) pre-selecting the adm.user rows that are
        candidates for this notification audience.

        Only the criteria SQL can express live here, `group_code` and
        `linked_query`. The tag rule is applied by `tagRuleMatches` on the
        candidate rows instead: it is a permission-engine expression (exact
        tags, `%` wildcards, `AND`/`NOT`, `;`) that a LIKE cannot reproduce.
        Callers must therefore pair this pre-selection with the tag check --
        `audienceUserIds` and `userMatchesAudience` are the two entry points
        that do, and that is what keeps the bulk snapshot and the per-user
        login alignment on one single rule.

        Returns (None, {}) when the notification targets all users."""
        if notification_record['all_users']:
            return None, {}
        where = []
        selection_kwargs = {}

        # Check if user has at least one of the specified groups. $all_groups is a
        # comma-join with no delimiter at the string boundaries, so the match is made
        # on delimited codes: a bare LIKE '%admin%' would also reach a user in
        # `superadmin`, `admin_ro` or `nonadmin` -- a false positive, i.e. a
        # group-restricted notification delivered outside its audience.
        if notification_record.get('group_code'):
            groups = [g.strip() for g in notification_record['group_code'].split(',') if g.strip()]
            if groups:
                group_conditions = []
                for i, g in enumerate(groups):
                    group_conditions.append(f"',' || $all_groups || ',' LIKE :group_{i}")
                    selection_kwargs[f'group_{i}'] = f'%,{g},%'
                where.append('(' + ' OR '.join(group_conditions) + ')')

        # Add linked query condition
        if notification_record.get('linked_query'):
            wherebag = Bag(notification_record['linked_query'])['query.where']
            condition, selection_kwargs = self.db.table('adm.user').sqlWhereFromBag(
                                    wherebag, selection_kwargs)
            where.append(condition)
        return (' AND '.join(where) if where else None), selection_kwargs

    def audienceTagRule(self, notification_record):
        """The tag rule in force for this notification, if any.
        `all_users` wins over every other criterion, the tag rule included."""
        if notification_record['all_users']:
            return None
        return notification_record['tag_rule']

    def tagRuleMatches(self, tag_rule, user_tags):
        """Evaluate a notification tag rule against a user's effective tags.

        Delegated to the permission engine, the same one that gates every
        other tagged resource of the framework: `$auth_tags LIKE '%admin%'`
        would also match a user tagged `superadmin`, and would honor none of
        the rule syntax the engine understands."""
        if not tag_rule:
            return True
        return self.db.application.checkResourcePermission(tag_rule, user_tags)

    def audienceUserIds(self, notification_record):
        """Return the pkeys of the adm.user rows matching this notification."""
        user_tbl = self.db.table('adm.user')
        where, selection_kwargs = self.audienceWhere(notification_record)
        tag_rule = self.audienceTagRule(notification_record)
        if not tag_rule:
            return user_tbl.query(where=where, **selection_kwargs).selection().output('pkeylist')
        # $all_tags is the column adm authentication reads to build the avatar
        # tags, so the rule is evaluated against the tags the user actually
        # logs in with: their own plus the ones inherited from their group.
        # Being a pyColumn it costs a query per candidate, paid only when a
        # tag rule has to be evaluated -- and the snapshot that calls this is
        # already one insert per user anyway.
        rows = user_tbl.query(where=where, columns='*,$all_tags', **selection_kwargs).fetch()
        return [r['id'] for r in rows if self.tagRuleMatches(tag_rule, r['all_tags'])]

    def userMatchesAudience(self, notification_record, user_id):
        """Return True if the given user matches the notification audience.
        Used for the dynamic per-user alignment at login."""
        where, selection_kwargs = self.audienceWhere(notification_record)
        user_where = '$id=:__audience_uid'
        if where:
            user_where = f'({where}) AND {user_where}'
        selection_kwargs['__audience_uid'] = user_id
        rows = self.db.table('adm.user').query(where=user_where, columns='*,$all_tags',
                                               **selection_kwargs).fetch()
        if not rows:
            return False
        return self.tagRuleMatches(self.audienceTagRule(notification_record), rows[0]['all_tags'])

    def updateUserNotificationsFromQuery(self, notification_record):
        user_notification_tbl = self.db.table('adm.user_notification')
        users = self.audienceUserIds(notification_record)

        # Delete previous unconfirmed notifications for this notification_id
        user_notification_tbl.deleteSelection(where='$notification_id=:notif_id AND $confirmed IS NOT TRUE',
                                              notif_id=notification_record['id'])

        for user_id in users:
            if user_notification_tbl.checkDuplicate(user_id=user_id,notification_id=notification_record['id']):
                continue
            new_notf = user_notification_tbl.newrecord(user_id=user_id,notification_id=notification_record['id'])
            user_notification_tbl.insert(new_notf)