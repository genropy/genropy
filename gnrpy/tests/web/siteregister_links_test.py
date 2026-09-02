"""Tests for the parent -> children links in the site register.

A register item carries its parent id (a page knows its connection, a connection
knows its user), but the other direction had no structure: every walk down the
hierarchy scanned the whole registry. The user item now holds a ``connections``
set and the connection item a ``pages`` set, both written exclusively through
``SiteRegister.updateRegisterLink`` so the two directions of a link cannot drift.

``SiteRegister`` is built directly with a stand-in server: the only thing its
constructor needs is ``server.daemon.register`` for the remote-bag handler.
"""

from gnr.web.daemon.siteregister import SiteRegister


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


def _register():
    return SiteRegister(_FakeServer(), sitename='testsite')


def _connections_of(reg, user):
    return reg.user_register.registerItems[user]['connections']


def _pages_of(reg, connection_id):
    return reg.connection_register.registerItems[connection_id]['pages']


def _new_page(reg, page_id, connection_id, user):
    return reg.new_page(page_id, pagename='p', connection_id=connection_id, user=user)


# ---------------------------------------------------------------------------
# the sets get filled
# ---------------------------------------------------------------------------


def test_a_fresh_user_starts_with_no_connections():
    reg = _register()
    reg.new_user(user='anna')
    assert _connections_of(reg, 'anna') == set()


def test_a_fresh_connection_starts_with_no_pages():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    assert _pages_of(reg, 'conn-1') == set()


def test_a_new_connection_lands_in_its_user_set():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    assert _connections_of(reg, 'anna') == {'conn-1'}


def test_the_user_is_created_implicitly_and_still_gets_the_link():
    """new_connection creates the user when missing; the link must not be lost."""
    reg = _register()
    assert not reg.user_register.exists('anna')
    reg.new_connection('conn-1', user='anna')
    assert _connections_of(reg, 'anna') == {'conn-1'}


def test_a_new_page_lands_in_its_connection_set():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    assert _pages_of(reg, 'conn-1') == {'page-1'}


def test_several_children_accumulate():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    assert _connections_of(reg, 'anna') == {'conn-1', 'conn-2'}
    assert _pages_of(reg, 'conn-1') == {'page-1', 'page-2'}
    assert _pages_of(reg, 'conn-2') == set()


def test_two_users_do_not_share_connections():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='marco')
    assert _connections_of(reg, 'anna') == {'conn-1'}
    assert _connections_of(reg, 'marco') == {'conn-2'}


# ---------------------------------------------------------------------------
# the sets get emptied
# ---------------------------------------------------------------------------


def test_dropping_a_page_removes_it_from_its_connection():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    reg.drop_page('page-1')
    assert _pages_of(reg, 'conn-1') == {'page-2'}


def test_dropping_a_connection_removes_it_from_its_user():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='anna')
    reg.drop_connection('conn-1')
    assert _connections_of(reg, 'anna') == {'conn-2'}


def test_dropping_a_connection_drops_its_pages_and_empties_the_set():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    reg.drop_connection('conn-1')
    assert not reg.connection_register.exists('conn-1')
    assert not reg.page_register.exists('page-1')
    assert not reg.page_register.exists('page-2')


def test_dropping_a_user_cascades_through_both_levels():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    reg.drop_user('anna')
    assert not reg.user_register.exists('anna')
    assert not reg.connection_register.exists('conn-1')
    assert not reg.page_register.exists('page-1')


def test_the_last_page_leaving_cascades_the_connection_away():
    """PageRegister.drop(cascade=True) drops the connection when no page is left."""
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    reg.drop_page('page-1', cascade=True)
    assert not reg.page_register.exists('page-1')
    assert not reg.connection_register.exists('conn-1')


def test_a_surviving_sibling_keeps_the_connection_alive():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    reg.drop_page('page-1', cascade=True)
    assert reg.connection_register.exists('conn-1')
    assert _pages_of(reg, 'conn-1') == {'page-2'}


# ---------------------------------------------------------------------------
# the single writer
# ---------------------------------------------------------------------------


def test_link_reports_whether_the_set_changed():
    reg = _register()
    reg.new_user(user='anna')
    ur = reg.user_register
    assert reg.updateRegisterLink(ur, 'anna', 'connections', 'conn-1', add=True) is True
    assert reg.updateRegisterLink(ur, 'anna', 'connections', 'conn-1', add=True) is False
    assert reg.updateRegisterLink(ur, 'anna', 'connections', 'conn-1') is True
    assert reg.updateRegisterLink(ur, 'anna', 'connections', 'conn-1') is False


def test_linking_under_a_missing_parent_is_refused():
    reg = _register()
    assert reg.updateRegisterLink(reg.user_register, 'ghost', 'connections', 'c', add=True) is False


def test_linking_under_no_parent_at_all_is_refused():
    """A page may be registered with no connection_id; nothing to link then."""
    reg = _register()
    assert reg.updateRegisterLink(reg.connection_register, None, 'pages', 'p', add=True) is False


def test_a_page_with_no_connection_does_not_raise():
    reg = _register()
    _new_page(reg, 'page-1', None, 'anna')
    assert reg.page_register.exists('page-1')
    reg.drop_page('page-1')
    assert not reg.page_register.exists('page-1')


def test_linking_does_not_refresh_the_parent_timestamp():
    """A child being born must not keep an otherwise idle parent alive."""
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    before = dict(reg.connection_register.itemsTS)
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    assert reg.connection_register.itemsTS == before


# ---------------------------------------------------------------------------
# the invariant: both directions of every link agree
# ---------------------------------------------------------------------------


def _links_from_children(reg):
    """Rebuild both link sets from the children, the way a scan would."""
    connections = {}
    for user in reg.user_register.registerItems:
        connections[user] = {k for k, v in reg.connection_register.registerItems.items()
                             if v['user'] == user}
    pages = {}
    for connection_id in reg.connection_register.registerItems:
        pages[connection_id] = {k for k, v in reg.page_register.registerItems.items()
                                if v['connection_id'] == connection_id}
    return connections, pages


def _links_from_parents(reg):
    connections = {k: set(v['connections'])
                   for k, v in reg.user_register.registerItems.items()}
    pages = {k: set(v['pages'])
             for k, v in reg.connection_register.registerItems.items()}
    return connections, pages


def test_both_directions_agree_through_a_full_lifecycle():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='anna')
    reg.new_connection('conn-3', user='marco')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    _new_page(reg, 'page-3', 'conn-2', 'anna')
    _new_page(reg, 'page-4', 'conn-3', 'marco')
    assert _links_from_parents(reg) == _links_from_children(reg)
    reg.drop_page('page-2')
    assert _links_from_parents(reg) == _links_from_children(reg)
    reg.drop_connection('conn-2')
    assert _links_from_parents(reg) == _links_from_children(reg)
    reg.change_connection_user('conn-1', user='bruno')
    assert _links_from_parents(reg) == _links_from_children(reg)
    reg.drop_user('marco')
    assert _links_from_parents(reg) == _links_from_children(reg)
    reg.drop_page('page-1', cascade=True)
    assert _links_from_parents(reg) == _links_from_children(reg)


def test_change_connection_user_moves_the_link_between_users():
    """The guest-to-authenticated shape: every login goes through here."""
    reg = _register()
    reg.new_connection('conn-1', user='guest_1')
    _new_page(reg, 'page-1', 'conn-1', 'guest_1')
    reg.change_connection_user('conn-1', user='anna')
    # the connection now belongs to anna, link included
    assert _connections_of(reg, 'anna') == {'conn-1'}
    assert [c['register_item_id'] for c in reg.connections(user='anna')] == ['conn-1']
    assert [p['register_item_id'] for p in reg.pages(user='anna')] == ['page-1']
    # the guest, left with no connections, is gone with its links
    assert not reg.user_register.exists('guest_1')
    assert reg.connections(user='guest_1') == []
    assert reg.pages(user='guest_1') == []
    assert _links_from_parents(reg) == _links_from_children(reg)


def test_change_connection_user_keeps_the_old_users_other_connections():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='anna')
    reg.change_connection_user('conn-1', user='bruno')
    assert _connections_of(reg, 'anna') == {'conn-2'}
    assert _connections_of(reg, 'bruno') == {'conn-1'}
    assert reg.user_register.exists('anna')
    assert _links_from_parents(reg) == _links_from_children(reg)


# ---------------------------------------------------------------------------
# the readers, now walking the links instead of the registry
# ---------------------------------------------------------------------------


def _populate(reg):
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='anna')
    reg.new_connection('conn-3', user='marco')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    _new_page(reg, 'page-3', 'conn-2', 'anna')
    _new_page(reg, 'page-4', 'conn-3', 'marco')
    return reg


def test_user_connection_keys_walks_the_user_set():
    reg = _populate(_register())
    assert sorted(reg.user_connection_keys('anna')) == ['conn-1', 'conn-2']
    assert reg.user_connection_keys('marco') == ['conn-3']
    assert reg.user_connection_keys('ghost') == []


def test_user_connection_items_and_connections_return_the_real_items():
    reg = _populate(_register())
    items = dict(reg.user_connection_items('marco'))
    assert list(items) == ['conn-3']
    assert items['conn-3'] is reg.connection_register.registerItems['conn-3']
    assert reg.user_connections('marco') == [reg.connection_register.registerItems['conn-3']]


def test_connection_page_keys_walks_the_connection_set():
    reg = _populate(_register())
    assert sorted(reg.connection_page_keys('conn-1')) == ['page-1', 'page-2']
    assert reg.connection_page_keys('conn-3') == ['page-4']
    assert reg.connection_page_keys('ghost') == []


def test_pages_of_a_connection():
    reg = _populate(_register())
    got = sorted(p['register_item_id'] for p in reg.pages(connection_id='conn-1'))
    assert got == ['page-1', 'page-2']


def test_pages_of_a_user_walks_user_then_connections():
    reg = _populate(_register())
    got = sorted(p['register_item_id'] for p in reg.pages(user='anna'))
    assert got == ['page-1', 'page-2', 'page-3']


def test_pages_with_no_argument_still_returns_everything():
    reg = _populate(_register())
    got = sorted(p['register_item_id'] for p in reg.pages())
    assert got == ['page-1', 'page-2', 'page-3', 'page-4']


def test_pages_with_a_mismatched_connection_and_user_returns_nothing():
    """conn-3 belongs to marco, so asking for anna's pages on it is empty."""
    reg = _populate(_register())
    assert reg.pages(connection_id='conn-3', user='anna') == []


def test_pages_of_an_unknown_parent_is_empty():
    reg = _populate(_register())
    assert reg.pages(connection_id='ghost') == []
    assert reg.pages(user='ghost') == []


def test_connections_of_a_user_and_of_nobody():
    reg = _populate(_register())
    got = sorted(c['register_item_id'] for c in reg.connection_register.connections(user='anna'))
    assert got == ['conn-1', 'conn-2']
    got_all = sorted(c['register_item_id']
                     for c in reg.connection_register.connections())
    assert got_all == ['conn-1', 'conn-2', 'conn-3']


def test_the_readers_agree_with_a_scan_of_the_whole_registry():
    """The conversion must not change what the readers answer, only how."""
    reg = _populate(_register())
    for connection_id in ['conn-1', 'conn-2', 'conn-3']:
        scanned = sorted(k for k, v in reg.page_register.registerItems.items()
                         if v['connection_id'] == connection_id)
        assert sorted(reg.connection_page_keys(connection_id)) == scanned
    for user in ['anna', 'marco']:
        scanned = sorted(k for k, v in reg.connection_register.registerItems.items()
                         if v['user'] == user)
        assert sorted(reg.user_connection_keys(user)) == scanned
        scanned_pages = sorted(k for k, v in reg.page_register.registerItems.items()
                               if v['user'] == user)
        assert sorted(p['register_item_id'] for p in reg.pages(user=user)) == scanned_pages


def test_readers_do_not_refresh_timestamps():
    reg = _populate(_register())
    before_pages = dict(reg.page_register.itemsTS)
    before_conns = dict(reg.connection_register.itemsTS)
    reg.pages(user='anna')
    reg.pages(connection_id='conn-1')
    reg.user_connection_items('anna')
    reg.connection_page_items('conn-1')
    assert reg.page_register.itemsTS == before_pages
    assert reg.connection_register.itemsTS == before_conns


def test_dropping_while_iterating_the_walk_is_safe():
    """drop_pages and drop_connections iterate what the readers return."""
    reg = _populate(_register())
    reg.drop_pages('conn-1')
    assert reg.connection_page_keys('conn-1') == []
    reg.drop_connections('anna')
    assert reg.user_connection_keys('anna') == []
    assert not reg.connection_register.exists('conn-2')
    assert not reg.page_register.exists('page-3')


# ---------------------------------------------------------------------------
# drift: a link set outliving the child it points at (#1219)
# ---------------------------------------------------------------------------


def test_dropping_a_page_whose_item_already_vanished_still_unlinks_it():
    """The unlink used to read the parent id off the page item, so it was skipped
    exactly when the item was already gone — leaving a dead id in the set forever."""
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    reg.page_register.registerItems.pop('page-1')   # item gone, set still holds it
    reg.drop_page('page-1')
    assert _pages_of(reg, 'conn-1') == set()


def test_dropping_a_connection_whose_item_already_vanished_still_unlinks_it():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.connection_register.registerItems.pop('conn-1')
    reg.drop_connection('conn-1')
    assert _connections_of(reg, 'anna') == set()


def test_drop_connections_converges_on_a_dangling_id():
    """A dead id made drop_connection skip the unlink, so every later call walked
    the same id again: the loop could never empty the set."""
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.connection_register.registerItems.pop('conn-1')
    reg.drop_connections('anna')
    assert _connections_of(reg, 'anna') == set()
    reg.drop_connections('anna')          # idempotent, nothing left to walk
    assert _connections_of(reg, 'anna') == set()


def test_a_dangling_page_is_pruned_instead_of_raising():
    """connection_page_items indexed registerItems directly: one dead id raised
    KeyError for every caller, and the id stayed. It is pruned and the live
    children are still returned."""
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    reg.page_register.registerItems.pop('page-1')
    got = reg.connection_page_items('conn-1')
    assert [k for k, _ in got] == ['page-2']
    assert _pages_of(reg, 'conn-1') == {'page-2'}


def test_a_dangling_connection_is_pruned_instead_of_raising():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='anna')
    reg.connection_register.registerItems.pop('conn-1')
    got = reg.user_connection_items('anna')
    assert [k for k, _ in got] == ['conn-2']
    assert _connections_of(reg, 'anna') == {'conn-2'}


def test_connection_pages_and_user_connections_prune_too():
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    reg.page_register.registerItems.pop('page-1')
    assert reg.connection_pages('conn-1') == []
    reg.connection_register.registerItems.pop('conn-1')
    assert reg.user_connections('anna') == []


def test_dropRegisterLinks_scans_every_parent_holding_the_child():
    """Driven by the sets rather than by the child, so it works with the child gone."""
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    reg.new_connection('conn-2', user='marco')
    _pages_of(reg, 'conn-2').add('page-1')          # drift: two parents claim it
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    reg.dropRegisterLinks(reg.connection_register, 'pages', 'page-1')
    assert _pages_of(reg, 'conn-1') == set()
    assert _pages_of(reg, 'conn-2') == set()


def test_load_rebuilds_the_link_sets_from_the_restored_children():
    """The three registers are pickled and restored independently, so a parent's
    set knows nothing of the children that came back — and whatever it held
    before dangles."""
    import io as _io
    reg = _register()
    reg.new_connection('conn-1', user='anna')
    _new_page(reg, 'page-1', 'conn-1', 'anna')
    _new_page(reg, 'page-2', 'conn-1', 'anna')
    storage = _io.BytesIO()
    reg.user_register.dump(storage)
    reg.connection_register.dump(storage)
    reg.page_register.dump(storage)
    storage.seek(0)

    restored = _register()
    restored.user_register.load(storage)
    restored.connection_register.load(storage)
    restored.page_register.load(storage)
    # the state a restore leaves behind before the rebuild: sets carrying whatever
    # was pickled with the parent, blind to the children actually restored
    _connections_of(restored, 'anna').add('ghost-conn')
    _pages_of(restored, 'conn-1').add('ghost-page')

    restored.rebuildRegisterLinks(restored.user_register, restored.connection_register,
                                  'user', 'connections')
    restored.rebuildRegisterLinks(restored.connection_register, restored.page_register,
                                  'connection_id', 'pages')

    assert _connections_of(restored, 'anna') == {'conn-1'}
    assert _pages_of(restored, 'conn-1') == {'page-1', 'page-2'}


def test_pages_prunes_a_dangling_id_by_connection():
    """pages() is the reader on the request path: validate_page_id falls back to it."""
    reg = _populate(_register())
    reg.page_register.registerItems.pop('page-1')
    got = sorted(p['register_item_id'] for p in reg.pages(connection_id='conn-1'))
    assert got == ['page-2']
    assert _pages_of(reg, 'conn-1') == {'page-2'}


def test_pages_prunes_a_dangling_id_by_user_across_connections():
    """The user walk spans several connections, so the prune cannot assume one parent."""
    reg = _populate(_register())
    reg.page_register.registerItems.pop('page-3')      # lives under conn-2
    got = sorted(p['register_item_id'] for p in reg.pages(user='anna'))
    assert got == ['page-1', 'page-2']
    assert _pages_of(reg, 'conn-2') == set()


def test_pages_with_include_data_prunes_instead_of_yielding_none():
    """get_item returns None for a missing key: without the prune that None
    travels on into Bag(page) and fails somewhere else entirely."""
    reg = _populate(_register())
    reg.page_register.registerItems.pop('page-1')
    got = reg.pages(connection_id='conn-1', include_data=True)
    assert None not in got
    assert [p['register_item_id'] for p in got] == ['page-2']


def test_connections_with_include_data_prunes_too():
    reg = _populate(_register())
    reg.connection_register.registerItems.pop('conn-1')
    got = reg.connection_register.connections(user='anna', include_data=True)
    assert None not in got
    assert [c['register_item_id'] for c in got] == ['conn-2']
