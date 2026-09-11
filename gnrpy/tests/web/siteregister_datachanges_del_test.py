"""Tests for the datachanges a register announces to the client (#1249).

``BaseRegister._on_data_trigger`` appended ``node.label`` only for ``evt == 'ins'``, so a
``pop('a.b.c')`` was announced on the PARENT path ``a.b`` carrying the removed value and
``delete=False``: the client wrote that value over the parent node -- siblings included --
and the deletion never reached it. ``gnrasync._on_data_trigger`` appends the label for
both events; the daemon now does the same and marks the change ``delete``.

The trigger lives on ``BaseRegister``, so every store built on it (page, user, connection,
global) is covered by the same code path -- the user register is exercised here for that
reason.

The register is a real ``SiteRegister`` built with a stand-in server -- its constructor
only needs ``server.daemon.register`` -- as in ``subscribed_tables_index_test.py``.

The fixture creates the subscribed root explicitly and clears the changes it produced, so
what each test asserts is only the event it fires: the parents a ``setItem`` autocreates
are announced too, which is a separate defect (#1230) and not what these tests measure.
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


def _site_register():
    return SiteRegister(_FakeServer(), sitename='testsite')


def _subscribed_page(sr=None):
    reg = (sr or _site_register()).page_register
    reg.create('p1')
    reg.subscribe_path('p1', 'a')
    reg.get_item_data('p1').setItem('a', Bag())
    reg.get_datachanges('p1', reset=True)
    return reg


def _paths(changes):
    return [(c.path, c.value, c.delete) for c in changes]


# ---------------------------------------------------------------------------
# what a write announces
# ---------------------------------------------------------------------------

def test_a_written_leaf_is_announced_on_its_own_path():
    reg = _subscribed_page()
    reg.get_item_data('p1').setItem('a.b', 1)
    changes = reg.get_datachanges('p1')
    assert _paths(changes) == [('a.b', 1, False)]
    assert changes[0].reason == 'serverChange'


def test_overwriting_a_leaf_keeps_the_leaf_path():
    reg = _subscribed_page()
    data = reg.get_item_data('p1')
    data.setItem('a.b', 1)
    data.setItem('a.b', 2)
    assert _paths(reg.get_datachanges('p1')) == [('a.b', 1, False), ('a.b', 2, False)]


def test_a_write_outside_the_subscribed_paths_is_ignored():
    reg = _subscribed_page()
    reg.get_item_data('p1').setItem('z.b', 1)
    assert reg.get_datachanges('p1') == []


# ---------------------------------------------------------------------------
# what a pop announces -- the defect
# ---------------------------------------------------------------------------

def test_a_popped_leaf_is_announced_on_its_own_path_as_a_delete():
    reg = _subscribed_page()
    data = reg.get_item_data('p1')
    data.setItem('a.b', 1)
    reg.get_datachanges('p1', reset=True)
    data.pop('a.b')
    assert _paths(reg.get_datachanges('p1')) == [('a.b', 1, True)]


def test_a_pop_does_not_announce_the_parent_path():
    reg = _subscribed_page()
    data = reg.get_item_data('p1')
    data.setItem('a.b.c', 1)
    data.setItem('a.b.d', 2)
    reg.get_datachanges('p1', reset=True)
    data.pop('a.b.c')
    changes = reg.get_datachanges('p1')
    assert [c.path for c in changes] == ['a.b.c']
    assert data['a.b.d'] == 2


def test_popping_a_subtree_announces_the_subtree_path():
    reg = _subscribed_page()
    data = reg.get_item_data('p1')
    data.setItem('a.b.c', 1)
    reg.get_datachanges('p1', reset=True)
    data.pop('a.b')
    changes = reg.get_datachanges('p1')
    assert [(c.path, c.delete) for c in changes] == [('a.b', True)]
    assert isinstance(changes[0].value, Bag)


def test_a_pop_outside_the_subscribed_paths_is_ignored():
    reg = _subscribed_page()
    data = reg.get_item_data('p1')
    data.setItem('z.b', 1)
    reg.get_datachanges('p1', reset=True)
    data.pop('z.b')
    assert reg.get_datachanges('p1') == []


# ---------------------------------------------------------------------------
# the flag has to reach the client
# ---------------------------------------------------------------------------

def test_the_delete_flag_travels_in_the_client_envelope():
    sr = _site_register()
    reg = _subscribed_page(sr)
    data = reg.get_item_data('p1')
    data.setItem('a.b', 1)
    reg.get_datachanges('p1', reset=True)
    data.pop('a.b')
    envelope = sr.handle_ping_get_datachanges('p1')
    nodes = envelope.getNodes()
    assert [n.attr['change_path'] for n in nodes] == ['a.b']
    assert nodes[0].attr['change_delete'] is True


def test_a_write_travels_in_the_client_envelope_without_the_delete_flag():
    sr = _site_register()
    reg = _subscribed_page(sr)
    reg.get_item_data('p1').setItem('a.b', 1)
    nodes = sr.handle_ping_get_datachanges('p1').getNodes()
    assert [n.attr['change_path'] for n in nodes] == ['a.b']
    assert nodes[0].attr['change_delete'] is False


# ---------------------------------------------------------------------------
# the trigger is BaseRegister's, so every store shares it
# ---------------------------------------------------------------------------

def test_the_user_store_announces_a_pop_the_same_way():
    reg = _site_register().user_register
    reg.create('u1')
    reg.subscribe_path('u1', 'a')
    data = reg.get_item_data('u1')
    data.setItem('a', Bag())
    data.setItem('a.b', 1)
    reg.get_datachanges('u1', reset=True)
    data.pop('a.b')
    assert _paths(reg.get_datachanges('u1')) == [('a.b', 1, True)]


# ---------------------------------------------------------------------------
# the trigger must not consume the pathlist the Bag shares with its subscribers
# ---------------------------------------------------------------------------

def test_the_trigger_leaves_the_event_pathlist_to_the_other_subscribers():
    reg = _subscribed_page()
    data = reg.get_item_data('p1')
    seen = []
    data.subscribe('probe', any=lambda node=None, pathlist=None, **kwargs:
                   seen.append('.'.join(pathlist + [node.label])))
    data.setItem('a.b', 1)
    data.pop('a.b')
    assert seen == ['a.b', 'a.b']
    assert [c.path for c in reg.get_datachanges('p1')] == ['a.b', 'a.b']
