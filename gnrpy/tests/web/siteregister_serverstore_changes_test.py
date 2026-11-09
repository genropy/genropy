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

The register is a real ``SiteRegister`` built with a stand-in server -- its constructor
only needs ``server.daemon.register`` -- as in ``subscribed_tables_index_test.py``.
"""

import logging
import types

from gnr.web.daemon.siteregister import SiteRegister
from gnr.web.daemon.siteregister_client import ServerStore
from gnr.web.gnrwebpage import GnrWebPage


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
