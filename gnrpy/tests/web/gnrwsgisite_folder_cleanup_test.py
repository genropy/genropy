"""Unit tests for the on-event connection-folder cleanup (#874).

These tests cover the three building blocks of the new cleanup pipeline:

- ``SiteRegister.claim_cleanup``     — atomic check-and-set on ``last_cleanup``
- ``GnrWsgiSite._maybeRunFolderCleanup`` — lottery + claim + spawn
- ``GnrWsgiSite._runFolderCleanup``  — scan, skip live, skip recent, rmtree

We deliberately avoid end-to-end tests that wait on real wall-clock timing
(e.g. waiting for the production defaults of ``folder_purge_interval_minutes=240``
and ``folder_purge_min_age_minutes=120`` to elapse). Even with aggressive
test-only thresholds (e.g. 20s/40s) such tests would add minutes of sleep to the
CI suite, which is not acceptable. Multi-worker mutual-exclusion (gunicorn
multi-process) is also not realistically exercisable from pytest. End-to-end
manual verification is documented in the PR description (test scenario "T3
Forced cleanup stress test").
"""

import os
import time

import gnr.web.gnrwsgisite as gws
from gnr.web.daemon.siteregister import SiteRegister


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeDaemon:
    def register(self, obj, name):
        # SiteRegister.__init__ calls server.daemon.register(self.remotebag_handler, 'RemoteData')
        # We swallow it: no Pyro4 daemon needed for these tests.
        pass


class _FakeServer:
    daemon = _FakeDaemon()


class _FakeRegister:
    """Minimal stand-in for the SiteRegisterClient used by GnrWsgiSite."""

    def __init__(self, claim_returns=True, live_connections=None):
        self.claim_returns = claim_returns
        self.live_connections = live_connections or {}
        self.claim_called_with = None

    def claim_cleanup(self, min_gap_seconds):
        self.claim_called_with = min_gap_seconds
        return self.claim_returns

    def connections(self):
        return self.live_connections


class _FakeSite:
    """Minimal object with the attributes ``GnrWsgiSite._maybeRunFolderCleanup``
    and ``GnrWsgiSite._runFolderCleanup`` access. Methods are invoked as
    ``GnrWsgiSite._method(self_=fake)`` to bypass ``__init__``.
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# claim_cleanup (siteregister.py)
# ---------------------------------------------------------------------------


def test_claim_cleanup_atomicity():
    reg = SiteRegister(_FakeServer(), sitename='test')
    reg.last_cleanup = 0  # force "long ago" so first claim succeeds
    assert reg.claim_cleanup(60) is True
    # immediate second call is within the gap → False
    assert reg.claim_cleanup(60) is False
    # forcing the field back to 0 simulates the gap elapsing
    reg.last_cleanup = 0
    assert reg.claim_cleanup(60) is True


def test_claim_cleanup_advances_timestamp():
    reg = SiteRegister(_FakeServer(), sitename='test')
    reg.last_cleanup = 0
    before = time.time()
    assert reg.claim_cleanup(60) is True
    # the field has been advanced to "now"
    assert reg.last_cleanup >= before


# ---------------------------------------------------------------------------
# _maybeRunFolderCleanup (gnrwsgisite.py)
# ---------------------------------------------------------------------------


def test_maybe_lottery_loses(monkeypatch):
    """threshold=0 → random()*100 (0..100) is always >= 0 → returns immediately."""
    site = _FakeSite(
        folder_purge_threshold=0,
        folder_purge_interval_minutes=240,
        register=_FakeRegister(),
    )
    spawned = []
    monkeypatch.setattr(gws, 'Thread', lambda **kw: spawned.append(kw) or _UnusedThread())
    gws.GnrWsgiSite._maybeRunFolderCleanup(site)
    assert spawned == []
    assert site.register.claim_called_with is None  # claim never even attempted


def test_maybe_claim_loses(monkeypatch):
    """threshold=100 → lottery always wins; claim returns False → no spawn."""
    site = _FakeSite(
        folder_purge_threshold=100,
        folder_purge_interval_minutes=4,
        register=_FakeRegister(claim_returns=False),
    )
    spawned = []
    monkeypatch.setattr(gws, 'Thread', lambda **kw: spawned.append(kw) or _UnusedThread())
    gws.GnrWsgiSite._maybeRunFolderCleanup(site)
    assert spawned == []
    # claim WAS called with the right interval (in seconds)
    assert site.register.claim_called_with == 4 * 60


def test_maybe_both_win_spawns_thread(monkeypatch):
    """threshold=100 + claim_returns=True → Thread spawned with daemon=True."""
    site = _FakeSite(
        folder_purge_threshold=100,
        folder_purge_interval_minutes=4,
        register=_FakeRegister(claim_returns=True),
    )
    # Provide a sentinel _runFolderCleanup so the bound-method lookup succeeds.
    sentinel_calls = []
    site._runFolderCleanup = lambda: sentinel_calls.append(True)

    spawned = []

    class _CapturingThread:
        def __init__(self, **kw):
            spawned.append(kw)

        def start(self):
            pass

    monkeypatch.setattr(gws, 'Thread', _CapturingThread)
    gws.GnrWsgiSite._maybeRunFolderCleanup(site)
    assert len(spawned) == 1
    assert spawned[0]['daemon'] is True
    assert spawned[0]['target'] is site._runFolderCleanup


# ---------------------------------------------------------------------------
# _runFolderCleanup (gnrwsgisite.py)
# ---------------------------------------------------------------------------


def test_runfoldercleanup_skips_live_and_recent(tmp_path):
    """Removes only orphans (not in register) older than min_age."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        folder_purge_min_age_minutes=2,  # 120s
        register=_FakeRegister(live_connections={'live1': {}}),
    )
    (tmp_path / 'live1').mkdir()         # live and old → must survive (live wins)
    (tmp_path / 'orphan_old').mkdir()    # orphan and old → must be removed
    (tmp_path / 'orphan_new').mkdir()    # orphan and recent → must survive (age wins)

    old_ts = time.time() - 200  # > 120s
    new_ts = time.time() - 30   # < 120s
    os.utime(str(tmp_path / 'live1'), (old_ts, old_ts))
    os.utime(str(tmp_path / 'orphan_old'), (old_ts, old_ts))
    os.utime(str(tmp_path / 'orphan_new'), (new_ts, new_ts))

    gws.GnrWsgiSite._runFolderCleanup(site)

    assert (tmp_path / 'live1').exists()
    assert not (tmp_path / 'orphan_old').exists()
    assert (tmp_path / 'orphan_new').exists()


def test_runfoldercleanup_ignores_files(tmp_path):
    """A stray non-directory entry under _connections is left alone."""
    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        folder_purge_min_age_minutes=0,
        register=_FakeRegister(live_connections={}),
    )
    stray = tmp_path / 'stray_file'
    stray.write_text('hello')
    old_ts = time.time() - 3600
    os.utime(str(stray), (old_ts, old_ts))

    gws.GnrWsgiSite._runFolderCleanup(site)

    assert stray.exists()


def test_runfoldercleanup_swallows_register_errors(tmp_path, monkeypatch):
    """If register.connections() raises, the error is logged, not propagated."""
    class _BrokenRegister:
        def connections(self):
            raise RuntimeError('register down')

    site = _FakeSite(
        allConnectionsFolder=str(tmp_path),
        folder_purge_min_age_minutes=0,
        register=_BrokenRegister(),
    )
    # Should not raise:
    gws.GnrWsgiSite._runFolderCleanup(site)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _UnusedThread:
    """Returned by lambdas that capture Thread kwargs but never start a thread."""

    def start(self):
        pass
