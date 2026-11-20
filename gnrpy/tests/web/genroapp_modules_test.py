"""GenroApp modules served by the ``modules`` webtool.

Softwell signs each module and the site holds it unchanged in
``site:genroapp/modules/<name>/<version>/``. ``/_tools/modules`` answers the
array of the signed manifests, ``/_tools/modules/<name>/<version>/<path>``
the raw bytes of one package file; anything else is a 404.
"""

import json
import os
import shutil

import pytest

import gnr.web.gnrwsgisite as gws

from webcommon import BaseGnrDaemonTest

SCALE = {'payload': 'c2NhbGU=', 'signature': 'c2lnLXNjYWxl'}
DRAWER = {'payload': 'ZHJhd2Vy', 'signature': 'c2lnLWRyYXdlcg=='}
INIT_PY = b'VALUE = 42\n'


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)


class TestGenroAppModules(BaseGnrDaemonTest):

    @pytest.fixture
    def modules_root(self):
        root = self.site.getStaticPath(gws.GENROAPP_MODULES)
        assert not os.path.exists(root)
        yield root
        shutil.rmtree(root, ignore_errors=True)

    @pytest.fixture
    def modules(self, modules_root, tmp_path):
        _write(os.path.join(modules_root, 'scale', '1.2.0', 'manifest.json'), json.dumps(SCALE).encode())
        _write(os.path.join(modules_root, 'scale', '1.2.0', 'scale', '__init__.py'), INIT_PY)
        _write(os.path.join(modules_root, 'drawer', '0.1.0', 'manifest.json'), json.dumps(DRAWER).encode())
        _write(os.path.join(modules_root, '.DS_Store'), b'')
        outside = tmp_path / 'secret.txt'
        outside.write_bytes(b'secret')
        os.symlink(outside, os.path.join(modules_root, 'scale', '1.2.0', 'scale', 'link.txt'))
        os.symlink(tmp_path, os.path.join(modules_root, 'scale', 'linked'))
        yield modules_root

    def _call_tool(self, *args):
        tool = self.site.load_webtool('modules')
        tool.site = self.site
        return tool(*args)

    def _assert_404(self, response):
        assert response['status'].startswith('404 ')

    def test_modules_path_is_none_without_the_folder(self, modules_root):
        assert self.site.get_genroapp_modules_path() is None

    def test_modules_path_points_to_the_folder(self, modules):
        assert self.site.get_genroapp_modules_path() == os.path.realpath(modules)

    def test_index_answers_404_without_the_folder(self, modules_root):
        self._assert_404(self.client.get('/_tools/modules'))

    def test_index_lists_the_signed_manifests(self, modules):
        response = self.client.get('/_tools/modules')
        assert response['status'].startswith('200 ')
        assert dict(response['headers'])['Content-Type'].startswith('application/json')
        assert json.loads(response['data']) == [DRAWER, SCALE]

    def test_file_is_served_as_is(self, modules):
        response = self.client.get('/_tools/modules/scale/1.2.0/scale/__init__.py')
        assert response['status'].startswith('200 ')
        assert dict(response['headers'])['Content-Type'].startswith('application/octet-stream')
        assert response['data'] == INIT_PY

    @pytest.mark.parametrize('url', [
        '/_tools/modules/scale/1.2.0/manifest.json',
        '/_tools/modules/scale/1.2.0/scale/missing.py',
        '/_tools/modules/scale/1.2.0/scale',
        '/_tools/modules/scale/1.2.0/scale/link.txt',
        '/_tools/modules/scale/linked/secret.txt',
        '/_tools/modules/scale/1.2.0',
        '/_tools/modules/scale',
    ])
    def test_request_outside_a_package_file_answers_404(self, modules, url):
        self._assert_404(self.client.get(url))

    @pytest.mark.parametrize('args', [
        ('scale', '1.2.0', '..', '..', '..', 'connection.rundoc'),
        ('scale', '..', '..', 'drawer', '0.1.0', 'manifest.json'),
        ('..', '..', 'genroapp', 'modules', 'scale', '1.2.0', 'scale', '__init__.py'),
        ('scale', '1.2.0', '/etc/hosts'),
        ('scale', '/', 'etc', 'hosts'),
    ])
    def test_traversal_answers_404(self, modules, args):
        assert self._call_tool(*args).status_code == 404
