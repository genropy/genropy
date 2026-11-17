#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct

from gnr.lib.services.antivirus import AntivirusService
from gnr.web.gnrbaseclasses import BaseComponent


class Service(AntivirusService):
    """Scans with a ClamAV ``clamd`` daemon listening on ``host`` and ``port``,
    through its ``INSTREAM`` command. The content travels on the connection:
    the daemon needs no access to the storage of the site.

    clamd has no authentication and its traffic is not encrypted: keep its
    port reachable only from the sites that use it.

    The limits set in clamd.conf decide what happens to a large file:

    - past ``StreamMaxLength`` (default 100M) clamd closes the connection, and
      the upload is refused as with an unavailable service;
    - past ``MaxFileSize`` (default 100M) or ``MaxScanSize`` (default 400M)
      clamd does not scan the whole content and can answer OK, unless
      ``AlertExceedsMax`` is set: then it reports a threat whose name starts
      with ``Heuristics.Limits.Exceeded``."""
    default_port = 3310
    chunk_size = 65536

    def __init__(self, parent, host=None, port=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.host = host
        self.port = int(port or self.default_port)

    def scan(self, content=None, filename=None, **kwargs):
        if not self.host:
            raise self.unavailable('no host is configured')
        try:
            reply = self.instream(content)
        except OSError as error:
            raise self.unavailable(error)
        if reply.endswith(' OK'):
            return None
        if reply.endswith(' FOUND'):
            return self.threatName(reply)
        raise self.unavailable(reply)

    def instream(self, content):
        """Send the content to clamd and return its reply, e.g. ``stream: OK``
        or ``stream: Eicar-Test-Signature FOUND``."""
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as connection:
            connection.sendall(b'zINSTREAM\0')
            for offset in range(0, len(content), self.chunk_size):
                chunk = content[offset:offset + self.chunk_size]
                connection.sendall(struct.pack('!I', len(chunk)) + chunk)
            connection.sendall(struct.pack('!I', 0))
            reply = b''
            while not reply.endswith(b'\0'):
                data = connection.recv(4096)
                if not data:
                    break
                reply += data
        return reply.rstrip(b'\0').decode('utf-8', 'replace').strip()


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.host', lbl='Host', width='30em')
        fb.numberTextBox(value='^.port', lbl='Port', placeholder=str(Service.default_port))
        fb.numberTextBox(value='^.timeout', lbl='Timeout (seconds)',
                         placeholder=str(Service.default_timeout))
