import logging
from pathlib import Path

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import gnrImport
from gnr.lib.services.storage import StorageNode
from gnr.web.gnrmenu import MenuStruct, MenuResolver


REPO_ROOT = Path(__file__).resolve().parents[3]


class _Site:
    def __init__(self, node=None, error=None):
        self.node = node
        self.error = error
        self.sources = []

    def storageNode(self, source):
        self.sources.append(source)
        if self.error:
            raise self.error
        return self.node


class _App:
    checkResourcePermission = GnrApp.checkResourcePermission

    def allowedByPreference(self, **kwargs):
        return True


class _Page:
    def __init__(self, site=None, userTags='', dbstore=None):
        self.site = site
        self.application = _App()
        self.userTags = userTags
        self.dbstore = dbstore
        self.rootenv = {}

    def checkPermission(self, pagepath, relative=True):
        return True


class _FixedSourceResolver(MenuResolver):
    def __init__(self, struct, **kwargs):
        self._struct = struct
        super().__init__(**kwargs)

    @property
    def sourceBag(self):
        return self._struct


def _build_struct(page, source='pkg:test/resources/test.html', tags='', **kwargs):
    struct = MenuStruct(page=page)
    struct.docpage('Report', source=source, tags=tags, **kwargs)
    return struct


def _load(struct, page, **kwargs):
    resolver = _FixedSourceResolver(struct, _page=page, path=None, **kwargs)
    return resolver.load()


def _symbolic_node():
    module = gnrImport(str(REPO_ROOT / 'resources/common/services/storage/symbolic.py'))
    package = type('Package', (), {
        'packageFolder': str(REPO_ROOT / 'projects/gnrcore/packages/test')
    })()
    app = type('App', (), {'packages': {'test': package}})()
    parent = type('Parent', (), {
        'default_uri': 'https://example.test/',
        'gnrapp': app
    })()
    service = module.Service(parent=parent)
    service.service_name = 'pkg'
    return StorageNode(path='test/resources/test.html', service=service)


def _http_node(url):
    module = gnrImport(str(REPO_ROOT / 'resources/common/services/storage/http.py'),
                       importAs='gnr_storage_http_service')
    service = module.Service(parent=object())
    service.service_name = '_http_'
    return StorageNode(path=url, service=service)


def _raw_node():
    module = gnrImport(str(REPO_ROOT / 'resources/common/services/storage/raw.py'))
    service = module.Service(parent=object())
    service.service_name = '_raw_'
    return StorageNode(path='/tmp/report.html', service=service)


def test_docpage_creates_node_with_tag_and_source():
    page = _Page()
    struct = _build_struct(page, tags='REPORT_VIEW')
    node = next(iter(struct))

    assert node.attr['tag'] == 'docpage'
    assert node.attr['label'] == 'Report'
    assert node.attr['source'] == 'pkg:test/resources/test.html'
    assert node.attr['tags'] == 'REPORT_VIEW'


def test_load_resolves_real_storage_node_to_public_url():
    site = _Site(node=_symbolic_node())
    page = _Page(site=site, userTags='REPORT_VIEW')
    struct = _build_struct(page, tags='REPORT_VIEW')

    result = _load(struct, page, externalSite='inherited', aux_instance='reporting')

    node = next(iter(result))
    assert site.sources == ['pkg:test/resources/test.html']
    assert node.attr['webpage'].startswith(
        'https://example.test/_pkg/test/resources/test.html?mtime=')
    assert node.attr['nonGenroContent'] is True
    assert node.attr['url_aux_instance'] == 'reporting'
    assert 'externalSite' not in node.attr


def test_load_resolves_absolute_http_url():
    url = 'https://www.example.test/report.html'
    site = _Site(node=_http_node(url))
    page = _Page(site=site)
    struct = _build_struct(page, source=url)

    node = next(iter(_load(struct, page, externalSite='inherited')))

    assert site.sources == [url]
    assert node.attr['webpage'] == url
    assert node.attr['nonGenroContent'] is True
    assert 'externalSite' not in node.attr


def test_load_ignores_entry_external_site_for_document_url():
    page = _Page(site=_Site(node=_symbolic_node()))
    struct = _build_struct(page, externalSite='named-site')

    node = next(iter(_load(struct, page)))

    assert node.attr['webpage'].startswith('https://example.test/_pkg/test/')
    assert 'externalSite' not in node.attr


@pytest.mark.parametrize('source,node', [
    (None, None),
    ('missing:report.html', None),
    ('report.html', _raw_node()),
])
def test_load_hides_unresolvable_document(source, node, caplog):
    page = _Page(site=_Site(node=node))
    struct = _build_struct(page, source=source)

    with caplog.at_level(logging.WARNING, logger='gnr.web'):
        result = _load(struct, page)

    assert len(result) == 0
    assert 'Cannot resolve docpage source' in caplog.text


def test_load_hides_storage_errors(caplog):
    page = _Page(site=_Site(error=RuntimeError('unknown service')))
    struct = _build_struct(page, source='broken:report.html')

    with caplog.at_level(logging.WARNING, logger='gnr.web'):
        result = _load(struct, page)

    assert len(result) == 0
    assert "broken:report.html" in caplog.text
    assert 'unknown service' in caplog.text


@pytest.mark.parametrize('user_tags,expected_count', [
    ('REPORT_VIEW', 1),
    ('SOMETHING_ELSE', 0),
])
def test_load_uses_framework_tag_permissions(user_tags, expected_count):
    page = _Page(site=_Site(node=_symbolic_node()), userTags=user_tags)
    struct = _build_struct(page, tags='REPORT_VIEW')

    assert len(_load(struct, page)) == expected_count


def test_webpage_still_uses_shared_page_finalization():
    page = _Page()
    struct = MenuStruct(page=page)
    struct.webpage('Report', filepath='report', aux_instance='reporting')

    result = _load(struct, page, basepath='reports')
    node = next(iter(result))

    assert node.attr['webpage'] == 'reports/report'
    assert node.attr['url_aux_instance'] == 'reporting'
