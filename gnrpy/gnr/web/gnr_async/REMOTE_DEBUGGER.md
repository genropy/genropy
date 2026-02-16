# Remote Debugger — Architecture and Status

Genro includes a built-in remote Python debugger that runs entirely in the
browser, integrated with the GnrIDE component. It allows setting breakpoints,
stepping through code, inspecting the call stack, and evaluating expressions
— all from within the Genro application itself.

## Overview

The debugger bridges Python's `pdb.Pdb` to the browser through two
independent channels:

1. **Unix socket (TCP)** — connects the Python debugger (running in a WSGI
   thread) to the async server
2. **WebSocket** — connects the async server to the browser (GnrIDE)

```
WSGI Thread (GnrPdb)          Async Server               Browser (GnrIDE)
       |                           |                           |
       |-- Unix socket ----------->|                           |
       |   stdout: B64-encoded     |                           |
       |   Bag (stack, vars, bp)   |                           |
       |                           |-- WebSocket ------------->|
       |                           |   pdb_out_bag / pdb_out_line
       |                           |                           |
       |                           |<-- WebSocket -------------|
       |                           |   pdb_command             |
       |<-- Unix socket -----------|   {cmd, pdb_id}           |
       |   stdin: PDB command      |                           |
```

## Components

### GnrPdb (Python debugger)

**File**: `gnrpy/gnr/web/gnrwebpage_proxy/gnrpdb.py` (class `GnrPdb`)

Subclass of `pdb.Pdb`. Created when a WSGI page has active breakpoints.

**Lifecycle**:

1. `GnrPdbClient.onPageStart()` is called at every `GnrWebPage.__call__()`
2. Reads breakpoints from `connectionStore['_pdb.breakpoints']`
3. If breakpoints exist, creates a `GnrPdb` instance
4. `GnrPdb.__init__()` connects to the async server via Unix socket
5. Sends identification: `\0{debugger_page_id},{pdb_id}\n`
6. Installs `sys.settrace()` and starts debugging

**Key overrides**:

- `format_stack_entry()` — builds a `Bag` with stack frames, local variables,
  watches, breakpoint list, and PDB state. Encodes it as Base64 XML and sends
  it through the socket. Also publishes `debugstep` to the debugged page
  (for the "Debug/Continue" overlay).
- `set_break()` / `clear_break()` — manage breakpoints on the `Breakpoint`
  registry, keeping track in `self.mybp` for cleanup.
- `do_level()` — custom command to navigate stack levels, updates
  `curindex`/`curframe` and re-prints the stack entry.
- `onClosePage()` — cleans up breakpoints and sends `close_debugger` to
  the IDE page.

**I/O redirection**: PDB's `stdin`/`stdout` are redirected to a file-like
object wrapping the Unix socket (`self.sock.makefile('rw')`). PDB reads
commands from the socket and writes output to the socket.

### GnrPdbClient (page proxy)

**File**: `gnrpy/gnr/web/gnrwebpage_proxy/gnrpdb.py` (class `GnrPdbClient`)

Proxy attached to `GnrWebPage` as `page.pdb`. Provides:

- `setBreakpoint(module, line, condition, evt)` — `@public_method` called
  from GnrIDE to add/remove breakpoints in `connectionStore`
- `getBreakpoints(module)` — `@public_method` to retrieve current breakpoints
- `onPageStart()` — entry point called at each RPC invocation

### DebugSession (async server bridge)

**File**: `gnrpy/gnr/web/gnrasync.py` (class `DebugSession`)

Handles a single TCP connection from `GnrPdb`. Uses four async queues to
bridge TCP ↔ WebSocket bidirectionally:

```
Unix Socket                    DebugSession                    WebSocket
    |                              |                              |
    |--read_until('\n')-->  socket_input_queue                    |
    |                       handle_socket_message()               |
    |                              |                              |
    |                       websocket_output_queue  -->write_message()
    |                              |                              |
    |                       websocket_input_queue  <--do_pdb_command()
    |                              |                              |
    |  <--stream.write()--  socket_output_queue                   |
```

**Queue flow**:

1. `dispatch_client()` — reads lines from TCP socket, puts in
   `socket_input_queue`
2. `consume_socket_input_queue()` → `handle_socket_message()`:
   - First message starts with `\0` or `|`: calls `link_debugger()` to
     associate the session with a `page_id` and `pdb_id`
   - Subsequent messages: puts in `websocket_output_queue`
3. `consume_websocket_output_queue()` — decodes B64 or wraps as
   `pdb_out_line`, sends to browser via `channels[page_id].write_message()`
4. `consume_websocket_input_queue()` — receives commands from browser
   (via shared `debug_queues`), puts in `socket_output_queue`
5. `consume_socket_output_queue()` — writes command back to TCP socket
   (PDB's stdin)

**Shared queue**: `debug_queues` is a dict on the server, keyed by
`{page_id},{pdb_id}`. Both `do_pdb_command` (WebSocket handler) and
`link_debugger` (DebugSession) access the same queue, creating it on
first access from either side.

### GnrDebugServer (TCP server)

**File**: `gnrpy/gnr/web/gnrasync.py` (class `GnrDebugServer`)

Tornado `TCPServer` that listens on the Unix socket. For each incoming
connection, creates a `DebugSession` and calls `on_connect()`.

### GnrIDE (JavaScript client)

**File**: `resources/common/gnrcomponents/gnride/gnride.js`

Registers three dynamic WebSocket handlers on initialization:

```javascript
genro.wsk.addhandler('do_pdb_out_bag',  function(data){ that.onPdbAnswer_bag(data); });
genro.wsk.addhandler('do_pdb_out_line', function(data){ that.onPdbAnswer_line(data); });
genro.wsk.addhandler('do_close_debugger', function(pdb_id){ that.closeDebugger(pdb_id); });
```

**`onPdbAnswer_bag(data)`**: Opens a debug tab in the IDE editor stack with:
- Source code with current line highlighted
- Call stack with navigation
- Local variables
- Watches
- Breakpoint list

**`onPdbAnswer_line(data)`**: Appends text output to the debug terminal.

**`sendCommand(command, pdb_id)`**: Sends a PDB command via WebSocket:
```javascript
genro.wsk.send("pdb_command", {cmd: command, pdb_id: pdb_id});
```

**Toolbar buttons**: `doNext()`, `doStep()`, `doReturn()`, `doContinue()`,
`doJump(lineno)`, `doLevel(level)`.

### Debugged page overlay (genro_dev.js)

**File**: `gnrjs/gnr_d11/js/genro_dev.js`

When a breakpoint is hit, the **debugged page** (not the IDE) receives a
`debugstep` publish event with info about the current frame. This triggers:

- `onDebugstep()` — shows a floating box on the page with module, function,
  line number
- Two buttons: **Debug** (opens GnrIDE) and **Continue** (sends `c` command)
- `addToDebugged()` — suspends the pending RPC call (prevents timeout)
- `removeFromDebugged()` — resumes after continue

The overlay HTML is rendered into `<div id="pdb_root">` (defined in
`gnrjs/gnr_d11/tpl/standard.tpl`), with dedicated CSS classes in
`gnrjs/gnr_d11/css/gnrbase.css`.

## Breakpoint management

Breakpoints are stored in the `connectionStore` under `_pdb.breakpoints`:

```
_pdb.breakpoints.{module_key}.r_{line}
    @module = "/path/to/module.py"
    @line = 42
    @condition = "x > 10"  (optional)
```

The IDE calls `page.pdb.setBreakpoint()` (RPC) to add/remove breakpoints.
At each WSGI request, `GnrPdbClient.onPageStart()` reads all breakpoints
and creates a `GnrPdb` instance if any exist.

Breakpoints persist across page refreshes (stored in `connectionStore`,
not page-local state).

## Debug session lifecycle

1. User sets breakpoint in GnrIDE → `setBreakpoint()` RPC → saved in
   `connectionStore`
2. User triggers an action on the debugged page → WSGI request
3. `GnrWebPage.__call__()` → `pdb.onPageStart()` → finds breakpoints
4. `GnrPdb` created → connects to async server Unix socket
5. `sys.settrace()` installed → execution proceeds until breakpoint hit
6. PDB stops → `format_stack_entry()` sends state to IDE via socket → async
   server → WebSocket
7. IDE shows debug tab with source, stack, variables
8. User sends command (next/step/continue) → WebSocket → async server →
   socket → PDB stdin
9. PDB executes command → sends new state → cycle repeats
10. On continue past last breakpoint → PDB detaches → WSGI request completes
11. `onClosePage()` → cleans up breakpoints → sends `close_debugger` to IDE

## Socket path (fixed)

All components now use the canonical name `sockets/debugger.sock`:

| Component | Socket name |
|-----------|-------------|
| `GnrPdb` (client) | `sockets/debugger.sock` |
| `gnrasync.py` (Tornado server) | `sockets/debugger.sock` |
| `gnrasync_io.py` (asyncio server) | `sockets/debugger.sock` |

Previously, each server used a different name (`debugger.tornado`,
`debugger.aiohttp`) while the client connected to `debugger.sock`,
making the debugger non-functional. This has been fixed by aligning
all components to the single canonical name.

## Value assessment

The integrated debugger provides capabilities that external debuggers
(VS Code, PyCharm) cannot replicate:

- **Context-aware**: sees Bag structures, shared objects, connection state
- **Zero setup**: no launch.json, no attach configuration, no port mapping
- **In-browser**: debug directly from the application, no IDE switching
- **Collaborative**: works with GnrIDE's code editor, which understands
  Genro's resource/mixin/component system
- **RPC-aware**: suspends the pending RPC call while debugging, preventing
  timeouts on the client side

The code is complete and intact (Python, JavaScript, CSS, HTML template).
Only the socket name mismatch prevents it from working.

**Recommendation**: fix the socket path and re-enable the debugger.
