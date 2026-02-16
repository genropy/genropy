# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrasync_io : async server based on asyncio/aiohttp
# Copyright (c) : 2004 - 2026 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Server asincrono Genro basato su asyncio e aiohttp.

Questo modulo sostituisce gnrasync.py (basato su Tornado) con un'implementazione
moderna che usa asyncio nativo e aiohttp per:

- WebSocket bidirezionali tra browser e server
- Shared Objects per collaborazione real-time tra pagine
- Debug remoto via socket TCP
- Proxy HTTP per invio comandi alle pagine

Il modulo NON gestisce il serving WSGI delle pagine web. In sviluppo e in
produzione, il server WSGI gira come processo separato.
"""

import asyncio
import base64
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from functools import wraps

from aiohttp import web, WSMsgType

from gnr.core.gnrbag import Bag, TraceBackResolver
from gnr.core.gnrstring import fromJson
from gnr.web import logger
from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import AsyncWebSocketHandler
from gnr.web.gnrwsgisite import GnrWsgiSite


# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------

MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

class ObjectDict(dict):
    """Dict che consente accesso ai valori anche come attributi.

    Esempio::

        d = ObjectDict(name='foo')
        d.name  # 'foo'
        d.name = 'bar'
    """

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f'No attribute or item: {name}')

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError(f'No attribute or item: {name}')


class AioWebSocket:
    """Wrapper su aiohttp.WebSocketResponse per compatibilità con
    AsyncWebSocketHandler.

    AsyncWebSocketHandler (in gnrwebsockethandler.py) chiama
    ``server.channels[page_id].write_message(data)`` per inviare messaggi.
    aiohttp usa ``ws.send_str(data)`` che è una coroutine. Questo wrapper
    espone ``write_message`` e schedula l'invio nell'event loop.
    """

    def __init__(self, ws):
        self._ws = ws

    def write_message(self, message):
        """Invia un messaggio al WebSocket.

        Schedula l'invio come task nell'event loop corrente, così può essere
        chiamato anche da contesti sincroni (es. callback di Bag.subscribe).
        """
        asyncio.ensure_future(self._ws.send_str(message))


# ---------------------------------------------------------------------------
# Decoratori
# ---------------------------------------------------------------------------

def threadpool(func):
    """Marca un metodo per l'esecuzione nel ThreadPoolExecutor.

    Il WebSocket handler controlla questo attributo per decidere se eseguire
    il metodo nel threadpool (per operazioni bloccanti come accesso al DB)
    o direttamente nell'event loop.
    """
    func._executor = 'threadpool'
    return func


def locked_coroutine(f):
    """Decorator che acquisisce ``self.lock`` (asyncio.Lock) prima di
    eseguire la coroutine async.

    Usato per serializzare operazioni concorrenti sullo stesso SharedObject.
    """
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        async with self.lock:
            result = await f(self, *args, **kwargs)
            return result
    return wrapper


def locked_threadpool(f):
    """Decorator che acquisisce ``self.lock`` e poi esegue la funzione
    nel ThreadPoolExecutor del server.

    Usato per operazioni bloccanti (save/load su file o DB) che devono
    essere serializzate.
    """
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        async with self.lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self.server.executors.get('threadpool'),
                lambda: f(self, *args, **kwargs)
            )
    return wrapper


# ---------------------------------------------------------------------------
# Debug remoto via socket TCP
# ---------------------------------------------------------------------------

class DebugSession:
    """Sessione di debug remoto via socket TCP.

    Gestisce la comunicazione bidirezionale tra il debugger (PDB) connesso
    via socket TCP e il browser connesso via WebSocket. I messaggi fluiscono
    attraverso code async:

    - socket_input_queue: dati dal debugger → handler
    - socket_output_queue: dati verso il debugger
    - websocket_output_queue: dati verso il browser (WebSocket)
    - websocket_input_queue: comandi dal browser → debugger
    """

    def __init__(self, reader, writer, server):
        self._reader = reader
        self._writer = writer
        self.server = server
        self.pdb_id = None
        self._page_id = None
        self.socket_input_queue = asyncio.Queue(maxsize=40)
        self.socket_output_queue = asyncio.Queue(maxsize=40)
        self.websocket_output_queue = asyncio.Queue(maxsize=40)
        self.websocket_input_queue = None
        asyncio.ensure_future(self._consume_socket_input_queue())

    @property
    def page_id(self):
        return self._page_id

    @page_id.setter
    def page_id(self, value):
        self._page_id = value

    @property
    def channels(self):
        return self.server.channels

    @property
    def debug_queues(self):
        return self.server.debug_queues

    def link_debugger(self, debugkey):
        """Collega la sessione TCP a una pagina browser per il debug.

        Args:
            debugkey: stringa "page_id,pdb_id" che identifica la sessione.
        """
        page_id, pdb_id = debugkey.split(',')
        self.page_id = page_id
        self.pdb_id = pdb_id
        if debugkey not in self.debug_queues:
            self.debug_queues[debugkey] = asyncio.Queue(maxsize=40)
        self.websocket_input_queue = self.debug_queues[debugkey]
        asyncio.ensure_future(self._consume_websocket_output_queue())
        asyncio.ensure_future(self._consume_websocket_input_queue())
        asyncio.ensure_future(self._consume_socket_output_queue())

    async def _handle_socket_message(self, message):
        """Smista un messaggio ricevuto dal socket TCP.

        Se inizia con '\\0' o '|', è un comando di collegamento debugger.
        Altrimenti è un output PDB da inoltrare al browser.
        """
        if message.startswith('\0') or message.startswith('|'):
            self.link_debugger(message[1:])
        else:
            await self.websocket_output_queue.put(message)

    async def _consume_socket_input_queue(self):
        """Loop che processa i messaggi in arrivo dal socket TCP."""
        while True:
            message = await self.socket_input_queue.get()
            await self._handle_socket_message(message)

    async def _consume_socket_output_queue(self):
        """Loop che invia messaggi al debugger via socket TCP."""
        while True:
            message = await self.socket_output_queue.get()
            self._writer.write(f'{message}\n'.encode())
            await self._writer.drain()

    async def _consume_websocket_input_queue(self):
        """Loop che riceve comandi dal browser e li inoltra al debugger."""
        while True:
            message = await self.websocket_input_queue.get()
            await self.socket_output_queue.put(str(message))

    async def _consume_websocket_output_queue(self):
        """Loop che invia output PDB al browser via WebSocket."""
        while True:
            data = await self.websocket_output_queue.get()
            if data.startswith('B64:'):
                envelope = base64.b64decode(data[4:])
            else:
                data = Bag(dict(line=data, pdb_id=self.pdb_id))
                envelope = Bag(dict(command='pdb_out_line', data=data)).toXml()
            self.channels.get(self.page_id).write_message(envelope)

    async def dispatch_client(self):
        """Legge righe dal socket TCP e le accoda per l'elaborazione."""
        try:
            while True:
                line = await self._reader.readline()
                if not line:
                    break
                line = line.decode().rstrip('\n')
                await self.socket_input_queue.put(line)
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass


async def _debug_client_handler(reader, writer, server):
    """Callback per asyncio.start_unix_server: crea una DebugSession
    e gestisce la connessione fino alla disconnessione.
    """
    session = DebugSession(reader, writer, server)
    await session.dispatch_client()
    writer.close()
    await writer.wait_closed()


# ---------------------------------------------------------------------------
# Handler HTTP: proxy WebSocket
# ---------------------------------------------------------------------------

async def ws_proxy_handler(request):
    """Handler HTTP POST per inviare messaggi alle pagine via WebSocket.

    Riceve richieste dal server WSGI (che gira in un processo separato)
    e le inoltra alle pagine connesse via WebSocket. Supporta:

    - Invio a una pagina specifica (page_id)
    - Invio a un servizio remoto (remote_service → page_id)
    - Broadcast a tutte le pagine (page_id='*')
    - Comandi esterni al server (page_id vuoto)
    """
    server = request.app['server']
    data = await request.post()
    page_id = data.get('page_id', '')
    envelope = data.get('envelope', '')
    remote_service = data.get('remote_service', '')

    if remote_service:
        page_id = server.remote_services.get(remote_service)
        if not page_id:
            return web.Response()

    if not page_id:
        envelope_bag = Bag(envelope)
        command = envelope_bag['command']
        cmd_data = envelope_bag['data']
        server.external_command(command, cmd_data)
        return web.Response()

    if page_id == '*':
        page_ids = list(server.channels.keys())
    else:
        page_ids = page_id.split(',')

    for dest_page_id in page_ids:
        channel = server.channels.get(dest_page_id)
        if channel:
            channel.write_message(envelope)

    return web.Response()


# ---------------------------------------------------------------------------
# Handler WebSocket
# ---------------------------------------------------------------------------

class WebSocketSession:
    """Gestisce una singola connessione WebSocket con un browser.

    Ogni sessione corrisponde a una pagina Genro aperta nel browser.
    Riceve comandi JSON dal client e li smista ai metodi ``do_*``
    corrispondenti. I comandi possono essere:

    - ``connected``: registra la pagina
    - ``call``: invoca un metodo server-side (eseguito nel threadpool)
    - ``ping``: keepalive
    - ``route``: inoltra messaggio a un'altra pagina
    - ``som.*``: operazioni su SharedObject
    - ``pdb_command``: comandi per il debugger remoto
    """

    def __init__(self, ws, server):
        self._ws = ws
        self.server = server
        self._page_id = None

    @property
    def page_id(self):
        return self._page_id

    @page_id.setter
    def page_id(self, value):
        self._page_id = value

    @property
    def channels(self):
        return self.server.channels

    @property
    def remote_services(self):
        return self.server.remote_services

    @property
    def pages(self):
        return self.server.pages

    @property
    def page(self):
        return self.pages[self.page_id]

    @property
    def gnrsite(self):
        return self.server.gnrsite

    @property
    def debug_queues(self):
        return self.server.debug_queues

    def _get_executor(self, method):
        """Restituisce l'executor associato al metodo, se marcato con @threadpool."""
        executor_name = getattr(method, '_executor', None)
        if executor_name:
            return self.server.executors.get(executor_name)
        return None

    def _get_handler(self, command, kwargs):
        """Risolve il comando nel metodo do_* corrispondente.

        Supporta comandi semplici (es. 'call') e con namespace
        (es. 'som.subscribe' → server.som.do_subscribe).
        """
        if '.' not in command:
            return getattr(self, 'do_%s' % command, self._wrong_command)

        kwargs['page_id'] = self.page_id
        proxy = self.server
        while '.' in command:
            proxy_name, command = command.split('.', 1)
            proxy = getattr(proxy, proxy_name, None)
        if proxy is None:
            return self._wrong_command
        return getattr(proxy, 'do_%s' % command, self._wrong_command)

    async def on_message(self, message):
        """Processa un messaggio JSON ricevuto dal WebSocket.

        Parsa il messaggio, trova l'handler appropriato, lo esegue
        (nel threadpool se marcato con @threadpool) e invia la risposta.
        """
        command, result_token, kwargs = self._parse_message(message)
        handler = self._get_handler(command, kwargs)
        if not handler:
            return

        executor = self._get_executor(handler)
        if executor:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                executor, lambda: handler(_time_start=time.time(), **kwargs)
            )
        else:
            result = handler(_time_start=time.time(), **kwargs)
            if asyncio.iscoroutine(result):
                result = await result

        if result_token:
            result = Bag(dict(token=result_token, envelope=result)).toXml(unresolved=True)
        if result is not None:
            await self._ws.send_str(result)

    def on_close(self):
        """Chiamato alla chiusura del WebSocket. Rimuove la pagina dai canali."""
        self.channels.pop(self.page_id, None)
        self.server.unregister_page(page_id=self.page_id)

    def do_echo(self, data=None, **kwargs):
        """Restituisce i dati ricevuti (per test)."""
        return data

    def do_ping(self, lastEventAge=None, **kwargs):
        """Gestisce il keepalive dal browser."""
        self.server.shared_status.onPing(self._page_id, lastEventAge)
        asyncio.ensure_future(self._ws.send_str('pong'))

    def do_user_event(self, event=None, **kwargs):
        """Registra un evento utente (movimento mouse, keypress, ecc.)."""
        self.server.shared_status.onUserEvent(self._page_id, event)

    def do_route(self, target_page_id=None, envelope=None, **kwargs):
        """Inoltra un messaggio a un'altra pagina."""
        ws = self.channels.get(target_page_id)
        if ws:
            ws.write_message(envelope)

    def do_register_service(self, page_id=None, gateway_service=None, **kwargs):
        """Registra un servizio remoto associato a una pagina."""
        if gateway_service:
            self.remote_services[gateway_service] = page_id
        self.do_connected(page_id=page_id, **kwargs)

    @threadpool
    def do_service(self, gateway_service=None, **kwargs):
        """Gestisce una richiesta a un servizio remoto (eseguito nel threadpool)."""
        service = self.gnrsite.getService(
            service_type='remotewsservice', service_name=gateway_service
        )
        if service and hasattr(service, 'on_message'):
            service.on_message(**kwargs)

    def do_connected(self, page_id=None, **kwargs):
        """Registra la pagina alla connessione WebSocket."""
        self._page_id = page_id
        if page_id not in self.channels:
            self.channels[page_id] = AioWebSocket(self._ws)
        if page_id not in self.pages:
            self.server.register_page(page_id=page_id)

    def do_pdb_command(self, cmd=None, pdb_id=None, **kwargs):
        """Invia un comando al debugger remoto."""
        debugkey = '%s,%s' % (self.page_id, pdb_id)
        if debugkey not in self.debug_queues:
            self.debug_queues[debugkey] = asyncio.Queue(maxsize=40)
        data_queue = self.debug_queues[debugkey]
        data_queue.put_nowait(cmd)

    @threadpool
    def do_call(self, method=None, _time_start=None, **kwargs):
        """Invoca un metodo server-side della pagina (eseguito nel threadpool).

        Questo è il meccanismo principale di RPC: il browser chiama un metodo
        Python della pagina e riceve il risultato come Bag XML.
        """
        error = None
        result = None
        result_attrs = None
        self.page._db = None
        handler = self.page.getWsMethod(method)
        if handler:
            try:
                result = handler(**kwargs)
                if isinstance(result, tuple):
                    result, result_attrs = result
            except Exception as e:
                result = TraceBackResolver()()
                error = str(e)
        envelope = Bag()
        envelope.setItem('data', result, _attributes=result_attrs,
                         _server_time=time.time() - _time_start)
        if error:
            envelope.setItem('error', error)
        return envelope

    def _wrong_command(self, command=None, **kwargs):
        """Handler di fallback per comandi sconosciuti."""
        return 'WRONG COMMAND: %s' % command

    def _parse_message(self, message):
        """Parsa un messaggio JSON dal WebSocket.

        Converte i valori tipizzati usando il catalog dell'applicazione
        e restituisce (command, result_token, kwargs).
        """
        kwargs = fromJson(message)
        catalog = self.server.gnrapp.catalog
        result = {}
        for k, v in list(kwargs.items()):
            k = k.strip()
            if isinstance(v, (bytes, str)):
                try:
                    v = catalog.fromTypedText(v)
                except Exception:
                    raise
            result[k] = v
        command = result.pop('command')
        result_token = result.pop('result_token', None)
        return command, result_token, result


async def websocket_handler(request):
    """Handler aiohttp per le connessioni WebSocket.

    Crea un WebSocketSession per ogni connessione e processa i messaggi
    in arrivo fino alla chiusura.
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    server = request.app['server']
    session = WebSocketSession(ws, server)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await session.on_message(msg.data)
            elif msg.type == WSMsgType.ERROR:
                logger.error('WebSocket error: %s', ws.exception())
    finally:
        session.on_close()

    return ws


# ---------------------------------------------------------------------------
# SharedObject: oggetti condivisi real-time
# ---------------------------------------------------------------------------

class SharedObject:
    """Oggetto condiviso tra pagine per collaborazione real-time.

    Permette a più pagine browser di condividere e sincronizzare dati.
    Le modifiche di una pagina vengono propagate in broadcast a tutte
    le altre pagine sottoscritte. Supporta:

    - Persistenza su file XML o database
    - Controllo di accesso tramite tag (read_tags, write_tags)
    - Backup automatico con versioning
    - Lock per serializzare le modifiche
    - Scadenza automatica dopo l'ultima disconnessione

    Args:
        manager: il SharedObjectsManager proprietario.
        shared_id: identificativo univoco dell'oggetto.
        expire: secondi dopo i quali l'oggetto viene distrutto
            se nessuna pagina è sottoscritta. 0 = immediato, -1 = mai.
        startData: dati iniziali (Bag o dict).
        read_tags: tag richiesti per leggere.
        write_tags: tag richiesti per scrivere.
        filepath: percorso file per persistenza (opzionale).
        dbSaveKw: parametri per persistenza su database (opzionale).
        saveInterval: intervallo di salvataggio automatico (opzionale).
        autoSave: se True, salva alla distruzione.
        autoLoad: se True, carica all'inizializzazione.
    """

    default_savedir = 'site:async/sharedobjects'

    def __init__(self, manager, shared_id, expire=None, startData=None,
                 read_tags=None, write_tags=None, filepath=None,
                 dbSaveKw=None, saveInterval=None, autoSave=None,
                 autoLoad=None, **kwargs):
        self.manager = manager
        self.lock = asyncio.Lock()
        self.server = manager.server
        self.shared_id = shared_id
        self._data = Bag(dict(root=Bag(startData)))
        self.read_tags = read_tags
        self.write_tags = write_tags
        self._data.subscribe('datachanges', any=self._on_data_trigger)
        self.subscribed_pages = {}
        self.expire = expire or 0
        self.focused_paths = {}
        if self.expire < 0:
            self.expire = 365 * 24 * 60 * 60
        self.timeout = None
        self.auto_save = autoSave
        self.save_interval = saveInterval
        self.auto_load = autoLoad
        self.changes = False
        self.db_save_kw = dbSaveKw
        self.on_init(**kwargs)

    @property
    def savepath(self):
        """Percorso del file XML per la persistenza."""
        return self.server.gnrsite.storageNode(
            self.default_savedir, '%s.xml' % self.shared_id
        )

    @property
    def data(self):
        """I dati condivisi (il nodo 'root' del Bag interno)."""
        return self._data['root']

    @property
    def sql_data_column(self):
        """Nome della colonna DB per i dati."""
        return self.db_save_kw.get('data_column') or 'shared_data'

    @property
    def sql_backup_column(self):
        """Nome della colonna DB per il backup."""
        return self.db_save_kw.get('backup_column') or 'shared_backup'

    @locked_threadpool
    def save(self):
        """Salva i dati su file XML o database (eseguito nel threadpool con lock).

        Se dbSaveKw è configurato, salva nel database usando il metodo
        saveSharedObject della tabella (se disponibile) o sql_save.
        Altrimenti salva come file XML.
        """
        if self.changes:
            if self.db_save_kw:
                kw = dict(self.db_save_kw)
                tblobj = self.server.db.table(kw.pop('table'))
                handler = getattr(tblobj, 'saveSharedObject', None)
                if handler:
                    handler(self.shared_id, self.data, **kw)
                else:
                    self._sql_save(tblobj)
                self.server.db.commit()
            else:
                with self.savepath.open(mode='wb') as savefile:
                    self.data.toXml(savefile, unresolved=True, autocreate=True)
        self.changes = False

    @locked_threadpool
    def load(self):
        """Carica i dati da file XML o database (eseguito nel threadpool con lock)."""
        if self.db_save_kw:
            tblobj = self.server.db.table(self.db_save_kw['table'])
            handler = getattr(tblobj, 'loadSharedObject', None)
            if handler:
                data = handler(self.shared_id)
            else:
                data = self._sql_load(tblobj)
        elif self.savepath.exists:
            with self.savepath.open(mode='r') as savefile:
                data = Bag(savefile)
        else:
            data = Bag()
        self._data['root'] = data
        self.changes = False

    def _sql_save(self, tblobj):
        """Salva i dati nella tabella DB con supporto backup versioning."""
        backup = self.db_save_kw.get('backup')
        data_column = self.sql_data_column
        with tblobj.recordToUpdate(self.shared_id) as record:
            if not self.data:
                logger.error('NO DATA IN SAVING: %s', self.shared_id)
            record[data_column] = deepcopy(self.data)
            on_saving_handler = getattr(tblobj, 'shared_onSaving', None)
            if on_saving_handler:
                on_saving_handler(record)
            if backup:
                backup_column = self.sql_backup_column
                if not record[backup_column]:
                    record[backup_column] = Bag()
                    n = 0
                else:
                    n = int(list(record[backup_column].keys())[-1].split('_')[1]) + 1
                record[backup_column].setItem(
                    'v_%s' % n, record[data_column], ts=datetime.now()
                )
                if len(record[backup_column]) > backup:
                    record[backup_column].popNode('#0')

    def _sql_load(self, tblobj, version=None):
        """Carica i dati dalla tabella DB, opzionalmente una versione specifica."""
        record = tblobj.record(self.shared_id).output('bag')
        on_loading_handler = getattr(tblobj, 'shared_onLoading', None)
        if on_loading_handler:
            on_loading_handler(record)
        if not version:
            return record[self.sql_data_column]
        return record[self.sql_backup_column].getItem('v_%i' % version)

    def on_init(self, **kwargs):
        """Hook chiamato dopo l'inizializzazione. Carica i dati se autoLoad è attivo."""
        if self.auto_load:
            self.load()

    def on_subscribe_page(self, page_id):
        """Hook chiamato quando una pagina si sottoscrive."""
        pass

    def on_unsubscribe_page(self, page_id):
        """Hook chiamato quando una pagina annulla la sottoscrizione."""
        pass

    def on_destroy(self):
        """Hook chiamato alla distruzione dell'oggetto. Salva se autoSave è attivo."""
        logger.debug('onDestroy %s', self.shared_id)
        if self.auto_save:
            self.save()

    def on_shutdown(self):
        """Chiamato allo shutdown del server. Salva se autoSave è attivo."""
        if self.auto_save:
            self.save()

    def subscribe(self, page_id=None, **kwargs):
        """Sottoscrive una pagina a questo shared object.

        Verifica i permessi e registra la pagina. Restituisce i dati
        correnti e il livello di privilegio.

        Returns:
            dict con 'privilege' ('readwrite'|'readonly') e 'data',
            oppure None se non autorizzato.
        """
        page = self.server.pages[page_id]
        privilege = self._check_permission(page)
        if privilege:
            page.sharedObjects.add(self.shared_id)
            sub_kwargs = dict(kwargs)
            sub_kwargs['page_id'] = page_id
            sub_kwargs['user'] = page.user
            self.subscribed_pages[page_id] = sub_kwargs
            self.server.shared_status.sharedObjectSubscriptionAddPage(
                self.shared_id, page_id, sub_kwargs
            )
            self.on_subscribe_page(page)
            return dict(privilege=privilege, data=self.data)
        return None

    def unsubscribe(self, page_id=None):
        """Annulla la sottoscrizione di una pagina.

        Se non restano pagine sottoscritte, schedula la distruzione
        dell'oggetto dopo il tempo di expire.
        """
        self.subscribed_pages.pop(page_id, None)
        self.server.shared_status.sharedObjectSubscriptionRemovePage(
            self.shared_id, page_id
        )
        self.on_unsubscribe_page(page_id)
        if not self.subscribed_pages:
            self.timeout = self.server.delayed_call(
                self.expire, self.manager.remove_shared_object, self
            )

    def _check_permission(self, page):
        """Verifica i permessi di accesso per una pagina.

        Returns:
            'readwrite', 'readonly', o None se non autorizzato.
        """
        privilege = 'readwrite'
        if self.read_tags and not self.server.gnrapp.checkResourcePermission(
            self.read_tags, page.userTags
        ):
            privilege = None
        elif self.write_tags and not self.server.gnrapp.checkResourcePermission(
            self.write_tags, page.userTags
        ):
            privilege = 'readonly'
        return privilege

    @locked_coroutine
    async def datachange(self, page_id=None, path=None, value=None,
                         attr=None, evt=None, fired=None, **kwargs):
        """Applica una modifica ai dati condivisi.

        Se ``fired`` è True, propaga il messaggio senza modificare i dati
        (usato per eventi/segnali). Altrimenti modifica il Bag interno,
        che a sua volta triggera _on_data_trigger per il broadcast.
        """
        if fired:
            data = Bag(dict(
                value=value, attr=attr, path=path,
                shared_id=self.shared_id, evt=evt, fired=fired
            ))
            self.broadcast(
                command='som.sharedObjectChange', data=data,
                from_page_id=page_id
            )
        else:
            path = 'root' if not path else 'root.%s' % path
            if evt == 'del':
                self._data.popNode(path, _reason=page_id)
            else:
                self._data.setItem(path, value, _attributes=attr,
                                   _reason=page_id)

    def _on_data_trigger(self, node=None, ind=None, evt=None,
                         pathlist=None, reason=None, **kwargs):
        """Callback triggerato da Bag.subscribe quando i dati cambiano.

        Costruisce l'envelope di notifica e lo invia in broadcast a tutte
        le pagine sottoscritte (esclusa quella che ha originato la modifica).
        """
        self.changes = True
        if reason == 'autocreate':
            return
        plist = pathlist[1:]
        if evt == 'ins' or evt == 'del':
            plist = plist + [node.label]
        path = '.'.join(plist)
        data = Bag(dict(
            value=node.value, attr=node.attr, path=path,
            shared_id=self.shared_id, evt=evt
        ))
        from_page_id = reason
        self.broadcast(
            command='som.sharedObjectChange', data=data,
            from_page_id=from_page_id
        )

    def on_path_focus(self, page_id=None, curr_path=None, focused=None):
        """Gestisce il focus/lock su un percorso dell'oggetto condiviso.

        Usato per mostrare agli altri utenti quale campo sta editando
        un utente (locking visuale collaborativo).
        """
        if focused:
            self.focused_paths[curr_path] = page_id
        else:
            self.focused_paths.pop(curr_path, None)
        self.broadcast(
            command='som.onPathLock', from_page_id=page_id,
            data=Bag(dict(locked=focused, lock_path=curr_path))
        )

    def broadcast(self, command=None, data=None, from_page_id=None):
        """Invia un messaggio a tutte le pagine sottoscritte.

        Esclude la pagina che ha originato la modifica (from_page_id).
        """
        envelope = Bag(dict(command=command, data=data)).toXml()
        channels = self.server.channels
        for p in list(self.subscribed_pages.keys()):
            if p != from_page_id:
                channel = channels.get(p)
                if channel:
                    channel.write_message(envelope)


class SqlSharedObject(SharedObject):
    """SharedObject specializzato per persistenza su database SQL.

    Attualmente identico a SharedObject (la persistenza SQL è gestita
    dalla classe base tramite dbSaveKw).
    """
    pass


class SharedLogger(SharedObject):
    """SharedObject specializzato per il logging condiviso."""

    def on_init(self, **kwargs):
        logger.debug('onInit %s', self.shared_id)

    def on_subscribe_page(self, page_id):
        logger.debug('onSubscribePage %s %s', self.shared_id, page_id)

    def on_unsubscribe_page(self, page_id):
        logger.debug('onUnsubscribePage %s %s', self.shared_id, page_id)

    def on_destroy(self):
        logger.debug('onDestroy %s', self.shared_id)


class SharedStatus(SharedObject):
    """Shared object globale che traccia lo stato del server.

    Contiene informazioni su utenti connessi, loro connessioni,
    pagine aperte ed eventi utente. Accessibile dalla dashboard
    di amministrazione (__global_status__).
    """

    def on_init(self, **kwargs):
        self.data['users'] = Bag()
        self.data['sharedObjects'] = Bag()

    @property
    def users(self):
        """Bag con gli utenti connessi."""
        return self.data['users']

    @property
    def shared_objects_data(self):
        """Bag con i metadati degli shared objects attivi."""
        return self.data['sharedObjects']

    def register_page(self, page):
        """Registra una pagina nello stato globale.

        Organizza i dati gerarchicamente: utente → connessione → pagina.
        """
        page_item = page.page_item
        users = self.users
        page_id = page.page_id
        if page.user not in users:
            users[page.user] = Bag(dict(
                start_ts=page_item['start_ts'],
                user=page.user, connections=Bag()
            ))
        userbag = users[page.user]
        connection_id = page.connection_id
        if connection_id not in userbag['connections']:
            userbag['connections'][connection_id] = Bag(dict(
                start_ts=page_item['start_ts'],
                user_ip=page_item['user_ip'],
                user_agent=page_item['user_agent'],
                connection_id=connection_id,
                pages=Bag()
            ))
        userbag['connections'][connection_id]['pages'][page_id] = Bag(dict(
            pagename=page_item['pagename'],
            relative_url=page_item['relative_url'],
            start_ts=page_item['start_ts'],
            page_id=page_id
        ))

    def unregister_page(self, page):
        """Rimuove una pagina dallo stato globale.

        Rimuove anche la connessione e l'utente se non hanno più pagine.
        """
        users = self.users
        userbag = users[page.user]
        connection_id = page.connection_id
        user_connections = userbag['connections']
        connection_pages = user_connections[connection_id]['pages']
        connection_pages.popNode(page.page_id)
        if not connection_pages:
            user_connections.popNode(connection_id)
            if not user_connections:
                users.popNode(page.user)

    def onPing(self, page_id, lastEventAge):
        """Aggiorna il timestamp dell'ultimo evento per la pagina."""
        page = self.server.pages.get(page_id)
        if page:
            userdata = self.users[page.user]
            conndata = userdata['connections'][page.connection_id]
            pagedata = conndata['pages'][page_id]
            pagedata['lastEventAge'] = lastEventAge
            conndata['lastEventAge'] = min(
                conndata['pages'].digest('#v.lastEventAge'),
                key=lambda i: i or 0
            )
            userdata['lastEventAge'] = min(
                userdata['connections'].digest('#v.lastEventAge'),
                key=lambda i: i or 0
            )

    def onUserEvent(self, page_id, event):
        """Registra un evento utente (movimento, typing, ecc.)."""
        page = self.server.pages.get(page_id)
        if page:
            pagedata = self.users[page.user]['connections'][page.connection_id]['pages'][page_id]
            old_target_id = pagedata['evt_targetId']
            for k, v in list(event.items()):
                pagedata['evt_%s' % k] = v
            if old_target_id == event['targetId']:
                if event['type'] == 'keypress':
                    pagedata['typing'] = True
            else:
                pagedata['typing'] = False

    def registerSharedObject(self, shared_id, sharingkw):
        """Registra un nuovo shared object nei metadati globali."""
        self.shared_objects_data[shared_id] = Bag(sharingkw)

    def unregisterSharedObject(self, shared_id):
        """Rimuove un shared object dai metadati globali."""
        self.shared_objects_data.pop(shared_id)

    def sharedObjectSubscriptionAddPage(self, shared_id, page_id, subkwargs):
        """Registra una sottoscrizione pagina nei metadati globali."""
        self.shared_objects_data[shared_id]['subscriptions'][page_id] = Bag(subkwargs)

    def sharedObjectSubscriptionRemovePage(self, shared_id, page_id):
        """Rimuove una sottoscrizione pagina dai metadati globali."""
        self.shared_objects_data[shared_id]['subscriptions'].pop(page_id, None)


# ---------------------------------------------------------------------------
# SharedObjectsManager
# ---------------------------------------------------------------------------

class SharedObjectsManager:
    """Gestisce il ciclo di vita degli SharedObject.

    Responsabile di creare, recuperare e distruggere gli shared objects.
    Espone metodi ``do_*`` invocabili dal WebSocket handler tramite
    il namespace 'som' (es. comando 'som.subscribe').
    """

    def __init__(self, server, gc_interval=5):
        self.server = server
        self.shared_objects = {}
        self.change_queue = asyncio.Queue(maxsize=100)

    def get_shared_object(self, shared_id, expire=None, startData=None,
                          read_tags=None, write_tags=None,
                          factory=SharedObject, **kwargs):
        """Restituisce uno shared object esistente o ne crea uno nuovo.

        Args:
            shared_id: identificativo univoco.
            expire: secondi prima della distruzione dopo l'ultima disconnessione.
            startData: dati iniziali.
            read_tags: tag di lettura.
            write_tags: tag di scrittura.
            factory: classe da istanziare (default SharedObject).

        Returns:
            l'istanza SharedObject.
        """
        if shared_id not in self.shared_objects:
            self.shared_objects[shared_id] = factory(
                self, shared_id=shared_id, expire=expire,
                startData=startData, read_tags=read_tags,
                write_tags=write_tags, **kwargs
            )
            sharing_kw = dict(kwargs)
            sharing_kw.update(dict(
                shared_id=shared_id, expire=expire,
                read_tags=read_tags, write_tags=write_tags,
                subscriptions=Bag()
            ))
            self.server.shared_status.registerSharedObject(
                shared_id, sharing_kw
            )
        return self.shared_objects[shared_id]

    def remove_shared_object(self, so):
        """Distrugge uno shared object se on_destroy non lo impedisce."""
        if so.on_destroy() is not False:
            self.shared_objects.pop(so.shared_id, None)
            self.server.shared_status.unregisterSharedObject(so.shared_id)

    def do_unsubscribe(self, shared_id=None, page_id=None, **kwargs):
        """Annulla la sottoscrizione di una pagina a uno shared object."""
        shared_object = self.shared_objects.get(shared_id)
        if shared_object:
            shared_object.unsubscribe(page_id=page_id)

    def do_subscribe(self, shared_id=None, page_id=None, **kwargs):
        """Sottoscrive una pagina a uno shared object.

        Crea l'oggetto se non esiste. Cancella il timeout di distruzione
        se era in corso. Restituisce l'envelope con i dati iniziali.
        """
        shared_object = self.get_shared_object(shared_id, **kwargs)
        subscription = shared_object.subscribe(page_id)
        if not subscription:
            subscription = dict(privilege='forbidden', data=Bag())
        elif shared_object.timeout:
            shared_object.timeout.cancel()
            shared_object.timeout = None

        data = Bag(dict(
            value=subscription['data'], shared_id=shared_id,
            evt='init', privilege=subscription['privilege']
        ))
        envelope = Bag(dict(command='som.sharedObjectChange', data=data))
        return envelope

    def do_datachange(self, shared_id=None, **kwargs):
        """Applica una modifica ai dati di uno shared object."""
        if shared_id in self.shared_objects:
            self.shared_objects[shared_id].datachange(**kwargs)

    def do_saveSharedObject(self, shared_id=None, **kwargs):
        """Salva uno shared object su disco/DB."""
        self.shared_objects[shared_id].save()

    def do_loadSharedObject(self, shared_id=None, **kwargs):
        """Carica uno shared object da disco/DB."""
        self.get_shared_object(shared_id).load()

    def do_dispatch(self, shared_id=None, so_method=None, so_pars=None, **kwargs):
        """Invoca un metodo arbitrario su uno shared object."""
        so = self.get_shared_object(shared_id)
        pars = so_pars or {}
        return getattr(so, so_method)(**pars)

    def on_shutdown(self):
        """Chiamato allo shutdown del server. Salva tutti gli shared objects."""
        for so in list(self.shared_objects.values()):
            so.on_shutdown()

    def do_onPathFocus(self, shared_id=None, page_id=None,
                       curr_path=None, focused=None, **kwargs):
        """Gestisce il focus/lock su un percorso di uno shared object."""
        self.shared_objects[shared_id].on_path_focus(
            page_id=page_id, curr_path=curr_path, focused=focused
        )


# ---------------------------------------------------------------------------
# DelayedCall
# ---------------------------------------------------------------------------

class DelayedCall:
    """Wrapper per chiamate ritardate nell'event loop asyncio.

    Equivalente di tornado.ioloop.IOLoop.call_later, con supporto
    per la cancellazione.
    """

    def __init__(self, loop, delay, cb, *args, **kwargs):
        if kwargs:
            self._handle = loop.call_later(
                delay, lambda: cb(*args, **kwargs)
            )
        else:
            self._handle = loop.call_later(delay, cb, *args)

    def cancel(self):
        """Cancella la chiamata ritardata."""
        self._handle.cancel()


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class GnrBaseAsyncServer:
    """Server asincrono base per Genro.

    Gestisce l'infrastruttura comune: inizializzazione del sito Genro,
    registrazione pagine, shared objects, canali WebSocket, signal handling
    e shutdown graceful.

    Args:
        port: porta TCP per connessioni HTTP/WebSocket (opzionale).
        instance: nome dell'istanza Genro.
        ssl_crt: percorso certificato SSL (opzionale).
        ssl_key: percorso chiave privata SSL (opzionale).
    """

    def __init__(self, port=None, instance=None, ssl_crt=None, ssl_key=None):
        self.port = port
        self.executors = {}
        self.channels = {}
        self.remote_services = {}
        self.pages = {}
        self.debug_queues = {}
        self.gnrsite = GnrWsgiSite(instance)
        self.instance_name = self.gnrsite.site_name
        self.gnrsite.ws_site = self
        self.gnrapp = self.gnrsite.gnrapp
        self.db = self.gnrapp.db
        self.ssl_key = ssl_key
        self.ssl_crt = ssl_crt
        self.wsk = AsyncWebSocketHandler(self)
        self.som = SharedObjectsManager(self)
        self.app = web.Application()
        self.app['server'] = self
        self._loop = None

    def _setup_routes(self):
        """Configura le route HTTP/WebSocket nell'applicazione aiohttp.

        Da sovrascrivere nelle sottoclassi per aggiungere route specifiche.
        """
        pass

    def delayed_call(self, delay, cb, *args, **kwargs):
        """Schedula una chiamata ritardata nell'event loop.

        Returns:
            un DelayedCall cancellabile.
        """
        return DelayedCall(self._loop, delay, cb, *args, **kwargs)

    def scheduler(self, *args, **kwargs):
        """Placeholder per lo scheduler periodico."""
        logger.info('Scheduler args %s kw %s', args, kwargs)

    def external_command(self, command, data):
        """Esegue un comando esterno ricevuto dal proxy HTTP.

        I comandi sono mappati a metodi do_* del server.
        """
        handler = getattr(self, 'do_%s' % command)
        handler(**data.asDict(ascii=True))

    def do_registerNewPage(self, page_id=None, page_info=None,
                           class_info=None, init_info=None,
                           mixin_set=None):
        """Registra una nuova pagina creandola dal class_info."""
        if not class_info:
            return
        page = self.gnrsite.resource_loader.instantiate_page(
            page_id=page_id, class_info=class_info,
            init_info=init_info, page_info=page_info
        )
        self.register_page(page)

    def register_page(self, page=None, page_id=None):
        """Registra una pagina nel server.

        Se viene passato solo page_id, tenta di recuperare la pagina
        dal resource_loader.
        """
        if not page:
            page = self.gnrsite.resource_loader.get_page_by_id(page_id)
            if not page:
                logger.warning(
                    'page %s not existing in gnrdaemon register', page_id
                )
                return
            logger.info(
                'page %s restored succesfully from gnrdaemon register',
                page_id
            )
        page.asyncServer = self
        page.sharedObjects = set()
        self.pages[page.page_id] = page
        self.shared_status.register_page(page)

    def unregister_page(self, page_id):
        """Rimuove una pagina dal server.

        Annulla tutte le sottoscrizioni agli shared objects della pagina.
        """
        page = self.pages.get(page_id)
        if not page:
            return
        if page.sharedObjects:
            for shared_id in page.sharedObjects:
                self.som.shared_objects[shared_id].unsubscribe(page_id)
        self.shared_status.unregister_page(page)
        self.pages.pop(page_id, None)

    @property
    def shared_status(self):
        """Lo SharedStatus globale (__global_status__).

        Traccia utenti connessi, connessioni e pagine. Accessibile dalla
        dashboard di amministrazione.
        """
        return self.som.get_shared_object(
            '__global_status__', expire=-1,
            read_tags='_DEV_,superadmin',
            write_tags='__SYSTEM__',
            factory=SharedStatus
        )

    @property
    def error_status(self):
        """Lo SharedLogger per gli errori (__error_status__)."""
        return self.som.get_shared_object(
            '__error_status__', expire=-1,
            startData=dict(users=Bag()),
            read_tags='_DEV_,superadmin',
            write_tags='__SYSTEM__',
            factory=SharedLogger
        )

    async def _start_async(self):
        """Avvia il server asincrono: HTTP, Unix socket e debug server."""
        self._setup_routes()

        # SSL
        ssl_context = None
        if self.ssl_crt and self.ssl_key:
            import ssl as ssl_mod
            ssl_context = ssl_mod.create_default_context(
                ssl_mod.Purpose.CLIENT_AUTH
            )
            ssl_context.load_cert_chain(self.ssl_crt, self.ssl_key)

        runner = web.AppRunner(self.app)
        await runner.setup()

        # Ascolta sulla porta TCP (se specificata)
        if self.port:
            site = web.TCPSite(runner, port=int(self.port),
                               ssl_context=ssl_context)
            await site.start()

        # Socket Unix per comunicazione con il server WSGI
        sockets_dir = os.path.join(self.gnrsite.site_path, 'sockets')
        if len(sockets_dir) > 90:
            sockets_dir = os.path.join(
                '/tmp', os.path.basename(self.gnrsite.instance_path),
                'gnr_sock'
            )
        if not os.path.exists(sockets_dir):
            os.makedirs(sockets_dir)
        socket_path = os.path.join(sockets_dir, 'async.aiohttp')
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        unix_site = web.UnixSite(runner, socket_path,
                                 ssl_context=ssl_context)
        await unix_site.start()
        os.chmod(socket_path, 0o666)

        # Debug server su Unix socket
        debug_socket_path = os.path.join(sockets_dir, 'debugger.sock')
        if os.path.exists(debug_socket_path):
            os.unlink(debug_socket_path)
        await asyncio.start_unix_server(
            lambda r, w: _debug_client_handler(r, w, self),
            path=debug_socket_path
        )

    def start(self):
        """Avvia il server (bloccante).

        Configura l'event loop, registra i signal handler per shutdown
        graceful e avvia il server.
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._loop.run_until_complete(self._start_async())

        # Signal handler per shutdown graceful
        for sig in (signal.SIGTERM, signal.SIGINT):
            self._loop.add_signal_handler(
                sig, lambda: asyncio.ensure_future(self._on_shutdown())
            )

        logger.info(
            'GnrAsyncServer started - instance: %s, port: %s',
            self.instance_name, self.port
        )
        self._loop.run_forever()

    async def _on_shutdown(self):
        """Esegue lo shutdown graceful del server.

        Salva gli shared objects e ferma l'event loop dopo un timeout.
        """
        self.som.on_shutdown()
        await asyncio.sleep(MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
        self._loop.stop()

    def log_to_page(self, page_id, **kwargs):
        """Invia un messaggio di log a una pagina specifica."""
        self.pages[page_id].log(**kwargs)


class GnrAsyncServer(GnrBaseAsyncServer):
    """Server asincrono Genro completo.

    Estende GnrBaseAsyncServer aggiungendo:
    - ThreadPoolExecutor per operazioni bloccanti
    - Route WebSocket e proxy HTTP
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executors['threadpool'] = ThreadPoolExecutor(max_workers=20)

    def _setup_routes(self):
        """Registra le route per WebSocket e proxy HTTP."""
        self.app.router.add_get('/websocket', websocket_handler)
        self.app.router.add_post('/wsproxy', ws_proxy_handler)


if __name__ == '__main__':
    server = GnrAsyncServer(port=8888, instance='sandbox')
    server.start()
