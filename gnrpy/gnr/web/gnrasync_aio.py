# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrasync_aio : asyncio/aiohttp port of gnrasync.py (legacy Tornado)
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

import asyncio
import functools
import inspect
import os
import signal
import ssl as ssl_module
import time
from concurrent.futures import ThreadPoolExecutor

from aiohttp import WSMsgType, web

from gnr.core.gnrbag import Bag, TraceBackResolver
from gnr.core.gnrstring import fromJson
from gnr.web import logger
from gnr.web.gnrwsgisite import GnrWsgiSite

MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3


def threadpool(func):
    """Marker decorator: handler runs in the threadpool executor."""
    func._executor = 'threadpool'
    return func


class DelayedCall:
    """Replacement for the Tornado-based DelayedCall.

    Uses asyncio.get_running_loop().call_later, which returns a TimerHandle
    with .cancel() — no need to keep a separate remove_timeout call.
    """

    def __init__(self, server, delay, cb, *args, **kwargs):
        loop = asyncio.get_running_loop()
        self.server = server
        self.handle = loop.call_later(delay, functools.partial(cb, *args, **kwargs))

    def cancel(self):
        self.handle.cancel()


class GnrWebSocketSession:
    """Per-connection state for an aiohttp WebSocket.

    Replaces the legacy GnrWebSocketHandler (Tornado WebSocketHandler subclass).
    The handler function ``websocket_handler`` instantiates one of these per
    incoming connection and dispatches messages here.

    Methods are kept compatible with the legacy ``do_*`` convention so that
    SharedObjectsManager and any external proxy keep their dispatch contract.
    """

    def __init__(self, server, ws):
        self.server = server
        self.ws = ws
        self._page_id = None

    # ---- properties mirroring legacy GnrBaseHandler --------------------
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
    def page_id(self):
        return self._page_id

    @page_id.setter
    def page_id(self, value):
        self._page_id = value

    @property
    def gnrsite(self):
        return self.server.gnrsite

    @property
    def debug_queues(self):
        return self.server.debug_queues

    # ---- writer used by SharedObject.broadcast and DebugSession --------
    async def write_message(self, msg):
        """Async writer used by code paths that already run in the loop.

        Mirrors the legacy ``write_message`` name. Coroutine-only: callers
        from other coroutines must ``await`` it. There are no remaining
        sync callers after the migration.
        """
        if not self.ws.closed:
            await self.ws.send_str(msg)

    # ---- dispatch ------------------------------------------------------
    def parseMessage(self, message):
        kwargs = fromJson(message)
        catalog = self.server.gnrapp.catalog
        result = dict()
        for k, v in list(kwargs.items()):
            k = k.strip()
            if isinstance(v, (bytes, str)):
                try:
                    v = catalog.fromTypedText(v)
                    result[k] = v
                except Exception:
                    raise
            else:
                result[k] = v
        command = result.pop('command')
        result_token = result.pop('result_token', None)
        return command, result_token, result

    def getHandler(self, command, kwargs):
        if '.' not in command:
            return getattr(self, 'do_%s' % command, self.wrongCommand)
        kwargs['page_id'] = self.page_id
        proxy = self.server
        while '.' in command:
            proxyname, command = command.split('.', 1)
            proxy = getattr(proxy, proxyname, None)
        if proxy is None:
            return self.wrongCommand
        return getattr(proxy, 'do_%s' % command, self.wrongCommand)

    def getExecutor(self, method):
        executor = getattr(method, '_executor', None)
        if executor:
            return self.server.executors.get(executor)

    async def on_message(self, message):
        command, result_token, kwargs = self.parseMessage(message)
        handler = self.getHandler(command, kwargs)
        if handler is None:
            return
        if getattr(handler, '_executor', None) == 'threadpool':
            loop = asyncio.get_running_loop()
            executor = self.server.executors['threadpool']
            result = await loop.run_in_executor(
                executor,
                functools.partial(handler, _time_start=time.time(), **kwargs),
            )
        else:
            result = handler(_time_start=time.time(), **kwargs)
            if inspect.isawaitable(result):
                result = await result
        if result_token:
            result = Bag(dict(token=result_token, envelope=result)).toXml(unresolved=True)
        if result is not None:
            await self.write_message(result)

    def on_close(self):
        self.channels.pop(self.page_id, None)
        self.server.unregisterPage(page_id=self.page_id)

    # ---- do_* command handlers (parity with legacy) --------------------
    def wrongCommand(self, command=None, **kwargs):
        return 'WRONG COMMAND: %s' % command

    def do_echo(self, data=None, **kwargs):
        return data

    async def do_ping(self, lastEventAge=None, **kwargs):
        # SharedStatus is set up in Phase 4. Until then, skip the ping
        # bookkeeping but always emit pong so the client heartbeat works.
        som = getattr(self.server, 'som', None)
        if som is not None and self._page_id is not None:
            shared_status = self.server.sharedStatus
            shared_status.onPing(self._page_id, lastEventAge)
        await self.write_message('pong')

    def do_user_event(self, event=None, **kwargs):
        som = getattr(self.server, 'som', None)
        if som is not None:
            self.server.sharedStatus.onUserEvent(self._page_id, event)

    async def do_route(self, target_page_id=None, envelope=None, **kwargs):
        target = self.channels.get(target_page_id)
        if target is not None:
            await target.write_message(envelope)

    def do_register_service(self, page_id=None, gateway_service=None, **kwargs):
        if gateway_service:
            self.remote_services[gateway_service] = page_id
        self.do_connected(page_id=page_id, **kwargs)

    @threadpool
    def do_service(self, gateway_service=None, **kwargs):
        service = self.gnrsite.getService(
            service_type='remotewsservice', service_name=gateway_service,
        )
        if service and hasattr(service, 'on_message'):
            service.on_message(**kwargs)

    def do_connected(self, page_id=None, **kwargs):
        self._page_id = page_id
        if page_id not in self.channels:
            self.channels[page_id] = self
        if page_id not in self.pages:
            self.server.registerPage(page_id=page_id)

    def do_pdb_command(self, cmd=None, pdb_id=None, **kwargs):
        debugkey = '%s,%s' % (self.page_id, pdb_id)
        queue = self.debug_queues.get(debugkey)
        if queue is None:
            queue = asyncio.Queue(maxsize=40)
            self.debug_queues[debugkey] = queue
        queue.put_nowait(cmd)

    @threadpool
    def do_call(self, method=None, _time_start=None, **kwargs):
        error = None
        result = None
        resultAttrs = None
        # Legacy code resets page._db once before calling getWsMethod twice;
        # the double getWsMethod is not load-bearing — keep one call.
        self.page._db = None
        handler = self.page.getWsMethod(method)
        if handler:
            try:
                result = handler(**kwargs)
                if isinstance(result, tuple):
                    result, resultAttrs = result
            except Exception as e:
                result = TraceBackResolver()()
                error = str(e)
        envelope = Bag()
        envelope.setItem(
            'data', result,
            _attributes=resultAttrs, _server_time=time.time() - _time_start,
        )
        if error:
            envelope.setItem('error', error)
        return envelope


async def websocket_handler(request):
    """aiohttp request handler for /websocket.

    Replaces tornado.websocket.WebSocketHandler subclass dispatch with the
    async-iteration pattern recommended by aiohttp.
    """
    server = request.app['server']
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    session = GnrWebSocketSession(server, ws)
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    await session.on_message(msg.data)
                except Exception:
                    logger.exception('error handling websocket message')
            elif msg.type == WSMsgType.ERROR:
                logger.warning('websocket connection closed with exception %s',
                               ws.exception())
                break
    finally:
        session.on_close()
    return ws


class GnrBaseAsyncServer:
    """Async server based on aiohttp + asyncio.

    Mirrors the public surface of the legacy GnrBaseAsyncServer
    (gnrasync.py): same constructor signature, same attributes
    (channels, pages, remote_services, executors, gnrsite, gnrapp, db,
    site_options) and the same start() entry point.
    """

    def __init__(self, port=None, instance=None, ssl_crt=None, ssl_key=None,
                 autoreload=None, site_options=None):
        self.port = port
        self.handlers = []
        self.executors = dict()
        self.channels = dict()
        self.remote_services = dict()
        self.pages = dict()
        self.debug_queues = dict()
        self.gnrsite = GnrWsgiSite(instance)
        self.instance_name = self.gnrsite.site_name
        self.gnrsite.ws_site = self
        self.gnrapp = self.gnrsite.gnrapp
        self.db = self.gnrapp.db
        self.ssl_key = ssl_key
        self.ssl_crt = ssl_crt
        self.site_options = site_options or dict()
        self.autoreload = autoreload  # accepted for CLI compat
        # The server-side wsk and som are populated by Phase 4; placeholders
        # let do_ping / do_user_event run cleanly until then.
        self.wsk = None
        self.som = None
        self.app = None
        self.runner = None
        self._shutdown_event = None

    # ---- API used by external callers (kept identical to legacy) ----
    def delayedCall(self, delay, cb, *args, **kwargs):
        return DelayedCall(self, delay, cb, *args, **kwargs)

    def addHandler(self, path, handler, options=None):
        if options:
            self.handlers.append((path, handler, options))
        else:
            self.handlers.append((path, handler))

    def addExecutor(self, name, executor):
        self.executors[name] = executor

    def externalCommand(self, command, data):
        handler = getattr(self, 'do_%s' % command)
        handler(**data.asDict(ascii=True))

    def do_registerNewPage(self, page_id=None, page_info=None, class_info=None,
                           init_info=None, mixin_set=None):
        if not class_info:
            return
        page = self.gnrsite.resource_loader.instantiate_page(
            page_id=page_id, class_info=class_info,
            init_info=init_info, page_info=page_info,
        )
        self.registerPage(page)

    def registerPage(self, page=None, page_id=None):
        if not page:
            page = self.gnrsite.resource_loader.get_page_by_id(page_id)
            if not page:
                logger.warning('page %s not existing in gnrdaemon register', page_id)
                return
            logger.info('page %s restored successfully from gnrdaemon register', page_id)
        page.asyncServer = self
        page.sharedObjects = set()
        self.pages[page.page_id] = page
        if self.som is not None:
            self.sharedStatus.registerPage(page)

    def unregisterPage(self, page_id):
        page = self.pages.get(page_id)
        if not page:
            return
        if self.som is not None and page.sharedObjects:
            for shared_id in page.sharedObjects:
                self.som.sharedObjects[shared_id].unsubscribe(page_id)
        if self.som is not None:
            self.sharedStatus.unregisterPage(page)
        self.pages.pop(page_id, None)

    @property
    def sharedStatus(self):
        # Lazily resolved by SharedObjectsManager (Phase 4).
        return self.som.getSharedObject(
            '__global_status__', expire=-1,
            read_tags='_DEV_,superadmin', write_tags='__SYSTEM__',
            # SharedStatus class will be wired in Phase 4
            factory=getattr(self, '_SharedStatusFactory', None),
        )

    @property
    def errorStatus(self):
        return self.som.getSharedObject(
            '__error_status__', expire=-1, startData=dict(users=Bag()),
            read_tags='_DEV_,superadmin', write_tags='__SYSTEM__',
            factory=getattr(self, '_SharedLoggerFactory', None),
        )

    def logToPage(self, page_id, **kwargs):
        self.pages[page_id].log(**kwargs)

    # ---- aiohttp wiring -----------------------------------------------
    def _build_app(self):
        app = web.Application()
        app['server'] = self
        app.router.add_get('/websocket', websocket_handler)
        # Phase 5 will register POST /wsproxy here.
        return app

    def _build_ssl_context(self):
        if not (self.ssl_crt and self.ssl_key):
            return None
        ctx = ssl_module.create_default_context(ssl_module.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(self.ssl_crt, self.ssl_key)
        return ctx

    def _ensure_sockets_dir(self):
        sockets_dir = os.path.join(self.gnrsite.site_path, 'sockets')
        if len(sockets_dir) > 90:
            sockets_dir = os.path.join(
                '/tmp',
                os.path.basename(self.gnrsite.instance_path),
                'gnr_sock',
            )
        if not os.path.exists(sockets_dir):
            os.makedirs(sockets_dir)
        return sockets_dir

    async def _run(self):
        self.app = self._build_app()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        sockets_dir = self._ensure_sockets_dir()
        socket_path = os.path.join(sockets_dir, 'async.sock')
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        unix_site = web.UnixSite(self.runner, socket_path)
        await unix_site.start()
        os.chmod(socket_path, 0o666)
        logger.info('aiohttp server bound to unix socket %s', socket_path)

        if self.port:
            tcp_site = web.TCPSite(
                self.runner,
                host='0.0.0.0',
                port=int(self.port),
                ssl_context=self._build_ssl_context(),
            )
            await tcp_site.start()
            logger.info('aiohttp server listening on TCP port %s', self.port)

        # Phase 6 wires the debugger TCP server here.

        self._shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._on_signal)
        await self._shutdown_event.wait()
        await self._cleanup()

    def _on_signal(self):
        if self._shutdown_event and not self._shutdown_event.is_set():
            self._shutdown_event.set()

    async def _cleanup(self):
        try:
            await asyncio.wait_for(
                self.runner.cleanup(),
                timeout=MAX_WAIT_SECONDS_BEFORE_SHUTDOWN,
            )
        except asyncio.TimeoutError:
            logger.warning('shutdown timeout exceeded')

    def start(self):
        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            pass


class GnrAsyncServer(GnrBaseAsyncServer):
    """Concrete server with the threadpool executor and websocket route."""

    def __init__(self, *args, **kwargs):
        # Drop the legacy `web=True` kwarg (Phase 7); kept silent for compat
        # so existing callers (serverwsgi.py and CLI) need no churn yet.
        kwargs.pop('web', None)
        super().__init__(*args, **kwargs)
        self.addExecutor('threadpool', ThreadPoolExecutor(max_workers=20))


if __name__ == '__main__':
    server = GnrAsyncServer(port=8888, instance='sandbox')
    server.start()
