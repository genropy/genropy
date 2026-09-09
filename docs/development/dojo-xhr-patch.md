# Experimental Dojo HTTP transport

The `dojo-xhr-patch` experiment replaces supported asynchronous Dojo HTTP
requests with native fetch. It applies to `dojo.xhr`, `xhrGet`, `xhrPost`,
`xhrPut`, `xhrDelete`, `rawXhrPost` and `rawXhrPut`, including callers outside
`genro.rpc`. Fetch completes the existing Dojo Deferred directly, bypassing
the legacy 50 ms completion polling interval.

## Configuration and rollback

Add this child to the instance's `instanceconfig.xml`:

```xml
<experimental-features dojo-xhr-patch="fetch"/>
```

Restart the instance to reload its configuration, then reload browser pages.
The server supplies `dojoXhrPatch` at bootstrap; a page request parameter
cannot override the instance setting. The patch is installed when the client
is constructed, before application initialization. Requests made before that
point continue to use the original transport.

To roll back, remove the attribute (or the node if otherwise empty), restart
the instance, and reload browser pages. Existing pages keep their installed
transport until reloaded. Only the exact value `fetch` enables the patch;
absent or other values leave Dojo unchanged.

The patch lives in `genro_patch.js`, so no vendor bundle rebuild is required.
Deploy the matching Python and JavaScript changes together and refresh any
deployment-managed static caches.

## Compatibility boundary

Supported requests use same-origin HTTP(S) with existing parameter/form
serialization, headers, cookies and the built-in Dojo text, JSON, XML and
JavaScript response handlers. XML/Bag serialization and WebSocket transport
are unchanged. The experiment targets the application's UTF-8 responses;
fetch's text decoding does not reproduce XHR decoding for other charsets.

Callbacks retain their context, ordering and transformations, including
Deferred chaining and errback recovery. `ioArgs.xhr` provides response text,
XML, status, status text, ready state, response-header access and abort. It is
an adapter, not an `XMLHttpRequest` instance, and does not implement XHR event
listeners or intermediate progress events. Callers that directly attach XHR
listeners after obtaining the Deferred require a separate compatibility
assessment before enabling the experiment for their instance.

Requests with `sync`, explicit username/password authentication, non-text
`responseType`, progress/upload options, iframe proxy options, file-input
forms or nonstandard response handlers retain the original transport.
Cross-origin and non-HTTP URLs also retain it. Browsers missing the required
fetch, abort, headers, URL or XML parser APIs do not install the patch.
Separate iframe/script transports and direct `XMLHttpRequest` calls are
unaffected. The supported generic methods are GET, POST, PUT, DELETE, PATCH
and HEAD; other methods retain the original transport.

Timeouts cover response-body consumption as well as receiving headers.
Cancellation, timeout and completion settle the request once and release
the timer and pending-request entry. `dojo._ioCancelAll()` covers both
original requests and fetch requests. Failed fetch requests are never
automatically retried through XHR, avoiding duplicate writes.

## Reproducible browser checks

From the repository root:

```sh
python gnrjs/tests/dojo_xhr_server.py
```

Open `http://127.0.0.1:8765/gnrjs/tests/dojo_xhr.html`. The page runs the same
contract checks against original Dojo and patched Dojo using real HTTP
requests. Add `?build=source` or `?build=release` to exercise the other bundled
Dojo 1.1 builds. Reloading starts again with original Dojo.

Coverage includes methods and raw bodies, parameter encoding, request and
response headers, XML attributes, callback order/context, chained Deferreds,
HTTP and parse errors, XML without Content-Type, malformed XML, recovery,
cancellation, timeout, synchronous calls,
form serialization, cookies, fallback routing and fetch network failure.
An explicit assertion verifies that fetch does not enter `dojo._ioWatch`.

The page also reports a local smoke benchmark: 12 warm-up requests followed
by 50 sequential calls per transport, client p50/p95 and median server time
from `X-GnrTime`. The original transport runs first, followed by fetch. This
fixture demonstrates completion latency; it is not an application throughput
benchmark or evidence of a general application speedup.

Before broad adoption, run a real form/TableHandler flow with error and
recovery, datachanges and resource loading. Extend measurement to alternating
transport rounds, WSK, representative payload sizes, serialization time and
controlled latency/concurrency. TYTX/NBag integration remains separate work
under issues #1274 and #329; this first transport experiment does not enable
or implement that codec.

## First validation, 2026-09-09

The browser contract passed on the compact, source and release Dojo 1.1
builds. The final compact-build run passed 18 checks, including the added
response-body timeout check. Its 50-call smoke benchmark reported:

| Transport | Client p50 | Client p95 | Server p50 |
| --- | ---: | ---: | ---: |
| Original Dojo | 51.60 ms | 52.00 ms | 0.11 ms |
| Dojo with fetch | 1.10 ms | 5.30 ms | 0.05 ms |

Three configuration tests and the existing webpage regression test passed.
JavaScript syntax checks and the Python lint selection used by CI passed;
new Python files also passed the default flake8 checks.

The full Python suite reported 1,564 passed, 86 skipped, 759 setup errors and
two failures. PostgreSQL initialization encountered exhausted system shared
memory resources (`shmget: No space left on device`, not disk exhaustion).
The two CSV failures (`test_getCsvDialect_limited_lines` and
`test_CsvReader_auto_dialect`) also reproduce in isolation without importing
the modified webpage module. This run does not establish a green full suite.
Real form/TableHandler validation and the broader benchmark remain pending.

## XML compatibility and instance validation, 2026-09-09

Responses without Content-Type now use XHR's XML default. Explicit text/plain
responses still have no responseXML. Malformed XML is recognized with both
the Mozilla and XHTML parser-error namespaces used by browser engines.
The added contract check first reproduced both regressions, then passed
after the corrections. The updated suite passed 20 checks on each bundled
Dojo build in the integrated browser, and on the compact build in Chrome.

The `/test/datastore/dojo_xhr` testhandler page exercises real application
RPC, the returned Dojo Deferred, callback chaining, Bag results, datachanges,
error recovery and a province TableHandler. Run it against a disposable
instance with the transport option enabled. Set the site's `wsgi.debug` to
`false` to exercise application error callbacks; debug mode can re-raise
the deliberate exception as HTTP 500.

Validation on the isolated `sandboxpg_fetchmode` PostgreSQL instance passed
the RPC and datachange checks, HTTP and application error recovery, resource
loading, and form load/save. A province name was changed through the form,
verified directly in PostgreSQL, and restored through the form. The runtime
used Python and JavaScript from the feature worktree. Four Python bootstrap
and webpage tests passed. After rebasing onto current develop, the full Python
suite passed with 2,509 passed and 10 skipped (Python 3.13). The compact browser
contract and application RPC/error-recovery checks also passed after the rebase.
Broader latency/concurrency measurements remain pending.
