"""Personal GenroApp site connectors: the ``<genroapp>`` tag, the request to the signing
service, the users that hold a connector, the device login and the revocation.

The HTTP call to the signing service is the only mocked part: ``FakeSigner`` stands for
``requests.post`` and answers what the signing service answers. The ``adm`` users, devices
and connectors live on a ``test_invoice`` sqlite database, as in ``test_login_device.py``.
"""
import base64
import hashlib
import json
import os
import types
from datetime import datetime, timedelta, timezone

import pytest
import requests

from gnr.web import gnrgenroapp

from test_login_checked_avatar import _Application
from test_login_checked_avatar import setup_module, teardown_module  # noqa: F401
from test_login_device import ORIGIN, _Key, _page

SIGNING_URL = 'https://signing.test/signing/genroapp/connectors/sign'
SITE_URL = ORIGIN + '/'
BODY = dict(name='Test site', url=SITE_URL, user='cn_alice', duration_days=30)
TAG = dict(name='Test site', signing_url=SIGNING_URL, signing_token='tag-token', duration_days='30')


class FakeSigner(object):
    """``requests.post`` of the signing service: it adds ``connector_id`` and ``expires``
    to the fields it receives and answers ``{payload, signature}``."""

    def __init__(self):
        self.calls = []
        self.status_code = 200
        self.error = None
        self.answer = None

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(dict(url=url, body=json, headers=headers))
        if self.error:
            raise self.error
        return types.SimpleNamespace(status_code=self.status_code,
                                     json=lambda: self.answer or self.signed(json))

    def signed(self, body):
        # one second apart: two connectors of one user never share the signing time
        signed_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=len(self.calls))
        digest = hashlib.sha256((body['url'] + body['user']).encode()).hexdigest()[:12]
        payload = dict(body, format='it.softwell.runner.link/v1',
                       connector_id=f'{digest}-{signed_at:%Y%m%dT%H%M%SZ}',
                       expires=(signed_at + timedelta(days=body['duration_days'])).strftime('%Y-%m-%dT%H:%M:%SZ'))
        del payload['duration_days']
        return dict(payload=base64.b64encode(json.dumps(payload).encode()).decode(),
                    signature=base64.b64encode(b'signature').decode())


def connector_payload(connector):
    return json.loads(base64.b64decode(connector['payload']))


@pytest.fixture
def signer(monkeypatch):
    fake = FakeSigner()
    monkeypatch.setattr(gnrgenroapp.requests, 'post', fake.post)
    return fake


@pytest.fixture(scope='module')
def application(tmp_path_factory):
    app = _Application('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(tmp_path_factory.mktemp('genroapp_connector'), 'testing'),
    ))
    db = app.db
    db.model.check(applyChanges=True)
    db.table('adm.group').insert(dict(code='CNMAIN', description='Main'))
    for username in ('cn_alice', 'cn_bob', 'cn_carl'):
        db.table('adm.user').insert(dict(username=username, md5pwd='secret', status='conf',
                                         email=f'{username}@test.local', group_code='CNMAIN',
                                         avatar_secret_2fa=None))
    db.commit()
    app.config.setItem('experimental.login', None, genroapp_device='true')
    return app


@pytest.fixture
def tag(application):
    """Write the ``<genroapp>`` tag of the instance; tag and connectors are removed after the test."""
    def setter(**attributes):
        application.config.popNode('genroapp')
        application.config.setItem('genroapp', None, **dict(TAG, **attributes))
        return gnrgenroapp.connector_config(application)
    yield setter
    application.config.popNode('genroapp')
    tbl = application.db.table('adm.user_connector')
    tbl.deleteSelection(where='$id IS NOT NULL')
    application.db.commit()


def _user_id(application, user):
    return application.db.table('adm.user').readColumns(columns='$id', where='$username=:u', u=user)


def _connector(application, config, user):
    """The connector the site gives to ``user``, as the webtool asks it."""
    connector = application.db.table('adm.user_connector').newConnector(
        config, user_id=_user_id(application, user), user=user, url=SITE_URL)
    application.db.commit()
    return connector


def _revoke(application, connector_id, user_tags='admin'):
    tbl = application.db.table('adm.user_connector')
    pkey = tbl.readColumns(columns='$id', where='$connector_id=:c', c=connector_id)
    with application.db.tempEnv(userTags=user_tags):
        tbl.revokeConnector(pkey=pkey)


def _register(application, user, connector_id=None):
    """A password login on a new page, then the registration of a new key."""
    page = _page(application)
    page.login_checkAvatar(user=user, password='secret')
    key = _Key()
    challenge = page.login_deviceChallenge()
    registered = page.login_deviceRegister(key_id=key.key_id, public_key=key.public_key, alg='ES256',
                                           device_name='Mac di prova', platform='macos',
                                           verification='biometry', signature=key.sign(user, challenge),
                                           connector_id=connector_id)
    return key, registered


def _device_login(application, key, user, connector_id=None):
    page = _page(application)
    challenge = page.login_deviceChallenge()
    return page.login_deviceLogin(key_id=key.key_id, user=user, signature=key.sign(user, challenge),
                                  connector_id=connector_id)


def _expire(application, connector_id):
    with application.db.table('adm.user_connector').recordToUpdate(where='$connector_id=:c', c=connector_id) as record:
        record['expires'] = datetime.now(timezone.utc) - timedelta(days=1)
    application.db.commit()


def _device_connector(application, key):
    return application.db.table('adm.user_device').readColumns(columns='$connector_id',
                                                               where='$key_id=:k', k=key.key_id)


# ---------------------------------------------------------------- the <genroapp> tag

def test_an_instance_without_the_tag_has_no_connector_data(application):
    assert gnrgenroapp.connector_config(application) is None


def test_the_tag_exposes_its_values(tag):
    config = tag(capabilities='signature, printers', lock_minutes_max='30', max_users='10')
    assert config == dict(name='Test site', signing_url=SIGNING_URL, signing_token='tag-token',
                          duration_days=30, capabilities=['signature', 'printers'],
                          lock_minutes_max=30, max_users=10)


def test_the_optional_attributes_may_be_missing(tag):
    config = tag(signing_token=None)
    assert (config['signing_token'], config['capabilities'], config['lock_minutes_max'], config['max_users']) == \
        (None, [], None, None)


@pytest.mark.parametrize('name', ['name', 'signing_url', 'duration_days'])
def test_a_tag_without_a_mandatory_attribute_is_an_error(tag, name):
    with pytest.raises(ValueError, match=name):
        tag(**{name: None})


# ---------------------------------------------------------------- the request to the signing service

def test_the_site_sends_the_tag_the_url_and_the_user(application, tag, signer):
    config = tag(capabilities='signature,printers', lock_minutes_max='30')
    _connector(application, config, 'cn_alice')
    call = signer.calls[0]
    assert call['url'] == SIGNING_URL
    assert call['headers'] == {'Authorization': 'Bearer tag-token'}
    assert call['body'] == dict(name='Test site', url=SITE_URL, user='cn_alice', duration_days=30,
                                capabilities=['signature', 'printers'], lock_minutes_max=30)


def test_the_optional_fields_are_not_sent_when_the_tag_has_none(application, tag, signer):
    _connector(application, tag(), 'cn_alice')
    assert signer.calls[0]['body'] == dict(name='Test site', url=SITE_URL, user='cn_alice', duration_days=30)


def test_the_site_returns_the_signed_connector_and_records_it(application, tag, signer):
    connector = _connector(application, tag(), 'cn_alice')
    assert set(connector) == {'payload', 'signature'}
    payload = connector_payload(connector)
    row = application.db.table('adm.user_connector').query(
        columns='$connector_id,$expires,$revoked,@user_id.username AS username').fetch()[0]
    assert (row['username'], row['connector_id'], row['revoked']) == ('cn_alice', payload['connector_id'], None)
    assert row['expires'].strftime('%Y-%m-%dT%H:%M:%SZ') == payload['expires']


def test_without_a_token_in_the_tag_the_keycloak_package_gives_it(application, tag, signer):
    """genropy does not import the package ``keycloak``: it uses the one of the instance."""
    application.packages.setItem('keycloak', types.SimpleNamespace(getToken=lambda: 'keycloak-token'))
    try:
        _connector(application, tag(signing_token=None), 'cn_alice')
    finally:
        application.packages.popNode('keycloak')
    assert signer.calls[0]['headers'] == {'Authorization': 'Bearer keycloak-token'}


def test_the_token_of_the_tag_wins_over_the_keycloak_package(application, tag, signer):
    application.packages.setItem('keycloak', types.SimpleNamespace(getToken=lambda: 'keycloak-token'))
    try:
        _connector(application, tag(), 'cn_alice')
    finally:
        application.packages.popNode('keycloak')
    assert signer.calls[0]['headers'] == {'Authorization': 'Bearer tag-token'}


def test_no_token_and_no_keycloak_package_is_an_error(application, tag, signer):
    with pytest.raises(ValueError, match='signing_token'):
        _connector(application, tag(signing_token=None), 'cn_alice')
    assert not signer.calls


@pytest.mark.parametrize('case', ['status', 'network', 'not_a_connector', 'no_connector_id',
                                  'empty_signature', 'no_signature_text'])
def test_a_failed_signature_gives_no_connector_and_no_record(application, tag, signer, case):
    if case == 'status':
        signer.status_code = 401
    elif case == 'network':
        signer.error = requests.ConnectionError('refused')
    elif case == 'not_a_connector':
        signer.answer = dict(error='no')
    elif case == 'empty_signature':
        signer.answer = dict(signer.signed(BODY), signature='')
    elif case == 'no_signature_text':
        signer.answer = dict(signer.signed(BODY), signature=None)
    else:
        signer.answer = dict(payload=base64.b64encode(b'{"expires":"2027-01-01T00:00:00Z"}').decode(),
                             signature='c2ln')
    with pytest.raises(gnrgenroapp.ConnectorSigningError) as refusal:
        _connector(application, tag(), 'cn_alice')
    assert refusal.value.status == 502
    assert application.db.table('adm.user_connector').query().count() == 0


# ---------------------------------------------------------------- max_users

def test_a_new_user_over_max_users_is_refused_before_the_signature(application, tag, signer):
    config = tag(max_users='2')
    _connector(application, config, 'cn_alice')
    _connector(application, config, 'cn_bob')
    with pytest.raises(gnrgenroapp.ConnectorUsersExceeded) as refusal:
        _connector(application, config, 'cn_carl')
    assert refusal.value.status == 409
    assert len(signer.calls) == 2


def test_the_place_is_counted_under_a_table_lock(application, tag, signer, monkeypatch):
    """Two requests never count the same free place: the table is locked before the
    count and until the commit. sqlite has no table lock, so the order is what is checked."""
    tbl = application.db.table('adm.user_connector')
    steps = []
    monkeypatch.setattr(tbl, 'lock', lambda: steps.append('lock'))
    count = tbl.placeHolders
    monkeypatch.setattr(tbl, 'placeHolders', lambda: steps.append('count') or count())
    _connector(application, tag(max_users='1'), 'cn_alice')
    assert steps == ['lock', 'count']


def test_a_user_that_holds_a_place_renews_on_a_full_site(application, tag, signer):
    config = tag(max_users='1')
    first = connector_payload(_connector(application, config, 'cn_alice'))
    second = connector_payload(_connector(application, config, 'cn_alice'))
    assert first['connector_id'] != second['connector_id']
    assert application.db.table('adm.user_connector').query().count() == 2


def test_without_max_users_the_users_are_not_limited(application, tag, signer):
    config = tag()
    for user in ('cn_alice', 'cn_bob', 'cn_carl'):
        _connector(application, config, user)
    assert len(signer.calls) == 3


def test_a_revoked_user_frees_a_place(application, tag, signer):
    config = tag(max_users='1')
    connector_id = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    _revoke(application, connector_id)
    assert _connector(application, config, 'cn_bob')


def test_a_user_keeps_the_place_while_one_connector_is_not_revoked(application, tag, signer):
    config = tag(max_users='1')
    first = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    _connector(application, config, 'cn_alice')
    _revoke(application, first)
    with pytest.raises(gnrgenroapp.ConnectorUsersExceeded):
        _connector(application, config, 'cn_bob')


def test_an_expired_connector_frees_a_place(application, tag, signer):
    config = tag(max_users='1')
    connector_id = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    _expire(application, connector_id)
    assert _connector(application, config, 'cn_bob')


# ---------------------------------------------------------------- revocation

@pytest.mark.parametrize('user_tags', ['user', None])
def test_only_an_administrator_revokes(application, tag, signer, user_tags):
    connector_id = connector_payload(_connector(application, tag(), 'cn_alice'))['connector_id']
    with pytest.raises(Exception, match='administrator'):
        _revoke(application, connector_id, user_tags=user_tags)
    assert application.db.table('adm.user_connector').validConnector(connector_id=connector_id, user='cn_alice')


def test_the_administrator_revokes_one_connector_at_a_time(application, tag, signer):
    config = tag()
    first = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    second = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    _revoke(application, first)
    tbl = application.db.table('adm.user_connector')
    assert not tbl.validConnector(connector_id=first, user='cn_alice')
    assert tbl.validConnector(connector_id=second, user='cn_alice')


# ---------------------------------------------------------------- the device login

def test_the_device_login_stores_the_connector_id(application, tag, signer):
    connector_id = connector_payload(_connector(application, tag(), 'cn_alice'))['connector_id']
    key, registered = _register(application, 'cn_alice')
    assert registered is True and _device_connector(application, key) is None
    assert _device_login(application, key, 'cn_alice', connector_id=connector_id)['user'] == 'cn_alice'
    assert _device_connector(application, key) == connector_id


def test_the_registration_stores_the_connector_id(application, tag, signer):
    connector_id = connector_payload(_connector(application, tag(), 'cn_alice'))['connector_id']
    key, registered = _register(application, 'cn_alice', connector_id=connector_id)
    assert registered is True
    assert _device_connector(application, key) == connector_id


def test_a_login_without_connector_id_is_accepted_and_keeps_the_stored_one(application, tag, signer):
    """GenroApp releases that do not send ``connector_id`` keep logging in."""
    connector_id = connector_payload(_connector(application, tag(), 'cn_alice'))['connector_id']
    key, registered = _register(application, 'cn_alice', connector_id=connector_id)
    assert _device_login(application, key, 'cn_alice')['user'] == 'cn_alice'
    assert _device_connector(application, key) == connector_id


@pytest.mark.parametrize('case', ['revoked', 'expired'])
def test_a_login_without_connector_id_checks_the_stored_one(application, tag, signer, case):
    """A device that logged in with a connector stays refused once that connector is
    revoked or expired, also when GenroApp sends no ``connector_id``."""
    connector_id = connector_payload(_connector(application, tag(), 'cn_alice'))['connector_id']
    key, registered = _register(application, 'cn_alice', connector_id=connector_id)
    if case == 'revoked':
        _revoke(application, connector_id)
    else:
        _expire(application, connector_id)
    assert _device_login(application, key, 'cn_alice') is None


def test_a_new_connector_lets_a_refused_device_log_in_again(application, tag, signer):
    config = tag()
    first = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    key, registered = _register(application, 'cn_alice', connector_id=first)
    _revoke(application, first)
    second = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    assert _device_login(application, key, 'cn_alice', connector_id=second)['user'] == 'cn_alice'
    assert _device_connector(application, key) == second
    assert _device_login(application, key, 'cn_alice')['user'] == 'cn_alice'


@pytest.mark.parametrize('case', ['revoked', 'expired', 'unknown', 'other_user'])
def test_the_device_login_refuses_a_connector_that_is_not_valid(application, tag, signer, case):
    config = tag()
    key, registered = _register(application, 'cn_alice')
    connector_id = connector_payload(_connector(application, config, 'cn_alice'))['connector_id']
    if case == 'revoked':
        _revoke(application, connector_id)
    elif case == 'expired':
        _expire(application, connector_id)
    elif case == 'unknown':
        connector_id = '000000000000-20260101T000000Z'
    else:
        connector_id = connector_payload(_connector(application, config, 'cn_bob'))['connector_id']
    assert _device_login(application, key, 'cn_alice', connector_id=connector_id) is None
    assert _device_connector(application, key) is None


@pytest.mark.parametrize('case', ['revoked', 'expired'])
def test_the_registration_refuses_a_connector_that_is_not_valid(application, tag, signer, case):
    connector_id = connector_payload(_connector(application, tag(), 'cn_alice'))['connector_id']
    if case == 'revoked':
        _revoke(application, connector_id)
    else:
        _expire(application, connector_id)
    key, registered = _register(application, 'cn_alice', connector_id=connector_id)
    assert registered is None
    assert application.db.table('adm.user_device').query(where='$key_id=:k', k=key.key_id).count() == 0


# ---------------------------------------------------------------- GenroApp tickets

def test_a_ticket_logs_in_its_user_once(application):
    tbl = application.db.table('adm.genroapp_ticket')
    ticket = tbl.newTicket(_user_id(application, 'cn_alice'))
    application.db.commit()
    assert tbl.consume(ticket) == 'cn_alice'
    application.db.commit()
    assert tbl.consume(ticket) is None


def test_an_expired_or_unknown_ticket_is_refused(application):
    tbl = application.db.table('adm.genroapp_ticket')
    ticket = tbl.newTicket(_user_id(application, 'cn_alice'))
    application.db.commit()
    with tbl.recordToUpdate(where='$used IS NOT TRUE') as record:
        record['expires'] = datetime.now(timezone.utc) - timedelta(seconds=1)
    application.db.commit()
    assert tbl.consume(ticket) is None
    assert tbl.consume('unknown') is None
    assert tbl.consume('') is None
    assert tbl.consume('a' * 129) is None


def test_only_the_hash_of_a_ticket_is_stored(application):
    tbl = application.db.table('adm.genroapp_ticket')
    ticket = tbl.newTicket(_user_id(application, 'cn_alice'))
    application.db.commit()
    assert not tbl.query(where='$id=:t', t=ticket).count()
    assert tbl.query(where='$id=:h', h=hashlib.sha256(ticket.encode()).hexdigest()).count() == 1


def test_the_ticket_login_replaces_the_password_of_its_user_only(application, tag):
    tag()
    ticket = application.db.table('adm.genroapp_ticket').newTicket(_user_id(application, 'cn_bob'))
    application.db.commit()
    page = _page(application)
    assert page.login_ticketLogin(ticket=ticket)['user'] == 'cn_bob'
    assert page.login_checkAvatar(user='cn_bob', password=None)['avatar.user'] == 'cn_bob'
    assert not page.login_checkAvatar(user='cn_carl', password=None)['avatar']
    other = _page(application)
    assert not other.login_checkAvatar(user='cn_bob', password=None)['avatar']


def test_the_ticket_login_needs_the_genroapp_tag(application):
    application.config.popNode('genroapp')
    ticket = application.db.table('adm.genroapp_ticket').newTicket(_user_id(application, 'cn_bob'))
    application.db.commit()
    assert _page(application).login_ticketLogin(ticket=ticket) is None


def test_a_user_uses_genroapp_with_a_connector_or_a_device(application, tag, signer):
    config = tag()
    tbl = application.db.table('adm.user_connector')
    assert not tbl.usesGenroApp(_user_id(application, 'cn_carl'))
    _connector(application, config, 'cn_carl')
    assert tbl.usesGenroApp(_user_id(application, 'cn_carl'))
    assert not tbl.usesGenroApp(None)
