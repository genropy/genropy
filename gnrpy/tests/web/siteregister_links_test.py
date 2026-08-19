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
    reg.drop_user('marco')
    assert _links_from_parents(reg) == _links_from_children(reg)
    reg.drop_page('page-1', cascade=True)
    assert _links_from_parents(reg) == _links_from_children(reg)
