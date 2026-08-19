"""Tests for the handbooks request resolver of the docu package.

Exercise docu.documentation.resolveRequestPath and the docuresolver
webtool against a real database built from the gnrdevelop instance
(which includes the docu package): name lookups through
calculateExternalUrl, homonym disambiguation and 404 fallbacks.
"""
import os
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from gnr.core.gnrlang import gnrImport

from core.common import BaseGnrAppTest

BASE_URL = 'https://docs.example.org'
CDN_BASE_URL = 'https://cdn.example.org'
INSTANCE_HOST = 'https://instance.example.org'
COMMON_RESOURCES = Path(__file__).resolve().parents[5] / 'resources' / 'common'


class TestDocuResolver(BaseGnrAppTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.doctbl = cls.db.table('docu.documentation')
        cls._makeFixture()

    @classmethod
    def _makeFixture(cls):
        """Two published handbooks sharing a page name.

        testguide: guide -> install, usage -> advanced, ghost (unpublished)
        otherbook: other -> install
        relbook: relroot -> setup (handbook_url stored as host-relative path)
        """
        def add_doc(name, parent_id=None, publish_date=True):
            record = dict(name=name, parent_id=parent_id,
                          publish_date=date.today() if publish_date else None)
            cls.doctbl.insert(record)
            return record['id']

        guide_root = add_doc('guide')
        add_doc('install', parent_id=guide_root)
        usage_id = add_doc('usage', parent_id=guide_root)
        add_doc('advanced', parent_id=usage_id)
        add_doc('ghost', parent_id=guide_root, publish_date=False)
        other_root = add_doc('other')
        add_doc('install', parent_id=other_root)
        rel_root = add_doc('relroot')
        add_doc('setup', parent_id=rel_root)

        handbook_tbl = cls.db.table('docu.handbook')
        handbook_tbl.insert(dict(name='testguide', title='Test guide', docroot_id=guide_root,
                                 handbook_url=f'{BASE_URL}/testguide/'))
        handbook_tbl.insert(dict(name='otherbook', title='Other book', docroot_id=other_root,
                                 handbook_url=f'{BASE_URL}/otherbook/'))
        handbook_tbl.insert(dict(name='relbook', title='Relative book', docroot_id=rel_root,
                                 handbook_url='/docs/relbook/'))
        cls.db.commit()

    def resolve(self, path):
        return self.doctbl.resolveRequestPath(path)

    def test_name_hit_moved_leaf(self):
        assert self.resolve('testguide/oldsection/advanced.html') == \
            f'{BASE_URL}/testguide/usage/advanced.html'

    def test_name_hit_branch_page(self):
        assert self.resolve('testguide/oldsection/usage/usage.html') == \
            f'{BASE_URL}/testguide/usage/usage.html'

    def test_name_hit_root_index(self):
        assert self.resolve('oldsite/guide.html') == f'{BASE_URL}/testguide/index.html'

    def test_homonym_disambiguated_by_handbook_segment(self):
        assert self.resolve('testguide/oldsection/install.html') == \
            f'{BASE_URL}/testguide/install.html'
        assert self.resolve('otherbook/oldsection/install.html') == \
            f'{BASE_URL}/otherbook/install.html'

    def test_homonym_unresolvable_ambiguity(self):
        assert self.resolve('unknownbook/install.html') is None

    def test_unknown_page(self):
        assert self.resolve('testguide/nowhere.html') is None

    def test_unpublished_page_excluded(self):
        assert self.resolve('testguide/ghost.html') is None

    def test_self_redirect_loop_guard(self):
        assert self.resolve('testguide/install.html') is None

    def test_empty_path(self):
        assert self.resolve('') is None
        assert self.resolve(None) is None

    @contextmanager
    def sphinxBaseurl(self, value):
        """Set the real docu.sphinx_baseurl preference, restoring it on exit"""
        self.db.table('adm.preference').loadPreference()
        try:
            self.app.setPreference('sphinx_baseurl', value, pkg='docu')
            yield
        finally:
            self.app.setPreference('sphinx_baseurl', None, pkg='docu')

    def test_relative_handbook_url_absolutized_by_preference(self):
        with self.sphinxBaseurl(f'{CDN_BASE_URL}/docs/'):
            assert self.resolve('relbook/oldsection/setup.html') == \
                f'{CDN_BASE_URL}/docs/relbook/setup.html'

    def test_relative_handbook_url_without_preference(self):
        assert self.resolve('relbook/oldsection/setup.html') == '/docs/relbook/setup.html'

    def test_relative_preference_cannot_absolutize(self):
        with self.sphinxBaseurl('/docs/'):
            assert self.resolve('relbook/oldsection/setup.html') == '/docs/relbook/setup.html'

    def test_absolute_handbook_url_ignores_preference(self):
        with self.sphinxBaseurl(f'{CDN_BASE_URL}/docs/'):
            assert self.resolve('testguide/oldsection/advanced.html') == \
                f'{BASE_URL}/testguide/usage/advanced.html'

    def _resolver_tool(self):
        module_path = os.path.join(self.app.packages['docu'].packageFolder,
                                   'webtools', 'resolver.py')
        module = gnrImport(module_path, avoidDup=True)
        tool = module.DocuResolver()

        def getResource(path, ext=None, pkg=None):
            resource_path = COMMON_RESOURCES / path
            return str(resource_path) if resource_path.exists() else None

        def externalUrl(url, **kwargs):
            fmt = '{}{}' if url.startswith('/') else '{}/{}'
            return fmt.format(INSTANCE_HOST, url)

        tool.site = SimpleNamespace(db=self.db,
                                    resource_loader=SimpleNamespace(getResource=getResource),
                                    externalUrl=externalUrl)
        return tool

    def test_webtool_moved_page_301(self):
        response = self._resolver_tool()('testguide', 'oldsection', 'advanced.html')
        assert response.status_code == 301
        assert response.headers['Location'] == f'{BASE_URL}/testguide/usage/advanced.html'

    def test_webtool_relative_location_falls_back_on_instance_host(self):
        response = self._resolver_tool()('relbook', 'oldsection', 'setup.html')
        assert response.status_code == 301
        assert response.headers['Location'] == f'{INSTANCE_HOST}/docs/relbook/setup.html'

    def test_webtool_relative_location_absolutized_by_preference(self):
        with self.sphinxBaseurl(f'{CDN_BASE_URL}/'):
            response = self._resolver_tool()('relbook', 'oldsection', 'setup.html')
        assert response.status_code == 301
        assert response.headers['Location'] == f'{CDN_BASE_URL}/docs/relbook/setup.html'

    def test_webtool_unknown_page_404(self):
        response = self._resolver_tool()('testguide', 'nowhere.html')
        assert response.status_code == 404
        template = (COMMON_RESOURCES / 'html_pages' / 'missing_result.html').read_text()
        assert response.get_data(as_text=True) == template

    # kept last: it publishes a crowd of homonyms the other tests do not expect

    def _insertDoc(self, name, parent_id=None):
        record = dict(name=name, parent_id=parent_id, publish_date=date.today())
        self.doctbl.insert(record)
        return record['id']

    def test_homonym_candidates_are_bounded(self):
        """Resolving a candidate costs a getAncestors query and this runs on the
        unauthenticated fallback of the published site: a name shared by more
        pages than the limit must not fan out into a query per page."""
        module_path = os.path.join(self.app.packages['docu'].packageFolder,
                                   'model', 'documentation.py')
        limit = gnrImport(module_path, avoidDup=True).RESOLVER_CANDIDATES_LIMIT
        for idx in range(limit + 2):
            self._insertDoc('faq', parent_id=self._insertDoc('capbook%02i' % idx))
        self.db.commit()
        resolved = []
        externalUrl = self.doctbl.calculateExternalUrl

        def countingExternalUrl(doc_record):
            #DP202608 spy delegating to the real resolution: what is counted is the
            #real per candidate query, not a simulated one
            resolved.append(doc_record.get('id'))
            return externalUrl(doc_record)

        self.doctbl.calculateExternalUrl = countingExternalUrl
        try:
            assert self.resolve('somebook/faq.html') is None
        finally:
            del self.doctbl.calculateExternalUrl
        assert len(resolved) == limit
