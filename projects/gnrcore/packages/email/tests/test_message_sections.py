import os

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrdummysite import GnrDummySite

from core.common import BaseGnrTest


PROXY_SECTIONS = ('dispatched_to_proxy', 'queue_issues')


class SendingStatusSections(BaseGnrTest):
    """Bootstrap of an email instance whose message ui is asked for its sections.

    The sections are read from the real resource on a real db: only the page
    that would host the component is left out, the component itself needs
    nothing more than the db to answer.
    """

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
        module_path = os.path.join(
            cls.db.application.packages['email'].packageFolder,
            'resources', 'tables', 'message', 'th_message.py',
        )
        cls.th_message = gnrImport(module_path, avoidDup=True)

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        super().teardown_class()

    def section_codes(self, view_class):
        view = view_class()
        view.db = self.db
        return [section['code'] for section in view.th_sections_sendingstatus()]


class TestSectionsWithoutMailProxy(SendingStatusSections):
    """No mail proxy service: proxy_ts stays null and the queue is drained by smtp.

    The two proxy sections would be filters that can never match, so the
    upperbar must not offer them.
    """

    def test_mailproxy_is_not_available(self):
        assert self.db.package('email').getMailProxy(raise_if_missing=False) is None

    def test_message_view_hides_proxy_sections(self):
        codes = self.section_codes(self.th_message.View)
        assert 'to_send' in codes
        assert 'sent' in codes
        for code in PROXY_SECTIONS:
            assert code not in codes

    def test_out_only_view_hides_proxy_sections(self):
        codes = self.section_codes(self.th_message.ViewOutOnly)
        assert 'to_send' in codes
        assert 'sent' in codes
        for code in PROXY_SECTIONS:
            assert code not in codes


class TestSectionsWithMailProxy(SendingStatusSections):
    """An activated mail proxy service: the proxy sections describe real states."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db.table('sys.service').addService(
            service_type='mailproxy', service_name='mailproxy',
            implementation='mailproxy',
            proxy_url='http://proxy.example.com',
            tenant_registered=True,
        )
        cls.db.commit()

    def test_mailproxy_is_available(self):
        assert self.db.package('email').getMailProxy(raise_if_missing=False) is not None

    def test_message_view_shows_proxy_sections(self):
        codes = self.section_codes(self.th_message.View)
        for code in PROXY_SECTIONS:
            assert code in codes

    def test_out_only_view_shows_the_queue_issues_section(self):
        codes = self.section_codes(self.th_message.ViewOutOnly)
        assert 'queue_issues' in codes
