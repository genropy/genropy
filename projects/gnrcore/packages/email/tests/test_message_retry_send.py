import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web.gnrdummysite import GnrDummySite

from core.common import BaseGnrTest


class TestRetrySendWithMailProxy(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        config = Bag(cls.test_instance_config_path)
        config.setItem('packages.gnrcore_email', None, pkgcode='gnrcore:email')
        config.toXml(cls.test_instance_config_path)
        bootstrap_app = GnrApp(cls.test_instance_name)
        bootstrap_app.db.model.check(applyChanges=True)
        bootstrap_app.db.commit()
        bootstrap_app.db.closeConnection()
        cls.site = GnrDummySite(cls.test_instance_name,
                                site_name=cls.test_instance_name)
        cls.db = cls.site.db
        cls.message_tbl = cls.db.table('email.message')
        cls.account_id = 'retry-send-account'
        cls.db.table('email.account').insert(dict(
            id=cls.account_id,
            account_name='Retry send test',
            smtp_from_address='sender@example.com',
        ))
        cls.db.table('sys.service').addService(
            service_type='mailproxy', service_name='mailproxy',
            implementation='mailproxy',
            proxy_url='http://proxy.example.com',
            tenant_registered=True,
        )
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        super().teardown_class()

    @pytest.fixture
    def proxy_calls(self, monkeypatch):
        calls = []
        service_class = type(self.db.package('email').getMailProxy())
        monkeypatch.setattr(service_class, 'run_now', lambda service: None)
        monkeypatch.setattr(service_class, 'delete_messages',
                            lambda service, message_ids: calls.append(message_ids))
        return calls

    def _new_message(self):
        return self.message_tbl.newMessage(account_id=self.account_id,
                                           to_address='recipient@example.com',
                                           from_address='sender@example.com',
                                           subject='Contract', body='Please sign',
                                           doCommit=True)

    def _fail_in_proxy(self, message_id):
        with self.message_tbl.recordToUpdate(message_id) as message:
            message['proxy_ts'] = self.message_tbl.newUTCDatetime()
            message['error_ts'] = self.message_tbl.newUTCDatetime()
            message['error_msg'] = 'Attachment fetch failed: 404'
        self.db.table('email.message_to_send').removeMessageFromQueue(message_id)
        self.db.commit()

    def test_retry_after_proxy_error_forgets_the_proxy_record(self, proxy_calls):
        message_id = self._new_message()['id']
        self._fail_in_proxy(message_id)

        self.message_tbl.retrySendMessage(message_id=message_id)
        self.db.commit()

        record = self.message_tbl.record(message_id).output('dict')
        assert proxy_calls == [[message_id]]
        assert record['error_ts'] is None
        assert record['error_msg'] is None
        assert record['proxy_ts'] is None
        assert self.db.table('email.message_to_send').existsRecord(message_id)

    def test_retry_of_undispatched_message_does_not_call_the_proxy(self, proxy_calls):
        message_id = self._new_message()['id']

        self.message_tbl.retrySendMessage(message_id=message_id)
        self.db.commit()

        assert proxy_calls == []
        assert self.db.table('email.message_to_send').existsRecord(message_id)
