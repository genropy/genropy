"""Tests for the datachanges a page store announces to the client (#1230).

A ``setItem('a.b.c', 1)`` on a Bag whose ``a`` and ``a.b`` do not exist yet makes the Bag
insert the parents on the fly (``reason='autocreate'``). Those parents carry an empty Bag,
and the client rewrites whatever it holds under that path whenever the value differs
(``genro_rpc.js:setDatachangesInData``), so announcing them wipes the client-side subtree
an instant before the leaf arrives. Writing the leaf recreates the parents anyway.

``_on_data_trigger`` lives on ``BaseRegister``, so the filter covers the page, user,
connection and global stores at once. ``gnrasync._on_data_trigger`` already filters the
identical event.

The register is a real ``SiteRegister`` built with a stand-in server -- its constructor
only needs ``server.daemon.register`` -- as in ``subscribed_tables_index_test.py``.
"""

from gnr.core.gnrbag import Bag
from gnr.web.daemon.siteregister import SiteRegister


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


def _subscribed_page():
    reg = SiteRegister(_FakeServer(), sitename='testsite').page_register
    reg.create('p1')
    reg.subscribe_path('p1', 'a')
    return reg


def test_autocreated_parents_are_not_announced_as_server_changes():
    reg = _subscribed_page()
    reg.get_item_data('p1').setItem('a.b.c', 1)
    changes = reg.get_datachanges('p1')
    assert [c.path for c in changes] == ['a.b.c']
    assert changes[0].reason == 'serverChange'


def test_an_explicitly_written_empty_bag_still_travels():
    reg = _subscribed_page()
    reg.get_item_data('p1').setItem('a.sub', Bag())
    changes = reg.get_datachanges('p1')
    assert [c.path for c in changes] == ['a.sub']


def test_attributes_and_rewrites_of_a_leaf_still_travel():
    reg = _subscribed_page()
    data = reg.get_item_data('p1')
    data.setItem('a.b.c', 1)
    data.setItem('a.b.c', 2)
    data.setItem('a.x', 'v', mode='wide')
    changes = reg.get_datachanges('p1')
    assert [c.path for c in changes] == ['a.b.c', 'a.b.c', 'a.x']
    assert [c.value for c in changes] == [1, 2, 'v']
    assert changes[2].attributes == dict(mode='wide')
