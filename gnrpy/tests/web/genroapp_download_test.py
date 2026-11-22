"""GenroApp download from the user settings and the ``connector`` webtool.

The site exposes the GenroApp link for each desktop platform; the ``connector`` webtool
gives the logged user a personal site connector, signed on request by the signing service
named in the ``<genroapp>`` tag of the instance; the ``apps`` formlet group shows up only
when at least one of the two is available.

The HTTP call to the signing service is the only mocked part (``FakeSigner``).
"""

import importlib.util
import json
import pathlib
import types

import pytest

import gnr.web.gnrwsgisite as gws
from gnr.web import gnrgenroapp
from gnr.web.gnrcookie import MarshalCookie

from webcommon import BaseGnrDaemonTest
from test_genroapp_connector import TAG, FakeSigner, connector_payload

FORMLET_DIR = (pathlib.Path(__file__).parents[3] / 'projects' / 'gnrcore' / 'packages'
               / 'adm' / 'resources' / 'tables' / 'user_setting' / 'formlet' / 'apps')

CONNECTOR_MIME = 'application/vnd.softwell.connection+json'
USER = 'genroapp_webtool_user'
CONNECTION_ID = 'genroapp_webtool_connection'


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
        self.application = site.gnrapp
        self.connection = _ConnectionStub(user_device)


class TestGenroAppDownload(BaseGnrDaemonTest):

    @pytest.fixture
    def tag(self):
        """Write the ``<genroapp>`` tag of the instance; it is removed after the test."""
        config = self.site.gnrapp.config

        def setter(**attributes):
            config.popNode('genroapp')
            config.setItem('genroapp', None, **dict(TAG, **attributes))
        yield setter
        config.popNode('genroapp')

    @pytest.fixture
    def signer(self, monkeypatch):
        fake = FakeSigner()
        monkeypatch.setattr(gnrgenroapp.requests, 'post', fake.post)
        return fake

    @pytest.fixture
    def logged(self):
        """A user of ``adm.user`` with a connection in the site register: the headers
        of a request with the cookie of that connection."""
        site = self.site
        db = site.db
        users = db.table('adm.user')
        user_id = users.newPkeyValue()
        users.insert(dict(id=user_id, username=USER, md5pwd='secret', status='conf',
                          email=f'{USER}@test.local', avatar_secret_2fa=None))
        db.commit()
        site.register.new_connection(CONNECTION_ID, types.SimpleNamespace(
            connection_name='test', user=USER, user_id=user_id, user_tags='user', ip='127.0.0.1',
            browser_name='test', user_agent='test', avatar_extra=None, electron_static=None))
        cookie = MarshalCookie({'user': USER, 'connection_id': CONNECTION_ID, 'data': None, 'locale': None},
                               site.config['secret'] or site.site_name)
        yield {'Cookie': f'{site.currentDomainIdentifier}={cookie.output()}'}
        site.register.drop_connection(CONNECTION_ID)
        db.table('adm.user_connector').deleteSelection(where='$user_id=:u', u=user_id)
        users.deleteSelection(where='$id=:u', u=user_id)
        db.commit()

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

    def test_webtool_answers_404_without_the_tag(self, logged, signer):
        response = self.client.get('/_tools/connector', headers=logged)
        assert response['status'].startswith('404 ')
        assert 'Content-Disposition' not in dict(response['headers'])
        assert not signer.calls

    def test_webtool_answers_401_without_login(self, tag, signer):
        tag()
        response = self.client.get('/_tools/connector')
        assert response['status'].startswith('401 ')
        assert not signer.calls

    def test_webtool_answers_401_to_a_cookie_of_no_connection(self, tag, signer, logged):
        tag()
        self.site.register.drop_connection(CONNECTION_ID)
        try:
            response = self.client.get('/_tools/connector', headers=logged)
        finally:
            # the fixture drops the connection again
            self.site.register.new_connection(CONNECTION_ID, types.SimpleNamespace(
                connection_name='test', user=USER, user_id=None, user_tags='user', ip='127.0.0.1',
                browser_name='test', user_agent='test', avatar_extra=None, electron_static=None))
        assert response['status'].startswith('401 ')
        assert not signer.calls

    def test_webtool_gives_the_logged_user_the_signed_connector(self, tag, signer, logged):
        tag(capabilities='signature')
        response = self.client.get('/_tools/connector', headers=logged)
        assert response['status'].startswith('200 ')
        headers = dict(response['headers'])
        assert headers['Content-Type'].startswith(CONNECTOR_MIME)
        assert headers['Content-Disposition'] == f'attachment; filename={self.site.site_name}.site'
        assert headers['Cache-Control'] == 'private, no-store'
        connector = json.loads(response['data'])
        assert set(connector) == {'payload', 'signature'}
        payload = connector_payload(connector)
        assert payload['user'] == USER and payload['capabilities'] == ['signature']
        call = signer.calls[0]
        assert call['headers'] == {'Authorization': 'Bearer tag-token'}
        assert call['body']['url'] == payload['url'] == 'http://127.0.0.1/'
        row = self.site.db.table('adm.user_connector').query(
            columns='$connector_id', where='@user_id.username=:u', u=USER).fetch()[0]
        assert row['connector_id'] == payload['connector_id']

    def test_the_connector_names_the_site_with_its_path(self, tag, signer, logged, monkeypatch):
        """A site mounted under a path: the connector opens that path, not the root of the host."""
        tag()
        monkeypatch.setattr(self.site, 'default_uri', '/gestionale/')
        response = self.client.get('/_tools/connector', headers=logged)
        assert response['status'].startswith('200 ')
        assert signer.calls[0]['body']['url'] == 'http://127.0.0.1/gestionale/'

    def test_the_connector_names_the_store_of_the_request(self, tag, signer, logged, monkeypatch):
        """A request through a named store of a single-domain site: the connector opens that store."""
        tag()
        monkeypatch.setitem(self.site.db.stores_handler.dbstores, 'reviewstore', {})
        response = self.client.get('/reviewstore/_tools/connector', headers=logged)
        assert response['status'].startswith('200 ')
        assert connector_payload(json.loads(response['data']))['url'] == 'http://127.0.0.1/reviewstore/'
        assert signer.calls[0]['body']['url'] == 'http://127.0.0.1/reviewstore/'

    def test_a_store_among_the_request_parameters_does_not_change_the_url(self, tag, signer, logged, monkeypatch):
        """A download at the site root with ``base_dbstore`` as a request parameter:
        only the route decides the signed URL, which stays the site root."""
        tag()
        monkeypatch.setitem(self.site.db.stores_handler.dbstores, 'reviewstore', {})
        response = self.client.get('/_tools/connector', query={'base_dbstore': 'reviewstore'}, headers=logged)
        assert response['status'].startswith('200 ')
        assert signer.calls[0]['body']['url'] == 'http://127.0.0.1/'
        assert connector_payload(json.loads(response['data']))['url'] == 'http://127.0.0.1/'

    def test_two_downloads_do_not_share_the_cache_header_list(self, tag, signer, logged):
        tag()
        for _ in range(2):
            headers = self.client.get('/_tools/connector', headers=logged)['headers']
            assert [value for name, value in headers if name == 'Cache-Control'] == ['private, no-store']

    def test_webtool_answers_409_to_a_new_user_on_a_full_site(self, tag, signer, logged):
        tag(max_users='0')
        response = self.client.get('/_tools/connector', headers=logged)
        assert response['status'].startswith('409 ')
        assert not signer.calls

    def test_webtool_answers_502_to_an_empty_signature(self, tag, signer, logged):
        tag()
        signer.answer = dict(signer.signed(dict(name='Test site', url='http://127.0.0.1/', user=USER,
                                                duration_days=30)), signature='')
        response = self.client.get('/_tools/connector', headers=logged)
        assert response['status'].startswith('502 ')
        assert self.site.db.table('adm.user_connector').query(
            where='@user_id.username=:u', u=USER).count() == 0

    def test_webtool_answers_502_when_the_signature_fails(self, tag, signer, logged):
        tag()
        signer.status_code = 500
        response = self.client.get('/_tools/connector', headers=logged)
        assert response['status'].startswith('502 ')
        assert self.site.db.table('adm.user_connector').query(
            where='@user_id.username=:u', u=USER).count() == 0

    @pytest.mark.parametrize('name', ['__info__', 'genroapp'])
    def test_formlet_enabled_on_mac(self, name, no_bundles):
        assert _load(name).is_enabled(_PageStub(self.site, 'mac:desktop')) is True

    @pytest.mark.parametrize('name', ['__info__', 'genroapp'])
    def test_formlet_hidden_without_app_and_connector(self, name, no_bundles):
        assert _load(name).is_enabled(_PageStub(self.site, 'linux:desktop')) is False

    @pytest.mark.parametrize('name', ['__info__', 'genroapp'])
    def test_formlet_enabled_by_the_tag_alone(self, name, no_bundles, tag):
        tag()
        assert _load(name).is_enabled(_PageStub(self.site, 'linux:desktop')) is True
