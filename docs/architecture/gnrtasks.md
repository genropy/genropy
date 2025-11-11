# GnrTask Module Documentation

## Overview

The `gnr.web.gnrtask` module provides a distributed task scheduling and execution system for Genropy applications. It implements an asynchronous scheduler-worker architecture similar to systems like Celery or RQ, designed to execute scheduled and on-demand tasks across multiple worker processes.

**Module Location:** `gnr/web/gnrtask.py`
**CLI Tools:** `gnr/web/cli/gnrtaskcontrol.py`, `gnrtaskscheduler.py`, `gnrtaskworker.py`
**Tests:** `tests/web/gnrtask_test.py`

## Architecture

```
┌────────────────────────────────────────────────────────┐
│              sys.task (Database Table)                 │
│  • Task definitions and schedules                      │
│  • Cron-like or frequency-based scheduling             │
│  • Last execution timestamps                           │
└───────────────────────┬────────────────────────────────┘
                        │
                        ↓ (Loads on startup/reload)
┌────────────────────────────────────────────────────────┐
│         GnrTaskScheduler (AsyncIO Service)             │
│  Host: 127.0.0.1 (default) | Port: 14951 (default)    │
│                                                         │
│  • Loads task configurations from database             │
│  • Determines when tasks are due                       │
│  • Manages multiple named queues (general, custom...)  │
│  • Tracks worker health via heartbeat                  │
│  • Handles task retries (up to 3 attempts)             │
│  • Provides web dashboard + REST API                   │
│  • Queue persistence (disk dump/restore)               │
└───────────────────────┬────────────────────────────────┘
                        │
                        ↓ (HTTP long-polling)
┌────────────────────────────────────────────────────────┐
│       GnrTaskWorker (AsyncIO + ProcessPool)            │
│  • Polls scheduler for tasks via /next-task            │
│  • Executes tasks in ProcessPoolExecutor               │
│  • Sends heartbeat every 2 seconds                     │
│  • Acknowledges completed tasks via /ack               │
│  • Supports multiple executor processes                │
│  • Graceful shutdown (SIGINT/SIGTERM)                  │
└────────────────────────────────────────────────────────┘
```

## Core Components

### 1. GnrTaskScheduler

**Location:** `gnrtask.py:211-664`

An asyncio-based HTTP service that manages task scheduling and queue distribution.

#### Key Features
- **Configuration Loading:** Loads tasks from `sys.task` table on startup or via `/reload` endpoint
- **Schedule Evaluation:** Checks every 1 second if tasks are due based on:
  - `run_asap` flag for immediate execution
  - `frequency` (in minutes) for interval-based scheduling
  - Calendar schedule (month/day/hour/minute) for cron-like scheduling
- **Queue Management:** Supports multiple named queues (default: "general")
- **Worker Tracking:** Monitors worker health via heartbeat (2-second intervals)
- **Retry Mechanism:** Automatically retries failed tasks up to 3 times
- **Persistence:** Dumps pending queue items to disk on shutdown, restores on startup
- **Web Dashboard:** Provides real-time monitoring UI at `http://host:port/`
- **REST API:** Exposes control and status endpoints

#### Initialization

```python
scheduler = GnrTaskScheduler(
    sitename="mysite",
    host="127.0.0.1",  # Optional, defaults to GNR_SCHEDULER_HOST
    port=14951         # Optional, defaults to GNR_SCHEDULER_PORT
)
scheduler.start()
```

#### Internal State
- `tasks` (dict): Loaded task configurations `{task_id: [GnrTask, last_scheduled_ts]}`
- `queues` (defaultdict): Named asyncio queues `{queue_name: asyncio.Queue()}`
- `workers` (dict): Active workers `{worker_id: {lastseen, worked_tasks, queue_name}}`
- `pending_ack` (dict): Tasks awaiting acknowledgment `{run_id: (task, sent_time, retries, worker_id)}`
- `failed_tasks` (list): Tasks that exceeded retry limit

#### Background Tasks
- **`schedule_loop()`**: Evaluates task schedules every 1 second
- **`retry_monitor()`**: Checks for stale workers and retries tasks every 2 seconds

### 2. GnrTaskWorker

**Location:** `gnrtask.py:704-854`

An asyncio worker process that polls the scheduler and executes tasks in parallel.

#### Key Features
- **Long-polling:** Continuously polls `/next-task` endpoint for work
- **Parallel Execution:** Uses `ProcessPoolExecutor` for concurrent task execution
- **Heartbeat:** Sends alive signal to scheduler every 2 seconds
- **Graceful Shutdown:** Handles SIGINT/SIGTERM, completes in-flight tasks
- **Queue Selection:** Can subscribe to specific named queues

#### Initialization

```python
worker = GnrTaskWorker(
    sitename="mysite",
    queue_name="general",  # Optional, defaults to "general" or GNR_WORKER_QUEUE_NAME
    processes=1            # Number of parallel executor processes
)
asyncio.run(worker.start())
```

#### Worker ID
Automatically generated as: `gnrworker-{hostname}-{pid}`
Can be overridden via `GNR_WORKER_ID` environment variable.

#### Execution Flow
1. **Poll:** Request `/next-task?worker_id=xxx&queue_name=yyy`
2. **Receive:** Get task from scheduler
3. **Execute:** Run `execute_task()` in separate process
4. **Acknowledge:** POST to `/ack` with `run_id`

### 3. GnrTask

**Location:** `gnrtask.py:139-209`

A dataclass representing a schedulable task.

#### Fields
```python
@dataclass
class GnrTask:
    name: str               # Human-readable task name
    action: str             # BTC command to execute
    db: Any                 # Database name
    table_name: Any         # Table to operate on
    schedule: dict          # Scheduling parameters
    task_id: str = None     # sys.task.id reference
    user: str = None        # User context
    domain: str = None      # Domain/tenant context
    saved_query_code: str = None  # Saved query for batch selection
    parameters: Any = None  # Task parameters (Bag/dict)
    queue_name: str = None  # Target queue (default: "general")
```

#### Schedule Dictionary Keys
- `run_asap` (bool): Execute immediately on next schedule check
- `frequency` (int): Execute every N minutes
- `month` (str): Comma-separated months (1-12)
- `day` (str): Comma-separated days (1-31)
- `hour` (str): Comma-separated hours (0-23)
- `minute` (str): Comma-separated minutes (0-59)

#### Methods

**`is_due(timestamp=None, last_scheduled_ts=None)`**
Determines if the task should execute at the given timestamp.

Returns:
- `'*'` - For `run_asap` or due frequency-based tasks
- `'YYYY-M-D-H-M'` - Key string for calendar-based schedules
- `False` - Task is not due

### 4. GnrTaskSchedulerClient

**Location:** `gnrtask.py:58-137`

A synchronous HTTP client for interacting with the scheduler from external code (UI, CLI, scripts).

#### Methods

```python
client = GnrTaskSchedulerClient(url="http://localhost:14951")

# Reload task configuration from database
client.reload(domain=None)  # Reload all or specific domain

# Get scheduler status
status = client.status()  # Returns dict with queues, workers, etc.

# Manually execute a task (bypasses schedule)
client.execute(
    table="myapp.mytable",
    action="export_data",
    parameters={"format": "csv"},
    user="admin",
    domain="default",
    worker_code="general",  # Optional queue name
    attime=None             # Optional future execution time
)

# Stop a running task execution
client.stop_run(run_id="execution-uuid")

# Empty a queue
client.empty_queue(queue_name="general")

# Generate fake tasks for testing
client.gen_fake(quantity=10)
```

### 5. execute_task() Function

**Location:** `gnrtask.py:668-703`

A standalone function executed in worker subprocess to run the actual task.

#### Process
1. Initialize `GnrApp` and `GnrWsgiSite` for the sitename
2. Retrieve BTC (Batch) class from task table
3. Instantiate task object with page context
4. Execute task with parameters: `task_obj(parameters=Bag, task_execution_record=record)`
5. Send acknowledgment to scheduler via POST `/ack`

#### Notes
- Runs in separate process (via ProcessPoolExecutor)
- Creates its own database connections
- Uses `db.tempEnv(connectionName="execution")` for isolation
- Logs execution start/end and errors

## REST API Endpoints

The scheduler exposes the following HTTP endpoints:

### Control Endpoints

| Method | Endpoint | Parameters | Description |
|--------|----------|------------|-------------|
| GET | `/execute` | table, action, parameters, user, domain, worker_code, attime | Manually schedule a task execution |
| GET | `/stop_run` | run_id | Request to stop a running task |
| GET | `/reload` | domain (optional) | Reload task configuration from database |
| GET | `/empty_queue` | queue_name | Clear all items from a queue |
| GET | `/gen_fake` | quantity | Generate fake tasks for testing |

### Worker Communication Endpoints

| Method | Endpoint | Parameters | Description |
|--------|----------|------------|-------------|
| GET | `/next-task` | worker_id, queue_name | Long-poll for next task (blocks until task available) |
| POST | `/ack` | {run_id} (JSON) | Acknowledge task completion |
| GET | `/alive` | worker_id, queue_name | Worker heartbeat signal |
| GET | `/leave` | worker_id | Worker graceful disconnect |

### Monitoring Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web dashboard (HTML) with auto-refresh |
| GET | `/status` | JSON status report |
| GET | `/metrics` | Plain-text metrics (for monitoring tools) |

### Status Response Format

```json
{
  "total_tasks": 15,
  "total_queue_size": 3,
  "queues_sizes": {
    "general": 2,
    "custom": 1
  },
  "workers": {
    "gnrworker-hostname-12345": {
      "lastseen": "2025-11-11T10:30:45.123456+00:00",
      "worked_tasks": 42,
      "queue_name": "general"
    }
  },
  "workers_total": 1,
  "pending": {
    "run-uuid-123": [
      {"task_id": "...", "run_id": "...", "queue_name": "general"},
      "2025-11-11T10:30:40.000000+00:00",
      0,
      "gnrworker-hostname-12345"
    ]
  },
  "failed": [],
  "scheduler_current_time": "2025-11-11T10:30:45.678901+00:00",
  "startup_time": "2025-11-11T08:00:00.000000+00:00",
  "server_uptime": "2:30:45.678901"
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GNR_SCHEDULER_HOST` | `127.0.0.1` | Scheduler bind address |
| `GNR_SCHEDULER_PORT` | `14951` | Scheduler HTTP port |
| `GNR_SCHEDULER_URL` | `http://127.0.0.1:14951` | Full scheduler URL |
| `GNR_WORKER_ID` | `gnrworker-{fqdn}-{pid}` | Worker identifier |
| `GNR_WORKER_QUEUE_NAME` | `general` | Default queue to consume |

### Constants

**Location:** `gnrtask.py:52-55`

```python
SCHEDULER_RUN_INTERVAL = 1      # Schedule check interval (seconds)
RETRY_LIMIT = 3                 # Maximum task retry attempts
NOTIFY_ALIVE_INTERVAL = 2       # Worker heartbeat interval (seconds)
ACK_TIMEOUT = 6                 # Worker timeout threshold (3x heartbeat)
```

## Database Schema

### sys.task Table

**Purpose:** Defines scheduled tasks

| Column | Type | Description |
|--------|------|-------------|
| id | UUID/String | Primary key |
| task_name | String | Human-readable name |
| table_name | String | Target table for BTC operation |
| command | String | BTC action to execute |
| saved_query_code | String | Saved query for record selection |
| parameters | JSON/Bag | Task parameters |
| stopped | Boolean | If true, task is disabled |
| last_scheduled_ts | Timestamp | Last time task was queued |
| last_execution_ts | Timestamp | Last time task completed |
| run_asap | Boolean | Execute immediately |
| frequency | Integer | Execute every N minutes |
| month | String | Calendar: months (1-12) |
| day | String | Calendar: days (1-31) |
| hour | String | Calendar: hours (0-23) |
| minute | String | Calendar: minutes (0-59) |

### sys.task_execution Table

**Purpose:** Audit log of task executions

| Column | Type | Description |
|--------|------|-------------|
| id | UUID/String | Primary key (run_id) |
| task_id | UUID/String | Foreign key to sys.task |
| start_ts | Timestamp | Execution start time |

**⚠️ Note:** Currently, this table is only populated with `task_id` and `start_ts`. The following fields are **NOT** recorded:
- End timestamp (completion time)
- Execution status (success/failure)
- Error messages or stack traces
- Task output or results
- Worker ID that executed the task

This limits audit trail and performance monitoring capabilities.

## CLI Tools

### gnrtaskcontrol

**Location:** `gnr/web/cli/gnrtaskcontrol.py`

Command-line interface for scheduler management.

#### Usage

```bash
# Reload task configuration
gnrtaskcontrol --url http://scheduler:14951 reload
gnrtaskcontrol reload -d mydomain  # Reload specific domain

# Get status
gnrtaskcontrol status

# Stop running task
gnrtaskcontrol stop_run <run-id>

# Empty queue
gnrtaskcontrol empty_queue -q general

# Manual task execution
gnrtaskcontrol execute mytable export --parameters '{"format":"csv"}' admin default general

# Generate test tasks
gnrtaskcontrol genfake -n 50
```

### gnrtaskscheduler

Start the scheduler service.

```bash
gnrtaskscheduler mysite --host 0.0.0.0 --port 14951
```

### gnrtaskworker

Start a worker process.

```bash
gnrtaskworker mysite --queue-name general --processes 4
```

## Workflow Examples

### Example 1: Scheduled Export Task

**Database Configuration:**
```python
# In sys.task table
{
    "task_name": "Daily Sales Export",
    "table_name": "sales.orders",
    "command": "export_csv",
    "parameters": {"destination": "/exports/sales.csv"},
    "hour": "2",      # 2 AM
    "minute": "0",
    "queue_name": "general"
}
```

**Execution Flow:**
1. Scheduler evaluates at 02:00:00 - task is due
2. Creates execution record in `sys.task_execution`
3. Puts task in "general" queue
4. Worker polls and receives task
5. Worker executes `export_csv` BTC command on `sales.orders`
6. Worker acknowledges completion
7. Scheduler updates `sys.task.last_execution_ts`

### Example 2: Manual Task Execution from Code

```python
from gnr.web.gnrtask import GnrTaskSchedulerClient

client = GnrTaskSchedulerClient()

# Schedule immediate execution
client.execute(
    table="users.accounts",
    action="send_notification",
    parameters={"message": "System maintenance tonight"},
    user="admin",
    domain="production",
    worker_code="notifications"  # Routes to "notifications" queue
)
```

### Example 3: Frequency-Based Monitoring Task

**Database Configuration:**
```python
# In sys.task table
{
    "task_name": "Check System Health",
    "table_name": "sys.monitoring",
    "command": "health_check",
    "frequency": 5,  # Every 5 minutes
    "queue_name": "monitoring"
}
```

## Task Execution Lifecycle

```
┌─────────────────┐
│  Task Defined   │  sys.task record created/updated
│   in Database   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Scheduler Loop  │  Checks is_due() every 1 second
│  Evaluates Due  │
└────────┬────────┘
         │ (Due)
         ↓
┌─────────────────┐
│ Insert Exec Log │  sys.task_execution record (task_id, start_ts)
│  Get run_id     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Enqueue Task    │  Put in named queue
│ (pending_ack)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Worker Polls    │  GET /next-task
│  Receives Task  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│Execute in Process│ ProcessPoolExecutor.run_in_executor()
│   (BTC Task)    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  POST /ack      │  Acknowledge completion (run_id only)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│Update sys.task  │  Set last_execution_ts
│ (complete_task) │
└─────────────────┘

[Parallel: Retry Monitor]
         │
         ↓
┌─────────────────┐
│  Check Timeout  │  If worker_id stale or timeout > ACK_TIMEOUT
│  (every 2s)     │
└────────┬────────┘
         │ (Timeout)
         ↓
┌─────────────────┐
│  Retry Task     │  retries < RETRY_LIMIT: re-enqueue
│  or Mark Failed │  retries >= RETRY_LIMIT: add to failed_tasks
└─────────────────┘
```

## Retry and Failure Handling

### Retry Mechanism

**Trigger Conditions:**
- Worker becomes stale (no heartbeat for > 6 seconds)
- Worker ID not in active workers list

**Retry Process:**
1. `retry_monitor()` checks `pending_ack` every 2 seconds
2. If worker timeout detected and retries < 3:
   - Re-enqueue task
   - Increment retry counter
3. If retries >= 3:
   - Remove from `pending_ack`
   - Add to `failed_tasks` list
   - Log error

**Limitations:**
- No distinction between execution errors and worker failures
- Failed tasks remain in memory only (lost on scheduler restart)
- No automatic recovery or notification for failed tasks
- Execution errors within the task itself are not captured by the scheduler

## Known Limitations

### 1. Incomplete Execution Tracking
**Issue:** The `sys.task_execution` table only records start time, not completion status or results.

**Impact:**
- No audit trail for task success/failure
- Cannot measure execution duration
- Error messages only in logs, not database
- Cannot identify which worker executed a task

**Workaround:** Task implementations must handle their own result logging.

### 2. Failed Task Persistence
**Issue:** Failed tasks (after 3 retries) are stored only in `scheduler.failed_tasks` list in memory.

**Impact:**
- Failed task list lost on scheduler restart
- No historical record of failures
- Manual investigation required to identify issues

### 3. Stop Run Not Implemented
**Issue:** The `/stop_run` endpoint returns "ok" but does not actually stop tasks.

**Location:** `gnrtask.py:603-606`

**Impact:** Cannot cancel in-flight or queued tasks.

### 4. Single Domain Support (Partial)
**Issue:** Multi-domain/multi-tenant support is partially implemented but not fully functional.

**Evidence:** Comments at lines 256-262 mention multi-domain checks not yet implemented.

### 5. No Task Result Storage
**Issue:** Task output/results are not captured or stored.

**Impact:** Cannot retrieve task results for display in UI or further processing.

### 6. Queue Dump Race Condition
**Issue:** `dump_queue_to_disk()` removes and re-adds items, potentially losing tasks if scheduler crashes during dump.

**Location:** `gnrtask.py:302-315`

## Testing

**Test Suite:** `tests/web/gnrtask_test.py`

**Coverage:**
- Task `is_due()` logic (run_asap, frequency, calendar)
- Queue persistence (dump/restore)
- Worker tracking and heartbeat
- Retry mechanism with limits
- Scheduler startup/shutdown
- API endpoints (next_task, acknowledge, status)
- Client methods

**Test Approach:** Uses pytest with monkeypatching to stub out database, HTTP, and asyncio components.

## Integration with Genropy

### BTC (Batch) Framework
Tasks execute via the Genropy Batch (BTC) framework:
1. Task table's `getBtcClass()` resolves the command to a Python class
2. BTC class is instantiated with page context and resource table
3. BTC instance is called with parameters and task execution record

### Database Integration
- Uses `GnrApp` for database access
- Requires `gnrcore:sys` and `gnrcore:adm` packages
- Uses `db.tempEnv(connectionName="execution")` for task execution isolation

### Page Context
- Creates `dummyPage` from `GnrWsgiSite` for task execution
- Provides page context needed by BTC classes
- Not a real HTTP request context

## Deployment Considerations

### Production Setup

1. **Run scheduler as a service:**
   ```bash
   # systemd unit example
   [Unit]
   Description=Genropy Task Scheduler
   After=network.target postgresql.service

   [Service]
   Type=simple
   User=genropy
   Environment="GNR_SCHEDULER_HOST=0.0.0.0"
   Environment="GNR_SCHEDULER_PORT=14951"
   ExecStart=/path/to/gnrtaskscheduler mysite
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. **Run workers as separate processes:**
   ```bash
   # Multiple workers for different queues
   gnrtaskworker mysite --queue-name general --processes 4
   gnrtaskworker mysite --queue-name reports --processes 2
   gnrtaskworker mysite --queue-name notifications --processes 1
   ```

3. **Monitor scheduler dashboard:**
   - Access `http://scheduler-host:14951/` in browser
   - Auto-refreshes every 2 seconds
   - Shows queue sizes, active workers, pending/failed tasks

4. **Integrate with monitoring:**
   - Use `/metrics` endpoint for Prometheus/Grafana
   - Use `/status` endpoint for custom monitoring scripts
   - Parse logs for detailed execution information

### Security Considerations

- **Network Exposure:** Default bind to 127.0.0.1 - only expose externally if needed
- **No Authentication:** Scheduler API has no authentication - use firewall/network isolation
- **No Authorization:** Any client can execute arbitrary tasks if they can reach the API
- **No Encryption:** HTTP only - consider reverse proxy with TLS if needed

### Scalability

- **Vertical Scaling:** Increase worker processes per worker instance
- **Horizontal Scaling:** Run multiple worker instances (automatically discovered by scheduler)
- **Queue Partitioning:** Use named queues to route different task types to specialized workers
- **Database Performance:** Task loading queries run on startup/reload - optimize sys.task table

### High Availability

- **Scheduler:** Single point of failure - consider active/passive failover with shared storage
- **Workers:** Automatically retry failed tasks - can lose workers without data loss
- **Queue Persistence:** Dumps to local disk - ensure disk reliability or use shared storage

## References

- **Source Code:** `gnr/web/gnrtask.py`
- **Test Suite:** `tests/web/gnrtask_test.py`
- **CLI Tools:** `gnr/web/cli/gnrtask*.py`
- **Related Tables:** `sys.task`, `sys.task_execution` (in gnrcore packages)
- **Related Framework:** Genropy BTC (Batch) framework

---

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Genropy Version:** Current development branch (feature/scheduler-worker)
