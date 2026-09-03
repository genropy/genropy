"""Regression tests for the thread-local ``currentPage`` cleanup in the
out-of-request task runners (#379/#380).

``site.currentPage`` is backed by ``gnr.core.gnrlang.ThreadedDict``:
assigning a page stores it under the current thread ident, assigning
``None`` pops that entry. Every runner that sets ``currentPage`` outside
``GnrWsgiSite.dispatcher()`` (which already resets it in a ``finally``)
must do the same, otherwise a task that raises - or simply returns early -
leaves the entry, and with it the whole page and its db connection, alive
for that thread ident forever.

The fake sites below reuse the real ``GnrWsgiSite.currentPage`` property
over a real ``ThreadedDict``, so the assertions exercise the actual
pop-on-None behaviour instead of a mock of it; only what is external to
the mechanism (resource loader, db, task classes) is faked.
"""

import contextlib
import logging
import threading

import pytest

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrlang import ThreadedDict
from gnr.web import gnrtask, gnrtask_new
from gnr.web.daemon.processes import GnrWorker


class _FakePage:
    """Minimal stand-in for the page a task runs on."""

    def __init__(self, raising=False):
        self.raising = raising
        self.download_name = None
        self._db = None
        self.calls = []

    @property
    def db(self):
        return _FakeDb()

    def table_script_run(self, **kwargs):
        self.calls.append(kwargs)
        if self.raising:
            raise RuntimeError('batch exploded')


class _FakeTaskTable:
    """``sys.task`` as seen by the runners."""

    def __init__(self, raising=False, task_class=None):
        self.raising = raising
        self.task_class = task_class
        self.run_calls = []

    def runTask(self, task, page=None):
        self.run_calls.append(task)
        if self.raising:
            raise RuntimeError('task exploded')

    def getBtcClass(self, table=None, command=None, page=None):
        if self.raising:
            raise RuntimeError('task class lookup exploded')
        return self.task_class


class _FakeDb:
    def __init__(self, tasktable=None):
        self.tasktable = tasktable or _FakeTaskTable()

    def table(self, name):
        return self.tasktable

    @contextlib.contextmanager
    def tempEnv(self, **kwargs):
        yield

    def closeConnection(self):
        pass


class _FakeSite:
    """Reuses the real thread-local ``currentPage`` property of
    ``GnrWsgiSite`` so ``site.currentPage = None`` really pops the entry.
    """

    currentPage = gws.GnrWsgiSite.currentPage

    def __init__(self, page=None, db=None):
        self._currentPages = ThreadedDict()
        self._page = page or _FakePage()
        self.db = db or _FakeDb()

    @property
    def dummyPage(self):
        return self._page


# ---------------------------------------------------------------------------
# gnr/web/daemon/processes.py - GnrWorker
# ---------------------------------------------------------------------------


class _FakeResourceLoader:
    def __init__(self, page):
        self._page = page

    def get_page_by_id(self, page_id):
        return self._page


class _FakeWorkerSite(_FakeSite):
    def __init__(self, page=None, db=None):
        super().__init__(page=page, db=db)
        self.resource_loader = _FakeResourceLoader(self._page)


class _FakeWorker:
    """Calls the real ``GnrWorker`` methods without going through
    ``GnrRemoteProcess.__init__`` (which would build a real site)."""

    run_batch = GnrWorker.run_batch
    run_task = GnrWorker.run_task

    def __init__(self, site):
        self.site = site
        self.lock = threading.Lock()
        self.execution_dict = {}
        self.logger = _CollectingLogger()


class _CollectingLogger:
    def __init__(self):
        self.warnings = []

    def warn(self, msg):
        self.warnings.append(msg)

    def debug(self, msg):
        pass


def test_worker_run_batch_success_leaves_no_thread_local_residue():
    site = _FakeWorkerSite()
    worker = _FakeWorker(site)

    worker.run_batch({'page_id': 'p1', 'batch_kwargs': {'a': 1}})

    assert site._page.calls == [{'a': 1}]
    assert site._currentPages._data == {}


def test_worker_run_batch_exception_leaves_no_thread_local_residue():
    site = _FakeWorkerSite(page=_FakePage(raising=True))
    worker = _FakeWorker(site)

    with pytest.raises(RuntimeError):
        worker.run_batch({'page_id': 'p1', 'batch_kwargs': {}})

    assert site._currentPages._data == {}


def test_worker_run_task_success_leaves_no_thread_local_residue():
    site = _FakeWorkerSite()
    worker = _FakeWorker(site)

    worker.run_task({'id': 't1', 'concurrent': False})

    assert site.db.tasktable.run_calls
    assert worker.execution_dict == {}
    assert site._currentPages._data == {}


def test_worker_run_task_exception_leaves_no_thread_local_residue():
    site = _FakeWorkerSite(db=_FakeDb(tasktable=_FakeTaskTable(raising=True)))
    worker = _FakeWorker(site)

    with pytest.raises(RuntimeError):
        worker.run_task({'id': 't1', 'concurrent': False})

    assert site._currentPages._data == {}


def test_worker_run_task_concurrency_guard_leaves_no_thread_local_residue():
    """The non-concurrent guard returns early when the task is already
    running elsewhere: that exit path must pop the entry too."""
    site = _FakeWorkerSite()
    worker = _FakeWorker(site)
    worker.execution_dict['t1'] = 4242

    worker.run_task({'id': 't1', 'concurrent': False})

    assert worker.logger.warnings, 'the guard should have logged the skip'
    assert site.db.tasktable.run_calls == [], 'the task must not run twice'
    assert site._currentPages._data == {}
    assert worker.execution_dict == {'t1': 4242}, \
        'the entry belongs to the execution already running it: releasing it here ' \
        'would let a third call through the guard'


# ---------------------------------------------------------------------------
# gnr/web/gnrtask.py - GnrTaskWorker.runTask
# ---------------------------------------------------------------------------


TASK_EXECUTION = {
    'id': 'exec1',
    'task_table': 'sys.task',
    'task_command': 'do_stuff',
    'task_saved_query': None,
    'task_parameters': {'a': 1},
    'table_table': 'sys.task',
    'table_name': 'task',
    'table_command': 'do_stuff',
}


class _FakeTaskObj:
    def __init__(self, raising=False):
        self.raising = raising
        self.calls = []

    def __call__(self, parameters=None, task_execution_record=None):
        self.calls.append(parameters)
        if self.raising:
            raise RuntimeError('task object exploded')


def _task_class_factory(task_obj):
    def task_class(page=None, resource_table=None, batch_selection_savedQuery=None):
        return task_obj
    return task_class


class _FakeLegacyTaskWorker:
    """Calls the real ``GnrTaskWorker.runTask`` without building a site."""

    runTask = gnrtask.GnrTaskWorker.runTask

    def __init__(self, site):
        self.site = site
        self.db = site.db


def _legacy_worker(task_class=None, raising=False):
    tasktable = _FakeTaskTable(raising=raising, task_class=task_class)
    site = _FakeSite(db=_FakeDb(tasktable=tasktable))
    return _FakeLegacyTaskWorker(site), site


def test_legacy_runtask_success_leaves_no_thread_local_residue():
    task_obj = _FakeTaskObj()
    worker, site = _legacy_worker(task_class=_task_class_factory(task_obj))

    worker.runTask(dict(TASK_EXECUTION))

    assert task_obj.calls, 'the task object should have been invoked'
    assert site._currentPages._data == {}


def test_legacy_runtask_missing_task_class_leaves_no_thread_local_residue():
    """``getBtcClass`` returning nothing makes runTask return early: the
    entry must be popped on that path as well."""
    worker, site = _legacy_worker(task_class=None)

    worker.runTask(dict(TASK_EXECUTION))

    assert site._currentPages._data == {}


def test_legacy_runtask_exception_leaves_no_thread_local_residue():
    task_obj = _FakeTaskObj(raising=True)
    worker, site = _legacy_worker(task_class=_task_class_factory(task_obj))

    with pytest.raises(RuntimeError):
        worker.runTask(dict(TASK_EXECUTION))

    assert site._currentPages._data == {}


def test_legacy_runtask_missing_task_class_is_logged(caplog):
    """The new runner logs the missing task class; the legacy one used to
    return in silence, so a task with a stale command vanished without a
    trace in the only place an operator would look."""
    worker, site = _legacy_worker(task_class=None)

    with caplog.at_level(logging.ERROR, logger='gnr.web.gnrtask'):
        worker.runTask(dict(TASK_EXECUTION))

    logged = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert any("Can't find task class" in m and 'do_stuff' in m for m in logged)


class _StopLoop(Exception):
    """Breaks out of ``start``'s ``while True`` after one pass."""


class _FakeStartWorker:
    """Calls the real ``GnrTaskWorker.start`` over a fake task table."""

    start = gnrtask.GnrTaskWorker.start

    def __init__(self, site, pkeys, failing):
        self.site = site
        self.db = site.db
        self.tblobj = self
        self.interval = 60
        self._pkeys = pkeys
        self._failing = failing
        self.attempted = []
        self.rollbacks = 0
        self.released = []

    def batchUpdate(self, updater, _pkeys=None, **kwargs):
        self.released.append((tuple(_pkeys), dict(updater)))

    def taskToExecute(self):
        return list(self._pkeys)

    @contextlib.contextmanager
    def recordToUpdate(self, pkey, **kwargs):
        yield dict(TASK_EXECUTION, id=pkey)

    def runTask(self, task_execution):
        self.attempted.append(task_execution['id'])
        if task_execution['id'] in self._failing:
            raise RuntimeError('task %s exploded' % task_execution['id'])


def test_legacy_start_survives_a_failing_task(monkeypatch, caplog):
    """One failing task used to propagate out of ``start``'s loop and kill the
    worker, so every task queued behind it was never run either."""
    site = _FakeSite(db=_FakeDb())
    site.db.commit = lambda: None
    site.db.rollbackAll = lambda: None
    worker = _FakeStartWorker(site, ['first', 'boom', 'last'], {'boom'})
    monkeypatch.setattr(gnrtask, 'sleep', lambda *a, **k: (_ for _ in ()).throw(_StopLoop()))

    with caplog.at_level(logging.ERROR, logger='gnr.web.gnrtask'):
        with pytest.raises(_StopLoop):
            worker.start()

    assert worker.attempted == ['first', 'boom', 'last']
    assert any('boom' in r.getMessage() for r in caplog.records
               if r.levelno >= logging.ERROR)


def test_legacy_start_releases_the_record_of_a_failing_task(monkeypatch, caplog):
    """``taskToExecute`` commits ``start_ts`` and ``pid`` before yielding, so
    surviving the failure without releasing the row leaves it claimed by a live
    pid: ``active_workers`` keeps counting it and ``checkAlive`` will not free
    it, and the task is never retried while this worker lives."""
    site = _FakeSite(db=_FakeDb())
    commits = []
    site.db.commit = lambda: commits.append(1)
    site.db.rollbackAll = lambda: None
    worker = _FakeStartWorker(site, ['first', 'boom'], {'boom'})
    monkeypatch.setattr(gnrtask, 'sleep', lambda *a, **k: (_ for _ in ()).throw(_StopLoop()))

    with caplog.at_level(logging.ERROR, logger='gnr.web.gnrtask'):
        with pytest.raises(_StopLoop):
            worker.start()

    assert worker.released == [(('boom',), {'pid': None, 'start_ts': None})], \
        'only the failing task must be released, and with the same columns checkAlive clears'
    assert len(commits) == 2, 'the release has to be committed, like the success path'


# ---------------------------------------------------------------------------
# gnr/web/gnrtask_new.py - execute_task
# ---------------------------------------------------------------------------


TASK_PAYLOAD = {
    'task_id': 'task1',
    'run_id': 'run1',
    'payload': {
        'table_name': 'sys.task',
        'action': 'do_stuff',
        'saved_query_code': None,
        'parameters': {'a': 1},
    },
}


class _DummyAckSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json=None):
        return None


def _patch_execute_task(monkeypatch, tasktable):
    """Replaces the app/site/ack plumbing of ``execute_task`` and returns
    the list the created fake sites are appended to."""
    sites = []
    db = _FakeDb(tasktable=tasktable)

    class DummyApp:
        def __init__(self, *args, **kwargs):
            self.db = db

    def site_factory(*args, **kwargs):
        site = _FakeSite(db=db)
        sites.append(site)
        return site

    monkeypatch.setattr(gnrtask_new, 'GnrApp', DummyApp)
    monkeypatch.setattr(gnrtask_new, 'GnrWsgiSite', site_factory)
    monkeypatch.setattr(gnrtask_new.requests, 'Session', lambda: _DummyAckSession())
    return sites


def test_execute_task_success_leaves_no_thread_local_residue(monkeypatch):
    task_obj = _FakeTaskObj()
    tasktable = _FakeTaskTable(task_class=_task_class_factory(task_obj))
    sites = _patch_execute_task(monkeypatch, tasktable)

    gnrtask_new.execute_task('gnrtest', dict(TASK_PAYLOAD))

    assert task_obj.calls, 'the task object should have been invoked'
    assert sites[0]._currentPages._data == {}


def test_execute_task_missing_task_class_leaves_no_thread_local_residue(monkeypatch):
    tasktable = _FakeTaskTable(task_class=None)
    sites = _patch_execute_task(monkeypatch, tasktable)

    gnrtask_new.execute_task('gnrtest', dict(TASK_PAYLOAD))

    assert sites[0]._currentPages._data == {}


def test_execute_task_exception_leaves_no_thread_local_residue(monkeypatch):
    task_obj = _FakeTaskObj(raising=True)
    tasktable = _FakeTaskTable(task_class=_task_class_factory(task_obj))
    sites = _patch_execute_task(monkeypatch, tasktable)

    with pytest.raises(RuntimeError):
        gnrtask_new.execute_task('gnrtest', dict(TASK_PAYLOAD))

    assert sites[0]._currentPages._data == {}
