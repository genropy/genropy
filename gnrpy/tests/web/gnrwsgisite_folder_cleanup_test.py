"""Unit tests for the on-event unified cleanup (#874).

Three building blocks are exercised:

- ``SiteRegister.claim_cleanup``     atomic check-and-set on ``last_cleanup``
- ``GnrWsgiSite._maybeRunCleanup``   lottery + claim + spawn
- ``GnrWsgiSite._runCleanup``        scan, expire pages, expire connection,
                                     rmtree orphan folders

End-to-end tests that wait on real wall-clock timing are deliberately
avoided: even with aggressive thresholds they would add minutes of
sleep to CI. Multi-worker mutual-exclusion (gunicorn multi-process) is
not realistically exercisable from pytest either.
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrlang import ThreadedDict
from gnr.web.daemon.siteregister import SiteRegister


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


PAGE_END_TS = datetime(2026, 10, 3, 11, 30)
CONNECTION_END_TS = datetime(2026, 10, 3, 11, 45)


class _FakeDaemon:
    def register(self, obj, name):
        # SiteRegister.__init__ calls
        # self.server.daemon.register(self.remotebag_handler, 'RemoteData')
        # We swallow it: no Pyro4 daemon needed for these tests.
        pass


class _FakeServer:
    daemon = _FakeDaemon()


class _FakeRegister:
    """Minimal stand-in for the SiteRegisterClient used by GnrWsgiSite.

    Exposes the four methods the cleanup code path relies on:
    ``claim_cleanup``, ``connections``, ``expire_pages``, ``expire_connection``.
    Each is configurable from the test.
    """

    def __init__(self,
                 claim_returns=True,
                 live_connections=None,
                 expire_pages_result=None,
                 expire_connection_result=None,
                 raises=None):
        self.claim_returns = claim_returns
        self.live_connections = live_connections or {}
        # expire_pages_result is {conn_id: {page_id: last_activity_ts}};
        # expire_connection_result is the last activity ts of the dropped
        # connection (or {conn_id: ts}), None when nothing is dropped.
        self.expire_pages_result = expire_pages_result or {}
        self.expire_connection_result = expire_connection_result
        self.raises = raises or {}
        self.claim_called_with = None
        self.expire_pages_called = []
        self.expire_connection_called = []

    def claim_cleanup(self, min_gap_seconds):
        self.claim_called_with = min_gap_seconds
        if 'claim_cleanup' in self.raises:
            raise self.raises['claim_cleanup']
        return self.claim_returns

    def connections(self):
        if 'connections' in self.raises:
            raise self.raises['connections']
        return {k: {'register_item_id': k, **(v or {})}
                for k, v in self.live_connections.items()}

    def expire_pages(self, connection_id):
        self.expire_pages_called.append(connection_id)
        if 'expire_pages' in self.raises:
            raise self.raises['expire_pages']
        return dict(self.expire_pages_result.get(connection_id, {}))

    def expire_connection(self, connection_id):
        self.expire_connection_called.append(connection_id)
        if 'expire_connection' in self.raises:
            raise self.raises['expire_connection']
        if isinstance(self.expire_connection_result, dict):
            return self.expire_connection_result.get(connection_id)
        return self.expire_connection_result


class _FakeSite:
    """Bag of attributes accessed by the cleanup methods. Methods are
    invoked unbound: ``GnrWsgiSite._method(self_=_FakeSite(...))``."""

    currentDomain = None
    rootDomain = '_main_'
    multidomain = False
    # the real walk, so the tests below exercise it through _runCleanup
    _cleanupConnectionFolders = gws.GnrWsgiSite._cleanupConnectionFolders
    _runCleanupThread = gws.GnrWsgiSite._runCleanupThread
    _logExpired = gws.GnrWsgiSite._logExpired
    _sessionLogEnv = gws.GnrWsgiSite._sessionLogEnv

    def __init__(self, **kwargs):
        self.logged = []
        self.db = _FakeDb()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def pageLog(self, event, page_id=None, end_ts=None):
        self.logged.append(('page', event, page_id, end_ts, self.db.env))

    def connectionLog(self, event, connection_id=None, end_ts=None):
        self.logged.append(('connection', event, connection_id, end_ts, self.db.env))



class _FakeDb:
    """Records the environment the session log is written in, and the
    closing of the connections of the thread."""
    closed = 0
    env = None

    def closeConnection(self):
        self.closed += 1

    @contextmanager
    def tempEnv(self, **kwargs):
        self.env = kwargs
        try:
            yield
        finally:
            self.env = None


ROOT_ENV = dict(storename=None, currentDomain=None)


class _UnusedThread:
    """Stand-in for Thread that records construction without running."""

    def __init__(self):
        self.started = False

    def start(self):
        self.started = True


# ---------------------------------------------------------------------------
# claim_cleanup (siteregister.py)
# ---------------------------------------------------------------------------


def test_claim_cleanup_first_call_succeeds():
    reg = SiteRegister(_FakeServer(), sitename='test')
    # last_cleanup is initialized to 0 in __init__
    assert reg.claim_cleanup(60) is True


def test_claim_cleanup_subsequent_call_within_gap_fails():
    reg = SiteRegister(_FakeServer(), sitename='test')
    assert reg.claim_cleanup(60) is True
    # immediate second call is within the gap
    assert reg.claim_cleanup(60) is False


def test_claim_cleanup_advances_last_cleanup():
    reg = SiteRegister(_FakeServer(), sitename='test')
    before = time.time()
    assert reg.claim_cleanup(60) is True
    assert reg.last_cleanup >= before


def test_claim_cleanup_succeeds_again_after_gap_elapses():
    reg = SiteRegister(_FakeServer(), sitename='test')
    assert reg.claim_cleanup(60) is True
    # Force the field back to "long ago" to simulate the gap elapsing.
    reg.last_cleanup = 0
    assert reg.claim_cleanup(60) is True


# ---------------------------------------------------------------------------
# _maybeRunCleanup (gnrwsgisite.py)
# ---------------------------------------------------------------------------


def test_maybe_lottery_loses(monkeypatch):
    """threshold=0 -> random()*100 (in [0,100)) is always >= 0 -> bail."""
    site = _FakeSite(
        cleanup_threshold=0,
        cleanup_interval_minutes=240,
        register=_FakeRegister(),
    )
    spawned = []
    monkeypatch.setattr(gws, 'Thread',
                        lambda **kw: spawned.append(kw) or _UnusedThread())
    gws.GnrWsgiSite._maybeRunCleanup(site)
    assert spawned == []
    # claim_cleanup never even attempted
    assert site.register.claim_called_with is None


def test_maybe_claim_loses(monkeypatch):
    """threshold=100 -> lottery always wins; claim returns False -> bail."""
    site = _FakeSite(
        cleanup_threshold=100,
        cleanup_interval_minutes=4,
        register=_FakeRegister(claim_returns=False),
    )
    spawned = []
    monkeypatch.setattr(gws, 'Thread',
                        lambda **kw: spawned.append(kw) or _UnusedThread())
    gws.GnrWsgiSite._maybeRunCleanup(site)
    assert spawned == []
    # claim_cleanup was called with cleanup_interval_minutes * 60
    assert site.register.claim_called_with == 4 * 60


def test_maybe_both_win_spawns_thread(monkeypatch):
    """threshold=100 + claim returns True -> Thread spawned and started."""
    runs = []
    site = _FakeSite(
        cleanup_threshold=100,
        cleanup_interval_minutes=4,
        currentDomain='acme',
        register=_FakeRegister(claim_returns=True),
        _runCleanup=lambda **kw: runs.append(kw),
    )
    spawned = []

    def fake_thread(**kw):
        spawned.append(kw)
        return _UnusedThread()

    monkeypatch.setattr(gws, 'Thread', fake_thread)
    gws.GnrWsgiSite._maybeRunCleanup(site)
    assert len(spawned) == 1
    # Thread is configured as a daemon and targets the site's cleanup thread body
    assert spawned[0]['daemon'] is True
    assert spawned[0]['target'] == site._runCleanupThread
    # the thread has no currentDomain of its own: the claimed one travels with it
    assert spawned[0]['kwargs'] == {'domain': 'acme'}


def test_runcleanup_walks_the_handed_domain_and_leaves_the_thread_clean():
    seen = []
    site = _FakeSite(
        _cleanupConnectionFolders=lambda: seen.append(site.currentDomain),
    )
    gws.GnrWsgiSite._runCleanup(site, domain='acme')
    assert seen == ['acme']
    assert site.currentDomain is None


def test_runcleanup_without_a_domain_leaves_the_request_domain_alone():
    """register_explorer calls it inside an rpc: the rest of that rpc still
    talks to the workspace register."""
    seen = []
    site = _FakeSite(
        currentDomain='acme',
        _cleanupConnectionFolders=lambda: seen.append(site.currentDomain),
    )
    gws.GnrWsgiSite._runCleanup(site)
    assert seen == ['acme']
    assert site.currentDomain == 'acme'


def test_runcleanup_resets_the_domain_on_failure():
    def boom():
        raise RuntimeError('cleanup failed')

    site = _FakeSite(_cleanupConnectionFolders=boom)
    try:
        gws.GnrWsgiSite._runCleanup(site, domain='acme')
    except RuntimeError:
        pass
    assert site.currentDomain is None


# ---------------------------------------------------------------------------
# _runCleanup (gnrwsgisite.py)
# ---------------------------------------------------------------------------


def test_runcleanup_without_folder_and_connections_does_nothing(tmp_path):
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path / 'does_not_exist'),
        connection_max_age=600,
        register=_FakeRegister(),
    )
    gws.GnrWsgiSite._runCleanup(site)
    assert site.register.expire_pages_called == []
    assert site.register.expire_connection_called == []
    assert site.logged == []


def test_runcleanup_expires_a_live_connection_that_never_wrote_a_folder(tmp_path):
    """A connection has a folder only once a page of it writes a file:
    without one it expires all the same, pages and connection."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path / 'does_not_exist'),
        connection_max_age=600,
        register=_FakeRegister(
            live_connections={'nofolder': {}},
            expire_pages_result={'nofolder': {'p_stale': PAGE_END_TS}},
            expire_connection_result=CONNECTION_END_TS,
        ),
    )

    gws.GnrWsgiSite._runCleanup(site)

    assert site.logged == [('page', 'expire', 'p_stale', PAGE_END_TS, ROOT_ENV),
                           ('connection', 'expire', 'nofolder', CONNECTION_END_TS, ROOT_ENV)]


def test_runcleanup_walks_each_live_connection_once(tmp_path):
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        register=_FakeRegister(live_connections={'withfolder': {}, 'nofolder': {}}),
    )
    (tmp_path / 'withfolder').mkdir()

    gws.GnrWsgiSite._runCleanup(site)

    assert site.register.expire_pages_called == ['withfolder', 'nofolder']
    assert site.register.expire_connection_called == ['withfolder', 'nofolder']


def test_closed_page_beacon_logs_the_end_and_offers_a_cleanup():
    """The beacon is all a closed page sends: the page leaves the register,
    its end is logged in the store of the domain, the cleanup gets its chance."""
    calls = []
    site = _FakeSite(
        multidomain=True, currentDomain='acme',
        register=SimpleNamespace(drop_page=lambda page_id: calls.append(('drop', page_id))),
        resource_loader=SimpleNamespace(drop_page_class_cache=lambda page_id: calls.append(('cache', page_id))),
        _maybeRunCleanup=lambda: calls.append(('cleanup',)),
    )

    gws.GnrWsgiSite.onClosedPage(site, page_id='p1')

    assert calls == [('drop', 'p1'), ('cache', 'p1'), ('cleanup',)]
    assert site.logged == [('page', 'close', 'p1', None, dict(storename='acme', currentDomain='acme'))]


def test_runcleanup_skips_non_directory_entries(tmp_path):
    """Stray files under _connections/ are left alone."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=0,
        register=_FakeRegister(live_connections={}),
    )
    stray = tmp_path / 'stray_file'
    stray.write_text('hello')
    old_ts = time.time() - 3600
    os.utime(str(stray), (old_ts, old_ts))

    gws.GnrWsgiSite._runCleanup(site)

    assert stray.exists()


def test_runcleanup_drops_orphan_old_folder(tmp_path):
    """Folder not in live connections AND old enough -> rmtree."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=120,
        register=_FakeRegister(live_connections={}),
    )
    (tmp_path / 'orphan_old').mkdir()
    old_ts = time.time() - 200
    os.utime(str(tmp_path / 'orphan_old'), (old_ts, old_ts))

    gws.GnrWsgiSite._runCleanup(site)

    assert not (tmp_path / 'orphan_old').exists()


def test_runcleanup_keeps_orphan_recent_folder(tmp_path):
    """Folder not in live connections but recent -> survives."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=120,
        register=_FakeRegister(live_connections={}),
    )
    (tmp_path / 'orphan_new').mkdir()
    new_ts = time.time() - 30
    os.utime(str(tmp_path / 'orphan_new'), (new_ts, new_ts))

    gws.GnrWsgiSite._runCleanup(site)

    assert (tmp_path / 'orphan_new').exists()


def test_runcleanup_drops_stale_pages_in_live_connection(tmp_path):
    """Live connection: stale pages get their per-page subfolder removed,
    the connection folder itself remains."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        register=_FakeRegister(
            live_connections={'live1': {}},
            expire_pages_result={'live1': {'p_stale': PAGE_END_TS}},
        ),
    )
    conn_dir = tmp_path / 'live1'
    conn_dir.mkdir()
    (conn_dir / 'p_stale').mkdir()
    (conn_dir / 'p_fresh').mkdir()

    gws.GnrWsgiSite._runCleanup(site)

    assert conn_dir.exists()
    assert (conn_dir / 'p_fresh').exists()
    assert not (conn_dir / 'p_stale').exists()
    assert site.logged == [('page', 'expire', 'p_stale', PAGE_END_TS, ROOT_ENV)]


def test_runcleanup_drops_stale_connection_and_folder(tmp_path):
    """Live connection that expire_connection drops -> rmtree the folder."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        register=_FakeRegister(
            live_connections={'live1': {}},
            expire_connection_result=CONNECTION_END_TS,
        ),
    )
    conn_dir = tmp_path / 'live1'
    conn_dir.mkdir()
    (conn_dir / 'p1').mkdir()

    gws.GnrWsgiSite._runCleanup(site)

    assert not conn_dir.exists()
    assert site.logged == [('connection', 'expire', 'live1', CONNECTION_END_TS, ROOT_ENV)]


def test_runcleanup_survives_a_failing_session_log(tmp_path, caplog):
    """The log write fails for one connection: the error is logged and
    the walk goes on to the next one."""
    logged = []

    def failing_log(connection_id, stale_pages, connection_end_ts):
        if connection_id == 'live1':
            raise RuntimeError('db_boom')
        logged.append(connection_id)

    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        register=_FakeRegister(
            live_connections={'live1': {}, 'live2': {}},
            expire_connection_result=CONNECTION_END_TS,
        ),
        _logExpired=failing_log,
    )
    (tmp_path / 'live1').mkdir()
    (tmp_path / 'live2').mkdir()

    with caplog.at_level(logging.ERROR, logger='gnr.web'):
        gws.GnrWsgiSite._runCleanup(site)

    assert logged == ['live2']
    assert not (tmp_path / 'live1').exists()
    assert not (tmp_path / 'live2').exists()
    assert any('Session log update failed for live1' in r.getMessage()
               for r in caplog.records)


def test_runcleanup_writes_the_session_log_in_the_store_of_the_domain(tmp_path):
    """The cleanup thread has no page: the db is pointed at the store of
    the workspace whose register is being walked."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        multidomain=True,
        register=_FakeRegister(
            live_connections={'live1': {}},
            expire_pages_result={'live1': {'p1': PAGE_END_TS}},
            expire_connection_result=CONNECTION_END_TS,
        ),
    )
    (tmp_path / 'live1').mkdir()

    gws.GnrWsgiSite._runCleanup(site, domain='acme')

    acme_env = dict(storename='acme', currentDomain='acme')
    assert site.logged == [('page', 'expire', 'p1', PAGE_END_TS, acme_env),
                           ('connection', 'expire', 'live1', CONNECTION_END_TS, acme_env)]


def test_runcleanup_writes_the_root_domain_log_in_the_root_store(tmp_path):
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        multidomain=True,
        register=_FakeRegister(
            live_connections={'live1': {}},
            expire_connection_result=CONNECTION_END_TS,
        ),
    )
    (tmp_path / 'live1').mkdir()

    gws.GnrWsgiSite._runCleanup(site, domain='_main_')

    assert site.logged == [('connection', 'expire', 'live1', CONNECTION_END_TS,
                            dict(storename=None, currentDomain='_main_'))]


class _PreferenceSite(_FakeSite):
    """A site whose adm preference differs by domain, read through the
    real property and the real recovery entry point."""
    multidomain = True
    connectionLogEnabled = gws.GnrWsgiSite.connectionLogEnabled
    checkPendingConnection = gws.GnrWsgiSite.checkPendingConnection

    def __init__(self, preferences, **kwargs):
        super().__init__(**kwargs)
        self.preferences = preferences
        self.preference_reads = []
        self._connectionLogEnabled = {}
        self.db.package = lambda pkg: True
        self.db.table = lambda name: self

    def getPreference(self, path, pkg=None):
        self.preference_reads.append(self.db.env)
        return self.preferences.get(self.db.env['storename'])

    def dropExpiredConnections(self):
        self.logged.append(('recover', self.currentDomain, self.db.env))


def test_connection_log_preference_is_read_once_for_each_domain():
    site = _PreferenceSite({None: 'A', 'acme': None}, currentDomain='_main_')
    assert site.connectionLogEnabled == 'A'
    site.currentDomain = 'acme'
    assert site.connectionLogEnabled is None
    site.preferences['acme'] = 'C'
    assert site.connectionLogEnabled is None
    site.currentDomain = '_main_'
    assert site.connectionLogEnabled == 'A'
    assert site.preference_reads == [dict(storename=None, currentDomain='_main_'),
                                     dict(storename='acme', currentDomain='acme')]


class _DomainSite(_PreferenceSite):
    """A site whose currentDomain is the real one, bound to the thread."""
    currentDomain = gws.GnrWsgiSite.currentDomain

    def __init__(self, preferences, **kwargs):
        self._currentDomains = ThreadedDict()
        super().__init__(preferences, **kwargs)


def _root_proxy(monkeypatch, site, client=None):
    """The proxy of the root domain, with a client that records the domain
    its constructor sees."""
    built = []

    def build(site):
        built.append(site.currentDomain)
        return client() if client else 'client'

    monkeypatch.setattr(gws, 'SiteRegisterClient', build)
    return gws.GnrDomainProxy(SimpleNamespace(site=site), '_main_'), built


def test_register_reached_first_from_a_workspace_is_built_as_its_own_domain(monkeypatch):
    """main_register can be reached first from a request of a workspace:
    neither the client nor the recovery of the root domain may see it."""
    site = _DomainSite({None: 'A', 'acme': 'A'}, currentDomain='acme')
    proxy, built = _root_proxy(monkeypatch, site)

    assert proxy.register == 'client'

    assert built == ['_main_']
    assert site.logged == [('recover', '_main_', dict(storename=None, currentDomain='_main_'))]
    assert site.currentDomain == 'acme'
    assert proxy.register == 'client'
    assert built == ['_main_']


def test_register_creation_leaves_a_thread_without_domain_as_it_was(monkeypatch):
    site = _DomainSite({None: 'A'})
    proxy, built = _root_proxy(monkeypatch, site)

    proxy.register

    assert built == ['_main_']
    assert site._currentDomains.get() is None


def test_register_creation_gives_the_domain_back_on_failure(monkeypatch):
    def failing_client():
        raise RuntimeError('daemon down')

    site = _DomainSite({None: 'A', 'acme': 'A'}, currentDomain='acme')
    proxy, built = _root_proxy(monkeypatch, site, client=failing_client)

    try:
        proxy.register
    except RuntimeError:
        pass

    assert built == ['_main_']
    assert site.logged == []
    assert site.currentDomain == 'acme'


def test_recovery_is_skipped_where_the_log_is_off():
    site = _PreferenceSite({None: 'A', 'acme': None}, currentDomain='acme')

    site.checkPendingConnection()

    assert site.logged == []


def test_cleanup_thread_closes_its_db_connections():
    runs = []
    site = _FakeSite(_runCleanup=lambda **kw: runs.append(kw))
    gws.GnrWsgiSite._runCleanupThread(site, domain='acme')
    assert runs == [{'domain': 'acme'}]
    assert site.db.closed == 1


def test_cleanup_thread_closes_its_db_connections_on_failure():
    def boom(**kw):
        raise RuntimeError('cleanup failed')

    site = _FakeSite(_runCleanup=boom)
    try:
        gws.GnrWsgiSite._runCleanupThread(site, domain='acme')
    except RuntimeError:
        pass
    assert site.db.closed == 1


def test_runcleanup_logs_summary(tmp_path, caplog):
    """When something is dropped, an INFO line summarises the counts."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=120,
        register=_FakeRegister(
            live_connections={'live1': {}},
            expire_pages_result={'live1': {'p1': PAGE_END_TS}},
        ),
    )
    conn_dir = tmp_path / 'live1'
    conn_dir.mkdir()
    (conn_dir / 'p1').mkdir()
    # also an orphan to bump the folder counter
    (tmp_path / 'orphan_old').mkdir()
    os.utime(str(tmp_path / 'orphan_old'),
             (time.time() - 600, time.time() - 600))

    with caplog.at_level(logging.INFO, logger='gnr.web'):
        gws.GnrWsgiSite._runCleanup(site)

    summaries = [r for r in caplog.records if 'Cleanup:' in r.getMessage()]
    assert len(summaries) == 1
    msg = summaries[0].getMessage()
    assert 'dropped 1 pages' in msg
    assert '0 connections' in msg
    assert 'removed 1 orphan folders' in msg


def test_runcleanup_no_log_when_nothing_dropped(tmp_path, caplog):
    """No log line when the pass had nothing to do."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=120,
        register=_FakeRegister(live_connections={}),
    )

    with caplog.at_level(logging.INFO, logger='gnr.web'):
        gws.GnrWsgiSite._runCleanup(site)

    summaries = [r for r in caplog.records if 'Cleanup:' in r.getMessage()]
    assert summaries == []


def test_runcleanup_swallows_connections_errors(tmp_path, caplog):
    """If register.connections() raises, the error is logged and the
    cleanup pass exits cleanly."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=120,
        register=_FakeRegister(raises={'connections': RuntimeError('boom')}),
    )

    with caplog.at_level(logging.ERROR, logger='gnr.web'):
        gws.GnrWsgiSite._runCleanup(site)

    assert any('Cleanup failed reading register' in r.getMessage()
               for r in caplog.records)


def test_runcleanup_swallows_expire_pages_errors(tmp_path, caplog):
    """If expire_pages() raises for a connection, the error is logged
    and the loop continues to expire_connection for the same one."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        register=_FakeRegister(
            live_connections={'live1': {}},
            raises={'expire_pages': RuntimeError('pages_boom')},
            expire_connection_result=CONNECTION_END_TS,
        ),
    )
    conn_dir = tmp_path / 'live1'
    conn_dir.mkdir()

    with caplog.at_level(logging.ERROR, logger='gnr.web'):
        gws.GnrWsgiSite._runCleanup(site)

    assert any('expire_pages failed' in r.getMessage()
               for r in caplog.records)
    # expire_connection still ran, dropped, rmtree happened
    assert not conn_dir.exists()


def test_maybe_swallows_claim_cleanup_errors(monkeypatch, caplog):
    """If register.claim_cleanup() raises (e.g. Pyro CommunicationError
    when the daemon is down), the cleanup pass is silently skipped:
    the exception is logged and no Thread is spawned. This prevents a
    failed RPC from turning a page-close into a 500 for the client."""
    site = _FakeSite(
        cleanup_threshold=100,
        cleanup_interval_minutes=4,
        register=_FakeRegister(
            raises={'claim_cleanup': RuntimeError('daemon unreachable')},
        ),
    )
    spawned = []
    monkeypatch.setattr(gws, 'Thread',
                        lambda **kw: spawned.append(kw) or _UnusedThread())

    with caplog.at_level(logging.ERROR, logger='gnr.web'):
        gws.GnrWsgiSite._maybeRunCleanup(site)

    assert spawned == []
    assert any('claim_cleanup failed' in r.getMessage()
               for r in caplog.records)


def test_maybe_real_thread_runs_cleanup():
    """End-to-end with a real Thread: when both gates clear, the
    spawned thread actually invokes _runCleanup. Catches regressions
    where the spawn idiom would silently change to .run() (sync) or
    the target is wired wrong."""
    started = threading.Event()
    captured_ident = []

    def _capture(**kw):
        captured_ident.append(threading.get_ident())
        started.set()

    site = _FakeSite(
        cleanup_threshold=100,
        cleanup_interval_minutes=4,
        register=_FakeRegister(claim_returns=True),
        _runCleanup=_capture,
    )

    gws.GnrWsgiSite._maybeRunCleanup(site)

    assert started.wait(timeout=5), "spawned thread did not run within 5s"
    assert len(captured_ident) == 1
    # The cleanup ran in a different thread than the test's main thread.
    assert captured_ident[0] != threading.get_ident()
