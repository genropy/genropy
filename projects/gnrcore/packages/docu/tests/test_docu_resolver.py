"""Tests for the handbooks request resolver of the docu package.

Exercise docu.documentation.resolveRequestPath and the docuresolver
webtool against a real database built from the gnrdevelop instance
(which includes the docu package): name lookups through
calculateExternalUrl, homonym disambiguation and 404 fallbacks.
"""
import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from gnr.core.gnrlang import gnrImport

from core.common import BaseGnrAppTest

BASE_URL = 'https://docs.example.org'
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

        handbook_tbl = cls.db.table('docu.handbook')
        handbook_tbl.insert(dict(name='testguide', title='Test guide', docroot_id=guide_root,
                                 handbook_url=f'{BASE_URL}/testguide/'))
        handbook_tbl.insert(dict(name='otherbook', title='Other book', docroot_id=other_root,
                                 handbook_url=f'{BASE_URL}/otherbook/'))
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

    def _resolver_tool(self):
        module_path = os.path.join(self.app.packages['docu'].packageFolder,
                                   'webtools', 'resolver.py')
        module = gnrImport(module_path, avoidDup=True)
        tool = module.DocuResolver()

        def getResource(path, ext=None, pkg=None):
            resource_path = COMMON_RESOURCES / path
            return str(resource_path) if resource_path.exists() else None

        tool.site = SimpleNamespace(db=self.db,
                                    resource_loader=SimpleNamespace(getResource=getResource))
        return tool

    def test_webtool_moved_page_301(self):
        response = self._resolver_tool()('testguide', 'oldsection', 'advanced.html')
        assert response.status_code == 301
        assert response.headers['Location'] == f'{BASE_URL}/testguide/usage/advanced.html'

    def test_webtool_unknown_page_404(self):
        response = self._resolver_tool()('testguide', 'nowhere.html')
        assert response.status_code == 404
        template = (COMMON_RESOURCES / 'html_pages' / 'missing_result.html').read_text()
        assert response.get_data(as_text=True) == template
