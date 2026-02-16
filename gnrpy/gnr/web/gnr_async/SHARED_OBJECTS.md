# Shared Objects — Architecture and Data Flow

Shared Objects are Genro's real-time collaboration mechanism. They allow
multiple browser pages to share a `Bag` data structure that stays
synchronized across all subscribers. Changes made by one page are
broadcast to all others in real time via WebSocket.

## Overview

```
Page A (browser)                Async Server               Page B (browser)
      |                              |                           |
      |-- som.subscribe ------------>|                           |
      |<-- init data ----------------|                           |
      |                              |                           |
      |-- som.datachange ----------->|                           |
      |   {path, value, evt}         |-- sharedObjectChange ---->|
      |                              |   (broadcast to others)   |
      |                              |                           |
      |                              |<-- som.datachange --------|
      |<-- sharedObjectChange -------|   (broadcast to others)   |
```

## Usage (Python page builder)

A shared object is declared in the page source tree:

```python
pane.sharedObject('.my_data',
                  shared_id='my_shared_id',
                  autoSave=True,
                  autoLoad=True,
                  expire=60,
                  read_tags='user',
                  write_tags='admin')
```

This generates a `SharedObject` node in the source tree. When the browser
renders this node, the JavaScript client automatically subscribes to the
shared object via WebSocket.

**Parameters**:

| Parameter | Description |
|-----------|-------------|
| `shared_path` | Local data path where shared data is stored |
| `shared_id` | Unique identifier for the shared object |
| `autoSave` | Save to persistent storage on destroy/shutdown |
| `autoLoad` | Load from persistent storage on creation |
| `expire` | Seconds to keep alive after last subscriber disconnects (0 = immediate, -1 = forever) |
| `read_tags` | User tags required for read access |
| `write_tags` | User tags required for write access |
| `startData` | Initial data (Bag or dict) |
| `dbSaveKw` | SQL persistence configuration (table, data_column, backup_column, backup) |
| `saveInterval` | Auto-save interval (not currently implemented) |

## Server-side architecture

### SharedObject

**File**: `gnrpy/gnr/web/gnrasync.py` (line 409)

Core class managing a shared `Bag` instance with subscription, persistence,
access control, and change broadcasting.

**Data structure**:

```python
self._data = Bag(dict(root=Bag(startData)))
#                     ^^^^
#                     All shared data lives under 'root'
#                     self.data property returns self._data['root']
```

The `root` wrapper exists because `Bag.subscribe()` needs a parent node
to monitor. The `data` property transparently accesses the inner Bag.

**Change detection**: Uses `Bag.subscribe('datachanges', any=self._on_data_trigger)`
to intercept all modifications to the data tree. The callback
`_on_data_trigger` fires on every insert, update, or delete.

**Key methods**:

- `subscribe(page_id)` — adds page to `subscribed_pages`, checks
  permissions, returns initial data with privilege level
- `unsubscribe(page_id)` — removes page, starts expiration timer if
  no subscribers remain
- `datachange(page_id, path, value, attr, evt, fired)` — applies a
  change from a client. For `fired` events (one-shot triggers),
  broadcasts without modifying data. For regular changes, modifies
  `self._data` which triggers `_on_data_trigger`
- `broadcast(command, data, from_page_id)` — sends XML envelope to all
  subscribed pages except the sender
- `save()` / `load()` — persist to XML file or SQL database (decorated
  with `@lockedThreadpool`)
- `checkPermission(page)` — returns `'readwrite'`, `'readonly'`, or `None`
- `onPathFocus(page_id, curr_path, focused)` — tracks which field each
  user is editing, broadcasts lock state

**Persistence**:

Two storage backends:

1. **XML file** (default): saves to `site:async/sharedobjects/{shared_id}.xml`
2. **SQL database**: when `dbSaveKw` is provided, uses `tblobj.saveSharedObject()`
   / `tblobj.loadSharedObject()` custom handlers, or falls back to
   `sql_save()` / `sql_load()` which use `tblobj.recordToUpdate(shared_id)`

SQL persistence supports **versioned backups**: each save stores the
previous version in a backup column, with configurable max versions.

**Locking**: All state-modifying operations use `@lockedCoroutine` or
`@lockedThreadpool` decorators that acquire `self.lock` (a Tornado
`Lock` / asyncio `Lock`).

**Expiration**: When the last subscriber disconnects, a `DelayedCall`
is scheduled to destroy the shared object after `expire` seconds.
If a new subscriber joins before expiration, the timer is cancelled.

### SharedObjectsManager

**File**: `gnrpy/gnr/web/gnrasync.py` (line 717)

Manages the lifecycle of all shared objects on the server.

**Attributes**:

- `sharedObjects` — dict of `{shared_id: SharedObject}`
- `change_queue` — Queue (currently unused, was planned for batching)

**Command dispatch** — receives WebSocket commands prefixed with `som.`:

| Command | Method | Description |
|---------|--------|-------------|
| `som.subscribe` | `do_subscribe()` | Create/get shared object, subscribe page, return initial data |
| `som.unsubscribe` | `do_unsubscribe()` | Remove page from subscribers |
| `som.datachange` | `do_datachange()` | Apply a client change |
| `som.saveSharedObject` | `do_saveSharedObject()` | Persist to storage |
| `som.loadSharedObject` | `do_loadSharedObject()` | Reload from storage |
| `som.dispatch` | `do_dispatch()` | Call arbitrary method on shared object |
| `som.onPathFocus` | `do_onPathFocus()` | Track field focus for locking |

**`do_subscribe()` flow**:

1. `getSharedObject()` — creates if not exists, registers in SharedStatus
2. `sharedObject.subscribe(page_id)` — checks permissions, adds to subscribers
3. If the object had an expiration timer, cancels it
4. Returns `Bag(command='som.sharedObjectChange', data=...)` with `evt='init'`

### SharedStatus

**File**: `gnrpy/gnr/web/gnrasync.py` (line 635)

Special `SharedObject` (id `__global_status__`) that tracks all
connected users, connections, and pages. Also tracks which shared
objects exist and who subscribes to them.

**Data structure**:

```
root/
  users/
    {username}/
      @start_ts, @user
      connections/
        {connection_id}/
          @start_ts, @user_ip, @user_agent
          pages/
            {page_id}/
              @pagename, @relative_url, @start_ts
              @lastEventAge    (updated on ping)
              @evt_*           (updated on user events)
  sharedObjects/
    {shared_id}/
      @shared_id, @expire, @read_tags, @write_tags
      subscriptions/
        {page_id}/
          @page_id, @user
```

Since `SharedStatus` is itself a `SharedObject`, any page can subscribe
to `__global_status__` to see who is connected in real time (used by
the admin/monitoring panel).

**Key methods**:

- `registerPage(page)` / `unregisterPage(page)` — maintain user/connection/page tree
- `onPing(page_id, lastEventAge)` — update activity timestamps
- `onUserEvent(page_id, event)` — track mouse/keyboard activity, typing detection
- `registerSharedObject()` / `unregisterSharedObject()` — track shared objects
- `sharedObjectSubscriptionAddPage()` / `sharedObjectSubscriptionRemovePage()`

### SharedLogger

**File**: `gnrpy/gnr/web/gnrasync.py` (line 620)

Subclass with logging hooks. Currently only logs lifecycle events
(`onInit`, `onSubscribePage`, etc.). Placeholder for future shared
logging functionality.

### SqlSharedObject

**File**: `gnrpy/gnr/web/gnrasync.py` (line 615)

Empty subclass — placeholder for SQL-specific extensions. The SQL
persistence logic is already in the base `SharedObject` class.

## Client-side architecture

### GnrSharedObjectHandler (som)

**File**: `gnrjs/gnr_d11/js/gnrsharedobjects.js`

Singleton accessible as `genro.som`. Manages shared object subscriptions
and handles incoming changes.

**Registration flow**:

1. Source tree rendering encounters a `SharedObject` node
2. `genro_src.js` extracts `shared_id` and `shared_*` attributes
3. Calls `genro.som.registerSharedObject(absPath, shared_id, kw)` (with 1ms delay)
4. `registerSharedObject()`:
   - Stores metadata in `genro._sharedObjects[shared_id]`
   - Sends `som.subscribe` via `genro.wsk.call()` (with result callback)
   - On response: calls `do_sharedObjectChange()` to set initial data
   - Sets `genro._sharedObjects_paths[path] = shared_id`
   - Publishes `shared_{shared_id}` topic with `{ready, privilege}`
   - Installs `focus`/`blur` event listeners for path locking

**Incoming changes** — `do_sharedObjectChange(data)`:

Receives a change notification from the server. Looks up the local
path via `genro._sharedObjects[shared_id].path`, then applies:

- `evt='del'` → `genro._data.popNode(fullpath, 'serverChange')`
- `evt='init'` or update → `genro._data.setItem(fullpath, value, attr, {doTrigger:'serverChange', lazySet:true})`
- `fired=true` → `genro._data.fireItem(fullpath, value, attr, 'serverChange')`

The reason `'serverChange'` prevents re-broadcasting (see outgoing changes).

**Outgoing changes** — `genro.dataTrigger()` in `genro.js`:

The global data trigger fires on every change to `genro._data`. For each
change, it checks if the path falls under any registered shared object:

```javascript
if (kw.reason != 'serverChange') {
    for (var shared_path in genro._sharedObjects_paths) {
        if (dpath.indexOf(shared_path) == 0) {
            // Check write privilege
            genro.wsk.send('som.datachange', {
                shared_id, path: inner,
                value, attr, evt, fired
            });
        }
    }
}
```

The `reason != 'serverChange'` guard prevents infinite loops:
server→client changes are tagged with reason `'serverChange'`, so they
don't get sent back to the server.

**Path locking** — `do_onPathLock(data)`:

When another user focuses on a field within a shared object, the server
broadcasts `som.onPathLock`. The client walks the source tree to find
the widget bound to that path and disables it, preventing concurrent
editing of the same field.

**Unregistration** — `unregisterSharedObject(shared_id)`:

Sends `som.unsubscribe`, then removes from `_sharedObjects` and
`_sharedObjects_paths`. Calls `on_unregistered` callback if provided.

### WebSocket command dispatch

**File**: `gnrjs/gnr_d11/js/gnrwebsocket.js`

The WebSocket `receivedCommand()` dispatcher handles `som.*` commands:

```javascript
if (command.indexOf('.') > 0) {
    comlst = command.split('.');
    handler = genro[comlst[0]]['do_' + comlst.splice(1).join('.')];
}
```

So `som.sharedObjectChange` → `genro.som.do_sharedObjectChange()` and
`som.onPathLock` → `genro.som.do_onPathLock()`.

Note: there is also a duplicate `do_sharedObjectChange` in
`gnrwebsocket.js` itself (lines 160-178), which handles the same
command but without `fired` support. The `gnrsharedobjects.js` version
is more complete and takes precedence when `genro.som` is initialized.

## WSGI integration (wsproxy)

The WSGI server (GnrWebPage) can send commands to connected browsers
through the async server, using the **wsproxy** HTTP bridge:

**File**: `gnrpy/gnr/web/gnrwsgisite_proxy/gnrwebsockethandler.py`

```
WSGI Thread                     Async Server              Browser
     |                               |                        |
     |-- HTTP POST /wsproxy --------->|                        |
     |   (Unix socket)               |                        |
     |   {page_id, envelope}         |-- WebSocket ---------->|
     |                               |   (envelope XML)       |
```

`WsgiWebSocketHandler` connects to the async server via Unix socket
(`sockets/async.tornado`) and sends HTTP POST requests to `/wsproxy`.
The async server's `GnrWsProxyHandler` receives these and forwards
the envelope to the target page's WebSocket channel.

This is used for server-initiated pushes: `page.wsk.publishToClient()`,
`page.wsk.setInClientData()`, `page.wsk.fireInClientData()`.

**Important**: The WSGI proxy does NOT interact with `SharedObjectsManager`
directly. Shared object changes always flow through the browser ↔ WebSocket
path. The WSGI proxy is for one-way server→client pushes.

### SharedLockedObject (page-level, separate concept)

**File**: `gnrpy/gnr/web/gnrsimplepage.py` (line 34)

Not to be confused with the real-time `SharedObject`. This is a
thread-safe wrapper for data shared between concurrent `do_call`
invocations on the same `GnrSimplePage` instance:

```python
class SharedLockedObject:
    def __init__(self, factory=None):
        self.lock = RLock()
        self.data = factory()

    def __enter__(self):
        self.lock.acquire()
        return self.data

    def __exit__(self, ...):
        self.lock.release()
```

Used via `page.sharedData(name)` as a context manager. This is a
purely server-side thread synchronization primitive.

## Known issues

### 1. Wsproxy socket path mismatch

Same problem as the debugger socket (now fixed). The WSGI proxy
`WsgiWebSocketHandler` hardcodes `sockets/async.tornado` but the
asyncio server listens on `sockets/async.aiohttp`:

| Component | Socket name |
|-----------|-------------|
| `WsgiWebSocketHandler` | `sockets/async.tornado` |
| `gnrasync.py` (Tornado) | `sockets/async.tornado` |
| `gnrasync_io.py` (asyncio) | `sockets/async.aiohttp` |
| `gnrdeploy.py` (Supervisor) | `sockets/async.tornado` |

When using the asyncio server, the WSGI proxy cannot reach it.
This must be aligned (same approach as the debugger fix: use a
canonical name).

### 2. Duplicate do_sharedObjectChange

The handler exists in both `gnrwebsocket.js` (simplified version,
no `fired` support) and `gnrsharedobjects.js` (complete version).
The `gnrwebsocket.js` version was likely added as a fallback for
pages without the shared objects module loaded. The duplication
is harmless when both are loaded (the `som.*` dispatch takes
precedence) but should be consolidated.

### 3. change_queue unused

`SharedObjectsManager.__init__` creates `self.change_queue = Queue(maxsize=100)`
but it's never consumed. There is commented-out code for a
`consume_change_queue` coroutine (lines 795-805). This was likely
planned for batching changes but never completed.

### 4. broadcast error on missing channel

`SharedObject.broadcast()` calls `channels.get(p).write_message(envelope)`
without checking if `channels.get(p)` returns `None`. If a subscribed
page disconnects without unsubscribing (e.g., browser crash), this
will raise `AttributeError`.

### 5. saveInterval not implemented

The `saveInterval` parameter is stored but never used. Periodic
auto-save was likely planned but not completed.
