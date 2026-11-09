"""Tests for ``SiteRegister.set_serverstore_changes`` on a page the register lost (#1231).

``get_item_data`` returns a detached ``Bag()`` on a cache miss, so writing the client's
``_serverstore_changes`` into it used to drop them with no error. The client has already
nulled its own buffer by then (``genro_rpc.js:306-308``), so the changes are
unrecoverable at the moment the server notices: the only available answer is to report.

The call answers a boolean and does not log, the convention #1253 sets for its sibling
``set_datachange``: whether a missing page is exceptional is the caller's to know. Two of
the three callers reach it after a check that the page existed, so absence there is the
cleanup race and worth a line; the third is the children loop of ``handle_ping``, whose
ids come from the browser's own walk over ``window.frames`` with no check at all, and
whose absence repeats on every ping carrying changes for a dead child.

Both client-addressed routes -- the ``pageId`` of ``rpc_setInServer`` and the children
ids of ``handle_ping`` -- reach only pages of the sender's own connection (#1837): its
iframes and its parent share the connection cookie, so no legitimate client crosses it.
The same holds for the page a ping runs for: ``serve_ping`` hands ``handle_ping`` the
connection of the request's cookie, and a page outside it gets the answer of a page
that no longer exists.

The register is a real ``SiteRegister`` built with a stand-in server -- its constructor
only needs ``server.daemon.register`` -- as in ``subscribed_tables_index_test.py``.
"""

import logging
import types

import pytest
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from gnr.web.daemon.siteregister import SiteRegister
from gnr.web.daemon.siteregister_client import ServerStore
from gnr.web.gnrcookie import MarshalCookie
from gnr.web.gnrwebpage import GnrWebPage
from gnr.web.gnrwsgisite import GnrWsgiSite


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


def test_serverstore_changes_for_an_unknown_page_answer_false(caplog):
    sr = SiteRegister(_FakeServer(), sitename='testsite')
    with caplog.at_level(logging.WARNING):
        assert sr.set_serverstore_changes('ghost', {'rootenv.language': 'en'}) is False
    assert not caplog.records, 'the callee does not know whether absence is exceptional'


def test_serverstore_changes_for_a_known_page_are_stored(caplog):
    sr = SiteRegister(_FakeServer(), sitename='testsite')
    sr.page_register.create('p1')
    sr.page_register.subscribe_path('p1', 'rootenv.language')
    with caplog.at_level(logging.WARNING):
        assert sr.set_serverstore_changes('p1', {'rootenv.language': 'en'}) is True
    assert sr.page_register.get_item_data('p1')['rootenv.language'] == 'en'
    assert not caplog.records


def test_asking_about_a_ghost_leaves_no_timestamp_behind():
    """``get_item`` calls ``updateTS`` before testing whether the item is there, and
    ``itemsTS`` is only popped in ``drop_item``, which never runs for an id that was
    never registered -- and it is pickled into the freeze. The children loop is where
    ghost ids come from, so the guard has to be ``exists``."""
    sr = SiteRegister(_FakeServer(), sitename='testsite')
    sr.set_serverstore_changes('ghost', {'rootenv.language': 'en'})
    assert 'ghost' not in sr.page_register.itemsTS
    assert 'ghost' not in sr.page_register.itemsData


def _page_register():
    sr = SiteRegister(_FakeServer(), sitename='testsite')
    sr.page_register.create('p1')
    for serverpath in ('rootenv.language', 'rootenv.workdate', 'rootenv.context_subtables',
                       'rootenv.current_sede_id'):
        sr.page_register.subscribe_path('p1', serverpath)
    data = sr.page_register.get_item_data('p1')
    data.setItem('waiting2fa', 'user_id')
    data.setItem('confirm_user_id', 'user_id')
    data.setItem('rootenv.user_local_tags', 'base')
    return sr, data


def test_client_changes_reach_the_paths_the_page_syncs():
    sr, data = _page_register()
    synced = {'rootenv.language': 'en', 'rootenv.workdate': '2026-01-01', 'rootenv.context_subtables': 'x',
              'rootenv.current_sede_id': 'S1', 'vb_filter.year': '2026', 'dbenv.fine_mese': '1'}
    assert sr.set_serverstore_changes('p1', synced) is True
    for path, value in synced.items():
        assert data[path] == value


def test_client_changes_never_reach_server_only_paths(caplog):
    sr, data = _page_register()
    forged = {'waiting2fa': '', 'last_2fa_otp': '1', 'confirm_user_id': 'victim',
              'confirm_user_id?x': '1', 'mixin_set': 'x', 'login_checked.user': 'victim',
              'login_page_rpcs': 'x', 'rootenv.user_local_tags': 'admin', 'rootenv': 'x', '': 'x',
              'rootenv.allowed_sede_id': 'x', 'rootenv.accesso_globale': True, 'rootenv.user_id': 'x',
              'rootenv.current_operatore_id': 'other',
              'vb_filter?dbenv': 'allowed_sede_id', 'rootenv.language': 'it'}
    with caplog.at_level(logging.WARNING):
        assert sr.set_serverstore_changes('p1', forged) is True
    assert data['waiting2fa'] == 'user_id'
    assert data['confirm_user_id'] == 'user_id'
    assert data['last_2fa_otp'] is None
    assert data['mixin_set'] is None
    assert data['login_checked'] is None
    assert data['login_page_rpcs'] is None
    assert data['rootenv.user_local_tags'] == 'base'
    assert data['rootenv.allowed_sede_id'] is None
    assert data['rootenv.accesso_globale'] is None
    assert data['rootenv.current_operatore_id'] is None
    assert data.getNode('vb_filter') is None
    assert data['rootenv.language'] == 'it'
    assert len(caplog.records) == len(forged) - 1


class _InProcessRegister(SiteRegister):
    """The register with the client's ``pageStore``, without the Pyro hop."""

    def pageStore(self, page_id, triggered=False):
        return ServerStore(self, 'page', page_id, triggered=triggered)


class _Page:
    page_id = 'p1'
    sourcepage_id = None
    pageStore = GnrWebPage.pageStore
    rpc_setInServer = GnrWebPage.rpc_setInServer

    def __init__(self, register):
        self.site = types.SimpleNamespace(register=register)


def test_set_in_server_never_reaches_server_only_paths(caplog):
    sr = _InProcessRegister(_FakeServer(), sitename='testsite')
    sr.page_register.create('p1')
    data = sr.page_register.get_item_data('p1')
    data.setItem('waiting2fa', 'user_id')
    data.setItem('rootenv.user_local_tags', 'base')
    page = _Page(sr)
    with caplog.at_level(logging.WARNING):
        page.rpc_setInServer('waiting2fa', value='')
        page.rpc_setInServer('confirm_user_id', value='victim', pageId='p1')
        page.rpc_setInServer('rootenv.user_local_tags', value='admin')
        page.rpc_setInServer('thermo_t1_stop', value=True)
    assert data['waiting2fa'] == 'user_id'
    assert data['confirm_user_id'] is None
    assert data['rootenv.user_local_tags'] == 'base'
    assert data['thermo_t1_stop'] is True
    assert len(caplog.records) == 3


def _two_connections():
    """p1 and its iframe f1 in anna's connection, v1 in bruno's."""
    sr = _InProcessRegister(_FakeServer(), sitename='testsite')
    sr.new_connection('conn-a', user='anna')
    sr.new_connection('conn-b', user='bruno')
    for page_id, connection_id, user in (('p1', 'conn-a', 'anna'), ('f1', 'conn-a', 'anna'),
                                         ('v1', 'conn-b', 'bruno')):
        sr.new_page(page_id, connection_id=connection_id, user=user)
    return sr


def test_set_in_server_reaches_a_page_of_the_same_connection(caplog):
    sr = _two_connections()
    with caplog.at_level(logging.WARNING):
        _Page(sr).rpc_setInServer('vb_filter.year', value='2026', pageId='f1')
    assert sr.page_register.get_item_data('f1')['vb_filter.year'] == '2026'
    assert not caplog.records


def test_set_in_server_from_an_iframe_reaches_its_source_page():
    sr = _two_connections()
    page = _Page(sr)
    page.page_id, page.sourcepage_id = 'f1', 'p1'
    page.rpc_setInServer('vb_filter.year', value='2026')
    assert sr.page_register.get_item_data('p1')['vb_filter.year'] == '2026'


def test_set_in_server_never_reaches_a_page_of_another_connection(caplog):
    sr = _two_connections()
    with caplog.at_level(logging.WARNING):
        _Page(sr).rpc_setInServer('vb_filter.year', value='2026', pageId='v1')
    assert sr.page_register.get_item_data('v1')['vb_filter.year'] is None
    assert len(caplog.records) == 1


def test_ping_children_reach_pages_of_the_same_connection(caplog):
    sr = _two_connections()
    with caplog.at_level(logging.WARNING):
        sr.handle_ping(page_id='p1', connection_id='conn-a',
                       _children_pages_info={'f1': {'vb_filter.year': '2026'}})
    assert sr.page_register.get_item_data('f1')['vb_filter.year'] == '2026'
    assert sr.page_register.registerItems['f1']['last_refresh_ts'] is not None
    assert not caplog.records


def test_ping_children_never_reach_pages_of_another_connection(caplog):
    sr = _two_connections()
    with caplog.at_level(logging.WARNING):
        sr.handle_ping(page_id='p1', connection_id='conn-a',
                       _children_pages_info={'v1': {'vb_filter.year': '2026'}})
    assert sr.page_register.get_item_data('v1')['vb_filter.year'] is None
    assert sr.page_register.registerItems['v1'].get('last_refresh_ts') is None
    assert len(caplog.records) == 1


def _pending(sr, page_id):
    sr.page_register.set_datachange(page_id, 'gnr.news', value=page_id)
    return sr.page_register.registerItems[page_id]['datachanges']


@pytest.mark.parametrize('connection_id', ['conn-a', None])
def test_a_ping_for_a_page_of_another_connection_is_refused(caplog, connection_id):
    sr = _two_connections()
    pending = _pending(sr, 'v1')
    with caplog.at_level(logging.WARNING):
        result = sr.handle_ping(page_id='v1', connection_id=connection_id,
                                _serverstore_changes={'vb_filter.year': '2026'})
    assert result is False
    assert sr.page_register.get_item_data('v1')['vb_filter.year'] is None
    assert sr.page_register.registerItems['v1']['datachanges'] == pending != []
    assert sr.page_register.registerItems['v1'].get('last_refresh_ts') is None
    assert len(caplog.records) == 1


def test_a_ping_for_a_page_that_does_not_exist_answers_the_same_and_logs_nothing(caplog):
    sr = _two_connections()
    with caplog.at_level(logging.WARNING):
        assert sr.handle_ping(page_id='ghost', connection_id='conn-a') is False
    assert not caplog.records


def test_a_ping_on_its_own_page_still_works(caplog):
    sr = _two_connections()
    _pending(sr, 'p1')
    with caplog.at_level(logging.WARNING):
        envelope = sr.handle_ping(page_id='p1', connection_id='conn-a',
                                  _serverstore_changes={'vb_filter.year': '2026'})
    assert envelope['dataChanges.sc_0'] == 'p1'
    assert sr.page_register.get_item_data('p1')['vb_filter.year'] == '2026'
    assert sr.page_register.registerItems['p1']['last_refresh_ts'] is not None
    assert not caplog.records


def test_a_ping_returns_datachanges_only_for_children_of_its_connection():
    sr = _two_connections()
    _pending(sr, 'f1')
    pending = _pending(sr, 'v1')
    envelope = sr.handle_ping(page_id='p1', connection_id='conn-a',
                              _children_pages_info={'f1': {}, 'v1': {}})
    assert envelope['childDataChanges.f1.sc_0'] == 'f1'
    assert envelope.getNode('childDataChanges.v1') is None
    assert sr.page_register.registerItems['v1']['datachanges'] == pending != []


class _PingSite:
    """The real ``serve_ping`` and ``failed_exception`` on the real register."""

    serve_ping = GnrWsgiSite.serve_ping
    failed_exception = GnrWsgiSite.failed_exception
    currentDomainIdentifier = 'testsite'
    config = {'secret': 'testsecret'}

    def __init__(self, register, connection_id=None):
        self.register = register
        headers = {}
        if connection_id:
            cookie = MarshalCookie({'user': 'anna', 'connection_id': connection_id}, 'testsecret')
            headers['Cookie'] = 'testsite=%s' % cookie.output()
        self.environ = EnvironBuilder(path='/_ping', headers=headers).get_environ()
        self.currentRequest = Request(self.environ)

    def ping(self, page_id):
        status = []
        result = self.serve_ping(Response(), self.environ, lambda s, h: status.append(s),
                                 page_id=page_id, connection_id='conn-b')
        if isinstance(result, str):
            return 'ok', result
        return status[0], b''.join(result).decode().replace(page_id, '<page_id>')


def test_serve_ping_runs_only_for_a_page_of_the_cookie_connection():
    sr = _two_connections()
    _pending(sr, 'v1')
    site = _PingSite(sr, connection_id='conn-a')
    status, body = site.ping('p1')
    assert status == 'ok'
    refused, ghost = site.ping('v1'), site.ping('ghost')
    assert refused[0].startswith('412')
    assert refused == ghost
    assert sr.page_register.registerItems['v1']['datachanges'] != []


def test_serve_ping_without_the_connection_cookie_is_refused():
    sr = _two_connections()
    assert _PingSite(sr).ping('p1')[0].startswith('412')
