"""Tests for the audience alignment of adm.notification.

Both paths that align a notification with its audience are exercised
against a real database:
 - the bulk snapshot taken by the notification triggers
   (``updateUserNotificationsFromQuery`` -> ``audienceUserIds``)
 - the per-user incremental alignment at login
   (``updateGenericNotification`` -> ``userMatchesAudience``)

so that the two stay coherent, and the static/dynamic behaviour, the tag
rule semantics and the start/end date window gating are all verified.

The tests need no running site nor a shared database: they build a
throwaway application on a temporary sqlite file, so users, tags and
notifications go through the actual table triggers.
"""
import datetime
import os
import shutil
import tempfile

from gnr.app.gnrapp import GnrApp


WORKDATE = datetime.date(2026, 6, 30)
# Tags unique to this module. TAG_ADMIN is a substring of TAG_SUPERADMIN on
# purpose: that pair is what tells a permission-engine match from a LIKE one.
TAG_ADMIN = 'ZZADMIN'
TAG_SUPERADMIN = 'SUPERZZADMIN'
TAG_OTHER = 'ZZOTHER'


class TestNotificationAudience(object):

    @classmethod
    def setup_class(cls):
        cls.instance_name = os.environ.get('GNR_TESTING_INSTANCE_NAME') or 'gnrdevelop'
        cls.temp_dir = tempfile.mkdtemp(prefix='gnr_notification_audience_')
        cls.app = GnrApp(cls.instance_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(cls.temp_dir, 'testing')))
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.db.updateEnv(workdate=WORKDATE)
        cls.notif_tbl = cls.db.table('adm.notification')
        cls.usernotif_tbl = cls.db.table('adm.user_notification')

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # --- fixtures ----------------------------------------------------------

    def _insert_user(self, username, group_code=None):
        tbl = self.db.table('adm.user')
        rec = tbl.newrecord(username=username, email='%s@test.local' % username,
                            firstname='Test', lastname='Aud', group_code=group_code)
        tbl.insert(rec)
        self.db.commit()
        return rec['id']

    def _tag_id(self, code):
        """The pkey of an adm.htag, created on first use."""
        tbl = self.db.table('adm.htag')
        existing = tbl.query(where='$code=:c', c=code, columns='$id').fetch()
        if existing:
            return existing[0]['id']
        rec = tbl.newrecord(code=code, description=code)
        tbl.insert(rec)
        self.db.commit()
        return rec['id']

    def _assign_tag(self, code, user_id=None, group_code=None):
        """Tag a user, or a whole group, the way the framework does: through
        adm.user_tag, which is what feeds the $all_tags column the audience is
        evaluated against."""
        tbl = self.db.table('adm.user_tag')
        rec = tbl.newrecord(tag_id=self._tag_id(code), user_id=user_id,
                            group_code=group_code)
        tbl.insert(rec)
        self.db.commit()

    def _insert_group(self, code):
        tbl = self.db.table('adm.group')
        if not tbl.query(where='$code=:c', c=code, columns='$code').fetch():
            rec = tbl.newrecord(code=code, description=code)
            tbl.insert(rec)
            self.db.commit()
        return code

    def _tagged_user(self, username, tags):
        user_id = self._insert_user(username)
        for tag in tags:
            self._assign_tag(tag, user_id=user_id)
        return user_id

    def _insert_notification(self, **kwargs):
        rec = self.notif_tbl.newrecord(**kwargs)
        self.notif_tbl.insert(rec)
        self.db.commit()
        return rec['id']

    def _linked_users(self, notification_id):
        rows = self.usernotif_tbl.query(where='$notification_id=:nid',
                                        nid=notification_id,
                                        columns='$user_id').fetch()
        return {r['user_id'] for r in rows}

    def _login(self, user_id):
        self.usernotif_tbl.updateGenericNotification(user_id)

    # --- static vs dynamic -------------------------------------------------

    def test_static_all_users_snapshot_is_frozen(self):
        existing = self._insert_user('notif_static_existing')
        notif_id = self._insert_notification(title='static all-users',
                                             dynamic_list=False)

        assert existing in self._linked_users(notif_id), \
            "the snapshot must link the users present at save time"

        # A user created after the snapshot must NOT be added to a static list.
        newcomer = self._insert_user('notif_static_newcomer')
        self._login(newcomer)
        assert newcomer not in self._linked_users(notif_id)

    def test_dynamic_all_users_grows_at_login(self):
        notif_id = self._insert_notification(title='dynamic all-users',
                                             dynamic_list=True)
        newcomer = self._insert_user('notif_dynamic_newcomer')
        self._login(newcomer)
        assert newcomer in self._linked_users(notif_id)

    def test_dynamic_list_is_the_default(self):
        notif_id = self._insert_notification(title='default audience mode')
        rec = self.notif_tbl.record(pkey=notif_id).output('dict')
        assert rec['dynamic_list'], "a new notification must be dynamic unless opted out"

    def test_notification_predating_the_column_still_enrols(self):
        """A row saved before dynamic_list existed has it NULL and no snapshot
        of its own: it used to be delivered by the incremental alignment at
        login, and it must keep being delivered after the upgrade."""
        notif_id = self._insert_notification(title='legacy notification',
                                             dynamic_list=None)
        rec = self.notif_tbl.record(pkey=notif_id).output('dict')
        assert rec['dynamic_list'] is None, "the legacy case is a NULL, not a False"

        newcomer = self._insert_user('notif_legacy_newcomer')
        self._login(newcomer)
        assert newcomer in self._linked_users(notif_id)

    # --- tag rule ----------------------------------------------------------

    def test_tag_rule_audience_coherent_on_both_paths(self):
        matching = self._tagged_user('notif_tag_match', [TAG_ADMIN])
        other = self._tagged_user('notif_tag_other', [TAG_OTHER])

        notif_id = self._insert_notification(title='tag dynamic',
                                             tag_rule=TAG_ADMIN, dynamic_list=True)

        # Snapshot path: only the matching user is linked.
        linked = self._linked_users(notif_id)
        assert matching in linked
        assert other not in linked

        # Login path must use the same audience rule: a new matching user is
        # linked, a new non-matching user is not.
        new_match = self._tagged_user('notif_tag_new_match', [TAG_ADMIN])
        new_nomatch = self._tagged_user('notif_tag_new_nomatch', [TAG_OTHER])
        self._login(new_match)
        self._login(new_nomatch)

        linked = self._linked_users(notif_id)
        assert new_match in linked
        assert new_nomatch not in linked

    def test_tag_rule_does_not_match_by_substring(self):
        """A rule on ZZADMIN must not reach a user tagged SUPERZZADMIN: that
        is exactly what a bare LIKE '%tag%' does, on either path."""
        superadmin = self._tagged_user('notif_tag_superadmin', [TAG_SUPERADMIN])
        notif_id = self._insert_notification(title='tag substring',
                                             tag_rule=TAG_ADMIN, dynamic_list=True)
        assert superadmin not in self._linked_users(notif_id)

        newcomer = self._tagged_user('notif_tag_superadmin_new', [TAG_SUPERADMIN])
        self._login(newcomer)
        assert newcomer not in self._linked_users(notif_id)

    def test_tag_rule_honors_wildcards(self):
        admin = self._tagged_user('notif_tag_wildcard_in', [TAG_ADMIN])
        other = self._tagged_user('notif_tag_wildcard_out', [TAG_OTHER])
        notif_id = self._insert_notification(title='tag wildcard',
                                             tag_rule='ZZADM%', dynamic_list=True)
        linked = self._linked_users(notif_id)
        assert admin in linked
        assert other not in linked

        newcomer = self._tagged_user('notif_tag_wildcard_new', [TAG_ADMIN])
        self._login(newcomer)
        assert newcomer in self._linked_users(notif_id)

    def test_tag_rule_honors_exclusions(self):
        only_admin = self._tagged_user('notif_tag_not_in', [TAG_ADMIN])
        both = self._tagged_user('notif_tag_not_out', [TAG_ADMIN, TAG_OTHER])
        notif_id = self._insert_notification(title='tag exclusion',
                                             tag_rule='%s NOT %s' % (TAG_ADMIN, TAG_OTHER),
                                             dynamic_list=True)
        linked = self._linked_users(notif_id)
        assert only_admin in linked
        assert both not in linked

        new_excluded = self._tagged_user('notif_tag_not_new', [TAG_ADMIN, TAG_OTHER])
        self._login(new_excluded)
        assert new_excluded not in self._linked_users(notif_id)

    def test_tag_rule_honors_alternative_rules(self):
        """`;` separates alternative rules: matching either one is enough."""
        second_rule = self._tagged_user('notif_tag_alt_in', [TAG_SUPERADMIN])
        neither = self._tagged_user('notif_tag_alt_out', [TAG_ADMIN])
        notif_id = self._insert_notification(title='tag alternatives',
                                             tag_rule='%s;%s' % (TAG_OTHER, TAG_SUPERADMIN),
                                             dynamic_list=True)
        linked = self._linked_users(notif_id)
        assert second_rule in linked
        assert neither not in linked

    def test_tag_rule_matches_tags_inherited_from_group(self):
        """The rule is evaluated on $all_tags, the very column the login reads
        to build the avatar tags, so a tag granted through the group counts."""
        group_code = self._insert_group('ZZGRP')
        self._assign_tag(TAG_ADMIN, group_code=group_code)
        in_group = self._insert_user('notif_tag_group_member', group_code=group_code)
        outsider = self._insert_user('notif_tag_group_outsider')

        notif_id = self._insert_notification(title='tag from group',
                                             tag_rule=TAG_ADMIN, dynamic_list=True)
        linked = self._linked_users(notif_id)
        assert in_group in linked
        assert outsider not in linked

        newcomer = self._insert_user('notif_tag_group_new', group_code=group_code)
        self._login(newcomer)
        assert newcomer in self._linked_users(notif_id)

    def test_no_audience_rule_implies_all_users(self):
        notif_id = self._insert_notification(title='implicit all-users')
        rec = self.notif_tbl.record(pkey=notif_id).output('dict')
        assert rec['all_users'], "no audience rule must imply all_users"

    def test_tag_rule_does_not_imply_all_users(self):
        notif_id = self._insert_notification(title='only tag rule', tag_rule=TAG_ADMIN)
        rec = self.notif_tbl.record(pkey=notif_id).output('dict')
        assert not rec['all_users'], "an explicit audience rule must not force all_users"

    # --- re-snapshot on update --------------------------------------------

    def test_audience_criteria_change_resnapshots(self):
        admin = self._tagged_user('notif_resnap_admin', [TAG_ADMIN])
        other = self._tagged_user('notif_resnap_other', [TAG_OTHER])
        notif_id = self._insert_notification(title='criteria change',
                                             tag_rule=TAG_ADMIN, dynamic_list=False)
        linked = self._linked_users(notif_id)
        assert admin in linked
        assert other not in linked

        with self.notif_tbl.recordToUpdate(notif_id) as rec:
            rec['tag_rule'] = TAG_OTHER
        self.db.commit()
        linked = self._linked_users(notif_id)
        assert other in linked
        assert admin not in linked, "a criteria change must rebuild the membership"

    def test_date_window_change_does_not_resnapshot_static_list(self):
        """Re-photographing on a date edit would enrol exactly the newcomers a
        static list exists to exclude."""
        member = self._tagged_user('notif_window_member', [TAG_ADMIN])
        notif_id = self._insert_notification(title='static window edit',
                                             tag_rule=TAG_ADMIN, dynamic_list=False,
                                             end_date=WORKDATE + datetime.timedelta(days=1))
        assert member in self._linked_users(notif_id)

        newcomer = self._tagged_user('notif_window_newcomer', [TAG_ADMIN])
        with self.notif_tbl.recordToUpdate(notif_id) as rec:
            rec['end_date'] = WORKDATE + datetime.timedelta(days=30)
        self.db.commit()

        linked = self._linked_users(notif_id)
        assert member in linked, "the pending rows of a static list must survive"
        assert newcomer not in linked

    # --- date window -------------------------------------------------------

    def test_date_window_gates_visibility(self):
        user_id = self._insert_user('notif_datewindow_user')
        notif_id = self._insert_notification(title='expired window',
                                             dynamic_list=True,
                                             end_date=WORKDATE - datetime.timedelta(days=10))

        # The snapshot links the user regardless of the window...
        assert user_id in self._linked_users(notif_id)
        # ...but an expired notification is not surfaced to the user.
        assert self.usernotif_tbl.nextUserNotification(user_id=user_id) is None

        # Reopening the window makes it visible again.
        with self.notif_tbl.recordToUpdate(notif_id) as rec:
            rec['end_date'] = WORKDATE + datetime.timedelta(days=10)
        self.db.commit()
        assert self.usernotif_tbl.nextUserNotification(user_id=user_id) is not None
