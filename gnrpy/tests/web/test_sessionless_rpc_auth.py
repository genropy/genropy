"""RPCs of a login-protected page need a session.

A request without a session gets a page_id from ``main`` (the login dialog):
on a page that requires tags for ``main`` every other RPC must be answered
expired, whatever tags the RPC itself declares. Public pages and page renders
(``method=None``, the mako and genshi plugins) keep their behaviour.

The websocket gets a handler under the same rule, and only for public methods.
"""
import types

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrdecorator import public_method, websocket_method
from gnr.web.gnrwebpage import AUTH_EXPIRED, AUTH_FORBIDDEN, AUTH_NOT_LOGGED, AUTH_OK, GnrWebPage


class _Application(object):
    checkResourcePermission = GnrApp.checkResourcePermission


class _Page(object):
    """The slice of a page _checkAuth reads, with the base pageAuthTags."""
    defaultAuthTags = ''
    pageAuthTags = GnrWebPage.pageAuthTags
    _checkAuth = GnrWebPage._checkAuth
    getWsMethod = GnrWebPage.getWsMethod

    @public_method
    def rpcMethod(self):
        pass

    @websocket_method
    def wsMethod(self):
        pass

    @public_method
    def login_checkAvatar(self):
        pass

    def plainMethod(self):
        pass

    def __init__(self, user=None, user_tags=None, **auth):
        self.connection = types.SimpleNamespace(loggedUser=user)
        self.application = _Application()
        self.userTags = user_tags
        for name, tags in auth.items():
            setattr(self, 'auth_%s' % name, tags)


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
