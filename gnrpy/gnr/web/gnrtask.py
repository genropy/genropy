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
import copy
import random
import requests
import json
import socket
import uuid
from datetime import datetime, timezone
from collections import defaultdict

from mako.template import Template
import aiohttp
import asyncio
from aiohttp import web

from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.web import logger

GNR_SCHEDULER_PORT=int(os.environ.get("GNR_SCHEDULER_PORT", "14951"))
GNR_SCHEDULER_HOST=os.environ.get("GNR_SCHEDULER_HOST", "127.0.0.1")
GNR_SCHEDULER_URL=os.environ.get("GNR_SCHEDULER_URL", f"http://{GNR_SCHEDULER_HOST}:{GNR_SCHEDULER_PORT}")

RETRY_LIMIT = 3
ACK_TIMEOUT = 15  # seconds

class GnrTaskSchedulerClient:
    """
    A simple object to interact with the scheduler APIs
    """
    def __init__(self, url=None, page=None):
        self.url = url and url or GNR_SCHEDULER_URL
        self.page = page
        
    def _call(self, uri, params=None):
        try:
            return requests.get(f"{self.url}/{uri}", params=params)
        except Exception as e:
            if self.page:
                self.page.clientPublish('floating_message',
                                        message='Unable to contact scheduler',
                                        messageType='warning')
            logger.error("Unable to contact scheduler: %s", e)
            
    def reload(self):
        r = self._call("reload")
        return r 

    def status(self):
        r = self.call("status")
        return r and r.json() or r.status_code

    def empty_queue(self, queue_name):
        r = self.call("empty_queue", dict(queue_name=queue_name))
        return r
    
    def gen_fake(self, quantity):
        r = self.call("gen_fake", dict(quantity=quantity))
                                       
class GnrTask(object):
    def __init__(self, record, db, table):
        self.record = record
        self.old_record = copy.deepcopy(self.record)
        self.db = db
        self.table = table
        self.task_id = record['id']
        self.payload = json.dumps(self.record.items(), default=str)
        self.queue_name = record['worker_code'] or "general"
        
    def __str__(self):
        return self.record['task_name']
    
    def __repr__(self):
        return str(self)

    async def completed(self):
        """
        The task has been executed and acknowledged, update
        the last execution timestamp accordingly
        """
        self.record['last_execution_ts'] = datetime.now(timezone.utc)
        await self.update_record()
        
    async def update_record(self):
        self.table.update(self.record, self.old_record)
        self.old_record = copy.deepcopy(self.record)
        logger.debug("Committing record change")
        self.db.commit()

    def is_due(self, timestamp=None):
        """
        Compute if the task is to be executed
        """
        if not timestamp:
            timestamp = datetime.now(timezone.utc)

        result = []
                
        if self.record['run_asap']:
            return '*'

        if self.record['frequency']:
            last_scheduled_ts = self.record['last_scheduled_ts']
            if last_scheduled_ts is None or (timestamp - last_scheduled_ts.replace(tzinfo=timezone.utc)).seconds/60. >= self.record['frequency']:
                return '*'
            else:
                return False
            
        if not self.record['minute']:
            return False
        
        months =  [int(x.strip()) for x in self.record['month'].split(',')] if self.record['month'] else range(1,13)
        days = [int(x.strip()) for x in self.record['day'].split(',')] if self.record['day'] else range(1,32)
        hours = [int(x.strip()) for x in self.record['hour'].split(',')] if self.record['hour'] else range(0,24)
        minutes = [int(x.strip()) for x in self.record['minute'].split(',')]
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
    
class GnrTaskScheduler:
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

        all_tasks = self.tasktbl.query("*,parameters", where='$stopped IS NOT TRUE').fetch()
        self.tasks = {x['id']: GnrTask(x, self.db, self.tasktbl) for x in all_tasks}
        
    async def complete_task(self, task_id):
        task = self.tasks.get(task_id)
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
            now = datetime.now(timezone.utc)
            to_retry = []
            for task_id, (task, sent_time, retries) in list(self.pending_ack.items()):
                print(task)
                print(task_id)
                if (now - sent_time).total_seconds() > ACK_TIMEOUT:
                    if retries < RETRY_LIMIT:
                        logger.info("Retrying task %s (%s)", task['task_id'], task['run_id'])
                        await self.queues[task['queue_name']].put(task)
                        self.pending_ack[task_id] = (task, datetime.now(timezone.utc), retries + 1)
                    else:
                        logger.error("Task %s (%s) failed after %s retries", task['task_id'], task['run_id'], RETRY_LIMIT)
                        self.failed_tasks.append(task)
                        del self.pending_ack[task_id]
            await asyncio.sleep(5)

    async def schedule_loop(self):
        while True:
            logger.debug("Checking for next schedule...")
            now = datetime.now(timezone.utc)
            for task_id, task in self.tasks.items():
                if task.is_due():
                    task.record['last_scheduled_ts'] = datetime.now(timezone.utc)
                    task_instance = {
                        "run_id": str(uuid.uuid4()),
                        "task_id": task.task_id,
                        "payload": task.payload,
                        "queue_name": task.queue_name
                        
                    }
                    logger.info("Scheduling task '%s' (%s - %s)",
                                task, task_id, task_instance['run_id'])
                    await self.queues[task.queue_name].put(task_instance)
            await asyncio.sleep(1)

    async def worker_leave(self, request):
        """
        Endpoint for workers telling us they're quitting the job.

        It just remove the worker from the monitoring list.
        """
        worker_id = request.query.get("worker_id")
        if worker_id and worker_id in self.workers:
            logger.info("Worker %s disconnected", worker_id)
            self.workers.pop(worker_id)
        return web.json_response(dict(status="bye"))
        
    async def next_task(self, request):
        worker_id = request.query.get("worker_id")
        queue_name = request.query.get("queue_name")
        if worker_id:
            if worker_id not in self.workers:
                logger.info("Worker %s (queue %s) connected", worker_id, queue_name)
                self.workers[worker_id] = {"lastseen": str(datetime.now(timezone.utc)),
                                           "worked_tasks": 1,
                                           "queue_name": queue_name}
            else:
                self.workers[worker_id]["lastseen"] = str(datetime.now(timezone.utc))
                self.workers[worker_id]["worked_tasks"] += 1
                
        task = await self.queues[queue_name].get()
        self.pending_ack[task["run_id"]] = (task, datetime.now(timezone.utc), 0)
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
        <p>Startup time: <span class="badge text-bg-secondary">${startup_time}</span></p>
        <p>Current scheduler server time: <span class="badge text-bg-secondary">${scheduler_current_time}</span></p>
        <p>Total configured tasks: <span class="badge text-bg-secondary">${total_tasks}</span></p>
        <p>Total Queue size: <span class="badge text-bg-secondary">${total_queue_size}</span></p>
        <h2>Queues</h2>
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
        return {
            "total_tasks": len(self.tasks),
            "total_queue_size": sum([x.qsize() for x in self.queues.values()]),
            "queues_sizes": {k: v.qsize() for k,v in self.queues.items()},
            "workers": self.workers,
            "workers_total": len(self.workers),
            "pending": self.pending_ack,
            "failed": self.failed_tasks,
            "scheduler_current_time": datetime.now(timezone.utc),
            "startup_time": self.startup_time

        }
    
    async def api_metrics(self, request):
        return web.Response(text="\n".join(f"{k} {v}" for k, v in self._get_status().items() if k != 'workers'),
                            content_type="text/plain")

    async def api_status(self, request):
        return web.Response(text=json.dumps(self._get_status(), default=str),
                            content_type="application/json")

    async def api_reload(self, request):
        await self.load_configuration(triggered=True)
        return web.json_response({"reload": "requested"})
    
    async def api_empty_queue(self, request):
        pass

    async def api_gen_fake(self, request):
        pass
    
    
    
    def create_app(self):
        app = web.Application()
        app.on_shutdown.append(lambda app: self.shutdown_scheduler())
        app.add_routes([
            web.get("/reload", self.api_reload),
            web.get("/next-task", self.next_task),
            web.get("/leave", self.worker_leave),
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

class GnrTaskWorker:
    def __init__(self, sitename, host, port, queue_name=None):
        self.host = host and host or "127.0.0.1"
        self.port = port and port or random.randint(20000,30000)
        self.worker_id = os.environ.get("GNR_WORKER_ID", f"gnrworker-{socket.getfqdn()}-{os.getpid()}")
        self.queue_name = queue_name or os.environ.get("GNR_WORKER_QUEUE_NAME", "general")
        self.sitename = sitename
        self.site = GnrWsgiSite(self.sitename)
        self.scheduler_url = GNR_SCHEDULER_URL

        self.app = GnrApp(self.sitename, enabled_packages=['gnrcore:sys'])
        self.db = self.app.db
        self.tasktbl = self.db.table("sys.task")

    async def start_service(self):
        asyncio.create_task(self.fetch_and_execute())
        
    async def fetch_and_execute(self):
        try:
            session_timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                while True:
                    try:
                        logger.debug("Connecting to scheduler")
                        async with session.get(f"{self.scheduler_url}/next-task",
                                               params={"worker_id": self.worker_id,
                                                       "queue_name": self.queue_name}) as resp:
                            if resp.status == 200:
                                logger.info("%s got new task: ", self.worker_id)
                                task = await resp.json()
                                await self.execute_task(task, session)
                    except Exception as e:
                        logger.error(e)
                        # wait before reconnect
                        await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise
        
    async def execute_task(self, task, session):
        logger.info("Executing %s - run %s", task['task_id'] ,task['run_id'])
        page = self.site.dummyPage
        self.site.currentPage = page
        page._db = None
        page.db
        
        record = {x[0]:x[1] for x in json.loads(task['payload'])}
        
        task_class = self.tasktbl.getBtcClass(table=record['table_name'],
                                              command=record['command'],
                                              page=page
                                              )
        if task_class:
            task_obj = task_class(page=page, resource_table=page.db.table(record['table_name']),
                                  batch_selection_savedQuery=record['saved_query_code'])
            task_params = record.get('parameters', {})
            with self.db.tempEnv(connectionName="execution"):
                logger.info("Executing task %s - %s",
                            record['table_name'],
                            record['command'])
                task_obj(parameters=Bag(task_params),task_execution_record=record)
        else:
            logger.error("Can't find task class for command %s", record['command'])
            
        try:
            async with session.post(f"{self.scheduler_url}/ack", json={"run_id": task["run_id"]}) as resp:
                logger.info("Acknowledged run %s, response %s", task['run_id'], await resp.text())
        except Exception as e:
            logger.error("Failed to acknowledge task run %s: %s", task['run_id'], e)

    async def shutdown_worker(self):
        logger.info("Worker is shutting down")
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
            except Exception as e:
                logger.error("Unable to leave scheduler: %s", e)
        
    def create_app(self):
        app = web.Application()
        app.on_shutdown.append(lambda app: self.shutdown_worker())
        app.on_startup.append(lambda app: asyncio.create_task(self.start_service()))
        return app
    
    def start(self):
        logger.info("Starting Task Worker %s for site %s - queue %s on http://%s:%s ",
                    self.worker_id, self.sitename,
                    self.queue_name,
                    self.host, self.port)
        web.run_app(self.create_app(), host=self.host, port=self.port)
                    
