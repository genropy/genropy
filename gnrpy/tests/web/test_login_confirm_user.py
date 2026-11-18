"""The login status is enforced by the server, and the confirm and recovery flows act only on checked users and stored addresses.

Real ``adm`` users on the ``test_invoice`` sqlite database, a real page store on
an in-process ``SiteRegister`` and real ``sys.external_token`` rows, as in
``test_login_checked_avatar.py``. Only the mail service is replaced, to read
where each message would go.
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

LOGIN_METHODS = ('login_checkAvatar', 'login_setChecked', 'login_isChecked', 'login_doLogin', 'login_setSelectedRootenv',
                 'login_completeRootEnv', 'login_selectableGroups', 'login_require2fa',
                 'login_canSetWorkdate', 'login_confirmUser', 'login_confirmNewPassword',
                 'loginPreference', '_immediate_message_parameters')


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


class _MailService(object):
    def __init__(self):
        self.sent = []

    def sendmail_template(self, record, to_address=None, **kwargs):
        self.sent.append(to_address)


class _Application(GnrApp):
    """The real application with the web avatar lookup, without a site to serve it."""
    getAvatar = GnrWsgiWebApp.getAvatar
    checkAllowedIp = GnrWsgiWebApp.checkAllowedIp


class _Page(object):
    rootenv = Bag()
    user = None

    def __init__(self, application):
        self.register = SiteRegister(_FakeServer(), sitename='testsite')
        self.register.page_register.create('p1')
        self.register.connection_register.create('c1')
        self.application = application
        self.db = application.db
        self.mail = _MailService()
        self._loginPreference = Bag()
        self.logged = []
        self.site = types.SimpleNamespace(gnrapp=application, homepage='/')
        application.site = types.SimpleNamespace(currentPage=self, multidomain=False)
        cls = _login_component()
        for name in LOGIN_METHODS:
            setattr(self, name, types.MethodType(getattr(cls, name), self))

    def pageStore(self):
        return ServerStore(self.register, 'page', 'p1')

    def connectionStore(self):
        return ServerStore(self.register, 'connection', 'c1')

    def callPackageHooks(self, method, *args, **kwargs):
        return {}

    def getService(self, name):
        return self.mail if name == 'mail' else None

    def pageAuthTags(self, method=None):
        return None

    def doLogin(self, login=None, **kwargs):
        self.logged.append(login['user'])
        login['error'] = 'stop here'

    def externalUrl(self, path, **kwargs):
        return f"{path}?gnrtoken={kwargs['gnrtoken']}"

    clientDatetime = GnrWebPage.clientDatetime
    externalUrlToken = GnrWebPage.externalUrlToken


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module')
def application(tmp_path_factory):
    app = _Application('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(tmp_path_factory.mktemp('login_status'), 'testing'),
    ))
    db = app.db
    db.model.check(applyChanges=True)
    for status in ('conf', 'new', 'wait', 'invt', 'bann'):
        # an insert as invt sends the invitation from the trigger: the status is set afterwards
        db.table('adm.user').insert(dict(username=f'ls_{status}', md5pwd='secret', status='new',
                                         email=f'ls_{status}@test.local'))
        db.table('adm.user').batchUpdate(dict(status=status), where='$username=:u', u=f'ls_{status}')
    db.table('adm.user').insert(dict(username='ls_noaddr', md5pwd='secret', status='conf'))
    db.commit()
    return app


@pytest.fixture
def page(application):
    page = _Page(application)
    yield page
    application.db.rollback()


def _user_id(page, username):
    return page.db.table('adm.user').readColumns(columns='$id', where='$username=:u', u=username)


def _login(user):
    return Bag(dict(user=user, password='secret'))


def test_banned_user_is_refused_and_cannot_log_in(page):
    result = page.login_checkAvatar(user='ls_bann', password='secret')
    assert result['avatar.status'] == 'bann'
    assert result['avatar.user_id'] is None
    assert page.pageStore().getItem('confirm_user_id') is None
    assert page.login_doLogin(rootenv=Bag(), login=_login('ls_bann')) == {'error': 'Invalid login'}
    assert page.logged == []


@pytest.mark.parametrize('status', ['new', 'wait', 'invt'])
def test_unconfirmed_user_gets_the_confirm_flow_but_cannot_log_in(page, status):
    username = f'ls_{status}'
    result = page.login_checkAvatar(user=username, password='secret')
    assert result['avatar.status'] == status
    assert page.pageStore().getItem('confirm_user_id') == _user_id(page, username)
    assert page.login_doLogin(rootenv=Bag(), login=_login(username)) == {'error': 'Invalid login'}
    assert page.logged == []


def test_confirmed_user_logs_in(page):
    page.login_checkAvatar(user='ls_conf', password='secret')
    assert page.pageStore().getItem('confirm_user_id') is None
    page.login_doLogin(rootenv=Bag(), login=_login('ls_conf'))
    assert page.logged == ['ls_conf']


def test_a_new_check_clears_the_user_to_confirm(page):
    page.login_checkAvatar(user='ls_new', password='secret')
    page.login_checkAvatar(user='ls_conf', password='secret')
    assert page.pageStore().getItem('confirm_user_id') is None


def test_confirm_without_a_checked_user_is_refused(page):
    assert page.login_confirmUser(email='x@example.invalid', user_id=_user_id(page, 'ls_new')) == 'err'
    assert page.mail.sent == []


def test_confirm_acts_once_on_the_checked_user(page):
    page.login_checkAvatar(user='ls_new', password='secret')
    assert page.login_confirmUser(email='ls_new_new@test.local') == 'ok'
    assert page.mail.sent == ['ls_new_new@test.local']
    assert page.pageStore().getItem('confirm_user_id') is None
    assert page.login_confirmUser(email='ls_new_new@test.local') == 'err'


def test_recovery_by_username_goes_to_the_stored_address(page):
    assert page.login_confirmNewPassword(username='ls_conf', email='attacker@example.invalid') == 'ok'
    assert page.mail.sent == ['ls_conf@test.local']
    token = page.db.table('sys.external_token').query(columns='$parameters').fetch()[-1]
    assert Bag(token['parameters'])['userid'] == _user_id(page, 'ls_conf')


def test_recovery_by_email_is_unchanged(page):
    assert page.login_confirmNewPassword(email='ls_conf@test.local') == 'ok'
    assert page.mail.sent == ['ls_conf@test.local']


def test_recovery_without_a_stored_address_is_refused(page):
    assert page.login_confirmNewPassword(username='ls_noaddr', email='attacker@example.invalid') == 'err'
    assert page.mail.sent == []
