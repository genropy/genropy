# gnr_async — Server asincrono Genro (asyncio/aiohttp)

Reimplementazione del server asincrono Genro (`gnrasync.py`, basato su Tornado)
usando **asyncio nativo** e **aiohttp**.

## Moduli

| Modulo | Descrizione |
|--------|-------------|
| `gnrasync_io.py` | Server principale: WebSocket, shared objects, debug remoto, proxy HTTP |

## Architettura

Il server async gestisce esclusivamente la comunicazione real-time.
Il serving delle pagine web (WSGI) gira come processo separato,
sia in sviluppo che in produzione.

```
Browser ──WebSocket──► gnr_async (aiohttp)
                          │
                          ├── WebSocketSession: RPC, routing, ping
                          ├── SharedObjectsManager: oggetti condivisi real-time
                          ├── DebugSession: debug remoto via TCP
                          └── WsProxyHandler: bridge HTTP ← server WSGI

Server WSGI ──Unix socket──► gnr_async (wsproxy)
```

## Componenti principali

### WebSocketSession
Gestisce la connessione WebSocket con il browser. Riceve comandi JSON
e li smista ai metodi `do_*`:

- `do_connected` — registra la pagina
- `do_call` — RPC: invoca metodi Python della pagina (threadpool)
- `do_ping` — keepalive
- `do_route` — inoltra messaggi tra pagine
- `do_service` — servizi remoti
- `do_pdb_command` — debug remoto

### SharedObject
Oggetto condiviso tra pagine per collaborazione real-time.
Le modifiche vengono propagate in broadcast a tutte le pagine sottoscritte.

Funzionalita:
- Persistenza su file XML o database SQL
- Controllo accesso tramite tag (read/write)
- Backup automatico con versioning
- Scadenza automatica dopo disconnessione
- Lock per serializzazione modifiche

Sottoclassi:
- `SharedStatus` — stato globale del server (utenti, connessioni, pagine)
- `SharedLogger` — logging condiviso
- `SqlSharedObject` — placeholder per estensioni SQL

### DebugSession
Sessione di debug remoto via socket TCP. Collega il debugger Python (PDB)
al browser tramite code async bidirezionali.

### AioWebSocket
Wrapper di compatibilita su `aiohttp.WebSocketResponse` che espone
`write_message()` per interoperare con `AsyncWebSocketHandler` esistente.

## Differenze rispetto a gnrasync.py (Tornado)

| Aspetto | Tornado | asyncio/aiohttp |
|---------|---------|-----------------|
| Coroutine | `@gen.coroutine` / `yield` | `async def` / `await` |
| Lock | `tornado.locks.Lock` | `asyncio.Lock` |
| Code | `tornado.queues.Queue` | `asyncio.Queue` |
| WebSocket server | `tornado.websocket` | `aiohttp.web.WebSocketResponse` |
| HTTP handler | `tornado.web.RequestHandler` | funzioni `aiohttp.web` |
| TCP server (debug) | `tornado.tcpserver.TCPServer` | `asyncio.start_unix_server` |
| Unix socket | `tornado.netutil.bind_unix_socket` | `aiohttp.web.UnixSite` |
| WSGI bridge | `tornado_wsgi.WSGIHandler` | rimosso (processo separato) |

## Dipendenze

- `aiohttp` (gia presente nel progetto)
- Nessuna dipendenza aggiuntiva rispetto al progetto base
