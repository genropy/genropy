"""The data a connection or a user writes belongs to its workspace (#1564, #1565).

``domainDataFolder`` is the only place that says where a domain keeps its
files; the static handlers, the page helpers, the cleanup and the register
freeze file all go through it. The root domain and single-domain sites keep
the historical ``data`` folder, so nothing moves for them.
"""

import os

from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.web.gnrwsgisite_proxy.gnrstatichandler import (
    ConnectionStaticHandler, PageStaticHandler, UserStaticHandler)
from gnr.web.daemon.siteregister import SiteRegister
from gnr.web.daemon.siteregister_client import SiteRegisterClient


class _FakeSite:
    rootDomain = '_main_'
    default_uri = '/app/'

    def __init__(self, site_path, multidomain=False, currentDomain='_main_'):
        self.site_path = str(site_path)
        self.multidomain = multidomain
        self.currentDomain = currentDomain

    domainDataFolder = GnrWsgiSite.domainDataFolder
    allConnectionsFolder = GnrWsgiSite.allConnectionsFolder
    allUsersFolder = GnrWsgiSite.allUsersFolder
    current_home_uri = GnrWsgiSite.current_home_uri


def test_single_domain_keeps_the_site_data_folder(tmp_path):
    site = _FakeSite(tmp_path)
    assert site.domainDataFolder('_users', 'bob') == os.path.join(
        str(tmp_path), 'data', '_users', 'bob')


def test_root_domain_keeps_the_site_data_folder_in_multidomain(tmp_path):
    site = _FakeSite(tmp_path, multidomain=True)
    assert site.allConnectionsFolder == os.path.join(str(tmp_path), 'data', '_connections')


def test_workspace_owns_its_data_folder(tmp_path):
    site = _FakeSite(tmp_path, multidomain=True, currentDomain='acme')
    assert site.allUsersFolder == os.path.join(
        str(tmp_path), 'data', '_domains', 'acme', '_users')


def test_same_user_in_two_workspaces_never_shares_a_folder(tmp_path):
    a = _FakeSite(tmp_path, multidomain=True, currentDomain='a')
    b = _FakeSite(tmp_path, multidomain=True, currentDomain='b')
    assert (UserStaticHandler(a).path('admin', 'x.pdf')
            != UserStaticHandler(b).path('admin', 'x.pdf'))


def test_static_handlers_follow_the_domain_folder(tmp_path):
    site = _FakeSite(tmp_path, multidomain=True, currentDomain='acme')
    base = os.path.join(str(tmp_path), 'data', '_domains', 'acme')
    assert ConnectionStaticHandler(site).path('c1', 'f') == os.path.join(base, '_connections', 'c1', 'f')
    assert PageStaticHandler(site).path('c1', 'p1', 'f') == os.path.join(base, '_connections', 'c1', 'p1', 'f')
    assert UserStaticHandler(site).path('bob', 'f') == os.path.join(base, '_users', 'bob', 'f')


def test_static_urls_carry_the_workspace(tmp_path):
    site = _FakeSite(tmp_path, multidomain=True, currentDomain='acme')
    assert UserStaticHandler(site).url('bob', 'f') == '/app/acme/_user/bob/f'
    assert PageStaticHandler(site).url('c1', 'p1', 'f') == '/app/acme/_page/c1/p1/f'


def test_static_urls_unchanged_outside_multidomain(tmp_path):
    site = _FakeSite(tmp_path)
    assert ConnectionStaticHandler(site).url('c1', 'f') == '/app/_conn/c1/f'


def test_register_freeze_file_is_per_workspace(tmp_path):
    client = _FakeSite(tmp_path, multidomain=True, currentDomain='acme')
    client.site = client
    client.STORAGE_PATH = SiteRegisterClient.STORAGE_PATH
    path = SiteRegisterClient.registerStoragePath(client)
    assert path == os.path.join(str(tmp_path), 'data', '_domains', 'acme', 'siteregister_data.pik')
    assert os.path.isdir(os.path.dirname(path))


def test_register_freeze_file_unchanged_for_root_domain(tmp_path):
    client = _FakeSite(tmp_path, multidomain=True)
    client.site = client
    client.STORAGE_PATH = SiteRegisterClient.STORAGE_PATH
    assert SiteRegisterClient.registerStoragePath(client) == os.path.join(
        str(tmp_path), 'siteregister_data.pik')


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()


def test_load_reports_a_missing_freeze_file(tmp_path):
    reg = SiteRegister(_FakeServer(), sitename='t',
                       storage_path=str(tmp_path / 'siteregister_data.pik'))
    assert reg.load() is False
