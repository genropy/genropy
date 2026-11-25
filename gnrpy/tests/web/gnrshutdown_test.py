"""The shutdown announced to the connected users (#1903).

The announcement goes through a real SiteRegister and the ServerStore the
command line uses against the daemon, so what is written is what the ping reads.
"""

import os
from datetime import datetime, timedelta

import pytest

from gnr.web import gnrshutdown
from gnr.web.daemon.siteregister import SiteRegister
from gnr.web.daemon.siteregister_client import ServerStore
from gnr.web.gnrshutdown import (SHUTDOWN_GRACE_SECONDS, SHUTDOWN_KEY, announce_shutdown, cancel_shutdown,
                                 parse_delay, shutdown_notice)
from gnr.web.gnrwsgisite import GnrWsgiSite


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


def _global_store():
    register = SiteRegister(_FakeServer(), sitename='testsite')
    register.setConfiguration(None)
    return ServerStore(register, register_name='global', register_item_id='*')


def test_module_under_test():
    checkout = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    assert gnrshutdown.__file__.startswith(checkout + os.sep)


@pytest.mark.parametrize('text,seconds', [
    ('90', 90), ('90s', 90), ('5m', 300), ('2h', 7200), (' 3 m ', 180),
])
def test_parse_delay(text, seconds):
    assert parse_delay(text) == seconds


@pytest.mark.parametrize('text', ['', None, '5x', 'm', '-5m', '1.5m', '0', '0m'])
def test_parse_delay_rejects(text):
    with pytest.raises(ValueError):
        parse_delay(text)


def test_announce_then_notice():
    store = _global_store()
    deadline = announce_shutdown(store, 300, 'Upgrading the application')
    entry = store.getItem(SHUTDOWN_KEY)
    assert entry == dict(deadline=deadline, reason='Upgrading the application')
    notice = shutdown_notice(entry, now=deadline - timedelta(seconds=120.5))
    assert notice == dict(reason='Upgrading the application', seconds_left=120.5)


def test_cancel_clears_the_announcement():
    store = _global_store()
    announce_shutdown(store, 300, 'Upgrading the application')
    assert cancel_shutdown(store) is True
    assert shutdown_notice(store.getItem(SHUTDOWN_KEY)) is None
    assert cancel_shutdown(store) is False


def test_cancel_without_announcement():
    assert cancel_shutdown(_global_store()) is False


def test_past_deadline_keeps_zero_for_the_grace_period():
    deadline = datetime.now()
    entry = dict(deadline=deadline, reason='late')
    for elapsed in (0, 1, SHUTDOWN_GRACE_SECONDS - 1):
        notice = shutdown_notice(entry, now=deadline + timedelta(seconds=elapsed))
        assert notice == dict(reason='late', seconds_left=0)
    assert _cancel_stored(entry) is False


def test_expired_announcement_is_ignored():
    deadline = datetime.now()
    entry = dict(deadline=deadline, reason='stale')
    assert shutdown_notice(entry, now=deadline + timedelta(seconds=SHUTDOWN_GRACE_SECONDS)) is None
    assert shutdown_notice(entry, now=deadline + timedelta(days=1)) is None


def _cancel_stored(entry):
    store = _global_store()
    with store as global_store:
        global_store.setItem(SHUTDOWN_KEY, entry)
    return cancel_shutdown(store)


class _Site:
    """The real ``shutdownNotice`` of the site on a real global store."""

    shutdownNotice = GnrWsgiSite.shutdownNotice
    SHUTDOWN_CACHE_SECONDS = GnrWsgiSite.SHUTDOWN_CACHE_SECONDS
    _shutdown_entry = GnrWsgiSite._shutdown_entry

    def __init__(self):
        self.store = _global_store()
        self.reads = 0
        self.main_register = self

    def globalStore(self, triggered=False):
        self.reads += 1
        return self.store


def test_site_without_announcement():
    assert _Site().shutdownNotice() is None


def test_site_announcement_reaches_the_ping():
    site = _Site()
    announce_shutdown(site.store, 120, 'Upgrading the application')
    notice = site.shutdownNotice()
    assert notice['reason'] == 'Upgrading the application'
    assert 119 <= notice['seconds_left'] <= 120


def test_site_reads_the_register_once_per_period(monkeypatch):
    site = _Site()
    announce_shutdown(site.store, 120, 'Upgrading the application')
    clock = [1000.0]
    monkeypatch.setattr('gnr.web.gnrwsgisite.time', lambda: clock[0])
    assert site.shutdownNotice()
    cancel_shutdown(site.store)
    clock[0] += site.SHUTDOWN_CACHE_SECONDS
    assert site.shutdownNotice()
    assert site.reads == 1
    clock[0] += 1
    assert site.shutdownNotice() is None
    assert site.reads == 2
