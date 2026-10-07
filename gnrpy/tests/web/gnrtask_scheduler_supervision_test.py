"""The legacy task scheduler survives a failed pass and is supervised by the
daemon (#1557).

The loop runs the real ``GnrTaskScheduler.start`` with a pass that raises the
way a lost database connection does; the supervisor runs the real
``GnrTaskSchedulerHandler`` with the child process replaced, since starting
the scheduler for real needs an instance and a database.
"""

import logging

import pytest

from gnr.web import gnrtask
from gnr.web.daemon import processes


class _StopLoop(Exception):
    pass


class _FakeDb:
    def __init__(self):
        self.closed = 0

    def closeConnection(self):
        self.closed += 1


class _FlakyScheduler:
    start = gnrtask.GnrTaskScheduler.start

    def __init__(self, failures):
        self.db = _FakeDb()
        self.interval = 60
        self.failures = failures
        self.passes = 0

    def writeTaskExecutions(self):
        self.passes += 1
        if self.passes <= self.failures:
            raise RuntimeError('server closed the connection unexpectedly')


def test_failed_pass_is_logged_and_retried(monkeypatch, caplog):
    scheduler = _FlakyScheduler(failures=1)
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise _StopLoop()

    monkeypatch.setattr(gnrtask, 'sleep', fake_sleep)

    with caplog.at_level(logging.ERROR, logger='gnr.web'):
        with pytest.raises(_StopLoop):
            scheduler.start()

    assert scheduler.passes == 2
    assert scheduler.db.closed == 2
    assert sleeps == [60, 60]
    assert any('server closed the connection' in r.exc_text
               for r in caplog.records if r.exc_text)


class _FakeProcess:
    created = []

    def __init__(self, name=None, target=None, args=None, **kwargs):
        self.name = name
        self.target = target
        self.args = args
        self.daemon = False
        self.alive = False
        self.exitcode = None
        self.terminated = False
        _FakeProcess.created.append(self)

    def start(self):
        self.alive = True

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminated = True
        self.alive = False


@pytest.fixture
def handler(monkeypatch):
    _FakeProcess.created = []
    monkeypatch.setattr(processes, 'Process', _FakeProcess)
    monkeypatch.setattr(processes.threading.Thread, 'start', lambda self: None)
    h = processes.GnrTaskSchedulerHandler(None, sitename='mysite')
    h.start()
    return h


def test_handler_starts_the_scheduler_child(handler):
    child = handler.scheduler_process
    assert _FakeProcess.created == [child]
    assert child.name == 'ts_mysite'
    assert child.args == ('mysite',)
    assert child.target == processes.GnrTaskSchedulerHandler.runSchedulerProcess
    assert child.daemon and child.alive
    assert handler.is_alive() and handler.monitor_running


def test_handler_leaves_a_live_child_alone(handler):
    child = handler.scheduler_process
    handler.checkSchedulerProcess()
    assert handler.scheduler_process is child
    assert len(_FakeProcess.created) == 1


def test_handler_restarts_a_dead_child(handler, caplog):
    dead = handler.scheduler_process
    dead.alive = False
    dead.exitcode = 1

    with caplog.at_level(logging.WARNING, logger='gnr.web'):
        handler.checkSchedulerProcess()

    assert handler.scheduler_process is not dead
    assert handler.scheduler_process.alive
    assert any('restarting' in r.getMessage() for r in caplog.records)


def test_handler_terminate_stops_child_and_supervision(handler):
    child = handler.scheduler_process
    handler.terminate()

    assert child.terminated
    assert not handler.monitor_running
    assert not handler.is_alive()
    handler.checkSchedulerProcess()
    assert len(_FakeProcess.created) == 1
