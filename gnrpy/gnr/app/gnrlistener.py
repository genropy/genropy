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

    from gnr.app.gnrapp import GnrApp
    app = GnrApp('myapp')
    app.listen()
"""

from __future__ import annotations

import json
import logging
import select
import signal
import time

log = logging.getLogger('gnr.listener')


class GnrListener:
    """Multi-channel PostgreSQL LISTEN dispatcher with declarative handlers.

    Args:
        app: The :class:`GnrApp` instance.
        timeout: Seconds to wait on ``select()`` before cycling.
        coalesce: Seconds to sleep after processing a batch of notifications.
    """

    def __init__(self, app, timeout=5, coalesce=1):
        self.app = app
        self.db = app.db
        self.timeout = timeout
        self.coalesce = coalesce
        self._handlers = {}
        self._running = False

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
        """
        if not self._handlers:
            log.warning('No handlers registered — nothing to listen for')
            return

        self._running = True
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        conn = self._listen_connection()
        log.info('GnrListener started — channels: %s', ', '.join(sorted(self.channels)))

        try:
            while self._running:
                if select.select([conn], [], [], self.timeout) != ([], [], []):
                    conn.poll()
                    processed = 0
                    while conn.notifies:
                        notify = conn.notifies.pop(0)
                        self._dispatch(notify)
                        processed += 1
                    if processed and self.coalesce:
                        time.sleep(self.coalesce)
        except Exception:
            log.exception('GnrListener error')
            raise
        finally:
            signal.signal(signal.SIGTERM, original_sigterm)
            signal.signal(signal.SIGINT, original_sigint)
            log.info('GnrListener shutting down')
            conn.close()

    def _listen_connection(self):
        """Open a dedicated AUTOCOMMIT connection via the adapter."""
        conn = self.db.adapter.listen_connection(sorted(self.channels))
        if conn is None:
            raise RuntimeError('The current database adapter does not support LISTEN/NOTIFY')
        for channel in sorted(self.channels):
            log.debug('LISTEN %s', channel)
        return conn

    def _dispatch(self, notify):
        """Route a notification to matching handlers."""
        channel = notify.channel
        handlers = self._handlers.get(channel, [])
        if not handlers:
            return
        try:
            payload = json.loads(notify.payload) if notify.payload else {}
        except (json.JSONDecodeError, TypeError):
            payload = {'raw': notify.payload}

        for handler, filters in handlers:
            if self._matches(payload, filters):
                try:
                    handler(payload)
                except Exception:
                    log.exception('Handler %s failed for %s',
                                  handler.__qualname__, payload)

    def _matches(self, payload, filters):
        """Check if payload matches all filter criteria."""
        for key, value in filters.items():
            if payload.get(key) != value:
                return False
        return True

    def _signal_handler(self, signum, _frame):
        """Handle SIGTERM/SIGINT for clean shutdown."""
        log.info('Received signal %s — stopping', signum)
        self._running = False
