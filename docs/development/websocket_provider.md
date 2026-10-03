# The optional WebSocket provider

A classic installation serves WebSockets through `WsgiWebSocketHandler`, which
reaches the `gnrasync` daemon over `sockets/async.sock`, and loads the
`gnrwebsocket` client. Nothing here changes that: with `GNR_DAEMON_PROVIDER`
unset the entry points are never even looked up.

## Selection

`GNR_DAEMON_PROVIDER` is the one variable. It already selects the register
provider (`gnr.web.daemon`); the same name is matched against the `gnr.web`
entry point `websockethandler`, on either the entry point's module or the name
of the distribution declaring it. Selection is per process: set the variable
before anything imports the site.

A provider is free to declare only the register. Zero matching entry points is
not an error — the classic handler stays, its probe finds no `async.sock`, and
the site runs with WebSockets off. An HTTP-only provider therefore starts.
Two entry points for one provider, or one that is not a class carrying
`checkSocket` and `sendCommandToPage`, raises `ImportError`: those are
configuration statements that cannot be honoured.

## What the site does with it

`GnrWsgiSite.__init__` resolves the class once into `site.websocket_handler_class`
and `site.wsk` builds it with the site as its one argument.

A selected provider also turns `site.websockets` on where the classic handler
leaves it off: the provider terminates the socket in the server that serves the
site, so there is no daemon to reach and no `wsgi?websockets` word to write. The
usual `checkSocket()` still decides whether the handler is kept.

## The client

A selected handler may declare `client_module`, the name of a javascript module
in `gnrjs/gnr_d11/js`. `GnrWebPage.gnrjs_imports` puts it where `gnrwebsocket`
was: it takes the place of the classic client, never a place beside it, so a
page declares one `gnr.GnrWebSocketHandler`. A handler without the attribute
leaves the frontend imports untouched.

`gnrwebsocket_kajenn` is the client genropy ships for a provider whose server
terminates the socket and speaks WSX. The wire format is the text `WSX://`
followed by a JSON object with `id`, `method`, `path`, `page_id` and `data`,
where `data` is the payload serialized as a TYTX json string; an answer carries
`id`, `status` and `data`.

What it carries:

- the channel of the page, on `/_wsx/openchannel`, sent at every opening of the
  socket — a reconnection opens the channel again — and answered before any
  call of the page is written;
- the ping, on `/_wsx/ping`;
- a page RPC sent with `dataRpc(httpMethod='WSK')`: the same form the HTTP
  branch posts, urlencoded into the `form` field of the payload. The answer is
  the site's own response body with its content-type, handed to
  `genro.rpc.resultHandler`, so datachanges and `js_requires` of that call are
  applied exactly as over HTTP.

What it does not carry: shared objects (`som.*`), `user_event`, `route`, and
anything the server sends on its own. `send` logs what it is given and drops it.
Datachanges outside a call's own answer and dbevents stay on the pull road.
