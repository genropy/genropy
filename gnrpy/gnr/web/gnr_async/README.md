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

## Dependencies

- `aiohttp` (already present in the project)
- No additional dependencies
