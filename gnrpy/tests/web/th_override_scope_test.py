"""A package declaring th_override_scope='context' keeps its _packages table-handler
overrides on the pages whose context package it is (#1299).

The real ResourceLoader mixes real resource files laid out as packages in tmp_path;
_th_mixinResource comes from resources/common/th/th_lib.py.
"""

import importlib.util
import os
import textwrap

import pytest

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrlang import GnrObject
from gnr.web.gnrwebpage import GnrWebPage
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader

TH_LIB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                           'resources', 'common', 'th', 'th_lib.py')

PACKAGES = ('owner', 'scoped', 'unscoped', 'third')
OVERRIDERS = ('scoped', 'unscoped')


def load_th_lib():
    spec = importlib.util.spec_from_file_location('th_lib_under_test',
                                                  os.path.abspath(TH_LIB_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TH_LIB = load_th_lib()

_FORM = '''
from gnr.web.gnrbaseclasses import BaseComponent

class Form(BaseComponent):
    def th_form(self, form):
        return '{label}'
'''


class _FakeStatic:
    def path(self, *args):
        return '/'.join(str(a) for a in args)


class _FakePackage:
    def __init__(self, name, folder, attributes=None):
        self.name = self.id = name
        self.packageFolder = folder
        self.attributes = dict(attributes or {})


class _FakeApp:
    def __init__(self, packages):
        self.packages = packages

    def experimentalFlag(self, group, name):
        return False


class _FakeSite:
    """The slice of GnrWsgiSite that ResourceLoader touches."""

    def __init__(self, root, packages):
        self.site_path = str(root / 'site')
        self.site_name = 'testsite'
        self.gnr_config = {}
        self.debug = False
        self.default_page = None
        self.resources_dirs = []
        self.gnrapp = _FakeApp(packages)
        self.resource_loader = ResourceLoader(site=self)

    def getStatic(self, name):
        return _FakeStatic()


class _FakeTable:
    pass


class _FakeDb:
    def __init__(self, packages):
        self.packages = packages

    def package(self, name):
        return self.packages.get(name)

    def table(self, name):
        return _FakeTable()


class _FakePage(GnrObject):
    """The slice of GnrWebPage that _th_mixinResource touches."""

    mixinComponent = GnrWebPage.mixinComponent
    _th_getResourceName = TH_LIB.TableHandlerCommon._th_getResourceName
    _th_mixinResource = TH_LIB.TableHandlerCommon._th_mixinResource

    def __init__(self, site, context, call_kwargs=None, page_args=None):
        self.site = site
        self.application = site.gnrapp
        self.db = _FakeDb(site.gnrapp.packages)
        self.package = self.db.package(context)
        self.resourceDirs = []
        self._call_kwargs = dict(call_kwargs or {})
        self.pageArgs = dict(page_args or {})
        self.css_requires = []
        self.js_requires = []
        self.envelope_css_requires = {}
        self.envelope_js_requires = {}
        self.mixed = []

    def mixin(self, component, **kwargs):
        self.mixed.append((getattr(component, '__mixin_pkg'), getattr(component, '__mixin_path')))
        return super().mixin(component, **kwargs)

    def overrides(self):
        return [pkg for pkg, path in self.mixed if path.startswith('tables/_packages/')]

    def build_form(self):
        self._th_mixinResource('root', table='owner.thing', defaultClass='Form')
        return self.root_form(None)


@pytest.fixture
def make_site(tmp_path, monkeypatch):
    def factory(**attributes):
        packages = {}
        for name in PACKAGES:
            folder = tmp_path / name
            packages[name] = _FakePackage(name, str(folder), attributes.get(name))
        owner_th = tmp_path / 'owner' / 'resources' / 'tables' / 'thing'
        owner_th.mkdir(parents=True)
        (owner_th / 'th_thing.py').write_text(textwrap.dedent(_FORM.format(label='owner')))
        for name in OVERRIDERS:
            override = tmp_path / name / 'resources' / 'tables' / '_packages' / 'owner' / 'thing'
            override.mkdir(parents=True)
            (override / 'th_thing.py').write_text(textwrap.dedent(_FORM.format(label=name)))
        site = _FakeSite(tmp_path, packages)
        monkeypatch.setattr(gws, 'currentSite', lambda: site)
        return site
    return factory


SCOPED = dict(scoped=dict(th_override_scope='context'))


def test_without_the_attribute_every_override_is_mixed(make_site):
    page = _FakePage(make_site(), 'third')
    assert page.build_form() == 'unscoped'
    assert page.mixed[0] == ('owner', 'tables/thing/th_thing:Form')
    assert page.overrides() == ['scoped', 'unscoped']


def test_scoped_override_stays_out_of_other_contexts(make_site):
    page = _FakePage(make_site(**SCOPED), 'third')
    assert page.build_form() == 'unscoped'
    assert page.overrides() == ['unscoped']


def test_scoped_override_wins_in_its_own_context(make_site):
    page = _FakePage(make_site(**SCOPED), 'scoped')
    assert page.build_form() == 'scoped'
    assert page.overrides() == ['unscoped', 'scoped']


def test_scoped_override_still_applies_as_declared_mainpkg(make_site):
    site = make_site(scoped=dict(th_override_scope='context'),
                     third=dict(mainpkg='scoped'))
    page = _FakePage(site, 'third')
    assert page.build_form() == 'unscoped'
    assert page.overrides() == ['scoped', 'unscoped']


def test_scope_holds_in_an_rpc_without_the_url_kwargs(make_site):
    site = make_site(**SCOPED)
    url_kwargs = dict(th_from_package='third')
    render = _FakePage(site, 'third', call_kwargs=url_kwargs, page_args=url_kwargs)
    rpc = _FakePage(site, 'third', call_kwargs=dict(method='_th_remoteFormDispatcher'),
                    page_args=url_kwargs)
    assert render.build_form() == rpc.build_form() == 'unscoped'
    assert render.overrides() == rpc.overrides() == ['unscoped']
