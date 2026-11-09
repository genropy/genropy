"""RPCs of a login-protected page need a session.

A request without a session gets a page_id from ``main`` (the login dialog):
on a page that requires tags for ``main`` every other RPC must be answered
expired, whatever tags the RPC itself declares. Public pages and page renders
(``method=None``, the mako and genshi plugins) keep their behaviour.

The websocket gets a handler under the same rule, and only for public methods.
A refused call is served anyway when its method is declared sessionless, or,
before doLogin, when the login dialog has checked the avatar (no 2FA pending)
and the method has no tags of its own: the rootenvForm fields call them.
"""
import types

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrdecorator import public_method, websocket_method

from gnr.web.gnrwebpage import AUTH_EXPIRED, AUTH_FORBIDDEN, AUTH_NOT_LOGGED, AUTH_OK, GnrUserNotAllowed, GnrWebPage
from gnr.web.gnrwebpage_proxy.rpc import GnrWebRpc


class _Application(object):
    checkResourcePermission = GnrApp.checkResourcePermission


class _Page(object):
    """The slice of a page _checkAuth reads, with the base pageAuthTags."""
    defaultAuthTags = ''
    pageAuthTags = GnrWebPage.pageAuthTags
    _checkAuth = GnrWebPage._checkAuth
    getWsMethod = GnrWebPage.getWsMethod
    resolveWsMethod = GnrWebPage.resolveWsMethod
    _resolvePublicMethod = GnrWebPage._resolvePublicMethod
    _servedWithoutAuth = GnrWebPage._servedWithoutAuth
    getSessionlessMethod = GnrWebPage.getSessionlessMethod
    _verifiedHandler = GnrWebPage._verifiedHandler

    @public_method
    def rpcMethod(self):
        pass

    @websocket_method
    def wsMethod(self):
        pass

    @public_method(sessionless=True)
    def login_checkAvatar(self):
        pass

    @public_method(tags='admin')
    def taggedMethod(self):
        pass

    def plainMethod(self):
        pass

    def rpc_legacy(self):
        pass

    def __init__(self, user=None, user_tags=None, store=None, **auth):
        self.connection = types.SimpleNamespace(loggedUser=user)
        self._store = dict(store or {})
        self.application = _Application()
        self.userTags = user_tags
        for name, tags in auth.items():
            setattr(self, 'auth_%s' % name, tags)

    def pageStore(self):
        return types.SimpleNamespace(getItem=self._store.get)

    def exception(self, exception, **kwargs):
        return exception(**kwargs)


class _GuardedPage(_Page):
    """A page whose pageAuthTags requires its tags for every method."""

    def pageAuthTags(self, method=None, **kwargs):
        return 'user'


def _check(page, method):
    return GnrWebPage._checkAuth(page, method=method)


def test_protected_page_rpc_without_session_is_expired():
    page = _Page(main='user')
    assert _check(page, 'app.getSelection') == AUTH_EXPIRED
    assert _check(page, '*|any:Component;anyMethod') == AUTH_EXPIRED


def test_protected_page_main_without_session_asks_for_login():
    assert _check(_Page(main='user'), 'main') == AUTH_NOT_LOGGED


def test_page_render_check_is_unchanged():
    assert _check(_Page(main='user'), None) == AUTH_OK


def test_public_page_rpc_without_session_is_served():
    assert _check(_Page(), 'app.getSelection') == AUTH_OK


def test_guarded_page_rpc_without_session_is_expired():
    assert _check(_GuardedPage(), 'app.getSelection') == AUTH_EXPIRED


def test_logged_user_is_unchanged():
    assert _check(_Page(user='someone', user_tags='user', main='user'), 'app.getSelection') == AUTH_OK
    page = _Page(user='someone', user_tags='user', main='user', custom='admin')
    assert _check(page, 'custom') == AUTH_FORBIDDEN


def test_websocket_without_session_on_protected_page_gets_no_handler():
    page = _Page(main='user')
    assert page.getWsMethod('rpcMethod') is None
    assert page.getWsMethod('wsMethod') is None


def test_websocket_login_rpc_without_session_is_served():
    page = _Page(main='user')
    assert page.getWsMethod('login_checkAvatar') == page.login_checkAvatar


def test_websocket_without_session_on_public_page_is_served():
    page = _Page()
    assert page.getWsMethod('rpcMethod') == page.rpcMethod


def test_websocket_serves_only_public_methods():
    page = _Page(user='someone', user_tags='user', main='user')
    assert page.getWsMethod('rpcMethod') == page.rpcMethod
    assert page.getWsMethod('wsMethod') == page.wsMethod
    assert page.getWsMethod('plainMethod') is None
    assert page.getWsMethod('missingMethod') is None


CHECKED = dict(login_checked={'user': 'someone'})


def test_websocket_refusal_names_its_error():
    assert _Page(main='user').resolveWsMethod('rpcMethod') == (None, 'expired')
    page = _Page(user='someone', user_tags='other', main='user', rpcMethod='admin')
    assert page.resolveWsMethod('rpcMethod') == (None, 'forbidden call')
    assert _Page().resolveWsMethod('missingMethod') == (None, 'missing handler: missingMethod')


def test_websocket_falls_back_to_the_rpc_prefix_as_http():
    page = _Page()
    assert page.getWsMethod('legacy') == page.rpc_legacy


def test_sessionless_method_is_served_on_a_guarded_page():
    page = _GuardedPage()
    assert page.getWsMethod('login_checkAvatar') == page.login_checkAvatar
    assert page.getSessionlessMethod('login_checkAvatar') == page.login_checkAvatar


def test_checked_avatar_serves_untagged_rpcs_before_login():
    page = _Page(main='user', store=CHECKED)
    assert page.getSessionlessMethod('rpcMethod') == page.rpcMethod
    assert page.getWsMethod('rpcMethod') == page.rpcMethod


def test_checked_avatar_waiting_for_2fa_is_expired():
    page = _Page(main='user', store=dict(CHECKED, waiting2fa='user_id'))
    assert page.getSessionlessMethod('rpcMethod') is None
    assert page.resolveWsMethod('rpcMethod') == (None, 'expired')


def test_checked_avatar_does_not_open_methods_with_page_tags():
    page = _Page(main='user', store=CHECKED, rpcMethod='admin')
    assert page.getSessionlessMethod('rpcMethod') is None


def test_checked_avatar_does_not_open_tagged_handlers():
    page = _Page(main='user', store=CHECKED)
    with pytest.raises(GnrUserNotAllowed):
        page.resolveWsMethod('taggedMethod')


def test_checked_avatar_does_not_lift_a_forbidden_logged_user():
    page = _Page(user='someone', user_tags='other', main='user', store=CHECKED)
    assert page.getSessionlessMethod('rpcMethod') is None


def test_without_a_checked_avatar_the_rpc_stays_expired():
    assert _Page(main='user').getSessionlessMethod('rpcMethod') is None


class _RpcPage(object):
    def __init__(self, sessionless=None, public=None):
        self.sessionless = sessionless
        self.public = public

    def getSessionlessMethod(self, method):
        return self.sessionless

    def getPublicMethod(self, prefix, method):
        return self.public


def _rpc_call(page, auth, method='anyMethod'):
    rpc = GnrWebRpc.__new__(GnrWebRpc)
    rpc.page = page
    result = rpc(method=method, _auth=auth)
    return result, getattr(rpc, 'error', None)


def test_http_rpc_refused_without_a_sessionless_handler():
    assert _rpc_call(_RpcPage(), AUTH_EXPIRED) == (None, 'expired')
    assert _rpc_call(_RpcPage(), AUTH_FORBIDDEN) == (None, 'forbidden call')


def test_http_rpc_serves_the_sessionless_handler():
    page = _RpcPage(sessionless=lambda: 'served')
    assert _rpc_call(page, AUTH_EXPIRED) == ('served', None)
    assert _rpc_call(page, AUTH_FORBIDDEN) == ('served', None)


def test_http_rpc_authorized_call_is_unchanged():
    assert _rpc_call(_RpcPage(public=lambda: 'ok'), AUTH_OK) == ('ok', None)
    assert _rpc_call(_RpcPage(), AUTH_OK) == (None, 'missing handler: anyMethod')
