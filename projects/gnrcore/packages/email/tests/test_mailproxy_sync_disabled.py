import json
import os
import time
from types import SimpleNamespace

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrdummysite import GnrDummySite

from core.common import BaseGnrTest


class ProxyClient:
    """Stands in for the remote proxy: only the network call is replaced."""
    tenant_id = 'test-tenant'
    batch_size = None

    def __init__(self, disabled=False):
        self.disabled = disabled
        self.payload = None

    def add_messages(self, payload):
        self.payload = payload
        return {'queued': len(payload)}


class TestMailProxySyncDisabled(BaseGnrTest):

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
        cls.queue_tbl = cls.db.table('email.message_to_send')
        cls.account_id = 'mailproxy-sync-account'
        cls.db.table('email.account').insert(dict(
            id=cls.account_id,
            account_name='Mail proxy sync test',
            smtp_from_address='sender@example.com',
        ))
        cls.db.commit()
        module_path = os.path.join(
            cls.site.gnrapp.packages['email'].packageFolder,
            'webpages', 'mailproxy', 'mp_endpoint.py',
        )
        cls.page_class = gnrImport(module_path, avoidDup=True).GnrCustomWebPage

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        super().teardown_class()

    def _insert_message(self, message_id):
        self.message_tbl.insert(self.message_tbl.newrecord(
            id=message_id,
            in_out='O',
            account_id=self.account_id,
            to_address='recipient@example.com',
            from_address='sender@example.com',
            subject='Proxy sync test',
            body_plain='Hello',
        ))
        self.db.commit()

    def _proxy_sync(self, proxy_service, delivery_report=None):
        page = self.page_class()
        page.db = self.db
        page.site = self.site
        page.response = SimpleNamespace(content_type=None)
        page.getService = lambda service_type: proxy_service
        page._request_json = lambda: {'delivery_report': delivery_report or []}
        return json.loads(page.proxy_sync())

    def _message(self, message_id):
        return self.message_tbl.readColumns(
            pkey=message_id, columns='$proxy_ts,$send_date')

    def test_disabled_service_reports_but_queues_nothing(self):
        delivered_id = 'mailproxy-sync-delivered'
        pending_id = 'mailproxy-sync-pending'
        self._insert_message(delivered_id)
        self._insert_message(pending_id)

        proxy_service = ProxyClient(disabled=True)
        response = self._proxy_sync(proxy_service, delivery_report=[
            {'id': delivered_id, 'sent_ts': int(time.time())},
        ])

        assert response == {'ok': True, 'queued': 0}
        assert proxy_service.payload is None
        assert self._message(delivered_id)[1] is not None
        assert self._message(pending_id)[0] is None
        assert self.queue_tbl.query(where='$message_id=:pkey',
                                    pkey=pending_id).count() == 1

    def test_enabled_service_hands_out_the_queue(self):
        pending_id = 'mailproxy-sync-enabled'
        self._insert_message(pending_id)

        proxy_service = ProxyClient(disabled=False)
        response = self._proxy_sync(proxy_service)

        assert response['queued'] == len(proxy_service.payload)
        assert pending_id in {m['id'] for m in proxy_service.payload}
        assert self._message(pending_id)[0] is not None
        assert self.queue_tbl.query(where='$message_id=:pkey',
                                    pkey=pending_id).count() == 0
