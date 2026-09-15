"""Unit tests for the experimental page-class cache (#1065).

Three things are pinned here:

- the cache helpers on ``ResourceLoader``: hit, miss, LRU eviction at the
  ceiling, drop on page close;
- the flag, read once from the ``<experimental>`` tag of instanceconfig.xml;
- the isolation of ``css_requires``/``js_requires``, which the cache turns
  from per-request lists into class attributes shared by every request of
  the same page.

A full site is not built: ``ResourceLoader.__init__`` needs six values from
its site and one static handler, so a stand-in supplies them and the code
under test is the real one.
"""

import gnr.web.gnrwsgisite_proxy.gnrresourceloader as grl
from gnr.web.gnrhtmlpage import GnrHtmlPage
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeStatic:
    def path(self, *args):
        return '/'.join(str(a) for a in args)


class _FakeApp:
    """The slice of GnrApp that page_class_cache_enabled touches."""

    def __init__(self, flag):
        self.flag = flag
        self.flag_reads = 0

    def experimentalFlag(self, group, name):
        assert (group, name) == ('page', 'page_class_cache')
        self.flag_reads += 1
        return self.flag


class _FakeSite:
    """The slice of GnrWsgiSite that ResourceLoader.__init__ touches."""

    def __init__(self, flag=False):
        self.site_path = '/tmp/site'
        self.site_name = 'testsite'
        self.gnr_config = {}
        self.debug = False
        self.default_page = None
        self.gnrapp = _FakeApp(flag)

    def getStatic(self, name):
        return _FakeStatic()


def _loader(flag=False):
    site = _FakeSite(flag=flag)
    return ResourceLoader(site=site), site


class _PageA:
    pass


class _PageB:
    pass


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def test_store_then_load_is_a_hit():
    loader, _site = _loader()
    key = ('page-1', '/pkg/a.py')
    loader.store_page_class_cache(key, _PageA)
    assert loader.load_page_class_cache(key) is _PageA


def test_load_of_an_unknown_key_is_a_miss():
    loader, _site = _loader()
    assert loader.load_page_class_cache(('page-1', '/pkg/a.py')) is None


def test_same_page_id_on_another_module_does_not_hit():
    """A page_id is validated against the connection, never against the url."""
    loader, _site = _loader()
    loader.store_page_class_cache(('page-1', '/pkg/a.py'), _PageA)
    assert loader.load_page_class_cache(('page-1', '/pkg/b.py')) is None


def test_same_module_on_another_page_id_does_not_hit():
    loader, _site = _loader()
    loader.store_page_class_cache(('page-1', '/pkg/a.py'), _PageA)
    assert loader.load_page_class_cache(('page-2', '/pkg/a.py')) is None


def test_two_pages_of_the_same_module_keep_their_own_class():
    loader, _site = _loader()
    loader.store_page_class_cache(('page-1', '/pkg/a.py'), _PageA)
    loader.store_page_class_cache(('page-2', '/pkg/a.py'), _PageB)
    assert loader.load_page_class_cache(('page-1', '/pkg/a.py')) is _PageA
    assert loader.load_page_class_cache(('page-2', '/pkg/a.py')) is _PageB


def test_eviction_at_the_ceiling_drops_the_least_recently_used(monkeypatch):
    monkeypatch.setattr(grl, 'PAGE_CLASS_CACHE_MAXSIZE', 3)
    loader, _site = _loader()
    for i in range(4):
        loader.store_page_class_cache(('page-%d' % i, '/pkg/a.py'), _PageA)
    assert len(loader._page_class_cache) == 3
    assert loader.load_page_class_cache(('page-0', '/pkg/a.py')) is None
    assert loader.load_page_class_cache(('page-3', '/pkg/a.py')) is _PageA


def test_a_read_refreshes_the_lru_position(monkeypatch):
    monkeypatch.setattr(grl, 'PAGE_CLASS_CACHE_MAXSIZE', 2)
    loader, _site = _loader()
    loader.store_page_class_cache(('page-0', '/pkg/a.py'), _PageA)
    loader.store_page_class_cache(('page-1', '/pkg/a.py'), _PageA)
    loader.load_page_class_cache(('page-0', '/pkg/a.py'))
    loader.store_page_class_cache(('page-2', '/pkg/a.py'), _PageA)
    assert loader.load_page_class_cache(('page-0', '/pkg/a.py')) is _PageA
    assert loader.load_page_class_cache(('page-1', '/pkg/a.py')) is None


def test_drop_forgets_every_entry_of_a_closed_page():
    loader, _site = _loader()
    loader.store_page_class_cache(('page-1', '/pkg/a.py'), _PageA)
    loader.store_page_class_cache(('page-1', '/pkg/b.py'), _PageB)
    loader.store_page_class_cache(('page-2', '/pkg/a.py'), _PageA)
    loader.drop_page_class_cache('page-1')
    assert loader.load_page_class_cache(('page-1', '/pkg/a.py')) is None
    assert loader.load_page_class_cache(('page-1', '/pkg/b.py')) is None
    assert loader.load_page_class_cache(('page-2', '/pkg/a.py')) is _PageA


def test_drop_of_an_unknown_page_is_harmless():
    loader, _site = _loader()
    loader.store_page_class_cache(('page-1', '/pkg/a.py'), _PageA)
    loader.drop_page_class_cache('page-9')
    assert loader.load_page_class_cache(('page-1', '/pkg/a.py')) is _PageA


# ---------------------------------------------------------------------------
# The flag
# ---------------------------------------------------------------------------


def test_flag_on_enables_the_cache():
    loader, _site = _loader(flag=True)
    assert loader.page_class_cache_enabled() is True


def test_flag_off_disables_the_cache():
    loader, _site = _loader(flag=False)
    assert loader.page_class_cache_enabled() is False


def test_flag_is_read_once_at_startup():
    loader, site = _loader(flag=True)
    loader.page_class_cache_enabled()
    loader.page_class_cache_enabled()
    assert site.gnrapp.flag_reads == 1


# ---------------------------------------------------------------------------
# css_requires / js_requires isolation
# ---------------------------------------------------------------------------


class _FakeHead:
    def style(self, *args, **kwargs):
        pass


class _FakeBuilder:
    head = _FakeHead()


class _RenderStub:
    """The slice of a page that setCssRequires/setJsRequires touch.

    ``css_requires``/``js_requires`` are class attributes here exactly as
    ``get_page_class`` builds them, so an in-place extend would show up on
    the class and leak into the next render of a cached class.
    """

    css_requires = ['base.css']
    js_requires = ['base.js']

    def __init__(self):
        self.envelope_css_requires = {'extra.css': '/extra.css'}
        self.envelope_js_requires = {'extra.js': '/extra.js'}
        self.builder = _FakeBuilder()

    def getResourceExternalUriList(self, name, ext, add_mtime=None):
        return []

    def script(self, *args, **kwargs):
        pass

    body = property(lambda self: self)


def test_root_render_does_not_extend_the_class_css_requires():
    stub = _RenderStub()
    GnrHtmlPage.setCssRequires(stub)
    GnrHtmlPage.setCssRequires(stub)
    assert _RenderStub.css_requires == ['base.css']


def test_root_render_does_not_extend_the_class_js_requires():
    stub = _RenderStub()
    GnrHtmlPage.setJsRequires(stub)
    GnrHtmlPage.setJsRequires(stub)
    assert _RenderStub.js_requires == ['base.js']
