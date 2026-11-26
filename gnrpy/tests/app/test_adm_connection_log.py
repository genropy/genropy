"""adm.connection and adm.served_page on a real database (issue #1977).

The session log must say when a connection and its pages really ended:
at logout, when the register expires them, and for the ones a restart
left open. The site register is a daemon: here it is a stub that only
answers which connections are alive.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


T0 = datetime.now().replace(microsecond=0) - timedelta(days=2)


class _Register:
    def __init__(self):
        self.live = {}

    def connections(self):
        return self.live


def _page(connection_id, page_id, path='/adm/user_page', parent_page_id=None, root_page_id=None):
    request = SimpleNamespace(remote_addr='10.0.0.1', path_info=path,
                              get_header=lambda name: 'pytest-agent')
    return SimpleNamespace(connection_id=connection_id, page_id=page_id, basename='user_page',
                           avatar=SimpleNamespace(user='mario', user_id=None),
                           request=request, parent_page_id=parent_page_id, root_page_id=root_page_id)


@pytest.fixture
def site(db_sqlite, monkeypatch):
    site = SimpleNamespace(register=_Register(), currentPage=None)
    monkeypatch.setattr(db_sqlite.application, 'site', site, raising=False)
    return site


def _connection(db, connection_id):
    return db.table('adm.connection').record(pkey=connection_id).output('dict')


def _served_page(db, page_id):
    return db.table('adm.served_page').record(pkey=page_id).output('dict')


def _open(db, site, connection_id, *page_ids):
    """Log a connection and its pages as started at T0."""
    site.currentPage = _page(connection_id, None)
    db.table('adm.connection').connectionLog('open')
    _stamp(db, 'adm.connection', connection_id, start_ts=T0)
    for page_id in page_ids:
        site.currentPage = _page(connection_id, page_id)
        db.table('adm.served_page').pageLog('open')
        _stamp(db, 'adm.served_page', page_id, start_ts=T0)
    site.currentPage = None


def _stamp(db, table, pkey, **values):
    tbl = db.table(table)
    with db.tempEnv(connectionName='system'):
        tbl.batchUpdate(values, where='$%s=:pkey' % tbl.pkey, pkey=pkey)
        db.commit()


def test_open_records_the_connection_and_the_page(db_sqlite, site):
    db = db_sqlite
    site.currentPage = _page('conn_open', None)
    db.table('adm.connection').connectionLog('open')
    site.currentPage = _page('conn_open', 'page_open', path='/sys/thpage/adm/user',
                             parent_page_id='page_parent', root_page_id='page_root')
    db.table('adm.served_page').pageLog('open')

    connection = _connection(db, 'conn_open')
    assert connection['ip'] == '10.0.0.1'
    assert connection['user_agent'] == 'pytest-agent'
    assert connection['start_ts'] is not None
    assert connection['end_ts'] is None

    page = _served_page(db, 'page_open')
    assert page['connection_id'] == 'conn_open'
    assert page['pagename'] == 'user_page'
    assert page['page_url'] == '/sys/thpage/adm/user'
    assert page['parent_page_id'] == 'page_parent'
    assert page['root_page_id'] == 'page_root'
    assert page['end_ts'] is None


def test_reopening_a_closed_connection_clears_its_end(db_sqlite, site):
    """A connection id logged again is open again, and closes again with
    the pages it opened in the meantime."""
    db = db_sqlite
    _open(db, site, 'conn_again')
    db.table('adm.connection').connectionLog('close', connection_id='conn_again')

    _open(db, site, 'conn_again', 'page_again')

    connection = _connection(db, 'conn_again')
    assert (connection['end_ts'], connection['end_reason']) == (None, None)
    db.table('adm.connection').connectionLog('close', connection_id='conn_again')
    assert _connection(db, 'conn_again')['end_reason'] == 'logout'
    assert _served_page(db, 'page_again')['end_reason'] == 'logout'


def test_the_first_close_wins(db_sqlite, site):
    """A logout already written is not replaced by a later recovery, nor
    an unloaded page by the expiry of its connection."""
    db = db_sqlite
    _open(db, site, 'conn_first', 'page_first')
    logout_ts = T0 + timedelta(minutes=60)
    unload_ts = T0 + timedelta(minutes=50)
    db.table('adm.served_page').closeServedPage('page_first', end_ts=unload_ts, end_reason='unload')
    db.table('adm.connection').closeConnection('conn_first', end_ts=logout_ts, end_reason='logout')

    db.table('adm.connection').closeConnection('conn_first', end_ts=T0, end_reason='aborted')
    db.table('adm.served_page').closeServedPage('page_first', end_ts=T0, end_reason='expired')

    connection = _connection(db, 'conn_first')
    assert (connection['end_reason'], connection['end_ts']) == ('logout', logout_ts)
    page = _served_page(db, 'page_first')
    assert (page['end_reason'], page['end_ts']) == ('unload', unload_ts)


def test_a_logout_racing_the_recovery_is_not_lost(db_sqlite, site):
    """Logout drops the connection from the register, then writes the log:
    a recovery running in between sees a leftover. The logout that follows
    replaces the inferred end, on the connection and on its pages."""
    db = db_sqlite
    _open(db, site, 'conn_race_out', 'page_race_out', 'page_race_unloaded')
    unload_ts = T0 + timedelta(minutes=10)
    db.table('adm.served_page').closeServedPage('page_race_unloaded', end_ts=unload_ts, end_reason='unload')
    site.register.live = {}

    db.table('adm.connection').dropExpiredConnections()
    assert _connection(db, 'conn_race_out')['end_reason'] == 'aborted'
    assert _served_page(db, 'page_race_out')['end_reason'] == 'aborted'
    db.table('adm.connection').connectionLog('close', connection_id='conn_race_out')

    connection = _connection(db, 'conn_race_out')
    assert connection['end_reason'] == 'logout'
    page = _served_page(db, 'page_race_out')
    assert (page['end_reason'], page['end_ts']) == ('logout', connection['end_ts'])
    unloaded = _served_page(db, 'page_race_unloaded')
    assert (unloaded['end_reason'], unloaded['end_ts']) == ('unload', unload_ts)


def test_an_expiry_racing_the_recovery_is_not_lost(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_race_exp', 'page_race_exp')
    site.register.live = {}
    last_ping = T0 + timedelta(days=1)

    db.table('adm.connection').dropExpiredConnections()
    db.table('adm.served_page').pageLog('expire', page_id='page_race_exp', end_ts=last_ping)
    db.table('adm.connection').connectionLog('expire', connection_id='conn_race_exp', end_ts=last_ping)

    connection = _connection(db, 'conn_race_exp')
    assert (connection['end_reason'], connection['end_ts']) == ('expired', last_ping)
    page = _served_page(db, 'page_race_exp')
    assert (page['end_reason'], page['end_ts']) == ('expired', last_ping)


def test_a_connection_opened_during_the_recovery_is_not_closed(db_sqlite, site):
    """A login lands after the log was read: the register, read later,
    has it, so it is not taken for a leftover."""
    db = db_sqlite

    def connections():
        _open(db, site, 'conn_racing')
        return {'conn_racing': {}}

    site.register.connections = connections

    db.table('adm.connection').dropExpiredConnections()

    assert _connection(db, 'conn_racing')['end_ts'] is None


def test_the_recovery_reads_the_log_before_the_register(db_sqlite, site, monkeypatch):
    """Read the other way round, a login between the two reads would be in
    the log and not in the register, and be closed as a leftover."""
    db = db_sqlite
    tbl = db.table('adm.connection')
    reads = []
    query = tbl.query

    def logged_query(*args, **kwargs):
        reads.append('log')
        return query(*args, **kwargs)

    def connections():
        reads.append('register')
        return {}

    monkeypatch.setattr(tbl, 'query', logged_query)
    site.register.connections = connections

    tbl.dropExpiredConnections()

    assert reads[:2] == ['log', 'register']


def test_an_end_never_precedes_the_start_the_log_has(db_sqlite, site):
    """The register knows a connection before its login and a page before
    it is served: with no ping after that, the expiry reports a moment the
    log has not started yet."""
    db = db_sqlite
    _open(db, site, 'conn_early', 'page_early', 'page_early_later', 'page_early_sooner', 'page_early_nostart')
    page_start = T0 + timedelta(minutes=5)
    _stamp(db, 'adm.served_page', 'page_early_later', start_ts=page_start)
    _stamp(db, 'adm.served_page', 'page_early_sooner', start_ts=T0 - timedelta(minutes=20))
    _stamp(db, 'adm.served_page', 'page_early_nostart', start_ts=None)
    before_start = T0 - timedelta(minutes=10)

    db.table('adm.served_page').pageLog('expire', page_id='page_early', end_ts=before_start)
    db.table('adm.connection').connectionLog('expire', connection_id='conn_early', end_ts=before_start)

    assert _served_page(db, 'page_early')['end_ts'] == T0
    assert _connection(db, 'conn_early')['end_ts'] == T0
    # the pages closed with the connection get its end, not the one the register reported
    assert _served_page(db, 'page_early_later')['end_ts'] == page_start
    assert _served_page(db, 'page_early_sooner')['end_ts'] == T0
    assert _served_page(db, 'page_early_nostart')['end_ts'] == T0


def test_logout_closes_the_connection_and_its_open_pages(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_logout', 'page_logout')

    db.table('adm.connection').connectionLog('close', connection_id='conn_logout')

    connection = _connection(db, 'conn_logout')
    assert connection['end_reason'] == 'logout'
    assert connection['end_ts'] is not None
    page = _served_page(db, 'page_logout')
    assert page['end_reason'] == 'logout'
    assert page['end_ts'] == connection['end_ts']


def test_unload_closes_the_page_only(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_unload', 'page_unload')

    db.table('adm.served_page').pageLog('close', page_id='page_unload')

    page = _served_page(db, 'page_unload')
    assert page['end_reason'] == 'unload'
    assert page['end_ts'] is not None
    assert _connection(db, 'conn_unload')['end_ts'] is None


def test_expired_page_ends_at_its_last_activity(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_exp_page', 'page_exp')
    last_activity = T0 + timedelta(minutes=90)

    db.table('adm.served_page').pageLog('expire', page_id='page_exp', end_ts=last_activity)

    page = _served_page(db, 'page_exp')
    assert page['end_reason'] == 'expired'
    assert page['end_ts'] == last_activity
    assert _connection(db, 'conn_exp_page')['end_ts'] is None


def test_expired_connection_ends_at_its_last_activity_with_its_pages(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_exp', 'page_exp_a', 'page_exp_b')
    page_end = T0 + timedelta(minutes=30)
    last_activity = T0 + timedelta(minutes=105)
    db.table('adm.served_page').pageLog('expire', page_id='page_exp_a', end_ts=page_end)

    db.table('adm.connection').connectionLog('expire', connection_id='conn_exp', end_ts=last_activity)

    connection = _connection(db, 'conn_exp')
    assert connection['end_reason'] == 'expired'
    assert connection['end_ts'] == last_activity
    assert _served_page(db, 'page_exp_a')['end_ts'] == page_end
    still_open = _served_page(db, 'page_exp_b')
    assert still_open['end_reason'] == 'expired'
    assert still_open['end_ts'] == last_activity


def test_restart_closes_leftovers_at_the_last_moment_the_log_knows(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_lost', 'page_lost_closed', 'page_lost_open')
    _open(db, site, 'conn_lost_nopages')
    _open(db, site, 'conn_alive', 'page_alive')
    _stamp(db, 'adm.served_page', 'page_lost_closed', start_ts=T0 + timedelta(minutes=5),
           end_ts=T0 + timedelta(minutes=20), end_reason='unload')
    last_seen = T0 + timedelta(minutes=45)
    _stamp(db, 'adm.served_page', 'page_lost_open', start_ts=last_seen)
    site.register.live = {'conn_alive': {}}

    db.table('adm.connection').dropExpiredConnections()

    lost = _connection(db, 'conn_lost')
    assert lost['end_reason'] == 'aborted'
    assert lost['end_ts'] == last_seen
    assert _served_page(db, 'page_lost_closed')['end_ts'] == T0 + timedelta(minutes=20)
    assert _served_page(db, 'page_lost_closed')['end_reason'] == 'unload'
    open_page = _served_page(db, 'page_lost_open')
    assert open_page['end_reason'] == 'aborted'
    assert open_page['end_ts'] == last_seen

    nopages = _connection(db, 'conn_lost_nopages')
    assert nopages['end_reason'] == 'aborted'
    assert nopages['end_ts'] == T0

    assert _connection(db, 'conn_alive')['end_ts'] is None
    assert _served_page(db, 'page_alive')['end_ts'] is None


def test_restart_with_an_empty_register_closes_every_leftover(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_empty_reg')
    site.register.live = {}

    db.table('adm.connection').dropExpiredConnections()

    assert _connection(db, 'conn_empty_reg')['end_reason'] == 'aborted'
    assert db.table('adm.connection').query(where='$end_ts IS NULL').count() == 0


def test_retention_removes_old_connections_with_their_pages(db_sqlite, site):
    db = db_sqlite
    _open(db, site, 'conn_old', 'page_old')
    _open(db, site, 'conn_recent', 'page_recent')
    _stamp(db, 'adm.connection', 'conn_old', start_ts=datetime.now() - timedelta(days=400))
    tbl = db.table('adm.connection')
    policy = tbl.defaultRetentionPolicy
    assert (policy['filter_column'], policy['retention_period']) == ('start_ts', 365)
    assert db.table('adm.served_page').defaultRetentionPolicy['filter_column'] == 'start_ts'

    tbl.executeRetentionPolicy(policy, dry_run=False)

    assert tbl.query(where='$id=:pkey', pkey='conn_old').count() == 0
    assert db.table('adm.served_page').query(where='$page_id=:pkey', pkey='page_old').count() == 0
    assert tbl.query(where='$id=:pkey', pkey='conn_recent').count() == 1
    assert db.table('adm.served_page').query(where='$page_id=:pkey', pkey='page_recent').count() == 1
