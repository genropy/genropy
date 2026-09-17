import os
import shutil
import tempfile

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
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
        return body.replace('$shared_content', 'Dear Ada') if body else None
"""

PLACEHOLDER = '$shared_content, this is the message.'
COMPOSED = 'Dear Ada, this is the message.'


class TestMessageCompiledBody(BaseGnrTest):
    """The compiled_body pyColumn is what the message ui reads instead of $body.

    A project that keeps a placeholder in $body (so that a circular mail does
    not store its content once per recipient) composes the real content in
    getBody. Asking for $compiled_body must return that composition, on the
    record load the forms do and on the query the grids do.
    """

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.temp_dir = tempfile.mkdtemp(prefix='gnr_email_compiled_')
        cls._install_body_compiler()
        bootstrap_app = GnrApp(cls.test_instance_name)
        bootstrap_app.db.model.check(applyChanges=True)
        bootstrap_app.db.commit()
        bootstrap_app.db.closeConnection()
        # the account triggers reach site services: a bare GnrApp has no site
        cls.site = GnrDummySite(cls.test_instance_name,
                                site_name=cls.test_instance_name)
        cls.app = cls.site.gnrapp
        cls.db = cls.site.db
        cls.message_tbl = cls.db.table('email.message')
        cls.account_id = 'compiled-body-account'
        cls.db.table('email.account').insert(dict(
            id=cls.account_id,
            account_name='Compiled body test',
            smtp_from_address='sender@example.com',
        ))
        cls.message_id = 'compiled-body-message'
        cls.message_tbl.insert(cls.message_tbl.newrecord(
            id=cls.message_id,
            in_out='O',
            account_id=cls.account_id,
            to_address='recipient@example.com',
            from_address='sender@example.com',
            subject='Compiled body test',
            body=PLACEHOLDER,
            html=True,
        ))
        cls.db.commit()

    @classmethod
    def _install_body_compiler(cls):
        packages_root = os.path.join(cls.temp_dir, 'packages')
        extension_root = os.path.join(packages_root, 'bodycompiler',
                                      'model', '_packages', 'email')
        os.makedirs(extension_root)
        with open(os.path.join(packages_root, 'bodycompiler', 'main.py'),
                  'w', encoding='utf-8') as fp:
            fp.write(PACKAGE_MAIN)
        with open(os.path.join(extension_root, 'message.py'),
                  'w', encoding='utf-8') as fp:
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

    def test_record_load_resolves_compiled_body(self):
        """What the message form does: load one record asking for the pyColumn."""
        record = self.message_tbl.record(self.message_id,
                                        virtual_columns='$compiled_body').output('bag')
        assert record['body'] == PLACEHOLDER
        assert record['compiled_body'] == COMPOSED

    def test_query_row_resolves_compiled_body(self):
        """What a grid does: the pyColumn is evaluated on the fetched row too.

        The override reads $body, so the query has to select it: on a row dict a
        column that was not selected raises instead of returning None.
        """
        row = self.message_tbl.query(columns='$id,$body,$compiled_body',
                                     where='$id=:mid', mid=self.message_id).fetch()[0]
        assert row['body'] == PLACEHOLDER
        assert row['compiled_body'] == COMPOSED
