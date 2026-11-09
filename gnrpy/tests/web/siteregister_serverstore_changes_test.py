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

from gnr.web.daemon.siteregister import SiteRegister


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
    data = sr.page_register.get_item_data('p1')
    data.setItem('waiting2fa', 'user_id')
    data.setItem('confirm_user_id', 'user_id')
    data.setItem('rootenv.user_local_tags', 'base')
    return sr, data


def test_client_changes_reach_the_paths_the_page_syncs():
    sr, data = _page_register()
    assert sr.set_serverstore_changes('p1', {'rootenv.language': 'en', 'vb_filter.year': '2026'}) is True
    assert data['rootenv.language'] == 'en'
    assert data['vb_filter.year'] == '2026'


def test_client_changes_never_reach_server_only_paths(caplog):
    sr, data = _page_register()
    forged = {'waiting2fa': '', 'last_2fa_otp': '1', 'confirm_user_id': 'victim',
              'confirm_user_id?x': '1', 'mixin_set': 'x', 'login_checked.user': 'victim',
              'login_page_rpcs': 'x', 'rootenv.user_local_tags': 'admin', 'rootenv': 'x', '': 'x',
              'rootenv.language': 'it'}
    with caplog.at_level(logging.WARNING):
        assert sr.set_serverstore_changes('p1', forged) is True
    assert data['waiting2fa'] == 'user_id'
    assert data['confirm_user_id'] == 'user_id'
    assert data['last_2fa_otp'] is None
    assert data['mixin_set'] is None
    assert data['login_checked'] is None
    assert data['login_page_rpcs'] is None
    assert data['rootenv.user_local_tags'] == 'base'
    assert data['rootenv.language'] == 'it'
    assert len(caplog.records) == len(forged) - 1
