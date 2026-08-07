import gnr.web.gnrmenu  # noqa: F401

from gnr.web.gnrmenu import MenuStruct, MenuResolver


# ---------------------------------------------------------------------------
# Lightweight doubles.
#
# MenuResolver/MenuStruct never touch the database directly for the
# `htmlpage` tag: they only need a page/site/application surface (storage
# node lookup, permission checks, user tags). GnrDummySite is not usable
# here (it subclasses GnrWsgiSite and needs a full site bootstrap, and is
# documented as currently broken as shipped), so these doubles follow the
# same lightweight-stub idiom already used for structural, non-DB code in
# gnrwebstruct_test.py (_PageStub/_AppStub).
# ---------------------------------------------------------------------------

class _StubStorageNode:
    def __init__(self, url):
        self._url = url

    def url(self):
        return self._url


class _StubSite:
    def __init__(self, urls):
        self._urls = urls

    def storageNode(self, source):
        return _StubStorageNode(self._urls[source])


class _StubApp:
    def checkResourcePermission(self, auth_tags, user_tags):
        if not auth_tags:
            return True
        wanted = set(auth_tags.split(','))
        got = set((user_tags or '').split(','))
        return bool(wanted & got)

    def allowedByPreference(self, **kwargs):
        return True


class _StubPage:
    def __init__(self, site=None, userTags='', dbstore=None):
        self.site = site
        self.application = _StubApp()
        self.userTags = userTags
        self.dbstore = dbstore
        self.rootenv = {}

    def checkPermission(self, pagepath, relative=True):
        return True


class _FixedSourceResolver(MenuResolver):
    """MenuResolver whose sourceBag is a fixed MenuStruct.

    Mirrors how PackageMenuResolver/DirectoryMenuResolver override
    sourceBag; used here to drive load() against a MenuStruct built with
    MenuStruct.htmlpage() without going through package/instance discovery.
    """
    def __init__(self, struct, **kwargs):
        self._struct = struct
        super().__init__(**kwargs)

    @property
    def sourceBag(self):
        return self._struct


def _build_struct(page, source='pkg:demo/report.html', tags=''):
    struct = MenuStruct(page=page)
    struct.htmlpage('Report', source=source, tags=tags)
    return struct


def _load(struct, page):
    resolver = _FixedSourceResolver(struct, _page=page, path=None)
    return resolver.load()


# ---------------------------------------------------------------------------
# MenuStruct.htmlpage
# ---------------------------------------------------------------------------

def test_htmlpage_creates_node_with_tag_and_source():
    page = _StubPage()
    struct = _build_struct(page, source='pkg:demo/report.html', tags='REPORT_VIEW')
    node = next(iter(struct))
    assert node.attr['tag'] == 'htmlpage'
    assert node.attr['label'] == 'Report'
    assert node.attr['source'] == 'pkg:demo/report.html'
    assert node.attr['tags'] == 'REPORT_VIEW'


# ---------------------------------------------------------------------------
# nodeType_htmlpage, driven through MenuResolver.load()
# ---------------------------------------------------------------------------

def test_load_resolves_source_to_storage_node_url():
    site = _StubSite({'pkg:demo/report.html': 'https://example.test/_storage/demo/report.html'})
    page = _StubPage(site=site, userTags='REPORT_VIEW')
    struct = _build_struct(page, source='pkg:demo/report.html', tags='REPORT_VIEW')

    result = _load(struct, page)

    node = next(iter(result), None)
    assert node is not None
    assert node.attr['label'] == 'Report'
    assert node.attr['webpage'] == 'https://example.test/_storage/demo/report.html'


def test_load_without_source_drops_webpage_attribute():
    # Bag.setItem defaults to _removeNullAttributes=True, so a None
    # 'webpage' (no source given) is stripped from attr rather than kept
    # as an explicit None -- same behaviour nodeType_webpage relies on
    # when neither filepath nor webpage is set.
    site = _StubSite({})
    page = _StubPage(site=site, userTags='')
    struct = _build_struct(page, source=None, tags='')

    result = _load(struct, page)

    node = next(iter(result), None)
    assert node is not None
    assert 'webpage' not in node.attr


def test_load_filters_node_when_user_lacks_tag():
    site = _StubSite({'pkg:demo/report.html': 'https://example.test/_storage/demo/report.html'})
    page = _StubPage(site=site, userTags='SOMETHING_ELSE')
    struct = _build_struct(page, source='pkg:demo/report.html', tags='REPORT_VIEW')

    result = _load(struct, page)

    assert len(result) == 0


def test_load_allows_node_when_user_has_tag():
    site = _StubSite({'pkg:demo/report.html': 'https://example.test/_storage/demo/report.html'})
    page = _StubPage(site=site, userTags='REPORT_VIEW')
    struct = _build_struct(page, source='pkg:demo/report.html', tags='REPORT_VIEW')

    result = _load(struct, page)

    assert len(result) == 1
    node = next(iter(result), None)
    assert node is not None
    assert node.attr['label'] == 'Report'
