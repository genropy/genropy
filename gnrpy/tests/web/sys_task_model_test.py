"""Tests for the legacy (non async) task scheduling logic of sys.task.

The model lives under projects/gnrcore and is normally reached through the
resource loader of a running instance; here it is loaded straight from its
path, so that isTaskScheduledNow/findTasks can be exercised without an
instance and without a database.
"""
import importlib.util
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TASK_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                               'projects', 'gnrcore', 'packages', 'sys',
                               'model', 'task.py')

ROME = ZoneInfo("Europe/Rome")


def load_task_model():
    spec = importlib.util.spec_from_file_location('sys_task_model_under_test',
                                                  os.path.abspath(TASK_MODEL_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_task(**kwargs):
    task = dict(id='task1', table_name='tbl', command='cmd', run_asap=None,
                frequency=None, month=None, day=None, hour=None, minute=None,
                last_scheduled_ts=None)
    task.update(kwargs)
    return task


def freeze_clocks(monkeypatch, module, instant_utc, zone=ROME):
    """Pin every clock the model could read to the same instant: the local one,
    carrying the zone offset, and the UTC one. A schedule entered as local wall
    clock time must match the local reading, whichever clock is read."""
    local_instant = instant_utc.astimezone(zone)

    class FrozenDatetime:
        @staticmethod
        def now(tz=None):
            return instant_utc.astimezone(tz) if tz else instant_utc

    monkeypatch.setattr(module, 'localnow', lambda: local_instant, raising=False)
    monkeypatch.setattr(module, 'datetime', FrozenDatetime)
    return local_instant


def make_table(module, tasks):
    """Real Table, with only the task query replaced: findTasks reads the
    records through self.query() and computes everything else itself."""

    class _QueryResult:
        def fetch(self):
            return tasks

    class _TaskTable(module.Table):
        def query(self, *args, **kwargs):
            return _QueryResult()

    return _TaskTable()


def test_is_task_scheduled_now_reads_wall_clock_fields():
    """The hour/minute columns are wall clock time: the same instant matches
    or not depending on the offset it is expressed in."""
    module = load_task_model()
    table = make_table(module, [])
    task = make_task(month='6', day='15', hour='9', minute='0')

    instant = datetime(2024, 6, 15, 7, 0, tzinfo=timezone.utc)

    assert table.isTaskScheduledNow(task, instant.astimezone(ROME)) == '2024-6-15-9-0'
    # the very same instant read in UTC is 07:00, the task is not due yet
    assert table.isTaskScheduledNow(task, instant) is False


def test_find_tasks_defaults_to_local_wall_clock(monkeypatch):
    """findTasks() with no timestamp must evaluate the schedule against the
    local wall clock, not against UTC (issue #975)."""
    module = load_task_model()
    # 07:00 UTC is 09:00 in Rome (summer time)
    freeze_clocks(monkeypatch, module, datetime(2024, 6, 15, 7, 0, tzinfo=timezone.utc))

    table = make_table(module, [make_task(month='6', day='15',
                                          hour='9', minute='0')])

    assert table.findTasks() == [('task1', '2024-6-15-9-0')]


def test_find_tasks_honours_explicit_timestamp():
    module = load_task_model()
    table = make_table(module, [make_task(month='6', day='15',
                                          hour='9', minute='0')])

    ts = datetime(2024, 6, 15, 9, 0, tzinfo=ROME)
    assert table.findTasks(timestamp=ts) == [('task1', '2024-6-15-9-0')]
