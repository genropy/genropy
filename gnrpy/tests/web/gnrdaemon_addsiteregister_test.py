"""Regression test for #1031.

``GnrDaemon.addSiteRegister`` raised ``UnboundLocalError`` on the
"site already registered" path, because ``sitename`` was derived only
inside the ``if`` branch while being referenced in the ``else`` branch.

A real ``GnrDaemon`` instance is not used here: its ``__init__`` starts a
``multiprocessing.Manager`` and the "already registered" branch touches
no other daemon state, so the method is exercised unbound against a
minimal fake, the same technique used in
``gnrwsgisite_folder_cleanup_test.py``.
"""

import logging

import pytest

from gnr.web import gnrtask
from gnr.web.daemon import handler
from gnr.web.daemon.handler import GnrDaemon


class _FakeDaemon:
    """Bag of attributes accessed by the "already registered" branch."""

    def __init__(self, siteregisters):
        self.siteregisters = siteregisters


def test_addsiteregister_already_registered_does_not_raise(caplog):
    fake = _FakeDaemon(siteregisters={'asp4': {}})

    with caplog.at_level(logging.INFO, logger='gnr.web'):
        GnrDaemon.addSiteRegister(fake, 'asp4')

    assert any('Site asp4 already existing' in r.getMessage()
               for r in caplog.records)


def test_addsiteregister_already_registered_with_domain_suffix(caplog):
    """domainIdentifier can carry a '|domain' suffix; the logged
    sitename must be the part before the pipe."""
    fake = _FakeDaemon(siteregisters={'asp4|example.com': {}})

    with caplog.at_level(logging.INFO, logger='gnr.web'):
        GnrDaemon.addSiteRegister(fake, 'asp4|example.com')

    assert any('Site asp4 already existing' in r.getMessage()
               for r in caplog.records)


class _FakeChild:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.terminated = False
        self.daemon = False

    def start(self):
        self.started = True

    def is_alive(self):
        return False

    def terminate(self):
        self.terminated = True


class _FakeSchedulerHandler(_FakeChild):
    created = []

    def __init__(self, parent, sitename=None):
        super().__init__(sitename=sitename)
        self.parent = parent
        self.sitename = sitename
        self.checked = False
        _FakeSchedulerHandler.created.append(self)

    def checkSchedulerProcess(self):
        self.checked = True


class _FakeNewSiteDaemon(_FakeDaemon):
    """Bag of attributes accessed when a site register is added or stopped
    (#1557, #1567)."""

    startTaskScheduler = GnrDaemon.startTaskScheduler
    stopTaskScheduler = GnrDaemon.stopTaskScheduler

    def __init__(self):
        super().__init__(siteregisters={})
        self.siteregisters_process = {}
        self.task_schedulers = {}
        self.sockets = None
        self.main_uri = 'PYRO:daemon@localhost:40404'
        self.host = 'localhost'
        self.hmac_key = 'key'

    def hasSysPackageAndIsPrimary(self, sitename):
        return True

    def startServiceProcesses(self, domainIdentifier, sitedict=None):
        pass


@pytest.fixture
def new_site_daemon(monkeypatch):
    _FakeSchedulerHandler.created = []
    monkeypatch.setattr(gnrtask, 'USE_ASYNC_TASKS', False)
    monkeypatch.setattr(handler, 'Process', _FakeChild)
    monkeypatch.setattr(handler, 'GnrTaskSchedulerHandler', _FakeSchedulerHandler)
    return _FakeNewSiteDaemon()


def test_addsiteregister_supervises_the_legacy_task_scheduler(new_site_daemon):
    fake = new_site_daemon

    GnrDaemon.addSiteRegister(fake, 'asp4|example.com')

    scheduler = fake.task_schedulers['asp4']
    assert isinstance(scheduler, _FakeSchedulerHandler)
    assert scheduler.started
    assert scheduler.parent is fake
    assert scheduler.sitename == 'asp4'
    assert 'task_scheduler' not in fake.siteregisters_process['asp4|example.com']


def test_one_task_scheduler_per_site_across_workspaces(new_site_daemon):
    fake = new_site_daemon

    GnrDaemon.addSiteRegister(fake, 'asp4')
    GnrDaemon.addSiteRegister(fake, 'asp4|ws1')
    GnrDaemon.addSiteRegister(fake, 'other')

    assert [s.sitename for s in _FakeSchedulerHandler.created] == ['asp4', 'other']


def test_addsiteregister_revives_a_dead_site_scheduler(new_site_daemon):
    fake = new_site_daemon
    GnrDaemon.addSiteRegister(fake, 'asp4')
    scheduler = fake.task_schedulers['asp4']

    GnrDaemon.addSiteRegister(fake, 'asp4|ws1')

    assert scheduler.checked
    assert _FakeSchedulerHandler.created == [scheduler]


def test_site_scheduler_outlives_a_workspace_and_ends_with_the_last(new_site_daemon):
    fake = new_site_daemon
    GnrDaemon.addSiteRegister(fake, 'asp4')
    GnrDaemon.addSiteRegister(fake, 'asp4|ws1')
    scheduler = fake.task_schedulers['asp4']

    GnrDaemon.onRegisterStop(fake, 'asp4|ws1')
    assert not scheduler.terminated
    assert fake.task_schedulers['asp4'] is scheduler

    GnrDaemon.onRegisterStop(fake, 'asp4')
    assert scheduler.terminated
    assert 'asp4' not in fake.task_schedulers


def test_register_stop_terminates_a_child_reported_not_alive(new_site_daemon):
    """A supervisor reports not alive while its child is down: stopping the
    register must still end it, or its monitor restarts an orphan process."""
    fake = new_site_daemon
    supervisor = _FakeChild()
    register = _FakeChild()
    fake.siteregisters = {'asp4': {'sitename': 'asp4'}}
    fake.siteregisters_process = {'asp4': {'register': register,
                                           'cron': supervisor}}

    GnrDaemon.onRegisterStop(fake, 'asp4')

    assert supervisor.terminated
    assert not register.terminated
    assert 'asp4' not in fake.siteregisters_process
