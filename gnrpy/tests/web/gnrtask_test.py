import asyncio
import json
import os
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from webcommon import BaseGnrTest

from gnr.web import gnrtask


class _AsyncFixtureWrapper:
    def __init__(self, wrapped, loop):
        self._wrapped = wrapped
        self._loop = loop

    def run(self, coro):
        return self._loop.run_until_complete(coro)

    def __getattr__(self, item):
        return getattr(self._wrapped, item)

    def __setattr__(self, key, value):
        if key in {"_wrapped", "_loop"} or key.startswith("_"):
            super().__setattr__(key, value)
        else:
            setattr(self._wrapped, key, value)


@pytest.fixture
def scheduler(monkeypatch, tmp_path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    class DummyQueryResult:
        def fetch(self):
            return []

        def output(self, data_format):
            return {}

    class DummyTable:
        def __init__(self, name):
            self.name = name
            self.inserted = []

        def insert(self, record):
            data = dict(record)
            data.setdefault("id", "exec-id")
            self.inserted.append(data)
            return data

        def query(self, *_, **__):
            return DummyQueryResult()

        @property
        def db(self):
            return self

        def commit(self):
            pass

        def record(self, task_id):
            return DummyQueryResult()

        def update(self, data_dict, task_record):
            return []

    class DummyDB:
        def __init__(self):
            self.dbname = "dummydb"

        def table(self, name):
            return DummyTable(name)

    class DummyApp:
        def __init__(self, *_, **__):
            self.db = DummyDB()

    monkeypatch.setattr(gnrtask, "GnrApp", DummyApp)

    class DummySite:
        def __init__(self, *_, **__):
            self.dummyPage = types.SimpleNamespace()
            self.currentPage = None

    monkeypatch.setattr(gnrtask, "GnrWsgiSite", DummySite)

    scheduler = gnrtask.GnrTaskScheduler("gnrtest", host=None, port=None)
    scheduler.dump_file_name = str(tmp_path / "queue_dump.json")
    wrapper = _AsyncFixtureWrapper(scheduler, loop)

    yield wrapper

    asyncio.set_event_loop(None)
    loop.close()


@pytest.fixture
def worker(monkeypatch):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    class DummyTable:
        pass

    class DummyDB:
        def table(self, name):
            return DummyTable()

    class DummyApp:
        def __init__(self, *_, **__):
            self.db = DummyDB()

    monkeypatch.setattr(gnrtask, "GnrApp", DummyApp)

    class DummySite:
        def __init__(self, *_, **__):
            self.dummyPage = types.SimpleNamespace()
            self.currentPage = None

    monkeypatch.setattr(gnrtask, "GnrWsgiSite", DummySite)

    worker = gnrtask.GnrTaskWorker("gnrtest", queue_name="custom", processes=2)
    wrapper = _AsyncFixtureWrapper(worker, loop)

    yield wrapper

    asyncio.set_event_loop(None)
    loop.close()


class _NoDaemonBase(BaseGnrTest):
    @classmethod
    def setup_class(cls):
        # Skip expensive BaseGnrTest environment bootstrap; tests provide their own stubs.
        pass

    @classmethod
    def teardown_class(cls):
        pass


class TestGnrTaskBasics(_NoDaemonBase):
    def test_task_is_due_run_asap_returns_wildcard(self):
        task = gnrtask.GnrTask(
            name="t1",
            action="run",
            db="test",
            table_name="tbl",
            schedule={"run_asap": True},
        )
        result = task.is_due(timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert result == "*"

    def test_task_is_due_frequency_respects_last_schedule(self):
        now = datetime(2024, 1, 1, 0, 30, tzinfo=timezone.utc)
        task = gnrtask.GnrTask(
            name="freq",
            action="run",
            db="test",
            table_name="tbl",
            schedule={"frequency": 10},
        )

        past_enough = now - timedelta(minutes=15)
        not_enough = now - timedelta(minutes=5)

        assert task.is_due(timestamp=now, last_scheduled_ts=past_enough) == "*"
        assert task.is_due(timestamp=now, last_scheduled_ts=not_enough) is False

    def test_task_is_due_matches_calendar_schedule(self):
        ts = datetime(2024, 4, 1, 12, 15, tzinfo=timezone.utc)
        task = gnrtask.GnrTask(
            name="calendar",
            action="run",
            db="test",
            table_name="tbl",
            schedule={"month": "4", "day": "1", "hour": "12", "minute": "15"},
        )

        result = task.is_due(timestamp=ts)
        assert result == "2024-4-1-12-15"


class TestGnrTaskScheduler(_NoDaemonBase):
    def test_dump_queue_to_disk_preserves_items(self, scheduler):
        item = {"queue_name": "general", "payload": {"task": 1}}

        async def runner():
            await scheduler.queues["general"].put(item)
            await scheduler.dump_queue_to_disk()

        scheduler.run(runner())

        assert scheduler.queues["general"].qsize() == 1
        dump_path = scheduler.dump_file_name
        with open(dump_path) as handle:
            assert json.load(handle) == [item]

    def test_load_queue_from_disk_restores_items(self, scheduler):
        item = {"queue_name": "custom", "payload": {"task": 2}}
        with open(scheduler.dump_file_name, "w") as handle:
            json.dump([item], handle)

        async def runner():
            await scheduler.load_queue_from_disk()
            restored_item = await asyncio.wait_for(scheduler.queues["custom"].get(), timeout=1)
            return restored_item, scheduler.queues["custom"].empty()

        restored, empty = scheduler.run(runner())

        assert scheduler.queues["custom"].qsize() == 0
        assert restored == item
        assert empty
        assert not os.path.exists(scheduler.dump_file_name)

    def test_worker_alive_tracks_workers(self, scheduler, monkeypatch):
        base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

        class DummyDateTime:
            def __init__(self):
                self.calls = 0

            def now(self, tz=None):
                self.calls += 1
                return base_time + timedelta(seconds=self.calls)

        monkeypatch.setattr(gnrtask, "datetime", DummyDateTime())

        scheduler.worker_alive("worker-1", "general")
        first_seen = scheduler.workers["worker-1"]["lastseen"]
        assert scheduler.workers["worker-1"]["queue_name"] == "general"
        assert scheduler.workers["worker-1"]["worked_tasks"] == 0

        scheduler.worker_alive("worker-1", "general")
        second_seen = scheduler.workers["worker-1"]["lastseen"]
        assert second_seen > first_seen

    def test_empty_queue_replaces_queue_instance(self, scheduler):
        async def runner():
            await scheduler.queues["custom"].put({"value": 1})
            await scheduler.empty_queue("custom")

        original_queue = scheduler.queues["custom"]
        scheduler.run(runner())
        new_queue = scheduler.queues["custom"]

        assert new_queue is not original_queue
        assert new_queue.qsize() == 0

    def test_put_task_in_queue_enqueues_and_records_execution(self, scheduler):
        task = gnrtask.GnrTask(
            name="qtask",
            action="run",
            db="test",
            table_name="tbl",
            schedule={},
            task_id="task1",
        )
        scheduler.tasks["task1"] = [task, None]

        async def runner():
            await scheduler.put_task_in_queue("task1", task)

        scheduler.run(runner())

        assert scheduler.tasks["task1"][1].tzinfo is timezone.utc
        assert scheduler.exectbl.inserted, "Execution table should record insert"
        exec_record = scheduler.exectbl.inserted[-1]
        assert exec_record["task_id"] == "task1"
        assert scheduler.queues["general"].qsize() == 1
        queued = scheduler.queues["general"].get_nowait()
        assert queued["payload"]["name"] == "qtask"
        assert queued["run_id"] == exec_record["id"]

    def test_complete_task_invokes_task_completion(self, scheduler, monkeypatch):
        task = gnrtask.GnrTask(
            name="ctask",
            action="run",
            db="test",
            table_name="tbl",
            schedule={},
            task_id="task42",
        )
        called = {}

        async def completed(tasktbl, exectbl):
            called["ok"] = True

        task.completed = completed
        scheduler.tasks["task42"] = [task, None]

        scheduler.run(scheduler.complete_task("task42"))
        assert called["ok"]

    def test_complete_task_unknown_logs_error(self, scheduler, caplog):
        caplog.set_level("ERROR")
        scheduler.tasks["missing"] = [None, None]
        scheduler.run(scheduler.complete_task("missing"))
        assert any("can't complete" in rec.message for rec in caplog.records)

    def test_load_configuration_populates_tasks(self, scheduler, monkeypatch):
        records = [
            {
                "id": "task1",
                "task_name": "Loaded Task",
                "table_name": "tbl",
                "command": "do_stuff",
                "saved_query_code": "code1",
                "parameters": {"foo": "bar"},
                "last_scheduled_ts": None,
                "run_asap": None,
                "month": None,
                "day": None,
                "hour": None,
                "minute": None,
                "frequency": 5,
            }
        ]

        class CustomQueryResult:
            def fetch(self_inner):
                return records

        class CustomTaskTable:
            def query(self_inner, *_, **__):
                return CustomQueryResult()

        scheduler.tasktbl = CustomTaskTable()

        scheduler.run(scheduler.load_configuration())

        assert "task1" in scheduler.tasks
        loaded_task, last_ts = scheduler.tasks["task1"]
        assert isinstance(loaded_task, gnrtask.GnrTask)
        assert loaded_task.name == "Loaded Task"
        assert loaded_task.schedule["frequency"] == 5
        assert last_ts is None

    def test_retry_monitor_requeues_and_increments_retry(self, scheduler, monkeypatch):
        task = {"queue_name": "general", "task_id": "task1", "run_id": "run1"}
        sent_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        scheduler.pending_ack["run1"] = (task, sent_time, 0, None)

        async def fake_sleep(_):
            raise asyncio.CancelledError

        monkeypatch.setattr(gnrtask.asyncio, "sleep", fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            scheduler.run(scheduler.retry_monitor())

        assert scheduler.queues["general"].qsize() == 1
        requeued = scheduler.queues["general"].get_nowait()
        assert requeued["run_id"] == "run1"
        assert scheduler.pending_ack["run1"][2] == 1

    def test_retry_monitor_marks_failed_after_limit(self, scheduler, monkeypatch):
        task = {"queue_name": "general", "task_id": "task1", "run_id": "run-limit"}
        sent_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        scheduler.pending_ack["run-limit"] = (task, sent_time, gnrtask.RETRY_LIMIT, None)

        async def fake_sleep(_):
            raise asyncio.CancelledError

        monkeypatch.setattr(gnrtask.asyncio, "sleep", fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            scheduler.run(scheduler.retry_monitor())

        assert "run-limit" not in scheduler.pending_ack
        assert scheduler.failed_tasks[-1]["run_id"] == "run-limit"

    def test_next_task_returns_task_and_tracks_worker(self, scheduler):
        item = {"run_id": "runX", "task_id": "taskX", "queue_name": "general"}

        async def runner():
            await scheduler.queues["general"].put(item)
            request = types.SimpleNamespace(query={"worker_id": "workerA", "queue_name": "general"})
            response = await scheduler.next_task(request)
            return response

        response = scheduler.run(runner())
        assert scheduler.workers["workerA"]["worked_tasks"] == 1
        assert "runX" in scheduler.pending_ack
        payload = json.loads(response.text)
        assert payload["run_id"] == "runX"

    def test_next_task_without_worker_id_returns_none(self, scheduler):
        request = types.SimpleNamespace(query={})

        async def runner():
            return await scheduler.next_task(request)

        response = scheduler.run(runner())
        assert response is None

    def test_acknowledge_known_task(self, scheduler, monkeypatch):
        called = {}

        async def fake_complete(task_id):
            called["task_id"] = task_id

        scheduler.pending_ack["run1"] = ({"task_id": "task1"}, datetime.now(timezone.utc), 0, None)
        monkeypatch.setattr(scheduler, "complete_task", fake_complete)

        class DummyRequest:
            async def json(self):
                return {"run_id": "run1"}

        response = scheduler.run(scheduler.acknowledge(DummyRequest()))
        assert json.loads(response.text) == {"status": "acknowledged"}
        assert "run1" not in scheduler.pending_ack
        assert called["task_id"] == "task1"

    def test_acknowledge_unknown_task(self, scheduler):
        class DummyRequest:
            async def json(self):
                return {"run_id": "unknown"}

        response = scheduler.run(scheduler.acknowledge(DummyRequest()))
        assert response.status == 400
        assert json.loads(response.text)["status"] == "unknown task"

    def test_schedule_single_execution_creates_manual_task(self, scheduler, monkeypatch):
        task_def = {
            "task_name": "manual",
            "action": "run",
            "table": "tbl",
            "parameters": {"x": 1},
            "worker_code": "custom",
            "domain": "domain",
        }

        original_cls = gnrtask.GnrTask

        class PatchedGnrTask(original_cls):
            def __init__(self, *args, **kwargs):
                if "table" in kwargs:
                    kwargs["table_name"] = kwargs.pop("table")
                super().__init__(*args, **kwargs)

        monkeypatch.setattr(gnrtask, "GnrTask", PatchedGnrTask)

        async def runner():
            return await scheduler.schedule_single_execution(task_def)

        result = scheduler.run(runner())
        assert result == "ok"
        assert scheduler.tasks[None][0].name == "manual"
        assert scheduler.queues["custom"].qsize() == 1

    def test_start_service_initializes_scheduler(self, scheduler, monkeypatch):
        calls = []

        async def fake_load_config(triggered=False):
            calls.append(("load_config", triggered))

        async def fake_load_queue():
            calls.append(("load_queue", None))

        async def fake_schedule_loop():
            return "schedule-loop"

        async def fake_retry_monitor():
            return "retry-monitor"

        created_task_names = []

        def fake_create_task(coro):
            created_task_names.append(coro.cr_code.co_name)
            coro.close()
            return types.SimpleNamespace(cancel=lambda: None)

        monkeypatch.setattr(scheduler, "load_configuration", fake_load_config)
        monkeypatch.setattr(scheduler, "load_queue_from_disk", fake_load_queue)
        monkeypatch.setattr(scheduler, "schedule_loop", fake_schedule_loop)
        monkeypatch.setattr(scheduler, "retry_monitor", fake_retry_monitor)
        monkeypatch.setattr(gnrtask.asyncio, "create_task", fake_create_task)

        scheduler.run(scheduler.start_service())

        assert ("load_config", False) in calls
        assert ("load_queue", None) in calls
        assert len(created_task_names) == 2
        assert set(created_task_names) == {"fake_schedule_loop", "fake_retry_monitor"}

    def test_shutdown_scheduler_dumps_queue(self, scheduler, monkeypatch):
        calls = []

        async def fake_dump():
            calls.append("dumped")

        monkeypatch.setattr(scheduler, "dump_queue_to_disk", fake_dump)
        scheduler.run(scheduler.shutdown_scheduler())
        assert calls == ["dumped"]


class TestSchedulerClient(_NoDaemonBase):
    def test_scheduler_client_routes_calls(self, monkeypatch):
        calls = []

        class DummyResponse:
            def __init__(self, data=None, ok=True, reason="OK"):
                self._data = data
                self.ok = ok
                self.reason = reason

            def json(self):
                return self._data

        def fake_get(url, params=None):
            calls.append((url, params))
            return DummyResponse(data={"status": "ok"})

        monkeypatch.setattr(gnrtask.requests, "get", fake_get)
        client = gnrtask.GnrTaskSchedulerClient(url="http://scheduler")

        client.stop_run("run1")
        client.execute("tbl", "act", {"a": 1}, user="usr", domain="dom", worker_code="w", attime="later")
        client.update_task({"id": 1})
        client.reload()
        status = client.status()
        client.empty_queue("general")
        client.gen_fake(3)

        assert status == {"status": "ok"}
        expected_uris = [
            "http://scheduler/stop_run",
            "http://scheduler/execute",
            "http://scheduler/update_task",
            "http://scheduler/reload",
            "http://scheduler/status",
            "http://scheduler/empty_queue",
            "http://scheduler/gen_fake",
        ]
        assert [uri for uri, _ in calls] == expected_uris
        execute_params = calls[1][1]
        assert execute_params["worker_code"] is None
        assert execute_params["attime"] is None

    def test_scheduler_client_raises_on_http_error(self, monkeypatch):
        class DummyResponse:
            ok = False
            reason = "boom"

        def fake_get(url, params=None):
            return DummyResponse()

        monkeypatch.setattr(gnrtask.requests, "get", fake_get)
        client = gnrtask.GnrTaskSchedulerClient(url="http://scheduler")

        with pytest.raises(Exception):
            client.empty_queue("general")


class TestGnrTaskWorker(_NoDaemonBase):
    def test_worker_notify_alive_success(self, worker, monkeypatch):
        calls = []

        class DummyResponse:
            status_code = 200

        class DummySession:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url, params=None, timeout=None):
                calls.append((url, params, timeout))
                return DummyResponse()

        monkeypatch.setattr(gnrtask.requests, "Session", lambda: DummySession())
        worker._notify_alive()

        assert len(calls) == 1
        url, params, timeout = calls[0]
        assert url.endswith("/alive")
        assert params["worker_id"] == worker.worker_id
        assert params["queue_name"] == worker.queue_name
        assert timeout == gnrtask.NOTIFY_ALIVE_INTERVAL * 2

    def test_worker_notify_alive_failure(self, worker, monkeypatch, caplog):
        caplog.set_level("ERROR")

        class BrokenSession:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url, params=None, timeout=None):
                raise RuntimeError("boom")

        monkeypatch.setattr(gnrtask.requests, "Session", lambda: BrokenSession())
        worker._notify_alive()
        assert any("Notify alive error" in rec.message for rec in caplog.records)

    def test_worker_say_goodbye_success(self, worker, monkeypatch):
        class DummyResponse:
            def __init__(self, status):
                self.status = status

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class DummySession:
            def __init__(self, *_, **__):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def get(self, *_, **__):
                return DummyResponse(200)

        monkeypatch.setattr(gnrtask.aiohttp, "ClientSession", DummySession)
        assert worker.run(worker.say_goodbye()) is True

    def test_worker_say_goodbye_failure(self, worker, monkeypatch):
        class DummyResponse:
            def __init__(self, status):
                self.status = status

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class DummySession:
            def __init__(self, *_, **__):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def get(self, *_, **__):
                return DummyResponse(500)

        monkeypatch.setattr(gnrtask.aiohttp, "ClientSession", DummySession)
        assert worker.run(worker.say_goodbye()) is False

    def test_worker_say_goodbye_exception(self, worker, monkeypatch, caplog):
        caplog.set_level("ERROR")

        class DummySession:
            def __init__(self, *_, **__):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def get(self, *_, **__):
                raise RuntimeError("boom")

        monkeypatch.setattr(gnrtask.aiohttp, "ClientSession", DummySession)
        assert worker.run(worker.say_goodbye()) is False
        assert any("Unable to leave scheduler" in rec.message for rec in caplog.records)

    def test_worker_shutdown_worker_stops_consumers(self, worker, monkeypatch):
        shutdown_called = {}

        class DummyPool:
            def shutdown(self, wait=True, cancel_futures=False):
                shutdown_called["args"] = (wait, cancel_futures)

        worker.process_pool = DummyPool()

        async def fake_say_goodbye():
            fake_say_goodbye.called = True
            return True

        fake_say_goodbye.called = False
        monkeypatch.setattr(worker, "say_goodbye", fake_say_goodbye)

        async def consumer():
            while True:
                item = await worker.tasks_q.get()
                worker.tasks_q.task_done()
                if item is None:
                    break

        async def runner():
            consumers = [asyncio.create_task(consumer()) for _ in range(worker.processes)]
            alive_task = asyncio.create_task(asyncio.sleep(60))
            await worker.shutdown_worker(consumers, alive_task)
            return consumers, alive_task

        consumers, alive_task = worker.run(runner())

        assert worker.stop_evt.is_set()
        assert worker.tasks_q.empty()
        assert fake_say_goodbye.called is True
        assert shutdown_called["args"] == (True, False)
        assert all(task.done() for task in consumers)
        assert alive_task.cancelled()
