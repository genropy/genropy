"""A component's ``css_requires`` loads every same-named css file (#148).

A page-level ``css_requires`` is resolved by ``get_css_path`` across all the
resource dirs, so each package shipping a ``<name>.css`` contributes its own.
A component mixed in at runtime (a table resource View, a ``mixinComponent``)
goes through the RPC envelope instead, which used to carry only the first file.

The real ResourceLoader resolves real files in two resource dirs and mixes a
real component in. The page stand-in only carries the attributes the loader
reads, and resolves a file to its own path as uri.
"""

import os
import textwrap

import pytest

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrlang import GnrObject
from gnr.web.gnrwsgisite_proxy import gnrresourceloader
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader


CSS_NAME = 'cascade_probe'

_COMPONENT = '''
from gnr.web.gnrbaseclasses import BaseComponent

class Probe(BaseComponent):
    css_requires = '%s'

class MissingCss(BaseComponent):
    css_requires = 'cascade_probe_missing'
''' % CSS_NAME


class _FakeStatic:
    def path(self, *args):
        return '/'.join(str(a) for a in args)


class _FakeSite:
    """The slice of GnrWsgiSite that ResourceLoader touches."""

    def __init__(self):
        self.site_path = '/tmp/site'
        self.site_name = 'testsite'
        self.gnr_config = {}
        self.debug = False
        self.default_page = None
        self.gnrapp = None
        self.resource_loader = ResourceLoader(site=self)

    def getStatic(self, name):
        return _FakeStatic()


class _Page(GnrObject):
    def __init__(self, resourceDirs):
        self.resourceDirs = resourceDirs
        self.css_requires = []
        self.js_requires = []
        self.envelope_css_requires = {}
        self.envelope_js_requires = {}

    def resolveResourceUri(self, fpath, add_mtime=False, pkg=None):
        return fpath


@pytest.fixture
def loader_and_dirs(tmp_path, monkeypatch):
    dirs = []
    for folder in ('generic', 'specific'):
        dirpath = tmp_path / folder
        dirpath.mkdir()
        (dirpath / ('%s.css' % CSS_NAME)).write_text('.from_%s{color:red;}\n' % folder)
        dirs.append(str(dirpath))
    (tmp_path / 'specific' / 'cascade_probe_component.py').write_text(textwrap.dedent(_COMPONENT))
    fake_site = _FakeSite()
    monkeypatch.setattr(gws, 'currentSite', lambda: fake_site)
    # resourceDirs go from the most specific to the most generic
    return fake_site.resource_loader, list(reversed(dirs))


def test_module_under_test():
    checkout = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    assert gnrresourceloader.__file__.startswith(checkout + os.sep)


def test_component_css_carries_every_file(loader_and_dirs):
    loader, resourceDirs = loader_and_dirs
    page = _Page(resourceDirs)
    loader.mixinPageComponent(page, 'cascade_probe_component:Probe')
    # same files, same order as a page-level css_requires (generic first)
    assert page.envelope_css_requires[CSS_NAME] == loader.getResourceList(resourceDirs, CSS_NAME, 'css')
    assert len(page.envelope_css_requires[CSS_NAME]) == 2


def test_page_level_css_is_not_sent_again(loader_and_dirs):
    loader, resourceDirs = loader_and_dirs
    page = _Page(resourceDirs)
    page.css_requires.append(CSS_NAME)
    loader.mixinPageComponent(page, 'cascade_probe_component:Probe')
    assert CSS_NAME not in page.envelope_css_requires


def test_missing_css_sends_nothing(loader_and_dirs):
    loader, resourceDirs = loader_and_dirs
    page = _Page(resourceDirs)
    loader.mixinPageComponent(page, 'cascade_probe_component:MissingCss')
    assert page.envelope_css_requires['cascade_probe_missing'] is None
