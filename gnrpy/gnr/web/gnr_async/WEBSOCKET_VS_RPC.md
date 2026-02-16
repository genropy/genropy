# WebSocket vs RPC — Communication Architecture

How Genro pages communicate with the server: the two parallel channels
(HTTP RPC and WebSocket), their routing, data passing mechanisms, and
the ping/keepalive system.

## Overview

Genro pages use **two independent communication channels**:

1. **HTTP RPC** — synchronous or async XMLHttpRequest to the WSGI server
2. **WebSocket** — persistent connection to the async server

The selection happens **client-side**, not server-side: the `httpMethod`
property on each resolver/call determines which channel to use.

```
Browser                     WSGI Server              Async Server
   |                            |                         |
   |-- HTTP POST (method=X) --->|                         |
   |   (page_id, kwargs)        |                         |
   |<-- XML envelope ---------- |                         |
   |    (result + dataChanges)  |                         |
   |                            |                         |
   |-- WebSocket JSON ---------------------------------->|
   |   {command:'call', method:'X', result_token:'T'}    |
   |<-- XML envelope ------------------------------------|
   |    (token + result)                                  |
   |                            |                         |
   |                            |-- HTTP POST /wsproxy -->|
   |                            |   (page_id, envelope)  |
   |<-- WebSocket push ----------------------------------|
   |    (setInClientData, publish, datachanges)           |
```

## Client-side routing: httpMethod

**File**: `gnrjs/gnr_d11/js/genro_rpc.js`

### GnrRemoteResolver (line 45, 65-76)

Every resolver has an `httpMethod` property (default `'POST'`):

```javascript
this.httpMethod = objectPop(kwargs, 'httpMethod') || 'POST';
```

At resolution time (`load()`), the method determines the channel:

```javascript
if (this.httpMethod == 'WSK') {
    result = genro.wsk.call(kw);        // WebSocket
} else {
    result = genro.rpc._serverCall(...); // HTTP (GET/POST/PUT/DELETE)
}
```

### remoteCall (line 399, 444-460)

Same pattern for explicit RPC calls:

```javascript
if (httpMethod == 'WSK') {
    result = genro.wsk.call(callKwargs);
} else {
    var deferred = this._serverCall(callKwargs, xhrKwargs, httpMethod);
}
```

### Who sets httpMethod='WSK'?

The `httpMethod` is specified declaratively in the page source tree,
typically on `dataRemote`, `dataRpc`, or resolver declarations:

```python
# Python page builder
pane.dataRpc('path', 'method_name', httpMethod='WSK', ...)
```

If not specified, the default is `'POST'` (HTTP RPC).

## Server-side: two independent handlers

### HTTP RPC path

**File**: `gnrpy/gnr/web/gnrwebpage.py` (line 577)

```
HTTP POST → WSGI dispatcher → page.__call__()
    → get_call_handler() → _rpcDispatcher()
        → rpc(method=..., **kwargs)
            → handler(**kwargs)
        → rpc.result_bag(result)    ← builds envelope with piggyback
```

The `_rpcDispatcher` (line 577) extracts `method` from kwargs, calls
the RPC handler, and builds the result envelope. The envelope includes
**piggybacked datachanges** (see below).

### WebSocket RPC path

**File**: `gnrpy/gnr/web/gnrasync.py` (line 360)

```
WebSocket JSON → on_message() → parseMessage()
    → getHandler('call') → do_call()
        → page.getWsMethod(method)
            → handler(**kwargs)
        → Bag(data=result)          ← simple envelope, NO piggyback
```

The `do_call` handler (line 360) runs in a threadpool (`@threadpool`),
looks up the method on the `GnrSimplePage` instance, executes it, and
returns a `Bag` envelope with `data` and optionally `error`.

**Key difference**: WebSocket RPC responses do **not** include piggybacked
datachanges. Server→client data pushes via WebSocket use a separate
mechanism (see Push commands below).

## Piggyback: datachanges on HTTP RPC responses

The HTTP RPC channel piggybacks server-side data changes on every
response, including ping responses. This is Genro's primary mechanism
for server→client state synchronization in the HTTP-only mode.

### Server: collecting datachanges

**File**: `gnrpy/gnr/web/gnrwebpage_proxy/rpc.py` (line 47)

```python
def result_bag(self, result):
    envelope = Bag()
    envelope.setItem('result', result, ...)

    # PIGGYBACK: collect and attach datachanges
    if not getattr(page, '_closed', False):
        dataChanges = self.page.collectClientDatachanges()   # line 77
        if dataChanges:
            envelope.setItem('dataChanges', dataChanges)     # line 79

    return envelope.toXml(unresolved=True, ...)
```

### Server: where datachanges come from

**File**: `gnrpy/gnr/web/gnrwebpage.py` (line 985)

```python
def collectClientDatachanges(self):
    store_datachanges = self.site.register.subscription_storechanges(
        self.user, self.page_id) or []
    local_datachanges = self.local_datachanges or []
    result = Bag()
    for j, change in enumerate(local_datachanges + store_datachanges):
        result.setItem('sc_%i' % j, change.value,
                       change_path=change.path,
                       change_reason=change.reason,
                       change_fired=change.fired,
                       change_attr=change.attributes,
                       change_ts=change.change_ts,
                       change_delete=change.delete)
    return result
```

Two sources:

1. **local_datachanges** — accumulated during the current RPC execution
   via `page.addLocalDatachange()` or `page.setInClientData()`
2. **store_datachanges** — from server-side store subscriptions
   (changes made by other pages/processes to stores this page subscribes to)

### Client: applying piggybacked datachanges

**File**: `gnrjs/gnr_d11/js/genro_rpc.js` (line 537)

```javascript
resultHandler: function(response, ioArgs) {
    var envelope = new gnr.GnrBag();
    envelope.fromXmlDoc(response, genro.clsdict);

    var datachanges = envelope.getItem('dataChanges');  // line 562
    if (datachanges) {
        genro.rpc.setDatachangesInData(datachanges);    // line 564
    }
    // ... return result
}
```

`setDatachangesInData` (line 467) iterates over change nodes and applies
each one to `genro._data`, handling deletes, fired events, and
`serverChange` reason mapping for server store subscriptions.

### Envelope XML structure

```xml
<GenroBag>
  <result _server_time="0.042">
    <!-- RPC result value -->
  </result>
  <dataChanges>
    <sc_0 change_path="current.user.name"
           change_reason="serverChange"
           change_fired=""
           change_ts="1234567890.123"
           change_delete="">New Value</sc_0>
    <sc_1 ... />
  </dataChanges>
  <!-- optional: js_requires, css_requires, error, etc. -->
</GenroBag>
```

## WebSocket push commands

When the server needs to push data to the client outside of an RPC
response, it uses the **wsproxy** bridge (HTTP→WebSocket) or direct
`AsyncWebSocketHandler` calls.

### Server→Client push via WSGI (wsproxy)

**File**: `gnrpy/gnr/web/gnrwsgisite_proxy/gnrwebsockethandler.py`

The WSGI page (`GnrWebPage`) calls methods on `page.wsk`:

```python
page.wsk.setInClientData(page_id, path='my.path', value='new_value')
page.wsk.publishToClient(page_id, topic='myTopic', data=data_bag)
page.wsk.fireInClientData(page_id, path='my.path', data=data_bag)
```

`WsgiWebSocketHandler` (line 82) sends these as HTTP POST to the async
server's `/wsproxy` endpoint via Unix socket. The async server then
forwards them as WebSocket messages to the target page.

### Server→Client push via async server (direct)

**File**: `gnrpy/gnr/web/gnrwsgisite_proxy/gnrwebsockethandler.py` (line 73)

`AsyncWebSocketHandler` calls `server.channels[page_id].write_message()`
directly — used when the push originates from within the async server
itself (e.g., shared object broadcasts).

### Client-side WebSocket command handlers

**File**: `gnrjs/gnr_d11/js/gnrwebsocket.js`

| Command | Handler (line) | Action |
|---------|---------------|--------|
| `setInClientData` | `do_setInClientData` (141) | Sets a value in `genro._data` |
| `datachanges` | `do_datachanges` (156) | Applies batch datachanges (same as piggyback) |
| `publish` | `do_publish` (180) | Publishes a topic via `genro.publish()` |
| `set` | `do_set` (130) | Sets data with optional fired |
| `alert` | `do_alert` (127) | Shows alert dialog |

### Command dispatch

**File**: `gnrjs/gnr_d11/js/gnrwebsocket.js` (line 81)

```javascript
onmessage: function(e) {
    var data = e.data;
    if (data == 'pong') return;              // keepalive response

    if (data.indexOf('<?xml') == 0) {
        var result = this.parseResponse(e.data);
        var token = result.getItem('token');
        if (token) {
            this.receivedToken(token, ...);  // RPC response (call)
        } else {
            this.receivedCommand(
                result.getItem('command'),   // push command
                result.getItem('data')
            );
        }
    } else {
        genro.publish('websocketMessage', data);  // raw text
    }
}
```

Two types of incoming WebSocket messages:

1. **Token-based** — response to a `wsk.call()`, matched by `result_token`
2. **Command-based** — server push, dispatched to `do_*` handlers

For `som.*` commands, the dispatcher (line 99) splits on `.` and routes
to `genro.som.do_*()`.

## WebSocket call protocol

**File**: `gnrjs/gnr_d11/js/gnrwebsocket.js` (line 198)

### Client sends (call)

```javascript
call: function(kw) {
    var deferred = new dojo.Deferred();
    var token = 'wstk_' + genro.getCounter('wstk');
    kw['result_token'] = token;
    kw['command'] = kw['command'] || 'call';
    kw = genro.rpc.serializeParameters(genro.src.dynamicParameters(kw));
    this.waitingCalls[token] = deferred;
    this.socket.send(dojo.toJson(kw));    // JSON message
    return deferred;
}
```

### Client sends (fire-and-forget)

```javascript
send: function(command, kw) {
    kw['command'] = command;
    kw = genro.rpc.serializeParameters(genro.src.dynamicParameters(kw));
    this.socket.send(dojo.toJson(kw));    // no token, no response
}
```

### Server receives and responds

**File**: `gnrpy/gnr/web/gnrasync.py` (line 277)

```python
@gen.coroutine
def on_message(self, message):
    command, result_token, kwargs = self.parseMessage(message)
    handler = self.getHandler(command, kwargs)
    # ... execute handler (possibly in threadpool) ...
    if result_token:
        result = Bag(dict(token=result_token, envelope=result)).toXml(...)
    if result is not None:
        self.write_message(result)
```

If `result_token` is present, the response includes it so the client
can match the deferred. If absent (fire-and-forget), the handler may
still `write_message()` directly (e.g., ping→pong).

## Ping mechanisms

Genro has **two independent ping systems** that serve different purposes.

### HTTP Polling ping (WSGI)

**Purpose**: Server→client state synchronization via piggybacked datachanges.

**File**: `gnrjs/gnr_d11/js/genro_rpc.js` (line 740)

```javascript
ping: function(kw) {
    if (genro.pollingRunning || !genro.polling_enabled) return;

    var xhrKwargs = {
        'url': '...' + genro.baseUrl + '_ping',  // special endpoint
        'timeout': 10000,
        'load': function(response, ioArgs) {
            genro.rpc.resultHandler(response, ioArgs);  // processes piggyback
        }
    };
    var pingKw = {
        page_id: genro.page_id,
        _lastUserEventTs: genro.getServerLastTs(),
        _lastRpc: genro.getServerLastRpc(),
        _pageProfilers: genro.getTimeProfilers(),
        sysrpc: true
    };
    this._serverCall(pingKw, xhrKwargs, 'POST');
}
```

**Server handler**: `gnrwebpage.py` line 2502 — `rpc_ping()` does nothing
(empty method), but the piggyback mechanism in `result_bag()` collects
and returns any pending datachanges.

**Scheduling**: Controlled by `auto_polling` (default 30s) and
`user_polling` (default 3s) settings from `gnrwebpage.py` (line 2331).

```javascript
// genro.js line 793
setAutoPolling: function(fast) {
    var delay = fast ? 2 : genro.auto_polling;
    genro.auto_polling_handler = setInterval(function() {
        if ((new Date() - genro.lastPing) / 1000 > genro.user_polling) {
            genro.rpc.ping({'reason': 'auto'});
        }
    }, delay * 1000);
}
```

Two triggers:
- **Auto** — every `auto_polling` seconds (30s default)
- **User** — on user activity, throttled by `user_polling` (3s default)

### WebSocket ping (keepalive)

**Purpose**: Connection keepalive and activity tracking.

**File**: `gnrjs/gnr_d11/js/gnrwebsocket.js` (line 63, 77)

```javascript
onopen: function() {
    this.send('connected', {'page_id': genro.page_id});
    this._interval = setInterval(function() {
        genro.wsk.ping();
    }, this.options.ping_time);  // default 1000ms
},

ping: function() {
    this.send('ping', {lastEventAge: (new Date() - genro._lastUserEventTs)});
}
```

**Server handler**: `gnrasync.py` line 315:

```python
def do_ping(self, lastEventAge=None, **kwargs):
    self.server.sharedStatus.onPing(self._page_id, lastEventAge)
    self.write_message('pong')
```

The server updates `SharedStatus` with the page's activity age, then
responds with a plain `'pong'` text message. The client ignores `'pong'`
in `onmessage()` (line 83).

### Comparison

| Aspect | HTTP Polling | WebSocket Ping |
|--------|-------------|----------------|
| Interval | 30s auto / 3s user activity | 1s fixed |
| Protocol | Full HTTP POST + XML response | JSON send + text 'pong' |
| Piggyback | Yes — carries datachanges | No — keepalive only |
| Server load | Heavy (full WSGI request) | Light (async handler) |
| Data sync | Primary mechanism (no WS) | None (use push commands) |
| Tracking | Profilers, lastRpc, children | lastEventAge only |

**Coexistence**: Both systems run simultaneously when WebSocket is active.
The HTTP ping continues to poll for datachanges from store subscriptions,
while the WebSocket ping maintains the connection and tracks activity
in SharedStatus.

## Synchronous RPC: what must use HTTP

Some calls **must** be synchronous (blocking), which is only possible
via HTTP XHR — WebSocket is inherently asynchronous.

### Bag resolvers (sync=true)

**File**: `gnrjs/gnr_d11/js/genro_rpc.js` (line 630)

```javascript
remoteResolver: function(methodname, params, kw) {
    var kwargs = objectUpdate({'sync': true}, params);  // forces sync
    kwargs.method = methodname;
    var resolver = new gnr.GnrRemoteResolver(kwargs, isGetter, cacheTime);
    return resolver;
}
```

Bag resolvers are used in `GnrBag` data trees to lazily load data.
When a node with a resolver is accessed, it **must** return the value
synchronously because the calling code expects an immediate result
(e.g., during page rendering or Bag traversal).

### Related record resolvers

**File**: `gnrjs/gnr_d11/js/genro_rpc.js` (line 799)

```javascript
remote_relOneResolver: function(params, parentbag) {
    var sync = ('sync' in params) ? objectPop(params, 'sync') : true;
    var kwargs = {'sync': sync, 'from_fld': params._from_fld, ...};
    kwargs.method = 'app.getRelatedRecord';
    var resolver = new gnr.GnrRemoteResolver(kwargs, isGetter, cacheTime);
}
```

Related record resolvers default to `sync=true` — they load linked
records when a Bag node is accessed, typically during form rendering
or grid display.

### Why sync requires HTTP

When `sync=true`, the HTTP XHR call blocks the JavaScript thread until
the response arrives (`dojo.xhrPost` with `sync: true`). This is the
only way to return a value synchronously from a remote call.

WebSocket `call()` returns a `Deferred` — it cannot block. If a resolver
has `httpMethod='WSK'`, it works asynchronously (the Deferred resolves
later), which is correct for `dataRemote` and other async-compatible
patterns but not for Bag lazy resolution.

**In practice**: Bag resolvers always use `httpMethod='POST'` (the
default) with `sync=true`. The `WSK` method is used for `dataRpc`,
`dataRemote`, and other async-compatible calls where the result is
consumed via callback.

## Summary table

| Feature | HTTP RPC | WebSocket |
|---------|----------|-----------|
| Transport | XMLHttpRequest (WSGI) | Persistent WS (async server) |
| Sync support | Yes (`sync: true`) | No (always async/deferred) |
| Server instance | `GnrWebPage` (per-request) | `GnrSimplePage` (persistent) |
| Piggyback | Yes (datachanges in response) | No |
| Push support | No (poll via ping) | Yes (direct push commands) |
| Bag resolver | Yes (required for sync) | No (deferred incompatible) |
| Method lookup | `getPublicMethod('rpc', name)` | `getWsMethod(name)` |
| Auth check | Full (`_checkAuth`) | None (trusted after connect) |
| DB connection | Per-request, with env | Reset per-call (`_db = None`) |
| dbstore | Propagated from request | Always `None` (single-store) |
| Keepalive | Polling (30s/3s) | Ping/pong (1s) |

## Known issues

### 1. Redundant HTTP polling with active WebSocket

When WebSocket is active, the HTTP polling ping continues to run
independently. This generates unnecessary WSGI requests because
store datachanges could be pushed via WebSocket instead of polled
via HTTP.

**Impact**: Extra server load from periodic HTTP requests that serve
no purpose when WebSocket push is available.

**Possible fix**: Disable HTTP polling when WebSocket is connected,
and route store datachanges through the WebSocket push mechanism.

### 2. No datachange piggyback on WebSocket RPC

The `do_call` handler in `gnrasync.py` does not collect or return
datachanges accumulated during the RPC execution. Any
`page.setInClientData()` calls within a WebSocket RPC handler
have no effect — the data is lost.

**Impact**: Server-side code that relies on `setInClientData()` or
`addLocalDatachange()` during RPC execution works correctly via HTTP
but silently fails via WebSocket.

**Possible fix**: Add `collectClientDatachanges()` to the `do_call`
envelope in `gnrasync.py`, or use `wsproxy` push after each `do_call`.

### 3. No auth check on WebSocket RPC

The HTTP path checks authentication via `_checkAuth()` before every
RPC call. The WebSocket path (`do_call`) has no such check — once
connected, any method can be called.

**Impact**: If a session expires, HTTP calls get rejected but
WebSocket calls continue to work until the connection drops.

### 4. Wsproxy socket path mismatch

See [SHARED_OBJECTS.md](SHARED_OBJECTS.md) — known issue #1.
`WsgiWebSocketHandler` connects to `sockets/async.tornado` but the
asyncio server listens on `sockets/async.aiohttp`.
