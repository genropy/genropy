"""RPCs of a login-protected page need a session.

A request without a session gets a page_id from ``main`` (the login dialog):
on a page that requires tags for ``main`` every other RPC must be answered
expired, whatever tags the RPC itself declares. Public pages and page renders
(``method=None``, the mako and genshi plugins) keep their behaviour.

The websocket gets a handler under the same rule, and only for public methods.
A refused call is served anyway when its method is declared sessionless, or,
before doLogin, when the login dialog has checked the avatar (no 2FA pending)
and a field of the dialog declared that call; the login page itself serves the
calls its struct declared, to anybody (see test_login_fields.py).
"""
import types

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method, websocket_method

from gnr.web.gnrwebpage import AUTH_EXPIRED, AUTH_FORBIDDEN, AUTH_NOT_LOGGED, AUTH_OK, GnrUserNotAllowed, GnrWebPage
from gnr.web.gnrwebpage import GnrVerifier
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
    _sessionlessHandler = GnrWebPage._sessionlessHandler
    getSessionlessMethod = GnrWebPage.getSessionlessMethod
    _verifiedHandler = GnrWebPage._verifiedHandler
    _loginRecorded = GnrWebPage._loginRecorded
    login_fieldSelect = GnrWebPage.login_fieldSelect
    login_fieldCount = GnrWebPage.login_fieldCount

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


class _AppProxy(object):
    def __init__(self):
        self.calls = []

    @public_method
    def dbSelect(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get('_id') == 'outside':
            return 'outside row', dict(errors='current value does not fit condition')
        return 'rows', {}

    @public_method
    def getRecordCount(self, field=None, value=None, **kwargs):
        self.calls.append(dict(field=field, value=value, **kwargs))
        return 1 if value == 'taken' else 0

    @public_method
    def getSelection(self, **kwargs):
        return 'all rows'


def _recorded(dbtable, field_id, method=None, count=None):
    return Bag(dict(methods=[method] if method else [],
                    dbselects=[dict(id=field_id, dbtable=dbtable,
                                    structure=dict(columns='$code', condition='$code=:c AND $u=:env_u'),
                                    params=['c', 'env_u'], pinned=dict(env_u='user_id'))],
                    counts=[count] if count else []))


class _FieldPage(_Page):
    """A protected login page: the dialog declared a dbSelect on adm.htag and a nodup on
    adm.user.username; its rootenvForm fields a dbSelect on adm.group and rpcMethod."""

    def __init__(self, store=None, **kwargs):
        store = dict(login_page_rpcs=_recorded('adm.htag', 'p0', count='adm.user.username'),
                     login_field_rpcs=_recorded('adm.group', 'f0', method='rpcMethod'), **(store or {}))
        super().__init__(main='user', store=store, **kwargs)
        self.app = _AppProxy()

    def _getProxyObject(self, method):
        proxy, submethod = method.split('.')
        return getattr(self, proxy), submethod


CHECKED = dict(login_checked={'user': 'someone'})


def test_websocket_refusal_names_its_error():
    assert _Page(main='user').resolveWsMethod('rpcMethod') == (None, 'expired')
    page = _Page(user='someone', user_tags='other', main='user', rpcMethod='admin')
    assert page.resolveWsMethod('rpcMethod') == (None, 'forbidden call')
    assert _Page().resolveWsMethod('missingMethod') == (None, 'missing handler: missingMethod')


def test_websocket_does_not_fall_back_to_the_rpc_prefix():
    assert _Page().resolveWsMethod('legacy') == (None, 'missing handler: legacy')


def test_sessionless_method_is_served_on_a_guarded_page():
    page = _GuardedPage()
    assert page.getWsMethod('login_checkAvatar') == page.login_checkAvatar
    assert page.getSessionlessMethod('login_checkAvatar') == page.login_checkAvatar


def test_app_rpcs_are_never_opened_by_the_login_page():
    page = _FieldPage(store=CHECKED)
    for method in ('app.dbSelect', 'app.getRecordCount', 'app.getSelection'):
        assert page.getSessionlessMethod(method) is None
        assert page.resolveWsMethod(method) == (None, 'expired')


def test_login_page_dbselect_is_served_to_anybody_with_its_own_structure():
    page = _FieldPage()
    sent = dict(dbtable='adm.htag', login_field='p0', columns='$md5pwd', condition='$code IS NOT NULL',
                ignorePartition=True, _storename='other', c='G1', _querystring='g')
    assert page.getSessionlessMethod('login_fieldSelect')(**sent) == ('rows', {})
    assert page.app.calls == [dict(dbtable='adm.htag', columns='$code', condition='$code=:c AND $u=:env_u',
                                   c='G1', _querystring='g')]


def test_rootenvform_dbselect_waits_for_the_avatar_check():
    sent = dict(dbtable='adm.group', login_field='f0', c='G1')
    page = _FieldPage()
    assert page.login_fieldSelect(**sent) == Bag()
    assert page.app.calls == []
    page = _FieldPage(store=dict(CHECKED, login_checked_rootenv=Bag(dict(user_id='U1'))))
    assert page.login_fieldSelect(env_u='OTHER', **sent) == ('rows', {})
    assert page.app.calls[-1]['env_u'] == 'U1'
    page = _FieldPage(store=dict(CHECKED, waiting2fa='user_id'))
    assert page.login_fieldSelect(**sent) == Bag()


def test_undeclared_table_gets_no_rows():
    page = _FieldPage(store=CHECKED)
    assert page.login_fieldSelect(dbtable='adm.user', login_field='f0', _querystring='*') == Bag()
    assert page.login_fieldSelect(dbtable='adm.group', _querystring='*') == Bag()
    assert page.app.calls == []


def test_a_key_outside_the_condition_gives_no_row():
    page = _FieldPage()
    assert page.login_fieldSelect(dbtable='adm.htag', login_field='p0', _id='outside') == (Bag(), {})
    assert page.login_fieldSelect(dbtable='adm.htag', login_field='p0', _id='inside') == ('rows', {})


class _RefusingVerifier(GnrVerifier):
    def verify(self, **kwargs):
        return GnrUserNotAllowed(method='refused')


def test_websocket_applies_the_verifiers_of_a_served_method():
    page = _FieldPage(store=CHECKED)
    _Page.rpcMethod.verifier = _RefusingVerifier
    try:
        with pytest.raises(GnrUserNotAllowed):
            page.resolveWsMethod('rpcMethod')
    finally:
        del _Page.rpcMethod.verifier
    _Page.rpcMethod.signed = True
    try:
        assert page.resolveWsMethod('rpcMethod') == (None, 'expired')
    finally:
        del _Page.rpcMethod.signed


def test_field_count_checks_only_the_declared_field():
    page = _FieldPage()
    assert page.login_fieldCount(value='taken', login_field='adm.user.username', login_check='nodup') \
        == Bag(dict(errorcode='duplicated_value'))
    assert page.login_fieldCount(value='free', login_field='adm.user.username', login_check='nodup') is True
    assert page.login_fieldCount(value='taken', login_field='adm.user.username', login_check='exist') is True
    assert page.login_fieldCount(value='free', login_field='adm.user.username', login_check='exist') \
        == Bag(dict(errorcode='missing'))
    assert page.login_fieldCount(value='x', login_field='adm.user.md5pwd') == Bag(dict(errorcode='not_allowed'))
    assert [c['field'] for c in page.app.calls] == ['adm.user.username'] * 4


def test_checked_avatar_serves_a_declared_method():
    page = _FieldPage(store=CHECKED)
    assert page.getSessionlessMethod('rpcMethod') == page.rpcMethod
    assert page.getWsMethod('rpcMethod') == page.rpcMethod


def test_checked_avatar_refuses_what_no_field_declared():
    page = _FieldPage(store=CHECKED)
    assert page.getSessionlessMethod('wsMethod') is None
    assert page.resolveWsMethod('plainMethod') == (None, 'expired')


def test_checked_avatar_waiting_for_2fa_is_expired():
    page = _FieldPage(store=dict(CHECKED, waiting2fa='user_id'))
    assert page.getSessionlessMethod('rpcMethod') is None
    assert page.resolveWsMethod('rpcMethod') == (None, 'expired')


def test_declared_method_keeps_its_tags():
    page = _FieldPage(store=CHECKED)
    _Page.rpcMethod.tags = 'admin'
    try:
        with pytest.raises(GnrUserNotAllowed):
            page.resolveWsMethod('rpcMethod')
    finally:
        del _Page.rpcMethod.tags


def test_checked_avatar_does_not_lift_a_forbidden_logged_user():
    page = _FieldPage(store=CHECKED, user='someone', user_tags='other', rpcMethod='admin')
    assert page.getSessionlessMethod('rpcMethod') is None


@pytest.mark.parametrize('method', [
    'app.getSelection',
    '*|login:LoginComponent;app.getSelection',
    '*|login:LoginComponent;login_newWindow',
    '*|login:LoginComponent;login_checkPwd',
    '*|other:Component;login_checkAvatar',
    'login:LoginComponent;login_checkAvatar',
    'pkg|login:LoginComponent;login_checkAvatar',
    'rpcMethod',
    'plainMethod',
])
def test_what_the_security_fix_refused_stays_refused(method):
    page = _FieldPage(store=dict(mixin_set=[(('login:LoginComponent',), ())]))
    page.mixinComponent = lambda *path, **kwargs: None
    page._mixinRequestedComponent = types.MethodType(GnrWebPage._mixinRequestedComponent, page)
    page._mixedByPage = types.MethodType(GnrWebPage._mixedByPage, page)
    assert _check(page, method) == AUTH_EXPIRED
    assert page.getSessionlessMethod(method) is None


def test_without_a_checked_avatar_a_declared_call_stays_expired():
    assert _FieldPage().getSessionlessMethod('rpcMethod') is None


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
