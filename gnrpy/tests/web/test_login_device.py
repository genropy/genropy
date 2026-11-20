"""GenroApp device login: registration, signed login, connection tags and the admin policy.

The keys are real P-256 keys made with ``cryptography``, as the Secure Enclave makes them.
The login component is loaded by path as in ``test_login_checked_avatar.py``; the
``adm`` users and devices live on a ``test_invoice`` sqlite database.
"""
import base64
import hashlib
import os
import types

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from gnr.core.gnrbag import Bag

from test_login_checked_avatar import _AppPage, _Application, _bind, _login
from test_login_checked_avatar import setup_module, teardown_module  # noqa: F401

ORIGIN = 'https://app.test'

LOGIN_METHODS = ('login_checkAvatar', 'login_setChecked', 'login_isChecked', 'login_doLogin',
                 'login_setSelectedRootenv', 'login_completeRootEnv', 'login_selectableGroups',
                 'login_require2fa', 'login_canSetWorkdate', 'login_deviceChecked', 'login_deviceRegistration',
                 'login_deviceOrigin', 'login_setDevice', 'login_popChallenge', 'login_deviceChallenge',
                 'login_deviceLogin', 'login_deviceRegister', 'login_newWindow', 'login_enforceWorkdate')


class _Key(object):
    def __init__(self):
        self.private = ec.generate_private_key(ec.SECP256R1())
        der = self.private.public_key().public_bytes(serialization.Encoding.DER,
                                                     serialization.PublicFormat.SubjectPublicKeyInfo)
        self.public_key = base64.b64encode(der).decode()
        self.key_id = base64.urlsafe_b64encode(hashlib.sha256(der).digest()).rstrip(b'=').decode()

    def sign(self, user, challenge, origin=ORIGIN):
        data = '\n'.join(('genroapp-device-v1', origin, user, challenge)).encode()
        return base64.b64encode(self.private.sign(data, ec.ECDSA(hashes.SHA256()))).decode()


class _DevicePage(_AppPage):
    request = types.SimpleNamespace(host_url=ORIGIN + '/')

    def setInClientData(self, *args, **kwargs):
        pass


def _page(application):
    return _bind(_DevicePage(application), *LOGIN_METHODS)


@pytest.fixture(scope='module')
def application(tmp_path_factory):
    app = _Application('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(tmp_path_factory.mktemp('login_device'), 'testing'),
    ))
    db = app.db
    db.model.check(applyChanges=True)
    db.table('adm.group').insert(dict(code='DVMAIN', description='Main'))
    for username in ('dv_alice', 'dv_bob', 'dv_admin'):
        db.table('adm.user').insert(dict(username=username, md5pwd='secret', status='conf',
                                         email=f'{username}@test.local', group_code='DVMAIN',
                                         avatar_secret_2fa=None))
    db.commit()
    return app


@pytest.fixture
def genroapp(application):
    """Set the adm GenroApp preferences; they are cleared after the test."""
    preference = application.db.table('adm.preference')

    def setter(**values):
        preference.setPreference('general.genroapp', Bag(values), pkg='adm')
    yield setter
    preference.setPreference('general.genroapp', Bag(), pkg='adm')


def _register(application, user, verification='biometry'):
    """A password login on a new page, then the registration of a new key."""
    page = _page(application)
    page.login_checkAvatar(user=user, password='secret')
    key = _Key()
    challenge = page.login_deviceChallenge()
    assert page.login_deviceRegister(key_id=key.key_id, public_key=key.public_key, alg='ES256',
                                      device_name='Mac di prova', platform='macos',
                                      verification=verification, signature=key.sign(user, challenge)) is True
    return key


def _device_login(application, key, user, origin=ORIGIN):
    page = _page(application)
    challenge = page.login_deviceChallenge()
    return page, page.login_deviceLogin(key_id=key.key_id, user=user, signature=key.sign(user, challenge, origin))


def _tags(page):
    return page.do_login_kwargs['rootenv']['user_local_tags']


def test_registration_stores_the_key(application):
    key = _register(application, 'dv_alice', 'user_presence')
    row = application.db.table('adm.user_device').query(
        columns='$alg,$verification,$device_name,@user_id.username AS username',
        where='$key_id=:k', k=key.key_id).fetch()[0]
    assert (row['alg'], row['verification'], row['device_name'], row['username']) == \
        ('ES256', 'user_presence', 'Mac di prova', 'dv_alice')


def test_registration_needs_a_checked_login(application):
    page = _page(application)
    key = _Key()
    challenge = page.login_deviceChallenge()
    assert page.login_deviceRegister(key_id=key.key_id, public_key=key.public_key, alg='ES256',
                                     verification='biometry', signature=key.sign('dv_alice', challenge)) is None


@pytest.mark.parametrize('field,value', [('alg', 'RS256'), ('verification', 'face'), ('key_id', 'forged')])
def test_registration_refuses_what_the_contract_does_not_allow(application, field, value):
    page = _page(application)
    page.login_checkAvatar(user='dv_alice', password='secret')
    key = _Key()
    challenge = page.login_deviceChallenge()
    kwargs = dict(key_id=key.key_id, public_key=key.public_key, alg='ES256', verification='biometry',
                  signature=key.sign('dv_alice', challenge))
    kwargs[field] = value
    assert page.login_deviceRegister(**kwargs) is None


def test_biometry_key_adds_device_and_biometric_tags(application, genroapp):
    key = _register(application, 'dv_alice', 'biometry')
    page, result = _device_login(application, key, 'dv_alice')
    assert result['user'] == 'dv_alice' and result['mode'] == 'password'
    page.login_checkAvatar(user='dv_alice', password='secret')
    page.login_doLogin(rootenv=Bag(), login=_login('dv_alice', 'DVMAIN'))
    assert _tags(page) == '_DEVICE_,_BIOMETRIC_'
    assert page.do_login_kwargs.get('authenticate') is None


def test_user_presence_key_adds_only_the_device_tag(application, genroapp):
    key = _register(application, 'dv_alice', 'user_presence')
    page, result = _device_login(application, key, 'dv_alice')
    page.login_checkAvatar(user='dv_alice', password='secret')
    page.login_doLogin(rootenv=Bag(), login=_login('dv_alice', 'DVMAIN'))
    assert _tags(page) == '_DEVICE_'


def test_password_login_has_no_device_tag(application, genroapp):
    page = _page(application)
    page.login_checkAvatar(user='dv_bob', password='secret')
    page.login_doLogin(rootenv=Bag(dict(user_local_tags='_DEVICE_')), login=_login('dv_bob', 'DVMAIN'))
    assert not _tags(page)


def test_signature_mode_logs_in_without_password(application, genroapp):
    genroapp(login_mode='signature')
    key = _register(application, 'dv_alice')
    page, result = _device_login(application, key, 'dv_alice')
    assert result['mode'] == 'signature'
    assert page.login_checkAvatar(user='dv_alice', password='')['avatar.user'] == 'dv_alice'
    page.login_doLogin(rootenv=Bag(), login=_login('dv_alice', 'DVMAIN'))
    assert page.do_login_kwargs['authenticate'] is False


def test_password_mode_still_asks_the_password(application, genroapp):
    key = _register(application, 'dv_alice')
    page, result = _device_login(application, key, 'dv_alice')
    assert not page.login_checkAvatar(user='dv_alice', password='')['avatar']


def test_the_signature_names_only_its_user(application, genroapp):
    genroapp(login_mode='signature')
    key = _register(application, 'dv_alice')
    page, result = _device_login(application, key, 'dv_alice')
    assert not page.login_checkAvatar(user='dv_bob', password='')['avatar']


@pytest.mark.parametrize('case', ['other_user', 'other_origin', 'revoked'])
def test_device_login_refused(application, case):
    key = _register(application, 'dv_alice')
    user, origin = 'dv_alice', ORIGIN
    if case == 'other_user':
        user = 'dv_bob'
    elif case == 'other_origin':
        origin = 'https://evil.test'
    else:
        tbl = application.db.table('adm.user_device')
        row = tbl.query(columns='$id,$user_id', where='$key_id=:k', k=key.key_id).fetch()[0]
        tbl.revokeDevice(row['id'], row['user_id'])
        application.db.commit()
    page, result = _device_login(application, key, user, origin)
    assert result is None
    assert page.login_deviceChecked(user) is None


def test_challenge_is_single_use(application):
    key = _register(application, 'dv_alice')
    page = _page(application)
    challenge = page.login_deviceChallenge()
    signature = key.sign('dv_alice', challenge)
    assert page.login_deviceLogin(key_id=key.key_id, user='dv_alice', signature=signature)
    assert page.login_deviceLogin(key_id=key.key_id, user='dv_alice', signature=signature) is None


def test_expired_challenge_is_refused(application):
    key = _register(application, 'dv_alice')
    page = _page(application)
    challenge = page.login_deviceChallenge()
    with page.pageStore() as ps:
        ps.setItem('login_device_challenge.expires', 0)
    assert page.login_deviceLogin(key_id=key.key_id, user='dv_alice',
                                  signature=key.sign('dv_alice', challenge)) is None


def test_revoke_of_another_user_device_is_refused(application):
    key = _register(application, 'dv_alice')
    db = application.db
    alice_device = db.table('adm.user_device').query(columns='$id', where='$key_id=:k', k=key.key_id).fetch()[0]
    bob_id = db.table('adm.user').readColumns(columns='$id', where='$username=:u', u='dv_bob')
    with pytest.raises(Exception, match='another user'):
        db.table('adm.user_device').revokeDevice(alice_device['id'], bob_id)


def test_policy_requires_registration_for_a_user_without_devices(application, genroapp):
    genroapp(required='all')
    page = _page(application)
    result = page.login_checkAvatar(user='dv_bob', password='secret')
    assert result['avatar.device_registration'] == 'required'
    assert page.login_doLogin(rootenv=Bag(), login=_login('dv_bob', 'DVMAIN')) == \
        {'error': '!![en]This user must log in with GenroApp'}


def test_policy_registration_then_login_goes_through(application, genroapp):
    genroapp(required='all')
    page = _page(application)
    page.login_checkAvatar(user='dv_admin', password='secret')
    key = _Key()
    challenge = page.login_deviceChallenge()
    assert page.login_deviceRegister(key_id=key.key_id, public_key=key.public_key, alg='ES256',
                                     verification='biometry', signature=key.sign('dv_admin', challenge))
    page.login_doLogin(rootenv=Bag(), login=_login('dv_admin', 'DVMAIN'))
    assert _tags(page) == '_DEVICE_,_BIOMETRIC_'


def test_policy_refuses_password_to_a_user_with_a_device(application, genroapp):
    _register(application, 'dv_alice')
    genroapp(required='all')
    result = _page(application).login_checkAvatar(user='dv_alice', password='secret')
    assert result['login_error_msg'] == '!![en]Log in with GenroApp from your registered computer'


def test_policy_without_required_tags_offers_registration(application, genroapp):
    genroapp(required='tags', required_tags='nobody_has_this')
    result = _page(application).login_checkAvatar(user='dv_bob', password='secret')
    assert result['avatar.device_registration'] == 'offer'


def test_new_window_keeps_the_connection_tags(application):
    page = _page(application)
    page.avatar = types.SimpleNamespace(as_dict=lambda: {}, user_tags='')
    page.connectionStore().setItem('defaultRootenv', Bag(dict(user_local_tags='_DEVICE_')))
    rootenv = Bag(dict(user_local_tags='_DEVICE_,_BIOMETRIC_,admin', workdate=None))
    page.login_newWindow(rootenv=rootenv)
    assert page.pageStore().getItem('rootenv.user_local_tags') == '_DEVICE_'
