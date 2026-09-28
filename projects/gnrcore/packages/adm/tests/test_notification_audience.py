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
# A tag whose htag is flagged require_2fa: it counts only for a user who has
# a 2fa secret of their own.
TAG_2FA = 'ZZ2FA'
# Same trick for the groups: GROUP_ADMIN is a substring of GROUP_SUPERADMIN, and
# $all_groups is a comma-join with no delimiter at the string boundaries.
GROUP_ADMIN = 'ZZADMG'
GROUP_SUPERADMIN = 'SUPERZZADMG'
GROUP_OTHER = 'ZZOTHERG'


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

    def _tag_id(self, code, require_2fa=None):
        """The pkey of an adm.htag, created on first use."""
        tbl = self.db.table('adm.htag')
        existing = tbl.query(where='$code=:c', c=code, columns='$id').fetch()
        if existing:
            return existing[0]['id']
        rec = tbl.newrecord(code=code, description=code, require_2fa=require_2fa)
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

    def _add_extra_group(self, user_id, code):
        """A group beyond the user's own group_code: $all_groups aggregates it
        through adm.user_group, comma-joined with the others."""
        tbl = self.db.table('adm.user_group')
        rec = tbl.newrecord(user_id=user_id, group_code=self._insert_group(code))
        tbl.insert(rec)
        self.db.commit()

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

    def _linked_rows(self, notification_id):
        """The adm.user_notification rows of a notification, by user: the pkey
        is what tells a row that survived an alignment from a re-created one."""
        rows = self.usernotif_tbl.query(where='$notification_id=:nid',
                                        nid=notification_id,
                                        columns='$id,$user_id,$confirmed').fetch()
        return {r['user_id']: r for r in rows}

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

    # --- group_code --------------------------------------------------------

    def test_group_code_audience_coherent_on_both_paths(self):
        member = self._insert_user('notif_group_member',
                                   group_code=self._insert_group(GROUP_ADMIN))
        other = self._insert_user('notif_group_other',
                                  group_code=self._insert_group(GROUP_OTHER))

        notif_id = self._insert_notification(title='group dynamic',
                                             group_code=GROUP_ADMIN, dynamic_list=True)
        linked = self._linked_users(notif_id)
        assert member in linked
        assert other not in linked

        newcomer = self._insert_user('notif_group_new', group_code=GROUP_ADMIN)
        self._login(newcomer)
        assert newcomer in self._linked_users(notif_id)

    def test_group_code_does_not_match_by_substring(self):
        """A notification restricted to ZZADMG must not reach a user in
        SUPERZZADMG: an unanchored LIKE '%code%' delivers it outside its
        audience, which is the unsafe direction of the error."""
        superadmin = self._insert_user('notif_group_superadmin',
                                       group_code=self._insert_group(GROUP_SUPERADMIN))
        notif_id = self._insert_notification(title='group substring',
                                             group_code=GROUP_ADMIN, dynamic_list=True)
        assert superadmin not in self._linked_users(notif_id)

        newcomer = self._insert_user('notif_group_superadmin_new',
                                     group_code=GROUP_SUPERADMIN)
        self._login(newcomer)
        assert newcomer not in self._linked_users(notif_id)

    def test_group_code_matches_a_secondary_group(self):
        """The delimited match must still see a group the user holds beyond their
        own group_code, which reaches $all_groups through the comma-join."""
        member = self._insert_user('notif_group_secondary',
                                   group_code=self._insert_group(GROUP_OTHER))
        self._add_extra_group(member, GROUP_ADMIN)
        notif_id = self._insert_notification(title='group secondary',
                                             group_code=GROUP_ADMIN, dynamic_list=True)
        assert member in self._linked_users(notif_id)

    def test_group_code_does_not_imply_all_users(self):
        notif_id = self._insert_notification(title='only group code',
                                             group_code=GROUP_ADMIN)
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

    # --- differential alignment -------------------------------------------

    def test_criteria_change_keeps_the_row_of_a_user_that_stays(self):
        """The alignment is differential: a user in the audience both before
        and after the edit must keep the very row they had. Dropping every
        pending row and re-creating the whole audience is what made saving a
        notification cost one write per user of the installation."""
        staying = self._tagged_user('notif_diff_staying', [TAG_ADMIN, TAG_OTHER])
        leaving = self._tagged_user('notif_diff_leaving', [TAG_ADMIN])
        joining = self._tagged_user('notif_diff_joining', [TAG_OTHER])
        notif_id = self._insert_notification(title='differential alignment',
                                             tag_rule=TAG_ADMIN, dynamic_list=False)
        before = self._linked_rows(notif_id)
        assert staying in before
        assert leaving in before
        assert joining not in before

        with self.notif_tbl.recordToUpdate(notif_id) as rec:
            rec['tag_rule'] = TAG_OTHER
        self.db.commit()

        after = self._linked_rows(notif_id)
        assert joining in after, "a user entering the audience must be enrolled"
        assert leaving not in after, "a user leaving the audience must lose their row"
        assert staying in after
        assert after[staying]['id'] == before[staying]['id'], \
            "the row of a user who stays in the audience must not be rewritten"

    def test_confirmed_row_survives_a_criteria_change_and_is_not_duplicated(self):
        """A user who already answered is out of the alignment: their row is
        neither dropped when they leave the audience nor created a second time
        when they are still in it."""
        answered_in = self._tagged_user('notif_diff_confirmed_in',
                                        [TAG_ADMIN, TAG_OTHER])
        answered_out = self._tagged_user('notif_diff_confirmed_out', [TAG_ADMIN])
        notif_id = self._insert_notification(title='confirmed rows',
                                             tag_rule=TAG_ADMIN, dynamic_list=False)
        rows = self._linked_rows(notif_id)
        for user_id in (answered_in, answered_out):
            with self.usernotif_tbl.recordToUpdate(rows[user_id]['id']) as rec:
                rec['confirmed'] = True
        self.db.commit()

        with self.notif_tbl.recordToUpdate(notif_id) as rec:
            rec['tag_rule'] = TAG_OTHER
        self.db.commit()

        linked = self.usernotif_tbl.query(where='$notification_id=:nid', nid=notif_id,
                                          columns='$id,$user_id,$confirmed').fetch()
        for user_id in (answered_in, answered_out):
            own = [r for r in linked if r['user_id'] == user_id]
            assert len(own) == 1, "a confirmed row must not be duplicated"
            assert own[0]['confirmed'], "a confirmed row must not be dropped"

    # --- batched tag resolution -------------------------------------------

    def test_batched_tags_match_the_pycolumn(self):
        """`allTagsByUser` is what the audience is evaluated on, so it must
        return what the `$all_tags` pyColumn returns user by user. The tags
        are compared as sets: their order is a detail of the query, and
        `checkResourcePermission` reads them as a membership list."""
        user_tbl = self.db.table('adm.user')
        group_code = self._insert_group('ZZBATCHG')
        self._assign_tag(TAG_OTHER, group_code=group_code)
        direct = self._tagged_user('notif_batch_direct', [TAG_ADMIN])
        in_group = self._insert_user('notif_batch_group', group_code=group_code)
        untagged = self._insert_user('notif_batch_untagged')

        user_ids = [direct, in_group, untagged]
        rows = user_tbl.query(where='$id IN :user_ids', user_ids=user_ids,
                              columns='$id,$group_code,$avatar_secret_2fa').fetch()
        batched = user_tbl.allTagsByUser(rows)
        assert set(batched) == set(user_ids)
        for user_id in user_ids:
            # The pyColumn resolves the tags on the row it is handed, so the
            # selection has to carry the columns it reads -- the same '*' the
            # avatar query uses.
            one_by_one = user_tbl.query(where='$id=:uid', uid=user_id,
                                        columns='*,$all_tags').fetch()[0]['all_tags']
            assert set(batched[user_id].split(',')) == set(one_by_one.split(',')), \
                "the batched resolution must not change the effective tags"

    def test_require_2fa_tag_counts_only_for_a_user_with_a_secret(self):
        """A tag flagged require_2fa reaches only the users who have a 2fa
        secret: the condition is per user, and the batched resolution has to
        apply it row by row as the per-user query did."""
        self._tag_id(TAG_2FA, require_2fa=True)
        with_secret = self._insert_user('notif_2fa_with_secret')
        without_secret = self._insert_user('notif_2fa_without_secret')
        with self.db.table('adm.user').recordToUpdate(with_secret) as rec:
            rec['avatar_secret_2fa'] = 'ZZSECRET'
        self.db.commit()
        self._assign_tag(TAG_2FA, user_id=with_secret)
        self._assign_tag(TAG_2FA, user_id=without_secret)

        notif_id = self._insert_notification(title='2fa tag rule',
                                             tag_rule=TAG_2FA, dynamic_list=True)
        linked = self._linked_users(notif_id)
        assert with_secret in linked
        assert without_secret not in linked, \
            "a require_2fa tag must not count for a user without a 2fa secret"
