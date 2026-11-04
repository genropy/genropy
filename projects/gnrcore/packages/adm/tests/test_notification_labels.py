"""Tests for the captions the notification dialog is built from.

``adm.user_notification.getNotification`` is the single payload the login
dialog reads to decide what its two buttons say and whether the cancel
button exists at all, so what matters here is that every caption reaches
the client and that the per-user override wins over the notification.

The empty cases are just as meaningful as the filled ones: an empty
``confirm_button_label`` is what makes the client fall back to its own
translated ``Confirm``, and an empty ``cancel_button_label`` is what makes
a notification mandatory, since cancelling it means being logged out.

The payload builds the message body through ``TableTemplateToHtml``, which
needs a site: the tests therefore run on a throwaway instance served by a
``GnrDummySite``, against a real database and through the real triggers.
"""
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web.gnrdummysite import GnrDummySite

from core.common import BaseGnrTest


class TestNotificationLabels(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        bootstrap_app = GnrApp(cls.test_instance_name)
        bootstrap_app.db.model.check(applyChanges=True)
        bootstrap_app.db.commit()
        bootstrap_app.db.closeConnection()
        cls.site = GnrDummySite(cls.test_instance_name,
                                site_name=cls.test_instance_name)
        cls.db = cls.site.db
        cls.notif_tbl = cls.db.table('adm.notification')
        cls.usernotif_tbl = cls.db.table('adm.user_notification')

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        super().teardown_class()

    # --- fixtures ----------------------------------------------------------

    def _notification_for(self, username, **kwargs):
        """A notification targeting all users, plus the adm.user_notification
        row its own insert trigger writes for `username`. Returns the pkey of
        that row, which is what the client asks the payload for."""
        usertbl = self.db.table('adm.user')
        user = usertbl.newrecord(username=username, email='%s@test.local' % username,
                                 firstname='Test', lastname='Label')
        usertbl.insert(user)
        self.db.commit()
        notif = self.notif_tbl.newrecord(title='notification for %s' % username, **kwargs)
        self.notif_tbl.insert(notif)
        self.db.commit()
        rows = self.usernotif_tbl.query(where='$notification_id=:nid AND $user_id=:uid',
                                        nid=notif['id'], uid=user['id'],
                                        columns='$id').fetch()
        return rows[0]['id']

    def _custom_notification(self, user_notification_id, **kwargs):
        """The per-user override bag, the one an application fills to tailor a
        notification for a single recipient."""
        bag = Bag()
        for k, v in kwargs.items():
            bag[k] = v
        with self.usernotif_tbl.recordToUpdate(user_notification_id) as rec:
            rec['notification'] = bag.toXml()
        self.db.commit()

    # --- the payload -------------------------------------------------------

    def test_captions_reach_the_client(self):
        pkey = self._notification_for('notif_lbl_full',
                                      confirm_label='I have read it',
                                      confirm_button_label='Accept',
                                      cancel_button_label='Refuse')
        payload = self.usernotif_tbl.getNotification(pkey=pkey)
        assert payload['confirm_label'] == 'I have read it'
        assert payload['confirm_button_label'] == 'Accept'
        assert payload['cancel_button_label'] == 'Refuse'

    def test_missing_captions_are_left_empty(self):
        """Nothing is invented server side: the client is the one that falls
        back to its translated `Confirm` and drops the cancel button."""
        pkey = self._notification_for('notif_lbl_empty')
        payload = self.usernotif_tbl.getNotification(pkey=pkey)
        assert not payload['confirm_label']
        assert not payload['confirm_button_label']
        assert not payload['cancel_button_label']

    def test_custom_notification_overrides_the_captions(self):
        pkey = self._notification_for('notif_lbl_custom',
                                      confirm_button_label='Accept',
                                      cancel_button_label='Refuse')
        self._custom_notification(pkey, confirm_button_label='Sign',
                                  cancel_button_label='Decline')
        payload = self.usernotif_tbl.getNotification(pkey=pkey)
        assert payload['confirm_button_label'] == 'Sign'
        assert payload['cancel_button_label'] == 'Decline'

    def test_partial_custom_notification_keeps_the_notification_captions(self):
        """An override bag that only retitles the message must not silently
        strip the buttons of the notification it belongs to."""
        pkey = self._notification_for('notif_lbl_partial',
                                      confirm_button_label='Accept',
                                      cancel_button_label='Refuse')
        self._custom_notification(pkey, title='A title just for this user')
        payload = self.usernotif_tbl.getNotification(pkey=pkey)
        assert payload['title'] == 'A title just for this user'
        assert payload['confirm_button_label'] == 'Accept'
        assert payload['cancel_button_label'] == 'Refuse'

    # --- the short captions the grids are headed with ----------------------

    def test_date_window_columns_have_a_short_caption(self):
        model = self.notif_tbl.model
        assert model.column('start_date').attributes['name_short'] == '!!Start'
        assert model.column('end_date').attributes['name_short'] == '!!End'

    def test_confirmed_column_has_a_short_caption(self):
        model = self.usernotif_tbl.model
        assert model.column('confirmed').attributes['name_short'] == '!!Conf.'
