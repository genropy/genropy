"""Loading a resource never reroutes a method another resource already bound to the page (#1665).

Two grouplet-like resources pull the same handler through ``py_requires``: the
handler module is imported once, so both share its function objects.
"""

import textwrap

import pytest

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrlang import GnrObject, serializedFuncName
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader


class _FakeStatic:
    def path(self, *args):
        return '/'.join(str(a) for a in args)


class _FakeApp:
    def experimentalFlag(self, group, name):
        return False


class _FakeSite:
    """The slice of GnrWsgiSite that ResourceLoader touches."""

    def __init__(self):
        self.site_path = '/tmp/site'
        self.site_name = 'testsite'
        self.gnr_config = {}
        self.debug = False
        self.default_page = None
        self.gnrapp = _FakeApp()
        self.resource_loader = ResourceLoader(site=self)

    def getStatic(self, name):
        return _FakeStatic()


class _FakePage(GnrObject):
    def __init__(self, resourceDirs):
        self.resourceDirs = resourceDirs
        self.css_requires = []
        self.js_requires = []
        self.envelope_css_requires = {}
        self.envelope_js_requires = {}


_HANDLER = '''
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent

class GridHandler(BaseComponent):
    @public_method
    def gr_getTemplate(self):
        return 'template'
'''

_GROUPLET = '''
from gnr.web.gnrbaseclasses import BaseComponent

class Grouplet(BaseComponent):
    py_requires = 'routing_handler:GridHandler'
'''


@pytest.fixture
def site(tmp_path, monkeypatch):
    (tmp_path / 'routing_handler.py').write_text(textwrap.dedent(_HANDLER))
    (tmp_path / 'routing_account.py').write_text(textwrap.dedent(_GROUPLET))
    (tmp_path / 'routing_item.py').write_text(textwrap.dedent(_GROUPLET))
    fake_site = _FakeSite()
    monkeypatch.setattr(gws, 'currentSite', lambda: fake_site)
    return fake_site, [str(tmp_path)]


def test_loading_another_resource_keeps_the_bound_route(site):
    fake_site, resourceDirs = site
    loader = fake_site.resource_loader
    page = _FakePage(resourceDirs)
    loader.mixinPageComponent(page, 'routing_account:Grouplet')
    held = page.gr_getTemplate
    before = serializedFuncName(held)
    assert before == '*|routing_account:Grouplet;gr_getTemplate'

    loader.loadResource('routing_item:Grouplet', page=page)
    assert serializedFuncName(held) == before

    other_page = _FakePage(resourceDirs)
    loader.mixinPageComponent(other_page, 'routing_item:Grouplet')
    assert serializedFuncName(held) == before
    assert serializedFuncName(other_page.gr_getTemplate) == '*|routing_item:Grouplet;gr_getTemplate'
