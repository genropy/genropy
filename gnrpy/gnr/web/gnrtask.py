#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package                : GenroPy web - see LICENSE for details
# module gnr.web.gnrtask : core module for genropy web framework
# Copyright (c)          : 2025 Softwell Srl - Milano
#--------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

# Copyright (c) 2025 Softwell.

import os
import uuid
import requests
import json
import socket
import signal
import threading
import contextlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any

from mako.template import Template
import aiohttp
import asyncio
from aiohttp import web
from concurrent.futures import ProcessPoolExecutor

from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.web import logger

GNR_SCHEDULER_PORT=int(os.environ.get("GNR_SCHEDULER_PORT", "14951"))
GNR_SCHEDULER_HOST=os.environ.get("GNR_SCHEDULER_HOST", "127.0.0.1")
GNR_SCHEDULER_URL=os.environ.get("GNR_SCHEDULER_URL", f"http://{GNR_SCHEDULER_HOST}:{GNR_SCHEDULER_PORT}")


SCHEDULER_RUN_INTERVAL = 1
RETRY_LIMIT = 3 # amount of attempt in execution retries
NOTIFY_ALIVE_INTERVAL = 2
ACK_TIMEOUT = NOTIFY_ALIVE_INTERVAL * 3 # general timeout from worker


class GnrTaskSchedulerClient:
    """
    A simple object that wraps scheduler APIs synchronously,
    useful for UI/cli interaction without implementing
    the current communication protocol
    """
    def __init__(self, url=None):
        self.url = url and url or GNR_SCHEDULER_URL

    def _call(self, uri, params=None):
        try:
            r = requests.get(f"{self.url}/{uri}", params=params)
            if not r.ok:
                raise Exception(f"Scheduler request error on URI /{uri}: {r.reason}")
            return r
        except Exception as e:
            logger.error("Error contacting scheduler: %s", e)
            raise

    def stop_run(self, run_id):
        """
        Request stop for task execution with run_id
        """
        return self._call("stop_run", dict(run_id=run_id))
    
    def execute(self, table, action,
                parameters,
                user, domains,
                worker_code=None,
                attime=None):
        """
        Insert in scheduler queue a single manual
        task execution, without using the Task table.
        """
        return self._call("execute", dict(table=table,
                                          action=action,
                                          parameters=parameters,
                                          user=user,
                                          domains=domains,
                                          worker_code=None,
                                          attime=None)
                          )
                          
    def update_task(self, record):
        """
        Manually update a task in the scheduler
        configuration
        """
        return self._call("update_task", dict(record=record))

        
    def reload(self):
        """
        Reload the whole task configuration
        """
        return self._call("reload")

    def status(self):
        """
        Retrieve the current status of queue, scheduler, workers etc
        """
        r = self._call("status")
        if r.ok:
            return r.json() or r.reason

    def empty_queue(self, queue_name):
        """
        Empty the named queue
        """
        return self._call("empty_queue", dict(queue_name=queue_name))
    
    def gen_fake(self, quantity):
        """
        Generate a :quantity items in the queue
        """
        return self._call("gen_fake", dict(quantity=quantity))

@dataclass
class GnrTask:
    name: str
    action: str
    db: Any 
    table_name: Any
    schedule: dict
    task_id: str = None
    user: str = None
    domains: str = None
    saved_query_code: str = None
    parameters: Any = None
    queue_name: str = None
    
    def __post_init__(self):
        self.queue_name = self.queue_name if self.queue_name else "general"

    # async def completed(self):
    #     """
    #     The task has been executed and acknowledged, update
    #     the last execution timestamp accordingly
    #     """
    #     self.record['last_execution_ts'] = datetime.now(timezone.utc)
    #     await self.update_record()
        
    # async def update_record(self):
    #     self.table.update(self.record, self.old_record)
    #     self.old_record = copy.deepcopy(self.record)
    #     logger.debug("Committing record change")
    #     self.db.commit()

    def is_due(self, timestamp=None, last_scheduled_ts=None):
        """
        Compute if the task is to be executed
        """
        if not timestamp:
            timestamp = datetime.now(timezone.utc)

        result = []
                
        if self.schedule.get("run_asap"):
            return '*'

        if self.schedule.get("frequency", None):
            if last_scheduled_ts is None or (timestamp - last_scheduled_ts.replace(tzinfo=timezone.utc)).seconds/60. >= self.schedule.get('frequency'):
                return '*'
            else:
                return False
            
        if not self.schedule.get("minute"):
            return False

        months =  list(map(int, self.schedule.get('month').split(','))) if self.schedule.get('month') else range(1,13)
        days = list(map(int, self.schedule.get('day').split(','))) if self.schedule.get('day') else range(1,32)
        hours = list(map(int, self.schedule.get('hour').split(','))) if self.schedule.get('hour') else range(0,24)
        minutes = list(map(int, self.schedule.get('minute').split(','))) if self.schedule.get('minutes') else range(0,60)

        hm = []
        for h in hours:
            for m in minutes:
                hm.append(h*60+m)
        y, m, d = timestamp.year, timestamp.month, timestamp.day
        h, minutes = timestamp.hour, timestamp.minute
        if m not in months or d not in days:
            return False
        curr_hm = h*60+minutes
        hmlist = [g for g in hm if g<=curr_hm]
        if not hmlist:
            return False
        key_hm = max(hmlist)
        result = '-'.join([str(y),str(m),str(d),str(int(key_hm/60)),str(key_hm%60)])
        return result

    async def completed(self):
        print("TASK COMPLETED")
        # TBD - update task execution accordingly

# class GnrTaskOld(object):
#     def __init__(self, record, db, table):
#         self.record = record
#         self.old_record = copy.deepcopy(self.record)
#         self.db = db
#         self.table = table
#         self.task_id = record['id']
#         self.payload = json.dumps(self.record.items(), default=str)
#         self.queue_name = record['worker_code'] or "general"
        
#     def __str__(self):
#         return self.record['task_name']
    
#     def __repr__(self):
#         return str(self)

#     async def completed(self):
#         """
#         The task has been executed and acknowledged, update
#         the last execution timestamp accordingly
#         """
#         self.record['last_execution_ts'] = datetime.now(timezone.utc)
#         await self.update_record()
        
#     async def update_record(self):
#         self.table.update(self.record, self.old_record)
#         self.old_record = copy.deepcopy(self.record)
#         logger.debug("Committing record change")
#         self.db.commit()

    
class GnrTaskScheduler:
    """
    ASyncio application which load the scheduling configuration and
    organize the queue to be served to workers. Responsible to
    compute and put the task in the queue when due.

    Export dashboard and a simple API to control the process
    
    """
    def __init__(self, sitename, host, port):
        self.sitename = sitename
        self.host = host and host or GNR_SCHEDULER_HOST
        self.port = port and port or GNR_SCHEDULER_PORT

        self.app = GnrApp(self.sitename, enabled_packages=['gnrcore:sys'])
        self.db = self.app.db
        self.tasktbl = self.db.table("sys.task")
        self.exectbl = self.db.table("sys.task_execution")
        self.startup_time = datetime.now(timezone.utc)
        
        def async_queue_gen():
            return asyncio.Queue()
        
        self.queues = defaultdict(async_queue_gen)
        
        self.pending_ack = {}
        self.failed_tasks = []
        self.workers = dict()
        self.stale_workers = dict()
        self.tasks = {}  # Loaded tasks from DB or mock
        self.dump_file_name = "gnr_scheduler_queue_dump.json"

    async def load_configuration(self, triggered=False):
        if triggered:
            logger.info("Triggered scheduler configuration loading")

        logger.info("Loading scheduler configuration")

        # FIXME: should be loop over a list of databases to load the tasks?
        all_tasks = self.tasktbl.query("*,parameters", where='$stopped IS NOT TRUE').fetch()
        # FIXME: the db can be provided by the task table when
        # running in a multi-workspace environment
        schedule_keys = ['run_asap','month','day','hour','minute','frequency']
        self.tasks = {}
        for x in all_tasks:
            schedule = {k: x.get(k, None) for k in schedule_keys}
            self.tasks[x['id']] = [GnrTask(name=x['task_name'],
                                           action=x['command'],
                                           db=self.db.dbname,
                                           table_name=x['table_name'],
                                           schedule=schedule,
                                           task_id=x['id'],
                                           saved_query_code=x['saved_query_code'],
                                           parameters=x['parameters']),
                                   x['last_scheduled_ts']]
        
    async def complete_task(self, task_id):
        task = self.tasks.get(task_id)[0]
        if task:
            logger.info("Task %s completed, saving", task_id)
            await task.completed()
        else:
            logger.error("Task %s not found, can't complete", task_id)
            
    async def start_service(self):
        await self.load_configuration()
        await self.load_queue_from_disk()
        logger.info(f"Starting scheduler on {self.host}:{self.port} - dashboard http://{self.host}:{self.port}")
        
        asyncio.create_task(self.schedule_loop())
        asyncio.create_task(self.retry_monitor())


    async def shutdown_scheduler(self):
        logger.info("Scheduler is shutting down")
        await self.dump_queue_to_disk()
        logger.info("Scheduler shutdown complete")
        
    async def dump_queue_to_disk(self):
        try:
            items = []
            for queue_name, queue in self.queues.items():
                while not queue.empty():
                    items.append(queue.get_nowait())
            with open(self.dump_file_name, "w") as f:
                json.dump(items, f)
            for item in items:
                await self.queues[item.get("queue_name")].put(item)  # Restore after peeking
            logger.info(f"Dumped {len(items)} pending queued tasks to disk.")
        except Exception as e:
            raise
            logger.error(f"Failed to dump queue: {e}")

    async def load_queue_from_disk(self):
        try:
            if os.path.exists(self.dump_file_name):
                with open(self.dump_file_name) as f:
                    items = json.load(f)
                for item in items:
                    await self.queues[item['queue_name']].put(item)
                logger.info(f"Loaded {len(items)} pending tasks from disk.")
                os.remove(self.dump_file_name)
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")

    async def retry_monitor(self):
        while True:
            logger.debug("Checking for tasks needing retry...")
            now = datetime.now(timezone.utc)
            for task_id, (task, sent_time, retries, worker_id) in list(self.pending_ack.items()):     
                if worker_id not in self.workers or (now - self.workers[worker_id]['lastseen']).total_seconds() > ACK_TIMEOUT:
                    if retries < RETRY_LIMIT:
                        logger.info("Retrying task %s (%s)", task['task_id'], task['run_id'])
                        await self.queues[task['queue_name']].put(task)
                        self.pending_ack[task_id] = (task, datetime.now(timezone.utc), retries + 1, None)
                    else:
                        logger.error("Task %s (%s) failed after %s retries", task['task_id'], task['run_id'], RETRY_LIMIT)
                        self.failed_tasks.append(task)
                        del self.pending_ack[task_id]
            await asyncio.sleep(SCHEDULER_RUN_INTERVAL*2)
            
    async def empty_queue(self, queue_name):
        # safer way to empty the queue is to just replace
        # the referenced object holding the queue
        # with a new empty one, since there is no clear()
        # we'd have to empty the queue manually requesting
        # all content
        self.queues[queue_name] = asyncio.Queue()

    async def put_task_in_queue(self, task_id, task):
        now = datetime.now(timezone.utc)
        self.tasks[task_id][1] = now
        exec_record = {
            "task_id": task_id,
            "start_ts": now,
        }
        exec_q = self.exectbl.insert(exec_record)
        self.exectbl.db.commit()
        
        task_instance = {
            "run_id": exec_q['id'],
            "task_id": task_id,
            "payload": asdict(task),
            "queue_name": task.queue_name
        }
        logger.info("Scheduling task '%s' (%s - %s)",
                    task, task_id, task_instance['run_id'])
                    
        await self.queues[task.queue_name].put(task_instance)
        
    async def schedule_loop(self):
        while True:
            logger.debug("Checking for next schedule...")
            for task_id, task in self.tasks.items():
                if task[0].is_due(last_scheduled_ts=task[1]):
                    try:
                        await self.put_task_in_queue(task_id, task[0])
                    except Exception as e:
                        logger.error("Unable to schedule task %s - %s", task_id, e)
            await asyncio.sleep(SCHEDULER_RUN_INTERVAL)

    def worker_alive(self, worker_id, queue_name):
        if worker_id not in self.workers:
            self.workers[worker_id] = {"lastseen": datetime.now(timezone.utc),
                                       "worked_tasks": 0,
                                       "queue_name": queue_name}
        else:
            self.workers[worker_id]["lastseen"] = datetime.now(timezone.utc)
        
        
    async def next_task(self, request):
        worker_id = request.query.get("worker_id")
        queue_name = request.query.get("queue_name")
        if worker_id:
            self.worker_alive(worker_id, queue_name)
            logger.info("Worker %s (queue %s) connected", worker_id, queue_name)
            self.workers[worker_id]["worked_tasks"] += 1            
            task = await self.queues[queue_name].get()
            self.pending_ack[task["run_id"]] = (task, datetime.now(timezone.utc), 0, worker_id)
            return web.json_response(task)

    async def acknowledge(self, request):
        data = await request.json()
        run_id = data.get("run_id")
        
        if run_id in self.pending_ack:
            logger.info("Task %s acknowledged", run_id)
            # update the task
            ack_run = self.pending_ack.pop(run_id)
            await self.complete_task(ack_run[0]['task_id'])
            return web.json_response({"status": "acknowledged"})
        return web.json_response({"status": "unknown task"}, status=400)

    async def schedule_single_execution(self, task_def):
        task_name = task_def.get("task_name", f"Manual exec on {task_def.get('table')}")
        task = GnrTask(
            name=task_name,
            db=task_def.get('domains'),
            action=task_def.get('action'),
            table=task_def.get('table'),
            schedule={},
            parameters=task_def.get('parameters'),
            queue_name=task_def.get('worker_code')
        )
        logger.info("New manually scheduled task: %s", task)
        task_id = str(uuid.uuid4())
        self.tasks[None] = [task, None]
        await self.put_task_in_queue(None, task)

        #new_task = GnrTask(db=self.db,
        #                   table=self.tasktbl, task_id=None)
        #    self.put_task_in_queue(task_id, task)
        return "ok"
    
    async def dashboard(self, request):
        template_content = """
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Gnr Scheduler Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.6/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-4Q6Gf2aSP4eDXB8Miphtr37CMZZQ5oXLH2yaXMJ2w8e2ZtHTl7GptT4jmndRuHDT" crossorigin="anonymous">
        </head>
        <script>
        setInterval(function () {
        location.reload();
        }, 2000); 
        </script>
        <body>
        <div class="container">
        <h1>Gnr Scheduler Dashboard</h1>
        <h2>Status</h2>
        <table class="table"><tbody>
        
        <tr><th>Startup time</th><td>${startup_time}</td>
        <th>Server time</th><td>${scheduler_current_time}</td>
        <th>Uptime</th><td>${server_uptime}</td></tr>
        <tr><th>Total tasks</th><td>${total_tasks}</td>
        <th>Total queue size</th><td>${total_queue_size}</td></tr>
        </tbody></table>
        
        <h2>Queue details</h2>
        <table class="table"><thead><tr>
        <th scope="col">Queue</th>
        <th scope="col">Items</th>
        </tr></thead><tbody>
        % for w in queues_sizes.items():
        <tr>
        <td>${w[0]}</td>
        <td>${w[1]}</td>
        </tr>
        % endfor
        </tbody></table>
        
        <h2>Running workers</h2>
        % if workers:
        <table class="table"><thead><tr>
        <th scope="col">Worker ID</th>
        <th scope="col">Queue</th>
        <th scope="col">Last seen</th>
        <th scope="col">Worked tasks</th>
        </tr></thead><tbody>
        % for w in workers.items():
        <tr>
        <td>${w[0]}</td>
        <td>${w[1]['queue_name']}</td>
        <td>${w[1]['lastseen']}</td>
        <td>${w[1]['worked_tasks']}</td>
        </tr>
        % endfor
        </tbody></table>
        % else:
        <div class="alert alert-danger" role="alert">
        No workers connected!
        </div>
        % endif

        <h2>Pending Acknowledgements</h2>
        % if pending:
        <table class="table"
        <thead><tr>
        <th scope="col">Queue</th>
        <th scope="col">Run ID</th>
        <th scope="col">Since</th>
        </tr></thead><tbody>
        % for k,v in pending.items():
        <tr>
        <td>${v[0]['queue_name']}</td>
        <td>${k}</td><td>${v[1]}</td>
        </tr>
        % endfor
        </tbody></table>
        % else:
        <div class="alert alert-success" role="alert">
        No pending acks
        </div>
        % endif
        
        <h2>Failed tasks</h2>
        % if failed:
        <table class="table">
        <thead><tr>
        <th scope="col">Queue</th>
        <th scope="col">Task Id</th>
        <th scope="col">Run id</th>
        </tr></thead><tbody>
        % for a in failed:
        <tr><td>${a['queue_name']}</td>
        <td>${a['task_id']}</td>
        <td>${a['run_id']}</td></tr>
        % endfor
        </tbody></table>
        % else:
        <div class="alert alert-success" role="alert">
        No failed tasks.
        </div>
        % endif
        </div>
        </body></html>
        """
        t = Template(template_content, strict_undefined=True)
        
        payload = self._get_status()
        return web.Response(
            text=t.render(**payload),
            content_type="text/html"
        )

    def _get_status(self):
        now = datetime.now(timezone.utc)
        return {
            "total_tasks": len(self.tasks),
            "total_queue_size": sum([x.qsize() for x in self.queues.values()]),
            "queues_sizes": {k: v.qsize() for k,v in self.queues.items()},
            "workers": self.workers,
            "workers_total": len(self.workers),
            "pending": self.pending_ack,
            "failed": self.failed_tasks,
            "scheduler_current_time": now,
            "startup_time": self.startup_time,
            "server_uptime": now - self.startup_time

        }



    async def api_worker_alive(self, request):
        worker_id = request.query.get("worker_id")
        queue_name = request.query.get("queue_name")
        logger.debug(f"Worker %s/%s is alive", worker_id, queue_name)
        self.worker_alive(worker_id, queue_name)
        return web.json_response(dict(status="ack"))
    
    async def api_worker_leave(self, request):
        """
        Endpoint for workers telling us they're quitting the job.

        It just remove the worker from the monitoring list.
        """
        worker_id = request.query.get("worker_id")
        if worker_id and worker_id in self.workers:
            logger.info("Worker %s disconnected", worker_id)
            self.workers.pop(worker_id)
        return web.json_response(dict(status="bye"))

    async def api_execute(self, request):
        # immediately execute a task
        r = await self.schedule_single_execution(request.query)
        return web.Response(text=r,
                            content_type="text/plain")
    
    async def api_stop_run(self, request):
        # TBD
        return web.Response(text="ok",
                            content_type="text/plain")
        
    async def api_metrics(self, request):
        return web.Response(text="\n".join(f"{k} {v}" for k, v in self._get_status().items() if k != 'workers'),
                            content_type="text/plain")

    async def api_status(self, request):
        return web.Response(text=json.dumps(self._get_status(), default=str),
                            content_type="application/json")

    async def api_update_task(self, request):
        """
        Receive a new task definition when a task is updated/inserted
        """
        pass
    
    async def api_reload(self, request):
        await self.load_configuration(triggered=True)
        return web.json_response({"reload": "requested"})
    
    async def api_empty_queue(self, request):
        queue = request.query.get("queue_name", "general")
        r = await self.empty_queue(queue)
        # check for r and raise http error
        return web.Response(text="OK", content_type="text/plain")

    async def api_gen_fake(self, request):
        for x in range(int(request.query.get("quantity"))):
            for task_id, task in self.tasks.items():
                await self.put_task_in_queue(task_id, task)
           
        return web.Response(text="OK", content_type="text/plain")
    
    
    def create_app(self):
        app = web.Application()
        app.on_shutdown.append(lambda app: self.shutdown_scheduler())
        app.add_routes([
            web.get("/execute", self.api_execute),
            web.get("/stop_run", self.api_stop_run),
            web.get("/reload", self.api_reload),
            web.get("/empty_queue", self.api_empty_queue),
            web.get("/gen_fake", self.api_gen_fake),
            web.get("/next-task", self.next_task),
            web.get("/leave", self.api_worker_leave),
            web.get("/alive", self.api_worker_alive),
            web.post("/ack", self.acknowledge),
            web.get("/", self.dashboard),
            web.get("/metrics", self.api_metrics),
            web.get("/status", self.api_status),
        ])
        app.on_startup.append(lambda app: self.start_service())
        return app
    
    def start(self):
        logger.info("Starting Task Scheduler for site: %s", self.sitename)
        web.run_app(self.create_app(), host=self.host, port=self.port)


############ WORKER CODE #####################################

def execute_task(sitename, task):
    app = GnrApp(sitename, enabled_packages=['gnrcore:sys'])
    # task.db contains the name of the database
    db = app.db
    site = GnrWsgiSite(sitename)
    tasktbl = db.table("sys.task")
    logger.info("Executing %s - run %s", task['task_id'] ,task['run_id'])    

    page = site.dummyPage
    site.currentPage = page
    page._db = None
    page.db
    record = task['payload'] #{x[0]:x[1] for x in task['payload']}
    task_class = tasktbl.getBtcClass(table=record['table_name'],
                                     command=record['action'],
                                     page=page
                                     )
    if task_class:
        task_obj = task_class(page=page, resource_table=page.db.table(record['table_name']),
                              batch_selection_savedQuery=record['saved_query_code'])
        task_params = record.get('parameters', {})
        with db.tempEnv(connectionName="execution"):
            logger.info("Executing task %s - %s",
                        record['table_name'],
                        record['action'])
            task_obj(parameters=Bag(task_params),task_execution_record=record)
    else:
        logger.error("Can't find task class for command %s", record['action'])
            
    try:
        with requests.post(f"{GNR_SCHEDULER_URL}/ack", json={"run_id": task["run_id"]}) as resp:
            logger.info("Acknowledged run %s, response %s", task['run_id'], resp.text)
    except Exception as e:
        logger.exception(e)
        logger.error("Failed to acknowledge task run %s: %s", task['run_id'], e)
        
class GnrTaskWorker:
    """
    Asyncio application which polls the schedulers queue, and execute
    the task when found in the queue. Can poll only specific queues if needed,
    otherwise it will consume the general queue.

    The execution is synchronous within the single worker process.
    """
    def __init__(self, sitename, queue_name=None, processes=1):
        self.processes = processes
        self.worker_id = os.environ.get("GNR_WORKER_ID", f"gnrworker-{socket.getfqdn()}-{os.getpid()}")
        self.queue_name = queue_name or os.environ.get("GNR_WORKER_QUEUE_NAME", "general")
        self.sitename = sitename
        self.site = GnrWsgiSite(self.sitename)
        self.scheduler_url = GNR_SCHEDULER_URL

        self.app = GnrApp(self.sitename, enabled_packages=['gnrcore:sys'])
        self.db = self.app.db
        self.tasktbl = self.db.table("sys.task")
        
        self.loop = None
        self.stop_evt = threading.Event()
        # the local queue has the size of the maximum
        # executor process, otherwise the first worker in a cluster
        # will get all the tasks
        self.tasks_q = asyncio.Queue(maxsize=self.processes)
        self.process_pool = None
        
    def _notify_alive(self):
        with requests.Session() as session:
            try:
                logger.debug("Pinging scheduler")
                resp = session.get(
                    f"{self.scheduler_url}/alive",
                    params={"worker_id": self.worker_id, "queue_name": self.queue_name},
                    timeout=NOTIFY_ALIVE_INTERVAL * 2,
                )
                if resp.status_code == 200:
                    logger.debug("Scheduler pinged")
                else:
                    logger.warning("Scheduler alive returned %s", resp.status_code)
            except Exception as e:
                logger.error("Notify alive error: %s", e)
        
    async def worker_alive(self):
        while not self.stop_evt.is_set():
            await asyncio.sleep(NOTIFY_ALIVE_INTERVAL)
            await asyncio.to_thread(self._notify_alive)


    async def poll(self):
        while not self.stop_evt.is_set():
            session_timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                logger.debug("Connecting to scheduler")
                try:
                    async with session.get(f"{self.scheduler_url}/next-task",
                                           params={"worker_id": self.worker_id,
                                                   "queue_name": self.queue_name}) as resp:
                        if resp.status == 200:
                            task = await resp.json()
                            logger.info("%s got new task: %s", self.worker_id, task)
                            await self.tasks_q.put(task)
                            logger.info("Hello")
                except Exception:
                    await asyncio.sleep(5)
                    
    async def executor(self, name):
        while not self.stop_evt.is_set():
            logger.info("Executor %s - Checking for new tasks to be executed", name)
            task = await self.tasks_q.get()
            if task is None:
                logger.debug("No tasks, idling")
                self.tasks_q.task_done()
                continue
            try:
                res = await self.loop.run_in_executor(self.process_pool, execute_task, self.sitename, task)
            except Exception as e:
                logger.error("Executor %s error: %s", name, e)
                logger.exception(e)
            finally:
                self.tasks_q.task_done()
              
    async def shutdown_worker(self, consumers, alive_task):
        logger.info("Worker is shutting down")
        self.stop_evt.set()
        for _ in consumers:
            await self.tasks_q.put(None)
        await asyncio.gather(*consumers, return_exceptions=True)
        alive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await alive_task
        if self.process_pool:
            self.process_pool.shutdown(wait=True, cancel_futures=False)
        await self.say_goodbye()
        
        logger.info("Worker shutdown complete")

    async def say_goodbye(self):
        """
        Inform the scheduler queue that the workers is leaving
        """
        logger.info("Saying good by to scheduler/queue")
        session_timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=session_timeout) as session:
            try:
                async with session.get(f"{self.scheduler_url}/leave", params={"worker_id": self.worker_id}) as resp:
                    if resp.status == 200:
                        logger.info("Informed scheduler, got %s response", resp.status)
                        return True
                    logger.warning("Scheduler leave returned %s", resp.status)
            except Exception as e:
                logger.error("Unable to leave scheduler: %s", e)
        return False

    async def start(self):

        logger.info("Starting Task Worker %s for site %s - queue %s - %s procs ",
                    self.worker_id, self.sitename,
                    self.queue_name,
                    self.processes)

        self.loop = asyncio.get_running_loop()
        self.process_pool = ProcessPoolExecutor(max_workers=self.processes)

        consumers = [
            asyncio.create_task(self.executor(f"E{i}")) for i in range(self.processes)
        ]
        poller_task = asyncio.create_task(self.poll())
        alive_task = asyncio.create_task(self.worker_alive())
        
        # signals
        stop = asyncio.Event()
        
        def _signal(*_):
            stop.set()
        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if sig:
                with contextlib.suppress(NotImplementedError):
                    self.loop.add_signal_handler(sig, _signal)

        await stop.wait()
        await self.shutdown_worker(consumers, alive_task)
        

