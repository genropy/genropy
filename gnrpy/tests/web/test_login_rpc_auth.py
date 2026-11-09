"""Login RPCs reach their handler without a session (#1589, #1591).

A page that requires tags for every RPC answers ``expired`` to a request
without a session, so its own login dialog could never log in. The RPCs that
authenticate by themselves declare it with ``@public_method(sessionless=True)``;
the other methods of the login component keep the page auth.
"""
import importlib.util
import pathlib

import pytest

LOGIN = (pathlib.Path(__file__).parents[3] / 'projects' / 'gnrcore'
         / 'packages' / 'adm' / 'resources' / 'login.py')


@pytest.fixture(scope='module')
def login_component():
    spec = importlib.util.spec_from_file_location('adm_login', LOGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LoginComponent


@pytest.mark.parametrize('name', [
    'login_checkAvatar', 'login_doLogin', 'login_checkOTPCode',
    'login_confirmUser', 'login_confirmNewPassword', 'login_changePassword',
    'login_createNewUser', 'login_checkNodupUsername', 'login_validateNewPassword',
])
def test_login_rpcs_are_sessionless(login_component, name):
    handler = getattr(login_component, name)
    assert handler.is_rpc and handler.sessionless


@pytest.mark.parametrize('name', ['login_newWindow', 'login_checkPwd'])
def test_other_login_rpcs_keep_page_auth(login_component, name):
    assert not getattr(getattr(login_component, name), 'sessionless', False)
