# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy app - see LICENSE for details
# module gnrlistener : Declarative event handling via PostgreSQL LISTEN/NOTIFY
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
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
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
# --------------------------------------------------------------------------

"""GnrListener — declarative event handling via PostgreSQL LISTEN/NOTIFY.

Usage::

    from gnr.app.gnrapplistener import GnrAppListener
    GnrAppListener('myapp').run()
"""

from __future__ import annotations

import select
import signal
import time
from concurrent.futures import ThreadPoolExecutor

from gnr.app import logger
from gnr.core.gnrstring import fromTypedJSON


class GnrListener:
    """Multi-channel PostgreSQL LISTEN dispatcher with declarative handlers.

    Args:
        app: The :class:`GnrApp` instance.
        timeout: Seconds to wait on ``select()`` before cycling.
        coalesce: Seconds to sleep after processing a batch of notifications.
        workers: Number of thread-pool workers for handler execution.
            ``1`` (default) runs handlers synchronously in the main loop.
            ``N > 1`` submits handlers to a ``ThreadPoolExecutor(N)``.
    """

    def __init__(self, app, timeout=5, coalesce=1, workers=1):
        self.app = app
        self.db = app.db
        self.timeout = timeout
        self.coalesce = coalesce
        self.workers = workers
        self._handlers = {}
        self._running = False
        self._executor = None

    def register(self, channel, handler, **filters):
        """Register a handler for a NOTIFY channel.

        Args:
            channel: PostgreSQL channel name (e.g. ``'dbevent'``).
            handler: Callable receiving a single ``payload`` dict argument.
            **filters: Key-value pairs that must match the JSON payload
                for the handler to fire.  E.g. ``table='invc.invoice'``
                means the handler only fires when ``payload['table']``
                equals ``'invc.invoice'``.
        """
        self._handlers.setdefault(channel, []).append((handler, filters))

    @property
    def channels(self):
        """Return the set of distinct channels with registered handlers."""
        return set(self._handlers.keys())

    def run(self):
        """Blocking event loop: LISTEN on all channels, dispatch forever.

        Handles SIGTERM and SIGINT for clean shutdown.
        When ``workers > 1``, handlers run in a thread pool.
        """
        if not self._handlers:
            logger.warning('No handlers registered — nothing to listen for')
            return

        self._running = True
        if self.workers > 1:
            self._executor = ThreadPoolExecutor(max_workers=self.workers)
            logger.info('Thread pool started with %d workers', self.workers)

        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        conn = self._listen_connection()
        logger.info('GnrListener started — channels: %s', ', '.join(sorted(self.channels)))

        try:
            while self._running:
                if select.select([conn], [], [], self.timeout) != ([], [], []):
                    notifications = self.db.adapter.poll_notifications(conn)
                    for notify in notifications:
                        self._dispatch(notify)
                    if notifications and self.coalesce:
                        time.sleep(self.coalesce)
        except Exception:
            logger.exception('GnrListener error')
            raise
        finally:
            if self._executor:
                self._executor.shutdown(wait=True)
                logger.info('Thread pool shut down')
            signal.signal(signal.SIGTERM, original_sigterm)
            signal.signal(signal.SIGINT, original_sigint)
            logger.info('GnrListener shutting down')
            conn.close()

    def _listen_connection(self):
        """Open a dedicated AUTOCOMMIT connection via the adapter."""
        conn = self.db.adapter.listen_connection(sorted(self.channels))
        if conn is None:
            raise RuntimeError('The current database adapter does not support LISTEN/NOTIFY')
        for channel in sorted(self.channels):
            logger.debug('LISTEN %s', channel)
        return conn

    def _dispatch(self, notify):
        """Route a notification to matching handlers."""
        channel = notify.channel
        handlers = self._handlers.get(channel, [])
        if not handlers:
            return
        try:
            payload = fromTypedJSON(notify.payload) if notify.payload else {}
        except (ValueError, TypeError):
            payload = {'raw': notify.payload}

        for handler, filters in handlers:
            if self._matches(payload, filters):
                if self._executor:
                    self._executor.submit(self._safe_call, handler, payload)
                else:
                    self._safe_call(handler, payload)

    @staticmethod
    def _safe_call(handler, payload):
        """Call handler with error logging."""
        try:
            handler(payload)
        except Exception:
            logger.exception('Handler %s failed for %s',
                          handler.__qualname__, payload)

    def _matches(self, payload, filters):
        """Check if payload matches all filter criteria."""
        for key, value in filters.items():
            if key == 'package':
                table_name = payload.get('table')
                if not table_name:
                    return False
                tblobj = self.db.table(table_name)
                if tblobj.pkg.name != value:
                    return False
            elif payload.get(key) != value:
                return False
        return True

    def _signal_handler(self, signum, _frame):
        """Handle SIGTERM/SIGINT for clean shutdown."""
        logger.info('Received signal %s — stopping', signum)
        self._running = False
