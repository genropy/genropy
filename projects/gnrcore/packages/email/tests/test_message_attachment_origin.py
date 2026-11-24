import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrdummysite import GnrDummySite

from core.common import BaseGnrTest


class ProxyClient:
    tenant_id = 'test-tenant'
    payload = None

    def add_messages(self, payload):
        self.payload = payload
        return {'queued': len(payload)}


class TestMessageAttachmentOrigin(BaseGnrTest):

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
        cls.app = cls.site.gnrapp
        cls.db = cls.site.db
        cls.message_tbl = cls.db.table('email.message')
        cls.account_id = 'attachment-origin-account'
        cls.db.table('email.account').insert(dict(
            id=cls.account_id,
            account_name='Attachment origin test',
            smtp_from_address='sender@example.com',
        ))
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        super().teardown_class()

    def _new_message(self, **kwargs):
        return self.message_tbl.newMessage(account_id=self.account_id,
                                           to_address='recipient@example.com',
                                           from_address='sender@example.com',
                                           subject='Contract', body='Please sign',
                                           doCommit=True, **kwargs)

    def test_missing_attachment_origin_raises(self):
        with pytest.raises(FileNotFoundError):
            self._new_message(attachments=['home:attachment_origin/missing/signed.pdf'])
        self.db.rollback()

    def test_proxy_marks_missing_attachment_as_error(self):
        message = self._new_message(weak_attachments='home:attachment_origin/missing/lost.pdf')
        module = gnrImport(self.app.packages['email'].packageFolder
                           + '/webpages/mailproxy/mp_endpoint.py', avoidDup=True)
        page = module.GnrCustomWebPage()
        page.db = self.db
        page.site = self.site
        proxy_client = ProxyClient()
        page._add_messages_to_proxy_queue(proxy_client, [message['id']])
        self.db.commit()

        record = self.message_tbl.record(message['id']).output('dict')
        assert proxy_client.payload is None
        assert 'Attachment not found' in record['error_msg']
        assert not self.db.table('email.message_to_send').existsRecord(message['id'])
