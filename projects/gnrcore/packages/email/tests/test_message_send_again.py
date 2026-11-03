from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web.gnrdummysite import GnrDummySite

from core.common import BaseGnrTest


class TestMessageSendAgain(BaseGnrTest):

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
        cls.atc_tbl = cls.db.table('email.message_atc')
        cls.queue_tbl = cls.db.table('email.message_to_send')
        cls.account_id = 'send-again-account'
        cls.db.table('email.account').insert(dict(
            id=cls.account_id,
            account_name='Send again test',
            smtp_from_address='sender@example.com',
        ))
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        super().teardown_class()

    def _origin_file(self, path, content=b'%PDF-1.4 signed'):
        node = self.site.storageNode(path, autocreate=-1)
        with node.open('wb') as f:
            f.write(content)
        return node

    def _new_message(self, **kwargs):
        return self.message_tbl.newMessage(account_id=self.account_id,
                                           to_address='recipient@example.com',
                                           from_address='sender@example.com',
                                           subject='Contract', body='Please sign',
                                           doCommit=True, **kwargs)

    def _queued(self, message_id):
        return self.queue_tbl.existsRecord(message_id)

    def _attachment_paths(self, message_id):
        return [r['filepath'] for r in self.atc_tbl.query(columns='$filepath',
                                                          where='$maintable_id=:mid',
                                                          mid=message_id).fetch()]

    def test_draft_is_queued_only_when_released(self):
        message = self._new_message(__is_draft=True)
        assert not self._queued(message['id'])
        with self.message_tbl.recordToUpdate(message['id']) as record:
            record['__is_draft'] = False
        self.db.commit()
        assert self._queued(message['id'])

    def test_send_again_creates_draft_copy_with_attachments(self):
        origin = self._origin_file('home:send_again/origin/contract.pdf')
        original = self._new_message(attachments=[origin.fullpath],
                                     headers_kwargs=dict(message_id='GNR_original'))
        with self.message_tbl.recordToUpdate(original['id']) as record:
            record['send_date'] = self.message_tbl.newUTCDatetime()
            record['proxy_ts'] = record['send_date']
        self.queue_tbl.removeMessageFromQueue(original['id'])
        self.db.commit()

        copy = self.message_tbl.sendAgainMessage(message_id=original['id'])
        self.db.commit()

        record = self.message_tbl.record(copy['id'], bagFields=True).output('dict')
        assert copy['id'] != original['id']
        assert record['__is_draft']
        assert record['send_date'] is None
        assert record['proxy_ts'] is None
        assert record['to_address'] == 'recipient@example.com'
        assert record['subject'] == 'Contract'
        assert Bag(record['extra_headers'])['message_id'] is None
        assert not self._queued(copy['id'])

        original_paths = self._attachment_paths(original['id'])
        copy_paths = self._attachment_paths(copy['id'])
        assert len(copy_paths) == 1
        assert copy_paths != original_paths
        copied = self.site.storageNode(copy_paths[0])
        assert copied.exists
        with copied.open('rb') as f:
            assert f.read() == b'%PDF-1.4 signed'
