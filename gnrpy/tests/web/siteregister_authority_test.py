"""The child item is authoritative, the parent's link set is derived from it.

Three registers hold the hierarchy: a page item carries ``connection_id``, a
connection item carries ``user``. Those two fields are the only statement of
where a child belongs. The ``pages`` set on a connection item and the
``connections`` set on a user item say the same thing in the other direction,
so they are an index: reconstructible at any moment from the children alone,
and never a source of truth.

One invariant follows, and every test here asserts it after a single access:
rebuilding the sets from the child fields must reproduce exactly the sets that
are stored. When it does, no reader has to search for the parent of an orphan
key, because no orphan key exists.

The suite walks the whole mutating surface -- the ``SiteRegister`` facade, the
registers underneath it, expiry and the freeze round trip -- so that a path
which maintains the item but forgets the index fails here rather than months
later on a running daemon.
"""

from datetime import datetime, timedelta

import pytest

from gnr.web.daemon.siteregister import SiteRegister


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


def _register(**cleanup):
    reg = SiteRegister(_FakeServer(), sitename='testsite')
    reg.setConfiguration(cleanup or None)
    return reg


# ---------------------------------------------------------------------------
# the invariant
# ---------------------------------------------------------------------------


def _derived(reg):
    """The link sets as a rebuild from the child items alone would produce them."""
    connections = {user: set() for user in reg.user_register.registerItems}
    for connection_id, item in reg.connection_register.registerItems.items():
        connections.setdefault(item['user'], set()).add(connection_id)
    pages = {c: set() for c in reg.connection_register.registerItems}
    for page_id, item in reg.page_register.registerItems.items():
        pages.setdefault(item['connection_id'], set()).add(page_id)
    return connections, pages


def _stored(reg):
    connections = {user: set(item.get('connections') or ())
                   for user, item in reg.user_register.registerItems.items()}
    pages = {connection_id: set(item.get('pages') or ())
             for connection_id, item in reg.connection_register.registerItems.items()}
    return connections, pages


def _orphans(reg):
    """Children whose declared parent is not in the register."""
    users = reg.user_register.registerItems
    connections = reg.connection_register.registerItems
    return (
        sorted(c for c, i in connections.items() if i['user'] not in users),
        sorted(p for p, i in reg.page_register.registerItems.items()
               if i['connection_id'] not in connections),
    )


def assert_authoritative(reg):
    """Every stored set equals its rebuild, and no child points at a dead parent."""
    stored_connections, stored_pages = _stored(reg)
    derived_connections, derived_pages = _derived(reg)
    orphan_connections, orphan_pages = _orphans(reg)
    assert orphan_connections == [], 'connections whose user is gone'
    assert orphan_pages == [], 'pages whose connection is gone'
    assert stored_connections == derived_connections, 'user connections sets drifted'
    assert stored_pages == derived_pages, 'connection pages sets drifted'


def _populate(reg, users=2, connections=2, pages=2):
    """users x connections x pages, ids carrying their whole ancestry."""
    for u in range(users):
        user = 'user-%d' % u
        for c in range(connections):
            connection_id = '%s/conn-%d' % (user, c)
            reg.new_connection(connection_id, user=user)
            for p in range(pages):
                reg.new_page('%s/page-%d' % (connection_id, p), pagename='p',
                             connection_id=connection_id, user=user)
    assert_authoritative(reg)
    return reg


# ---------------------------------------------------------------------------
# the invariant holds on an untouched and on a populated register
# ---------------------------------------------------------------------------


def test_an_empty_register_is_authoritative():
    assert_authoritative(_register())


def test_a_populated_register_is_authoritative():
    assert_authoritative(_populate(_register()))


def test_the_helper_catches_a_set_that_lost_a_live_page():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.connection_register.registerItems['user-0/conn-0']['pages'].clear()
    with pytest.raises(AssertionError):
        assert_authoritative(reg)


def test_the_helper_catches_a_set_holding_a_dead_page():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.connection_register.registerItems['user-0/conn-0']['pages'].add('ghost')
    with pytest.raises(AssertionError):
        assert_authoritative(reg)


def test_the_helper_catches_a_page_whose_connection_is_gone():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.connection_register.drop_item('user-0/conn-0')
    with pytest.raises(AssertionError):
        assert_authoritative(reg)


# ---------------------------------------------------------------------------
# creation through the facade
# ---------------------------------------------------------------------------


def test_new_user_alone():
    reg = _register()
    reg.new_user(user='anna')
    assert_authoritative(reg)


def test_new_connection_on_an_existing_user():
    reg = _register()
    reg.new_user(user='anna')
    reg.new_connection('conn-1', user='anna')
    assert_authoritative(reg)


def test_new_connection_creating_its_user():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    assert_authoritative(reg)


def test_new_page():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_page('page-1', pagename='p', connection_id='conn-1', user='anna')
    assert_authoritative(reg)


def test_new_page_repeated_with_the_same_id():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    for _ in range(3):
        reg.new_page('page-1', pagename='p', connection_id='conn-1', user='anna')
    assert_authoritative(reg)


def test_new_connection_refuses_an_id_already_registered():
    """The duplicate is refused outright, so the set cannot gain a second entry."""
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    with pytest.raises(AssertionError, match='already registered'):
        reg.new_connection('conn-1', user='anna')
    assert_authoritative(reg)


def test_two_users_holding_a_connection_each():
    reg = _register()
    reg.new_connection('conn-a', user='anna')
    reg.new_connection('conn-b', user='bruno')
    assert_authoritative(reg)


# ---------------------------------------------------------------------------
# removal through the facade
# ---------------------------------------------------------------------------


def test_drop_page():
    reg = _populate(_register())
    reg.drop_page('user-0/conn-0/page-0')
    assert_authoritative(reg)


def test_drop_every_page_one_by_one():
    reg = _populate(_register())
    for page_id in list(reg.page_register.registerItems):
        reg.drop_page(page_id)
        assert_authoritative(reg)


def test_drop_pages_of_a_connection():
    reg = _populate(_register())
    reg.drop_pages('user-0/conn-0')
    assert_authoritative(reg)


def test_drop_connection():
    reg = _populate(_register())
    reg.drop_connection('user-0/conn-0')
    assert_authoritative(reg)


def test_drop_every_connection_one_by_one():
    reg = _populate(_register())
    for connection_id in list(reg.connection_register.registerItems):
        reg.drop_connection(connection_id)
        assert_authoritative(reg)


def test_drop_connections_of_a_user():
    reg = _populate(_register())
    reg.drop_connections('user-0')
    assert_authoritative(reg)


def test_drop_user():
    reg = _populate(_register())
    reg.drop_user('user-0')
    assert_authoritative(reg)


def test_drop_every_user():
    reg = _populate(_register())
    for user in list(reg.user_register.registerItems):
        reg.drop_user(user)
        assert_authoritative(reg)
    assert reg.page_register.registerItems == {}


def test_drop_page_twice():
    reg = _populate(_register())
    reg.drop_page('user-0/conn-0/page-0')
    reg.drop_page('user-0/conn-0/page-0')
    assert_authoritative(reg)


def test_drop_an_unknown_page():
    reg = _populate(_register())
    reg.drop_page('never-existed')
    assert_authoritative(reg)


def test_drop_an_unknown_connection():
    reg = _populate(_register())
    reg.drop_connection('never-existed')
    assert_authoritative(reg)


def test_drop_an_unknown_user():
    reg = _populate(_register())
    reg.drop_user('never-existed')
    assert_authoritative(reg)


# ---------------------------------------------------------------------------
# cascade: the last child takes its parent down
# ---------------------------------------------------------------------------


def test_page_drop_cascade_takes_the_emptied_connection():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.page_register.drop('user-0/conn-0/page-0', cascade=True)
    assert not reg.connection_register.exists('user-0/conn-0')
    assert_authoritative(reg)


def test_page_drop_cascade_spares_a_connection_with_pages_left():
    reg = _populate(_register(), users=1, connections=1, pages=2)
    reg.page_register.drop('user-0/conn-0/page-0', cascade=True)
    assert reg.connection_register.exists('user-0/conn-0')
    assert_authoritative(reg)


def test_connection_drop_cascade_takes_the_emptied_user():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.connection_register.drop('user-0/conn-0', cascade=True)
    assert not reg.user_register.exists('user-0')
    assert_authoritative(reg)


def test_connection_drop_cascade_spares_a_user_with_connections_left():
    reg = _populate(_register(), users=1, connections=2, pages=1)
    reg.connection_register.drop('user-0/conn-0', cascade=True)
    assert reg.user_register.exists('user-0')
    assert_authoritative(reg)


def test_cascade_from_a_page_stops_at_the_connection():
    """One level only: drop_connection is called without cascade, so the
    emptied user stays. Asserted as it behaves, not as the name suggests."""
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.drop_page('user-0/conn-0/page-0', cascade=True)
    assert not reg.connection_register.exists('user-0/conn-0')
    assert reg.user_register.exists('user-0')
    assert_authoritative(reg)


# ---------------------------------------------------------------------------
# the registers reached directly, bypassing the facade
# ---------------------------------------------------------------------------


def test_page_register_create_maintains_the_connection_set():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.page_register.create('loose-page', pagename='p',
                             connection_id='user-0/conn-0', user='user-0')
    assert_authoritative(reg)


def test_connection_register_create_maintains_the_user_set():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.connection_register.create('loose-conn', user='user-0')
    assert_authoritative(reg)


def test_page_register_drop_maintains_the_connection_set():
    reg = _populate(_register(), users=1, connections=1, pages=2)
    reg.page_register.drop('user-0/conn-0/page-0')
    assert_authoritative(reg)


def test_connection_register_drop_maintains_the_user_set():
    reg = _populate(_register(), users=1, connections=2, pages=1)
    reg.connection_register.drop('user-0/conn-1')
    assert_authoritative(reg)


def test_a_register_reached_through_get_register_behaves_the_same():
    reg = _populate(_register(), users=1, connections=1, pages=2)
    reg.get_register('page').drop('user-0/conn-0/page-0')
    assert_authoritative(reg)


# ---------------------------------------------------------------------------
# moving a connection between users
# ---------------------------------------------------------------------------


def test_change_connection_user_to_a_fresh_user():
    reg = _populate(_register(), users=1, connections=2, pages=1)
    reg.change_connection_user('user-0/conn-0', user='bruno')
    assert_authoritative(reg)


def test_change_connection_user_to_an_existing_user():
    reg = _populate(_register(), users=2, connections=1, pages=1)
    reg.change_connection_user('user-0/conn-0', user='user-1')
    assert_authoritative(reg)


def test_change_connection_user_emptying_the_old_user():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.change_connection_user('user-0/conn-0', user='bruno')
    assert not reg.user_register.exists('user-0')
    assert_authoritative(reg)


def test_change_connection_user_to_the_same_user():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.change_connection_user('user-0/conn-0', user='user-0')
    assert_authoritative(reg)


def test_change_connection_user_then_drop_the_connection():
    reg = _populate(_register(), users=2, connections=1, pages=1)
    reg.change_connection_user('user-0/conn-0', user='user-1')
    reg.drop_connection('user-0/conn-0')
    assert_authoritative(reg)


def test_change_connection_user_moves_the_pages_too():
    reg = _populate(_register(), users=2, connections=1, pages=2)
    reg.change_connection_user('user-0/conn-0', user='user-1')
    assert all(p['user'] == 'user-1'
               for p in reg.page_register.registerItems.values()
               if p['connection_id'] == 'user-0/conn-0')
    assert_authoritative(reg)


# ---------------------------------------------------------------------------
# expiry
# ---------------------------------------------------------------------------


def _age(item, seconds):
    item['last_refresh_ts'] = datetime.now() - timedelta(seconds=seconds)


def test_expire_pages_drops_the_idle_ones_only():
    reg = _populate(_register(page_max_age=60), users=1, connections=1, pages=2)
    _age(reg.page_register.registerItems['user-0/conn-0/page-0'], 3600)
    _age(reg.page_register.registerItems['user-0/conn-0/page-1'], 5)
    assert reg.expire_pages('user-0/conn-0') == ['user-0/conn-0/page-0']
    assert_authoritative(reg)


def test_expire_pages_draining_a_connection():
    reg = _populate(_register(page_max_age=60), users=1, connections=1, pages=2)
    for item in reg.page_register.registerItems.values():
        _age(item, 3600)
    reg.expire_pages('user-0/conn-0')
    assert_authoritative(reg)


def test_expire_pages_on_an_unknown_connection():
    reg = _populate(_register(page_max_age=60), users=1, connections=1, pages=1)
    assert reg.expire_pages('never-existed') == []
    assert_authoritative(reg)


def test_expire_connection_drops_it_with_its_pages():
    reg = _populate(_register(connection_max_age=60), users=1, connections=2, pages=2)
    _age(reg.connection_register.registerItems['user-0/conn-0'], 3600)
    assert reg.expire_connection('user-0/conn-0') is True
    assert_authoritative(reg)


def test_expire_connection_spares_a_fresh_one():
    reg = _populate(_register(connection_max_age=60), users=1, connections=1, pages=1)
    _age(reg.connection_register.registerItems['user-0/conn-0'], 5)
    assert reg.expire_connection('user-0/conn-0') is False
    assert_authoritative(reg)


def test_expire_connection_on_an_unknown_connection():
    reg = _populate(_register(connection_max_age=60), users=1, connections=1, pages=1)
    assert reg.expire_connection('never-existed') is False
    assert_authoritative(reg)


def test_expire_every_connection_of_a_user():
    reg = _populate(_register(connection_max_age=60), users=1, connections=2, pages=1)
    for item in reg.connection_register.registerItems.values():
        _age(item, 3600)
    for connection_id in list(reg.connection_register.registerItems):
        reg.expire_connection(connection_id)
        assert_authoritative(reg)
    assert reg.user_register.registerItems == {}


# ---------------------------------------------------------------------------
# the freeze round trip rebuilds the sets from the children
# ---------------------------------------------------------------------------


def _round_trip(reg, tmp_path):
    reg.storage_path = str(tmp_path / 'register.pik')
    reg.dump()
    restored = _register()
    restored.storage_path = reg.storage_path
    assert restored.load() is True
    return restored


def test_a_round_trip_preserves_the_hierarchy(tmp_path):
    reg = _populate(_register())
    restored = _round_trip(reg, tmp_path)
    assert_authoritative(restored)
    assert restored.page_register.registerItems.keys() == reg.page_register.registerItems.keys()


def test_a_round_trip_rebuilds_a_set_that_had_drifted(tmp_path):
    reg = _populate(_register(), users=1, connections=1, pages=2)
    reg.connection_register.registerItems['user-0/conn-0']['pages'] = {'ghost'}
    assert_authoritative(_round_trip(reg, tmp_path))


def test_a_round_trip_of_an_empty_register(tmp_path):
    assert_authoritative(_round_trip(_register(), tmp_path))


def test_dropping_after_a_round_trip(tmp_path):
    reg = _populate(_register())
    restored = _round_trip(reg, tmp_path)
    restored.drop_page('user-0/conn-0/page-0')
    restored.drop_connection('user-1/conn-1')
    restored.drop_user('user-0')
    assert_authoritative(restored)


# ---------------------------------------------------------------------------
# re-registering an id: a replacement, and the replacement may name another parent
# ---------------------------------------------------------------------------


def test_re_registering_a_page_under_another_connection_moves_it():
    """create replaces the item wholesale. Without unlinking the previous one,
    both connections end up claiming the page -- the drift a parent-unknown scan
    was there to clean up."""
    reg = _populate(_register(), users=1, connections=2, pages=0)
    reg.new_page('page-1', pagename='p', connection_id='user-0/conn-0', user='user-0')
    reg.new_page('page-1', pagename='p', connection_id='user-0/conn-1', user='user-0')
    assert_authoritative(reg)
    assert reg.connection_page_keys('user-0/conn-0') == []
    assert reg.connection_page_keys('user-0/conn-1') == ['page-1']


def test_re_registering_a_connection_under_another_user_moves_it():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.new_user(user='bruno')
    reg.connection_register.create('user-0/conn-0', user='bruno')
    assert_authoritative(reg)


def test_re_registering_a_page_on_the_same_connection_is_a_no_op():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.new_page('page-1', pagename='p', connection_id='user-0/conn-0', user='user-0')
    reg.new_page('page-1', pagename='p', connection_id='user-0/conn-0', user='user-0')
    assert_authoritative(reg)
    assert sorted(reg.connection_page_keys('user-0/conn-0')) == [
        'page-1', 'user-0/conn-0/page-0']


def test_the_two_ends_of_a_link_agree_on_its_name():
    """child_link_name on the parent and parent_link_name on the child name the
    same set; they are declared in two classes, so the pair is asserted here."""
    reg = _register()
    assert reg.user_register.child_link_name == reg.connection_register.parent_link_name
    assert reg.connection_register.child_link_name == reg.page_register.parent_link_name
    assert reg.page_register.child_link_name is None
    assert reg.user_register.parent_field is None


def test_re_registering_a_connection_keeps_its_pages():
    """The replacement item arrives with an empty set while its pages are still
    there and still name it."""
    reg = _populate(_register(), users=1, connections=1, pages=2)
    reg.connection_register.create('user-0/conn-0', user='user-0')
    assert_authoritative(reg)
    assert sorted(reg.connection_page_keys('user-0/conn-0')) == [
        'user-0/conn-0/page-0', 'user-0/conn-0/page-1']


def test_re_registering_a_user_keeps_its_connections():
    reg = _populate(_register(), users=1, connections=2, pages=1)
    reg.user_register.create('user-0')
    assert_authoritative(reg)
    assert len(reg.user_connection_keys('user-0')) == 2


def test_reparenting_a_register_whose_items_have_no_parent_is_refused():
    """It used to write a None key into the item and then fail on the missing
    parent register, leaving the item corrupted. Registers are reachable through
    get_register, remotely included."""
    reg = _populate(_register(), users=1, connections=1, pages=1)
    with pytest.raises(AssertionError, match='no parent'):
        reg.user_register.reparent_item('user-0', 'bruno')
    assert None not in reg.user_register.registerItems['user-0']
    assert_authoritative(reg)


# ---------------------------------------------------------------------------
# update_item: the parent field is a link, not an ordinary field
# ---------------------------------------------------------------------------


def test_update_item_moving_a_page_to_another_connection_moves_the_link():
    """update_item writes whatever it is given straight into the item. The parent
    field is half of a link, so it goes through reparent_item instead."""
    reg = _populate(_register(), users=1, connections=2, pages=1)
    reg.page_register.update_item('user-0/conn-0/page-0',
                                  dict(connection_id='user-0/conn-1'))
    assert_authoritative(reg)
    assert reg.connection_page_keys('user-0/conn-0') == []
    assert sorted(reg.connection_page_keys('user-0/conn-1')) == [
        'user-0/conn-0/page-0', 'user-0/conn-1/page-0']


def test_update_item_moving_a_connection_to_another_user_moves_the_link():
    reg = _populate(_register(), users=2, connections=1, pages=1)
    reg.connection_register.update_item('user-0/conn-0', dict(user='user-1'))
    assert_authoritative(reg)
    assert reg.user_connection_keys('user-0') == []


def test_update_item_carries_the_other_fields_through():
    reg = _populate(_register(), users=1, connections=2, pages=1)
    reg.page_register.update_item('user-0/conn-0/page-0',
                                  dict(connection_id='user-0/conn-1', pagename='moved'))
    item = reg.page_register.registerItems['user-0/conn-0/page-0']
    assert item['pagename'] == 'moved'
    assert item['connection_id'] == 'user-0/conn-1'
    assert_authoritative(reg)


def test_update_item_without_the_parent_field_is_untouched():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.page_register.update_item('user-0/conn-0/page-0', dict(pagename='renamed'))
    assert reg.page_register.registerItems['user-0/conn-0/page-0']['pagename'] == 'renamed'
    assert_authoritative(reg)


def test_update_item_on_a_register_whose_items_have_no_parent():
    reg = _populate(_register(), users=1, connections=1, pages=1)
    reg.user_register.update_item('user-0', dict(user_name='Zero'))
    assert reg.user_register.registerItems['user-0']['user_name'] == 'Zero'
    assert_authoritative(reg)
