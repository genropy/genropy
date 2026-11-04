"""UrlInfo resolution through the site-wide pathfile_cache (#1449)."""

import pytest

from gnr.web.gnrwsgisite import UrlInfo


class _FakeSite:
    mainpackage = 'mainpkg'

    def __init__(self, static_dir):
        self.site_static_dir = str(static_dir)
        self.pathfile_cache = {}


@pytest.fixture
def site(tmp_path):
    folder = tmp_path / 'webpages' / 'office'
    folder.mkdir(parents=True)
    (folder / 'index.py').touch()
    (folder / 'orders.py').touch()
    return _FakeSite(tmp_path)


def resolve(site, *url):
    info = UrlInfo(site, ['webpages', *url])
    return info.relpath.rsplit('/webpages/', 1)[1], info.request_args


def test_folder_url_serves_its_index(site):
    assert resolve(site, 'office') == ('office/index.py', [])
    assert resolve(site, 'office') == ('office/index.py', [])


def test_folder_url_does_not_shadow_its_pages(site):
    resolve(site, 'office')
    assert resolve(site, 'office', 'orders') == ('office/orders.py', [])
    assert resolve(site, 'office', 'orders', 'x') == ('office/orders.py', ['x'])


def test_explicit_index_after_folder_url(site):
    resolve(site, 'office')
    assert resolve(site, 'office', 'index') == ('office/index.py', [])
