"""Async scheduler: acknowledging a run on a real database (issue #1553).

A task stopped or deleted while it runs is dropped from the in-memory
schedule by the reload, so the acknowledgement of its run must close the
run without looking the task up there.
"""
import asyncio
import json
import types
from datetime import datetime, timezone

import pytest

from core.common import BaseGnrTest

from gnr.web import gnrtask_new


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


class _AckRequest:
    def __init__(self, run_id):
        self.run_id = run_id

    async def json(self):
        return {"run_id": self.run_id}


@pytest.fixture
def scheduler(db_sqlite, monkeypatch):
    monkeypatch.setattr(gnrtask_new, "GnrApp",
                        lambda *args, **kwargs: types.SimpleNamespace(db=db_sqlite))
    # the sys.task triggers ask the running scheduler over HTTP to reload
    monkeypatch.setattr(gnrtask_new.GnrTaskSchedulerClient, "reload",
                        lambda self, domain=None: None)
    return gnrtask_new.GnrTaskScheduler("test_invoice", host=None, port=None)


def _task_and_run(db, with_task=True):
    task_id = None
    if with_task:
        tasktbl = db.table("sys.task")
        task = tasktbl.newrecord(task_name="ack test", table_name="invc.invoice",
                                 command="noop", frequency=60)
        tasktbl.insert(task)
        task_id = task["id"]
    exectbl = db.table("sys.task_execution")
    run = exectbl.newrecord(task_id=task_id, start_ts=datetime.now(timezone.utc))
    exectbl.insert(run)
    db.commit()
    return task_id, run["id"]


def _acknowledge(scheduler, task_id, run_id):
    scheduler.pending_ack[run_id] = ({"task_id": task_id}, datetime.now(timezone.utc), 0, None)
    response = asyncio.run(scheduler.acknowledge(_AckRequest(run_id)))
    return response.status, json.loads(response.text)


def test_ack_of_task_missing_from_schedule_closes_run(scheduler, db_sqlite):
    task_id, run_id = _task_and_run(db_sqlite)
    assert task_id not in scheduler.tasks

    assert _acknowledge(scheduler, task_id, run_id) == (200, {"status": "acknowledged"})

    run = db_sqlite.table("sys.task_execution").record(run_id).output("dict")
    task = db_sqlite.table("sys.task").record(task_id).output("dict")
    assert run["end_ts"] is not None
    assert task["last_execution_ts"] is not None


def test_ack_of_deleted_task_is_harmless(scheduler, db_sqlite):
    task_id, run_id = _task_and_run(db_sqlite)
    db_sqlite.table("sys.task").delete(dict(id=task_id))
    db_sqlite.commit()

    assert _acknowledge(scheduler, task_id, run_id) == (200, {"status": "acknowledged"})
    assert not db_sqlite.table("sys.task_execution").query(where="$id=:r", r=run_id).fetch()


def test_ack_of_manual_run_closes_run(scheduler, db_sqlite):
    _, run_id = _task_and_run(db_sqlite, with_task=False)

    assert _acknowledge(scheduler, None, run_id) == (200, {"status": "acknowledged"})

    run = db_sqlite.table("sys.task_execution").record(run_id).output("dict")
    assert run["end_ts"] is not None
