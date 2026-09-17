"""End to end checks on GnrDummySite, the site that runs without a gnrdaemon.

Everything here builds a real site on the isolated ``gnrtest`` instance and
renders through it: importing the module is not enough to tell whether the
class can be instantiated at all.
"""

import os

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web import gnrdummysite
from gnr.web.gnrbaseclasses import BagToHtmlWeb
from gnr.web.gnrdummysite import FakeRegister, FakeStore, GnrDummySite


class TestGnrDummySite(BaseGnrTest):
    """No daemon is started for this class: nothing here may need one."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)

    def test_module_under_test(self):
        # the editable install resolves gnr.* to the main checkout, so make sure
        # the module being exercised is the one in this working tree
        checkout = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        assert gnrdummysite.__file__.startswith(checkout + os.sep)

    def test_site_builds(self):
        assert isinstance(self.site, GnrDummySite)
        assert isinstance(self.site.register, FakeRegister)
        # built by GnrWsgiSite.__init__ out of register.siteregister
        assert self.site.datacollector is not None

    def test_register_is_memoized(self):
        assert self.site.register is self.site.register

    def test_main_register_bypasses_the_domain_proxy(self):
        assert self.site.main_register is self.site.register
        # the daemon backed register of the rootDomain proxy is never built
        assert self.site.domains[self.site.rootDomain]._register is None

    def test_stores_are_null(self):
        register = self.site.register
        for store in (register.globalStore(), register.pageStore('a_page'),
                      register.connectionStore('a_connection'), register.userStore('a_user')):
            assert isinstance(store, FakeStore)
            assert store.getItem('anything') is None
            assert store.getItem('anything', 'fallback') == 'fallback'
            store.setItem('anything', 'value')
            store.delItem('anything')
            assert store.getItem('anything') is None

    def test_store_is_a_context_manager(self):
        with self.site.register.globalStore() as store:
            store.setItem('CACHE_TS.foo', 'value')
        assert store.getItem('CACHE_TS.foo') is None

    def test_application_cache_round_trip(self):
        # WebApplicationCache reads the timestamps through site.main_register
        cache = self.site.gnrapp.cache
        assert cache.getItem('a_key', lambda: 'a_value') == 'a_value'
        assert cache.getItem('a_key') == 'a_value'
        cache.updatedItem('a_key')
        assert not cache.expiredItem('a_key')

    def test_get_dbenv_is_an_empty_bag(self):
        dbenv = self.site.register.get_dbenv('a_page', register_name='page')
        assert isinstance(dbenv, Bag)
        assert len(dbenv) == 0

    def test_datacollector_is_empty(self):
        collector = self.site.datacollector
        assert list(collector.users) == []
        assert list(collector.pages) == []
        assert list(collector.connections) == []
        assert collector.counters == {}

    def test_no_subscribed_tables(self):
        assert self.site.getSubscribedTables(['adm.user']) == []

    def test_dummy_page_renders(self):
        rendered = self.site.dummyPage.rootPage()
        assert '<page_id' in rendered
        assert '<connection_id' in rendered
        assert '<user' in rendered

    def test_print_path_renders_html(self):
        builder = BagToHtmlWeb(table=self.site.db.table('adm.user'))
        assert builder.get_css_requires() == ['/_rsrc/common/print_stylesheet.css']
        html = builder(record={}, filepath=None)
        assert html.startswith('<!DOCTYPE html')
        assert '/_rsrc/common/print_stylesheet.css' in html
