# gnr_async — Genro async server (asyncio/aiohttp)

Modern reimplementation of the Genro async server (`gnrasync.py`, Tornado-based)
using **native asyncio** and **aiohttp**.

## Modules

| Module | Description |
|--------|-------------|
| `gnrasync_io.py` | Main server: WebSocket, shared objects, remote debug, HTTP proxy |

## Architecture

The async server handles real-time communication only.
Web page serving (WSGI) runs as a separate process,
both in development and production.

```
Browser ──WebSocket──► gnr_async (aiohttp)
                          |
                          +-- WebSocketSession: RPC, routing, ping
                          +-- SharedObjectsManager: real-time shared objects
                          +-- DebugSession: remote debug via TCP
                          +-- WsProxyHandler: HTTP bridge from WSGI server

WSGI Server ──Unix socket──► gnr_async (wsproxy)
```

## Main components

### WebSocketSession

Handles a single WebSocket connection with the browser.
Receives JSON commands and dispatches them to `do_*` methods:

- `do_connected` — registers the page
- `do_call` — RPC: invokes server-side Python methods (threadpool)
- `do_ping` — keepalive
- `do_route` — forwards messages between pages
- `do_service` — remote services
- `do_pdb_command` — remote debugging

### SharedObject

Object shared between pages for real-time collaboration.
Changes are broadcast to all subscribed pages.

Features:

- Persistence to XML files or SQL database
- Access control via tags (read/write)
- Automatic backup with versioning
- Auto-expiration after last disconnection
- Lock for change serialization

Subclasses:

- `SharedStatus` — global server state (users, connections, pages)
- `SharedLogger` — shared logging
- `SqlSharedObject` — placeholder for SQL extensions

### DebugSession

Remote debug session via TCP socket. Bridges the Python debugger (PDB)
to the browser through bidirectional async queues.

### AioWebSocket

Compatibility wrapper on `aiohttp.WebSocketResponse` exposing
`write_message()` to interoperate with the existing `AsyncWebSocketHandler`.

## Differences from gnrasync.py (Tornado)

| Aspect | Tornado | asyncio/aiohttp |
|--------|---------|-----------------|
| Coroutines | `@gen.coroutine` / `yield` | `async def` / `await` |
| Lock | `tornado.locks.Lock` | `asyncio.Lock` |
| Queues | `tornado.queues.Queue` | `asyncio.Queue` |
| WebSocket server | `tornado.websocket` | `aiohttp.web.WebSocketResponse` |
| HTTP handler | `tornado.web.RequestHandler` | `aiohttp.web` functions |
| TCP server (debug) | `tornado.tcpserver.TCPServer` | `asyncio.start_unix_server` |
| Unix socket | `tornado.netutil.bind_unix_socket` | `aiohttp.web.UnixSite` |
| WSGI bridge | `tornado_wsgi.WSGIHandler` | removed (separate process) |

## Startup

### Development

The asyncio WebSocket server starts alongside the WSGI server with the `-ws` flag:

```bash
gnrwsgiserve mysite -ws
```

This launches two processes:

- **WSGI** (werkzeug) — serves web pages
- **WebSocket** (asyncio/aiohttp) — handles real-time communication

The `-ws` and `-t` (tornado) flags are mutually exclusive:

- `-ws` — two separate processes (WSGI + asyncio WebSocket)
- `-t` — single Tornado process with integrated WSGI (legacy)

### Production

In production the WebSocket server runs as a separate process managed
by Supervisor, with Nginx routing:

- `/websocket` — asyncio process (Unix socket)
- `/` — Gunicorn (Unix socket)

## JavaScript client

The browser-side WebSocket handler lives in `gnrjs/gnr_d11/js/gnrwebsocket.js`
and contains two parts:

### GnrWebSocketHandler

Genro application-level handler (`gnr.GnrWebSocketHandler`).
Manages the protocol: JSON commands out, XML/GnrBag responses in.

Key methods: `create()`, `send()`, `call()` (RPC with token-based response),
`onmessage()` (dispatches to `do_*` handlers).

### ReconnectingWebSocket (vendored)

Auto-reconnecting WebSocket wrapper included at the bottom of the same file.

**Current version**: [pladaria/reconnecting-websocket v4.4.0](https://github.com/pladaria/reconnecting-websocket) (MIT license).

Replaced the original Joe Walnes (2012) library. Key improvements:

- Exponential backoff with random jitter (avoids thundering herd)
- Built-in message queue with configurable `maxEnqueuedMessages`
- No deprecated DOM APIs (`initCustomEvent`, `document.createElement` as EventTarget)
- `reconnect()` method for explicit reconnection
- Maintained codebase with TypeScript source

Option name mapping from the old library:

| Old (Walnes) | New (pladaria) |
| ------------ | -------------- |
| `reconnectInterval` | `minReconnectionDelay` |
| `maxReconnectInterval` | `maxReconnectionDelay` |
| `reconnectDecay` | `reconnectionDelayGrowFactor` |
| `timeoutInterval` | `connectionTimeout` |
| `maxReconnectAttempts` | `maxRetries` |

## GnrSimplePage (static page)

The async server maintains a persistent page instance (`GnrSimplePage`) for each
connected browser page. This is the counterpart of the ephemeral `GnrWebPage`
that the WSGI server recreates on every HTTP request.

`GnrSimplePage` is instantiated by `resource_loader.instantiate_page()` and stored
in `server.pages[page_id]`. WebSocket RPC calls (`do_call`) execute methods on this
persistent instance via ThreadPoolExecutor.

### Known limitations

The WebSocket subsystem was abandoned for several years while the WSGI page
(`GnrWebPage`) continued to evolve. As a result, `GnrSimplePage` has diverged
significantly. The following issues have been identified and must be addressed
before production deployment:

| # | Issue | Severity | Status |
| --- | ----- | -------- | ------ |
| 1 | `dbstore` always `None` — multi-tenant broken | Critical | Deferred (see below) |
| 2 | `locale` hardcoded to `'en'` | Critical | Deferred (see below) |
| 3 | Thread safety on shared instance | Critical | Likely OK (see below) |
| 4 | `request`/`response`/`environ` absent | Grave | Not an issue |
| 5 | `extraFeatures` absent | Grave | To verify |
| 6 | `local_datachanges` absent | Grave | To verify |
| 7 | Lifecycle hooks not called | Grave | Not an issue |
| 8 | Connection "frozen" at registration time | Significant | Not an issue |
| 9 | Mixin accumulation without cleanup | Significant | Not an issue |
| 10 | `getWsMethod` doesn't verify `@public_method` | Significant | Fix before production |
| 11 | `do_call` calls `getWsMethod` twice | Significant | Confirmed bug, not blocking |
| 12 | State accumulation / memory leak | Significant | To verify |

### Decision: dbstore (multi-tenant)

The multi-tenant feature (`dbstore`) was developed after the original WebSocket
implementation. In the current testing phase, the async server operates in
**single-store mode only** (`dbstore=None`).

**IMPORTANT**: Multi-database support must be implemented before deploying the
asyncio server in production environments that use multi-tenant configurations.
This requires propagating the correct `dbstore` value from the WSGI page
registration to the `GnrSimplePage` instance, and ensuring it is applied
on every `do_call` execution.

### Decision: locale

`GnrSimplePage` hardcodes `_locale='en'`, ignoring the user's `_language`
attribute captured in `ATTRIBUTES_SIMPLEWEBPAGE`. All date/number formatting
and translations via WebSocket RPC use English regardless of the connected user.

Not blocking for the current testing phase (single-locale environments).
Must be fixed before production by propagating `_language` from the WSGI
page registration to the `GnrSimplePage` instance.

### Decision: thread safety

The `GnrSimplePage` instance is shared across concurrent `do_call` invocations
running in the ThreadPoolExecutor. Analysis shows the existing design already
handles thread isolation for the critical paths:

- **DB access**: `GnrSqlDb` uses `_thread.get_ident()` for thread-local env;
  `do_call` resets `page._db = None` before each invocation, forcing a fresh
  connection per thread.
- **Private data**: `page.privateData` uses `_thread.get_ident()` as key,
  providing per-thread storage.
- **Shared data**: `page.sharedData()` returns `SharedLockedObject` instances
  with built-in locking.
- **Call parameters**: `_call_args` / `_call_kwargs` are set only at `__init__`
  time, not modified per-call. Each `do_call` receives its parameters as
  function arguments, not via shared page state.

This should work correctly in practice. Must be verified under load before
production deployment to confirm no edge cases exist.

## Dependencies

- `aiohttp` (already present in the project)
- No additional dependencies
