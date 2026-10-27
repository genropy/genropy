"""The 2fa "remember this client" cookie on a real database.

The cookie must be signed, bound to the user and to the user's 2fa secret, and
expire after ``expiry_days`` days. The service is loaded by path: ``projects/``
is not importable. Request and response are the real werkzeug objects the site
uses, so the cookie goes through the same serialization a browser would see.
"""
import importlib.util
import pathlib
import time
import types
from http.cookies import SimpleCookie

import pytest
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from core.common import BaseGnrTest

from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.web.gnrwebreqresp import GnrWebRequest, GnrWebResponse

SERVICE = (pathlib.Path(__file__).parents[3] / 'projects' / 'gnrcore' / 'packages'
           / 'adm' / 'resources' / 'services' / '2fa' / 'service.py')


def _service_class():
    spec = importlib.util.spec_from_file_location('adm_2fa_service', SERVICE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Main


class _Page(object):
    siteName = 'testsite'
    newMarshalCookie = GnrBaseWebPage.newMarshalCookie
    get_cookie = GnrBaseWebPage.get_cookie
    add_cookie = GnrBaseWebPage.add_cookie

    def __init__(self, cookies=None):
        self.site = types.SimpleNamespace(config={'secret': 'site-secret'})
        headers = {'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items())} if cookies else {}
        self.request = GnrWebRequest(Request(EnvironBuilder(path='/', headers=headers).get_environ()))
        self.response = GnrWebResponse(Response())

    def set_cookies(self):
        result = {}
        for header in self.response.headers.getlist('Set-Cookie'):
            cookie = SimpleCookie()
            cookie.load(header)
            for name, morsel in cookie.items():
                result[name] = morsel
        return result


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module')
def users(db_sqlite):
    tbl = db_sqlite.table('adm.user')
    ids = {}
    for username in ('tfa_alice', 'tfa_bob'):
        rec = tbl.newrecord(username=username, email=f'{username}@test.local', status='conf',
                            md5pwd='secret', avatar_secret_2fa=f'{username}-2fa')
        tbl.insert(rec)
        ids[username] = rec['id']
    db_sqlite.commit()
    return ids


def _service(db, page):
    parent = types.SimpleNamespace(db=db, currentPage=page,
                                   gnrapp=types.SimpleNamespace(instanceName='test'))
    return _service_class()(parent=parent, secret='service-secret')


def _remember(db, user_id):
    page = _Page()
    _service(db, page).remember2fa(user_id)
    return page.set_cookies()


def _saved(db, user_id, cookies):
    return _service(db, _Page(cookies)).saved2fa(user_id)


def test_remembered_client_skips_the_code(db_sqlite, users):
    user_id = users['tfa_alice']
    morsels = _remember(db_sqlite, user_id)
    cookies = {name: morsel.value for name, morsel in morsels.items()}
    assert _saved(db_sqlite, user_id, cookies) is True


def test_cookie_lasts_expiry_days(db_sqlite, users):
    morsel = next(iter(_remember(db_sqlite, users['tfa_alice']).values()))
    expires = time.mktime(time.strptime(morsel['expires'], '%a, %d %b %Y %H:%M:%S GMT')) - time.timezone
    assert 29 * 86400 < expires - time.time() <= 30 * 86400


def test_unsigned_cookie_is_refused(db_sqlite, users):
    user_id = users['tfa_alice']
    assert _saved(db_sqlite, user_id, {f'testsite_{user_id}_otp': user_id}) is False


def test_cookie_of_another_user_is_refused(db_sqlite, users):
    alice, bob = users['tfa_alice'], users['tfa_bob']
    value = next(iter(_remember(db_sqlite, alice).values())).value
    assert _saved(db_sqlite, bob, {f'testsite_{bob}_otp': value}) is False


def test_expired_cookie_is_refused(db_sqlite, users, monkeypatch):
    user_id = users['tfa_alice']
    cookies = {name: m.value for name, m in _remember(db_sqlite, user_id).items()}
    later = time.time() + 31 * 86400
    monkeypatch.setattr('gnr.web.gnrcookie.time', lambda: later)
    assert _saved(db_sqlite, user_id, cookies) is False


def test_new_2fa_secret_revokes_remembered_clients(db_sqlite, users):
    user_id = users['tfa_bob']
    cookies = {name: m.value for name, m in _remember(db_sqlite, user_id).items()}
    with db_sqlite.table('adm.user').recordToUpdate(user_id) as user:
        user['avatar_secret_2fa'] = 'tfa_bob-new-2fa'
    db_sqlite.commit()
    assert _saved(db_sqlite, user_id, cookies) is False
