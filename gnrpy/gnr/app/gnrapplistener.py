# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy app - see LICENSE for details
# module gnrapplistener : High-level listener launcher via composition
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

"""GnrAppListener — auto-discovery listener wrapper around GnrApp.

Usage::

    from gnr.app.gnrapplistener import GnrAppListener
    GnrAppListener('myapp').run()
"""

from __future__ import annotations

import logging

from gnr.app.gnrapp import GnrApp
from gnr.app.gnrlistener import GnrListener

log = logging.getLogger('gnr.listener')


class GnrAppListener:
    """Wraps a :class:`GnrApp` to auto-discover ``@listen`` handlers and run the listener.

    Args:
        app: Either a :class:`GnrApp` instance or a string (instance name)
            that will be used to create one.
        timeout: Seconds to wait on ``select()`` before cycling.
        coalesce: Seconds to sleep after processing a batch.
        workers: Number of thread-pool workers (1 = synchronous).
    """

    def __init__(self, app, timeout=5, coalesce=1, workers=1):
        if isinstance(app, str):
            app = GnrApp(app)
        self.app = app
        self.timeout = timeout
        self.coalesce = coalesce
        self.workers = workers

    def run(self):
        """Discover @listen handlers, register them, and start the event loop."""
        listener = GnrListener(self.app, timeout=self.timeout,
                               coalesce=self.coalesce, workers=self.workers)
        for dbtable in self.app.db.tables:
            for attr_name in dir(dbtable):
                try:
                    method = getattr(dbtable, attr_name)
                except Exception:
                    continue
                channel = getattr(method, '_listen_channel', None)
                if channel is None:
                    continue
                listener.register(channel, method, table=dbtable.fullname)
        listener.run()
