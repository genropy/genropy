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
import time

import gnr.web.gnrwsgisite as gws
from gnr.web.daemon.siteregister import SiteRegister


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


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
                 expire_connection_result=False,
                 raises=None):
        self.claim_returns = claim_returns
        self.live_connections = live_connections or {}
        # expire_pages_result is either a list (returned for any conn)
        # or a dict {conn_id: [page_ids]}.
        self.expire_pages_result = expire_pages_result or []
        self.expire_connection_result = expire_connection_result
        self.raises = raises or {}
        self.claim_called_with = None
        self.expire_pages_called = []
        self.expire_connection_called = []

    def claim_cleanup(self, min_gap_seconds):
        self.claim_called_with = min_gap_seconds
        return self.claim_returns

    def connections(self):
        if 'connections' in self.raises:
            raise self.raises['connections']
        return [{'register_item_id': k, **(v or {})}
                for k, v in self.live_connections.items()]

    def expire_pages(self, connection_id):
        self.expire_pages_called.append(connection_id)
        if 'expire_pages' in self.raises:
            raise self.raises['expire_pages']
        if isinstance(self.expire_pages_result, dict):
            return list(self.expire_pages_result.get(connection_id, []))
        return list(self.expire_pages_result)

    def expire_connection(self, connection_id):
        self.expire_connection_called.append(connection_id)
        if 'expire_connection' in self.raises:
            raise self.raises['expire_connection']
        if isinstance(self.expire_connection_result, dict):
            return self.expire_connection_result.get(connection_id, False)
        return self.expire_connection_result


class _FakeSite:
    """Bag of attributes accessed by the cleanup methods. Methods are
    invoked unbound: ``GnrWsgiSite._method(self_=_FakeSite(...))``."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


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
        register=_FakeRegister(claim_returns=True),
        _runCleanup=lambda: runs.append(True),
    )
    spawned = []

    def fake_thread(**kw):
        spawned.append(kw)
        return _UnusedThread()

    monkeypatch.setattr(gws, 'Thread', fake_thread)
    gws.GnrWsgiSite._maybeRunCleanup(site)
    assert len(spawned) == 1
    # Thread is configured as a daemon and targets the site's _runCleanup
    assert spawned[0]['daemon'] is True
    assert spawned[0]['target'] is site._runCleanup


# ---------------------------------------------------------------------------
# _runCleanup (gnrwsgisite.py)
# ---------------------------------------------------------------------------


def test_runcleanup_skips_when_folder_missing(tmp_path):
    """Bail immediately when allConnectionsFolder doesn't exist."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path / 'does_not_exist'),
        connection_max_age=600,
        register=_FakeRegister(),
    )
    # Should not raise and should not call register methods.
    gws.GnrWsgiSite._runCleanup(site)
    assert site.register.expire_pages_called == []
    assert site.register.expire_connection_called == []


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
            expire_pages_result={'live1': ['p_stale']},
            expire_connection_result=False,
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


def test_runcleanup_drops_stale_connection_and_folder(tmp_path):
    """Live connection that expire_connection drops -> rmtree the folder."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=600,
        register=_FakeRegister(
            live_connections={'live1': {}},
            expire_pages_result=[],
            expire_connection_result=True,
        ),
    )
    conn_dir = tmp_path / 'live1'
    conn_dir.mkdir()
    (conn_dir / 'p1').mkdir()

    gws.GnrWsgiSite._runCleanup(site)

    assert not conn_dir.exists()


def test_runcleanup_logs_summary(tmp_path, caplog):
    """When something is dropped, an INFO line summarises the counts."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        connection_max_age=120,
        register=_FakeRegister(
            live_connections={'live1': {}},
            expire_pages_result={'live1': ['p1']},
            expire_connection_result=False,
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
            expire_connection_result=True,
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
