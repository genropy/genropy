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
import os
import signal
import ssl as ssl_module
from concurrent.futures import ThreadPoolExecutor

from aiohttp import web

from gnr.web import logger
from gnr.web.gnrwsgisite import GnrWsgiSite

MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3


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


class GnrBaseAsyncServer:
    """Async server skeleton based on aiohttp + asyncio.

    Phase 2: skeleton only. WebSocket / WsProxy / Debugger handlers
    are added in subsequent phases.
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
        self.autoreload = autoreload  # accepted for CLI compat; aiohttp has no built-in equivalent
        self.app = None
        self.runner = None
        self._shutdown_event = None

    def delayedCall(self, delay, cb, *args, **kwargs):
        return DelayedCall(self, delay, cb, *args, **kwargs)

    def addHandler(self, path, handler, options=None):
        # aiohttp routes are added before AppRunner.setup(); options carried for compat
        if options:
            self.handlers.append((path, handler, options))
        else:
            self.handlers.append((path, handler))

    def addExecutor(self, name, executor):
        self.executors[name] = executor

    def externalCommand(self, command, data):
        handler = getattr(self, 'do_%s' % command)
        handler(**data.asDict(ascii=True))

    def _build_app(self):
        """Build aiohttp Application and register routes from self.handlers.

        Subclasses populate self.handlers in __init__ before start().
        """
        app = web.Application()
        app['server'] = self
        # Phase 3+ will register actual websocket / wsproxy / debugger handlers here
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

        # Remove stale socket file if present (aiohttp UnixSite does not unlink)
        if os.path.exists(socket_path):
            os.unlink(socket_path)

        unix_site = web.UnixSite(self.runner, socket_path)
        await unix_site.start()
        os.chmod(socket_path, 0o666)
        logger.info('aiohttp server bound to unix socket %s', socket_path)

        if self.port:
            ssl_context = self._build_ssl_context()
            tcp_site = web.TCPSite(
                self.runner,
                host='0.0.0.0',
                port=int(self.port),
                ssl_context=ssl_context,
            )
            await tcp_site.start()
            logger.info('aiohttp server listening on TCP port %s', self.port)

        # Phase 6 will start the debugger TCP server here.

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
        """Synchronous entry point used by the CLI.

        Mirrors the legacy GnrBaseAsyncServer.start() signature so callers
        (gnrpy/gnr/app/cli/gnrasync.py and serverwsgi.py) need no changes.
        """
        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            pass

    def logToPage(self, page_id, **kwargs):
        self.pages[page_id].log(**kwargs)


class GnrAsyncServer(GnrBaseAsyncServer):
    """Concrete server. Phase 2 wires only the threadpool executor.

    WebSocket handlers, WsProxy and SharedObjectsManager are added in
    subsequent phases (3, 4, 5).
    """

    def __init__(self, *args, **kwargs):
        # The legacy server accepts a `web=True` kwarg that turned Tornado
        # into a full WSGI container as well. That mode is dropped (Fase 7);
        # we still accept the kwarg for CLI compat but ignore it.
        kwargs.pop('web', None)
        super().__init__(*args, **kwargs)
        self.addExecutor('threadpool', ThreadPoolExecutor(max_workers=20))


if __name__ == '__main__':
    server = GnrAsyncServer(port=8888, instance='sandbox')
    server.start()
