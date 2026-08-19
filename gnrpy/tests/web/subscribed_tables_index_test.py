"""Tests for the table -> subscribers reverse index and the write-time gate (#968).

The gate in ``GnrWsgiWebApp.notifyDbEvent`` must ask whether a table is observed by
**any** live page, not by the page doing the write: the commit-time filter it replaces
unions the subscriptions of every registered page, so a per-page question would drop
the cross-page updates that broadcast exists for — a menu badge on page A watching a
table that page B writes.

``PageRegister`` is built directly: ``BaseRegister.__init__`` only wants a siteregister
object, so no daemon and no Pyro are involved. The gate's memo is exercised on a real
``GnrWsgiWebApp.subscribedTables`` with stubbed db/site.
"""

from gnr.web.daemon.siteregister import PageRegister
from gnr.web.gnrwebapp import GnrWsgiWebApp


class _FakeSiteRegister:
    def refresh_ts(self, *args, **kwargs):
        pass


def _register():
    return PageRegister(_FakeSiteRegister())


# ---------------------------------------------------------------------------
# the reverse index
# ---------------------------------------------------------------------------


def test_create_indexes_the_initial_subscriptions():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar,foo.baz')
    assert sorted(reg.subscribed_tables()) == ['foo.bar', 'foo.baz']


def test_create_without_subscriptions_indexes_nothing():
    reg = _register()
    reg.create('page-1')
    assert reg.subscribed_tables() == []


def test_subscribe_adds_to_the_index():
    reg = _register()
    reg.create('page-1')
    reg.subscribeTable('page-1', table='foo.bar', subscribe=True)
    assert reg.subscribed_tables() == ['foo.bar']


def test_unsubscribe_removes_the_table_when_it_was_the_last_subscriber():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar')
    reg.subscribeTable('page-1', table='foo.bar', subscribe=False)
    assert reg.subscribed_tables() == []


def test_a_table_stays_observed_while_another_page_subscribes_it():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar')
    reg.create('page-2', subscribed_tables='foo.bar')
    reg.subscribeTable('page-1', table='foo.bar', subscribe=False)
    assert reg.subscribed_tables() == ['foo.bar']
    reg.subscribeTable('page-2', table='foo.bar', subscribe=False)
    assert reg.subscribed_tables() == []


def test_subscribing_twice_does_not_double_the_subscriber():
    reg = _register()
    reg.create('page-1')
    reg.subscribeTable('page-1', table='foo.bar', subscribe=True)
    reg.subscribeTable('page-1', table='foo.bar', subscribe=True)
    reg.subscribeTable('page-1', table='foo.bar', subscribe=False)
    assert reg.subscribed_tables() == []


def test_dropping_a_page_unindexes_all_its_tables():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar,foo.baz')
    reg.create('page-2', subscribed_tables='foo.baz')
    reg.drop('page-1')
    assert reg.subscribed_tables() == ['foo.baz']


def test_dropping_an_unknown_page_is_harmless():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar')
    reg.drop('page-9')
    assert reg.subscribed_tables() == ['foo.bar']


def test_filter_subscribed_tables_keeps_only_the_observed_ones():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar')
    assert reg.filter_subscribed_tables(['foo.bar', 'foo.other']) == ['foo.bar']
    assert reg.filter_subscribed_tables(['foo.other']) == []


# ---------------------------------------------------------------------------
# the gate: scope and memoization
# ---------------------------------------------------------------------------


class _FakeDb:
    def __init__(self):
        self.currentEnv = {}

    def updateEnv(self, **kwargs):
        self.currentEnv.update(kwargs)


class _FakeSite:
    def __init__(self, tables):
        self.tables = tables
        self.calls = 0

    def allSubscribedTables(self):
        self.calls += 1
        return self.tables


def _app(tables):
    app = object.__new__(GnrWsgiWebApp)
    app.db = _FakeDb()
    app.site = _FakeSite(tables)
    return app


def test_gate_sees_a_table_subscribed_by_another_page():
    """The regression: the writer is not among the subscribers, the event must pass."""
    app = _app(['foo.bar'])
    assert app.subscribedTables('foo.bar') is True


def test_gate_rejects_a_table_nobody_observes():
    app = _app(['foo.bar'])
    assert app.subscribedTables('foo.other') is False


def test_gate_asks_the_register_once_per_request():
    app = _app(['foo.bar'])
    app.subscribedTables('foo.bar')
    app.subscribedTables('foo.bar')
    app.subscribedTables('foo.other')
    assert app.site.calls == 1


def test_gate_memo_survives_an_empty_answer():
    """An empty set must be cached too, or every write re-asks the register."""
    app = _app([])
    assert app.subscribedTables('foo.bar') is False
    assert app.subscribedTables('foo.bar') is False
    assert app.site.calls == 1


def test_gate_without_a_table_returns_the_whole_set():
    app = _app(['foo.bar', 'foo.baz'])
    assert app.subscribedTables() == frozenset({'foo.bar', 'foo.baz'})


def test_gate_memo_dies_with_the_env():
    """clearCurrentEnv at the start of each page must invalidate the memo."""
    app = _app(['foo.bar'])
    app.subscribedTables('foo.bar')
    app.db.currentEnv = {}
    app.site.tables = ['foo.new']
    assert app.subscribedTables('foo.new') is True
    assert app.site.calls == 2


# ---------------------------------------------------------------------------
# the single-writer invariant
# ---------------------------------------------------------------------------


def _index_from_pages(reg):
    """Rebuild the index by scanning the per-page lists, the way it used to work."""
    rebuilt = {}
    for page_id, item in reg.items():
        for table in item['subscribed_tables']:
            rebuilt.setdefault(table, set()).add(page_id)
    return rebuilt


def test_index_never_diverges_from_the_per_page_lists():
    """The whole point of routing every mutation through updateSubscriptions."""
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar,foo.baz')
    reg.create('page-2', subscribed_tables='foo.baz')
    reg.create('page-3')
    reg.subscribeTable('page-3', table='foo.bar', subscribe=True)
    reg.subscribeTable('page-1', table='foo.bar', subscribe=False)
    reg.subscribeTable('page-2', table='foo.other', subscribe=True)
    reg.subscribeTable('page-2', table='foo.other', subscribe=False)
    assert dict(reg.tableSubscribers) == _index_from_pages(reg)
    reg.drop('page-2')
    assert dict(reg.tableSubscribers) == _index_from_pages(reg)


def test_dropping_a_page_empties_its_own_list_too():
    reg = _register()
    item = reg.create('page-1', subscribed_tables='foo.bar')
    reg.drop('page-1')
    assert item['subscribed_tables'] == []


def test_update_reports_whether_anything_changed():
    reg = _register()
    item = reg.create('page-1')
    tables = item['subscribed_tables']
    assert reg.updateSubscriptions('page-1', tables, add='foo.bar') is True
    assert reg.updateSubscriptions('page-1', tables, add='foo.bar') is False
    assert reg.updateSubscriptions('page-1', tables, remove='foo.bar') is True
    assert reg.updateSubscriptions('page-1', tables, remove='foo.bar') is False


# ---------------------------------------------------------------------------
# the per-table lookups, now served by the index
# ---------------------------------------------------------------------------


def test_page_keys_of_a_table_come_from_the_index():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar')
    reg.create('page-2', subscribed_tables='foo.bar,foo.baz')
    reg.create('page-3', subscribed_tables='foo.baz')
    assert sorted(reg.subscribed_table_page_keys('foo.bar')) == ['page-1', 'page-2']
    assert reg.subscribed_table_page_keys('foo.other') == []


def test_pages_of_a_table_are_the_real_register_items():
    reg = _register()
    item = reg.create('page-1', subscribed_tables='foo.bar')
    assert reg.subscribed_table_pages('foo.bar') == [item]
    assert reg.subscribed_table_page_items('foo.bar') == [('page-1', item)]


def test_notifying_a_table_does_not_refresh_the_subscribers_timestamp():
    """The scan this replaced read the items directly; get_item would touch itemsTS."""
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar')
    before = dict(reg.itemsTS)
    reg.subscribed_table_pages('foo.bar')
    reg.subscribed_table_page_items('foo.bar')
    assert reg.itemsTS == before


def test_a_dropped_page_leaves_no_dangling_key_in_the_index():
    reg = _register()
    reg.create('page-1', subscribed_tables='foo.bar')
    reg.create('page-2', subscribed_tables='foo.bar')
    reg.drop('page-1')
    assert reg.subscribed_table_page_keys('foo.bar') == ['page-2']
    assert reg.subscribed_table_pages('foo.bar') == [reg.registerItems['page-2']]
