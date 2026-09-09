# Optional WebSocket provider

Classic installations continue to use the existing WebSocket handler and client.
Installing an alternative provider does not activate it. Selection reuses
`GNR_DAEMON_PROVIDER`, the existing daemon selector; there is no separate
WebSocket switch. The selected provider also exports a `gnr.web` entry point
called `websockethandler`. The bridge selects `genropy-asgi` for both interfaces.

The provider must export a handler class with `checkSocket` and
`sendCommandToPage`. An explicitly selected missing, ambiguous or invalid provider
raises ImportError at import time rather than silently falling back. Set the
variable before importing the site; provider selection is process-wide, not a
per-request switch.

A selected handler can declare `client_module`; this replaces the
`gnrwebsocket` entry in the frontend's JavaScript imports. Without selection,
the frontend imports are untouched. A selected handler without this attribute
keeps the original client. Normal site WebSocket enablement is still required.

The supplied `gnrwebsocket_asgi` client implements the initial genropy-asgi
request/response contract: open an owned page channel, send correlated WSK calls,
and process ordinary legacy XML/JSON RPC results. It requires the corresponding
bridge adapter (genropy/genropy-asgi#22). It does not provide full gnrasync
compatibility: unsolicited push, shared objects, automatic reconnection and
cookie-changing authentication flows are outside this increment.

The provider variable does not need to be set for ordinary WSGI deployments.
