"""Real-database tests for the notification audience alignment.

Exercises both alignment paths against a temporary SQLite database:
 - the bulk snapshot taken by the notification triggers
   (``updateUserNotificationsFromQuery``)
 - the per-user incremental alignment at login
   (``updateGenericNotification`` -> ``userMatchesAudience``)

so that the two stay coherent, and verifies the static/dynamic behaviour
and the start/end date window gating.
"""

import datetime

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


WORKDATE = datetime.date(2026, 6, 30)
UNIQUE_TAG = 'ZZNOTIFTAG'


class TestNotificationAudience:

    def _insert_user(self, db, username, auth_tags=None, lastname='Aud'):
        tbl = db.table('adm.user')
        rec = tbl.newrecord(username=username, email='%s@test.local' % username,
                            firstname='Test', lastname=lastname, auth_tags=auth_tags)
        tbl.insert(rec)
        db.commit()
        return rec['id']

    def _insert_notification(self, db, **kwargs):
        tbl = db.table('adm.notification')
        rec = tbl.newrecord(**kwargs)
        tbl.insert(rec)
        db.commit()
        return rec['id']

    def _linked_users(self, db, notification_id):
        rows = db.table('adm.user_notification').query(
            where='$notification_id=:nid', nid=notification_id,
            columns='$user_id').fetch()
        return {r['user_id'] for r in rows}

    def test_static_all_users_snapshot_is_frozen(self, db_sqlite):
        existing = self._insert_user(db_sqlite, 'notif_static_existing')
        notif_id = self._insert_notification(db_sqlite, title='static all-users')

        linked = self._linked_users(db_sqlite, notif_id)
        assert existing in linked, "snapshot must link users present at save time"

        # A user created after the snapshot must NOT be added to a static list.
        newcomer = self._insert_user(db_sqlite, 'notif_static_newcomer')
        db_sqlite.table('adm.user_notification').updateGenericNotification(newcomer)
        assert newcomer not in self._linked_users(db_sqlite, notif_id)

    def test_dynamic_all_users_grows_at_login(self, db_sqlite):
        notif_id = self._insert_notification(db_sqlite, title='dynamic all-users',
                                             dynamic_list=True)
        newcomer = self._insert_user(db_sqlite, 'notif_dynamic_newcomer')
        db_sqlite.table('adm.user_notification').updateGenericNotification(newcomer)
        assert newcomer in self._linked_users(db_sqlite, notif_id)

    def test_tag_rule_audience_coherent_on_both_paths(self, db_sqlite):
        matching = self._insert_user(db_sqlite, 'notif_tag_match', auth_tags=UNIQUE_TAG)
        other = self._insert_user(db_sqlite, 'notif_tag_other', auth_tags='something_else')

        notif_id = self._insert_notification(db_sqlite, title='tag dynamic',
                                             tag_rule=UNIQUE_TAG, dynamic_list=True)

        # Snapshot path: only the matching user is linked.
        linked = self._linked_users(db_sqlite, notif_id)
        assert matching in linked
        assert other not in linked

        # Login path must use the same audience rule: a new matching user is
        # linked, a new non-matching user is not.
        new_match = self._insert_user(db_sqlite, 'notif_tag_new_match', auth_tags=UNIQUE_TAG)
        new_nomatch = self._insert_user(db_sqlite, 'notif_tag_new_nomatch', auth_tags='zzz')
        usernotif_tbl = db_sqlite.table('adm.user_notification')
        usernotif_tbl.updateGenericNotification(new_match)
        usernotif_tbl.updateGenericNotification(new_nomatch)

        linked = self._linked_users(db_sqlite, notif_id)
        assert new_match in linked
        assert new_nomatch not in linked

    def test_no_audience_rule_implies_all_users(self, db_sqlite):
        notif_id = self._insert_notification(db_sqlite, title='implicit all-users')
        rec = db_sqlite.table('adm.notification').record(pkey=notif_id).output('dict')
        assert rec['all_users'], "no audience rule must imply all_users"

    def test_tag_rule_does_not_imply_all_users(self, db_sqlite):
        notif_id = self._insert_notification(db_sqlite, title='only tag rule',
                                             tag_rule=UNIQUE_TAG)
        rec = db_sqlite.table('adm.notification').record(pkey=notif_id).output('dict')
        assert not rec['all_users'], "an explicit audience rule must not force all_users"

    def test_date_window_gates_visibility(self, db_sqlite):
        db_sqlite.updateEnv(workdate=WORKDATE)
        user_id = self._insert_user(db_sqlite, 'notif_datewindow_user')
        notif_tbl = db_sqlite.table('adm.notification')
        notif_id = self._insert_notification(db_sqlite, title='expired window',
                                             dynamic_list=True,
                                             end_date=WORKDATE - datetime.timedelta(days=10))
        usernotif_tbl = db_sqlite.table('adm.user_notification')

        # Snapshot links the user regardless of the window...
        assert user_id in self._linked_users(db_sqlite, notif_id)
        # ...but an expired notification is not surfaced to the user.
        assert usernotif_tbl.nextUserNotification(user_id=user_id) is None

        # Reopening the window makes it visible again.
        with notif_tbl.recordToUpdate(notif_id) as rec:
            rec['end_date'] = WORKDATE + datetime.timedelta(days=10)
        db_sqlite.commit()
        assert usernotif_tbl.nextUserNotification(user_id=user_id) is not None
