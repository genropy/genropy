"""Tests for ``SiteRegister.set_serverstore_changes`` on a page the register lost (#1231).

``get_item_data`` returns a detached ``Bag()`` on a cache miss, so writing the client's
``_serverstore_changes`` into it used to drop them with no error and no log. The page can
only be missing because cleanup raced the request, which is exactly the case that has to
be visible.

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


def test_serverstore_changes_for_an_unknown_page_are_reported(caplog):
    sr = SiteRegister(_FakeServer(), sitename='testsite')
    with caplog.at_level(logging.WARNING):
        sr.set_serverstore_changes('ghost', {'rootenv.language': 'en'})
    messages = [rec.getMessage() for rec in caplog.records]
    assert any('ghost' in msg and 'rootenv.language' in msg for msg in messages)


def test_serverstore_changes_for_a_known_page_are_stored(caplog):
    sr = SiteRegister(_FakeServer(), sitename='testsite')
    sr.page_register.create('p1')
    with caplog.at_level(logging.WARNING):
        sr.set_serverstore_changes('p1', {'rootenv.language': 'en'})
    assert sr.page_register.get_item_data('p1')['rootenv.language'] == 'en'
    assert not caplog.records
