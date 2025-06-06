import os
import time
import signal
import random
import requests
import json
import socket
import uuid
from datetime import datetime, timedelta

from mako.template import Template
import aiohttp
import asyncio
from aiohttp import web

from gnr.app.gnrapp import GnrApp

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
        
    def _call(self, uri):
        try:
            return requests.get(f"{self.url}/{uri}")
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
        r = self_call("status")
        return r and r.json() or r.status_code

# [id=KsHEQhCJOrCCSLDqcNA6Uw,
#  __ins_ts=2025-06-03 14:24:35.509291,
#  __del_ts=None,
#  __mod_ts=2025-06-03 16:50:15.044202,
#  __ins_user=cgabriel,
#  table_name=fatt.prodotto,
#  task_name=Task test,
#  command=action/cambia_prezzi,
#  month=None,
#  day=None,
#  weekday=None,
#  hour=None,
#  minute=None,
#  frequency=1,
#  last_scheduled_ts=2025-06-03 16:50:15.031971,
#  last_execution_ts=None,
#  last_error_ts=None,
#  run_asap=None,
#  max_workers=None,
#  log_result=None,
#  user_id=rwWx_Mw1O1OrkFfNY9VXMg,
#  date_start=None,
#  date_end=None,
#  stopped=None,
#  worker_code=None,
#  saved_query_code=None,
#  pkey=KsHEQhCJOrCCSLDqcNA6Uw]

    
class GnrTask(object):
    def __init__(self, record):
        self.record = record
        self.task_id = record['id']
        self.payload = json.dumps(self.record.items(), default=str)

    def __str__(self):
        return self.record['task_name']
    
    def __repr__(self):
        return str(self)

    def completed(self):
        """
        The task has been executed and acknoledged, update
        the last execution timestamp accordingly
        """
        self.record['last_execution_ts'] = "FIXME"
        # FIXME
        
    def is_due(self, timestamp=None):
        """
        Compute if the task is to be executed
        """
        if not timestamp:
            timestamp = datetime.now()

        result = []
                
        if self.record['run_asap']:
            return '*'
        
        if self.record['frequency']:
            last_scheduled_ts = self.record['last_scheduled_ts']
            if last_scheduled_ts is None or (timestamp - last_scheduled_ts).seconds/60. >= self.record['frequency']:
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
        self.exectbl = self.db.table("sys.task")
        self.task_queue = asyncio.Queue()
        
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

        all_tasks = self.tasktbl.query(where='$stopped IS NOT TRUE').fetch()
        self.tasks = {x['id']: GnrTask(x) for x in all_tasks}
        

    async def start_service(self):
        await self.load_configuration()
        await self.load_queue_from_disk()
        asyncio.create_task(self.schedule_loop())
        asyncio.create_task(self.retry_monitor())


    async def shutdown_scheduler(self):
        logger.info("Scheduler is shutting down")
        await self.dump_queue_to_disk()
        logger.info("Scheduler shutdown complete")
        
    async def dump_queue_to_disk(self):
        try:
            items = []
            while not self.task_queue.empty():
                items.append(self.task_queue.get_nowait())
            with open(self.dump_file_name, "w") as f:
                json.dump(items, f)
            for item in items:
                await self.task_queue.put(item)  # Restore after peeking
            logger.info(f"Dumped {len(items)} pending queued tasks to disk.")
        except Exception as e:
            logger.error(f"Failed to dump queue: {e}")

    async def load_queue_from_disk(self):
        try:
            if os.path.exists(self.dump_file_name):
                with open(self.dump_file_name) as f:
                    items = json.load(f)
                for item in items:
                    await self.task_queue.put(item)
                logger.info(f"Loaded {len(items)} pending tasks from disk.")
                os.remove(self.dump_file_name)
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")

    async def retry_monitor(self):
        while True:
            now = datetime.utcnow()
            to_retry = []
            for task_id, (task, sent_time, retries) in list(self.pending_ack.items()):
                if (now - sent_time).total_seconds() > ACK_TIMEOUT:
                    if retries < RETRY_LIMIT:
                        logger.info("Retrying task %s (%s)", task, task_id)
                        await self.task_queue.put(task)
                        self.pending_ack[task_id] = (task, datetime.utcnow(), retries + 1)
                    else:
                        logger.error("Task %s (%s) failed after %s retries", task, task_id, RETRY_LIMIT)
                        self.failed_tasks.append(task)
                        del self.pending_ack[task_id]
            await asyncio.sleep(5)

    async def schedule_loop(self):
        while True:
            now = datetime.utcnow()
            for task_id, task in self.tasks.items():
                if task.is_due():
                    task_instance = {
                        "run_id": str(uuid.uuid4()),
                        "task_id": task.task_id,
                        "payload": task.payload
                    }
                    logger.info("Scheduling task '%s' (%s - %s)",
                                task, task_id, task_instance['run_id'])
                    await self.task_queue.put(task_instance)
            await asyncio.sleep(5)

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
        if worker_id:
            if worker_id not in self.workers:
                logger.info("Worker %s connected", worker_id)
            self.workers[worker_id] = {"lastseen": datetime.utcnow()}
        task = await self.task_queue.get()
        self.pending_ack[task["run_id"]] = (task, datetime.utcnow(), 0)
        return web.json_response(task)

    async def acknowledge(self, request):
        data = await request.json()
        run_id = data.get("run_id")
        if run_id in self.pending_ack:
            logger.info("Task %s acknowledged", run_id)
            del self.pending_ack[run_id]
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
        <body>
        <div class="container">
        <h1>Gnr Scheduler Dashboard</h1>
        <p>Total configured tasks: <span class="badge text-bg-secondary">${total_tasks}</span></p>
        <p>Queue size: <span class="badge text-bg-secondary">${queue_size}</span></p>
        <h2>Workers</h2>
        % if workers:
        <table class="table"><thead><tr>
        <th scope="col">Worker ID</th>
        <th scope="col">Last seen</th>
        </tr></thead><tbody>
        % for w in workers:
        <tr>
         <td>${w[0]}</td><td>${w[1]['lastseen']}</td>
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
        <table class="table>
        <thead><tr>
        <th scope="col"></th>
        <th scope="col"></th>
        </tr></thead><tbody>
        % for a in pending:
        <tr>
        <td>${a[0]}</td>${a[1]}</td>
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
        <table class="table>
        <thead><tr>
        <th scope="col">Task Id</th>
        <th scope="col">Task Name</th>
        <th scope="col">Run id</th>
        </tr></thead><tbody>
        % for a in failed:
        <tr><td>${a['task_id']}</td><td>${a['task_name']}</td>
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

        payload = {
            "total_tasks": len(self.tasks),
            "queue_size": self.task_queue.qsize(),
            "workers": self.workers.items(),
            "pending": self.pending_ack.items(),
            "failed": self.failed_tasks
        }
        return web.Response(text=t.render(**payload), content_type="text/html")

    def _get_status(self):
        return {
            'gnr_scheduler_task_queue_size': self.task_queue.qsize(),
            'gnr_scheduler_workers_total': len(self.workers),
            'gnr_scheduler_tasks_failed_total': len(self.failed_tasks),
            'gnr_scheduler_tasks_pending_ack': len(self.pending_ack),
        }
        
    async def metrics(self, request):
        return web.Response(text="\n".join(f"{k} {v}" for k, v in self._get_status()),
                            content_type="text/plain")

    async def reload(self, request):
        await self.load_configuration(triggered=True)
        return web.json_response({"reload": "requested"})
    
    async def status(self, request):
        return web.Response(text=json.dumps(self._get_status()),
                            content_type="application/json")
    
    def create_app(self):
        app = web.Application()
        app.on_shutdown.append(lambda app: self.shutdown_scheduler())
        app.add_routes([
            web.get("/reload", self.reload),
            web.get("/next-task", self.next_task),
            web.get("/leave", self.worker_leave),
            web.post("/ack", self.acknowledge),
            web.get("/", self.dashboard),
            web.get("/metrics", self.metrics),
            web.get("/status", self.status),
        ])
        app.on_startup.append(lambda app: self.start_service())
        return app
    
    def start(self):
        logger.info("Starting Task Scheduler for site: %s", self.sitename)
        web.run_app(self.create_app(), host=self.host, port=self.port)

class GnrTaskWorker:
    def __init__(self, sitename, host, port):
        self.host = host and host or "127.0.0.1"
        self.port = port and port or random.randint(20000,30000)
        self.worker_id = os.environ.get("GNR_WORKER_ID", f"gnrworker-{socket.getfqdn()}-{os.getpid()}")

        self.sitename = sitename
        self.scheduler_url = GNR_SCHEDULER_URL

        self.executed = []

    async def start_service(self):
        asyncio.create_task(self.fetch_and_execute())
        
    async def fetch_and_execute(self):
        try:
            session_timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                while True:
                    try:
                        async with session.get(f"{self.scheduler_url}/next-task", params={"worker_id": self.worker_id}) as resp:
                            if resp.status == 200:
                                logger.info("%s got new task!", self.worker_id)
                                task = await resp.json()
                                await self.execute_task(task, session)
                    except Exception as e:
                        logger.error("Request error: %s", e)
                        await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise
        
    async def execute_task(self, task, session):
        logger.info("Executing %s", str(task))
        payload = json.loads(task['payload'])
        # Simulated execution logic
        #await asyncio.sleep(random.randint(1,3))
        self.executed.append(task)
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

        async def dashboard(request):
            return {"executed": self.executed, "worker_id": self.worker_id}
        app.add_routes([web.get("/dashboard", dashboard)])
        
        app.on_startup.append(lambda app: asyncio.create_task(self.start_service()))
        return app
    
    def start(self):
        logger.info("Starting Task Worker %s for site %s on http://%s:%s ",
                    self.worker_id, self.sitename,
                    self.host, self.port)
        web.run_app(self.create_app(), host=self.host, port=self.port)
                    
