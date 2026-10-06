"""login_doLogin goes through only for the user login_checkAvatar checked on the same page.

The login component is loaded by path: ``projects/`` is not importable. The page
store is a real one, on an in-process ``SiteRegister`` as in
``siteregister_serverstore_changes_test.py``.
"""
import importlib.util
import pathlib
import types

from gnr.core.gnrbag import Bag
from gnr.web.daemon.siteregister import SiteRegister
from gnr.web.daemon.siteregister_client import ServerStore

LOGIN = (pathlib.Path(__file__).parents[3] / 'projects' / 'gnrcore'
         / 'packages' / 'adm' / 'resources' / 'login.py')


def _login_component():
    spec = importlib.util.spec_from_file_location('adm_login', LOGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LoginComponent


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


class _Page(object):
    def __init__(self):
        self.register = SiteRegister(_FakeServer(), sitename='testsite')
        self.register.page_register.create('p1')
        self.logged = []

    def pageStore(self):
        return ServerStore(self.register, 'page', 'p1')

    def doLogin(self, login=None, **kwargs):
        self.logged.append(login['user'])
        login['error'] = 'stop here'


def _page():
    cls = _login_component()
    page = _Page()
    for name in ('login_doLogin', 'login_setChecked', 'login_isChecked'):
        setattr(page, name, types.MethodType(getattr(cls, name), page))
    return page


def _login(user, group_code=None):
    return Bag(dict(user=user, password='secret', group_code=group_code))


def test_unchecked_login_is_refused():
    page = _page()
    assert page.login_doLogin(rootenv=Bag(), login=_login('alice')) == {'error': 'Invalid login'}
    assert page.logged == []


def test_checked_login_goes_through():
    page = _page()
    page.login_setChecked('alice')
    page.login_doLogin(rootenv=Bag(), login=_login('alice'))
    assert page.logged == ['alice']


def test_login_as_another_user_is_refused():
    page = _page()
    page.login_setChecked('alice')
    assert page.login_doLogin(rootenv=Bag(), login=_login('bob')) == {'error': 'Invalid login'}
    assert page.logged == []


def test_login_with_another_group_is_refused():
    page = _page()
    page.login_setChecked('alice', 'plain')
    assert page.login_doLogin(rootenv=Bag(), login=_login('alice', 'admin')) == {'error': 'Invalid login'}
    assert page.logged == []


def test_a_reset_check_refuses_the_login():
    page = _page()
    page.login_setChecked('alice')
    page.login_setChecked(None)
    assert page.login_doLogin(rootenv=Bag(), login=_login('alice')) == {'error': 'Invalid login'}


def test_pending_code_still_wins():
    page = _page()
    page.login_setChecked('alice')
    with page.pageStore() as ps:
        ps.setItem('waiting2fa', 'u1')
    assert page.login_doLogin(rootenv=Bag(), login=_login('alice')) == {'error': 'Waiting authentication code'}
    assert page.logged == []


def test_guest_login_needs_no_check():
    page = _page()
    page.login_doLogin(rootenv=Bag(), login=_login('guest'), guestName='guest')
    assert page.logged == ['guest']
