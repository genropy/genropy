"""Login RPCs reach their handler without a session (#1589, #1591).

A page that requires tags for every RPC answers ``expired`` to a request
without a session, so its own login dialog could never log in. The RPCs that
authenticate by themselves are let through, and only when the method name
cannot resolve to anything else.
"""
import pytest

from gnr.web.gnrwebpage import isLoginRpc


@pytest.mark.parametrize('method', [
    '*|login:LoginComponent;login_checkAvatar',
    '*|login:LoginComponent;login_doLogin',
    '*|login:LoginComponent;login_checkOTPCode',
    'login_checkAvatar',
])
def test_login_rpcs_skip_page_auth(method):
    assert isLoginRpc(method)


@pytest.mark.parametrize('method', [
    None,
    '',
    'main',
    'app.getSelection',
    '*|login:LoginComponent;app.getSelection',
    '*|login:LoginComponent;login_confirmUser',
    '*|login:LoginComponent;login_createNewUser',
    '*|other:Component;login_checkAvatar',
    'login:LoginComponent;login_checkAvatar',
    'pkg|login:LoginComponent;login_checkAvatar',
])
def test_other_rpcs_keep_page_auth(method):
    assert not isLoginRpc(method)
