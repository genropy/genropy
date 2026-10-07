"""login_doLogin goes through only for the user login_checkAvatar checked on the same page.

The login component is loaded by path: ``projects/`` is not importable. The page
store is a real one, on an in-process ``SiteRegister`` as in
``siteregister_serverstore_changes_test.py``. The group menu test authenticates
real ``adm`` users on the ``test_invoice`` sqlite database.
"""
import importlib.util
import os
import pathlib
import types

import pytest

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web.daemon.siteregister import SiteRegister
from gnr.web.daemon.siteregister_client import ServerStore
from gnr.web.gnrwebapp import GnrWsgiWebApp
from gnr.web.gnrwebpage import GnrWebPage

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
        self.do_login_kwargs = kwargs
        login['error'] = 'stop here'


class _Application(GnrApp):
    """The real application with the web avatar lookup, without a site to serve it."""
    getAvatar = GnrWsgiWebApp.getAvatar
    checkAllowedIp = GnrWsgiWebApp.checkAllowedIp


class _AppPage(_Page):
    rootenv = Bag()

    def __init__(self, application):
        super().__init__()
        self.register.connection_register.create('c1')
        self.application = application
        self.db = application.db
        application.site = types.SimpleNamespace(currentPage=self, multidomain=False)

    def connectionStore(self):
        return ServerStore(self.register, 'connection', 'c1')

    def callPackageHooks(self, method, *args, **kwargs):
        return {}

    def getService(self, name):
        return None

    def pageAuthTags(self, method=None):
        return None

    clientDatetime = GnrWebPage.clientDatetime


def _bind(page, *names):
    cls = _login_component()
    for name in names:
        setattr(page, name, types.MethodType(getattr(cls, name), page))
    return page


def _page():
    return _bind(_Page(), 'login_doLogin', 'login_setChecked', 'login_isChecked')


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module')
def application(tmp_path_factory):
    app = _Application('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(tmp_path_factory.mktemp('login_groups'), 'testing'),
    ))
    db = app.db
    db.model.check(applyChanges=True)
    groups = db.table('adm.group')
    groups.insert(dict(code='LGMAIN', description='Main'))
    groups.insert(dict(code='LGPLAIN', description='Plain'))
    groups.insert(dict(code='LG2FA', description='Strong', require_2fa=True))
    for username, secret in (('lg_no2fa', None), ('lg_2fa', 'S3CR3T')):
        user = db.table('adm.user').insert(dict(username=username, md5pwd='secret', status='conf',
                                                email=f'{username}@test.local', group_code='LGMAIN',
                                                avatar_secret_2fa=secret))
        for code in ('LGPLAIN', 'LG2FA'):
            db.table('adm.user_group').insert(dict(user_id=user['id'], group_code=code))
    db.commit()
    return app


def _menu_codes(application, username):
    page = _bind(_AppPage(application), 'login_checkAvatar', 'login_setChecked', 'login_completeRootEnv',
                 'login_selectableGroups', 'login_require2fa', 'login_canSetWorkdate')
    result = page.login_checkAvatar(user=username, password='secret')
    assert result['rootenv.group_selector'] is True
    return result['avatar.login_groups'].digest('#v.code')


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


def test_guest_name_from_the_client_is_refused():
    page = _page()
    assert page.login_doLogin(rootenv=Bag(), login=_login('guest'), guestName='guest') == {'error': 'Invalid login'}
    assert page.logged == []


def test_guest_name_does_not_reach_do_login():
    page = _page()
    page.login_setChecked('alice')
    page.login_doLogin(rootenv=Bag(), login=_login('alice'), guestName='bob')
    assert page.logged == ['alice']
    assert 'guestName' not in page.do_login_kwargs


def test_group_menu_hides_2fa_groups_without_a_secret(application):
    assert _menu_codes(application, 'lg_no2fa') == ['LGMAIN', 'LGPLAIN']


def test_group_menu_offers_2fa_groups_with_a_secret(application):
    assert _menu_codes(application, 'lg_2fa') == ['LGMAIN', 'LGPLAIN', 'LG2FA']
