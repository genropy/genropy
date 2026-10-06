"""adm.api_token.validate_token on a real database (issue #1580).

A token may carry a user_id: validate_token then returns the user's
identity, and packages add their own keys through onApiTokenValidation.
"""

import pytest

from core.common import BaseGnrTest

from gnr.core.gnrlang import GnrException


SECRET_KEYS = ('pwd', 'md5pwd', 'avatar_secret_2fa', 'avatar_last_2fa_otp')


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _tag(db, code):
    tbl = db.table('adm.htag')
    rec = tbl.newrecord(code=code, description=code)
    tbl.insert(rec)
    return rec['id']


def _group(db, code):
    db.table('adm.group').insert(dict(code=code, description=code))
    return code


def _user(db, username, status='conf', group_code=None, tags=()):
    tbl = db.table('adm.user')
    rec = tbl.newrecord(username=username, email=f'{username}@test.local',
                        firstname='Api', lastname='Token', status=status,
                        group_code=group_code, md5pwd='secret',
                        avatar_secret_2fa='2fa', avatar_last_2fa_otp='otp')
    tbl.insert(rec)
    for tag_id in tags:
        db.table('adm.user_tag').insert(dict(user_id=rec['id'], tag_id=tag_id))
    return rec['id']


def _token(db, user_id=None, group_code=None, tags=()):
    tbl = db.table('adm.api_token')
    rec = tbl.newrecord(description='test token', user_id=user_id,
                        group_code=group_code)
    tbl.insert(rec)
    for tag_id in tags:
        db.table('adm.api_token_tag').insert(dict(api_token_id=rec['id'], tag_id=tag_id))
    token_value = tbl.activate_api_token(record_id=rec['id'])
    db.commit()
    return rec['id'], token_value


@pytest.fixture(scope='module')
def data(db_sqlite):
    db = db_sqlite
    d = dict(db=db)
    d['tag_user'] = _tag(db, 'ZZTKUSER')
    d['tag_token'] = _tag(db, 'ZZTKTOKEN')
    d['group_user'] = _group(db, 'ZZTKG1')
    d['group_token'] = _group(db, 'ZZTKG2')
    d['user_conf'] = _user(db, 'tk_conf', group_code=d['group_user'],
                           tags=[d['tag_user']])
    d['user_wait'] = _user(db, 'tk_wait', status='wait')
    db.commit()
    return d


def _validate(db, token_value):
    return db.table('adm.api_token').validate_token(token_value)


def test_token_without_user_returns_todays_dict(data):
    db = data['db']
    token_id, token_value = _token(db, group_code=data['group_token'],
                                   tags=[data['tag_token']])
    result = _validate(db, token_value)
    assert result == {'token_id': token_id, 'auth_tags': 'ZZTKTOKEN',
                      'group_code': data['group_token'],
                      'description': 'test token'}


def test_token_with_conf_user(data):
    db = data['db']
    token_id, token_value = _token(db, user_id=data['user_conf'])
    result = _validate(db, token_value)
    assert result['token_id'] == token_id
    assert result['user'] == 'tk_conf'
    assert result['user_id'] == data['user_conf']
    assert result['user_name']
    assert result['user_record']['username'] == 'tk_conf'


def test_token_with_non_conf_user_is_refused(data):
    db = data['db']
    _, token_value = _token(db, user_id=data['user_wait'])
    assert _validate(db, token_value) is None


def test_auth_tags_are_the_union(data):
    db = data['db']
    _, token_value = _token(db, user_id=data['user_conf'],
                            tags=[data['tag_token']])
    tags = set(_validate(db, token_value)['auth_tags'].split(','))
    assert {'ZZTKUSER', 'ZZTKTOKEN'} <= tags


def test_group_comes_from_the_user_not_the_token(data):
    db = data['db']
    _, token_value = _token(db, user_id=data['user_conf'],
                            group_code=data['group_token'])
    assert _validate(db, token_value)['group_code'] == data['group_user']


def test_secrets_are_not_in_the_result(data):
    db = data['db']
    _, token_value = _token(db, user_id=data['user_conf'])
    result = _validate(db, token_value)
    for key in SECRET_KEYS:
        assert key not in result
        assert key not in result['user_record']


def test_packages_add_prefixed_keys(data, monkeypatch):
    db = data['db']
    packages = db.application.packages
    monkeypatch.setattr(packages['sys'], 'onApiTokenValidation',
                        lambda token_info: {'appcode': 'X'}, raising=False)
    monkeypatch.setattr(packages['invc'], 'onApiTokenValidation',
                        lambda token_info: {'appcode': 'Y',
                                            'env_allowed': ['A', 'B']},
                        raising=False)
    _, token_value = _token(db, user_id=data['user_conf'])
    result = _validate(db, token_value)
    assert result['sys_appcode'] == 'X'
    assert result['invc_appcode'] == 'Y'
    assert result['invc_env_allowed'] == ['A', 'B']
    assert result['user'] == 'tk_conf'


def test_hook_receives_a_copy(data, monkeypatch):
    db = data['db']

    def hook(token_info):
        token_info['auth_tags'] = 'HACKED'
        return None

    monkeypatch.setattr(db.application.packages['sys'], 'onApiTokenValidation',
                        hook, raising=False)
    _, token_value = _token(db, user_id=data['user_conf'])
    assert _validate(db, token_value)['auth_tags'] != 'HACKED'


def test_unknown_user_is_refused(data):
    db = data['db']
    assert db.table('adm.api_token').userTokenInfo(
        {'auth_tags': ''}, 'tk_nobody') is None


def test_package_cannot_overwrite_existing_keys(data, monkeypatch):
    db = data['db']
    monkeypatch.setattr(db.application.packages['sys'], 'onApiTokenValidation',
                        lambda token_info: {'appcode': 'X'}, raising=False)
    token_info = {'token_id': 'T', 'sys_appcode': 'base'}
    with pytest.raises(GnrException):
        db.table('adm.api_token').packagesTokenInfo(token_info)
    assert token_info['sys_appcode'] == 'base'


def test_deleting_the_user_deletes_its_tokens(data):
    db = data['db']
    user_id = _user(db, 'tk_deleted')
    token_id, _ = _token(db, user_id=user_id)
    user_tbl = db.table('adm.user')
    user_tbl.delete(user_tbl.record(user_id).output('dict'))
    db.commit()
    assert not db.table('adm.api_token').existsRecord(token_id)
