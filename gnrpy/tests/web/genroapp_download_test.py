"""GenroApp download from the user settings.

The site exposes the GenroApp link for each desktop platform and the signed
RunDoc placed in ``site:genroapp/connection.rundoc``; the ``rundoc`` webtool
serves that file as an attachment; the ``apps`` formlet group shows up only
when at least one of the two is available.
"""

import importlib.util
import json
import os
import pathlib

import pytest

import gnr.web.gnrwsgisite as gws

from webcommon import BaseGnrDaemonTest

FORMLET_DIR = (pathlib.Path(__file__).parents[3] / 'projects' / 'gnrcore' / 'packages'
               / 'adm' / 'resources' / 'tables' / 'user_setting' / 'formlet' / 'apps')

RUNDOC = json.dumps({'payload': 'cGF5bG9hZA==', 'signature': 'c2lnbmF0dXJl'}).encode()
RUNDOC_MIME = 'application/vnd.softwell.connection+json'


def _load(name):
    spec = importlib.util.spec_from_file_location(f'apps_{name}', FORMLET_DIR / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ConnectionStub(object):
    def __init__(self, user_device):
        self.user_device = user_device


class _PageStub(object):
    def __init__(self, site, user_device):
        self.site = site
        self.connection = _ConnectionStub(user_device)


class TestGenroAppDownload(BaseGnrDaemonTest):

    @pytest.fixture
    def rundoc(self):
        path = self.site.getStaticPath(gws.GENROAPP_RUNDOC, autocreate=-1)
        with open(path, 'wb') as f:
            f.write(RUNDOC)
        yield path
        os.remove(path)

    @pytest.fixture
    def no_bundles(self, monkeypatch):
        monkeypatch.setattr(type(self.site), 'get_mobile_app_config',
                            lambda site, mobile_os=None: {})

    def test_mac_falls_back_to_the_published_link(self, no_bundles):
        assert self.site.get_genroapp_download_url('mac') == gws.GENROAPP_DOWNLOADS['mac']

    def test_platform_without_app_has_no_link(self, no_bundles):
        assert self.site.get_genroapp_download_url('linux') is None
        assert self.site.get_genroapp_download_url('mobile') is None

    def test_bundles_override_the_published_link(self, monkeypatch):
        monkeypatch.setattr(type(self.site), 'get_mobile_app_config',
                            lambda site, mobile_os=None: {'download_url': 'https://example.org/app.dmg'})
        assert self.site.get_genroapp_download_url('mac') == 'https://example.org/app.dmg'

    def test_rundoc_path_is_none_without_the_file(self):
        assert not os.path.exists(self.site.getStaticPath(gws.GENROAPP_RUNDOC))
        assert self.site.get_genroapp_rundoc_path() is None

    def test_rundoc_path_points_to_the_file(self, rundoc):
        assert self.site.get_genroapp_rundoc_path() == rundoc

    def test_webtool_serves_the_rundoc_as_attachment(self, rundoc):
        response = self.client.get('/_tools/rundoc')
        assert response['status'].startswith('200 ')
        headers = dict(response['headers'])
        assert headers['Content-Type'].startswith(RUNDOC_MIME)
        assert headers['Content-Disposition'] == f'attachment; filename={self.site.site_name}.rundoc'
        assert response['data'] == RUNDOC

    def test_webtool_answers_404_without_the_file(self):
        response = self.client.get('/_tools/rundoc')
        assert response['status'].startswith('404 ')
        assert 'Content-Disposition' not in dict(response['headers'])

    @pytest.mark.parametrize('name', ['__info__', 'genroapp'])
    def test_formlet_enabled_on_mac(self, name, no_bundles):
        assert _load(name).is_enabled(_PageStub(self.site, 'mac:desktop')) is True

    @pytest.mark.parametrize('name', ['__info__', 'genroapp'])
    def test_formlet_hidden_without_app_and_rundoc(self, name, no_bundles):
        assert _load(name).is_enabled(_PageStub(self.site, 'linux:desktop')) is False

    @pytest.mark.parametrize('name', ['__info__', 'genroapp'])
    def test_formlet_enabled_by_rundoc_alone(self, name, no_bundles, rundoc):
        assert _load(name).is_enabled(_PageStub(self.site, 'linux:desktop')) is True
