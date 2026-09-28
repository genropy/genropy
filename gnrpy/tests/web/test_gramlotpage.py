"""Exercise the optional adapter through real Werkzeug requests and TYTX."""
from types import SimpleNamespace

import pytest
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

pytest.importorskip('gramlot')
from gramlot.page import endpoint, source
from gramlot.transport import to_tytx
from genro_tytx import from_tytx
from gnr.web.gramlotpage import GramlotPage
from gnr.core.gnrbag import Bag


class PublicPage(GramlotPage):
    public = True

    def main(self, root):
        root.h2('Hello World')

    @endpoint
    def echo(self, value):
        return value

    @source
    def detail(self, root):
        root.p('Remote Source')


def dispatch(path='', method='GET', data=None, origin=None, page_class=PublicPage,
             site=None, extra_headers=None):
    headers = {'Content-Type': 'application/vnd.tytx+json'}
    headers.update(extra_headers or {})
    if origin:
        headers['Origin'] = origin
    env = EnvironBuilder(path='/demo' + path, method=method, data=data,
                         headers=headers).get_environ()
    page = page_class(site or SimpleNamespace(db=object()), path.strip('/').split('/') if path else ())
    return page.serve(Request(env), Response())


def test_single_bundle_document():
    response = dispatch()
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert text.count(' src=') == 1
    assert '/demo/_assets/gramlot.min.js' in text
    assert 'importmap' not in text


def test_explicit_public_opt_in():
    assert dispatch(page_class=GramlotPage).status_code == 403


def test_endpoint_and_source():
    response = dispatch('/_rpc/data/echo', 'POST', to_tytx({'value': 42}, 'json'))
    assert from_tytx(response.get_data(as_text=True), transport='json')['result'] == 42
    response = dispatch('/_rpc/source/detail', 'POST', to_tytx({}, 'json'))
    assert response.status_code == 200
    assert 'Remote Source' in response.get_data(as_text=True)


@pytest.mark.parametrize('path,method,data,origin,status', [
    ('/_rpc/data/serve', 'POST', '{}', None, 404),
    ('/_rpc/data/echo', 'GET', None, None, 405),
    ('/_rpc/data/echo', 'POST', '{}', 'https://other.test', 403),
    ('/_rpc/data/echo', 'POST', 'invalid', None, 400),
    ('/_rpc/data/echo', 'POST', to_tytx({}, 'json'), None, 422),
    ('/_rpc/source/echo', 'POST', '{}', None, 404),
])
def test_dispatch_boundary(path, method, data, origin, status):
    assert dispatch(path, method, data, origin).status_code == status


@pytest.fixture
def gramlot_db(tmp_path):
    from gnr.sql.gnrsql import GnrSqlDb

    db = GnrSqlDb(implementation='sqlite', dbname=str(tmp_path / 'gramlot.db'))
    try:
        yield db
    finally:
        db.closeConnection()
        db.clearCurrentEnv()


def test_db_discards_previous_request_environment(gramlot_db):
    gramlot_db.updateEnv(storename='previous_store', user='previous_user',
                        userTags='admin', tenant='previous_tenant')
    page = PublicPage(SimpleNamespace(db=gramlot_db))

    db = page.db

    assert db is gramlot_db
    assert db.currentEnv == {}
    assert db.currentStorename == db.rootstore
    row = db.execute('SELECT :env_user, :env_userTags, :env_tenant').fetchone()
    assert tuple(row) == (None, None, None)


def test_db_keeps_environment_during_same_request(gramlot_db):
    page = PublicPage(SimpleNamespace(db=gramlot_db))
    page.db.updateEnv(user='current_user', tenant='current_tenant')

    row = page.db.execute('SELECT :env_user, :env_tenant').fetchone()

    assert tuple(row) == ('current_user', 'current_tenant')
    assert page.db.currentEnv['user'] == 'current_user'


def test_new_page_resets_shared_db_environment(gramlot_db):
    site = SimpleNamespace(db=gramlot_db)
    first = PublicPage(site)
    first.db.updateEnv(user='first_user')
    second = PublicPage(site)

    assert second.db is first.db
    assert second.db.currentEnv == {}
    assert second.db.execute('SELECT :env_user').fetchone()[0] is None


@pytest.mark.parametrize('configured', [None, 'browser', 'absolute'])
def test_instance_browser_asset(tmp_path, configured):
    config = Bag()
    asset_dir = tmp_path / ('gramlot_assets' if configured is None else 'browser')
    if configured:
        config.setItem('gramlot', None,
                       assets_path=str(asset_dir) if configured == 'absolute' else configured)
    asset_dir.mkdir()
    (asset_dir / 'gramlot.min.js').write_text('export const instanceBundle = true;')
    site = SimpleNamespace(site_path=str(tmp_path), config=config)
    response = dispatch('/_assets/gramlot.min.js', site=site)
    try:
        assert response.status_code == 200
        response.direct_passthrough = False
        assert response.get_data(as_text=True) == 'export const instanceBundle = true;'
        etag = response.headers['ETag']
    finally:
        response.close()
    cached = dispatch('/_assets/gramlot.min.js', site=site,
                      extra_headers={'If-None-Match': etag})
    try:
        assert cached.status_code == 304
    finally:
        cached.close()
    assert dispatch('/_assets/../gramlot.min.js', site=site).status_code == 404


def test_missing_instance_browser_asset(tmp_path):
    site = SimpleNamespace(site_path=str(tmp_path), config=Bag())
    response = dispatch('/_assets/gramlot.min.js', site=site)
    assert response.status_code == 503
    assert str(tmp_path) not in response.get_data(as_text=True)


def test_private_page_does_not_serve_assets():
    assert dispatch('/_assets/gramlot.min.js', page_class=GramlotPage).status_code == 403
