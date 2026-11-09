import os
import shutil
import tempfile

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrdummysite import GnrDummySite

from core.common import BaseGnrTest


PACKAGE_MAIN = """from gnr.app.gnrdbo import GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(name_short='Body compiler', name_long='Body compiler')

    def config_db(self, pkg):
        pass
"""

MESSAGE_EXTENSION = """class Table(object):
    def getBody(self, message=None, **kwargs):
        body = message['body'] if message else None
        return body.replace('{{recipient}}', 'Ada') if body else None
"""


class ProxyClient:
    tenant_id = 'test-tenant'

    def add_messages(self, payload):
        self.payload = payload
        return {'queued': len(payload)}


class TestMailProxyBody(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.temp_dir = tempfile.mkdtemp(prefix='gnr_email_proxy_')
        cls._install_body_compiler()
        bootstrap_app = GnrApp(cls.test_instance_name)
        bootstrap_app.db.model.check(applyChanges=True)
        bootstrap_app.db.commit()
        bootstrap_app.db.closeConnection()
        cls.site = GnrDummySite(cls.test_instance_name,
                                site_name=cls.test_instance_name)
        cls.app = cls.site.gnrapp
        cls.db = cls.site.db
        cls.message_tbl = cls.db.table('email.message')
        cls.account_id = 'mailproxy-test-account'
        cls.db.table('email.account').insert(dict(
            id=cls.account_id,
            account_name='Mail proxy test',
            smtp_from_address='sender@example.com',
        ))
        cls.db.commit()
        module_path = os.path.join(
            cls.app.packages['email'].packageFolder,
            'webpages', 'mailproxy', 'mp_endpoint.py',
        )
        module = gnrImport(module_path, avoidDup=True)
        cls.page = module.GnrCustomWebPage()
        cls.page.db = cls.db
        cls.page.site = cls.site

    @classmethod
    def _install_body_compiler(cls):
        packages_root = os.path.join(cls.temp_dir, 'packages')
        package_root = os.path.join(packages_root, 'bodycompiler')
        extension_root = os.path.join(package_root, 'model', '_packages', 'email')
        os.makedirs(extension_root)
        with open(os.path.join(package_root, 'main.py'), 'w', encoding='utf-8') as fp:
            fp.write(PACKAGE_MAIN)
        with open(os.path.join(extension_root, 'message.py'), 'w', encoding='utf-8') as fp:
            fp.write(MESSAGE_EXTENSION)

        config = Bag(cls.test_instance_config_path)
        config.setItem('packages.gnrcore_email', None, pkgcode='gnrcore:email')
        config.setItem('packages.bodycompiler', None,
                       pkgcode='bodycompiler', path=packages_root)
        config.toXml(cls.test_instance_config_path)

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        shutil.rmtree(getattr(cls, 'temp_dir', ''), ignore_errors=True)
        super().teardown_class()

    @classmethod
    def _insert_message(cls, message_id, body=None, body_plain=None):
        cls.message_tbl.insert(cls.message_tbl.newrecord(
            id=message_id,
            in_out='O',
            account_id=cls.account_id,
            to_address='recipient@example.com',
            from_address='sender@example.com',
            subject='Proxy body test',
            body=body,
            body_plain=body_plain,
            html=bool(body),
        ))
        cls.db.commit()

    def test_proxy_uses_compiled_body_and_plain_fallback(self):
        compiled_id = 'mailproxy-compiled'
        plain_id = 'mailproxy-plain'
        placeholder = 'Hello {{recipient}}'
        self._insert_message(compiled_id, body=placeholder)
        self._insert_message(plain_id, body_plain='Plain fallback')

        proxy_client = ProxyClient()
        queued = self.page._add_messages_to_proxy_queue(
            proxy_client, [compiled_id, plain_id])
        self.db.commit()

        payload = {message['id']: message for message in proxy_client.payload}
        assert queued == 2
        assert payload[compiled_id]['body'] == 'Hello Ada'
        assert payload[plain_id]['body'] == 'Plain fallback'

        compiled = self.message_tbl.record(compiled_id).output('dict')
        plain = self.message_tbl.record(plain_id).output('dict')
        assert compiled['body'] == placeholder
        assert compiled['proxy_ts'] is not None
        assert plain['proxy_ts'] is not None
        assert self.db.table('email.message_to_send').query().count() == 0
